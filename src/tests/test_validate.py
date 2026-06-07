"""The validator: the GripLab IR is coherent, and incoherent IR is rejected with
useful messages. This is the gate that lets mechanism be derived from the IR
without review."""

import pytest

from taut.corpus.build import IR_PATH
from taut.ir.dsl import BOOL, INT, STR, Enum, F, Msg, Ref, method, schema, service
from taut.ir.load import load_schema
from taut.ir.validate import validate, validate_or_raise


def test_griplab_ir_is_valid():
    assert validate(load_schema(IR_PATH)) == []


def test_dangling_message_ref():
    errs = validate(schema(Msg("A", F("x", 1, Ref("Nope")))))
    assert any("dangling message ref" in e for e in errs)


def test_duplicate_tag():
    errs = validate(schema(Msg("A", F("x", 1, STR), F("y", 1, INT))))
    assert any("duplicate tag" in e for e in errs)


def test_enum_duplicate_values():
    errs = validate(schema(Enum("E", a=1, b=1), Msg("A", F("x", 1, Ref("E")))))
    assert any("duplicate wire values" in e for e in errs)


def test_method_must_bind_out():
    # A method (unary by default) with no `out` is rejected.
    errs = validate(schema(service("S", method("m", role="out"))))
    assert any("must bind out" in e for e in errs)


def test_out_slot_must_match_shape():
    s = schema(
        Msg("V", F("x", 1, STR)),
        service("S", method("m", role="out", shape="atom",
                            out={"delta": Ref("V")})),  # 'delta' is not an atom slot
    )
    assert any("not allowed for shape" in e for e in validate(s))


def test_unknown_shape_rejected():
    s = schema(
        Msg("V", F("x", 1, STR)),
        service("S", method("m", role="out", shape="bogus", out={"x": Ref("V")})),
    )
    assert any("unknown delivery shape" in e for e in validate(s))


def test_kind_is_derived_not_storable():
    # D22: there is no `kind` to set, and unary-with-a-shape is unrepresentable.
    # `out` as a bare type binds the shape's sole slot; kind/output/events derive.
    m_unary = method("u", role="out", out=BOOL)
    assert m_unary.shape == "unary" and not m_unary.streams()
    assert m_unary.output == BOOL and m_unary.events == ()
    m_stream = method("s", role="out", shape="atom", out=Ref("V"))
    assert m_stream.streams() and m_stream.output is None
    assert m_stream.events == (("replace", Ref("V")),)
    # multi-slot shapes require an explicit {slot: type} map
    with pytest.raises(ValueError):
        method("bad", role="out", shape="swmr", out=Ref("V"))


def test_validate_or_raise():
    with pytest.raises(ValueError):
        validate_or_raise(schema(Msg("A", F("x", 1, Ref("Nope")))))
