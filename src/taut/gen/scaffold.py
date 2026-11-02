"""Scaffold generator — emit, for any schema + service, the per-language
**API types**, a typed **client**, and **server** stubs, for Python, TypeScript,
Rust, and C++. Used to populate docs examples' `generated/` trees.

What's actually per-API generated is the **types**. Clients and servers in
taut's design are *generic* runtime that read the IR (one ~100-line client/
server per language, zero per-method code — see dev-docs/CodeShape.md); the
client/server here are thin *typed convenience stubs* over that runtime. The
type emitters reuse the byte-exact-proven Rust/C++ generators.
"""

from __future__ import annotations

from importlib import resources
from pathlib import Path
from types import MappingProxyType

from . import cpp as _cpp
from . import go as _go
from . import java as _java
from . import js as _js
from . import kotlin as _kotlin
from . import rust as _rust
from . import swift as _swift
from ..ir.model import (
    EnumRef, ListOf, MapOf, MsgRef, Scalar, Schema, ServiceDef, TypeRef,
)
from ..ir.options import OPTIONS
from .names import Clash

# Compiled targets whose generated code imports external runtime modules. Maps
# lang -> list of (output path relative to its lang dir, vendored resource file).
# Each carries the CBOR runtime plus `ext.<lang>`, the side-channel/extension accessor
# runtime (Phase 2 fills it in). emit() vendors each resource that *exists*, so the ext
# slot ships automatically once its file lands. Python uses the installed package
# directly; TypeScript vendors its IR-driven runtime from the resources below.
_RUNTIMES: dict[str, list[tuple[str, str]]] = {
    "typescript": [
        ("cbor.ts", "typescript/cbor.ts"),
        ("codec.ts", "typescript/codec.ts"),
        ("schema.ts", "typescript/schema.ts"),
        ("taut_client.ts", "typescript/taut_client.ts"),
        ("ext.ts", "typescript/ext.ts"),
    ],
    # use crate::cbor / crate::ext; the fail-closed runtime, Rust's only one, vendored as `cbor.rs`
    "rust":   [("cbor.rs", "cbor_fail_closed.rs"), ("descriptors.rs", "descriptors.rs"), ("ext.rs", "ext.rs")],
    "cpp":    [("taut/cbor.hpp", "cbor.hpp"), ("taut/ext.hpp", "ext.hpp")],
    "swift":  [("cbor.swift", "cbor.swift"), ("ext.swift", "ext.swift")],
    "go":     [("cbor.go", "cbor.go"), ("ext.go", "ext.go")],
    "kotlin": [("cbor.kt", "cbor.kt"), ("ext.kt", "ext.kt")],
    "js":     [("cbor.js", "cbor.js"), ("ext.js", "ext.js")],
    "java":   [("Cbor.java", "Cbor.java"), ("Ext.java", "Ext.java")],
}


def _runtime_source(resource: str) -> str:
    return resources.files("taut.gen.runtime").joinpath(resource).read_text(encoding="utf-8")


def _runtime_exists(resource: str) -> bool:
    return resources.files("taut.gen.runtime").joinpath(resource).is_file()


def _attr(name: str) -> str:
    return name.replace(".", "_")


# =============================================================================
# Python
# =============================================================================

PYTHON_RESERVED_FIELD_NAMES = MappingProxyType({
    "mro": "an attribute every class has, which dataclass reads as the field's default",
})
"""Field names a dataclass cannot take besides `__*__` ones (`python_name_clashes`): an attribute
the class has before `dataclass` runs is read as the field's default, and a field without one may
not follow it."""

PYTHON_RESERVED_TYPE_NAMES = MappingProxyType({
    "dataclass": "a name api.py imports, which a later message's decorator would call",
    "Enum": "a name api.py imports, which a later enum would subclass",
})
"""Message and enum names api.py cannot take: a class rebinds the name it imports."""


def python_name_clashes(schema: Schema) -> list[Clash]:
    """A field named `__*__`: Python reserves the form, and most such names are attributes every
    class has, which dataclass reads as a default like `mro`'s. Which ones grows with Python."""
    return [(f"{m.name}.{f.name}", "field", "a `__*__` name, which Python reserves")
            for m in schema.messages.values() for f in m.fields
            if len(f.name) > 4 and f.name.startswith("__") and f.name.endswith("__")]


def _py_ty(t: TypeRef | None) -> str:
    if t is None:
        return "None"
    if isinstance(t, Scalar):
        return {"int": "int", "str": "str", "bytes": "bytes", "bool": "bool", "float": "float"}[t.kind]
    if isinstance(t, (EnumRef, MsgRef)):
        return t.name
    if isinstance(t, ListOf):
        return f"list[{_py_ty(t.elem)}]"
    if isinstance(t, MapOf):
        return f"dict[{_py_ty(t.key)}, {_py_ty(t.value)}]"
    raise TypeError(t)


def python_api(schema: Schema, forward_compat: bool = False, *, validation=False,
               external_types=None, identity=None) -> str:
    from .python import emit_types
    return emit_types(schema, validation=validation, external_types=external_types, identity=identity)


