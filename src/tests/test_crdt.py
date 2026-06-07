"""CRDT surface: the wire (CrdtOp/CrdtState) is representable and round-trips;
the reference engine (lww + counter) converges regardless of op order; merge is
idempotent; unsupported merge types hit the empty engine slot."""

import pytest

from prism.corpus.build import IR_PATH
from prism.crdt import EngineNotBound, ReferenceDoc
from prism.crdt.engine import op_from_wire, op_to_wire
from prism.ir.dsl import INT, STR, F, Msg, schema as mk_schema
from prism.ir.load import load_schema
from prism.ir.validate import validate
from prism.wire import codec

SCHEMA = load_schema(IR_PATH)
TITLE, VOTES = 1, 2  # Board field tags (lww str, counter int)


def test_ir_with_crdt_validates():
    assert validate(SCHEMA) == []


def test_replicas_converge_regardless_of_order():
    a = ReferenceDoc("A", SCHEMA)
    b = ReferenceDoc("B", SCHEMA)
    a_title = a.local_apply(TITLE, "hello")
    a_votes = a.local_apply(VOTES, 3)
    b_title = b.local_apply(TITLE, "world")
    b_votes = b.local_apply(VOTES, 5)

    # exchange in *different* orders on each replica
    a.merge(b_votes); a.merge(b_title)
    b.merge(a_title); b.merge(a_votes)

    assert a.materialize() == b.materialize()           # converged
    assert a.materialize() == {"title": "world", "votes": 8}  # lww (1,"B")>(1,"A"); counter 3+5


def test_merge_is_idempotent():
    a = ReferenceDoc("A", SCHEMA)
    b = ReferenceDoc("B", SCHEMA)
    op = b.local_apply(VOTES, 5)
    assert a.merge(op) is True
    assert a.merge(op) is False                          # already applied
    assert a.materialize()["votes"] == 5                 # not double-counted


def test_op_round_trips_on_the_wire():
    op = {"doc": "board:1", "actor": "A", "seq": 1, "field": VOTES, "value": 3}
    wire = op_to_wire(SCHEMA, op)                         # value -> CBOR bytes
    # CrdtOp is a normal IR message: encodes/decodes byte-exact
    assert codec.decode(SCHEMA, "CrdtOp", codec.encode(SCHEMA, "CrdtOp", wire)) == wire
    # and the native value is recovered
    assert op_from_wire(SCHEMA, wire) == op

    lww = {"doc": "board:1", "actor": "B", "seq": 1, "field": TITLE, "value": "world"}
    assert op_from_wire(SCHEMA, op_to_wire(SCHEMA, lww)) == lww


def test_snapshot_is_the_reconstructible_op_log():
    a = ReferenceDoc("A", SCHEMA)
    a.local_apply(TITLE, "hi")
    a.local_apply(VOTES, 2)
    snap = a.snapshot()
    # a fresh replica rebuilds identical state from the snapshot's ops
    fresh = ReferenceDoc("C", SCHEMA)
    for op in snap["ops"]:
        fresh.merge(op)
    assert fresh.materialize() == a.materialize()


def test_unsupported_merge_hits_the_empty_engine_slot():
    # text/sequence needs a real engine (Automerge/Yjs); the slot is unbound.
    text_doc = mk_schema(Msg("Doc", F("body", 1, STR, merge="text")))
    with pytest.raises(EngineNotBound):
        ReferenceDoc("A", text_doc, doc="Doc")


def test_validator_rejects_bad_merge():
    counter_on_str = validate(mk_schema(Msg("M", F("x", 1, STR, merge="counter"))))
    assert any("counter merge requires an int" in e for e in counter_on_str)
    assert validate(mk_schema(Msg("M", F("x", 1, INT, merge="lww")))) == []  # int lww is fine
