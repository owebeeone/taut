#!/usr/bin/env python3
"""Show that this tree is ready to release taut-proto VERSION. Nothing here tags, pushes or
publishes, and no git state changes: what a step builds goes to a temporary directory, removed
when the checks end.

gearu runs these checks in its release candidate (gearu.toml): `checks` runs metadata, tests and
parity, and `exact_checks` runs build and smoke on the commit it tags. To show a tree is ready to
tag without gearu, run every step:

    uv run --no-project --python 3.13 --with pytest --with build --with twine \\
        python scripts/release_checks.py 0.10.0

The steps, in order (`--only` selects some):
- metadata: pyproject.toml keeps the distribution's name, its version dynamic for setuptools-scm
  and the `tautc` script;
- tests: the whole suite, `pytest src/tests`, where a skipped test fails the release: a test
  skips when its toolchain is missing;
- parity: `tautc parity --require-all`: every language and forward-compat build runs, so a
  missing toolchain fails the release rather than skipping its target;
- build: `python -m build` at VERSION, which setuptools-scm is told because the tag does not exist
  yet; `twine check`; and every vendored runtime file in the wheel;
- smoke: the wheel in a fresh venv reports VERSION and imports; its `tautc` writes Rust types,
  and generates every target with its runtime exactly as this tree's source does.
"""

from __future__ import annotations

import argparse
import importlib.util
import os
import re
import subprocess
import sys
import tempfile
import zipfile
from collections.abc import Callable
from pathlib import Path
from xml.etree import ElementTree

REPO = Path(__file__).resolve().parent.parent
PACKAGE_NAME = "taut-proto"
PRETEND_VERSION_ENV = "SETUPTOOLS_SCM_PRETEND_VERSION_FOR_TAUT_PROTO"
RUNTIME = REPO / "src" / "taut" / "gen" / "runtime"
SMOKE_IR = REPO / "ir" / "griplab.taut.py"
STEPS = ("metadata", "tests", "parity", "build", "smoke")
# A release version as gearu's {python_version} writes it: 1.2.3, or 1.2.3rc1 for a candidate.
RELEASE_VERSION = re.compile(r"\d+\.\d+\.\d+(?:rc\d+)?")


class NotReady(Exception):
    """A step found the tree not ready to release; the message says why."""


def log(message: str) -> None:
    print(f"[release-checks] {message}", flush=True)


def run(command: list[object], *, env: dict[str, str] | None = None) -> None:
    argv = [str(part) for part in command]
    log("$ " + " ".join(argv))
    code = subprocess.run(argv, cwd=REPO, env=env).returncode
    if code != 0:
        raise NotReady(f"exit {code}: {' '.join(argv)}")


def source_env() -> dict[str, str]:
    """The environment that runs this tree's source: `src` first on PYTHONPATH."""
    env = os.environ.copy()
    src = str(REPO / "src")
    env["PYTHONPATH"] = src + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
    return env


def require_modules(*names: str) -> None:
    missing = [name for name in names if importlib.util.find_spec(name) is None]
    if missing:
        raise NotReady(f"this Python lacks {', '.join(missing)}: run the checks under `uv run "
                       "--no-project --python 3.13 --with pytest --with build --with twine`")


def metadata_problems(text: str) -> list[str]:
    """What pyproject.toml's `text` lacks of what a release needs."""
    needs = {
        f'project.name = "{PACKAGE_NAME}"': rf'(?m)^name\s*=\s*"{re.escape(PACKAGE_NAME)}"$',
        'project.dynamic = ["version"], which setuptools-scm fills':
            r'(?m)^dynamic\s*=\s*\["version"\]$',
        'project.scripts.tautc = "taut.cli:main"':
            r'(?m)^tautc\s*=\s*"taut\.cli:main"(?:\s*(?:#.*)?)$',
    }
    return [f"pyproject.toml: expected {need}" for need, pattern in needs.items()
            if not re.search(pattern, text)]


def missing_runtime(wheel: Path) -> list[str]:
    """This tree's vendored runtime files that `wheel` does not hold. `tautc gen --with-runtime`
    skips a runtime file it cannot find, so a gap in package-data would not fail there."""
    with zipfile.ZipFile(wheel) as archive:
        held = set(archive.namelist())
    wanted = sorted("taut/gen/runtime/" + path.relative_to(RUNTIME).as_posix()
                    for path in RUNTIME.rglob("*")
                    if path.is_file() and "__pycache__" not in path.parts)
    return [name for name in wanted if name not in held]


def skipped_tests(report: Path) -> list[str]:
    """Each test pytest's JUnit `report` records as skipped, with its reason. An expected failure
    (xfail), which the report also files as skipped, is not one."""
    root = ElementTree.parse(report).getroot()
    return [f"{case.get('classname')}.{case.get('name')}: {skip.get('message', '')}"
            for case in root.iter("testcase") for skip in case.findall("skipped")
            if skip.get("type") != "pytest.xfail"]


def tree_differences(left: Path, right: Path) -> list[str]:
    """Each file path under either tree that the other lacks, or holds with other bytes."""
    def files(root: Path) -> dict[str, Path]:
        return {path.relative_to(root).as_posix(): path for path in root.rglob("*") if path.is_file()}

    a, b = files(left), files(right)
    return sorted(name for name in a.keys() | b.keys()
                  if name not in a or name not in b or a[name].read_bytes() != b[name].read_bytes())


