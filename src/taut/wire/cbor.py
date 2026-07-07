"""Minimal deterministic CBOR codec — the frozen wire substrate.

A deliberately tiny subset of RFC 8949, in core deterministic encoding
(§4.2.1): definite-length items, shortest-form integer arguments, and map keys
emitted in ascending order. Supported major types:

  0/1  unsigned / negative integer
  2    byte string
  3    text string (utf-8)
  4    array
  5    map (integer keys only — field tags)
  7    simple: false (0xf4), true (0xf5), null (0xf6);
       float: half (0xf9) / single (0xfa) / double (0xfb)

This is the whole vocabulary taut freezes. Floats use **shortest-form**
(preferred serialization, §4.2.1): the smallest of half/single/double that
round-trips the value exactly, NaN canonical to F9 7E00, -0.0 preserved. No tags,
no indefinite lengths, no big-nums. Other languages bind to the *same* subset; the
corpus is byte-exact across all of them. Hand-rolled (no dependency) so the bytes
are fully under our control and pinned by the RFC vectors in the tests.
"""

from __future__ import annotations

import struct
from typing import Any


INT_MIN = -(1 << 63)
INT_MAX = (1 << 63) - 1


class DecodeError(ValueError):
    """Typed fail-closed CBOR decode error."""

    def __init__(self, tag: str, **payload: Any) -> None:
        self.tag = tag
        self.payload = payload
        for key, value in payload.items():
            setattr(self, key, value)
        detail = f": {payload}" if payload else ""
        super().__init__(f"{tag}{detail}")


class EncodeError(ValueError):
    """Typed fail-closed CBOR encode error."""

    def __init__(self, tag: str, **payload: Any) -> None:
        self.tag = tag
        self.payload = payload
        for key, value in payload.items():
            setattr(self, key, value)
        detail = f": {payload}" if payload else ""
        super().__init__(f"{tag}{detail}")


# --- encode -------------------------------------------------------------------

def _head(major: int, n: int) -> bytes:
    """Major type byte + shortest-form argument for a non-negative n."""
    if n > INT_MAX:
        raise EncodeError("IntOutOfSubset", value=n)
    mt = major << 5
    if n < 24:
        return bytes([mt | n])
    if n < 0x100:
        return bytes([mt | 24, n])
    if n < 0x10000:
        return bytes([mt | 25]) + n.to_bytes(2, "big")
    if n < 0x100000000:
        return bytes([mt | 26]) + n.to_bytes(4, "big")
    if n < 0x10000000000000000:
        return bytes([mt | 27]) + n.to_bytes(8, "big")
    raise ValueError("integer too large for the frozen CBOR subset")


def _float_bytes(value: float) -> bytes:
    """Shortest-form IEEE-754: the smallest of half/single/double that round-trips
    `value` exactly; NaN canonical to the half quiet-NaN F9 7E00 (§4.2.1).

    Python delegates half/single narrowing to `struct`; targets without native
    float16 hand-roll round-to-nearest-even narrowing — `corpus/float_vectors.json`
    is the byte-exact contract (subnormal/boundary/near-miss rows included)."""
    if value != value:                        # NaN — canonical, before any width test
        return b"\xf9\x7e\x00"
    try:
        h = struct.pack(">e", value)          # half
        if struct.unpack(">e", h)[0] == value:
            return b"\xf9" + h
    except OverflowError:
        pass
    try:
        s = struct.pack(">f", value)          # single
        if struct.unpack(">f", s)[0] == value:
            return b"\xfa" + s
    except OverflowError:
        pass
    return b"\xfb" + struct.pack(">d", value)  # double


def dumps(value: Any) -> bytes:
    out = bytearray()
    _encode(value, out)
    return bytes(out)


