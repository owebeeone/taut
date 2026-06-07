"""Minimal deterministic CBOR codec — the frozen wire substrate.

A deliberately tiny subset of RFC 8949, in core deterministic encoding
(§4.2.1): definite-length items, shortest-form integer arguments, and map keys
emitted in ascending order. Supported major types:

  0/1  unsigned / negative integer
  2    byte string
  3    text string (utf-8)
  4    array
  5    map (integer keys only — field tags)
  7    simple: false (0xf4), true (0xf5), null (0xf6)

This is the whole vocabulary taut freezes. No floats, no tags, no indefinite
lengths, no big-nums. Other languages bind to the *same* subset; the corpus is
byte-exact across all of them. Hand-rolled (no dependency) so the bytes are
fully under our control and pinned by the RFC vectors in the tests.
"""

from __future__ import annotations

from typing import Any


# --- encode -------------------------------------------------------------------

def _head(major: int, n: int) -> bytes:
    """Major type byte + shortest-form argument for a non-negative n."""
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
        raise ValueError("trailing bytes after top-level CBOR item")
    return value


def _read_arg(data: bytes, offset: int, info: int) -> tuple[int, int]:
    if info < 24:
        return info, offset
    if info == 24:
        return data[offset], offset + 1
    if info == 25:
        return int.from_bytes(data[offset:offset + 2], "big"), offset + 2
    if info == 26:
        return int.from_bytes(data[offset:offset + 4], "big"), offset + 4
    if info == 27:
        return int.from_bytes(data[offset:offset + 8], "big"), offset + 8
    raise ValueError(f"unsupported additional-info {info} in frozen subset")


def _decode(data: bytes, offset: int) -> tuple[Any, int]:
    initial = data[offset]
    major = initial >> 5
    info = initial & 0x1F
    offset += 1

    if major == 0:
        n, offset = _read_arg(data, offset, info)
        return n, offset
    if major == 1:
        n, offset = _read_arg(data, offset, info)
        return -1 - n, offset
    if major == 2:
        n, offset = _read_arg(data, offset, info)
        return bytes(data[offset:offset + n]), offset + n
    if major == 3:
        n, offset = _read_arg(data, offset, info)
        return data[offset:offset + n].decode("utf-8"), offset + n
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
        raise ValueError(f"unsupported simple value {info}")
    raise ValueError(f"unsupported major type {major}")
