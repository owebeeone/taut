"""Names some generator cannot take (TautV010Plan.md, step E1a).

`validate` refuses a field, message or enum name that a target's generated code or vendored
runtime already uses where that name is declared, and names each target it breaks, so a schema
that validates generates and compiles in all nine targets. Each generator keeps its reservations
beside it (`RESERVED_FIELD_NAMES`, `RESERVED_TYPE_NAMES`, and `name_clashes` for what no fixed set
holds). They were found by generating and compiling schemas that use each name in every target;
these tests pin that validate refuses each and accepts the names beside them.
"""

import re
from pathlib import Path

import pytest

from taut.gen import cpp, go, java, js, kotlin, rust, scaffold, swift
from taut.ir.dsl import INT, Enum, F, List, Map, Msg, Ref, schema
from taut.ir.load import load_schema
from taut.ir.validate import validate

ROOT = Path(__file__).resolve().parents[2]
RESERVATIONS = {
    "rust": (rust.RESERVED_FIELD_NAMES, rust.RESERVED_TYPE_NAMES),
    "cpp": (cpp.RESERVED_FIELD_NAMES, cpp.RESERVED_TYPE_NAMES),
    "swift": (swift.RESERVED_FIELD_NAMES, swift.RESERVED_TYPE_NAMES),
    "go": (go.RESERVED_FIELD_NAMES, go.RESERVED_TYPE_NAMES),
    "kotlin": (kotlin.RESERVED_FIELD_NAMES, kotlin.RESERVED_TYPE_NAMES),
    "java": (java.RESERVED_FIELD_NAMES, java.RESERVED_TYPE_NAMES),
    "js": (js.RESERVED_FIELD_NAMES, js.RESERVED_TYPE_NAMES),
    "python": (scaffold.PYTHON_RESERVED_FIELD_NAMES, scaffold.PYTHON_RESERVED_TYPE_NAMES),
}
FIELDS = [(target, name) for target, (fields, _) in RESERVATIONS.items() for name in fields]
TYPES = [(target, name) for target, (_, types) in RESERVATIONS.items() for name in types]


def refused_by(errors: list[str], where: str, kind: str) -> set[str]:
    """The targets named by the one error refusing `where`'s name: 'the cpp and go generators
    (a runtime type); the swift generator (...)'."""
    found = [e for e in errors if e.startswith(f"{where}: {kind} name reserved by the ")]
    assert len(found) == 1, errors
    groups = re.findall(r"the ((?:\w+, )*\w+(?: and \w+)?) generators? \(", found[0])
    return {target for group in groups for target in re.split(r", | and ", group)}


def field_named(name: str):
    return schema(Msg("Probe", F(name, 1, INT)))


@pytest.mark.parametrize(("target", "name"), FIELDS)
def test_each_reserved_field_name_is_refused_naming_its_target(target, name):
    # Go's names are its own spelling, which a name without `_` keeps (`go.field_name`).
    assert target in refused_by(validate(field_named(name)), f"Probe.{name}", "field")


@pytest.mark.parametrize(("target", "name"), TYPES)
def test_each_reserved_type_name_is_refused_for_a_message_and_an_enum_naming_its_target(target, name):
    assert target in refused_by(validate(schema(Msg(name, F("n", 1, INT)))), name, "message")
    assert target in refused_by(validate(schema(Enum(name, a=0))), f"enum {name}", "enum")


def test_an_error_names_the_name_the_target_and_why():
    assert validate(field_named("try_from_cbor")) == [
        "Probe.try_from_cbor: field name reserved by the cpp generator (a member function)"]


@pytest.mark.parametrize(("where", "kind", "s", "targets"), [
    # the clashes the language agents reported, and the targets each breaks, all confirmed
    ("Probe.to_cbor", "field", field_named("to_cbor"), {"cpp", "go"}),
    ("Probe.try_from_cbor", "field", field_named("try_from_cbor"), {"cpp"}),
    ("Probe.try_decode", "field", field_named("try_decode"), {"cpp"}),
    ("Probe.max_depth", "field", field_named("max_depth"), {"cpp"}),
    ("Probe.max_encoded_len", "field", field_named("max_encoded_len"), {"cpp"}),
    ("Probe.Cbor", "field", field_named("Cbor"), {"kotlin", "swift"}),
    ("Probe.toCbor", "field", field_named("toCbor"), {"go", "js", "swift"}),
    ("Probe.MAX_DEPTH", "field", field_named("MAX_DEPTH"), {"java"}),
    ("Probe.MAX_ENCODED_LEN", "field", field_named("MAX_ENCODED_LEN"), {"java"}),
    ("Probe.wireResidual", "field", field_named("wireResidual"), {"go", "java", "js", "kotlin"}),
    ("Default", "message", schema(Msg("Default", F("n", 1, INT))), {"go", "rust"}),
    ("enum Default", "enum", schema(Enum("Default", a=0)), {"rust"}),
    ("taut", "message", schema(Msg("taut", F("n", 1, INT))), {"kotlin"}),
    ("Cbor", "message", schema(Msg("Cbor", F("n", 1, INT))),
     {"cpp", "go", "java", "kotlin", "rust", "swift"}),
    ("DecodeError", "message", schema(Msg("DecodeError", F("n", 1, INT))),
     {"cpp", "go", "kotlin", "rust"}),
    ("KV", "message", schema(Msg("KV", F("n", 1, INT))), {"go", "java"}),
    ("CborError", "message", schema(Msg("CborError", F("n", 1, INT))), {"swift"}),
    ("DecodeResult", "message", schema(Msg("DecodeResult", F("n", 1, INT))), {"cpp"}),
])
def test_the_reported_clashes_are_refused_for_exactly_the_targets_they_break(where, kind, s, targets):
    assert refused_by(validate(s), where, kind) == targets


