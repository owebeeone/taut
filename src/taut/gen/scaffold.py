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

from . import cpp as _cpp
from . import go as _go
from . import java as _java
from . import js as _js
from . import kotlin as _kotlin
from . import rust as _rust
from . import swift as _swift
from ..ir.model import EnumRef, ListOf, MapOf, MsgRef, Scalar, Schema, ServiceDef, TypeRef

# Compiled targets whose generated code imports an external CBOR runtime module.
# Maps lang -> (output path relative to its lang dir, vendored resource file).
# Python/TS use the IR-driven runtime codec (the installed package), so they have
# nothing to emit here.
_RUNTIMES: dict[str, tuple[str, str]] = {
    "rust": ("cbor.rs", "cbor.rs"),          # generated api.rs: `use crate::cbor::Cbor`
    "cpp": ("taut/cbor.hpp", "cbor.hpp"),    # generated api.hpp: `#include "taut/cbor.hpp"`
    "swift": ("cbor.swift", "cbor.swift"),   # same-module Cbor / encode / decode
    "go": ("cbor.go", "cbor.go"),            # same-package Cbor / Encode / Decode
    "kotlin": ("cbor.kt", "cbor.kt"),        # same-package Cbor / encode / decode
    "js": ("cbor.js", "cbor.js"),            # require("./cbor.js")
    "java": ("Cbor.java", "Cbor.java"),      # same-package taut.Cbor / KV
}


def _runtime_source(resource: str) -> str:
    return resources.files("taut.gen.runtime").joinpath(resource).read_text(encoding="utf-8")


def _attr(name: str) -> str:
    return name.replace(".", "_")


# =============================================================================
# Python
# =============================================================================

def _py_ty(t: TypeRef | None) -> str:
    if t is None:
        return "None"
    if isinstance(t, Scalar):
        return {"int": "int", "str": "str", "bytes": "bytes", "bool": "bool"}[t.kind]
    if isinstance(t, (EnumRef, MsgRef)):
        return t.name
    if isinstance(t, ListOf):
        return f"list[{_py_ty(t.elem)}]"
    if isinstance(t, MapOf):
        return f"dict[{_py_ty(t.key)}, {_py_ty(t.value)}]"
    raise TypeError(t)


def python_api(schema: Schema, forward_compat: bool = False) -> str:
    out = ['"""GENERATED native Python types — do not edit."""',
           "from __future__ import annotations",
           "from dataclasses import dataclass",
           "from enum import Enum", ""]
    for e in schema.enums.values():
        out.append(f"class {e.name}(Enum):")
        for m, v in e.members.items():
            out.append(f"    {m} = {v}")
        out.append("")
    for m in schema.messages.values():
        out.append("@dataclass(slots=True)")
        out.append(f"class {m.name}:")
        if not m.fields:
            out.append("    pass")
        for f in m.fields:
            ann = f"{_py_ty(f.type)} | None" if f.optional else _py_ty(f.type)
            out.append(f"    {f.name}: {ann}")
        out.append("")
    return "\n".join(out) + "\n"


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
        return {"int": "number", "str": "string", "bytes": "Uint8Array", "bool": "boolean"}[t.kind]
    if isinstance(t, (EnumRef, MsgRef)):
        return t.name
    if isinstance(t, ListOf):
        return f"{_ts_ty(t.elem)}[]"
    if isinstance(t, MapOf):
        return f"Record<string, {_ts_ty(t.value)}>"
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
           'import type { tautClient } from "../../../../trial/ts/src/client.ts";',
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
        return {"int": "i64", "str": "String", "bytes": "Vec<u8>", "bool": "bool"}[t.kind]
    if isinstance(t, (EnumRef, MsgRef)):
        return t.name
    if isinstance(t, ListOf):
        return f"Vec<{_rs_ty(t.elem)}>"
    if isinstance(t, MapOf):
        return f"std::collections::BTreeMap<{_rs_ty(t.key)}, {_rs_ty(t.value)}>"
    raise TypeError(t)


def rust_api(schema: Schema, forward_compat: bool = False) -> str:
    out = ["// GENERATED native Rust types + codec — do not edit.", "#![allow(dead_code)]",
           "use crate::cbor::Cbor;", ""]
    for e in schema.enums.values():
        out += _rust._emit_enum(e.name, e.members) + [""]
    for m in schema.messages.values():
        out += _rust._emit_message(m, forward_compat) + [""]
    return "\n".join(out) + "\n"


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
        return {"int": "long long", "str": "std::string_view", "bytes": "std::string_view", "bool": "bool"}[t.kind]
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
        return {"int": "Int64", "str": "String", "bytes": "[UInt8]", "bool": "Bool"}[t.kind]
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
        return {"int": "int64", "str": "string", "bytes": "[]byte", "bool": "bool"}[t.kind]
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
        return {"int": "Long", "str": "String", "bytes": "ByteArray", "bool": "Boolean"}[t.kind]
    if isinstance(t, (EnumRef, MsgRef)):
        return t.name
    if isinstance(t, ListOf):
        return f"List<{_kt_ty(t.elem)}>"
    if isinstance(t, MapOf):
        return f"Map<{_kt_ty(t.key)}, {_kt_ty(t.value)}>"
    raise TypeError(t)