def _encode(value: Any, out: bytearray) -> None:
    # bool before int: bool is a subclass of int in Python.
    if value is None:
        out.append(0xF6)
    elif value is True:
        out.append(0xF5)
    elif value is False:
        out.append(0xF4)
    elif isinstance(value, int):
        if value >= 0:
            out += _head(0, value)
        else:
            out += _head(1, -1 - value)
    elif isinstance(value, float):
        out += _float_bytes(value)
    elif isinstance(value, (bytes, bytearray)):
        out += _head(2, len(value))
        out += bytes(value)
    elif isinstance(value, str):
        encoded = value.encode("utf-8")
        out += _head(3, len(encoded))
        out += encoded
    elif isinstance(value, list):
        out += _head(4, len(value))
        for item in value:
            _encode(item, out)
    elif isinstance(value, dict):
        # deterministic: integer keys in ascending order
        keys = sorted(value.keys())
        if not all(isinstance(k, int) and k >= 0 for k in keys):
            raise ValueError("frozen subset allows only non-negative integer map keys")
        out += _head(5, len(keys))
        for k in keys:
            out += _head(0, k)
            _encode(value[k], out)
    else:
        raise TypeError(f"type {type(value).__name__} is not in the frozen CBOR subset")


# --- decode -------------------------------------------------------------------

def loads(data: bytes) -> Any:
    value, offset = _decode(data, 0)
    if offset != len(data):
        raise DecodeError("TrailingBytes")
    return value


def _take(data: bytes, offset: int, n: int) -> bytes:
    end = offset + n
    if offset < 0 or end > len(data):
        raise DecodeError("Truncated")
    return data[offset:end]


def _read_arg(data: bytes, offset: int, info: int) -> tuple[int, int]:
    if info < 24:
        return info, offset
    if info == 24:
        return _take(data, offset, 1)[0], offset + 1
    if info == 25:
        return int.from_bytes(_take(data, offset, 2), "big"), offset + 2
    if info == 26:
        return int.from_bytes(_take(data, offset, 4), "big"), offset + 4
    if info == 27:
        return int.from_bytes(_take(data, offset, 8), "big"), offset + 8
    raise DecodeError("UnsupportedInfo", info=info)


def _decode(data: bytes, offset: int) -> tuple[Any, int]:
    initial = _take(data, offset, 1)[0]
    major = initial >> 5
    info = initial & 0x1F
    offset += 1

    if major == 0:
        n, offset = _read_arg(data, offset, info)
        if n > INT_MAX:
            raise DecodeError("IntOverflow", value=n)
        return n, offset
    if major == 1:
        n, offset = _read_arg(data, offset, info)
        if n > INT_MAX:
            raise DecodeError("IntOverflow", value=-1 - n)
        return -1 - n, offset
    if major == 2:
        n, offset = _read_arg(data, offset, info)
        return _take(data, offset, n), offset + n
    if major == 3:
        n, offset = _read_arg(data, offset, info)
        raw = _take(data, offset, n)
        try:
            return raw.decode("utf-8"), offset + n
        except UnicodeDecodeError as exc:
            raise DecodeError("InvalidUtf8") from exc
    if major == 4:
        n, offset = _read_arg(data, offset, info)
        items = []
        for _ in range(n):
            item, offset = _decode(data, offset)
            items.append(item)
        return items, offset
    if major == 5:
        n, offset = _read_arg(data, offset, info)
        result: dict[int, Any] = {}
        for _ in range(n):
            key, offset = _decode(data, offset)
            if not isinstance(key, int) or isinstance(key, bool):
                raise DecodeError("NonIntegerMapKey")
            if key in result:
                raise DecodeError("DuplicateMapKey", key=key)
            val, offset = _decode(data, offset)
            result[key] = val
        return result, offset
    if major == 7:
        if info == 20:
            return False, offset
        if info == 21:
            return True, offset
        if info == 22:
            return None, offset
        if info == 25:
            return struct.unpack(">e", _take(data, offset, 2))[0], offset + 2
        if info == 26:
            return struct.unpack(">f", _take(data, offset, 4))[0], offset + 4
        if info == 27:
            return struct.unpack(">d", _take(data, offset, 8))[0], offset + 8
        raise DecodeError("UnsupportedInfo", info=info)
    raise DecodeError("UnsupportedMajor", major=major)
