"""The golden conformance corpus is the contract. Every reference value must
encode to the exact committed bytes and round-trip back. This is what lets us
trust the IR-driven codec without line-by-line review — and what P3 (TypeScript)
will reproduce byte-for-byte."""

import json

from taut.corpus.build import GOLDEN_PATH, IR_PATH, reference_values
from taut.ir.load import load_schema
from taut.wire import codec


def test_golden_bytes_reproduced_and_roundtrip():
    schema = load_schema(IR_PATH)
    golden = json.loads(GOLDEN_PATH.read_text())
    refs = reference_values()
    assert set(golden) == set(refs)            # corpus and references in lockstep
    for name, (message, value) in refs.items():
        entry = golden[name]
        assert entry["message"] == message
        encoded = codec.encode(schema, message, value).hex()
        assert encoded == entry["cbor"], f"byte mismatch for {name}"
        decoded = codec.decode(schema, message, bytes.fromhex(entry["cbor"]))
        assert decoded == value, f"round-trip mismatch for {name}"


def test_transient_field_never_on_the_wire():
    schema = load_schema(IR_PATH)
    snapshot = reference_values()["swmr/snapshot"][1]
    decoded = codec.decode(schema, "FileSnapshot", codec.encode(schema, "FileSnapshot", snapshot))
    assert "preview" not in decoded          # transient: native-only
    assert decoded == snapshot


def test_swmr_resume_offset_chain_is_contiguous():
    refs = reference_values()
    snap = refs["swmr/snapshot"][1]
    d1 = refs["swmr/delta-1"][1]
    d2 = refs["swmr/delta-2"][1]
    assert d1["base_seq"] == snap["resume_seq"]   # first delta resumes at the snapshot offset
    assert d2["base_seq"] == d1["seq"]            # contiguous: no gap, no double-apply
