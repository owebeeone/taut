import json
from pathlib import Path
from typing import Any

import pytest

from taut.ir.load import load_schema
from taut.ir.model import EnumRef
from taut.wire import cbor, codec


ROOT = Path(__file__).resolve().parents[2]
SCHEMA = load_schema(ROOT / "ir" / "parity_int.taut.py")
INT_VECTORS = ROOT / "corpus" / "parity" / "int.vectors.json"
MALFORMED_VECTORS = ROOT / "corpus" / "parity" / "malformed.vectors.json"


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def _intbox(value: dict[str, Any]) -> dict[str, Any]:
    return {
        "n": int(value["n"]),
        "by_id": {int(k): int(v) for k, v in value["by_id"]},
    }


def _assert_error(exc: BaseException, expect: dict[str, Any]) -> None:
    assert isinstance(exc, cbor.DecodeError | cbor.EncodeError)
    assert exc.tag == expect["tag"]
    for key, value in expect.items():
        if key == "tag":
            continue
        assert str(exc.payload[key]) == str(value)


def _baseline(vectors: list[dict]) -> list[dict]:
    # Pin the reviewed set; `lead` rows (strict-canonical D2 etc.) belong to the
    # governed `tautc parity` gate (see corpus/parity/gen_vectors.py).
    return [row for row in vectors if not row.get("lead")]


def test_python_replays_i64_int_vectors():
    for row in _baseline(_load(INT_VECTORS)["vectors"]):
        value = _intbox(row["value"])
        if row["kind"] == "round_trip":
            wire = codec.encode(SCHEMA, row["message"], value)
            assert wire.hex() == row["cbor"], row["name"]
            assert codec.decode(SCHEMA, row["message"], wire) == value, row["name"]
        elif row["kind"] == "encode_fail":
            with pytest.raises(codec.EncodeError) as got:
                codec.encode(SCHEMA, row["message"], value)
            _assert_error(got.value, row["expect"])
        else:
            raise AssertionError(f"unknown int vector kind {row['kind']!r}")


def test_python_replays_malformed_vectors():
    for row in _baseline(_load(MALFORMED_VECTORS)["vectors"]):
        wire = bytes.fromhex(row["bytes"])
        with pytest.raises(codec.DecodeError) as got:
            if row["stage"] == "raw_decode":
                cbor.loads(wire)
            elif row["stage"] == "from_cbor":
                codec.decode(SCHEMA, row["schema"], wire)
            elif row["stage"] == "from_wire":
                codec._from_wire(SCHEMA, EnumRef(row["schema"]), cbor.loads(wire), strict=True)
            else:
                raise AssertionError(f"unknown malformed stage {row['stage']!r}")
        _assert_error(got.value, row["expect"])
