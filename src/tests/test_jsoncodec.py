"""The IR-driven CBOR<->JSON bridge: point at the IR + a message, convert both
ways losslessly. Conventions follow proto3 JSON (int64->string, bytes->base64,
enum->name); CBOR -> JSON -> CBOR is byte-identical for residual-free values."""

import base64

from taut.corpus.build import IR_PATH
from taut.ir.load import load_schema
from taut.ir.dsl import F, STR, Msg, schema
from taut.wire import codec, jsoncodec


def test_missing_ok_python_decode_is_per_field_and_rejects_malformed_values():
    s = schema(Msg("M", F("old", 1, STR, optional=True),
                   F("new", 2, STR, optional=True, missing_ok=True)))
    assert codec.decode_struct(s, "M", {1: None, 2: None}, strict=True) == {
        "old": None, "new": None
    }
    assert codec.decode_struct(s, "M", {1: None}, strict=True) == {
        "old": None, "new": None
    }
    try:
        codec.decode_struct(s, "M", {2: "ok"}, strict=True)
    except codec.DecodeError as exc:
        assert exc.tag == "MissingKey" and exc.key == 1
    else:
        raise AssertionError("strict legacy optional slot must remain required")
    try:
        codec.decode_struct(s, "M", {1: None, 2: 3}, strict=True)
    except codec.DecodeError as exc:
        assert exc.tag == "WrongType"
    else:
        raise AssertionError("present malformed missing_ok value must fail")


def test_python_empty_message_requires_map():
    s = schema(Msg("Empty"))
    assert codec.decode_struct(s, "Empty", {}, strict=True) == {}
    try:
        codec.decode_struct(s, "Empty", True, strict=True)
    except codec.DecodeError as exc:
        assert exc.tag == "WrongType"
    else:
        raise AssertionError("strict empty message must reject non-map input")

# razel's BuildResult exercises every wrinkle: enum, i64, list-of-message,
# nested bytes, and an optional (present + absent).
RAZEL = load_schema(IR_PATH.parent / "razel.taut.py")

FULL = {
    "target": "//pkg:lib",
    "status": "built",
    "recomputes": 7,
    "outputs": [{"path": "out/lib.rlib", "digest": b"\xde\xad\xbe\xef"}],
    "message": "ok",
}
BARE = {"target": "//y", "status": "failed", "recomputes": 0, "outputs": [], "message": None}


def test_json_conventions():
    jv = jsoncodec.to_json_value(RAZEL, "BuildResult", FULL)
    assert jv["recomputes"] == "7"                                   # i64 -> string
    assert jv["status"] == "built"                                   # enum -> name
    assert jv["outputs"][0]["digest"] == base64.b64encode(b"\xde\xad\xbe\xef").decode()  # bytes -> base64
    assert jsoncodec.to_json_value(RAZEL, "BuildResult", BARE)["message"] is None        # optional absent -> null


def test_native_json_native_roundtrip():
    for val in (FULL, BARE):
        text = jsoncodec.to_json(RAZEL, "BuildResult", val)
        assert jsoncodec.from_json(RAZEL, "BuildResult", text) == val


def test_cbor_json_cbor_is_byte_identical():
    for val in (FULL, BARE):
        data = codec.encode(RAZEL, "BuildResult", val)
        text = jsoncodec.cbor_to_json(RAZEL, "BuildResult", data)
        assert jsoncodec.json_to_cbor(RAZEL, "BuildResult", text) == data


def test_json_is_canonical():
    # sorted keys + compact separators => reproducible text, independent of input order
    a = jsoncodec.to_json(RAZEL, "BuildResult", FULL)
    shuffled = {"message": "ok", "outputs": FULL["outputs"], "recomputes": 7,
                "status": "built", "target": "//pkg:lib"}
    b = jsoncodec.to_json(RAZEL, "BuildResult", shuffled)
    assert a == b
    assert " " not in a  # compact (no spaces) by default


def test_golden_corpus_roundtrips_through_json():
    # the strongest check: every real golden vector survives cbor -> json -> cbor
    # byte-for-byte (the JSON profile is lossless for residual-free wire bytes).
    import json as _json

    g = load_schema(IR_PATH)
    golden = _json.loads((IR_PATH.parent.parent / "corpus" / "griplab.golden.json").read_text())
    assert golden, "empty golden corpus"
    for name, entry in golden.items():
        data = bytes.fromhex(entry["cbor"])
        msg = entry["message"]
        text = jsoncodec.cbor_to_json(g, msg, data)
        assert jsoncodec.json_to_cbor(g, msg, text) == data, f"{name} ({msg})"