def python_client(schema: Schema, svc: ServiceDef) -> str:
    out = ['"""GENERATED typed client over a generic taut transport (call/subscribe)."""',
           "from __future__ import annotations",
           "from .api import *  # noqa: F401,F403", "",
           f"class {svc.name}Client:",
           "    def __init__(self, transport):",
           "        self._t = transport", ""]
    for meth in svc.methods:
        sig = "".join(f", {pn}: {_py_ty(pt)}" for pn, pt in meth.params)
        kwargs = "".join(f", {pn}={pn}" for pn, _ in meth.params)
        if not meth.streams():
            ret = _py_ty(meth.output)
            out.append(f"    async def {_attr(meth.name)}(self{sig}) -> {ret}:")
            out.append(f'        return await self._t.call("{meth.name}", {ret}{kwargs})')
        else:
            out.append(f"    def {_attr(meth.name)}(self{sig}):  # {meth.shape} stream")
            out.append(f'        return self._t.subscribe("{meth.name}"{kwargs})')
        out.append("")
    return "\n".join(out) + "\n"


def python_server(schema: Schema, svc: ServiceDef) -> str:
    out = ['"""GENERATED server stubs: a handler Protocol + IR-driven registration."""',
           "from __future__ import annotations",
           "from typing import Protocol",
           "from .api import *  # noqa: F401,F403", "",
           f"class {svc.name}Handlers(Protocol):"]
    for meth in svc.methods:
        sig = "".join(f", {pn}: {_py_ty(pt)}" for pn, pt in meth.params)
        if not meth.streams():
            out.append(f"    async def {_attr(meth.name)}(self{sig}) -> {_py_ty(meth.output)}: ...")
        else:
            out.append(f"    def {_attr(meth.name)}(self{sig}): ...  # -> Subscription ({meth.shape})")
    out += ["", f'def register(transport, schema, handlers: "{svc.name}Handlers") -> None:',
            "    bind = {"]
    for meth in svc.methods:
        out.append(f'        "{meth.name}": handlers.{_attr(meth.name)},')
    out += ["    }",
            f'    for m in schema.services["{svc.name}"].methods:',
            "        transport.register_method(m, bind[m.name])"]
    return "\n".join(out) + "\n"


# =============================================================================
# TypeScript
# =============================================================================

def _ts_ty(t: TypeRef | None) -> str:
    if t is None:
        return "void"
    if isinstance(t, Scalar):
        return {"int": "bigint", "str": "string", "bytes": "Uint8Array", "bool": "boolean", "float": "number"}[t.kind]
    if isinstance(t, (EnumRef, MsgRef)):
        return t.name
    if isinstance(t, ListOf):
        return f"{_ts_ty(t.elem)}[]"
    if isinstance(t, MapOf):
        return f"Map<{_ts_ty(t.key)}, {_ts_ty(t.value)}>"
    raise TypeError(t)


def ts_api(schema: Schema, forward_compat: bool = False) -> str:
    out = ["// GENERATED native TypeScript types — do not edit.", ""]
    for e in schema.enums.values():
        members = " | ".join(f'"{m}"' for m in e.members)
        out.append(f"export type {e.name} = {members};")
    out.append("")
    for m in schema.messages.values():
        out.append(f"export interface {m.name} {{")
        for f in m.fields:
            ty = f"{_ts_ty(f.type)} | null" if f.optional else _ts_ty(f.type)
            out.append(f"  {f.name}: {ty};")
        out.append("}")
        out.append("")
    return "\n".join(out) + "\n"


def ts_client(schema: Schema, svc: ServiceDef) -> str:
    out = ["// GENERATED typed client over the generic tautClient (call/subscribe).",
           'import type { tautClient } from "./taut_client.ts";',
           "import type * as api from \"./api.ts\";", "",
           f"export class {svc.name}Client {{",
           "  private c: tautClient;",
           "  constructor(c: tautClient) { this.c = c; }"]
    for meth in svc.methods:
        args = ", ".join(f"{pn}: {_ts_ty(pt)}" for pn, pt in meth.params)
        obj = "{ " + ", ".join(pn for pn, _ in meth.params) + " }" if meth.params else "{}"
        nm = _attr(meth.name)
        if not meth.streams():
            ret = _ts_ty(meth.output)
            out.append(f"  {nm}({args}): Promise<api.{ret}> {{")
            out.append(f'    return this.c.call("{meth.name}", {obj}) as Promise<api.{ret}>;')
            out.append("  }")
        else:
            out.append(f"  {nm}({args + ', ' if args else ''}onEvent: (event: string, value: unknown) => void): () => void {{  // {meth.shape}")
            out.append(f'    return this.c.subscribe("{meth.name}", {obj}, onEvent);')
            out.append("  }")
    out.append("}")
    return "\n".join(out) + "\n"


