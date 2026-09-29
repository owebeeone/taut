"""validate's option checks (TautOptions.md OPT-L4) and the lint channel (OPT-D4, OPT-D5).

Per declaration, at every level: a registered name, a level among the definition's, and a value
that passes `check_value`, since a model loaded from JSON or built by hand never ran a constructor.
Per root (every message, and every type a method binds as a param or out slot): `max_depth` at
least the root's non-recursive nesting, no root nesting past the ceiling, and a declared
`max_encoded_len` at least the root's smallest canonical encoding. The floors are options.py's.
"""

import dataclasses
from pathlib import Path

import pytest

from taut.cli import main
from taut.ir.dsl import (
    BOOL,
    BYTES,
    FLOAT,
    INT,
    MISSING_OK,
    STR,
    Enum,
    F,
    List,
    Map,
    Msg,
    Ref,
    extension,
    method,
    option,
    schema,
    service,
)
from taut.ir.load import load_schema
from taut.ir.model import EnumRef, ListOf, MapOf, MsgRef, Scalar
from taut.ir.options import nesting, root_effective, roots, smallest_encoding
from taut.ir.shapes import BAND_START
from taut.ir.validate import lint, validate
from taut.wire import cbor, codec

ROOT = Path(__file__).resolve().parents[2]


def _lists(n, elem=INT):
    """`elem` inside n nested lists."""
    for _ in range(n):
        elem = ListOf(elem)
    return elem


# --- the depth floor: non-recursive nesting (OPT-D5) ------------------------------------------

NESTED = schema(
    Enum("Mode", ok=0, alt=1),
    Msg("Leaf", F("x", 1, INT), F("m", 2, Ref("Mode"))),
    Msg("Keyed", F("by", 1, Map(STR, Ref("Leaf")))),
    Msg("Grid", F("g", 1, List(List(INT)))),
    Msg("Skip", F("t", 1, List(List(INT)), transient=True), F("x", 2, INT)),
    Msg("Tree", F("kids", 1, List(Ref("Tree")))),
    Msg("Flat2", F("v", 1, List(INT))),
    Msg("Holds", F("t", 1, Ref("Tree"))),
    Msg("Ping", F("pong", 1, Ref("Pong"), optional=True)),
    Msg("Pong", F("pings", 1, List(Ref("Ping")))),
)


@pytest.mark.parametrize("tref, depth", [
    (INT, 0),
    (FLOAT, 0),
    (EnumRef("Mode"), 0),
    (ListOf(INT), 1),
    (ListOf(ListOf(INT)), 2),
    (MapOf(STR, INT), 2),                    # an array of {1: key, 2: value} maps
    (MapOf(INT, MsgRef("Leaf")), 3),
    (ListOf(MapOf(STR, INT)), 3),
    (MsgRef("Leaf"), 1),
    (MsgRef("Keyed"), 4),                    # 1 + map 2 + Leaf 1
    (MsgRef("Grid"), 3),
    (MsgRef("Skip"), 1),                     # a transient field is not on the wire
    (MsgRef("Tree"), 2),                     # the Tree inside counts 0: it is on the path
    (MsgRef("Flat2"), 2),
    (MsgRef("Holds"), 3),
    (MsgRef("Ping"), 3),                     # Ping, Pong, list, then Ping again: 0
    (MsgRef("Pong"), 3),
    (ListOf(MsgRef("Tree")), 3),
])
def test_nesting_of_each_shape(tref, depth):
    assert nesting(NESTED, tref) == depth


def test_glade_nests_five_deep_and_razel_three():
    glade = load_schema(ROOT / "ir" / "glade.taut.py")
    depths = {name: nesting(glade, MsgRef(name)) for name in glade.messages}
    assert max(depths.values()) == 5
    assert {name for name, depth in depths.items() if depth == 5} == {
        "Hello", "Welcome", "Ops", "Heads"}
    assert (depths["Op"], depths["StreamHeads"], depths["Head"]) == (3, 3, 1)
    razel = load_schema(ROOT / "ir" / "razel.taut.py")
    assert max(nesting(razel, MsgRef(name)) for name in razel.messages) == 3