def artifacts(version: str, work: Path) -> tuple[Path, Path]:
    """The sdist and wheel the build step makes."""
    dist = work / "dist"
    return dist / f"taut_proto-{version}.tar.gz", dist / f"taut_proto-{version}-py3-none-any.whl"


def venv_bin(venv: Path, name: str) -> Path:
    if os.name == "nt":
        return venv / "Scripts" / f"{name}.exe"
    return venv / "bin" / name


def step_metadata(version: str, work: Path) -> None:
    problems = metadata_problems((REPO / "pyproject.toml").read_text(encoding="utf-8"))
    if problems:
        raise NotReady("\n".join(problems))


def step_tests(version: str, work: Path) -> None:
    require_modules("pytest")
    report = work / "pytest.xml"
    run([sys.executable, "-m", "pytest", "src/tests", "-q", "-rs", "-p", "no:cacheprovider",
         f"--basetemp={work / 'pytest'}", f"--junit-xml={report}"], env=source_env())
    skipped = skipped_tests(report)
    if skipped:
        raise NotReady(f"{len(skipped)} tests skipped, and a release runs every test; install what "
                       "they name:\n  " + "\n  ".join(skipped))


def step_parity(version: str, work: Path) -> None:
    run([sys.executable, "-m", "taut.cli", "parity", "--require-all"], env=source_env())


def step_build(version: str, work: Path) -> None:
    require_modules("build", "twine")
    env = os.environ.copy()
    env[PRETEND_VERSION_ENV] = version
    run([sys.executable, "-m", "build", "--outdir", work / "dist"], env=env)
    built = sorted(path.name for path in (work / "dist").iterdir())
    expected = sorted(path.name for path in artifacts(version, work))
    if built != expected:
        raise NotReady(f"built {built}, expected {expected}")
    run([sys.executable, "-m", "twine", "check", *artifacts(version, work)])
    missing = missing_runtime(artifacts(version, work)[1])
    if missing:
        raise NotReady("the wheel lacks vendored runtime files: " + ", ".join(missing))


def step_smoke(version: str, work: Path) -> None:
    venv = work / "venv"
    run([sys.executable, "-m", "venv", venv])
    python = venv_bin(venv, "python")
    run([python, "-m", "pip", "install", "--quiet", artifacts(version, work)[1]])
    run([python, "-c", "import importlib.metadata as md, taut, taut.cli; "
                       f"found = md.version({PACKAGE_NAME!r}); "
                       f"assert found == {version!r}, found; print('import and version OK')"])
    tautc = venv_bin(venv, "tautc")
    rust = work / "smoke-rust"
    run([tautc, "gen", SMOKE_IR, "-o", rust, "--lang", "rust", "--api-only"])
    if not (rust / "rust" / "api.rs").is_file():
        raise NotReady("the wheel's tautc wrote no rust/api.rs")
    from_wheel, from_source = work / "gen-wheel", work / "gen-source"
    run([tautc, "gen", SMOKE_IR, "-o", from_wheel, "--with-runtime", "--forward-compat"])
    run([sys.executable, "-m", "taut.cli", "gen", SMOKE_IR, "-o", from_source, "--with-runtime",
         "--forward-compat"], env=source_env())
    differ = tree_differences(from_wheel, from_source)
    if differ:
        raise NotReady("the wheel's tautc does not generate what this tree does: " + ", ".join(differ))
    log(f"the wheel generates every target as this tree does: {len(list(from_wheel.rglob('*.*')))} files")


STEP_RUNS: dict[str, Callable[[str, Path], None]] = {
    "metadata": step_metadata,
    "tests": step_tests,
    "parity": step_parity,
    "build": step_build,
    "smoke": step_smoke,
}


def selected_steps(parser: argparse.ArgumentParser, only: str | None) -> tuple[str, ...]:
    if only is None:
        return STEPS
    names = only.split(",")
    if not only or any(name not in STEPS for name in names):
        parser.error(f"--only takes steps from {','.join(STEPS)}, not {only!r}")
    if len(set(names)) != len(names):
        parser.error(f"--only names a step twice: {only!r}")
    if "smoke" in names and "build" not in names:
        parser.error("smoke installs the wheel that build makes: select build too")
    return tuple(step for step in STEPS if step in names)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="release_checks.py",
        description="Show that this tree is ready to release taut-proto VERSION. Nothing is "
                    "tagged, pushed or published.")
    parser.add_argument("version", help="the release version as PEP 440 writes it: 0.10.0, or "
                                        "0.10.0rc1 for a release candidate (gearu's {python_version})")
    parser.add_argument("--only", metavar="STEPS",
                        help=f"comma-separated steps, run in their order (default: all): {','.join(STEPS)}")
    args = parser.parse_args(argv)
    if not RELEASE_VERSION.fullmatch(args.version):
        parser.error(f"{args.version!r} is not a release version, such as 0.10.0 or 0.10.0rc1")
    steps = selected_steps(parser, args.only)
    with tempfile.TemporaryDirectory(prefix="taut-release-checks-") as tmp:
        for step in steps:
            log(f"== {step}")
            try:
                STEP_RUNS[step](args.version, Path(tmp))
            except NotReady as problem:
                print(f"[release-checks] not ready, at {step}: {problem}", file=sys.stderr, flush=True)
                return 1
    log(f"passed: {', '.join(steps)}, for {PACKAGE_NAME} {args.version}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
