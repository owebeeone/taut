"""map<K,V> — keyed collections. Wire is a key-sorted array of {1: key, 2: value}
(deterministic, unlike proto's unordered maps). K is a scalar (int/str/bool); V is
any scalar/enum/message."""

from taut.ir.dsl import BOOL, INT, STR, Enum, F, List, Map, Msg, Ref, schema as mk
from taut.ir.export import schema_json
from taut.ir.load import schema_from_json
from taut.ir.validate import validate
from taut.wire import codec, jsoncodec

S = mk(
    Enum("Color", red=0, green=1),
    Msg("Item", F("sku", 1, STR), F("qty", 2, INT)),
    Msg("Cfg",
        F("labels", 1, Map(STR, STR)),
        F("counts", 2, Map(STR, INT)),
        F("flags", 3, Map(INT, BOOL)),
        F("palette", 4, Map(STR, Ref("Color"))),
        F("items", 5, Map(INT, Ref("Item")))),
)

VAL = {
    "labels": {"b": "two", "a": "one"},
    "counts": {"y": -3, "x": 5},
    "flags": {3: True, 1: False},
    "palette": {"p": "green", "q": "red"},
    "items": {2: {"sku": "B", "qty": 9}, 1: {"sku": "A", "qty": 4}},
}


def test_validates():
    assert validate(S) == []


def test_bad_map_types_rejected():
    assert any("map key must be" in e for e in validate(mk(Msg("M", F("x", 1, Map(Ref("M"), STR))))))
    assert any("cannot be a list or map" in e for e in validate(mk(Msg("M", F("x", 1, Map(STR, List(STR)))))))
    assert any("cannot be a list or map" in e for e in validate(mk(Msg("M", F("x", 1, Map(STR, Map(STR, STR)))))))


def test_wire_roundtrip():
    assert codec.decode(S, "Cfg", codec.encode(S, "Cfg", VAL)) == VAL


def test_wire_is_deterministic_regardless_of_insertion_order():
    shuffled = {
        "labels": {"a": "one", "b": "two"},
        "counts": {"x": 5, "y": -3},
        "flags": {1: False, 3: True},
        "palette": {"q": "red", "p": "green"},
        "items": {1: {"sku": "A", "qty": 4}, 2: {"sku": "B", "qty": 9}},
    }
    assert codec.encode(S, "Cfg", shuffled) == codec.encode(S, "Cfg", VAL)  # keys sorted on the wire


def test_json_profile_map_is_object():
    text = jsoncodec.cbor_to_json(S, "Cfg", codec.encode(S, "Cfg", VAL))
    assert '"counts":{"x":"5","y":"-3"}' in text   # int64 values -> strings; keys sorted
    assert '"flags":{"1":false,"3":true}' in text  # int keys -> string keys
    assert '"palette":{"p":"green","q":"red"}' in text  # enum -> member name
    # round-trips back to the same native value
    assert codec.decode(S, "Cfg", jsoncodec.json_to_cbor(S, "Cfg", text)) == VAL


def test_export_reload():
    assert validate(schema_from_json(schema_json(S))) == []


def test_compat_gate_sees_map_value_type_change():
    from taut.ir import compat
    base = mk(Msg("M", F("m", 1, Map(STR, INT))))
    changed = mk(Msg("M", F("m", 1, Map(STR, STR))))   # value int -> str
    assert compat.breaking(base, changed)
