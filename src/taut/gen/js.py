"""JavaScript code generator — ES classes + a deterministic-CBOR codec, paired
with the vendored `cbor.js` runtime (CommonJS; emitted by `tautc gen --lang js
--with-runtime`). Enums are frozen name->wire objects (a field holds the wire
int); optionals are nullable, and an `optional=MISSING_OK` field also reads an
absent key as null; forward-compat residual rides along (cbor.js's
encode sorts map keys). Codec integer fields are BigInt so every i64 value is
exact.

Each class is a decode root (TautCheckedDecode.md CD-B3, TautOptions.md OPT-L6): it
carries its effective bounds as read-only `MAX_DEPTH` and `MAX_ENCODED_LEN` (null for
none), resolved by `taut.ir.options.effective` here at generation, and `decode(bytes)`
applies both through cbor.js's raw decode before `fromCbor`.
"""

from __future__ import annotations

from collections.abc import Iterator
from types import MappingProxyType

from ..ir.model import MISSING_OK, EnumRef, FieldDef, ListOf, MapOf, MsgRef, Scalar, Schema, TypeRef
from ..ir.options import effective
from .names import Clash, scope_clashes

# The names api.js takes from cbor.js, in the order its `require` lists them.
_IMPORTS = ("CInt", "CFloat", "CText", "CBytes", "CBool", "CArr", "CMap", "CNull", "cget",
            "cgetOrNull", "mapFromCbor", "cmapEntries", "compareCodePoints", "isNull", "expectInt",
            "expectFloat", "expectText", "expectBytes", "expectBool", "expectArray", "expectMap",
            "enumFromWire", "enumFromCbor", "decode")

RESERVED_FIELD_NAMES = MappingProxyType({
    "toCbor": "a method, which the instance's own field would hide",
    "wireResidual": "the forward-compat residual field",
    "__proto__": "the prototype, which the constructor would replace",
})
"""Field names a class cannot take: the constructor sets each field on the instance, where it
hides the class's method of its name, or, for `__proto__`, replaces the prototype that holds
them. The static members sit on the class and meet no field."""

RESERVED_TYPE_NAMES = MappingProxyType({
    **dict.fromkeys(_IMPORTS, "a name api.js takes from cbor.js"),
    **dict.fromkeys("Map Object Set".split(), "a global the code uses"),
    **dict.fromkeys("__dirname __filename exports module require".split(),
                    "a name CommonJS gives every module"),
    **dict.fromkeys("bytes c e f v value".split(), "a parameter or local that hides the class"),
})
"""Message and enum names api.js cannot take: a class or constant there redeclares a name it
takes from cbor.js or CommonJS gives it, shadows a global its code uses, or is hidden by a
parameter or local where the code names it. An enum's derived names are `name_clashes`'s."""


def _module_names(schema: Schema) -> Iterator[tuple[str, str, str]]:
    """Each name api.js declares, and the enum or message it is for."""
    for e in schema.enums.values():
        yield from ((name, f"enum {e.name}", "enum") for name in (
            e.name, f"{e.name}Values", f"{e.name}FromWire", f"{e.name}FromCbor"))
    for m in schema.messages.values():
        yield m.name, m.name, "message"


def name_clashes(schema: Schema) -> list[Clash]:
    """An enum's `EValues`, `EFromWire` or `EFromCbor` meeting another name of api.js (a
    message `ModeValues`, or `mapFromCbor` for an enum `map`)."""
    return scope_clashes(_module_names(schema), RESERVED_TYPE_NAMES)


def _key_order(key: TypeRef) -> str:
    """The comparator a map<K,V> field's entries are sorted by before encoding (D24). A
    str key sorts by code point with cbor.js's `compareCodePoints`, Python's order: JS
    `<` compares UTF-16 code units, which puts U+10000 before U+FFFF. An int or bool key
    compares with `<`."""
    if isinstance(key, Scalar) and key.kind == "str":
        return "(a, b) => compareCodePoints(a[0], b[0])"
    return "(a, b) => a[0] < b[0] ? -1 : a[0] > b[0] ? 1 : 0"


def _enc(t: TypeRef, expr: str) -> str:
    if isinstance(t, Scalar):
        return {"int": f"CInt({expr})", "str": f"CText({expr})",
                "bytes": f"CBytes({expr})", "bool": f"CBool({expr})",
                "float": f"CFloat({expr})"}[t.kind]
    if isinstance(t, EnumRef):
        return f"CInt({expr})"          # enum value is its wire int
    if isinstance(t, MsgRef):
        return f"{expr}.toCbor()"
    if isinstance(t, ListOf):
        return f"CArr({expr}.map((e) => {_enc(t.elem, 'e')}))"
    if isinstance(t, MapOf):  # Map -> key-sorted array of {1:k, 2:v}
        return (f"CArr([...{expr}.entries()].sort({_key_order(t.key)})"
                f".map(([k, v]) => CMap([[1, {_enc(t.key, 'k')}], [2, {_enc(t.value, 'v')}]])))")
    raise TypeError(t)


