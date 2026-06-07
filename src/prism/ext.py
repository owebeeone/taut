"""Extension accessors — attach / read / clear a side-channel on a host message's
wire bytes, knowing only the extension's schema (never the host's).

An extension is a typed message bound to a band tag (>= shapes.BAND_START). Infra
piggybacks it on any message; the host app's schema doesn't include the tag, so
the host ignores it and preserves it (forward-compat). These operate on the
top-level CBOR map, so they work on *any* Prism message generically.
"""

from __future__ import annotations

from typing import Any

from .ir.model import Schema
from .ir.shapes import BAND_START
from .wire import cbor, codec


def _check(tag: int) -> None:
    if tag < BAND_START:
        raise ValueError(f"extension tag {tag} is below the band (< {BAND_START})")


def ext_set(schema: Schema, message_bytes: bytes, ext_message: str, tag: int, value: dict) -> bytes:
    """Strap `value` (an `ext_message`) onto the host message at `tag`."""
    _check(tag)
    top = cbor.loads(message_bytes)
    top[tag] = codec.encode_struct(schema, ext_message, value)
    return cbor.dumps(top)


def ext_get(schema: Schema, message_bytes: bytes, ext_message: str, tag: int) -> dict | Any:
    """Read the `ext_message` riding at `tag`, or None if absent."""
    _check(tag)
    top = cbor.loads(message_bytes)
    if tag not in top:
        return None
    return codec.decode_struct(schema, ext_message, top[tag])


def ext_clear(message_bytes: bytes, tag: int) -> bytes:
    """Strip the side-channel at `tag` before final delivery."""
    _check(tag)
    top = cbor.loads(message_bytes)
    top.pop(tag, None)
    return cbor.dumps(top)
