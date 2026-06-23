"""float scalar — IR surface, validation, and the IR-driven codec/JSON profile.

The wire-substrate float vectors live in test_cbor.py; this covers float threaded
*through a schema*: coercion at the field boundary (rule E), map-key rejection,
list/map-value support, and the JSON profile (number + non-finite sentinels)."""

import math
import struct

from taut.ir.dsl import FLOAT, INT, F, List, Map, Msg, schema as mk
from taut.ir.export import schema_json
from taut.ir.load import schema_from_json
from taut.ir.model import Scalar
from taut.ir.validate import validate
from taut.wire import codec, jsoncodec

S = mk(Msg("M",
           F("x", 1, FLOAT),
           F("xs", 2, List(FLOAT)),
           F("by_id", 3, Map(INT, FLOAT))))   # float as map *value* is allowed


def test_float_is_a_scalar():
    assert FLOAT == Scalar("float")


def test_float_schema_validates():
    assert validate(S) == []


def test_float_map_key_rejected():
    errs = validate(mk(Msg("Bad", F("k", 1, Map(FLOAT, INT)))))
    assert any("map key must be" in e for e in errs)


def test_float_wire_roundtrip():
    val = {"x": 1.5, "xs": [0.0, -0.0, 100000.0], "by_id": {1: 0.1, 2: float("inf")}}
    out = codec.decode(S, "M", codec.encode(S, "M", val))
    assert out["x"] == 1.5
    assert out["xs"][0] == 0.0 and out["xs"][2] == 100000.0
    assert out["by_id"][1] == 0.1 and math.isinf(out["by_id"][2])
    # -0.0 preserved bit-exactly through the wire
    assert struct.pack(">d", out["xs"][1]) == struct.pack(">d", -0.0)


def test_int_coerces_to_float_at_field_boundary():
    # rule E: an int placed in a float field encodes as float(+0.0), not int 0.
    dec = codec.decode(S, "M", codec.encode(S, "M", {"x": 0, "xs": [], "by_id": {}}))
    assert isinstance(dec["x"], float)
    assert struct.pack(">d", dec["x"]) == struct.pack(">d", 0.0)


def test_float_json_profile():
    val = {"x": 1.5, "xs": [0.25], "by_id": {1: 2.0}}
    text = jsoncodec.cbor_to_json(S, "M", codec.encode(S, "M", val))
    assert '"x":1.5' in text                  # float -> JSON number (not a string)
    assert codec.decode(S, "M", jsoncodec.json_to_cbor(S, "M", text)) == val


def test_float_json_nonfinite_sentinels():
    val = {"x": float("inf"), "xs": [float("-inf")], "by_id": {1: float("nan")}}
    text = jsoncodec.cbor_to_json(S, "M", codec.encode(S, "M", val))
    assert '"Infinity"' in text and '"-Infinity"' in text and '"NaN"' in text
    back = codec.decode(S, "M", jsoncodec.json_to_cbor(S, "M", text))
    assert math.isinf(back["x"]) and back["x"] > 0
    assert math.isinf(back["xs"][0]) and back["xs"][0] < 0
    assert math.isnan(back["by_id"][1])


def test_float_export_reload():
    assert validate(schema_from_json(schema_json(S))) == []


def test_scaffold_stub_native_types_cover_float():
    # the per-language stub-signature maps must know float, so Phase-2 agents
    # never have to touch scaffold.py (only their own gen/<lang>.py + runtime).
    from taut.gen import scaffold as sc
    got = (sc._py_ty(FLOAT), sc._ts_ty(FLOAT), sc._rs_ty(FLOAT), sc._cpp_ty(FLOAT),
           sc._swift_ty(FLOAT), sc._go_ty(FLOAT), sc._kt_ty(FLOAT), sc._java_ty(FLOAT))
    assert got == ("float", "number", "f64", "double", "Double", "float64", "Double", "double")


def test_bool_coerces_to_float_at_field_boundary():
    # bool is int-like, so float(True) == 1.0 rides the same rule-E coercion as int.
    # (Static targets enforce types at compile time; the dynamic interpreter coerces.)
    dec = codec.decode(S, "M", codec.encode(S, "M", {"x": True, "xs": [False], "by_id": {}}))
    assert dec["x"] == 1.0 and dec["xs"][0] == 0.0


def test_float_merge_policy():
    # lww on a float field is fine; counter requires an int field (float rejected).
    assert validate(mk(Msg("Lww", F("v", 1, FLOAT, merge="lww")))) == []
    errs = validate(mk(Msg("Ctr", F("v", 1, FLOAT, merge="counter"))))
    assert any("counter merge requires an int" in e for e in errs)
