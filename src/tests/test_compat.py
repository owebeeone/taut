"""The breaking-change gate (P7) — DoD: rejects an incompatible IR change and
accepts a compatible one. Plus the rule table and JSON round-trip."""

import json

import pytest

from taut.corpus.build import IR_JSON_PATH, IR_PATH
from taut.ir import compat
from taut.ir.dsl import (
    BOOL, INT, MISSING_OK, STR, Enum, F, List, Msg, Params, Ref, method, option, schema, service,
)
from taut.ir.export import schema_json
from taut.ir.load import load_schema, schema_from_json
from taut.ir.model import Schema
from taut.ir.options import OPTIONS, OptionDef


def _details(changes):
    return " | ".join(c.detail for c in changes)


# --- DoD: identical accepted, the two canonical directions -------------------

def test_identical_ir_has_no_breaking_changes():
    cur = schema_from_json(json.loads(IR_JSON_PATH.read_text()))
    assert compat.diff(cur, cur) == []


def test_json_round_trips():
    s = load_schema(IR_PATH)
    assert schema_from_json(schema_json(s)) == s


def test_catalogue_metadata_only_change_is_not_a_method_change():
    s = load_schema(IR_PATH)
    old_data = schema_json(s)
    new_data = json.loads(json.dumps(old_data))
    new_data["shapes"]["atom"]["position"] = "future-version-metadata"
    old = schema_from_json(old_data)
    new = schema_from_json(new_data)
    assert compat.diff(old, new) == []


def test_accepts_compatible_added_optional_field():
    old = schema(Msg("A", F("x", 1, STR)))
    new = schema(Msg("A", F("x", 1, STR), F("y", 2, INT, optional=True)))
    assert compat.breaking(old, new) == []
    compat.check_or_raise(old, new)  # does not raise
    assert "y (tag 2) added" in _details(compat.diff(old, new))


def test_presence_is_a_ladder_graded_by_direction():
    required = schema(Msg("A", F("x", 1, STR)))
    nullable = schema(Msg("A", F("x", 1, STR, optional=True)))
    missing = schema(Msg("A", F("x", 1, STR, optional=MISSING_OK)))
    for old, new in ((required, nullable), (nullable, missing), (required, missing)):
        assert not compat.breaking(old, new)
    assert "A.x optional->missing_ok" in _details(compat.diff(nullable, missing))
    assert "A.x required->missing_ok" in _details(compat.diff(required, missing))
    assert "A.x missing_ok->optional" in _details(compat.breaking(missing, nullable))
    assert "A.x missing_ok->required" in _details(compat.breaking(missing, required))
    assert "A.x optional->required" in _details(compat.breaking(nullable, required))


def test_rejects_removed_field():
    old = schema(Msg("A", F("x", 1, STR), F("y", 2, INT)))
    new = schema(Msg("A", F("x", 1, STR)))
    bad = compat.breaking(old, new)
    assert any("y (tag 2) removed" in c.detail for c in bad)
    with pytest.raises(ValueError):
        compat.check_or_raise(old, new)


# --- the rule table ----------------------------------------------------------

def test_rejects_wire_type_change():
    old = schema(Msg("A", F("x", 1, STR)))
    new = schema(Msg("A", F("x", 1, INT)))
    assert any("wire-type changed" in c.detail for c in compat.breaking(old, new))


def test_rejects_tag_renumber():
    old = schema(Msg("A", F("x", 1, STR)))
    new = schema(Msg("A", F("x", 2, STR)))
    assert compat.breaking(old, new)  # x moved tag 1->2 (and tag 1 removed)


def test_rejects_new_required_field_but_accepts_optional():
    old = schema(Msg("A", F("x", 1, STR)))
    req = schema(Msg("A", F("x", 1, STR), F("y", 2, INT)))
    opt = schema(Msg("A", F("x", 1, STR), F("y", 2, INT, optional=True)))
    assert compat.breaking(old, req)      # required add is breaking
    assert not compat.breaking(old, opt)  # optional add is fine


def test_enum_member_value_change_breaks_but_add_is_ok():
    old = schema(Enum("E", a=0, b=1), Msg("M", F("e", 1, Ref("E"))))
    changed = schema(Enum("E", a=0, b=2), Msg("M", F("e", 1, Ref("E"))))
    added = schema(Enum("E", a=0, b=1, c=2), Msg("M", F("e", 1, Ref("E"))))
    assert any("wire value" in c.detail for c in compat.breaking(old, changed))
    assert not compat.breaking(old, added)


