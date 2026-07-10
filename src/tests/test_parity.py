"""The governed Wave-1 parity gate (Phase 0 of TautCodecParityPlan.md).

The Python harness replays corpus/parity/{int,malformed}.vectors.json through
wire.codec/wire.cbor directly (no subprocess). These tests assert the gate's
*governance* holds now that strict-canonical D2 has landed in every Wave-1 codec:

  - every Wave-1 target passes in full (incl. the D2 rows NonCanonicalInt /
    NegativeMapKey) and is GATED (de-listed) — a Wave-1 red would fail CI.
  - the leading frontier is now Wave-2 (cpp/swift/go/kotlin/java): allowlisted
    (xfail-that-runs) until each real replay harness lands in Phase 4.
  - a fully-green target that is still allowlisted is a violation (must de-list).
  - a gated (non-allowlisted) target that fails is a violation.

`test_full_gate_governance_clean` drives every Wave-1 harness (rust/ts/js via
subprocess, skipped if the toolchain is absent) end-to-end via `tautc parity`.
"""

import json

import pytest

from taut.cli import main
from taut.corpus import parity


def test_int_and_malformed_artifacts_validate():
    assert parity.validate_int_vectors() == 11
    assert parity.validate_malformed_vectors() == 16


def test_allowlist_gates_wave1_and_covers_every_wave2_target():
    statuses = {s.target: s for s in parity.target_statuses()}
    # D2-strict has landed: every Wave-1 target passes in full, so each is GATED
    # (de-listed). A Wave-1 entry reappearing in the allowlist would be drift.
    for target in parity.WAVE1:
        assert statuses[target].status == "gated", target
    # The leading frontier is Wave-2, honestly allowlisted with a reason until its
    # real replay harness lands (Phase 4).
    for target in (t for t in parity.TARGETS if t not in parity.WAVE1):
        assert statuses[target].status == "allowlisted", target
        assert statuses[target].reason


def test_python_harness_passes_including_the_d2_strict_rows():
    report = parity.run_python()
    assert report.available
    # every vector passes now — including the leading D2-strict rows
    # (NonCanonicalInt / NegativeMapKey) this gate led with.
    for r in report.results:
        assert r.status in (parity.PASS, parity.TYPE_SATISFIED), (r.name, r.detail)
    assert report.failed_tags == []
    assert report.green


def test_python_target_governance_is_clean():
    # python is green (D2-strict landed) AND gated (de-listed) -> no violation.
    report = parity.run_python()
    assert parity.governance({"python": report}, parity.allowlisted_targets()) == []


def test_governance_flags_a_green_but_allowlisted_target():
    # Inverse check that makes the gate LEAD: the day a target passes fully it
    # must be de-listed, or CI fails.
    green = parity.TargetReport("python", available=True, results=[
        parity.VectorResult("ok", "malformed", "Truncated", parity.PASS, "", False),
    ])
    assert parity.governance({"python": green}, {"python"})      # green + listed -> violation
    assert parity.governance({"python": green}, set()) == []     # green + gated -> fine


def test_governance_flags_a_gated_target_that_fails():
    # A gated (non-allowlisted) target that reports a failure is a violation.
    # (Synthetic red: the real Python harness is fully green post-D2.)
    red = parity.TargetReport("python", available=True, results=[
        parity.VectorResult("boom", "malformed", "NonCanonicalInt", parity.FAIL, "decoded ok", True),
    ])
    assert parity.governance({"python": red}, set())             # red + gated -> violation


def test_skipped_target_is_not_a_violation():
    skipped = parity.TargetReport("rust", available=False, skip_reason="rustc absent")
    assert parity.governance({"rust": skipped}, set()) == []
    assert parity.governance({"rust": skipped}, {"rust"}) == []


def test_parity_cli_python_only_reports_clean(capsys):
    assert main(["parity", "--no-compile"]) == 0
    out = capsys.readouterr().out
    assert "int vectors: 11" in out
    assert "malformed vectors: 16" in out
    assert "governance: clean" in out


def test_committed_vectors_match_generator():
    """The committed .json is exactly `gen_vectors.py` output — reviewable AND
    regenerable, and no hand-edit has drifted from the generator."""
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "parity_gen_vectors", parity.PARITY_DIR / "gen_vectors.py")
    gen = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gen)
    assert gen.render(gen.INT_VECTORS) == parity.INT_VECTORS.read_text()
    assert gen.render(gen.MALFORMED_VECTORS) == parity.MALFORMED_VECTORS.read_text()


def test_target_statuses_rejects_duplicate_allowlist_entry(tmp_path):
    data = json.loads(parity.ALLOWLIST.read_text())
    data["targets"].append(dict(data["targets"][0]))  # a second entry for the same target
    path = tmp_path / "allowlist.json"
    path.write_text(json.dumps(data))
    with pytest.raises(parity.ParityValidationError, match="duplicate target"):
        parity.target_statuses(path)


def test_full_gate_governance_clean():
    """End-to-end: run every available Wave-1 harness through `tautc parity`.
    Unavailable toolchains are skipped-with-reason (not a violation), so this is
    green whether or not rustc/node are present."""
    outcome = parity.run_gate(run_compiled=True)
    ran = [t for t, r in outcome.reports.items() if r.available]
    assert "python" in ran
    assert outcome.violations == [], "\n".join(outcome.violations)
    # D2-strict has landed: every available Wave-1 target is now fully green
    # (this gate led with these rows red; they pass now).
    for target in ran:
        assert outcome.reports[target].green, outcome.reports[target].failed_tags
    assert outcome.reports["python"].failed_tags == []
