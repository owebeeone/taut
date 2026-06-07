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


def test_unary_requires_output():
    errs = validate(schema(service("S", method("m", kind="unary", role="out"))))
    assert any("must declare output" in e for e in errs)


def test_stream_event_must_match_shape():
    s = schema(
        Msg("V", F("x", 1, STR)),
        service("S", method("m", kind="server_stream", role="out", shape="atom",
                            events={"delta": Ref("V")})),  # 'delta' is not an atom event
    )
    assert any("not allowed for shape" in e for e in validate(s))


def test_unknown_shape_rejected():
    s = schema(
        Msg("V", F("x", 1, STR)),
        service("S", method("m", kind="server_stream", role="out", shape="bogus",
                            events={"x": Ref("V")})),
    )
    assert any("unknown delivery shape" in e for e in validate(s))


def test_server_stream_must_not_have_output():
    s = schema(
        Msg("V", F("x", 1, STR)),
        service("S", method("m", kind="server_stream", role="out", shape="atom",
                            events={"replace": Ref("V")}, output=BOOL)),
    )
    assert any("must not declare output" in e for e in validate(s))


def test_validate_or_raise():
    with pytest.raises(ValueError):
        validate_or_raise(schema(Msg("A", F("x", 1, Ref("Nope")))))