def test_service_method_changes():
    base = schema(
        Msg("V", F("x", 1, STR)),
        service("S",
                method("get", role="out", out=Ref("V")),
                method("sub", role="out", shape="atom", out=Ref("V"))),
    )
    removed = schema(Msg("V", F("x", 1, STR)),
                     service("S", method("sub", role="out", shape="atom", out=Ref("V"))))
    shape_changed = schema(
        Msg("V", F("x", 1, STR)),
        service("S",
                method("get", role="out", out=Ref("V")),
                method("sub", role="out", out=Ref("V"))),  # was shape="atom" (now unary)
    )
    assert any("method S.get removed" in c.detail for c in compat.breaking(base, removed))
    assert any("shape" in c.detail for c in compat.breaking(base, shape_changed))
    # adding a method is compatible
    added = schema(
        Msg("V", F("x", 1, STR)),
        service("S",
                method("get", role="out", out=Ref("V")),
                method("sub", role="out", shape="atom", out=Ref("V")),
                method("ping", role="out", out=BOOL)),
    )
    assert not compat.breaking(base, added)


# --- options (D27, TautOptions.md OPT-K1-K4) ---------------------------------

def _pairs(changes):
    return [(c.level, c.detail) for c in changes]


def _tree(*message_options):
    return schema(Msg("Tree", *message_options, F("children", 1, List(Ref("Tree")))))


@pytest.mark.parametrize("name,high,low", [("max_depth", 64, 16), ("max_encoded_len", 4096, 64)])
def test_a_bound_changed_at_a_message_is_breaking_both_ways(name, high, low):
    make = getattr(option, name)
    wide, narrow = _tree(make(high)), _tree(make(low))
    assert _pairs(compat.diff(wide, narrow)) == [
        ("breaking", f"message Tree wire option {name} {high}->{low}")]
    assert _pairs(compat.diff(narrow, wide)) == [
        ("breaking", f"message Tree wire option {name} {low}->{high}")]
    with pytest.raises(ValueError, match=f"message Tree wire option {name} {low}->{high}"):
        compat.check_or_raise(narrow, wide)


def test_none_is_unbounded_so_a_first_max_encoded_len_lowers_it():
    unbounded, bounded = _tree(), _tree(option.max_encoded_len(1024))
    assert _pairs(compat.diff(unbounded, bounded)) == [
        ("breaking", "message Tree wire option max_encoded_len none->1024")]
    assert _pairs(compat.diff(bounded, unbounded)) == [
        ("breaking", "message Tree wire option max_encoded_len 1024->none")]


def _app(*file_options, leaf=()):
    """Roots of every kind: a message that inherits the file's values, one that declares its own
    max_depth, and method slots typed as a message, a list of messages and a scalar."""
    return schema(
        *file_options,
        Msg("Leaf", *leaf, F("x", 1, INT)),
        Msg("Tree", option.max_depth(64), F("children", 1, List(Ref("Tree")))),
        service("S",
                method("get", role="out", out=Ref("Leaf")),
                method("all", role="out", params=Params(limit=INT), out=List(Ref("Leaf")))),
    )


def test_a_file_level_change_reaches_every_inheriting_root():
    old, new = _app(option.max_depth(16)), _app(option.max_depth(24))
    # Tree declares its own; S.get's slot is typed Leaf, so its root is the message Leaf
    assert _pairs(compat.diff(old, new)) == [
        ("breaking", "message Leaf wire option max_depth 16->24"),
        ("breaking", "method S.all param limit wire option max_depth 16->24"),
        ("breaking", "method S.all out value wire option max_depth 16->24"),
    ]
    with pytest.raises(ValueError, match="method S.all out value wire option max_depth"):
        compat.check_or_raise(old, new)


def test_a_first_file_level_max_encoded_len_reaches_every_root_that_declares_none():
    old, new = _app(), _app(option.max_encoded_len(2**20))
    assert _pairs(compat.diff(old, new)) == [
        ("breaking", f"message Leaf wire option max_encoded_len none->{2**20}"),
        ("breaking", f"message Tree wire option max_encoded_len none->{2**20}"),
        ("breaking", f"method S.all param limit wire option max_encoded_len none->{2**20}"),
        ("breaking", f"method S.all out value wire option max_encoded_len none->{2**20}"),
    ]


