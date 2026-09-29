"""The governed parity gate (TautCodecParityPlan.md §8 P1; TautCheckedDecode.md CD-C4, §5.4).

Which targets are gated and which allowlisted is data, in corpus/parity/allowlist.json;
no test here pins a target's status. The tests check that the artifacts validate,
that the comparator and the report parser enforce the runner protocol (an accept row,
payloads compared as strings, a row never reported, a runner exiting non-zero, a
build that fails), that a target's runner is found by module, and, end-to-end with
whatever toolchains are present, that the gate's governance is clean.
"""

import importlib.util
import json
import os
import sys
import textwrap

import pytest

import taut.corpus
from taut.cli import main
from taut.corpus import parity, toolchains

INT_ROWS = 11
MALFORMED_ROWS = 31


def _row(name):
    return next(r for r in parity.malformed_rows() if r["name"] == name)


def _passing_lines():
    """The report a runner prints when every row behaves as the corpus expects."""
    lines = [f"{row['name']}\t{parity.PASS}\t" for row in parity.int_rows()]
    for row in parity.malformed_rows():
        expect = row["expect"]
        if expect.get("accept"):
            lines.append(f"{row['name']}\t{parity.OK}\t")
        else:
            lines.append(f"{row['name']}\t{parity.ERR}\t{parity.format_error(expect['tag'], expect)}")
    return lines


# --- artifacts ------------------------------------------------------------------

def test_int_and_malformed_artifacts_validate():
    assert parity.validate_int_vectors() == INT_ROWS
    assert parity.validate_malformed_vectors() == MALFORMED_ROWS


def test_malformed_rows_expect_a_known_tag_or_accept(tmp_path):
    data = json.loads(parity.MALFORMED_VECTORS.read_text())
    accept = {r["name"] for r in data["vectors"] if "accept" in r["expect"]}
    assert {"map-key-2^53", "optional-present-null"} <= accept      # M8, M15
    for bad in ({"accept": False}, {"accept": True, "tag": "Truncated"},
                {"tag": "Malformed"}, {"tag": "MissingKey", "field": 1}):
        data["vectors"][0]["expect"] = bad
        path = tmp_path / "malformed.vectors.json"
        path.write_text(json.dumps(data))
        with pytest.raises(parity.ParityValidationError):
            parity.validate_malformed_vectors(path)


def test_malformed_rows_name_the_fixture_messages():
    schema = parity.parity_schema()
    for row in parity.malformed_rows():
        if row["stage"] == "from_cbor":
            assert row["schema"] in schema.messages, row["name"]
        if row["stage"] == "from_wire":
            assert row["schema"] in schema.enums, row["name"]
    assert {"OptBox", "Empty"} <= set(schema.messages)


def test_committed_vectors_match_generator():
    """The committed .json is exactly `gen_vectors.py` output — reviewable AND
    regenerable, and no hand-edit has drifted from the generator."""
    spec = importlib.util.spec_from_file_location(
        "parity_gen_vectors", parity.PARITY_DIR / "gen_vectors.py")
    gen = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gen)
    assert gen.render(gen.INT_VECTORS) == parity.INT_VECTORS.read_text()
    assert gen.render(gen.MALFORMED_VECTORS) == parity.MALFORMED_VECTORS.read_text()


# --- allowlist governance ---------------------------------------------------------

def test_every_allowlisted_target_has_phase_owner_and_reason():
    entries = json.loads(parity.ALLOWLIST.read_text())["targets"]
    for entry in entries:
        assert entry["target"] in parity.TARGETS
        for key in ("phase", "owner", "reason"):
            assert isinstance(entry.get(key), str) and entry[key], (entry["target"], key)
    statuses = {s.target: s for s in parity.target_statuses()}
    assert {e["target"] for e in entries} == {t for t, s in statuses.items() if s.status == "allowlisted"}


def _allowlist(tmp_path, *entries):
    path = tmp_path / "allowlist.json"
    path.write_text(json.dumps({"version": 1, "targets": list(entries)}))
    return path


ENTRY = {"target": "java", "phase": "P2", "owner": "codec-parity", "reason": "fails M1"}


@pytest.mark.parametrize("key", ["phase", "owner", "reason"])
def test_target_statuses_rejects_an_entry_without_phase_owner_or_reason(tmp_path, key):
    assert parity.allowlisted_targets(_allowlist(tmp_path, ENTRY)) == {"java"}
    entry = {k: v for k, v in ENTRY.items() if k != key}
    with pytest.raises(parity.ParityValidationError, match=f"no allowlist {key}"):
        parity.target_statuses(_allowlist(tmp_path, entry))


def test_target_statuses_rejects_duplicate_allowlist_entry(tmp_path):
    with pytest.raises(parity.ParityValidationError, match="duplicate target"):
        parity.target_statuses(_allowlist(tmp_path, ENTRY, dict(ENTRY)))


