"""Python projection of native IR, with one shared runtime owner."""
from __future__ import annotations

import hashlib
import json
import keyword


def field_attribute(name):
    """Python keywords have an explicit, recorded trailing-underscore projection."""
    return name + "_" if keyword.iskeyword(name) else name

from ..contracts import GENERATOR_BUILD, RUNTIME_OWNER
from ..ir.export import schema_json


def _freeze_spec(t):
    from ..facts import ListOf, MapOf, MsgRef
    if isinstance(t, ListOf):
        return ("list", _freeze_spec(t.elem))
    if isinstance(t, MapOf):
        return ("map", _freeze_spec(t.value))
    return ("message",) if isinstance(t, MsgRef) else ("scalar",)


def emit_types(schema, *, validation=False, external_types=None, identity=None, python_records="stdlib"):
    if python_records not in ("stdlib", "yidl"):
        raise ValueError("python_records must be stdlib or yidl")
    yidl_records = python_records == "yidl"
    required_capabilities = ("descriptors.v1", "codec.v1", "oneof.v1")
    if yidl_records:
        required_capabilities += ("records.yidl.v1",)
    from .scaffold import _py_ty, python_name_clashes, PYTHON_RESERVED_TYPE_NAMES
    external_types = dict(external_types or {})
    unknown = set(external_types) - (set(schema.messages) | set(schema.enums))
    if unknown:
        raise ValueError(f"unknown Python external types {sorted(unknown)}")
    collisions = python_name_clashes(schema)
    for msg in schema.messages.values():
        attrs = [field_attribute(f.name) for f in msg.fields if not f.virtual]
        if len(attrs) != len(set(attrs)):
            collisions.append((msg.name, "fields", "schema fields collide after Python keyword escaping"))
        for f in msg.fields:
            if f.name.startswith("__"):
                collisions.append((f"{msg.name}.{f.name}", "field", "Python private-name mangling is unsupported"))
                continue
            if f.name in ("DESCRIPTOR", "__taut_binding__") or f.name.startswith("_taut_") or (
                    validation and f.name in ("validate", "is_valid")):
                collisions.append((f"{msg.name}.{f.name}", "field", "generated descriptor/validation symbol"))
    reserved_types = set(PYTHON_RESERVED_TYPE_NAMES) | {
        "SCHEMA", "SCHEMA_DESCRIPTOR", "BINDING", "int", "str", "bool", "float", "bytes", "list", "dict"}
    for name in set(schema.messages) | set(schema.enums):
        if name in reserved_types or name.startswith("_taut_"):
            collisions.append((name, "type", "generated/runtime symbol"))
    for e in schema.enums.values():
        if "DESCRIPTOR" in e.members or "__taut_binding__" in e.members:
            collisions.append((e.name, "enum", "descriptor symbol"))
    if collisions:
        raise ValueError(f"Python generated name collisions: {collisions}")
    document = schema_json(schema)
    identity = identity or "schema_" + hashlib.sha256(json.dumps(document, sort_keys=True).encode()).hexdigest()[:16]
    out = ['"""GENERATED native Python types — do not edit."""',
           f"# Generator build: {GENERATOR_BUILD}; descriptor=1; codec=1; owner={RUNTIME_OWNER}",
           "from __future__ import annotations",
           "from dataclasses import dataclass as _taut_dataclass, field as _taut_field" if not yidl_records else "",
           "from enum import Enum as _taut_Enum",
           "from typing import ClassVar as _taut_ClassVar",
           "try:",
           "    from taut.contracts import require_contract as _taut_require_contract",
           f"    _taut_require_contract(artifact={identity!r}, descriptor=1, codec=1, capabilities={required_capabilities!r}, generator={GENERATOR_BUILD!r})",
           "    from taut import facts as _taut_facts",
           "    from taut.descriptors import publish as _taut_publish, MessageDescriptor as _taut_MessageDescriptor",
           "except ImportError as _taut_error:",
           f"    raise ImportError({(identity + ': compatible taut foundation required (owner=taut.python.foundation, descriptor=1, codec=1); supply compatible runtime and regenerate/rebind artifacts')!r}) from _taut_error"]
    if yidl_records:
        out.insert(out.index("    from taut import facts as _taut_facts"),
                   "    from taut.records import taut_dataclass as _taut_dataclass, "
                   "field as _taut_field, freeze_field as _taut_freeze_field")
    if validation:
        out += ["try:", "    from taut.validation import (ValidationReport as _taut_ValidationReport,",
                "        validate_record as _taut_validate, is_record_valid as _taut_is_valid)",
                "except ImportError as _taut_error:",
                f"    raise ImportError({(identity + ': required validation engine is missing/incompatible; regenerate source owner with validation or rebind compatible package runtime')!r}) from _taut_error"]
    out.append("")
    for name, path in sorted(external_types.items()):
        module, dot, symbol = path.rpartition(".")
        if not dot or not all(p.isidentifier() for p in path.split(".")):
            raise ValueError(f"{name}: Python external type must be module.Class, found {path!r}")
        out.append(f"from {module} import {symbol} as {name}")
    for e in schema.enums.values():
        if e.name in external_types:
            continue
        out.append(f"class {e.name}(_taut_Enum):")
        out.extend(f"    {m} = {v}" for m, v in e.members.items())
        if not e.members:
            out.append("    pass")
        out.append("")
    for msg in schema.messages.values():
        if msg.name in external_types:
            continue
        out += ["@_taut_dataclass(slots=True)", f"class {msg.name}:",
                "    DESCRIPTOR: _taut_ClassVar[_taut_MessageDescriptor]"]
        for f in msg.fields:
            if f.virtual:
                continue
            ann = f"{_py_ty(f.type)} | None" if f.optional else _py_ty(f.type)
            default = " = _taut_field(default=None, kw_only=True)" if f.cases else ""
            if yidl_records:
                hook = f"freeze=_taut_freeze_field({_freeze_spec(f.type)!r})"
                default = (" = _taut_field(default=None, kw_only=True, " + hook + ")"
                           if f.cases else " = _taut_field(" + hook + ")")
            out.append(f"    {field_attribute(f.name)}: {ann}{default}")
        if validation:
            out += ["", "    def validate(self, *, recursive: bool = True) -> _taut_ValidationReport:",
                    "        return _taut_validate(self, self.DESCRIPTOR, self.__taut_binding__, recursive=recursive)",
                    "", "    def is_valid(self, *, recursive: bool = True) -> bool:",
                    "        return _taut_is_valid(self, self.DESCRIPTOR, self.__taut_binding__, recursive=recursive)"]
        out.append("")
    # Dataclass repr is a source projection of canonical fact constructors, not a DSL loader.
    # Prefix constructor names so schema names cannot shadow runtime facts.
    import ast
    tree = ast.parse(repr(schema), mode="eval")
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            node.func = ast.Attribute(ast.Name("_taut_facts", ast.Load()), node.func.id, ast.Load())
    facts = ast.unparse(tree)
    out += [f"SCHEMA = _taut_facts.freeze_schema({facts})",
            "SCHEMA_DESCRIPTOR, BINDING = _taut_publish(",
            "    SCHEMA, {" + ", ".join(f"{n!r}: {n}" for n in schema.messages) + "},",
            "    {" + ", ".join(f"{n!r}: {n}" for n in schema.enums) + "},",
            f"    identity={identity!r}, ir_version={document['version']}, external={tuple(external_types)!r},",
            "    attributes=" + repr({m.name: {f.name: field_attribute(f.name) for f in m.fields if not f.virtual}
                                      for m in schema.messages.values()}) + ")",
            "", "__all__ = " + repr(list(schema.enums) + list(schema.messages) + ["SCHEMA", "SCHEMA_DESCRIPTOR", "BINDING"])]
    source = "\n".join(out) + "\n"
    try:
        compile(source, f"{identity}/api.py", "exec")
    except SyntaxError as exc:
        raise ValueError(f"{identity}: Python schema/host name or external import collision: {exc}") from exc
    return source