def test_moving_a_declaration_without_changing_an_effective_value_is_no_change():
    at_file = schema(option.max_depth(16), option.max_encoded_len(512),
                     Msg("A", F("x", 1, INT)),
                     Msg("B", option.max_depth(64), F("y", 1, INT)))
    at_messages = schema(Msg("A", option.max_depth(16), option.max_encoded_len(512), F("x", 1, INT)),
                         Msg("B", option.max_depth(64), option.max_encoded_len(512), F("y", 1, INT)))
    assert compat.diff(at_file, at_file) == []
    assert compat.diff(at_file, at_messages) == []
    assert compat.diff(at_messages, at_file) == []
    # declaring the default changes no effective value
    assert compat.diff(_tree(), _tree(option.max_depth(32))) == []
    # nor does a file-level change that every root overrides
    overridden = schema(option.max_depth(8), option.max_encoded_len(4), *at_messages.messages.values())
    assert compat.diff(at_messages, overridden) == []
    assert compat.diff(at_file, overridden) == []


def test_a_move_off_the_file_changes_the_slots_that_take_the_files_values():
    at_file, at_leaf = _app(option.max_depth(16)), _app(leaf=(option.max_depth(16),))
    assert _pairs(compat.diff(at_file, at_leaf)) == [
        ("breaking", "method S.all param limit wire option max_depth 16->32"),
        ("breaking", "method S.all out value wire option max_depth 16->32"),
    ]


def test_a_new_message_that_declares_a_bound_is_message_added():
    old = schema(Msg("A", F("x", 1, INT)))
    new = schema(Msg("A", F("x", 1, INT)),
                 Msg("Tree", option.max_depth(64), option.max_encoded_len(8),
                     F("children", 1, List(Ref("Tree")))))
    assert _pairs(compat.diff(old, new)) == [("compatible", "message Tree added")]
    assert _pairs(compat.diff(new, old)) == [("breaking", "message Tree removed")]


# Options of the other classes, registered for a test: none exists yet (OPT-D2, question 7).
_CLASSES = (
    OptionDef("gen_names", bool, frozenset({"file", "message", "field"}), default=False,
              klass="codegen", inherits=("field", "message", "file")),
    OptionDef("doc", str, frozenset({"file", "message", "field", "enum"}), default="",
              klass="metadata", inherits=()),
    OptionDef("merge_like", str, frozenset({"file", "message"}), default="lww",
              klass="semantic", inherits=("message", "file")),
)


@pytest.fixture
def classes(monkeypatch):
    for defn in _CLASSES:
        monkeypatch.setitem(OPTIONS, defn.name, defn)


def test_a_semantic_change_is_breaking_as_for_wire(classes):
    old = schema(Msg("A", F("x", 1, INT)), Msg("B", option.merge_like("counter"), F("y", 1, INT)))
    new = schema(option.merge_like("counter"), Msg("A", F("x", 1, INT)), Msg("B", F("y", 1, INT)))
    # B's value moved to the file, which A now inherits
    assert _pairs(compat.diff(old, new)) == [
        ("breaking", "message A semantic option merge_like 'lww'->'counter'")]
    with pytest.raises(ValueError, match="merge_like"):
        compat.check_or_raise(old, new)


def test_a_codegen_change_is_compatible_with_a_note(classes):
    old = schema(Msg("A", F("x", 1, INT)))
    new = schema(option.gen_names(True), Msg("A", F("x", 1, INT, option.gen_names(False))))
    note = "(wire-compatible; the generated API may change)"
    assert _pairs(compat.diff(old, new)) == [
        ("compatible", f"file codegen option gen_names unset->True {note}"),
        ("compatible", f"A.x codegen option gen_names unset->False {note}"),
    ]
    compat.check_or_raise(old, new)   # does not raise


def test_a_metadata_change_is_listed_and_changes_nothing(classes):
    old = schema(Enum("E", option.doc("old"), a=0), Msg("A", option.doc("a"), F("x", 1, INT)))
    new = schema(Enum("E", option.doc("new"), a=0), Msg("A", F("x", 1, INT)))
    assert _pairs(compat.diff(old, new)) == [
        ("compatible", "message A metadata option doc 'a'->unset"),
        ("compatible", "enum E metadata option doc 'old'->'new'"),
    ]
    compat.check_or_raise(old, new)   # does not raise


def test_an_unregistered_option_is_breaking_since_its_class_is_unknown():
    old = Schema(enums={}, messages={}, options={"nope": 1})
    new = Schema(enums={}, messages={}, options={"nope": 2})
    assert _pairs(compat.diff(old, new)) == [("breaking", "file unknown option nope 1->2")]
    assert compat.diff(old, old) == []


def test_every_breaking_class_option_resolves_where_roots_see_it():
    """The gate grades wire and semantic options at roots through `effective`, which reads the file
    and message levels; an option declared elsewhere needs the gate extended first."""
    for name, defn in OPTIONS.items():
        if defn.klass in ("wire", "semantic"):
            assert defn.levels <= {"file", "message"}, name
