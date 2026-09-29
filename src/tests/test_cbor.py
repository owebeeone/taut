"""The frozen CBOR subset, pinned to RFC 8949 Appendix A vectors (ints, strings,
bytes, arrays, maps, simples) plus shortest-form floats. This is the substrate
oracle — every language's codec must agree with these exact bytes."""

import inspect
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


# --- decode bounds: depth and length (D26, TautCheckedDecode.md §3, CD-E5) --------------------
# The raw decoder's own contract. Rows B1-B30 and the typed entry points are in test_bounds.py,
# which also pins these constants to taut.ir.options' copies.

def _nest(opener: str, count: int, leaf: str) -> bytes:
    """`count` copies of `opener` (hex), then `leaf`: `_nest("81", 31, "80")` is 32 arrays."""
    return bytes.fromhex(opener * count + leaf)


def _refusal(data: bytes, **limits) -> tuple[str, dict]:
    with pytest.raises(cbor.DecodeError) as got:
        cbor.loads(data, **limits)
    assert type(got.value) is cbor.DecodeError
    return got.value.tag, got.value.payload


def _accepts(data: bytes, **limits) -> bool:
    return cbor.dumps(cbor.loads(data, **limits)) == data


def test_bounds_constants_and_signature():
    assert cbor.DEFAULT_MAX_DEPTH == 32
    assert cbor.MAX_DEPTH_CEILING == 128
    params = inspect.signature(cbor.loads).parameters
    assert list(params) == ["data", "max_depth", "max_encoded_len"]
    assert params["max_depth"].kind is inspect.Parameter.KEYWORD_ONLY
    assert params["max_depth"].default == cbor.DEFAULT_MAX_DEPTH
    assert params["max_encoded_len"].kind is inspect.Parameter.KEYWORD_ONLY
    assert params["max_encoded_len"].default is None


@pytest.mark.parametrize("opener, leaf", [
    ("81", "80"), ("a100", "a0"), ("81", "a0"), ("a100", "80"),
])
def test_default_depth_takes_32_containers_and_refuses_the_33rd(opener, leaf):
    assert _accepts(_nest(opener, 31, leaf))
    assert _accepts(_nest(opener, 32, "00"))                 # a scalar adds no depth
    assert _refusal(_nest(opener, 32, leaf)) == ("TooDeep", {"limit": 32})


def test_arrays_and_maps_count_alike():
    assert _accepts(_nest("81a100", 16, "00"))               # 32 containers, alternating
    assert _refusal(_nest("81a100", 16, "80")) == ("TooDeep", {"limit": 32})
    assert _refusal(_nest("81a100", 16, "a0")) == ("TooDeep", {"limit": 32})


def test_a_top_level_container_has_depth_1():
    for accepted in ("00", "6161", "80", "a0", "8100", "a10000", "820102"):
        assert _accepts(bytes.fromhex(accepted), max_depth=1), accepted
    for refused in ("8180", "81a0", "a10080", "a100a0", "820180"):
        assert _refusal(bytes.fromhex(refused), max_depth=1) == ("TooDeep", {"limit": 1}), refused


def test_a_map_key_is_an_item_of_its_map():
    # The key item is read first, depth included, then checked (CD-E5 step 3).
    assert _refusal(bytes.fromhex("a18000"), max_depth=1) == ("TooDeep", {"limit": 1})
    assert _refusal(bytes.fromhex("a18000"), max_depth=2) == ("NonIntegerMapKey", {})


@pytest.mark.parametrize("max_depth", [1, 2, 5, 31, 33, 64, 127, 128])
def test_a_depth_argument_applies_as_given(max_depth):
    assert _accepts(_nest("81", max_depth - 1, "80"), max_depth=max_depth)
    assert _refusal(_nest("81", max_depth, "80"), max_depth=max_depth) == (
        "TooDeep", {"limit": max_depth})


@pytest.mark.parametrize("max_depth", [129, 1000, 2**31, 2**64])
def test_a_depth_argument_above_the_ceiling_applies_the_ceiling(max_depth):
    assert _accepts(_nest("81", 127, "80"), max_depth=max_depth)
    assert _refusal(_nest("81", 128, "80"), max_depth=max_depth) == ("TooDeep", {"limit": 128})


