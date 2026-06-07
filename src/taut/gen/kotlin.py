"""Kotlin code generator — mutable `data class`es + a deterministic-CBOR codec,
mirroring the other compiled targets. Pairs with the vendored `cbor.kt` runtime
(emitted by `tautc gen --lang kotlin --with-runtime`); both are `package taut`.

Design (per the v0.3 discussion): mutable `var` data classes with default
`equals`/`hashCode`/`copy` (the ByteArray-equals nuance is deferred). Optionals
are nullable `T?`; enums are `enum class` carrying the wire value; Kotlin keywords
get backtick-escaped. Kotlin's `encode` sorts map keys, so forward-compat residual
just rides along (no merge).
"""

from __future__ import annotations

from ..ir.model import EnumRef, FieldDef, ListOf, MsgRef, Scalar, Schema, TypeRef

_KT_KEYWORDS = frozenset("""
as as? break class continue do else false for fun if in in? interface is is! null
object package return super this throw true try typealias typeof val var when while
open data sealed inner companion annotation abstract final override public private
protected internal lateinit vararg const inline operator infix external suspend
tailrec reified crossinline noinline expect actual enum
""".split())


def _id(name: str) -> str:
    return f"`{name}`" if name in _KT_KEYWORDS else name


def _kt_ty(t: TypeRef) -> str:
    if isinstance(t, Scalar):
        return {"int": "Long", "str": "String", "bytes": "ByteArray", "bool": "Boolean"}[t.kind]
    if isinstance(t, (EnumRef, MsgRef)):
        return t.name
    if isinstance(t, ListOf):
        return f"List<{_kt_ty(t.elem)}>"
    raise TypeError(t)


def _field_type(f: FieldDef) -> str:
    base = _kt_ty(f.type)
    return f"{base}?" if f.optional else base


def _default(t: TypeRef) -> str:
    if isinstance(t, Scalar):
        return {"int": "0L", "str": '""', "bytes": "ByteArray(0)", "bool": "false"}[t.kind]
    if isinstance(t, ListOf):
        return "emptyList()"
    raise TypeError(f"no Kotlin default for transient field of type {t!r}")


def _enc(t: TypeRef, expr: str) -> str:
    if isinstance(t, Scalar):
        return {"int": f"Cbor.int({expr})", "str": f"Cbor.text({expr})",
                "bytes": f"Cbor.bytes({expr})", "bool": f"Cbor.bool({expr})"}[t.kind]
    if isinstance(t, EnumRef):
        return f"Cbor.int({expr}.wire)"
    if isinstance(t, MsgRef):
        return f"{expr}.toCbor()"
    if isinstance(t, ListOf):
        return f"Cbor.arr({expr}.map {{ {_enc(t.elem, 'it')} }})"
    raise TypeError(t)


def _dec(t: TypeRef, expr: str) -> str:
    if isinstance(t, Scalar):
        return {"int": f"{expr}.intVal", "str": f"{expr}.textVal",
                "bytes": f"{expr}.bytesVal", "bool": f"{expr}.boolVal"}[t.kind]
    if isinstance(t, EnumRef):
        return f"{t.name}.fromWire({expr}.intVal)"
    if isinstance(t, MsgRef):
        return f"{t.name}.fromCbor({expr})"
    if isinstance(t, ListOf):
        return f"{expr}.arrVal.map {{ {_dec(t.elem, 'it')} }}"
    raise TypeError(t)


def _emit_enum(name: str, members: dict[str, int]) -> list[str]:
    entries = ", ".join(f"{_id(m)}({v})" for m, v in members.items())
    return [
        f"enum class {name}(val wire: Long) {{",
        f"    {entries};",
        "    companion object { fun fromWire(v: Long) = values().first { it.wire == v } }",
        "}",
    ]


def _emit_message(msg, forward_compat: bool = False) -> list[str]:
    out = [f"data class {msg.name}("]
    for f in msg.fields:
        n, ft = _id(f.name), _field_type(f)
        if f.transient:
            out.append(f"    var {n}: {ft} = {'null' if f.optional else _default(f.type)},")
        elif f.optional:
            out.append(f"    var {n}: {ft} = null,")
        else:
            out.append(f"    var {n}: {ft},")
    if forward_compat:
        out.append("    var wireResidual: List<Pair<Long, Cbor>> = emptyList(),")
    out.append(") {")
    # toCbor
    out.append("    fun toCbor(): Cbor {")
    entries = []
    for f in msg.wire_fields():
        n = _id(f.name)
        if f.optional:
            enc = f"({n}?.let {{ {_enc(f.type, 'it')} }} ?: Cbor.nul)"
        else:
            enc = _enc(f.type, n)
        entries.append(f"{f.tag}L to {enc}")
    body = "listOf(" + ", ".join(entries) + ")"
    out.append(f"        return Cbor.map({body}{' + wireResidual' if forward_compat else ''})")
    out.append("    }")
    out.append("    companion object {")
    out.append(f"        fun fromCbor(c: Cbor): {msg.name} {{")
    out.append(f"            return {msg.name}(")
    for f in msg.fields:
        if f.transient:
            continue  # native-only; data-class default applies
        n = _id(f.name)
        if f.optional:
            dec = f"c.get({f.tag}).let {{ if (it.isNull) null else {_dec(f.type, 'it')} }}"
        else:
            dec = _dec(f.type, f"c.get({f.tag})")
        out.append(f"                {n} = {dec},")
    if forward_compat:
        known = ", ".join(f"{f.tag}L" for f in msg.wire_fields())
        out.append(f"                wireResidual = c.mapEntries.filter {{ it.first !in listOf({known}) }},")
    out.append("            )")
    out.append("        }")
    out.append("    }")
    out.append("}")
    return out


def emit_types(schema: Schema, forward_compat: bool = False) -> str:
    out = ["// GENERATED native Kotlin types + codec — do not edit.",
           "// Pairs with the vendored cbor.kt runtime (same package).",
           "package taut", ""]
    for e in schema.enums.values():
        out += _emit_enum(e.name, e.members) + [""]
    for m in schema.messages.values():
        out += _emit_message(m, forward_compat) + [""]
    return "\n".join(out) + "\n"
