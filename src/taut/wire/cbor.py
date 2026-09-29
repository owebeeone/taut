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

Decode is bounded (D26, TautCheckedDecode.md §3). An array or map has depth one
more than the arrays and maps around it, and one deeper than the call's depth
bound is `TooDeep{limit}`; with a length bound, longer input is `TooLarge{len,
limit}` before a byte is read. For any input bytes `loads` returns a value or
raises `DecodeError`, nothing else. This module imports nothing from taut, so it
keeps its own copies of the two depth numbers; the parity corpus pins them to
`taut.ir.options`' (TautOptions.md OPT-L1).
"""

from __future__ import annotations

import struct
from typing import Any


INT_MIN = -(1 << 63)
INT_MAX = (1 << 63) - 1

DEFAULT_MAX_DEPTH = 32    # the depth bound where none is given (CD-B1)
MAX_DEPTH_CEILING = 128   # no call applies a deeper bound (CD-B3)


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

def loads(data: bytes, *, max_depth: int = DEFAULT_MAX_DEPTH,
          max_encoded_len: int | None = None) -> Any:
    """Decode one item that fills `data`, raising `DecodeError` on any fault (CD-E5).

    `max_depth` bounds nesting: a top-level array or map has depth 1, and one at depth
    `max_depth` + 1 is `TooDeep{limit}` once its head is read. A value above the ceiling
    applies the ceiling, and `limit` names the bound applied. `max_encoded_len`, when
    given, bounds the input's length, checked first. A depth below 1 or a negative length
    is the caller's error, `ValueError`, not a `DecodeError`.
    """
    limit = _depth_bound(max_depth)
    if max_encoded_len is not None:
        _check_length_bound(max_encoded_len)
        if len(data) > max_encoded_len:
            raise DecodeError("TooLarge", len=len(data), limit=max_encoded_len)
    value, offset = _decode(data, 0, 0, limit)
    if offset != len(data):
        raise DecodeError("TrailingBytes")
    return value


def _is_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _depth_bound(max_depth: int) -> int:
    if not _is_int(max_depth):
        raise TypeError(f"max_depth must be an int, not {max_depth!r}")
    if max_depth < 1:
        raise ValueError(f"max_depth must be at least 1, not {max_depth}")
    return min(max_depth, MAX_DEPTH_CEILING)


def _check_length_bound(max_encoded_len: int) -> None:
    if not _is_int(max_encoded_len):
        raise TypeError(f"max_encoded_len must be an int or None, not {max_encoded_len!r}")
    if max_encoded_len < 0:
        raise ValueError(f"max_encoded_len must not be negative, not {max_encoded_len}")


def _take(data: bytes, offset: int, n: int) -> bytes:
    end = offset + n
    if offset < 0 or end > len(data):
        raise DecodeError("Truncated")
    return data[offset:end]


def _read_arg(data: bytes, offset: int, info: int) -> tuple[int, int]:
    if info < 24:
        return info, offset
    if info == 24:
        value, end = _take(data, offset, 1)[0], offset + 1
        fits_shorter = value < 24
    elif info == 25:
        value, end = int.from_bytes(_take(data, offset, 2), "big"), offset + 2
        fits_shorter = value <= 0xFF
    elif info == 26:
        value, end = int.from_bytes(_take(data, offset, 4), "big"), offset + 4
        fits_shorter = value <= 0xFFFF
    elif info == 27:
        value, end = int.from_bytes(_take(data, offset, 8), "big"), offset + 8
        fits_shorter = value <= 0xFFFFFFFF
    else:
        raise DecodeError("UnsupportedInfo", info=info)
    # Strict-canonical (D2): a multi-byte argument that fits a shorter width is
    # non-minimal — the canonical encoder never emits it, so reject it.
    if fits_shorter:
        raise DecodeError("NonCanonicalInt", value=value)
    return value, end


def _enter(depth: int, limit: int) -> None:
    """A container whose head is read, inside `depth` others: refuse it before its first
    item if it would sit deeper than `limit` (CD-B2)."""
    if depth >= limit:
        raise DecodeError("TooDeep", limit=limit)


def _decode(data: bytes, offset: int, depth: int, limit: int) -> tuple[Any, int]:
    """The item at `offset`, inside `depth` arrays and maps, under depth bound `limit`."""
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
        _enter(depth, limit)
        items = []
        for _ in range(n):
            item, offset = _decode(data, offset, depth + 1, limit)
            items.append(item)
        return items, offset
    if major == 5:
        n, offset = _read_arg(data, offset, info)
        _enter(depth, limit)
        result: dict[int, Any] = {}
        for _ in range(n):
            key, offset = _decode(data, offset, depth + 1, limit)
            if not isinstance(key, int) or isinstance(key, bool):
                raise DecodeError("NonIntegerMapKey")
            if key < 0:
                raise DecodeError("NegativeMapKey", key=key)
            if key in result:
                raise DecodeError("DuplicateMapKey", key=key)
            val, offset = _decode(data, offset, depth + 1, limit)
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
