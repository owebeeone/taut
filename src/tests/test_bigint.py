"""BIGINT is tagged, arbitrary precision and distinct from legacy INT."""
import pytest

from taut.ir.dsl import BIGINT, INT, F, List, Msg, schema
from taut.ir.validate import validate_or_raise
from taut.wire import cbor, codec, jsoncodec


SCHEMA = schema(Box=Msg(n=F(1, BIGINT), values=F(2, List(BIGINT)), small=F(3, INT)))


@pytest.mark.parametrize('value', [0, -1, 1, -5, 2**63, -(2**63)-1,
                                  2**64-1, 2**64, -(2**64)-1,
                                  2**1024-1, -(2**1024)-1])
def test_bigint_native_and_wire_round_trip(value):
    validate_or_raise(SCHEMA)
    native = {'n': value, 'values': [value, -value], 'small': 4}
    encoded = codec.encode(SCHEMA, 'Box', native)
    assert codec.decode(SCHEMA, 'Box', encoded) == native
    assert codec.encode(SCHEMA, 'Box', codec.decode(SCHEMA, 'Box', encoded)) == encoded


@pytest.mark.parametrize(('value', 'hex_value'), [(0, 'c240'), (-1, 'c340'),
                                                (5, 'c24105'), (-5, 'c34104'),
                                                (256, 'c2420100'), (-257, 'c3420100')])
def test_bigint_golden(value, hex_value):
    assert cbor.dumps(cbor.Bignum(value)).hex() == hex_value
    assert cbor.loads(bytes.fromhex(hex_value)) == cbor.Bignum(value)


@pytest.mark.parametrize(('wire', 'reason'), [
    ('c2', 'Truncated'), ('c241', 'Truncated'), ('c201', 'WrongType'),
    ('c281', 'WrongType'), ('c24100', 'NonCanonicalBigInt'),
    ('c3420001', 'NonCanonicalBigInt'), ('c2580101', 'NonCanonicalInt'),
    ('c0', 'UnsupportedMajor'), ('a1c2410100', 'NonIntegerMapKey'),
    ('c24000', 'TrailingBytes')])
def test_bigint_bad_wire(wire, reason):
    with pytest.raises(cbor.DecodeError) as error:
        cbor.loads(bytes.fromhex(wire))
    assert error.value.tag == reason


def test_bigint_does_not_widen_int_or_erase_type():
    with pytest.raises(cbor.EncodeError):
        codec.encode(SCHEMA, 'Box', {'n': 0, 'values': [], 'small': 2**63})
    with pytest.raises(cbor.DecodeError, match='WrongType'):
        codec.decode(SCHEMA, 'Box', bytes.fromhex('a3010502800300'))
    with pytest.raises(TypeError):
        cbor.Bignum(True)


def test_bigint_ir_version_and_relabelled_old_ir_are_distinct():
    from taut.ir.export import schema_json
    from taut.ir.load import schema_from_json
    from taut.ir.options import smallest_encoding
    from taut.ir.model import Scalar
    exported = schema_json(SCHEMA)
    assert exported["version"] == 4
    assert schema_json(schema(Small=Msg(n=F(1, INT))))["version"] == 2
    assert smallest_encoding(SCHEMA, Scalar("bigint")) == 2
    assert schema_from_json(exported) == SCHEMA
    exported["version"] = 3
    with pytest.raises(ValueError, match="bigint requires IR version 4"):
        schema_from_json(exported)


def test_bigint_json_is_exact_even_beyond_python_decimal_digit_limit():
    native = {"n": -(2**20000), "values": [2**20000, -1, 0], "small": 4}
    text = jsoncodec.to_json(SCHEMA, "Box", native)
    assert jsoncodec.from_json(SCHEMA, "Box", text) == native
    for bad in (True, 1.5, 5, "01", "-0", "+1", "1e3", " 5"):
        with pytest.raises(TypeError):
            jsoncodec.from_json_value(SCHEMA, "Box", {"n": bad, "values": [], "small": "4"})
    with pytest.raises(TypeError):
        jsoncodec.to_json(SCHEMA, "Box", {"n": True, "values": [], "small": 4})


@pytest.mark.parametrize("supported", [False, True])
def test_typescript_toolchain_probe_executes_typed_source(monkeypatch, supported):
    from pathlib import Path
    from taut.corpus import toolchains
    monkeypatch.setattr(toolchains, "find_node", lambda: "/candidate/node")
    def probe(args):
        assert args[:2] == ["/candidate/node", "--experimental-strip-types"]
        assert ": number" in Path(args[2]).read_text()
        return supported
    monkeypatch.setattr(toolchains, "_runs", probe)
    assert toolchains.find_node_for_typescript() == ("/candidate/node" if supported else None)
