"""scripts/release_checks.py: the checks a release runs. gearu runs them in its release candidate
(gearu.toml), and anyone may run them to show a tree is ready to tag. Its heavy steps are the
release itself; these tests pin its interface, its metadata check, and that gearu.toml runs every
step once, with the release's version."""

import ast
import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "release_checks.py"


def _script():
    if "release_checks" not in sys.modules:   # registered first, as an import would: dataclass needs it
        spec = importlib.util.spec_from_file_location("release_checks", SCRIPT)
        sys.modules["release_checks"] = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(sys.modules["release_checks"])
    return sys.modules["release_checks"]


def _run(*args):
    return subprocess.run([sys.executable, str(SCRIPT), *args], text=True, capture_output=True)


def test_the_metadata_step_passes_on_this_tree():
    run = _run("0.10.0", "--only", "metadata")
    assert run.returncode == 0, run.stdout + run.stderr
    assert "passed: metadata, for taut-proto 0.10.0" in run.stdout


def test_the_metadata_check_names_each_declaration_it_misses():
    checks = _script()
    good = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert checks.metadata_problems(good) == []
    static = good.replace('dynamic = ["version"]', 'version = "0.10.0"')
    assert checks.metadata_problems(static) == [
        'pyproject.toml: expected project.dynamic = ["version"], which setuptools-scm fills']


@pytest.mark.parametrize("version", ["v0.10.0", "0.10", "0.10.0-rc.1", "0.10.0.dev1", ""])
def test_a_version_that_is_not_a_release_is_refused(version):
    """gearu passes `{python_version}`: 0.10.0, or 0.10.0rc1 for a release candidate."""
    run = _run(version, "--only", "metadata")
    assert run.returncode == 2 and "release_checks.py: error:" in run.stderr, run.stderr
    assert "release version" in run.stderr


@pytest.mark.parametrize("only", ["metadata,nope", "tests,tests", "smoke", ""])
def test_a_bad_step_selection_is_refused(only):
    """An unknown or repeated step, no step, and smoke without the build it installs."""
    run = _run("0.10.0", "--only", only)
    assert run.returncode == 2 and "release_checks.py: error:" in run.stderr, run.stderr


def test_gearu_runs_every_step_on_its_candidate_and_rereads_metadata_on_the_tagged_commit():
    """A tag-derived version needs no release commit, so the commit gearu tags is its candidate:
    `checks` runs every step once, and `exact_checks` only rereads the metadata."""
    tomllib = pytest.importorskip("tomllib")
    release = tomllib.loads((ROOT / "gearu.toml").read_text(encoding="utf-8"))["release"]
    [checks], [exact] = release["checks"], release["exact_checks"]
    for command in (checks, exact):
        assert command[command.index("scripts/release_checks.py") + 1] == "{python_version}"
    assert "--only" not in checks
    assert exact[exact.index("--only") + 1] == "metadata"
    assert {"pytest", "pytest-xdist", "build", "twine"} <= {
        checks[i + 1] for i, arg in enumerate(checks) if arg == "--with"}


def test_metadata_runs_first_and_the_other_steps_side_by_side():
    stages = _script().stages
    assert stages(_script().STEPS) == [[("metadata",)], [("tests",), ("parity",), ("build", "smoke")]]
    assert stages(("metadata",)) == [[("metadata",)]]
    assert stages(("parity", "build", "smoke")) == [[("parity",), ("build", "smoke")]]


def test_the_tests_step_names_each_skipped_test_but_not_an_expected_failure(tmp_path):
    """A test whose toolchain is missing skips, and a release runs every test, so the tests step
    fails on a skip and names it. pytest's JUnit report files an xfail as skipped too."""
    report = tmp_path / "pytest.xml"
    report.write_text(
        '<?xml version="1.0" encoding="utf-8"?><testsuites><testsuite name="pytest">'
        '<testcase classname="tests.test_kotlin" name="test_a">'
        '<skipped type="pytest.skip" message="no kotlinc that runs">detail</skipped></testcase>'
        '<testcase classname="tests.test_x" name="test_b">'
        '<skipped type="pytest.xfail" message="known"/></testcase>'
        '<testcase classname="tests.test_x" name="test_c"/>'
        '</testsuite></testsuites>', encoding="utf-8")
    assert _script().skipped_tests(report) == ["tests.test_kotlin.test_a: no kotlinc that runs"]


def _gate_reruns():
    """Each test that reruns what the parity step runs, with whether it is marked `gate`: one
    that runs the whole gate (`parity.run_gate(run_compiled=True)`), or a target's real runner
    through `parity.governed_variants`."""
    found = {}
    for path in sorted((ROOT / "src" / "tests").glob("test_*.py")):
        for fn in ast.parse(path.read_text(encoding="utf-8")).body:
            if not (isinstance(fn, ast.FunctionDef) and fn.name.startswith("test_")):
                continue
            for call in (node for node in ast.walk(fn) if isinstance(node, ast.Call)):
                name = ast.unparse(call.func)
                runner = (name == "parity.governed_variants" and call.args
                          and ast.unparse(call.args[0]).startswith("parity_"))
                whole = name == "parity.run_gate" and any(
                    k.arg == "run_compiled" and ast.unparse(k.value) == "True" for k in call.keywords)
                if runner or whole:
                    marks = {ast.unparse(d) for d in fn.decorator_list}
                    found[f"{path.name}::{fn.name}"] = "pytest.mark.gate" in marks
    return found


def test_every_test_that_reruns_the_gate_is_marked_gate():
    """The release's tests step deselects `gate` tests, because its parity step runs the whole
    gate with --require-all. An unmarked rerun would build every target twice."""
    found = _gate_reruns()
    assert len(found) == 8, found      # the whole gate, and seven generated targets' own runs
    assert [name for name, marked in found.items() if not marked] == []