def test_extensions_count_at_every_message_themselves_included():
    base = (Msg("Host", F("id", 1, INT)), Msg("Deep", F("g", 1, List(List(INT)))))
    assert nesting(schema(*base), MsgRef("Host")) == 1
    s = schema(*base, extension("Deep", tag=BAND_START + 1))
    assert nesting(s, MsgRef("Host")) == 4           # Host, then Deep riding it: 1 + 3
    assert nesting(s, MsgRef("Deep")) == 3           # Deep riding Deep is on the path
    assert nesting(s, ListOf(MsgRef("Host"))) == 5
    assert nesting(s, ListOf(INT)) == 1              # extensions ride messages, not lists


def test_extensions_ride_extensions():
    s = schema(
        Msg("Host", F("id", 1, INT)),
        Msg("E1", F("x", 1, INT)),
        Msg("E2", F("y", 1, List(INT))),
        extension("E1", tag=BAND_START + 1),
        extension("E2", tag=BAND_START + 2),
    )
    assert nesting(s, MsgRef("Host")) == 4           # Host, E1, E2, E2's list
    assert nesting(s, MsgRef("E1")) == 3             # E1, E2 riding it, E2's list
    assert nesting(s, MsgRef("E2")) == 2             # E2's list, or E1 riding it: E2 again is 0


def test_nesting_is_memoized_across_shared_paths():
    # 2^40 paths from M0, one per choice of field at each step, yet one value per message.
    chain = [Msg(f"M{i}", F("a", 1, Ref(f"M{i + 1}")), F("b", 2, List(Ref(f"M{i + 1}"))))
             for i in range(40)]
    s = schema(*chain, Msg("M40", F("x", 1, INT)))
    assert nesting(s, MsgRef("M0")) == 81


def test_nesting_refuses_an_unknown_message():
    with pytest.raises(KeyError, match="Nope"):
        nesting(NESTED, MsgRef("Nope"))


# --- the length floor: the smallest canonical encoding (OPT-D6) -------------------------------

ENCODED = schema(
    Enum("Mode", ok=0, alt=1),
    Enum("Wide", mid=100, big=1000),         # the shortest member, 100, is 18 64
    Enum("Negative", n=-25),                 # 38 18
    Enum("Void"),                            # no members, so no value
    Msg("Empty"),
    Msg("Leaf", F("x", 1, INT), F("m", 2, Ref("Mode"))),
    Msg("Tree", F("kids", 1, List(Ref("Tree")))),
    Msg("Head", F("origin", 1, STR), F("seq", 2, INT), F("hash", 3, BYTES, optional=True)),
    Msg("Floaty", F("r", 1, FLOAT)),
    Msg("FarTag", F("x", 24, INT), F("y", 256, INT)),
    Msg("Nulls", F("t", 1, Ref("Tree"), optional=True), F("s", 2, STR, optional=MISSING_OK),
        F("w", 3, Ref("Wide"), optional=True)),
    Msg("Skip", F("t", 1, List(List(INT)), transient=True), F("x", 2, INT)),
    Msg("Nest", F("leaf", 1, Ref("Leaf")), F("wide", 2, Ref("Wide")), F("neg", 3, Ref("Negative"))),
    Msg("Many", **{f"f{i}": F(i, INT) for i in range(1, 25)}),
    Msg("Loop", F("next", 1, Ref("Loop"))),
    Msg("OptLoop", F("next", 1, Ref("OptLoop"), optional=True)),
    Msg("Ping", F("pong", 1, Ref("Pong"))),
    Msg("Pong", F("ping", 1, Ref("Ping"))),
    Msg("ToLoop", F("x", 1, INT), F("ping", 2, Ref("Ping"))),
    Msg("HasVoid", F("v", 1, Ref("Void"))),
    Msg("MaybeVoid", F("v", 1, Ref("Void"), optional=True)),
)