def ts_server(schema: Schema, svc: ServiceDef) -> str:
    out = ["// GENERATED server stubs: a handler interface + IR-driven registration.",
           "import type * as api from \"./api.ts\";", "",
           f"export interface {svc.name}Handlers {{"]
    for meth in svc.methods:
        args = ", ".join(f"{pn}: {_ts_ty(pt)}" for pn, pt in meth.params)
        if not meth.streams():
            out.append(f"  {_attr(meth.name)}({args}): Promise<api.{_ts_ty(meth.output)}>;")
        else:
            out.append(f"  {_attr(meth.name)}({args}): unknown;  // Subscription ({meth.shape})")
    out.append("}")
    out.append("")
    out.append(f"// Register against the IR (the transport reads kind/params from the contract):")
    out.append(f"export function register(transport: any, schema: any, h: {svc.name}Handlers): void {{")
    out.append(f'  const bind: Record<string, unknown> = {{')
    for meth in svc.methods:
        out.append(f'    "{meth.name}": h.{_attr(meth.name)}.bind(h),')
    out.append("  };")
    out.append(f'  for (const m of schema.services["{svc.name}"].methods) transport.registerMethod(m, bind[m.name]);')
    out.append("}")
    return "\n".join(out) + "\n"


# =============================================================================
# Rust  (API reuses the byte-exact-proven type generator)
# =============================================================================

def _rs_ty(t: TypeRef | None) -> str:
    if t is None:
        return "()"
    if isinstance(t, Scalar):
        return {"int": "i64", "str": "String", "bytes": "Vec<u8>", "bool": "bool", "float": "f64"}[t.kind]
    if isinstance(t, (EnumRef, MsgRef)):
        return t.name
    if isinstance(t, ListOf):
        return f"Vec<{_rs_ty(t.elem)}>"
    if isinstance(t, MapOf):
        return f"std::collections::BTreeMap<{_rs_ty(t.key)}, {_rs_ty(t.value)}>"
    raise TypeError(t)


def rust_api(schema: Schema, forward_compat: bool = False,
             external_types: dict[str, str] | None = None, *, validation=False,
             identity=None, runtime_path="crate") -> str:
    from .rust_metadata import emit_types
    return emit_types(schema, forward_compat=forward_compat, external_types=external_types,
                      validation=validation, identity=identity, runtime_path=runtime_path)


def rust_client(schema: Schema, svc: ServiceDef) -> str:
    out = ["// GENERATED typed client over the generic taut Client.",
           "use crate::api::*;", "use crate::client::Client;", "use crate::cbor::Cbor;", "",
           f"pub struct {svc.name}Client<'a> {{ c: &'a Client }}", "",
           f"impl<'a> {svc.name}Client<'a> {{",
           f"    pub fn new(c: &'a Client) -> Self {{ Self {{ c }} }}"]
    for meth in svc.methods:
        if not meth.streams():
            args = "".join(f", {pn}: {_rs_ty(pt)}" for pn, pt in meth.params)
            out.append(f"    // {meth.name}({', '.join(pn for pn,_ in meth.params)}) -> {_rs_ty(meth.output)}")
            out.append(f"    // self.c.call(\"{meth.name}\", &[..encode args..]).await -> {_rs_ty(meth.output)}::from_cbor(..)")
        else:
            out.append(f"    // {meth.name}: subscribe (\"{meth.shape}\") -> stream of {[(e) for e,_ in meth.events]}")
    out.append("}")
    return "\n".join(out) + "\n"


def rust_server(schema: Schema, svc: ServiceDef) -> str:
    out = ["// GENERATED server handler trait + registration sketch.",
           "use crate::api::*;", "",
           f"pub trait {svc.name}Handlers {{"]
    for meth in svc.methods:
        if not meth.streams():
            args = "".join(f", {pn}: {_rs_ty(pt)}" for pn, pt in meth.params)
            out.append(f"    fn {_attr(meth.name)}(&self{args}) -> {_rs_ty(meth.output)};")
        else:
            out.append(f"    // {meth.name}: returns a subscription ({meth.shape})")
    out.append("}")
    out.append("// register(): for m in schema.services[\"%s\"].methods { transport.register_method(m, ..) }" % svc.name)
    return "\n".join(out) + "\n"


# =============================================================================
# C++  (API reuses the compile-time-proven type generator)
# =============================================================================

def _cpp_ty(t: TypeRef | None) -> str:
    if t is None:
        return "void"
    if isinstance(t, Scalar):
        return {"int": "long long", "str": "std::string_view", "bytes": "std::string_view", "bool": "bool", "float": "double"}[t.kind]
    if isinstance(t, (EnumRef, MsgRef)):
        return t.name
    if isinstance(t, ListOf):
        return f"std::vector<{_cpp_ty(t.elem)}>"
    if isinstance(t, MapOf):
        return f"std::map<{_cpp_ty(t.key)}, {_cpp_ty(t.value)}>"
    raise TypeError(t)


def cpp_api(schema: Schema, forward_compat: bool = False) -> str:
    # enums + structs + constexpr to_cbor/from_cbor (+ wire_residual when forward_compat)
    return _cpp._emit_types(schema, forward_compat)


