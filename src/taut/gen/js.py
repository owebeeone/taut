"""JavaScript code generator — ES classes + a deterministic-CBOR codec, paired
with the vendored `cbor.js` runtime (CommonJS; emitted by `tautc gen --lang js
--with-runtime`). Enums are frozen name->wire objects (a field holds the wire
int); optionals are nullable; forward-compat residual rides along (cbor.js's
encode sorts map keys). Integers are JS numbers (safe to 2^53, like the TS codec).
"""

from __future__ import annotations

from ..ir.model import EnumRef, FieldDef, ListOf, MapOf, MsgRef, Scalar, Schema, TypeRef


def _enc(t: TypeRef, expr: str) -> str:
    if isinstance(t, Scalar):
        return {"int": f"CInt({expr})", "str": f"CText({expr})",
                "bytes": f"CBytes({expr})", "bool": f"CBool({expr})"}[t.kind]
    if isinstance(t, EnumRef):
        return f"CInt({expr})"          # enum value is its wire int
    if isinstance(t, MsgRef):
        return f"{expr}.toCbor()"
    if isinstance(t, ListOf):
        return f"CArr({expr}.map((e) => {_enc(t.elem, 'e')}))"
    if isinstance(t, MapOf):  # Map -> key-sorted array of {1:k, 2:v}
        return (f"CArr([...{expr}.entries()].sort((a, b) => a[0] < b[0] ? -1 : a[0] > b[0] ? 1 : 0)"
                f".map(([k, v]) => CMap([[1, {_enc(t.key, 'k')}], [2, {_enc(t.value, 'v')}]])))")
    raise TypeError(t)


def _dec(t: TypeRef, expr: str) -> str:
    if isinstance(t, Scalar):
        return {"int": f"{expr}.i", "str": f"{expr}.s",
                "bytes": f"{expr}.b", "bool": f"({expr}.i !== 0)"}[t.kind]
    if isinstance(t, EnumRef):
        return f"{expr}.i"
    if isinstance(t, MsgRef):
        return f"{t.name}.fromCbor({expr})"
    if isinstance(t, ListOf):
        return f"{expr}.arr.map((e) => {_dec(t.elem, 'e')})"
    if isinstance(t, MapOf):
        return (f"new Map({expr}.arr.map((e) => "
                f"[{_dec(t.key, 'cget(e, 1)')}, {_dec(t.value, 'cget(e, 2)')}]))")
    raise TypeError(t)


def _emit_enum(name: str, members: dict[str, int]) -> list[str]:
    body = ", ".join(f"{m}: {v}" for m, v in members.items())
    return [f"const {name} = Object.freeze({{ {body} }});"]


def _emit_message(msg, forward_compat: bool = False) -> list[str]:
    wire = list(msg.wire_fields())
    out = [f"class {msg.name} {{", "  constructor(o = {}) {"]
    for f in msg.fields:
        out.append(f"    this.{f.name} = o.{f.name};")
    if forward_compat:
        out.append("    this.wireResidual = o.wireResidual || [];")
    out.append("  }")
    # toCbor
    out.append("  toCbor() {")
    out.append("    const m = [")
    for f in wire:
        fn = f"this.{f.name}"
        if f.optional:
            enc = f"({fn} != null ? {_enc(f.type, fn)} : CNull())"
        else:
            enc = _enc(f.type, fn)
        out.append(f"      [{f.tag}, {enc}],")
    out.append("    ];")
    if forward_compat:
        out.append("    for (const kv of this.wireResidual) m.push(kv);") # encode sorts
    out.append("    return CMap(m);")
    out.append("  }")
    # fromCbor
    out.append("  static fromCbor(c) {")
    out.append(f"    const v = new {msg.name}();")
    for f in msg.fields:
        if f.transient:
            continue
        fn = f"v.{f.name}"
        if f.optional:
            out.append(f"    {{ const f = cget(c, {f.tag}); {fn} = isNull(f) ? null : {_dec(f.type, 'f')}; }}")
        else:
            out.append(f"    {fn} = {_dec(f.type, f'cget(c, {f.tag})')};")
    if forward_compat:
        known = ", ".join(str(f.tag) for f in wire)
        out.append(f"    {{ const k = new Set([{known}]); v.wireResidual = cmapEntries(c).filter((kv) => !k.has(kv[0])); }}")
    out.append("    return v;")
    out.append("  }")
    out.append("}")
    return out


def emit_types(schema: Schema, forward_compat: bool = False) -> str:
    out = ['"use strict";',
           "// GENERATED native JS types + codec — do not edit. Pairs with cbor.js.",
           'const { CInt, CText, CBytes, CBool, CArr, CMap, CNull, cget, cmapEntries, isNull } = require("./cbor.js");',
           ""]
    names = []
    for e in schema.enums.values():
        out += _emit_enum(e.name, e.members) + [""]
        names.append(e.name)
    for m in schema.messages.values():
        out += _emit_message(m, forward_compat) + [""]
        names.append(m.name)
    out.append("module.exports = { " + ", ".join(names) + " };")
    return "\n".join(out) + "\n"
