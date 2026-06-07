"""Load an authored `.taut.py` IR module by path and return its SCHEMA.

The authored IR uses an unusual double extension (`griplab.taut.py`) and is not
a normal import target, so it is loaded explicitly here — appropriate, since the
loader is exactly the thing that consumes authored intent.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

from .model import (
    EnumDef,
    EnumRef,
    ExtensionDef,
    FieldDef,
    ListOf,
    MessageDef,
    MethodDef,
    MsgRef,
    Scalar,
    Schema,
    ServiceDef,
    TypeRef,
)


def load_schema(path: str | Path) -> Schema:
    path = Path(path)
    spec = importlib.util.spec_from_file_location("_taut_ir_module", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load IR module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    schema = getattr(module, "SCHEMA", None)
    if not isinstance(schema, Schema):
        raise ValueError(f"{path} must define SCHEMA: Schema")
    return schema


def _typeref_from_json(d: dict) -> TypeRef:
    k = d["k"]
    if k == "scalar":
        return Scalar(d["scalar"])
    if k == "enum":
        return EnumRef(d["name"])
    if k == "msg":
        return MsgRef(d["name"])
    if k == "list":
        return ListOf(_typeref_from_json(d["elem"]))
    raise ValueError(f"unknown type ref {d!r}")


def schema_from_json(data: dict) -> Schema:
    """Inverse of export.schema_json — load a Schema from the neutral IR JSON."""
    enums = {e["name"]: EnumDef(e["name"], dict(e["members"])) for e in data["enums"]}
    messages = {}
    for m in data["messages"]:
        fields = tuple(
            FieldDef(f["name"], f["tag"], _typeref_from_json(f["type"]), f["optional"], f["transient"], f.get("merge"))
            for f in m["fields"]
        )
        messages[m["name"]] = MessageDef(
            m["name"], fields,
            tuple(m.get("reserved_tags", [])),
            tuple(m.get("reserved_names", [])),
            m.get("next_id"),
        )
    services = {}
    for s in data.get("services", []):
        methods = tuple(
            MethodDef(
                name=m["name"],
                role=m["role"],
                shape=m["shape"],
                out=tuple((o["slot"], _typeref_from_json(o["type"])) for o in m["out"]),
                params=tuple((p["name"], _typeref_from_json(p["type"])) for p in m["params"]),
            )
            for m in s["methods"]
        )
        services[s["name"]] = ServiceDef(s["name"], methods)
    extensions = tuple(ExtensionDef(e["message"], e["tag"]) for e in data.get("extensions", []))
    return Schema(enums=enums, messages=messages, services=services, extensions=extensions)
