"""IR-driven codec — native value <-> CBOR bytes, driven by the schema.

This is the mechanism the IR derives, realized as a runtime interpreter over the
IR data (not emitted source). A "native value" here is a plain dict keyed by
field name (enums as their member-name string); the dataclass binding is a thin
adapter layered on top. The wire is a projection of the *tagged* subset:

  - message  -> CBOR map { field.tag : encoded-value }, transient fields skipped
  - enum     -> its integer wire value
  - list     -> CBOR array
  - scalar   -> passthrough (int/str/bytes/bool); float fields coerce value->float
  - optional -> always emitted; None -> CBOR null (deterministic; no omission)
"""

from __future__ import annotations

from typing import Any

from ..ir.model import EnumRef, ListOf, MapOf, MsgRef, Scalar, Schema, TypeRef
from . import cbor


def encode(schema: Schema, message: str, value: dict[str, Any]) -> bytes:
    return cbor.dumps(encode_struct(schema, message, value))


def decode(schema: Schema, message: str, data: bytes) -> dict[str, Any]:
    return decode_struct(schema, message, cbor.loads(data))


def encode_struct(schema: Schema, message: str, value: dict[str, Any]) -> dict[int, Any]:
    """Native dict -> CBOR-ready int-keyed structure (composable, no bytes yet)."""
    return _to_wire(schema, MsgRef(message), value)


def decode_struct(schema: Schema, message: str, struct: Any) -> dict[str, Any]:
    """CBOR-decoded int-keyed structure -> native dict."""
    return _from_wire(schema, MsgRef(message), struct)


def _to_wire(schema: Schema, tref: TypeRef, value: Any) -> Any:
    if isinstance(tref, Scalar):
        return float(value) if tref.kind == "float" else value
    if isinstance(tref, EnumRef):
        return schema.enums[tref.name].members[value]   # member name -> int
    if isinstance(tref, ListOf):
        return [_to_wire(schema, tref.elem, v) for v in value]
    if isinstance(tref, MapOf):
        # key-sorted array of {1: key, 2: value} — deterministic, like a message list
        return [
            {1: _to_wire(schema, tref.key, k), 2: _to_wire(schema, tref.value, value[k])}
            for k in sorted(value)
        ]
    if isinstance(tref, MsgRef):
        msg = schema.messages[tref.name]
        out: dict[int, Any] = {}
        for f in msg.wire_fields():
            fv = value.get(f.name)
            out[f.tag] = None if fv is None else _to_wire(schema, f.type, fv)
        # forward-compat: re-emit fields this schema doesn't know (preserved raw)
        for tag, raw in value.get("__unknown__", {}).items():
            out[int(tag)] = raw
        return out
    raise TypeError(f"unknown type ref {tref!r}")


def _from_wire(schema: Schema, tref: TypeRef, cv: Any) -> Any:
    if isinstance(tref, Scalar):
        return cv
    if isinstance(tref, EnumRef):
        members = schema.enums[tref.name].members
        reverse = {v: k for k, v in members.items()}
        return reverse[cv]                               # int -> member name
    if isinstance(tref, ListOf):
        return [_from_wire(schema, tref.elem, v) for v in cv]
    if isinstance(tref, MapOf):
        return {
            _from_wire(schema, tref.key, e[1]): _from_wire(schema, tref.value, e[2])
            for e in cv
        }
    if isinstance(tref, MsgRef):
        msg = schema.messages[tref.name]
        out: dict[str, Any] = {}
        known: set[int] = set()
        for f in msg.wire_fields():
            known.add(f.tag)
            raw = cv.get(f.tag)
            out[f.name] = None if raw is None else _from_wire(schema, f.type, raw)
        # forward-compat: capture tags this schema doesn't know (raw, preserved)
        unknown = {tag: val for tag, val in cv.items() if tag not in known}
        if unknown:
            out["__unknown__"] = unknown
        return out
    raise TypeError(f"unknown type ref {tref!r}")
