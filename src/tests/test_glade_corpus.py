"""Glade wire golden corpus is the contract (GLP-0005, P0.S3). Every reference
value must encode to the exact committed bytes and round-trip back. P0.S4
(Rust/TS) reproduces these bytes; this pins the Python reference."""

import json

from taut.corpus.glade_build import GOLDEN_PATH, IR_PATH, glade_values
from taut.ir.load import load_schema
from taut.ir.options import effective
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


def test_glade_shape_enum_appends_swmr_and_crdt_without_renumbering_existing_shapes():
    schema = load_schema(IR_PATH)
    assert schema.enums["Shape"].members == {
        "value": 0,
        "log": 1,
        "stream": 2,
        "swmr": 3,
        "crdt": 4,
    }
    _message, op = glade_values(schema)["edge/op-swmr"]
    assert op["shape"] == "swmr"


def test_glade_declares_a_bound_that_keeps_the_frame_cap_at_16_mib():
    """A glade frame is its FrameType tag byte, then one frame message, and a carrier refuses a
    frame over 16 MiB, its tag byte included (glade's frame limit). glade's schema declares the
    message's share of that at file level, 16 MiB less the tag byte, so every message resolves
    to it, at the default depth, and glade-wire's frame limit, one byte more, stays 16 MiB
    (TautCheckedDecode.md CD-B4, CD-G3)."""
    schema = load_schema(IR_PATH)
    message_bound = 16 * 1024 * 1024 - 1
    assert schema.options == {"max_encoded_len": message_bound}
    assert effective(schema, "max_encoded_len") == message_bound
    for message in schema.messages:
        assert effective(schema, "max_encoded_len", message=message) == message_bound, message
        assert effective(schema, "max_depth", message=message) == 32, message
