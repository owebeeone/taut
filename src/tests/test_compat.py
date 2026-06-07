"""The breaking-change gate (P7) — DoD: rejects an incompatible IR change and
accepts a compatible one. Plus the rule table and JSON round-trip."""

import json

import pytest

from taut.corpus.build import IR_JSON_PATH, IR_PATH
from taut.ir import compat
from taut.ir.dsl import BOOL, INT, STR, Enum, F, Msg, Ref, method, schema, service
from taut.ir.export import schema_json
from taut.ir.load import load_schema, schema_from_json


def _details(changes):
    return " | ".join(c.detail for c in changes)


# --- DoD: identical accepted, the two canonical directions -------------------

def test_identical_ir_has_no_breaking_changes():
    cur = schema_from_json(json.loads(IR_JSON_PATH.read_text()))
    assert compat.diff(cur, cur) == []


def test_json_round_trips():
    s = load_schema(IR_PATH)
    assert schema_from_json(schema_json(s)) == s


def test_accepts_compatible_added_optional_field():
    old = schema(Msg("A", F("x", 1, STR)))
    new = schema(Msg("A", F("x", 1, STR), F("y", 2, INT, optional=True)))
    assert compat.breaking(old, new) == []
    compat.check_or_raise(old, new)  # does not raise
    assert "y (tag 2) added" in _details(compat.diff(old, new))


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
