"""Read-only HEAD comparison and isolated baseline reproduction. No worktree/reset."""
from pathlib import Path
import hashlib
import io
import json
import os
import subprocess
import sys
import zipfile

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
BASELINE = HERE / "scratch/baseline-head"
RESULTS = HERE / "results"


def git(*args, check=True):
    return subprocess.run(["git", "-c", f"safe.directory={REPO.as_posix()}", "-C", str(REPO), *args],
                          capture_output=True, check=check)


def main():
    RESULTS.mkdir(exist_ok=True)
    head = git("rev-parse", "HEAD").stdout.decode().strip()
    missing = "dev-docs/TautProtoApiSurfaceExtensions.md"
    absent = git("cat-file", "-e", f"HEAD:{missing}", check=False)
    assert absent.returncode != 0 and not (REPO / missing).exists()
    paths = ["src/tests/test_dev_docs.py", "src/tests/test_go.py", "src/taut/gen/go.py",
             "src/taut/corpus/parity_go.py", "src/tests/test_java.py", "src/taut/gen/java.py",
             "src/taut/gen/runtime/Cbor.java", "src/tests/test_rust.py"]
    paths += [p.relative_to(REPO).as_posix() for p in (REPO / "src/taut/gen/runtime").glob("*.go")]
    comparisons = {}
    for path in paths:
        original = git("show", f"HEAD:{path}").stdout
        current = (REPO / path).read_bytes()
        same = original.decode("utf-8").replace("\r\n", "\n") == current.decode("utf-8").replace("\r\n", "\n")
        assert same, path
        comparisons[path] = {"same_source": same, "head_sha256": hashlib.sha256(original).hexdigest(),
                             "working_sha256": hashlib.sha256(current).hexdigest(),
                             "git_diff_empty": not git("diff", "HEAD", "--", path).stdout}
    archive = git("archive", "--format=zip", "HEAD", "src", "ir", "corpus").stdout
    BASELINE.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(archive)) as z:
        for item in z.infolist():
            if not (BASELINE / item.filename).resolve().is_relative_to(BASELINE.resolve()):
                raise ValueError("archive path outside baseline root")
        z.extractall(BASELINE)
    env = dict(os.environ, PYTHONPATH=str(BASELINE / "src") + os.pathsep +
               str(Path(os.environ["LOCALAPPDATA"]) / "Programs/Python/Python311/Lib/site-packages"),
               PYTEST_DISABLE_PLUGIN_AUTOLOAD="1")
    tests = ["src/tests/test_dev_docs.py::test_proto_api_surface_extensions_doc_exists_and_covers_contract",
             "src/tests/test_go.py::test_go_runtime_and_parity_runner_are_gofmt_clean",
             "src/tests/test_go.py::test_generated_go_is_gofmt_clean"]
    result = subprocess.run([sys.executable, "-m", "pytest", *tests, "-q", "--tb=short"], cwd=BASELINE,
                            env=env, capture_output=True, text=True, encoding="utf-8")
    (RESULTS / "baseline-head-tests.log").write_text(result.stdout + result.stderr, encoding="utf-8")
    assert result.returncode == 1 and "3 failed" in result.stdout, result.stdout + result.stderr
    diagnostic = '''
from pathlib import Path
import importlib.util, json, subprocess
spec=importlib.util.spec_from_file_location('baseline_go_tests', 'src/tests/test_go.py')
m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
sources={'runner': m.parity_go._source(), **m._generated_go()}
out=Path('line-ending-probe');out.mkdir(exist_ok=True)
observations={}
for name, source in sources.items():
    default=out/(name+'_default.go'); lf=out/(name+'_lf.go')
    default.write_text(source, encoding='utf-8')
    lf.write_text(source, encoding='utf-8', newline='\\n')
    a=subprocess.run(['gofmt','-l',str(default)],capture_output=True,text=True)
    b=subprocess.run(['gofmt','-l',str(lf)],capture_output=True,text=True)
    assert a.returncode==b.returncode==0 and a.stdout.strip() and not b.stdout.strip()
    assert b'\\r\\n' in default.read_bytes() and b'\\r\\n' not in lf.read_bytes()
    observations[name]={'default_has_crlf':True,'default_gofmt_lists_file':True,'same_source_lf_gofmt_clean':True}
print(json.dumps(observations,sort_keys=True))
'''
    probe = subprocess.run([sys.executable, "-c", diagnostic], cwd=BASELINE, env=env,
                           capture_output=True, text=True, encoding="utf-8")
    assert probe.returncode == 0, probe.stdout + probe.stderr
    java_test = "src/tests/test_java.py::test_java_decode_error_key_is_text"
    java_env = dict(env)
    java_env.pop("JAVA_TOOL_OPTIONS", None)
    java_baseline = subprocess.run([sys.executable, "-m", "pytest", java_test, "-q", "--tb=short"],
                                   cwd=BASELINE, env=java_env, capture_output=True, text=True, encoding="utf-8")
    (RESULTS / "baseline-java-encoding.log").write_text(java_baseline.stdout + java_baseline.stderr, encoding="utf-8")
    assert java_baseline.returncode == 1 and "1 failed" in java_baseline.stdout
    unsafe_env = dict(os.environ)
    for key in list(unsafe_env):
        if key.startswith(("GIT_CONFIG_", "GIT_CONFIG_COUNT")):
            unsafe_env.pop(key)
    ownership = subprocess.run(["git", "-C", str(REPO), "describe", "--tags", "--abbrev=0", "--match", "v[0-9]*"],
                               env=unsafe_env, capture_output=True, text=True)
    assert ownership.returncode == 128 and "dubious ownership" in ownership.stderr
    fixed_env = dict(os.environ, PYTHONPATH=str(REPO / "src") + os.pathsep +
                     str(Path(os.environ["LOCALAPPDATA"]) / "Programs/Python/Python311/Lib/site-packages"),
                     PYTEST_DISABLE_PLUGIN_AUTOLOAD="1", JAVA_TOOL_OPTIONS="-Dfile.encoding=UTF-8",
                     GIT_CONFIG_COUNT="1", GIT_CONFIG_KEY_0="safe.directory", GIT_CONFIG_VALUE_0=REPO.as_posix())
    fixed = subprocess.run([sys.executable, "-m", "pytest", java_test,
                           "src/tests/test_rust.py::test_glade_build_names_the_release_tag_its_checkout_descends_from",
                           "-q"], cwd=REPO, env=fixed_env, capture_output=True, text=True, encoding="utf-8")
    assert fixed.returncode == 0 and "2 passed" in fixed.stdout, fixed.stdout + fixed.stderr
    (RESULTS / "corrected-environment-tests.log").write_text(fixed.stdout + fixed.stderr, encoding="utf-8")
    evidence = {"head": head, "missing_document": {"path": missing, "absent_in_head": True,
                "cat_file_exit": absent.returncode, "cat_file_stderr": absent.stderr.decode().strip()},
                "unchanged_sources": comparisons, "isolated_head_test_exit": result.returncode,
                "isolated_head_result": "3 failed (same missing doc and two gofmt tests)",
                "line_ending_probe": json.loads(probe.stdout),
                "java_baseline_result": "1 failed, original HEAD test without UTF-8 Java stdout override",
                "git_original_environment": {"exit": ownership.returncode, "stderr": ownership.stderr},
                "corrected_environment_result": "2 passed (Java encoding and Rust Git-tag test)",
                "note": "Baseline archive is disposable under Limbo; no original source was reset or edited."}
    (RESULTS / "baseline-evidence.json").write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    print(f"HEAD {head}: document absent; all {len(comparisons)} source comparisons unchanged.")
    print("Isolated HEAD: same 3 failures reproduced. Identical Go source written with LF: gofmt clean for all files.")
    print("Isolated HEAD Java: same encoding failure. Git ownership failure reproduced read-only; corrected Java/Git tests: 2 passed.")


if __name__ == "__main__":
    main()