def _dec(t: TypeRef, expr: str) -> str:
    if isinstance(t, Scalar):
        return {"int": f"expectInt({expr})", "str": f"expectText({expr})",
                "bytes": f"expectBytes({expr})", "bool": f"expectBool({expr})",
                "float": f"expectFloat({expr})"}[t.kind]
    if isinstance(t, EnumRef):
        return f"{t.name}FromCbor({expr})"
    if isinstance(t, MsgRef):
        return f"{t.name}.fromCbor({expr})"
    if isinstance(t, ListOf):
        return f"expectArray({expr}).map((e) => {_dec(t.elem, 'e')})"
    if isinstance(t, MapOf):  # entries checked for keys 1 and 2 first; a repeated key is refused
        return (f"mapFromCbor(new Map(), {expr}, (key) => {_dec(t.key, 'key')}, "
                f"(value) => {_dec(t.value, 'value')})")
    raise TypeError(t)


def _emit_enum(name: str, members: dict[str, int]) -> list[str]:
    body = ", ".join(f"{m}: {v}" for m, v in members.items())
    values = ", ".join(str(v) for v in members.values())
    return [
        f"const {name} = Object.freeze({{ {body} }});",
        f"const {name}Values = new Set([{values}]);",
        f"function {name}FromWire(v) {{ return enumFromWire(v, \"{name}\", {name}Values); }}",
        f"function {name}FromCbor(c) {{ return enumFromCbor(c, \"{name}\", {name}Values); }}",
    ]


def _emit_message(schema: Schema, msg, forward_compat: bool = False) -> list[str]:
    wire = list(msg.wire_fields())
    max_depth = effective(schema, "max_depth", message=msg.name)
    max_encoded_len = effective(schema, "max_encoded_len", message=msg.name)
    out = [
        f"class {msg.name} {{",
        # The decode root's effective bounds (CD-B3), read-only so no caller can change them.
        f"  static get MAX_DEPTH() {{ return {max_depth}; }}",
        f"  static get MAX_ENCODED_LEN() {{ return {'null' if max_encoded_len is None else max_encoded_len}; }}",
        "  constructor(o = {}) {",
    ]
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
    if not wire:  # a message with no fields must still be a map (CD-E5)
        out.append("    expectMap(c);")
    out.append(f"    const v = new {msg.name}();")
    for f in msg.fields:
        if f.transient:
            continue
        fn = f"v.{f.name}"
        if f.optional:
            get = "cgetOrNull" if f.optional == MISSING_OK else "cget"
            out.append(f"    {{ const f = {get}(c, {f.tag}); {fn} = isNull(f) ? null : {_dec(f.type, 'f')}; }}")
        else:
            out.append(f"    {fn} = {_dec(f.type, f'cget(c, {f.tag})')};")
    if forward_compat:
        known = ", ".join(str(f.tag) for f in wire)
        out.append(f"    {{ const k = new Set([{known}]); v.wireResidual = cmapEntries(c).filter((kv) => !k.has(kv[0])); }}")
    out.append("    return v;")
    out.append("  }")
    # decode: bytes -> this message, under its own bounds and no caller's (CD-B3)
    out.append("  static decode(bytes) {")
    out.append(f"    return {msg.name}.fromCbor(decode(bytes, "
               f"{{ maxDepth: {msg.name}.MAX_DEPTH, maxEncodedLen: {msg.name}.MAX_ENCODED_LEN }}));")
    out.append("  }")
    out.append("}")
    return out


def emit_types(schema: Schema, forward_compat: bool = False) -> str:
    out = ['"use strict";',
           "// GENERATED native JS types + codec — do not edit. Pairs with cbor.js.",
           f'const {{ {", ".join(_IMPORTS)} }} = require("./cbor.js");',
           ""]
    names = []
    for e in schema.enums.values():
        out += _emit_enum(e.name, e.members) + [""]
        names.append(e.name)
        names.append(f"{e.name}FromWire")
        names.append(f"{e.name}FromCbor")
    for m in schema.messages.values():
        out += _emit_message(schema, m, forward_compat) + [""]
        names.append(m.name)
    out.append("module.exports = { " + ", ".join(names) + " };")
    return "\n".join(out) + "\n"
