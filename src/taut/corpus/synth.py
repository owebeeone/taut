"""Deterministic coverage-value synthesis from an IR.

For each message, build one native value that exercises every wire field's type —
scalars (incl. negative / multibyte ints), enums, lists, bytes, nested messages —
deterministically: same IR => same values => same golden bytes (stable, diffable).
This is what lets the conformance kit derive a corpus from any IR with zero
hand-authored reference values (the thing razel had to write by hand).
"""

from __future__ import annotations

from typing import Any

from ..ir.model import EnumRef, ListOf, MsgRef, Scalar, Schema, TypeRef

# Per-field int samples, picked by field tag — covers small, negative, multibyte,
# and zero across a message without any randomness.
_INTS = (42, -7, 300, 0)


def _synth(schema: Schema, tref: TypeRef, seed: int, stack: tuple[str, ...]) -> Any:
    if isinstance(tref, Scalar):
        if tref.kind == "int":
            return _INTS[seed % len(_INTS)]
        if tref.kind == "str":
            return f"s{seed}"
        if tref.kind == "bytes":
            return bytes((seed & 0xFF, 0x01, 0x02))
        if tref.kind == "bool":
            return seed % 2 == 0
        raise TypeError(f"unknown scalar {tref.kind!r}")
    if isinstance(tref, EnumRef):
        members = list(schema.enums[tref.name].members)
        return members[seed % len(members)]
    if isinstance(tref, ListOf):
        return [_synth(schema, tref.elem, seed, stack)]
    if isinstance(tref, MsgRef):
        if tref.name in stack:            # break a reference cycle -> null on the wire
            return None
        return synth_message(schema, tref.name, stack)
    raise TypeError(f"unknown type ref {tref!r}")


def synth_message(schema: Schema, name: str, _stack: tuple[str, ...] = ()) -> dict[str, Any]:
    """One deterministic coverage value (native dict) for message `name`."""
    stack = _stack + (name,)
    msg = schema.messages[name]
    return {f.name: _synth(schema, f.type, f.tag, stack) for f in msg.wire_fields()}


def synth_values(schema: Schema) -> dict[str, tuple[str, Any]]:
    """`name -> (message, native value)`, one coverage value per message in the IR."""
    return {name: (name, synth_message(schema, name)) for name in schema.messages}