def cpp_client(schema: Schema, svc: ServiceDef) -> str:
    out = ["// GENERATED typed client stub over a generic transport.",
           '#pragma once', '#include "api.hpp"', "",
           f"namespace taut::{svc.name.lower()} {{", ""]
    for meth in svc.methods:
        if not meth.streams():
            args = ", ".join(f"{_cpp_ty(pt)} {pn}" for pn, pt in meth.params)
            out.append(f"// {meth.name}: ({args}) -> {_cpp_ty(meth.output)}   [transport.call(\"{meth.name}\", ...)]")
        else:
            out.append(f"// {meth.name}: subscribe (\"{meth.shape}\")")
    out += ["", "} // namespace"]
    return "\n".join(out) + "\n"


def cpp_server(schema: Schema, svc: ServiceDef) -> str:
    out = ["// GENERATED server handler interface stub.",
           '#pragma once', '#include "api.hpp"', "",
           f"struct {svc.name}Handlers {{"]
    for meth in svc.methods:
        if not meth.streams():
            args = ", ".join(f"{_cpp_ty(pt)} {pn}" for pn, pt in meth.params)
            out.append(f"    virtual {_cpp_ty(meth.output)} {_attr(meth.name)}({args}) = 0;")
        else:
            out.append(f"    // {_attr(meth.name)}: subscription ({meth.shape})")
    out.append("};")
    return "\n".join(out) + "\n"


# =============================================================================
# Swift
# =============================================================================

def _swift_ty(t: TypeRef | None) -> str:
    if t is None:
        return "Void"
    if isinstance(t, Scalar):
        return {"int": "Int64", "str": "String", "bytes": "[UInt8]", "bool": "Bool", "float": "Double"}[t.kind]
    if isinstance(t, (EnumRef, MsgRef)):
        return t.name
    if isinstance(t, ListOf):
        return f"[{_swift_ty(t.elem)}]"
    if isinstance(t, MapOf):
        return f"[{_swift_ty(t.key)}: {_swift_ty(t.value)}]"
    raise TypeError(t)


def swift_api(schema: Schema, forward_compat: bool = False) -> str:
    return _swift.emit_types(schema, forward_compat)


def swift_client(schema: Schema, svc: ServiceDef) -> str:
    out = ["// GENERATED typed client stub over a generic transport.", ""]
    for meth in svc.methods:
        args = ", ".join(f"{pn}: {_swift_ty(pt)}" for pn, pt in meth.params)
        if not meth.streams():
            out.append(f"// {meth.name}({args}) -> {_swift_ty(meth.output)}   [transport.call]")
        else:
            out.append(f"// {meth.name}({args}): subscribe (\"{meth.shape}\")")
    return "\n".join(out) + "\n"


def swift_server(schema: Schema, svc: ServiceDef) -> str:
    out = ["// GENERATED server handler protocol stub.", f"public protocol {svc.name}Handlers {{"]
    for meth in svc.methods:
        args = ", ".join(f"{pn}: {_swift_ty(pt)}" for pn, pt in meth.params)
        if not meth.streams():
            out.append(f"    func {_attr(meth.name)}({args}) -> {_swift_ty(meth.output)}")
        else:
            out.append(f"    // {_attr(meth.name)}: subscription ({meth.shape})")
    out.append("}")
    return "\n".join(out) + "\n"


# =============================================================================
# Go
# =============================================================================

def _go_ty(t: TypeRef | None) -> str:
    if t is None:
        return ""
    if isinstance(t, Scalar):
        return {"int": "int64", "str": "string", "bytes": "[]byte", "bool": "bool", "float": "float64"}[t.kind]
    if isinstance(t, (EnumRef, MsgRef)):
        return t.name
    if isinstance(t, ListOf):
        return f"[]{_go_ty(t.elem)}"
    if isinstance(t, MapOf):
        return f"map[{_go_ty(t.key)}]{_go_ty(t.value)}"
    raise TypeError(t)


def go_api(schema: Schema, forward_compat: bool = False) -> str:
    return _go.emit_types(schema, forward_compat)


def go_client(schema: Schema, svc: ServiceDef) -> str:
    out = ["// GENERATED typed client stub over a generic transport.", "package taut", ""]
    for meth in svc.methods:
        args = ", ".join(f"{pn} {_go_ty(pt)}" for pn, pt in meth.params)
        kind = "call" if not meth.streams() else f'subscribe ("{meth.shape}")'
        out.append(f"// {_go._pascal(meth.name)}({args}) {_go_ty(meth.output)}  [{kind}]")
    return "\n".join(out) + "\n"


def go_server(schema: Schema, svc: ServiceDef) -> str:
    out = ["// GENERATED server handler interface stub.", "package taut", "",
           f"type {svc.name}Handlers interface {{"]
    for meth in svc.methods:
        args = ", ".join(f"{pn} {_go_ty(pt)}" for pn, pt in meth.params)
        if not meth.streams():
            out.append(f"\t{_go._pascal(meth.name)}({args}) {_go_ty(meth.output)}")
        else:
            out.append(f"\t// {_go._pascal(meth.name)}: subscription ({meth.shape})")
    out.append("}")
    return "\n".join(out) + "\n"


