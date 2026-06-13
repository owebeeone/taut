"""Glade fold conformance (GLP-0005, P0.S5). The reference folds are the
cross-language oracle: the Rust node (P1) and TS client (P2) must reproduce
these results. Every vector's expected output is hand-reviewed here."""

import json

from taut.crdt.glade_fold import (
    FOLDS_PATH,
    Equivocation,
    fold_log,
    fold_value,
    is_equivocation,
    run,
    vectors,
)
import pytest


def test_every_vector_matches_reference():
    for case in vectors():
        assert run(case) == case["expect"], f"fold mismatch for {case['name']}"


def test_lww_tiebreak_is_lamport_then_origin():
    a = {"origin": "a", "seq": 2, "lamport": 5, "prev": None, "payload": b"A"}
    b = {"origin": "b", "seq": 1, "lamport": 5, "prev": None, "payload": b"B"}
    # equal lamport -> higher origin id wins, regardless of arrival order
    assert fold_value([a, b]) == b"B"
    assert fold_value([b, a]) == b"B"


def test_fold_is_order_independent_and_idempotent():
    a = {"origin": "a", "seq": 1, "lamport": 1, "prev": None, "payload": b"A"}
    b = {"origin": "b", "seq": 1, "lamport": 2, "prev": None, "payload": b"B"}
    assert fold_value([a, b]) == fold_value([b, a, a, b])           # value: order/dup independent
    assert fold_log([a, b]) == fold_log([b, a, b]) == [b"A", b"B"]  # log: order/dup independent


def test_equivocation_detected_and_blocks_fold():
    a = {"origin": "a", "seq": 1, "lamport": 1, "prev": None, "payload": b"A"}
    fork = {"origin": "a", "seq": 1, "lamport": 1, "prev": None, "payload": b"A-fork"}
    assert is_equivocation([a, fork]) is True
    with pytest.raises(Equivocation):
        fold_value([a, fork])
    with pytest.raises(Equivocation):
        fold_log([a, fork])


def test_committed_oracle_in_lockstep_with_reference():
    """corpus/glade_folds.json must match the reference (regen gate)."""
    committed = json.loads(FOLDS_PATH.read_text())
    names = [c["name"] for c in vectors()]
    assert [e["name"] for e in committed] == names, "fold oracle out of date — rerun glade_fold"
