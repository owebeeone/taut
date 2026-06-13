"""Glade wire golden corpus is the contract (GLP-0005, P0.S3). Every reference
value must encode to the exact committed bytes and round-trip back. P0.S4
(Rust/TS) reproduces these bytes; this pins the Python reference."""

import json

from taut.corpus.glade_build import GOLDEN_PATH, IR_PATH, glade_values
from taut.ir.load import load_schema
from taut.wire import codec


def test_glade_golden_bytes_reproduced_and_roundtrip():
    schema = load_schema(IR_PATH)
    golden = json.loads(GOLDEN_PATH.read_text())
    values = glade_values(schema)
    assert set(golden) == set(values)              # corpus and references in lockstep
    for name, (message, value) in values.items():
        entry = golden[name]
        assert entry["message"] == message, f"message mismatch for {name}"
        encoded = codec.encode(schema, message, value).hex()
        assert encoded == entry["cbor"], f"byte mismatch for {name}"
        decoded = codec.decode(schema, message, bytes.fromhex(entry["cbor"]))
        assert decoded == value, f"round-trip mismatch for {name}"


def test_glade_covers_every_message():
    schema = load_schema(IR_PATH)
    covered = {m for (m, _v) in glade_values(schema).values()}
    assert covered == set(schema.messages), "every message must have at least one vector"


def test_glade_op_chain_and_null_key_edges():
    schema = load_schema(IR_PATH)
    values = glade_values(schema)
    # null/default key is empty bytes, empty refs, no prev (first op in a chain)
    _m, op_min = values["edge/op-min"]
    assert op_min["key"] == b"" and op_min["refs"] == [] and op_min["prev"] is None
    # a later op carries a 32-byte prev-hash (the per-origin chain, GQ-9)
    _m, op_chain = values["edge/op-chain"]
    assert isinstance(op_chain["prev"], bytes) and len(op_chain["prev"]) == 32
    assert op_chain["refs"], "chained op carries causal refs"
    # equivocation is a first-class error code
    _m, err = values["edge/error-equivocation"]
    assert err["code"] == "equivocation"
