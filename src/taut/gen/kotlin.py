"""Kotlin code generator — mutable `data class`es + a deterministic-CBOR codec,
mirroring the other compiled targets. Pairs with the vendored `cbor.kt` runtime
(emitted by `tautc gen --lang kotlin --with-runtime`); both are `package taut`.

Design (per the v0.3 discussion): mutable `var` data classes with default
`equals`/`hashCode`/`copy` (the ByteArray-equals nuance is deferred). Optionals
are nullable `T?`: an absent key is `MissingKey`, except under `optional=MISSING_OK`,
which reads it as null; enums are `enum class` carrying the wire value; Kotlin keywords
get backtick-escaped. Kotlin's `encode` sorts map keys, so forward-compat residual
just rides along (no merge).

Decode is bounded per root (D26, TautCheckedDecode.md CD-B3; TautOptions.md OPT-L6): each
message's companion holds `MAX_DEPTH` and `MAX_ENCODED_LEN`, its effective values as
`options.effective` resolves them here, and `decode(bytes)`, which applies both through the
runtime's raw `decode`. `fromCbor` reads a tree its caller decoded and applies none (G1).
"""

from __future__ import annotations

from typing import cast

from ..ir.model import MISSING_OK, EnumRef, FieldDef, ListOf, MapOf, MsgRef, Scalar, Schema, TypeRef
from ..ir.options import effective

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
        return {"int": "Long", "str": "String", "bytes": "ByteArray",
                "bool": "Boolean", "float": "Double"}[t.kind]
    if isinstance(t, (EnumRef, MsgRef)):
        return t.name
    if isinstance(t, ListOf):
        return f"List<{_kt_ty(t.elem)}>"
    if isinstance(t, MapOf):
        return f"Map<{_kt_ty(t.key)}, {_kt_ty(t.value)}>"
    raise TypeError(t)


def _field_type(f: FieldDef) -> str:
    base = _kt_ty(f.type)
    return f"{base}?" if f.optional else base


def _default(t: TypeRef) -> str:
    if isinstance(t, Scalar):
        return {"int": "0L", "str": '""', "bytes": "ByteArray(0)",
                "bool": "false", "float": "0.0"}[t.kind]
    if isinstance(t, ListOf):
        return "emptyList()"
    raise TypeError(f"no Kotlin default for transient field of type {t!r}")


def _enc(t: TypeRef, expr: str) -> str:
    if isinstance(t, Scalar):
        return {"int": f"Cbor.int({expr})", "str": f"Cbor.text({expr})",
                "bytes": f"Cbor.bytes({expr})", "bool": f"Cbor.bool({expr})",
                "float": f"Cbor.float({expr})"}[t.kind]
    if isinstance(t, EnumRef):
        return f"Cbor.int({expr}.wire)"
    if isinstance(t, MsgRef):
        return f"{expr}.toCbor()"
    if isinstance(t, ListOf):
        return f"Cbor.arr({expr}.map {{ {_enc(t.elem, 'it')} }})"
    if isinstance(t, MapOf):  # ascending keys: an int or bool by value, a str by code point
        order = "Cbor.codePointOrder" if isinstance(t.key, Scalar) and t.key.kind == "str" else ""
        return (f"Cbor.arr({expr}.toSortedMap({order}).map {{ "
                f"Cbor.map(listOf(1L to {_enc(t.key, 'it.key')}, 2L to {_enc(t.value, 'it.value')})) }})")
    raise TypeError(t)


def _dec(t: TypeRef, expr: str) -> str:
    if isinstance(t, Scalar):
        return {"int": f"{expr}.intVal", "str": f"{expr}.textVal",
                "bytes": f"{expr}.bytesVal", "bool": f"{expr}.boolVal",
                "float": f"{expr}.floatVal"}[t.kind]
    if isinstance(t, EnumRef):
        return f"{t.name}.fromWire({expr}.intVal)"
    if isinstance(t, MsgRef):
        return f"{t.name}.fromCbor({expr})"
    if isinstance(t, ListOf):
        return f"{expr}.arrVal.map {{ {_dec(t.elem, 'it')} }}"
    if isinstance(t, MapOf):  # entry checks and DuplicateMapKey: the runtime's mapFieldVal
        return (f"{expr}.mapFieldVal {{ "
                f"{_dec(t.key, 'it.get(1)')} to {_dec(t.value, 'it.get(2)')} }}")
    raise TypeError(t)


