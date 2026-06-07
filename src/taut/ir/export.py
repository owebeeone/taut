"""Serialize a Schema to neutral JSON — the language-neutral IR artifact.

The IR stops being Python objects and becomes a flat, portable document any
language can read (the same artifact that would be published as an OCI blob).
TypeScript/Rust/C++ bindings consume this, not the `.taut.py` source.
"""

from __future__ import annotations

import json
from pathlib import Path

from .model import EnumRef, ListOf, MethodDef, MsgRef, Scalar, Schema, TypeRef
from .shapes import SHAPES


def _typeref_json(t: TypeRef) -> dict:
    if isinstance(t, Scalar):
        return {"k": "scalar", "scalar": t.kind}
    if isinstance(t, EnumRef):
        return {"k": "enum", "name": t.name}
    if isinstance(t, MsgRef):
        return {"k": "msg", "name": t.name}
    if isinstance(t, ListOf):
        return {"k": "list", "elem": _typeref_json(t.elem)}
    raise TypeError(f"unknown type ref {t!r}")


def _method_json(m: MethodDef) -> dict:
    return {
        "name": m.name,
        "kind": m.kind,
        "role": m.role,
        "params": [{"name": pn, "type": _typeref_json(pt)} for pn, pt in m.params],
        "output": _typeref_json(m.output) if m.output is not None else None,
        "shape": m.shape,
        "events": [{"event": en, "type": _typeref_json(et)} for en, et in m.events],
    }


def schema_json(schema: Schema) -> dict:
    return {
        "version": 1,
        "shapes": {name: {**spec, "events": sorted(spec["events"])} for name, spec in SHAPES.items()},
        "enums": [
            {"name": e.name, "members": e.members}
            for e in schema.enums.values()
        ],
        "messages": [
            {
                "name": m.name,
                "reserved_tags": list(m.reserved_tags),
                "reserved_names": list(m.reserved_names),
                "next_id": m.next_id,
                "fields": [
                    {
                        "name": f.name,
                        "tag": f.tag,
                        "type": _typeref_json(f.type),
                        "optional": f.optional,
                        "transient": f.transient,
                        "merge": f.merge,
                    }
                    for f in m.fields
                ],
            }
            for m in schema.messages.values()
        ],
        "services": [
            {"name": s.name, "methods": [_method_json(m) for m in s.methods]}
            for s in schema.services.values()
        ],
        "extensions": [{"message": e.message, "tag": e.tag} for e in schema.extensions],
    }


def export_to(schema: Schema, path: str | Path) -> None:
    Path(path).write_text(json.dumps(schema_json(schema), indent=2) + "\n")
