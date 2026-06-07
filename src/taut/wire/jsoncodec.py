"""IR-driven CBOR <-> JSON bridge — a canonical JSON profile for the same IR.

Point at the IR + a message name and convert between the deterministic-CBOR wire
and JSON, losslessly, with no per-message code. Conventions follow proto3's JSON
mapping (familiar and safe):

  - int (i64)        -> JSON **string**  (JSON numbers are IEEE-754 doubles, safe
                                          only to 2^53; 64-bit ints ride as text)
  - bytes            -> base64 string
  - enum             -> its member-name string
  - bool / str       -> passthrough
  - list             -> JSON array
  - message          -> JSON object keyed by field name
  - optional absent  -> JSON null

JSON is **canonical** by default (sorted keys, compact separators) so the text is
reproducible. Like proto3 JSON, this profile does NOT carry unknown/residual
fields: the CBOR wire is the forward-compat-preserving form; JSON is the legible
interchange/debug form. CBOR -> JSON -> CBOR is byte-identical for any value with
no residual.
"""

from __future__ import annotations

import base64
import json
from typing import Any

from ..ir.model import EnumRef, ListOf, MsgRef, Scalar, Schema, TypeRef
from . import codec


def _to_json(schema: Schema, tref: TypeRef, value: Any) -> Any:
    if value is None:
        return None
    if isinstance(tref, Scalar):
        if tref.kind == "int":
            return str(value)                          # i64 as string (precision)
        if tref.kind == "bytes":
            return base64.b64encode(value).decode("ascii")
        return value                                   # str / bool passthrough
    if isinstance(tref, EnumRef):
        return value                                   # member-name string
    if isinstance(tref, ListOf):
        return [_to_json(schema, tref.elem, v) for v in value]
    if isinstance(tref, MsgRef):
        msg = schema.messages[tref.name]
        return {f.name: _to_json(schema, f.type, value.get(f.name)) for f in msg.wire_fields()}
    raise TypeError(f"unknown type ref {tref!r}")


def _from_json(schema: Schema, tref: TypeRef, jv: Any) -> Any:
    if jv is None:
        return None
    if isinstance(tref, Scalar):
        if tref.kind == "int":
            return int(jv)                             # string (or number) -> int
        if tref.kind == "bytes":
            return base64.b64decode(jv)
        return jv
    if isinstance(tref, EnumRef):
        return jv
    if isinstance(tref, ListOf):
        return [_from_json(schema, tref.elem, v) for v in jv]
    if isinstance(tref, MsgRef):
        msg = schema.messages[tref.name]
        obj = jv or {}
        return {f.name: _from_json(schema, f.type, obj.get(f.name)) for f in msg.wire_fields()}
    raise TypeError(f"unknown type ref {tref!r}")


# --- native value <-> JSON-safe Python ---------------------------------------

def to_json_value(schema: Schema, message: str, value: dict[str, Any]) -> Any:
    """Native value -> JSON-safe Python (dict / list / str / bool / None)."""
    return _to_json(schema, MsgRef(message), value)


def from_json_value(schema: Schema, message: str, jv: Any) -> dict[str, Any]:
    """JSON-safe Python -> native value."""
    return _from_json(schema, MsgRef(message), jv)


# --- native value <-> JSON text ----------------------------------------------

def to_json(schema: Schema, message: str, value: dict[str, Any], *, indent: int | None = None) -> str:
    """Native value -> canonical JSON text (sorted keys; pass `indent` to pretty-print)."""
    seps = (",", ":") if indent is None else (",", ": ")
    return json.dumps(
        to_json_value(schema, message, value),
        sort_keys=True, separators=seps, indent=indent, ensure_ascii=False,
    )


def from_json(schema: Schema, message: str, text: str) -> dict[str, Any]:
    """JSON text -> native value."""
    return from_json_value(schema, message, json.loads(text))


# --- CBOR bytes <-> JSON text (the headline: point at the IR, go both ways) ---

def cbor_to_json(schema: Schema, message: str, data: bytes, *, indent: int | None = None) -> str:
    """Deterministic-CBOR bytes -> canonical JSON text."""
    return to_json(schema, message, codec.decode(schema, message, data), indent=indent)


def json_to_cbor(schema: Schema, message: str, text: str) -> bytes:
    """JSON text -> deterministic-CBOR bytes."""
    return codec.encode(schema, message, from_json(schema, message, text))