def test_governance_flags_a_green_but_allowlisted_target():
    # Inverse check that makes the gate LEAD: the day a target passes fully it
    # must be de-listed, or CI fails.
    green = parity.TargetReport("python", available=True, results=[
        parity.VectorResult("ok", "malformed", "Truncated", parity.PASS, "", False),
    ])
    assert parity.governance({"python": green}, {"python"})      # green + listed -> violation
    assert parity.governance({"python": green}, set()) == []     # green + gated -> fine


def test_governance_flags_a_gated_target_that_fails():
    red = parity.TargetReport("python", available=True, results=[
        parity.VectorResult("boom", "malformed", "NonCanonicalInt", parity.FAIL, "decoded ok", True),
    ])
    assert parity.governance({"python": red}, set())             # red + gated -> violation
    assert parity.governance({"python": red}, {"python"}) == []  # red + listed -> fine


def test_skipped_target_is_not_a_violation():
    skipped = parity.skipped("rust", "rustc absent")
    assert not skipped.available and skipped.skip_reason == "rustc absent"
    assert parity.governance({"rust": skipped}, set()) == []
    assert parity.governance({"rust": skipped}, {"rust"}) == []


# --- the comparator -------------------------------------------------------------

def test_an_accept_row_passes_only_on_ok():
    row = _row("map-key-2^53")
    assert parity.judge("js", row, parity.OK, "")[0] == parity.PASS
    assert parity.judge("js", row, parity.ERR, "NonIntegerMapKey")[0] == parity.FAIL
    assert parity.judge("js", row, parity.UNTYPED, "RangeError: x")[0] == parity.FAIL


def test_a_tag_row_compares_the_tag_and_every_named_payload_field_as_a_string():
    row = _row("key-first-negative")                     # {"tag": "NegativeMapKey", "key": "-1"}
    assert parity.judge("js", row, parity.ERR, "NegativeMapKey;key=-1") == (parity.PASS, "")
    assert parity.judge("js", row, parity.ERR, "NegativeMapKey;key=1")[0] == parity.FAIL
    assert parity.judge("js", row, parity.ERR, "NegativeMapKey")[0] == parity.FAIL  # payload missing
    assert parity.judge("js", row, parity.ERR, "Truncated")[0] == parity.FAIL
    assert parity.judge("js", row, parity.OK, "")[0] == parity.FAIL
    assert parity.judge("js", row, parity.UNTYPED, "TypeError: x")[0] == parity.FAIL
    assert parity.judge("js", row, "pass", "")[0] == parity.FAIL                 # not an outcome
    status, detail = parity.judge("js", _row("wrong-type-text"), parity.ERR, "WrongType;expected=str")
    assert status == parity.FAIL and detail == "got WrongType;expected=str, expected WrongType;expected=text"
    # an int in the row and in the report compare equal; fields the row does not name are ignored
    assert parity.judge("js", _row("key-first-duplicate"), parity.ERR,
                        "DuplicateMapKey;key=1;value=0")[0] == parity.PASS


def test_payload_exemptions_are_per_target():
    row = _row("positive-int-overflow")                  # {"tag": "IntOverflow", "value": "9223372036854775808"}
    assert parity.PAYLOAD_EXEMPT == {"rust": frozenset({("IntOverflow", "value")})}
    assert parity.judge("rust", row, parity.ERR, "IntOverflow")[0] == parity.PASS
    assert parity.judge("python", row, parity.ERR, "IntOverflow")[0] == parity.FAIL
    assert parity.judge("python", row, parity.ERR, "IntOverflow;value=9223372036854775808")[0] == parity.PASS


# --- report parsing and hardening -----------------------------------------------------

def test_a_complete_passing_report_is_green():
    report = parity.parse_report("js", "\n".join(_passing_lines()) + "\n")
    assert report.green
    assert len(report.results) == INT_ROWS + MALFORMED_ROWS


def test_a_row_never_reported_fails():
    lines = [line for line in _passing_lines() if not line.startswith("optional-absent\t")]
    report = parity.parse_report("js", "\n".join(lines))
    assert not report.green
    assert [(r.name, r.detail) for r in report.failures] == [("optional-absent", parity.NO_REPORT)]


def test_a_runner_exiting_non_zero_fails_its_target_even_if_every_row_passed():
    report = parity.parse_report("js", "\n".join(_passing_lines()), returncode=101, stderr="boom")
    assert report.failures == []
    assert not report.green
    assert report.fault.startswith("runner exited 101")
    assert parity.governance({"js": report}, set())