def kotlin_api(schema: Schema, forward_compat: bool = False) -> str:
    return _kotlin.emit_types(schema, forward_compat)


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
        return {"int": "long", "str": "String", "bytes": "byte[]", "bool": "boolean"}[t.kind]
    if isinstance(t, (EnumRef, MsgRef)):
        return t.name
    if isinstance(t, ListOf):
        return f"java.util.List<{_java_ty(t.elem)}>"
    if isinstance(t, MapOf):
        return f"java.util.Map<{_java_ty(t.key)}, {_java_ty(t.value)}>"
    raise TypeError(t)


def java_api(schema: Schema, forward_compat: bool = False) -> str:
    return _java.emit_types(schema, forward_compat)


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


def emit(
    schema: Schema,
    out_dir: Path,
    *,
    langs: list[str] | None = None,
    services: list[str] | None = None,
    runtime: bool = False,
    forward_compat: bool = False,
) -> list[Path]:
    """Generate per-language code from an IR (the engine behind the `tautc` CLI).

    - `langs`: subset of {python, typescript, rust, cpp}; default all.
    - `services`: services to emit client/server for; default = every service in
      the schema. Pass `[]` for **api only** (native types + encoders/decoders,
      no RPC stubs) — the common build-script case for compiled targets.
    - `runtime`: when True, also emit the vendored CBOR runtime for compiled
      targets (`rust` -> `cbor.rs`, `cpp` -> `taut/cbor.hpp`) so the generated
      code is self-contained. Off by default — emitted only on demand.
    - `forward_compat`: when True, generated structs carry a `wire_residual` field
      that preserves unknown/newer-version tags (Rust today). Off by default.
      An IR that declares extensions requires it for compiled targets (D14:
      extensions ride the residual space) — otherwise generation is a build error.

    `api.{ext}` (types + codec) is always written per language; client/server are
    `client.{ext}` for a lone service, `client_{svc}.{ext}` when several.
    """
    lang_keys = list(langs) if langs is not None else list(_LANGS)
    unknown = [l for l in lang_keys if l not in _LANGS]
    if unknown:
        raise ValueError(f"unknown lang(s) {unknown}; known: {sorted(_LANGS)}")
    _GENERATED = {"rust", "cpp", "swift", "go", "kotlin", "js", "java"}
    if schema.extensions and not forward_compat and (_GENERATED & set(lang_keys)):
        raise ValueError(
            "this IR declares extensions; generating a typed target "
            f"({'/'.join(sorted(_GENERATED))}) requires forward_compat (extensions ride "
            "the residual space) — pass --forward-compat"
        )
    svc_names = list(services) if services is not None else list(schema.services)
    missing = [s for s in svc_names if s not in schema.services]
    if missing:
        raise ValueError(f"unknown service(s) {missing}; known: {sorted(schema.services)}")
    multi = len(svc_names) > 1
    written: list[Path] = []
    for lang in lang_keys:
        ext, api_fn, client_fn, server_fn = _LANGS[lang]
        d = out_dir / lang
        d.mkdir(parents=True, exist_ok=True)
        api_path = d / f"api.{ext}"
        api_path.write_text(api_fn(schema, forward_compat=forward_compat))
        written.append(api_path)
        if runtime and lang in _RUNTIMES:
            rel, resource = _RUNTIMES[lang]
            rt_path = d / rel
            rt_path.parent.mkdir(parents=True, exist_ok=True)
            rt_path.write_text(_runtime_source(resource))
            written.append(rt_path)
        for sname in svc_names:
            svc = schema.services[sname]
            suffix = f"_{sname}" if multi else ""
            for stem, fn in (("client", client_fn), ("server", server_fn)):
                path = d / f"{stem}{suffix}.{ext}"
                path.write_text(fn(schema, svc))
                written.append(path)
    if "python" in lang_keys and svc_names:
        # Python output is a package (client/server use relative imports).
        init = out_dir / "python" / "__init__.py"
        init.write_text("from .api import *  # noqa: F401,F403\n")
        written.append(init)
    return written


def emit_all(schema: Schema, service_name: str, out_dir: Path) -> list[Path]:
    """Back-compat: api + client/server for one service, all languages."""
    return emit(schema, out_dir, services=[service_name])