# =============================================================================
# Kotlin
# =============================================================================

def _kt_ty(t: TypeRef | None) -> str:
    if t is None:
        return "Unit"
    if isinstance(t, Scalar):
        return {"int": "Long", "str": "String", "bytes": "ByteArray", "bool": "Boolean", "float": "Double"}[t.kind]
    if isinstance(t, (EnumRef, MsgRef)):
        return t.name
    if isinstance(t, ListOf):
        return f"List<{_kt_ty(t.elem)}>"
    if isinstance(t, MapOf):
        return f"Map<{_kt_ty(t.key)}, {_kt_ty(t.value)}>"
    raise TypeError(t)


def kotlin_api(schema: Schema, forward_compat: bool = False, *, validation=False, external_types=None, identity=None) -> str:
    return _kotlin.emit_types(schema, forward_compat, validation=validation, external_types=external_types, identity=identity)


def kotlin_client(schema: Schema, svc: ServiceDef) -> str:
    out = ["// GENERATED typed client stub over a generic transport.", "package taut", ""]
    for meth in svc.methods:
        args = ", ".join(f"{pn}: {_kt_ty(pt)}" for pn, pt in meth.params)
        kind = "call" if not meth.streams() else f'subscribe ("{meth.shape}")'
        out.append(f"// {_attr(meth.name)}({args}): {_kt_ty(meth.output)}  [{kind}]")
    return "\n".join(out) + "\n"


def kotlin_server(schema: Schema, svc: ServiceDef) -> str:
    out = ["// GENERATED server handler interface stub.", "package taut", "",
           f"interface {svc.name}Handlers {{"]
    for meth in svc.methods:
        args = ", ".join(f"{pn}: {_kt_ty(pt)}" for pn, pt in meth.params)
        if not meth.streams():
            out.append(f"    fun {_attr(meth.name)}({args}): {_kt_ty(meth.output)}")
        else:
            out.append(f"    // {_attr(meth.name)}: subscription ({meth.shape})")
    out.append("}")
    return "\n".join(out) + "\n"


# =============================================================================
# JavaScript
# =============================================================================

def js_api(schema: Schema, forward_compat: bool = False) -> str:
    return _js.emit_types(schema, forward_compat)


def js_client(schema: Schema, svc: ServiceDef) -> str:
    out = ['"use strict";', "// GENERATED typed client stub over a generic transport.", ""]
    for meth in svc.methods:
        args = ", ".join(pn for pn, _ in meth.params)
        kind = "call" if not meth.streams() else f'subscribe ("{meth.shape}")'
        out.append(f"// {_attr(meth.name)}({args})  [{kind}]")
    return "\n".join(out) + "\n"


def js_server(schema: Schema, svc: ServiceDef) -> str:
    out = ['"use strict";', "// GENERATED server handler shape (implement these as a name->fn map):"]
    for meth in svc.methods:
        args = ", ".join(pn for pn, _ in meth.params)
        tag = "" if not meth.streams() else f"  // subscription ({meth.shape})"
        out.append(f"//   {meth.name}: ({args}) => ...{tag}")
    return "\n".join(out) + "\n"


# =============================================================================
# Java
# =============================================================================

def _java_ty(t: TypeRef | None) -> str:
    if t is None:
        return "void"
    if isinstance(t, Scalar):
        return {"int": "long", "str": "String", "bytes": "byte[]", "bool": "boolean", "float": "double"}[t.kind]
    if isinstance(t, (EnumRef, MsgRef)):
        return t.name
    if isinstance(t, ListOf):
        return f"java.util.List<{_java_ty(t.elem)}>"
    if isinstance(t, MapOf):
        return f"java.util.Map<{_java_ty(t.key)}, {_java_ty(t.value)}>"
    raise TypeError(t)


def java_api(schema: Schema, forward_compat: bool = False, *, validation=False, external_types=None, identity=None) -> str:
    return _java.emit_types(schema, forward_compat, validation=validation, external_types=external_types, identity=identity)


def java_client(schema: Schema, svc: ServiceDef) -> str:
    out = ["// GENERATED typed client stub over a generic transport.", "package taut;", ""]
    for meth in svc.methods:
        args = ", ".join(f"{_java_ty(pt)} {pn}" for pn, pt in meth.params)
        kind = "call" if not meth.streams() else f'subscribe ("{meth.shape}")'
        out.append(f"// {_attr(meth.name)}({args}) -> {_java_ty(meth.output)}  [{kind}]")
    return "\n".join(out) + "\n"


