"""The conformance kit: derive a golden corpus from any IR with auto-synthesized
coverage values, and emit a per-language parity harness. Generalizes the GripLab
corpus discipline so consumers don't hand-roll reference values + vectors."""

from taut.corpus import kit, synth
from taut.corpus.build import IR_PATH
from taut.ir.load import load_schema
from taut.wire import codec

RAZEL = load_schema(IR_PATH.parent / "razel.taut.py")
GRIPLAB = load_schema(IR_PATH)


def test_synth_is_deterministic():
    assert synth.synth_values(RAZEL) == synth.synth_values(RAZEL)


def test_synth_covers_every_message_and_encodes():
    values = synth.synth_values(RAZEL)
    assert set(values) == set(RAZEL.messages)            # one vector per message
    for name, (msg, val) in values.items():
        # synthesized values are valid: they encode and round-trip through the codec
        assert codec.decode(RAZEL, msg, codec.encode(RAZEL, msg, val)) == val


def test_synth_exercises_the_type_space():
    # BuildResult has an enum, an i64, a list-of-message, and an optional — the value
    # should populate each (coverage, not just shape).
    _, val = synth.synth_values(RAZEL)["BuildResult"]
    assert isinstance(val["recomputes"], int)
    assert val["status"] in RAZEL.enums["BuildStatus"].members
    assert isinstance(val["outputs"], list) and val["outputs"]
    assert isinstance(val["outputs"][0]["digest"], (bytes, bytearray))


def test_build_corpus_matches_canonical_codec():
    values = synth.synth_values(RAZEL)
    corpus = kit.build_corpus(RAZEL, values)
    for name, entry in corpus.items():
        msg, val = values[name]
        assert entry["message"] == msg
        assert bytes.fromhex(entry["cbor"]) == codec.encode(RAZEL, msg, val)


def test_rust_harness_is_self_contained_and_covers_messages():
    corpus = kit.build_corpus(RAZEL, synth.synth_values(RAZEL))
    rs = kit.rust_vectors(RAZEL, corpus)
    assert "pub static VECTORS" in rs
    assert "fn corpus_byte_parity" in rs
    # a reencode arm for each message, using crate-root re-exported types
    for m in RAZEL.messages:
        assert f'"{m}" => crate::{m}::from_cbor(c).to_cbor(),' in rs


def test_golden_json_is_stable():
    corpus = kit.build_corpus(GRIPLAB, synth.synth_values(GRIPLAB))
    assert kit.golden_json(corpus) == kit.golden_json(corpus)