def test_depth_is_checked_once_the_head_is_complete():
    # CD-B2: before the first item, so missing items do not matter...
    assert _refusal(_nest("81", 33, "")) == ("TooDeep", {"limit": 32})
    assert _refusal(_nest("a100", 32, "a1")) == ("TooDeep", {"limit": 32})
    assert _refusal(_nest("81", 32, "9bffffffffffffffff")) == ("TooDeep", {"limit": 32})
    assert _refusal(_nest("81", 32, "bbffffffffffffffff")) == ("TooDeep", {"limit": 32})
    # ...but a torn head is Truncated, and the head's own faults come first.
    for torn in ("98", "9900", "9a000000", "9b00", "b8", "bb00000000000000"):
        assert _refusal(_nest("81", 32, torn)) == ("Truncated", {}), torn
    assert _refusal(_nest("81", 32, "9800")) == ("NonCanonicalInt", {"value": 0})
    assert _refusal(_nest("81", 32, "9c")) == ("UnsupportedInfo", {"info": 28})
    assert _refusal(_nest("81", 32, "bf")) == ("UnsupportedInfo", {"info": 31})


@pytest.mark.parametrize("opener, leaf", [("81", "80"), ("a100", "a0"), ("81a100", "80")])
def test_deep_input_is_too_deep_not_recursion_error(opener, leaf):
    data = _nest(opener, 100_000, leaf)
    assert _refusal(data) == ("TooDeep", {"limit": 32})
    assert _refusal(data, max_depth=128) == ("TooDeep", {"limit": 128})
    assert _refusal(data, max_depth=10**9) == ("TooDeep", {"limit": 128})


def test_length_bound():
    data = bytes.fromhex("83010203")
    assert _accepts(data, max_encoded_len=4)                 # exactly at the bound
    assert _accepts(data, max_encoded_len=2**40)             # any length may be passed
    assert _refusal(data, max_encoded_len=3) == ("TooLarge", {"len": 4, "limit": 3})
    big = cbor.dumps(b"x" * 100_000)
    assert _accepts(big)                                     # no bound unless one is passed
    assert _accepts(big, max_encoded_len=None)
    assert _refusal(big, max_encoded_len=len(big) - 1) == (
        "TooLarge", {"len": len(big), "limit": len(big) - 1})


def test_length_is_checked_before_any_byte_is_read():
    assert _refusal(bytes.fromhex("c0c0c0c0"), max_encoded_len=3) == (
        "TooLarge", {"len": 4, "limit": 3})
    assert _refusal(_nest("81", 40, "80"), max_encoded_len=10) == (
        "TooLarge", {"len": 41, "limit": 10})
    assert _refusal(bytes.fromhex("0000"), max_encoded_len=1) == (
        "TooLarge", {"len": 2, "limit": 1})


def test_a_zero_length_bound():
    assert _refusal(b"", max_encoded_len=0) == ("Truncated", {})
    assert _refusal(b"\x00", max_encoded_len=0) == ("TooLarge", {"len": 1, "limit": 0})


@pytest.mark.parametrize("limits", [
    {"max_depth": 0}, {"max_depth": -1}, {"max_depth": -(2**64)},
    {"max_encoded_len": -1}, {"max_encoded_len": -(2**64)},
])
def test_an_out_of_range_argument_is_a_caller_error(limits):
    # ValueError itself, never a DecodeError (its subclass), and before any byte is read.
    for data in (b"", b"\x00", bytes.fromhex("c0c0c0c0")):
        with pytest.raises(ValueError) as got:
            cbor.loads(data, **limits)
        assert type(got.value) is ValueError, data


@pytest.mark.parametrize("limits", [
    {"max_depth": True}, {"max_depth": 32.0}, {"max_depth": "32"}, {"max_depth": None},
    {"max_encoded_len": False}, {"max_encoded_len": 4.0}, {"max_encoded_len": "4"},
])
def test_an_argument_of_the_wrong_type_is_a_caller_error(limits):
    with pytest.raises(TypeError):
        cbor.loads(b"\x00", **limits)


def test_bounds_are_keyword_only():
    with pytest.raises(TypeError):
        cbor.loads(b"\x00", 32)  # type: ignore[misc]