def java_server(schema: Schema, svc: ServiceDef) -> str:
    out = ["// GENERATED server handler interface stub.", "package taut;", "",
           f"interface {svc.name}Handlers {{"]
    for meth in svc.methods:
        args = ", ".join(f"{_java_ty(pt)} {pn}" for pn, pt in meth.params)
        if not meth.streams():
            out.append(f"    {_java_ty(meth.output)} {_attr(meth.name)}({args});")
        else:
            out.append(f"    // {_attr(meth.name)}: subscription ({meth.shape})")
    out.append("}")
    return "\n".join(out) + "\n"


# =============================================================================
# driver
# =============================================================================

_LANGS = {
    "python":     ("py",    python_api, python_client, python_server),
    "typescript": ("ts",    ts_api,     ts_client,     ts_server),
    "rust":       ("rs",    rust_api,   rust_client,   rust_server),
    "cpp":        ("hpp",   cpp_api,    cpp_client,    cpp_server),
    "swift":      ("swift", swift_api,  swift_client,  swift_server),
    "go":         ("go",    go_api,     go_client,     go_server),
    "kotlin":     ("kt",    kotlin_api, kotlin_client, kotlin_server),
    "js":         ("js",    js_api,     js_client,     js_server),
    "java":       ("java",  java_api,   java_client,   java_server),
}

# The options each target implements (TautOptions.md OPT-F2): the wire options, which all nine
# implement in v0.10.0 (TautV010Plan.md D1). emit() refuses a requested target that lacks an option
# the schema declares. Wire and semantic options bind every target; a target may ignore a metadata
# option, and a codegen option whose `targets` leave it out (OPT-D2).
_IMPLEMENTED_OPTIONS: dict[str, frozenset[str]] = {
    "python":     frozenset({"max_depth", "max_encoded_len"}),
    "typescript": frozenset({"max_depth", "max_encoded_len"}),
    "rust":       frozenset({"max_depth", "max_encoded_len"}),
    "cpp":        frozenset({"max_depth", "max_encoded_len"}),
    "swift":      frozenset({"max_depth", "max_encoded_len"}),
    "go":         frozenset({"max_depth", "max_encoded_len"}),
    "kotlin":     frozenset({"max_depth", "max_encoded_len"}),
    "js":         frozenset({"max_depth", "max_encoded_len"}),
    "java":       frozenset({"max_depth", "max_encoded_len"}),
}


