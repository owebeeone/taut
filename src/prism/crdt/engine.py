"""CRDT convergence — the pluggable engine slot, plus a reference for the merge
types whose semantics are trivial enough to *be* the reference (lww, counter).

Per the build prompt: the wire + API surface support CRDT from day one, but a
working convergence engine is NOT a per-platform deliverable — it's a slot you
bind to Automerge/Yjs. So:

  - `CrdtEngine` is the slot (a Protocol): local_apply / merge / materialize / snapshot.
  - `ReferenceDoc` implements it for `lww` (last-writer-wins register) and
    `counter` (PN-counter) — these are commutative/idempotent by construction
    (LWW = max by (seq, actor); counter = sum of distinct per-(actor,seq) deltas),
    so the "engine" is arithmetic, not a real convergence engine.
  - `text` / sequence / set merges need a real engine (RGA/Yjs/Automerge) and are
    out of v1 — declaring such a field and using ReferenceDoc raises EngineNotBound.

Ops are the neutral dicts the codec produces:
  {"doc","actor","seq","field","value"}  (value is the native field value here;
  on the wire it is CBOR bytes — see CrdtOp / op_to_wire / op_from_wire).
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from ..ir.model import Schema
from ..wire import cbor, codec


class EngineNotBound(Exception):
    """A field's merge type has no bound convergence engine (e.g. text)."""


@runtime_checkable
class CrdtEngine(Protocol):
    def local_apply(self, field: int, value: Any) -> dict: ...
    def merge(self, op: dict) -> bool: ...
    def materialize(self) -> dict: ...
    def snapshot(self) -> dict: ...


_SUPPORTED = {"lww", "counter"}


class ReferenceDoc:
    """Reference engine for lww + counter docs."""

    def __init__(self, actor: str, schema: Schema, doc: str = "Board") -> None:
        self._actor = actor
        self._doc = doc
        self._fields = {f.tag: f for f in schema.messages[doc].fields if f.merge}
        for f in self._fields.values():
            if f.merge not in _SUPPORTED:
                raise EngineNotBound(f"{doc}.{f.name}: merge {f.merge!r} needs an external engine")
        self._seq = 0
        self._applied: set[tuple[str, int]] = set()       # (actor, seq) seen — dedup
        self._lww_stamp: dict[int, tuple[int, str]] = {}   # field -> winning (seq, actor)
        self._values: dict[int, Any] = {}
        self._log: list[dict] = []

    def local_apply(self, field: int, value: Any) -> dict:
        self._seq += 1
        op = {"doc": self._doc, "actor": self._actor, "seq": self._seq, "field": field, "value": value}
        self.merge(op)
        return op

    def merge(self, op: dict) -> bool:
        key = (op["actor"], op["seq"])
        if key in self._applied:
            return False                                   # idempotent: already applied
        self._applied.add(key)
        self._log.append(op)
        f = self._fields[op["field"]]
        if f.merge == "counter":
            self._values[op["field"]] = self._values.get(op["field"], 0) + op["value"]
        else:  # lww
            stamp = (op["seq"], op["actor"])
            if stamp > self._lww_stamp.get(op["field"], (0, "")):
                self._lww_stamp[op["field"]] = stamp
                self._values[op["field"]] = op["value"]
        return True

    def materialize(self) -> dict:
        out = {}
        for tag, f in self._fields.items():
            out[f.name] = self._values.get(tag, 0 if f.merge == "counter" else "")
        return out

    def snapshot(self) -> dict:
        version: dict[str, int] = {}
        for actor, seq in self._applied:
            version[actor] = max(version.get(actor, 0), seq)
        return {
            "doc": self._doc,
            "ops": list(self._log),
            "version": [{"actor": a, "seq": s} for a, s in sorted(version.items())],
        }


# --- op <-> wire (CrdtOp) -----------------------------------------------------

def op_to_wire(schema: Schema, op: dict, doc: str = "Board") -> dict:
    """Native op -> CrdtOp wire dict (value encoded to CBOR bytes per field type)."""
    field = next(f for f in schema.messages[doc].fields if f.tag == op["field"])
    value_bytes = cbor.dumps(codec.encode_struct(schema, doc, {field.name: op["value"]})[field.tag])
    return {"doc": op["doc"], "actor": op["actor"], "seq": op["seq"], "field": op["field"], "value": value_bytes}


def op_from_wire(schema: Schema, wire: dict, doc: str = "Board") -> dict:
    field = next(f for f in schema.messages[doc].fields if f.tag == wire["field"])
    value = codec.decode_struct(schema, doc, {field.tag: cbor.loads(wire["value"])})[field.name]
    return {"doc": wire["doc"], "actor": wire["actor"], "seq": wire["seq"], "field": wire["field"], "value": value}
