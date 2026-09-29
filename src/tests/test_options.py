"""Options (D27, TautOptions.md): definitions, the `option` namespace and resolution.

The DSL's side (positional option values at each level, the rebuilds) is in test_dsl.py.
"""

import dataclasses

import pytest

from taut.ir.dsl import INT, F, List, Msg, Ref, schema
from taut.ir.model import Schema
from taut.ir.options import (
    CLASSES,
    DEFAULT_MAX_DEPTH,
    LEVELS,
    MAX_DEPTH_CEILING,
    MAX_ENCODED_LEN_CEILING,
    OPTIONS,
    OptionDef,
    OptionValue,
    check_value,
    effective,
    effective_map,
    option,
)


# --- the definitions (OPT-D1, D5, D6) --------------------------------------------------------

def test_runtime_numbers():
    assert DEFAULT_MAX_DEPTH == 32
    assert MAX_DEPTH_CEILING == 128
    assert MAX_ENCODED_LEN_CEILING == 2**31 - 1
    assert LEVELS == ("file", "message", "field", "enum", "enum_value", "service", "method")
    assert CLASSES == ("wire", "codegen", "metadata", "semantic")


def test_max_depth_is_defined_as_opt_d5_gives_it():
    assert OPTIONS["max_depth"] == OptionDef(
        "max_depth", int, frozenset({"file", "message"}), default=32, klass="wire",
        inherits=("message", "file"),
    )
    assert OPTIONS["max_depth"].targets is None


def test_max_encoded_len_is_defined_as_opt_d6_gives_it():
    assert OPTIONS["max_encoded_len"] == OptionDef(
        "max_encoded_len", int, frozenset({"file", "message"}), default=None, klass="wire",
        inherits=("message", "file"),
    )
    assert OPTIONS["max_encoded_len"].targets is None


@pytest.mark.parametrize("name", sorted(OPTIONS))
def test_every_definition_is_consistent(name):
    defn = OPTIONS[name]
    assert defn.name == name
    assert defn.value_type in (int, bool, str)
    assert defn.levels <= set(LEVELS)
    assert defn.klass in CLASSES
    assert set(defn.inherits) <= defn.levels, "inherits names only levels in levels"
    assert len(set(defn.inherits)) == len(defn.inherits)
    if defn.default is not None:   # None: no value where nothing is declared
        check_value(name, defn.default)   # the default passes its own checks


def test_definitions_and_values_are_frozen():
    with pytest.raises(dataclasses.FrozenInstanceError):
        OPTIONS["max_depth"].default = 64
    with pytest.raises(dataclasses.FrozenInstanceError):
        option.max_depth(16).value = 64


# --- the namespace (OPT-L1, question 6) ------------------------------------------------------

def test_attribute_access_gives_the_typed_constructor():
    assert option.max_depth(16) == OptionValue("max_depth", 16)
    assert option.max_encoded_len(1024) == OptionValue("max_encoded_len", 1024)


def test_an_unknown_option_raises_attribute_error_naming_the_known_ones():
    with pytest.raises(AttributeError, match="max_dept") as excinfo:
        option.max_dept(16)
    for known in OPTIONS:
        assert known in str(excinfo.value)
    assert not hasattr(option, "deprecated")
    assert getattr(option, "__wrapped__", None) is None


@pytest.mark.parametrize("args", [("ns.name", 1), ("max_depth", 16), ()])
def test_calling_the_namespace_is_reserved_for_custom_options(args):
    with pytest.raises(TypeError, match="custom options are reserved"):
        option(*args)


# --- the constructors: type and range --------------------------------------------------------

@pytest.mark.parametrize("name", ["max_depth", "max_encoded_len"])
@pytest.mark.parametrize("bad", ["16", 16.0, True, False, None, [16]])
def test_int_options_refuse_other_types_bool_included(name, bad):
    with pytest.raises(TypeError, match=name):
        getattr(option, name)(bad)
    with pytest.raises(TypeError, match=name):
        check_value(name, bad)


@pytest.mark.parametrize("bad", [0, -1, 129, 2**31])
def test_max_depth_refuses_values_outside_1_to_128(bad):
    with pytest.raises(ValueError, match="max_depth"):
        option.max_depth(bad)


@pytest.mark.parametrize("good", [1, 32, 128])
def test_max_depth_takes_values_from_1_to_128(good):
    assert option.max_depth(good).value == good


@pytest.mark.parametrize("bad", [0, -1, 2**31])
def test_max_encoded_len_refuses_values_outside_1_to_the_ceiling(bad):
    with pytest.raises(ValueError, match="max_encoded_len"):
        option.max_encoded_len(bad)