def test_swift_refuses_a_field_named_like_a_declared_message_or_enum():
    s = schema(Enum("Mode", ok=0), Msg("Hold", F("n", 1, INT)), Msg("Spare", F("n", 1, INT)),
               Msg("Probe", F("Probe", 1, INT), F("Hold", 2, Ref("Hold")), F("Mode", 3, Ref("Mode")),
                   F("Spare", 4, INT)))
    errors = validate(s)
    for field in ("Probe", "Hold", "Mode", "Spare"):
        assert refused_by(errors, f"Probe.{field}", "field") == {"swift"}
    assert len(errors) == 4, errors


def test_swift_refuses_an_enum_named_like_one_of_its_members():
    assert refused_by(validate(schema(Enum("Level", Level=0, low=1))), "enum Level", "enum") == {"swift"}


def test_go_refuses_two_fields_with_one_go_name():
    errors = validate(schema(Msg("Probe", F("foo_bar", 1, INT), F("fooBar", 2, INT),
                                 F("_x", 3, INT), F("x", 4, INT))))
    assert refused_by(errors, "Probe.fooBar", "field") == {"go"}
    assert refused_by(errors, "Probe.x", "field") == {"go"}
    assert len(errors) == 2, errors


@pytest.mark.parametrize("name", ["to_cbor", "toCbor", "ToCbor", "To_Cbor", "_to_cbor_"])
def test_go_reads_a_field_by_the_pascal_cased_name_its_struct_declares(name):
    assert "go" in refused_by(validate(field_named(name)), f"Probe.{name}", "field")


@pytest.mark.parametrize("name", ["arr", "x", "arr3", "x12", "e7"])
def test_go_refuses_a_type_named_like_a_list_decoders_numbered_local(name):
    assert refused_by(validate(schema(Msg(name, F("n", 1, INT)))), name, "message") == {"go"}


@pytest.mark.parametrize(("where", "kind", "s"), [
    ("HoldMaxDepth", "message",   # Hold's HoldMaxDepth constant
     schema(Msg("Hold", F("n", 1, INT)), Msg("HoldMaxDepth", F("n", 1, INT)))),
    ("TryHoldFromCbor", "message",
     schema(Msg("Hold", F("n", 1, INT)), Msg("TryHoldFromCbor", F("n", 1, INT)))),
    ("ModeOk", "message", schema(Enum("Mode", ok=0), Msg("ModeOk", F("n", 1, INT)))),
    ("enum K", "enum", schema(Enum("K", int=0))),   # KInt, the runtime's
])
def test_go_refuses_a_declaration_whose_generated_names_meet_another(where, kind, s):
    assert refused_by(validate(s), where, kind) == {"go"}


@pytest.mark.parametrize(("where", "kind", "s", "targets"), [
    ("ModeValues", "message", schema(Enum("Mode", ok=0), Msg("ModeValues", F("n", 1, INT))), {"js"}),
    ("ModeFromCbor", "message", schema(Enum("Mode", ok=0), Msg("ModeFromCbor", F("n", 1, INT))),
     {"js"}),
    ("enum map", "enum", schema(Enum("map", ok=0)), {"js"}),   # mapFromCbor, cbor.js's
    ("try_Mode_from_wire", "message",
     schema(Enum("Mode", ok=0), Msg("try_Mode_from_wire", F("n", 1, INT))), {"cpp"}),
])
def test_js_and_cpp_refuse_a_name_an_enums_generated_names_meet(where, kind, s, targets):
    assert refused_by(validate(s), where, kind) == targets


@pytest.mark.parametrize("name", ["__init__", "__doc__", "__slots__", "__module__"])
def test_python_refuses_a_dunder_field_name(name):
    assert refused_by(validate(field_named(name)), f"Probe.{name}", "field") == {"python"}


def test_names_beside_the_reserved_ones_are_accepted():
    """Names compare exactly, as each language compares them: `MAX_DEPTH` is Java's but
    `MaxDepth` is no one's, `taut` is Kotlin's but `Taut` is not, and Go reads `to_cbor` and
    `toCbor` as its `ToCbor` but not `tocbor`. `Error` is no one's: Swift's runtime spells
    `Swift.Error` (test_swift.py), and glade's schema declares a message `Error`."""
    s = schema(
        Enum("Taut", ok=0), Enum("Kv", ok=0), Msg("Error", F("n", 1, INT)),
        Msg("Defaults", F("n", 1, INT)), Msg("TAUT", F("n", 1, INT)), Msg("CBOR", F("n", 1, INT)),
        Msg("MapKey", F("n", 1, INT)), Msg("DecodeErrors", F("n", 1, INT)),
        Msg("Probe", F("to_cbor_x", 1, INT), F("MaxDepth", 2, INT), F("MAXDEPTH", 3, INT),
            F("maxdepth", 4, INT), F("cbor", 5, INT), F("tocbor", 6, INT), F("TOCBOR", 7, INT),
            F("wireresidual", 8, INT), F("__x", 9, INT), F("taut", 10, Ref("Taut")),
            F("kv", 11, List(Ref("Kv"))), F("hold", 12, Map(INT, Ref("Defaults")))),
    )
    assert validate(s) == []


def test_the_names_fixture_still_validates():
    """Its fields are named like the generators' locals (TautV010Plan.md §0). That every committed
    IR file validates is test_validate.py's."""
    s = load_schema(ROOT / "ir" / "parity_int.taut.py")
    assert validate(s) == []
    names = {f.name for f in s.messages["Names"].fields}
    assert {"m", "c", "it", "java", "encode_value", "decodeDictionary"} <= names