@pytest.mark.parametrize("tref, length", [
    (INT, 1), (STR, 1), (BYTES, 1), (BOOL, 1),
    (FLOAT, 3),                              # 0.0 is a half: f9 0000
    (EnumRef("Mode"), 1),
    (EnumRef("Wide"), 2),
    (EnumRef("Negative"), 2),
    (EnumRef("Void"), None),
    (ListOf(MsgRef("Loop")), 1),             # an empty array, whatever it would hold
    (MapOf(STR, MsgRef("Loop")), 1),
    (MsgRef("Empty"), 1),                    # a0
    (MsgRef("Leaf"), 5),                     # a2 01 00 02 00
    (MsgRef("Tree"), 3),                     # a1 01 80
    (MsgRef("Head"), 7),                     # a3 01 60 02 00 03 f6
    (MsgRef("Floaty"), 5),                   # a1 01 f9 0000
    (MsgRef("FarTag"), 8),                   # a2 1818 00 190100 00
    (MsgRef("Nulls"), 7),                    # every optional field is its key and a null
    (MsgRef("Skip"), 3),                     # a1 02 00: the transient field is not written
    (MsgRef("Nest"), 13),                    # a3 01 [5] 02 1864 03 3818
    (MsgRef("Many"), 51),                    # b818, 23 one-byte keys, 1818, 24 zeros
    (MsgRef("OptLoop"), 3),                  # a1 01 f6
    (MsgRef("MaybeVoid"), 3),
    (MsgRef("Loop"), None),                  # a required field recursing without end
    (MsgRef("Ping"), None),
    (MsgRef("Pong"), None),
    (MsgRef("ToLoop"), None),
    (MsgRef("HasVoid"), None),
])
def test_smallest_encoding_of_each_shape(tref, length):
    assert smallest_encoding(ENCODED, tref) == length


def _minimal(s, tref):
    """The value of `tref` built from each field's shortest canonical value."""
    if isinstance(tref, Scalar):
        return {"int": 0, "str": "", "bytes": b"", "bool": False, "float": 0.0}[tref.kind]
    if isinstance(tref, EnumRef):
        members = s.enums[tref.name].members
        return min(members, key=lambda member: len(cbor.dumps(members[member])))
    if isinstance(tref, ListOf):
        return []
    if isinstance(tref, MapOf):
        return {}
    fields = s.messages[tref.name].wire_fields()
    return {f.name: None if f.optional else _minimal(s, f.type) for f in fields}


def _encoded_schemas():
    yield pytest.param(ENCODED, id="encoded")
    for path in sorted((ROOT / "ir").glob("*.taut.py")):
        yield pytest.param(load_schema(path), id=path.name)


@pytest.mark.parametrize("s", list(_encoded_schemas()))
def test_smallest_encoding_is_what_the_encoder_writes(s):
    checked = 0
    for name in s.messages:
        length = smallest_encoding(s, MsgRef(name))
        if length is not None:
            assert len(codec.encode(s, name, _minimal(s, MsgRef(name)))) == length, name
            checked += 1
    assert checked


def test_smallest_encoding_is_memoized():
    # Each message holds its successor twice: 2^40 visits unmemoized; 3 * (2^41 - 1) bytes.
    chain = [Msg(f"M{i}", F("a", 1, Ref(f"M{i + 1}")), F("b", 2, Ref(f"M{i + 1}")))
             for i in range(40)]
    s = schema(*chain, Msg("M40", F("x", 1, INT)))
    assert smallest_encoding(s, MsgRef("M0")) == 3 * (2**41 - 1)


@pytest.mark.parametrize("tref", [MsgRef("Nope"), EnumRef("Nope"), Scalar("uuid")])
def test_smallest_encoding_refuses_an_unknown_name(tref):
    with pytest.raises(KeyError):
        smallest_encoding(ENCODED, tref)


# --- roots (OPT-D4) ---------------------------------------------------------------------------

def test_roots_are_every_message_then_every_other_slot_type_once():
    s = schema(
        Msg("A", F("x", 1, INT)),
        Msg("B", F("a", 1, Ref("A"))),
        service("S",
                method("m", role="out", params=[("xs", List(INT)), ("a", Ref("A"))],
                       out=List(Ref("A"))),
                method("n", role="query", params=[("ys", List(INT))], out=Ref("B")),
                method("w", role="out", shape="swmr", out={"snapshot": Ref("B"), "delta": INT})),
    )
    assert roots(s) == [
        ("A", MsgRef("A")),
        ("B", MsgRef("B")),
        ("S.m param xs", ListOf(INT)),
        ("S.m out[value]", ListOf(MsgRef("A"))),
        ("S.w out[delta]", INT),
    ]


def test_a_root_that_is_not_a_message_takes_the_file_values_else_the_defaults():
    tree = Msg("Tree", option.max_depth(64), option.max_encoded_len(4096),
               F("kids", 1, List(Ref("Tree"))))
    s = schema(option.max_depth(16), tree)
    assert root_effective(s, "max_depth", MsgRef("Tree")) == 64
    assert root_effective(s, "max_depth", ListOf(MsgRef("Tree"))) == 16
    assert root_effective(s, "max_encoded_len", ListOf(MsgRef("Tree"))) is None
    assert root_effective(schema(tree), "max_depth", ListOf(MsgRef("Tree"))) == 32