def _emit_enum(name: str, members: dict[str, int]) -> list[str]:
    entries = ", ".join(f"{_id(m)}({v})" for m, v in members.items())
    out = [
        f"enum class {name}(val wire: Long) {{",
        f"    {entries};",
        "    companion object {",
        f"        fun fromWire(v: Long): {name} {{",
        "            for (e in values()) if (e.wire == v) return e",
        f'            throw DecodeError.UnknownEnum("{name}", v)',
        "        }",
        "    }",
        "}",
    ]
    return out


def _bounds(schema: Schema, message: str) -> tuple[int, int | None]:
    """`(max_depth, max_encoded_len)` of a decode rooted at `message`: its effective values
    (TautOptions.md OPT-D3, OPT-D4), resolved once, here, at generation. None is no length
    bound."""
    return (cast(int, effective(schema, "max_depth", message=message)),
            cast("int | None", effective(schema, "max_encoded_len", message=message)))


def _emit_message(msg, bounds: tuple[int, int | None], forward_compat: bool = False) -> list[str]:
    # Kotlin refuses a `data class` without constructor parameters, so a message
    # with no fields is a plain class that keeps value equality.
    fieldless = not msg.fields and not forward_compat
    out = [f"{'class' if fieldless else 'data class'} {msg.name}("]
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
    if fieldless:
        out.append(f"    override fun equals(other: Any?): Boolean = other is {msg.name}")
        out.append("    override fun hashCode(): Int = 0")
    # toCbor. Under forward-compat the known entries meet the residual in `+`, where nothing
    # types them, so they name their type: kotlinc cannot infer T for the empty `listOf()` of a
    # message with no wire field (none, or only transient ones). Likewise its known tags below.
    out.append("    fun toCbor(): Cbor {")
    entries = []
    for f in msg.wire_fields():
        n = _id(f.name)
        if f.optional:
            enc = f"({n}?.let {{ {_enc(f.type, 'it')} }} ?: Cbor.nul)"
        else:
            enc = _enc(f.type, n)
        entries.append(f"{f.tag}L to {enc}")
    body = ("listOf<Pair<Long, Cbor>>(" if forward_compat else "listOf(") + ", ".join(entries) + ")"
    out.append(f"        return Cbor.map({body}{' + wireResidual' if forward_compat else ''})")
    out.append("    }")
    # The bounds of a decode rooted here and the typed entry point that applies them (CD-B3,
    # OPT-L6). The raw decode is named by its package: inside the companion, `decode` is this one.
    max_depth, max_encoded_len = bounds
    out.append("    companion object {")
    out.append(f"        const val MAX_DEPTH: Int = {max_depth}")
    out.append(f"        val MAX_ENCODED_LEN: Int? = {'null' if max_encoded_len is None else max_encoded_len}")
    out.append(f"        fun decode(bytes: ByteArray): {msg.name} = "
               "fromCbor(taut.decode(bytes, MAX_DEPTH, MAX_ENCODED_LEN))")
    out.append(f"        fun fromCbor(c: Cbor): {msg.name} {{")
    if not msg.wire_fields():
        # No field reads the input, and a message must still be a map (CD-E5).
        out += ["            if (c.kind != Cbor.MAP) {",
                '                throw DecodeError.WrongType("map")',
                "            }"]
    out.append(f"            return {msg.name}(")
    for f in msg.fields:
        if f.transient:
            continue  # native-only; data-class default applies
        n = _id(f.name)
        if f.optional == MISSING_OK:  # an absent key reads as null, like a present null
            dec = (f"c.getOrNull({f.tag})?.let "
                   f"{{ if (it.isNull) {{ null }} else {{ {_dec(f.type, 'it')} }} }}")
        elif f.optional:
            dec = f"c.get({f.tag}).let {{ if (it.isNull) null else {_dec(f.type, 'it')} }}"
        else:
            dec = _dec(f.type, f"c.get({f.tag})")
        out.append(f"                {n} = {dec},")
    if forward_compat:
        known = ", ".join(f"{f.tag}L" for f in msg.wire_fields())
        out.append(f"                wireResidual = c.mapEntries.filter {{ it.first !in listOf<Long>({known}) }},")
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
        out += _emit_message(m, _bounds(schema, m.name), forward_compat) + [""]
    return "\n".join(out) + "\n"