def test_a_row_reported_twice_or_unknown_or_with_a_bad_outcome_fails():
    lines = _passing_lines()
    report = parity.parse_report("js", "\n".join([*lines, lines[-1]]))
    assert [r.detail for r in report.failures] == ["reported more than once"]
    report = parity.parse_report("js", "\n".join([*lines, "no-such-row\tok\t"]))
    assert report.failures == [] and "no-such-row" in report.fault and not report.green
    name = parity.int_rows()[0]["name"]
    report = parity.parse_report("js", "\n".join([f"{name}\tok\t", *lines[1:]]))
    assert [(r.name, r.status) for r in report.failures] == [(name, parity.FAIL)]


def test_a_build_failure_is_red_not_a_skip(tmp_path):
    ok = parity.build("go", [sys.executable, "-c", "pass"], cwd=tmp_path)
    assert ok is None
    red = parity.build("go", [sys.executable, "-c", "import sys; sys.stderr.write('bad'); sys.exit(2)"],
                       cwd=tmp_path)
    assert red.available and not red.green
    assert red.fault.startswith("build failed (exit 2)") and "bad" in red.fault
    assert {r.detail for r in red.results} == {parity.NO_REPORT}
    assert parity.governance({"go": red}, set())


def test_a_generator_refusal_is_red(tmp_path):
    red = parity.generate("no-such-language", tmp_path)
    assert red is not None and red.available and not red.green
    assert red.fault.startswith("generation failed")


def test_run_runner_judges_the_report_and_the_exit_status(tmp_path):
    (tmp_path / "report.txt").write_text("\n".join(_passing_lines()) + "\n")
    emit = "import sys; sys.stdout.write(open('report.txt').read()); sys.exit({})"
    assert parity.run_runner("js", [sys.executable, "-c", emit.format(0)], cwd=tmp_path).green
    red = parity.run_runner("js", [sys.executable, "-c", emit.format(1)], cwd=tmp_path)
    assert red.failures == [] and red.fault.startswith("runner exited 1")
    missing = parity.run_runner("js", [str(tmp_path / "no-such-runner")], cwd=tmp_path)
    assert missing.available and missing.fault.startswith("runner did not start")


# --- the Python harness -----------------------------------------------------------

def test_python_harness_reports_every_row_and_its_governance_is_clean():
    report = parity.run_python()
    assert report.available
    assert len(report.results) == INT_ROWS + MALFORMED_ROWS
    assert parity.governance({"python": report}, parity.allowlisted_targets()) == []


def test_python_harness_uses_the_gate_comparator(monkeypatch):
    judged = []
    real = parity.judge

    def spy(target, row, outcome, detail):
        judged.append((target, row["name"]))
        return real(target, row, outcome, detail)

    monkeypatch.setattr(parity, "judge", spy)
    parity.run_python()
    assert judged == [("python", row["name"]) for row in parity.malformed_rows()]


# --- the registry and the default run ---------------------------------------------------

def test_a_target_has_a_runner_exactly_when_its_module_exists():
    for target in parity.TARGETS:
        module = importlib.util.find_spec(f"taut.corpus.parity_{target}")
        assert (target in parity._RUNNERS) == (target == "python" or module is not None), target
    assert "python" in parity._RUNNERS and "no-such-target" not in parity._RUNNERS
    assert list(parity._RUNNERS) == [t for t in parity.TARGETS if t in parity._RUNNERS]


def test_adding_a_runner_module_adds_a_target_to_the_gate(tmp_path, monkeypatch):
    target = next((t for t in parity.TARGETS if t not in parity._RUNNERS), None)
    if target is None:
        pytest.skip("every target already has a runner module")
    module = f"taut.corpus.parity_{target}"
    (tmp_path / f"parity_{target}.py").write_text(textwrap.dedent(f"""
        from taut.corpus import parity

        STDOUT = ""

        def run():
            return parity.parse_report({target!r}, STDOUT)
    """))
    monkeypatch.setattr(taut.corpus, "__path__", [*taut.corpus.__path__, str(tmp_path)])
    importlib.invalidate_caches()
    try:
        assert target in parity._RUNNERS
        runner = importlib.import_module(module)
        listed = target in parity.allowlisted_targets()
        runner.STDOUT = "\n".join(_passing_lines())                  # green
        outcome = parity.run_gate(target=target)
        assert outcome.reports[target].green
        assert bool(outcome.violations) == listed                     # a green target must be de-listed
        runner.STDOUT = ""                                           # red: no row reported
        outcome = parity.run_gate(target=target)
        assert not outcome.reports[target].green
        assert bool(outcome.violations) == (not listed)
    finally:
        sys.modules.pop(module, None)