# --- per declaration: name, level and value, at every level -----------------------------------

BASE = schema(Enum("Kind", a=0), Msg("M", F("x", 1, INT)))
WHERE = {"file": "file", "message": "M", "field": "M.x", "enum": "enum Kind"}


def _declare(level, options):
    """BASE with `options` declared at one level, as a model no DSL constructor checked."""
    if level == "file":
        return dataclasses.replace(BASE, options=options)
    m = BASE.messages["M"]
    if level == "message":
        return dataclasses.replace(BASE, messages={"M": dataclasses.replace(m, options=options)})
    if level == "field":
        field = dataclasses.replace(m.fields[0], options=options)
        return dataclasses.replace(BASE, messages={"M": dataclasses.replace(m, fields=(field,))})
    kind = dataclasses.replace(BASE.enums["Kind"], options=options)
    return dataclasses.replace(BASE, enums={"Kind": kind})


def test_the_base_model_is_valid():
    assert validate(BASE) == []


@pytest.mark.parametrize("level", ["file", "message", "field", "enum"])
def test_an_unknown_option_is_refused_at_every_level(level):
    assert validate(_declare(level, {"max_dept": 16})) == [
        f"{WHERE[level]}: unknown option 'max_dept' (known: max_depth, max_encoded_len)"]


@pytest.mark.parametrize("level", ["field", "enum"])
@pytest.mark.parametrize("name, value", [("max_depth", 16), ("max_encoded_len", 1024)])
def test_a_bound_is_refused_at_a_level_it_does_not_have(level, name, value):
    assert validate(_declare(level, {name: value})) == [
        f"{WHERE[level]}: option {name} is not allowed at {level} level (allowed: file, message)"]


def test_the_dsl_leaves_the_level_to_validate():
    s = schema(
        Enum("Kind", option.max_encoded_len(3), a=0),
        Msg("Tree", F("kids", 1, List(Ref("Tree")), option.max_depth(5)), option.max_depth(64)),
    )
    assert validate(s) == [
        "Tree.kids: option max_depth is not allowed at field level (allowed: file, message)",
        "enum Kind: option max_encoded_len is not allowed at enum level (allowed: file, message)",
    ]


@pytest.mark.parametrize("level", ["file", "message"])
@pytest.mark.parametrize("name, value, why", [
    ("max_depth", "16", "takes int values, not '16'"),
    ("max_depth", True, "takes int values, not True"),
    ("max_depth", None, "takes int values, not None"),
    ("max_depth", 0, "takes a value from 1 to 128, not 0"),
    ("max_depth", 129, "takes a value from 1 to 128, not 129"),            # above the ceiling
    ("max_encoded_len", 8.0, "takes int values, not 8.0"),
    ("max_encoded_len", None, "takes int values, not None"),
    ("max_encoded_len", -1, "takes a value from 1 to 2147483647, not -1"),
    ("max_encoded_len", 2**31, "takes a value from 1 to 2147483647, not 2147483648"),   # ceiling
])
def test_a_value_no_constructor_checked_is_refused(level, name, value, why):
    assert validate(_declare(level, {name: value})) == [f"{WHERE[level]}: option {name} {why}"]


def test_each_declaration_check_stands_alone():
    assert validate(_declare("field", {"max_depth": "16", "nope": 1})) == [
        "M.x: option max_depth is not allowed at field level (allowed: file, message)",
        "M.x: option max_depth takes int values, not '16'",
        "M.x: unknown option 'nope' (known: max_depth, max_encoded_len)",
    ]


# --- per root: max_depth between the floor and the ceiling -----------------------------------

@pytest.mark.parametrize("name, field", [
    ("Tree", F("kids", 1, List(Ref("Tree")))),
    ("Flat2", F("v", 1, List(INT))),
])
def test_a_root_that_needs_2_passes_declaring_2_and_fails_declaring_1(name, field):
    assert validate(schema(Msg(name, option.max_depth(2), field))) == []
    assert validate(schema(Msg(name, option.max_depth(1), field))) == [
        f"{name}: max_depth 1 (declared here) is below its non-recursive nesting 2"]