@pytest.mark.parametrize("good", [1, 16 * 2**20, 2**31 - 1])
def test_max_encoded_len_takes_values_up_to_the_ceiling(good):
    assert option.max_encoded_len(good).value == good


def test_check_value_refuses_an_unregistered_name():
    with pytest.raises(KeyError, match="nope"):
        check_value("nope", 1)


# --- resolution (OPT-D3) ---------------------------------------------------------------------

def _tree_schema(*file_options):
    return schema(
        *file_options,
        Msg("Tree", option.max_depth(64), F("children", 1, List(Ref("Tree")))),
        Msg("Holds", F("t", 1, Ref("Tree"))),
    )


def test_nothing_declared_resolves_to_the_defaults():
    s = schema(Msg("M", F("x", 1, INT)))
    assert effective(s, "max_depth") == 32
    assert effective(s, "max_depth", message="M") == 32
    assert effective(s, "max_encoded_len") is None
    assert effective(s, "max_encoded_len", message="M") is None
    bare = Schema(enums={}, messages={})
    assert effective(bare, "max_depth") == 32


def test_the_message_overrides_the_file_which_overrides_the_default():
    s = _tree_schema(option.max_depth(16))
    assert effective(s, "max_depth", message="Tree") == 64   # the message's own
    assert effective(s, "max_depth", message="Holds") == 16  # the file's
    assert effective(s, "max_depth") == 16                   # at file level
    assert effective(_tree_schema(), "max_depth", message="Holds") == 32   # the default


def test_enclosure_is_lexical_a_message_inherits_nothing_from_its_user():
    s = schema(
        Msg("Outer", option.max_depth(8), option.max_encoded_len(64), F("inner", 1, Ref("Inner"))),
        Msg("Inner", F("x", 1, INT)),
    )
    assert effective(s, "max_depth", message="Outer") == 8
    assert effective(s, "max_depth", message="Inner") == 32
    assert effective(s, "max_encoded_len", message="Inner") is None
    assert effective(s, "max_depth") == 32   # a message's declaration never reaches the file


def test_max_encoded_len_inherits_like_max_depth():
    s = schema(
        option.max_encoded_len(4096),
        Msg("Blob", option.max_encoded_len(2**20), F("x", 1, INT)),
        Msg("Small", F("x", 1, INT)),
    )
    assert effective(s, "max_encoded_len") == 4096
    assert effective(s, "max_encoded_len", message="Small") == 4096
    assert effective(s, "max_encoded_len", message="Blob") == 2**20


def test_effective_values_are_computed_not_stored():
    s = _tree_schema(option.max_depth(16))
    assert s.options == {"max_depth": 16}
    assert s.messages["Tree"].options == {"max_depth": 64}
    assert s.messages["Holds"].options == {}


def test_effective_refuses_an_unregistered_option_or_an_unknown_message():
    s = _tree_schema()
    with pytest.raises(KeyError, match="nope"):
        effective(s, "nope")
    with pytest.raises(KeyError, match="Nope"):
        effective(s, "max_depth", message="Nope")
    with pytest.raises(KeyError, match="Nope"):
        effective_map(s, message="Nope")


def test_effective_map_resolves_every_option_of_the_level_defaults_included():
    s = _tree_schema(option.max_encoded_len(1024))
    assert effective_map(s) == {"max_depth": 32, "max_encoded_len": 1024}
    assert effective_map(s, message="Tree") == {"max_depth": 64, "max_encoded_len": 1024}
    assert effective_map(s, message="Holds") == {"max_depth": 32, "max_encoded_len": 1024}
    assert list(effective_map(s)) == ["max_depth", "max_encoded_len"]   # registry order


def test_effective_map_holds_only_wire_and_codegen_options_defined_for_the_level(monkeypatch):
    extra = [
        OptionDef("gen_file", bool, frozenset({"file"}), default=False, klass="codegen",
                  inherits=("file",)),
        OptionDef("gen_field", bool, frozenset({"field"}), default=False, klass="codegen",
                  inherits=("field",)),
        OptionDef("doc", str, frozenset({"file", "message"}), default="", klass="metadata",
                  inherits=("message", "file")),
        OptionDef("merge_like", str, frozenset({"file", "message"}), default="lww",
                  klass="semantic", inherits=("message", "file")),
    ]
    for defn in extra:
        monkeypatch.setitem(OPTIONS, defn.name, defn)
    s = _tree_schema()
    assert effective_map(s) == {"max_depth": 32, "max_encoded_len": None, "gen_file": False}
    assert effective_map(s, message="Tree") == {"max_depth": 64, "max_encoded_len": None}
    assert effective(s, "doc", message="Tree") == ""   # still resolvable one by one
