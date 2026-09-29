"""Serialize a Schema to neutral JSON — the language-neutral IR artifact.

The IR stops being Python objects and becomes a flat, portable document any
language can read (the same artifact that would be published as an OCI blob).
TypeScript/Rust/C++ bindings consume this, not the `.taut.py` source.

Version 2 (TautOptions.md OPT-I1, OPT-I2) adds options. Every level carries its
declared `options`, `{}` when none: the file at the top level, and each message,
field and enum. Each service, method and enum value (through its enum's
`member_options`) carries one too, reserved and always `{}` until its level gets
its first option. The file and each message also carry `effective`: every wire
and codegen option of the level, resolved by `options.effective_map`, which is
what readers outside Python use.
"""

from __future__ import annotations

import json
from pathlib import Path

from .model import EnumRef, ListOf, MapOf, MethodDef, MsgRef, Scalar, Schema, TypeRef
from .options import effective_map
from .shapes import SHAPES

IR_VERSION = 2


def _typeref_json(t: TypeRef) -> dict:
    if isinstance(t, Scalar):
        return {"k": "scalar", "scalar": t.kind}
    if isinstance(t, EnumRef):
        return {"k": "enum", "name": t.name}
    if isinstance(t, MsgRef):
        return {"k": "msg", "name": t.name}
    if isinstance(t, ListOf):
        return {"k": "list", "elem": _typeref_json(t.elem)}
    if isinstance(t, MapOf):
        return {"k": "map", "key": _typeref_json(t.key), "value": _typeref_json(t.value)}
    raise TypeError(f"unknown type ref {t!r}")


def _method_json(m: MethodDef) -> dict:
    # The minimal contract (D22): name, role, shape (sole discriminator), in, out.
    return {
        "name": m.name,
        "options": {},   # reserved (OPT-I2)
        "role": m.role,
        "shape": m.shape,
        "params": [{"name": pn, "type": _typeref_json(pt)} for pn, pt in m.params],
        "out": [{"slot": slot, "type": _typeref_json(t)} for slot, t in m.out],
    }


def schema_json(schema: Schema) -> dict:
    # Option maps are copied, so that editing the document leaves the frozen model alone.
    return {
        "version": IR_VERSION,
        "options": dict(schema.options),
        "effective": effective_map(schema),
        "shapes": {name: spec.to_json() for name, spec in SHAPES.items()},
        "enums": [
            {
                "name": e.name,
                "options": dict(e.options),
                "members": e.members,
                "member_options": {member: {} for member in e.members},   # reserved (OPT-I2)
            }
            for e in schema.enums.values()
        ],
        "messages": [
            {
                "name": m.name,
                "options": dict(m.options),
                "effective": effective_map(schema, message=key),
                "reserved_tags": list(m.reserved_tags),
                "reserved_names": list(m.reserved_names),
                "next_id": m.next_id,
                "fields": [
                    {
                        "name": f.name,
                        "tag": f.tag,
                        "options": dict(f.options),
                        "type": _typeref_json(f.type),
                        "optional": f.optional,
                        "transient": f.transient,
                        "merge": f.merge,
                    }
                    for f in m.fields
                ],
            }
            for key, m in schema.messages.items()
        ],
        "services": [
            {
                "name": s.name,
                "options": {},   # reserved (OPT-I2)
                "methods": [_method_json(m) for m in s.methods],
            }
            for s in schema.services.values()
        ],
        "extensions": [{"message": e.message, "tag": e.tag} for e in schema.extensions],
    }


def export_to(schema: Schema, path: str | Path) -> None:
    Path(path).write_text(json.dumps(schema_json(schema), indent=2) + "\n")