def test_a_file_value_must_cover_every_root_that_inherits_it():
    s = schema(
        option.max_depth(2),
        Msg("Leaf", F("x", 1, INT)),
        Msg("Grid", F("g", 1, List(List(INT)))),
        Msg("Own", option.max_depth(3), F("g", 1, List(List(INT)))),
    )
    assert validate(s) == ["Grid: max_depth 2 (the file's) is below its non-recursive nesting 3"]


def test_the_default_must_cover_every_root_that_declares_nothing():
    assert validate(schema(Msg("Deep", F("x", 1, _lists(31))))) == []
    assert validate(schema(Msg("Deep", F("x", 1, _lists(32))))) == [
        "Deep: max_depth 32 (the default) is below its non-recursive nesting 33"]


def test_a_root_nesting_past_the_ceiling_is_refused_whatever_it_declares():
    assert validate(schema(Msg("Deep", option.max_depth(128), F("x", 1, _lists(127))))) == []
    assert validate(schema(Msg("Deep", option.max_depth(128), F("x", 1, _lists(128))))) == [
        "Deep: nests 129 deep, above the max_depth ceiling 128"]


def test_extensions_raise_every_message_floor():
    base = (Msg("Host", option.max_depth(3), F("id", 1, INT)),
            Msg("Deep", F("g", 1, List(List(INT)))))
    assert validate(schema(*base)) == []
    assert validate(schema(*base, extension("Deep", tag=BAND_START + 1))) == [
        "Host: max_depth 3 (declared here) is below its non-recursive nesting 4"]


# --- per root: a declared max_encoded_len holds the smallest encoding -------------------------

def test_a_declared_max_encoded_len_must_hold_the_smallest_encoding():
    assert validate(schema(Msg("Sized", option.max_encoded_len(3), F("b", 1, BYTES)))) == []
    assert validate(schema(Msg("Sized", option.max_encoded_len(2), F("b", 1, BYTES)))) == [
        "Sized: max_encoded_len 2 (declared here) is below its smallest encoding, 3 bytes"]


def test_a_file_max_encoded_len_must_hold_every_root_that_inherits_it():
    s = schema(
        option.max_encoded_len(3),
        Msg("Small", F("x", 1, INT)),
        Msg("Pair", F("x", 1, INT), F("y", 2, INT)),
        Msg("Own", option.max_encoded_len(5), F("x", 1, INT), F("y", 2, INT)),
    )
    assert validate(s) == [
        "Pair: max_encoded_len 3 (the file's) is below its smallest encoding, 5 bytes"]


def test_a_type_with_no_finite_value_admits_no_declared_length():
    # A required field whose type recurses without end has no finite value, so no
    # max_encoded_len can hold one: a declared one is refused. Without one, no length floor
    # applies and validate refuses nothing.
    loop = F("next", 1, Ref("Loop"))
    assert validate(schema(Msg("Loop", loop))) == []
    assert validate(schema(Msg("Loop", option.max_encoded_len(2**31 - 1), loop))) == [
        "Loop: max_encoded_len 2147483647 (declared here) admits no value: none has a finite "
        "encoding (a required field recurses without end or is an enum without members)"]
    assert validate(schema(option.max_encoded_len(64), Msg("Loop", loop))) == [
        "Loop: max_encoded_len 64 (the file's) admits no value: none has a finite "
        "encoding (a required field recurses without end or is an enum without members)"]


# --- method slots are roots --------------------------------------------------------------------

def test_a_method_slot_is_a_root_under_the_file_values():
    s = schema(
        option.max_depth(2),
        Msg("Tree", option.max_depth(64), F("kids", 1, List(Ref("Tree")))),
        service("S",
                method("get", role="out", out=List(Ref("Tree"))),
                method("put", role="in", params=[("rows", List(List(INT)))], out=Ref("Tree")),
                method("deep", role="in", params=[("grid", _lists(3))], out=BOOL)),
    )
    assert validate(s) == [
        "S.get out[value]: max_depth 2 (the file's) is below its non-recursive nesting 3",
        "S.deep param grid: max_depth 2 (the file's) is below its non-recursive nesting 3",
    ]


def test_a_method_slot_under_a_file_max_encoded_len():
    s = schema(
        option.max_encoded_len(2),
        Msg("Empty"),
        service("S",
                method("ratio", role="out", out=FLOAT),
                method("ping", role="ctl", params=[("n", INT)], out=Ref("Empty"))),
    )
    assert validate(s) == [
        "S.ratio out[value]: max_encoded_len 2 (the file's) is below its smallest encoding, 3 bytes"]


