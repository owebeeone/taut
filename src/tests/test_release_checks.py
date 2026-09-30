"""scripts/release_checks.py: the checks a release runs. gearu runs them in its release candidate
(gearu.toml), and anyone may run them to show a tree is ready to tag. Its heavy steps are the
release itself; these tests pin its interface, its metadata check, and that gearu.toml runs every
step once, with the release's version."""

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "release_checks.py"


def _script():
    spec = importlib.util.spec_from_file_location("release_checks", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


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


def test_gearu_runs_every_step_once_with_the_release_version():
    tomllib = pytest.importorskip("tomllib")
    release = tomllib.loads((ROOT / "gearu.toml").read_text(encoding="utf-8"))["release"]
    steps = []
    for command in (*release["checks"], *release["exact_checks"]):
        assert command[command.index("scripts/release_checks.py") + 1] == "{python_version}"
        steps += command[command.index("--only") + 1].split(",")
    assert steps == list(_script().STEPS)


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