def test_the_gate_runs_every_target_with_a_runner_by_default(monkeypatch):
    def fake(target):
        return lambda: parity.skipped(target, "fake toolchain")

    monkeypatch.setattr(parity, "_RUNNERS", {"python": fake("python"), "go": fake("go")})
    assert set(parity.run_gate().reports) == {"python", "go"}
    assert set(parity.run_gate(run_compiled=False).reports) == {"python"}
    assert set(parity.run_gate(target="go").reports) == {"go"}
    assert parity.run_gate(target="java").reports == {}           # no runner: not run


def test_a_runner_that_raises_is_red_and_the_others_still_run(monkeypatch):
    def broken():
        raise RuntimeError("runner bug")

    monkeypatch.setattr(parity, "_RUNNERS", {"python": parity.run_python, "go": broken})
    outcome = parity.run_gate()
    assert outcome.reports["python"].available and outcome.reports["python"].results
    assert outcome.reports["go"].available and not outcome.reports["go"].green
    assert outcome.reports["go"].fault == "runner raised\nRuntimeError: runner bug"
    assert "  ! RuntimeError: runner bug" in outcome.lines
    assert f"  - no row reported ({INT_ROWS + MALFORMED_ROWS} rows)" in outcome.lines


def test_parity_cli_python_only_reports_clean(capsys):
    assert main(["parity", "--no-compile"]) == 0
    out = capsys.readouterr().out
    assert f"int vectors: {INT_ROWS}" in out
    assert f"malformed vectors: {MALFORMED_ROWS}" in out
    assert "governance: clean" in out


def test_full_gate_governance_clean():
    """End-to-end: every target that has a runner, through `tautc parity`. A missing
    toolchain skips with its reason (not a violation), so this holds whichever
    toolchains are present; a target that ran is green exactly when it is not
    allowlisted, and an allowlisted target's reason names every row it fails."""
    outcome = parity.run_gate(run_compiled=True)
    assert outcome.violations == [], "\n".join(outcome.violations)
    assert set(outcome.reports) == set(parity._RUNNERS)
    assert outcome.reports["python"].available
    reasons = {s.target: s.reason for s in parity.target_statuses() if s.status == "allowlisted"}
    for target, report in outcome.reports.items():
        if report.available and target in reasons:
            unnamed = [r.name for r in report.failures if r.name not in reasons[target]]
            assert unnamed == [], (target, unnamed)
            assert not report.fault, (target, report.fault)


# --- toolchain finders ------------------------------------------------------------------

def _tool(path, code=0):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"#!/bin/sh\nexit {code}\n")
    path.chmod(0o755)
    return path


@pytest.mark.skipif(os.name == "nt", reason="fake tools are shell scripts")
def test_java_tools_come_from_java_home_first(tmp_path, monkeypatch):
    home = tmp_path / "jdk"
    javac, java = _tool(home / "bin" / "javac"), _tool(home / "bin" / "java")
    monkeypatch.setenv("JAVA_HOME", str(home))
    assert toolchains.find_java_tools() == (str(javac), str(java))
    _tool(home / "bin" / "javac", code=1)                          # a broken JDK is passed over
    assert toolchains.find_java_tools() != (str(javac), str(java))


@pytest.mark.skipif(os.name == "nt", reason="fake tools are shell scripts")
def test_kotlinc_comes_from_the_kotlinc_variable_with_the_java_it_runs_with(tmp_path, monkeypatch):
    kotlinc = _tool(tmp_path / "kotlinc" / "bin" / "kotlinc")
    java = _tool(tmp_path / "jdk" / "bin" / "java")
    monkeypatch.setenv("KOTLINC", str(tmp_path / "kotlinc"))      # a directory names its bin/kotlinc
    monkeypatch.setenv("JAVA_HOME", str(tmp_path / "jdk"))
    assert toolchains.find_kotlin_tools() == (str(kotlinc), str(java))
    assert toolchains.java_env(str(java))["JAVA_HOME"] == str((tmp_path / "jdk").resolve())


@pytest.mark.skipif(os.name == "nt", reason="PATH isolation uses POSIX paths")
def test_a_missing_toolchain_is_none(tmp_path, monkeypatch):
    monkeypatch.setenv("PATH", str(tmp_path))
    monkeypatch.delenv("JAVA_HOME", raising=False)
    monkeypatch.delenv("KOTLINC", raising=False)
    monkeypatch.setattr(toolchains, "ANDROID_STUDIO_JBR", tmp_path / "no-jbr")
    monkeypatch.setattr(toolchains, "ANDROID_STUDIO_KOTLINC", tmp_path / "no-kotlinc")
    for finder in (toolchains.find_rustc, toolchains.find_node, toolchains.find_node_for_typescript,
                   toolchains.find_go, toolchains.find_swiftc, toolchains.find_cxx,
                   toolchains.find_java_tools, toolchains.find_kotlinc, toolchains.find_kotlin_tools):
        assert finder() is None, finder.__name__