def test_a_slot_typed_as_a_message_is_that_message_root_checked_once():
    s = schema(
        Msg("Flat2", option.max_depth(1), F("v", 1, List(INT))),
        service("S", method("get", role="out", out=Ref("Flat2")),
                method("put", role="in", params=[("f", Ref("Flat2"))], out=BOOL)),
    )
    assert validate(s) == ["Flat2: max_depth 1 (declared here) is below its non-recursive nesting 2"]


# --- what validate already refuses does not break the option checks ---------------------------

def test_a_dangling_reference_skips_its_roots_floors():
    s = schema(
        option.max_depth(1),
        Msg("A", F("x", 1, Ref("Nope"))),
        Msg("B", F("xs", 1, List(INT))),
        service("S", method("get", role="out", out=List(Ref("Nope")))),
    )
    assert validate(s) == [
        "A.x: dangling message ref 'Nope'",
        "S.get out[value]: dangling message ref 'Nope'",
        "B: max_depth 1 (the file's) is below its non-recursive nesting 2",
    ]


def test_a_clean_schema_with_bounds_at_both_levels():
    s = schema(
        option.max_depth(16),
        option.max_encoded_len(1 << 20),
        Enum("Mode", ok=0),
        Msg("Tree", option.max_depth(64), option.max_encoded_len(1 << 24),
            F("kids", 1, List(Ref("Tree")))),
        Msg("Leaf", F("m", 1, Ref("Mode")), F("tags", 2, Map(STR, INT))),
        service("S", method("leaves", role="out", out=List(Ref("Leaf")))),
    )
    assert validate(s) == []
    assert lint(s) == []


# --- lint: warnings, never errors (OPT-D4, OPT-D5) --------------------------------------------

def test_lint_warns_about_a_recursive_message_that_declares_no_max_depth():
    s = schema(
        Msg("Tree", F("kids", 1, List(Ref("Tree")))),
        Msg("Holds", F("t", 1, Ref("Tree"))),                # embeds a tree, is not one
        Msg("Ping", F("pong", 1, Ref("Pong"), optional=True)),
        Msg("Pong", F("pings", 1, Map(INT, Ref("Ping")))),
    )
    assert validate(s) == []
    assert lint(s) == [
        "Tree: recursive but declares no max_depth; a decode rooted at it applies the default 32, "
        "which its data may outgrow",
        "Ping: recursive but declares no max_depth; a decode rooted at it applies the default 32, "
        "which its data may outgrow",
        "Pong: recursive but declares no max_depth; a decode rooted at it applies the default 32, "
        "which its data may outgrow",
    ]


def test_lint_names_the_file_value_a_recursive_message_inherits():
    s = schema(option.max_depth(16), Msg("Tree", F("kids", 1, List(Ref("Tree")))))
    assert lint(s) == [
        "Tree: recursive but declares no max_depth; a decode rooted at it applies the file's 16, "
        "which its data may outgrow"]


def test_a_recursive_message_that_declares_max_depth_is_no_warning():
    assert lint(schema(Msg("Tree", option.max_depth(64), F("kids", 1, List(Ref("Tree")))))) == []


def test_extensions_do_not_make_a_message_recursive():
    s = schema(Msg("Host", F("id", 1, INT)), Msg("Ext", F("x", 1, INT)),
               extension("Ext", tag=BAND_START + 1))
    assert lint(s) == []


BOUNDS = (
    # TautCheckedDecode.md CD-C1's bounds fixture messages
    Msg("Tree64", option.max_depth(64), F("kids", 1, List(Ref("Tree64")))),
    Msg("Flat2", option.max_depth(2), F("v", 1, List(INT))),
    Msg("Sized8", option.max_encoded_len(8), F("b", 1, BYTES)),
    Msg("Holds64", F("t", 1, Ref("Tree64"))),
    Msg("HoldsSized8", F("s", 1, Ref("Sized8"))),
)


def test_lint_warns_where_an_embedder_applies_another_bound():
    s = schema(*BOUNDS)
    assert validate(s) == []
    assert lint(s) == [
        "Tree64: its max_depth 64 cannot take effect inside Holds64, which embeds it; "
        "a decode rooted there applies 32",
        "Sized8: its max_encoded_len 8 cannot take effect inside HoldsSized8, which embeds it; "
        "a decode rooted there applies no bound",
    ]


