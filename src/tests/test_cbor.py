"""The frozen CBOR subset, pinned to RFC 8949 Appendix A vectors (ints, strings,
bytes, arrays, maps, simples) plus shortest-form floats. This is the substrate
oracle — every language's codec must agree with these exact bytes."""

import math
import struct

import pytest

from taut.wire import cbor

VECTORS = [
    (0, "00"), (1, "01"), (10, "0a"), (23, "17"), (24, "1818"), (100, "1864"),
    (1000, "1903e8"), (1000000, "1a000f4240"),
    (-1, "20"), (-100, "3863"), (-1000, "3903e7"),
    (b"", "40"), (b"\x01\x02\x03\x04", "4401020304"),
    ("", "60"), ("a", "6161"), ("IETF", "6449455446"),
    (False, "f4"), (True, "f5"), (None, "f6"),
    ([], "80"), ([1, 2, 3], "83010203"), ([1, [2, 3]], "8201820203"),
]


def test_encode_matches_rfc_vectors():
    for value, expected in VECTORS:
        assert cbor.dumps(value).hex() == expected, value


def test_decode_roundtrips():
    for value, expected in VECTORS:
        assert cbor.loads(bytes.fromhex(expected)) == value


def test_map_keys_emitted_in_ascending_order():
    # deterministic: keys sorted regardless of insertion order
    assert cbor.dumps({3: 1, 1: 2, 2: 3}).hex() == "a3010202030301"


def test_rejects_out_of_subset():
    with pytest.raises(TypeError):
        cbor.dumps(1 + 2j)            # complex: still out of the subset
    with pytest.raises(ValueError):
        cbor.dumps({"k": 1})          # only integer map keys


# --- floats: shortest-form (preferred serialization, RFC 8949 §4.2.1) ---------
# Smallest of half/single/double that round-trips the exact value; NaN canonical
# to F9 7E00; -0.0 preserved. Hex independently pinned from IEEE-754 via `struct`.
FLOAT_VECTORS = [
    (0.0, "f90000"), (-0.0, "f98000"),
    (1.0, "f93c00"), (-1.0, "f9bc00"), (1.5, "f93e00"),
    (65504.0, "f97bff"),                        # max half-normal
    (2.0 ** -24, "f90001"),                     # min half-subnormal
    (2.0 ** -14, "f90400"),                     # min half-normal
    (100000.0, "fa47c35000"),                   # single (not half) — RFC App. A
    (3.4028234663852886e+38, "fa7f7fffff"),     # max single
    (2.0 ** -149, "fa00000001"),                # min single-subnormal
    (1.00048828125, "fa3f801000"),              # near-miss: not half, exact single
    (0.1, "fb3fb999999999999a"),                # double only
    (1.1, "fb3ff199999999999a"),
    (3.141592653589793, "fb400921fb54442d18"),
    (5e-324, "fb0000000000000001"),             # min double-subnormal
    (1.7976931348623157e+308, "fb7fefffffffffffff"),
    (float("inf"), "f97c00"), (float("-inf"), "f9fc00"),
]


def test_float_encode_matches_vectors():
    for value, expected in FLOAT_VECTORS:
        assert cbor.dumps(value).hex() == expected, value


def test_float_decode_bit_exact():
    for value, expected in FLOAT_VECTORS:
        got = cbor.loads(bytes.fromhex(expected))
        # bit-compare so -0.0 != +0.0 (which would compare equal under ==)
        assert struct.pack(">d", got) == struct.pack(">d", value), value


def test_float_shortest_width():
    def fits(value, fmt):
        try:
            return struct.unpack(fmt, struct.pack(fmt, value))[0] == value
        except OverflowError:
            return False
    for value, expected in FLOAT_VECTORS:
        head = bytes.fromhex(expected)[0]
        width = {0xF9: "half", 0xFA: "single", 0xFB: "double"}[head]
        want = "half" if fits(value, ">e") else "single" if fits(value, ">f") else "double"
        assert width == want, (value, width, want)


def test_float_nan_canonical():
    for bits in (0x7FF8000000000000, 0x7FF0000000000001, 0xFFF8000000000000, 0x7FFFFFFFFFFFFFFF):
        v = struct.unpack(">d", bits.to_bytes(8, "big"))[0]
        assert math.isnan(v)
        assert cbor.dumps(v).hex() == "f97e00", hex(bits)
    assert math.isnan(cbor.loads(bytes.fromhex("f97e00")))


def _assert_roundtrip(v):
    enc = cbor.dumps(v)
    dec = cbor.loads(enc)
    assert struct.pack(">d", dec) == struct.pack(">d", v), v
    assert cbor.dumps(dec) == enc, v             # shortest form is idempotent


def test_float_roundtrip_idempotent():
    extra = [0.5, 2.0, -1.5, 1.0 / 3.0, math.e, 1e16, 1e-16, 1e300, -(2.0 ** -149)]
    for value, _ in FLOAT_VECTORS:
        _assert_roundtrip(value)
    for v in extra:
        _assert_roundtrip(v)


def test_float_decode_accepts_all_widths():
    # width-lenient decode (rule D): the same value as half/single/double all read
    # back equal, even though the encoder only ever emits the shortest (half here).
    for hx in ("f93c00", "fa3f800000", "fb3ff0000000000000"):
        assert cbor.loads(bytes.fromhex(hx)) == 1.0, hx
