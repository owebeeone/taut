"""The frozen CBOR subset, pinned to RFC 8949 Appendix A vectors. This is the
substrate oracle — every language's codec must agree with these exact bytes."""

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
    import pytest
    with pytest.raises(TypeError):
        cbor.dumps(1.5)               # no floats in the frozen subset
    with pytest.raises(ValueError):
        cbor.dumps({"k": 1})          # only integer map keys