def test_an_embedder_at_any_depth_or_a_method_slot():
    s = schema(
        Msg("Tree64", option.max_depth(64), F("kids", 1, List(Ref("Tree64")))),
        Msg("Holds64", F("t", 1, Ref("Tree64"))),
        Msg("Outer", F("h", 1, Map(STR, Ref("Holds64")))),
        service("S", method("trees", role="out", out=List(Ref("Tree64")))),
    )
    assert lint(s) == [
        "Tree64: its max_depth 64 cannot take effect inside Holds64, which embeds it; "
        "a decode rooted there applies 32",
        "Tree64: its max_depth 64 cannot take effect inside Outer, which embeds it; "
        "a decode rooted there applies 32",
        "Tree64: its max_depth 64 cannot take effect inside S.trees out[value], which embeds it; "
        "a decode rooted there applies 32",
    ]


def test_an_embedder_applying_the_same_value_is_no_warning():
    s = schema(
        option.max_depth(64),
        Msg("Tree64", option.max_depth(64), F("kids", 1, List(Ref("Tree64")))),
        Msg("Holds64", F("t", 1, Ref("Tree64"))),
        Msg("Sized8", option.max_encoded_len(8), F("b", 1, BYTES)),
        Msg("HoldsSized8", option.max_encoded_len(8), F("s", 1, Ref("Sized8"))),
    )
    assert lint(s) == []


def test_lint_passes_over_what_validate_refuses():
    tree = MsgRef("Tree")
    s = schema(
        Msg("Tree", F("kids", 1, List(tree))),
        Msg("Holds", F("t", 1, tree)),
        Msg("A", F("x", 1, Ref("Nope"))),
    )
    bad = dataclasses.replace(s.messages["Tree"], options={"max_depth": "64"})
    s = dataclasses.replace(s, messages={**s.messages, "Tree": bad})
    assert validate(s) == [
        "A.x: dangling message ref 'Nope'",
        "Tree: option max_depth takes int values, not '64'",
    ]
    assert lint(s) == []


# --- tautc: lint's warnings go to stderr, and never fail a command ----------------------------

RECURSIVE = """
from taut.ir.dsl import F, Msg, Ref, schema

SCHEMA = schema(Msg("Node", F("next", 1, Ref("Node"), optional=True)))
"""


@pytest.mark.parametrize("argv", [
    ["gen", "{ir}", "-o", "{out}", "-l", "python", "--api-only"],
    ["corpus", "{ir}", "-o", "{out}"],
    ["json", "{ir}", "-m", "Node", "-i", "{cbor}", "-o", "{out}/node.json"],
], ids=["gen", "corpus", "json"])
def test_tautc_prints_lint_warnings_to_stderr_and_succeeds(tmp_path, capsys, argv):
    ir = tmp_path / "node.taut.py"
    ir.write_text(RECURSIVE)
    node = tmp_path / "node.cbor"
    node.write_bytes(bytes.fromhex("a101f6"))
    out = tmp_path / "out"
    out.mkdir()
    assert main([arg.format(ir=ir, out=out, cbor=node) for arg in argv]) == 0
    assert (f"tautc {argv[0]}: warning: Node: recursive but declares no max_depth; a decode "
            "rooted at it applies the default 32, which its data may outgrow\n"
            in capsys.readouterr().err)


def test_tautc_prints_no_warning_for_a_clean_schema(tmp_path, capsys):
    ir = ROOT / "ir" / "glade.taut.py"
    assert main(["gen", str(ir), "-o", str(tmp_path), "-l", "python", "--api-only"]) == 0
    assert "warning" not in capsys.readouterr().err


def test_tautc_refuses_a_bound_below_its_floor(tmp_path):
    ir = tmp_path / "flat.taut.py"
    ir.write_text("from taut.ir.dsl import INT, F, List, Msg, option, schema\n"
                  'SCHEMA = schema(Msg("Flat2", option.max_depth(1), F("v", 1, List(INT))))\n')
    with pytest.raises(ValueError, match="Flat2: max_depth 1 .* nesting 2"):
        main(["gen", str(ir), "-o", str(tmp_path / "out"), "-l", "python"])
    assert not (tmp_path / "out").exists()