def emit(
    schema: Schema,
    out_dir: Path,
    *,
    langs: list[str] | None = None,
    services: list[str] | None = None,
    runtime: bool = False,
    forward_compat: bool = False,
    rust_external_types: dict[str, str] | None = None,
    runtime_mode: str | None = None,
    validation: bool = False,
    runtime_bindings: dict | None = None,
    python_external_types: dict[str, str] | None = None,
    schema_identity: str | None = None,
    java_external_types: dict | None = None,
    kotlin_external_types: dict | None = None,
) -> list[Path]:
    """Generate per-language code from an IR (the engine behind the `tautc` CLI).

    - `langs`: subset of `_LANGS` (python, typescript, rust, cpp, swift, go, kotlin, js,
      java); default all.
    - `services`: services to emit client/server for; default = every service in
      the schema. Pass `[]` for **api only** (native types + encoders/decoders,
      no RPC stubs) — the common build-script case for compiled targets.
    - `runtime`: when True, also emit the vendored CBOR runtime for compiled
      targets (`_RUNTIMES`: the CBOR codec and extension helpers) so the generated
      code is self-contained. Off by default — emitted only on demand.
    - `forward_compat`: when True, generated structs carry a `wire_residual` field
      that preserves unknown/newer-version tags, in every generated target. Off by
      default; python and typescript always keep them.
      An IR that declares extensions requires it for compiled targets (D14:
      extensions ride the residual space) — otherwise generation is a build error.

    Rust's codec is fail-closed, its only codec since v0.10.0, which removed the legacy
    one and `fail_closed=False` (CLI `--legacy-codec`) with it: generated `from_cbor`
    returns `Result<Self, DecodeError>` and `from_wire` is fallible, so decode never
    panics on malformed or untrusted input, and a CBOR `int` outside the frozen `i64`
    subset is a typed error. With `runtime=True` the fail-closed runtime (typed
    `DecodeError`, bounds-checked `try_decode` and `try_*` accessors) is vendored as
    `cbor.rs`. See dev-docs/RustFailClosed.md.

    `api.{ext}` (types + codec) is always written per language; client/server are
    `client.{ext}` for a lone service, `client_{svc}.{ext}` when several.
    """
    from .python_runtime import resolve_mode, runtime_binding, plan_outputs, apply_outputs, output_locks
    from ..rules import check_rules
    mode = resolve_mode(runtime, runtime_mode, validation)
    runtime = mode == "source"
    lang_keys = list(langs) if langs is not None else list(_LANGS)
    errors = check_rules(schema)
    if errors:
        raise ValueError("; ".join(errors))
    constrained = any(f.oneof or f.cases for m in schema.messages.values() for f in m.fields)
    if (validation or constrained) and set(lang_keys) - {"python", "rust", "java", "kotlin"}:
        raise ValueError("oneof/validation supports Python, Rust, Java and Kotlin only; explicitly select supported languages")
    if mode == "package" and set(lang_keys) - {"python", "rust", "java", "kotlin"}:
        raise ValueError("package runtime binding is implemented for Python, Rust, Java and Kotlin only")
    kotlin_binding = None
    if "kotlin" in lang_keys:
        from .kotlin_runtime import binding as resolve_kotlin_binding
        kotlin_binding = resolve_kotlin_binding(runtime_bindings, out_dir / "kotlin", mode)
    if kotlin_external_types is not None and "kotlin" not in lang_keys:
        raise ValueError("Kotlin external types require a Kotlin generation target")
    java_binding = None
    if "java" in lang_keys:
        from .java_runtime import binding as resolve_java_binding, verify_artifact
        java_binding = resolve_java_binding(runtime_bindings, out_dir / "java", mode)
        artifact = (runtime_bindings or {}).get("java", {}).get("artifact")
        if artifact:
            verify_artifact(Path(artifact), validation=validation)
    if java_external_types is not None and "java" not in lang_keys:
        raise ValueError("Java external types require a Java generation target")
    rust_binding = None
    if "rust" in lang_keys:
        from .rust_runtime import binding as resolve_rust_binding
        rust_binding = resolve_rust_binding(runtime_bindings, out_dir / "rust", mode)
    if rust_external_types is not None:
        from .rust_external import imports

        if "rust" not in lang_keys:
            raise ValueError("Rust external types require a Rust generation target")
        imports(schema, rust_external_types)
    unknown = [l for l in lang_keys if l not in _LANGS]
    if unknown:
        raise ValueError(f"unknown lang(s) {unknown}; known: {sorted(_LANGS)}")
    if runtime and rust_external_types and (not rust_binding[2] or rust_binding[0] == "crate"):
        raise ValueError(
            "external Rust types cannot be generated with runtime=True: "
            "the owner crate must supply the shared runtime; bind its module and existing source_root"
        )
    _GENERATED = {"rust", "cpp", "swift", "go", "kotlin", "js", "java"}
    if schema.extensions and not forward_compat and (_GENERATED & set(lang_keys)):
        raise ValueError(
            "this IR declares extensions; generating a typed target "
            f"({'/'.join(sorted(_GENERATED))}) requires forward_compat (extensions ride "
            "the residual space) — pass --forward-compat"
        )
    # OPT-F2: before writing anything, refuse a requested target that lacks an option the schema
    # declares at any level (declared, not defaulted), so that no target ignores a declared value.
    # An option the registry does not know binds every target (OPT-F1).
    declared = set(schema.options)
    for enum_def in schema.enums.values():
        declared.update(enum_def.options)
    for msg in schema.messages.values():
        declared.update(msg.options)
        for fld in msg.fields:
            declared.update(fld.options)
    lacking: list[str] = []
    for lang in lang_keys:
        for name in sorted(declared - _IMPLEMENTED_OPTIONS[lang]):
            defn = OPTIONS.get(name)
            ignorable = defn is not None and (defn.klass == "metadata" or (
                defn.klass == "codegen" and defn.targets is not None and lang not in defn.targets))
            if not ignorable:
                lacking.append(f"{lang} lacks {name}")
    if lacking:
        raise ValueError("this schema declares options a requested target does not implement, "
                         f"so its code would ignore them: {'; '.join(lacking)}")
    if "python" in lang_keys:
        from ..ir.validate import validate_or_raise
        validate_or_raise(schema)
    svc_names = list(services) if services is not None else list(schema.services)
    missing = [s for s in svc_names if s not in schema.services]
    if missing:
        raise ValueError(f"unknown service(s) {missing}; known: {sorted(schema.services)}")
    multi = len(svc_names) > 1
    written: list[Path] = []
    all_writes = {}
    python_texts = {}
    rust_texts = {}
    java_texts = {}
    kotlin_texts = {}
    for lang in lang_keys:
        ext, api_fn, client_fn, server_fn = _LANGS[lang]
        d = out_dir / lang
        api_path = d / f"api.{ext}"
        api_kwargs = {"forward_compat": forward_compat}
        if lang == "rust":
            api_kwargs.update(external_types=rust_external_types, validation=validation,
                              identity=schema_identity, runtime_path=rust_binding[0])
        if lang == "kotlin":
            api_kwargs.update(validation=validation, external_types=kotlin_external_types, identity=schema_identity)
        if lang == "java":
            api_kwargs.update(validation=validation, external_types=java_external_types, identity=schema_identity)
        if lang == "python":
            api_kwargs.update(validation=validation, external_types=python_external_types, identity=schema_identity)
        api_text = api_fn(schema, **api_kwargs)
        if lang == "python":
            python_texts[f"api.{ext}"] = api_text
        elif lang == "rust":
            rust_texts[f"api.{ext}"] = api_text
        elif lang == "java":
            java_texts[f"api.{ext}"] = api_text
        elif lang == "kotlin":
            kotlin_texts[f"api.{ext}"] = api_text
        else:
            all_writes[api_path] = api_text.encode("utf-8")
        written.append(api_path)
        if runtime and lang in _RUNTIMES and lang not in ("rust", "java", "kotlin"):
            for rel, resource in _RUNTIMES[lang]:
                if not _runtime_exists(resource):
                    continue   # e.g. ext.<lang> before Phase 2 — vendored once its file lands
                rt_path = d / rel
                all_writes[rt_path] = _runtime_source(resource).encode("utf-8")
                written.append(rt_path)
        for sname in svc_names:
            svc = schema.services[sname]
            suffix = f"_{sname}" if multi else ""
            for stem, fn in (("client", client_fn), ("server", server_fn)):
                path = d / f"{stem}{suffix}.{ext}"
                content = fn(schema, svc)
                if lang == "python":
                    python_texts[path.name] = content
                elif lang == "rust":
                    rust_texts[path.name] = content
                elif lang == "java":
                    java_texts[path.name] = content
                elif lang == "kotlin":
                    kotlin_texts[path.name] = content
                else:
                    all_writes[path] = content.encode("utf-8")
                written.append(path)
    plans = []
    lock_roots = []
    if "python" in lang_keys:
        # Python output is a package (client/server use relative imports).
        init = out_dir / "python" / "__init__.py"
        python_texts["__init__.py"] = "from .api import *  # noqa: F401,F403\n"
        written.append(init)
        source_root = runtime_binding(runtime_bindings, out_dir / "python")
        directory = (out_dir / "python").resolve()
        lock_roots.extend([directory, source_root])
        plans.append((directory, source_root, directory / ".taut-python-outputs.json", plan_outputs,
                      python_texts, {"consume_source": "source_root" in (runtime_bindings or {}).get("python", {})}))
    if "rust" in lang_keys:
        from .rust_runtime import plan_outputs as rust_plan_outputs, canonical_path
        directory = canonical_path(out_dir / "rust")
        _, source_root, consume_source = rust_binding
        lock_roots.extend([directory, source_root])
        plans.append((directory, source_root, directory / ".taut-rust-outputs.json", rust_plan_outputs,
                      rust_texts, {"consume_source": consume_source, "external": bool(rust_external_types)}))
    if "java" in lang_keys:
        from .java_runtime import plan_outputs as java_plan_outputs, canonical_path
        directory = canonical_path(out_dir / "java")
        _, source_root, consume_source = java_binding
        lock_roots.extend([directory, source_root])
        plans.append((directory, source_root, directory / ".taut-java-outputs.json", java_plan_outputs,
                      java_texts, {"consume_source": consume_source, "external": bool(java_external_types)}))
    if "kotlin" in lang_keys:
        from .kotlin_runtime import plan_outputs as kotlin_plan_outputs, canonical_path
        directory = canonical_path(out_dir / "kotlin")
        source_root, consume_source = kotlin_binding
        lock_roots.extend([directory, source_root])
        plans.append((directory, source_root, directory / ".taut-kotlin-outputs.json", kotlin_plan_outputs,
                      kotlin_texts, {"consume_source": consume_source, "external": bool(kotlin_external_types)}))
    import json
    for _, _, previous, _, _, _ in plans:
        if previous.exists():
            prior_root = json.loads(previous.read_text(encoding="utf-8")).get("source_root")
            if prior_root:
                lock_roots.append(Path(prior_root))
    with output_locks(lock_roots):
        deletes = set()
        for directory, source_root, previous, planner, texts, extra in plans:
            if previous.exists():
                locked_prior = json.loads(previous.read_text(encoding="utf-8")).get("source_root")
                if locked_prior and Path(locked_prior).resolve() not in {p.resolve() for p in lock_roots}:
                    raise ValueError("output ownership changed concurrently; rerun generation to lock its new runtime owner")
            writes, stale = planner(directory, texts, mode=mode, validation=validation,
                                    source_root=source_root, **extra)
            conflicts = set(writes) & set(all_writes)
            if conflicts:
                raise ValueError(f"conflicting generated output owners: {sorted(map(str, conflicts))}")
            all_writes.update(writes)
            deletes.update(stale)
            written.extend(p for p in writes if p not in {directory / n for n in texts})
        apply_outputs(all_writes, deletes)
    return written


def emit_all(schema: Schema, service_name: str, out_dir: Path, *, runtime: bool = False,
             runtime_mode: str | None = None, validation: bool = False,
             runtime_bindings: dict | None = None, python_external_types=None,
             schema_identity=None, langs=None, rust_external_types=None, java_external_types=None, kotlin_external_types=None) -> list[Path]:
    """Back-compat: api + client/server for one service, all languages."""
    return emit(schema, out_dir, services=[service_name], runtime=runtime, runtime_mode=runtime_mode,
                validation=validation, runtime_bindings=runtime_bindings,
                python_external_types=python_external_types, schema_identity=schema_identity, langs=langs,
                rust_external_types=rust_external_types, java_external_types=java_external_types, kotlin_external_types=kotlin_external_types)
