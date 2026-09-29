"""Java code generator — plain classes + a deterministic-CBOR codec, paired with
the vendored `Cbor.java` runtime (`tautc gen --lang java --with-runtime`). Per the
v0.3 call: mutable public fields, default `equals` (keep it simple). Enums carry
the wire value; optionals use boxed/reference types; forward-compat residual rides
along (Cbor.encode sorts map keys).

Note: classes are emitted package-private into one `api.java` (same `package taut`
as the runtime) — the simple single-file form. A public/multi-file projection is a
later refinement; Java also can't name a field after a keyword (no escape), unlike
the backtick languages.

Names (TautV010Plan.md §0). Java reads a name in an expression as a variable before a
class, and a class before a package, so a field hides whatever shares its name wherever
its class's code calls through that name: a field `m` hid toCbor's local `m`, and a field
`java` the package in `java.util.List.of`. So the codec names nothing a field can be named:
- every parameter, local and lambda parameter it declares starts with `$`, which a taut
  field name, a Python identifier, never holds;
- a message's codec is a class of its own beside it, `<Message>$Codec`, where none of the
  message's fields is in scope to hide `Cbor`, a message or enum class, or the package
  `java`; the message's `toCbor` and `fromCbor` call it, and the message's class names a
  class only as a type, where no field can hide it;
- nothing is imported, since an import clashes with a message of its name: the codec spells
  java.util's classes in full.
Enums keep their code: their constants are upper case, so none shares a name it uses.
"""

from __future__ import annotations

from ..ir.model import MISSING_OK, EnumRef, FieldDef, ListOf, MapOf, MsgRef, Scalar, Schema, TypeRef


def _java_ty(t: TypeRef, boxed: bool = False) -> str:
    if isinstance(t, Scalar):
        prim = {"int": "long", "str": "String", "bytes": "byte[]", "bool": "boolean", "float": "double"}[t.kind]
        box = {"int": "Long", "str": "String", "bytes": "byte[]", "bool": "Boolean", "float": "Double"}[t.kind]
        return box if boxed else prim
    if isinstance(t, (EnumRef, MsgRef)):
        return t.name
    if isinstance(t, ListOf):
        return f"java.util.List<{_java_ty(t.elem, boxed=True)}>"
    if isinstance(t, MapOf):
        return f"java.util.Map<{_java_ty(t.key, boxed=True)}, {_java_ty(t.value, boxed=True)}>"
    raise TypeError(t)


def _field_type(f: FieldDef) -> str:
    return _java_ty(f.type, boxed=f.optional)


def _param(depth: int) -> str:
    """The parameter of a lambda `depth` lambdas deep: `$e`, then `$e1`, `$e2`, ... A list's
    items and a map's entries are each read by a lambda, and lists nest and a map may sit
    in a list, but Java refuses a lambda parameter that redeclares an enclosing one."""
    return "$e" if depth == 0 else f"$e{depth}"


def _enc(t: TypeRef, expr: str, depth: int = 0) -> str:
    if isinstance(t, Scalar):
        return {"int": f"Cbor.int_({expr})", "str": f"Cbor.text({expr})",
                "bytes": f"Cbor.bytes({expr})", "bool": f"Cbor.bool({expr})",
                "float": f"Cbor.float_({expr})"}[t.kind]
    if isinstance(t, EnumRef):
        return f"Cbor.int_({expr}.wire)"
    if isinstance(t, MsgRef):
        return f"{expr}.toCbor()"
    e = _param(depth)
    if isinstance(t, ListOf):
        return f"Cbor.arr({expr}.stream().map({e} -> {_enc(t.elem, e, depth + 1)}).toList())"
    if isinstance(t, MapOf):  # ascending keys: an int or bool by value, a str by code point
        if isinstance(t.key, Scalar) and t.key.kind == "str":
            entries = f"Cbor.sortedByCodePoint({expr})"
        else:
            entries = f"new java.util.TreeMap<>({expr})"
        return (f"Cbor.arr({entries}.entrySet().stream().map({e} -> "
                f"Cbor.map(java.util.List.of(new KV(1, {_enc(t.key, f'{e}.getKey()', depth + 1)}), "
                f"new KV(2, {_enc(t.value, f'{e}.getValue()', depth + 1)})))).toList())")
    raise TypeError(t)


def _dec(t: TypeRef, expr: str, depth: int = 0) -> str:
    if isinstance(t, Scalar):
        return {"int": f"{expr}.asInt()", "str": f"{expr}.asText()",
                "bytes": f"{expr}.asBytes()", "bool": f"{expr}.asBool()",
                "float": f"{expr}.asFloat()"}[t.kind]
    if isinstance(t, EnumRef):
        return f"{t.name}.fromWire({expr}.asInt())"
    if isinstance(t, MsgRef):
        return f"{t.name}.fromCbor({expr})"
    e = _param(depth)
    if isinstance(t, ListOf):
        return f"{expr}.asArray().stream().map({e} -> {_dec(t.elem, e, depth + 1)}).toList()"
    if isinstance(t, MapOf):  # entry maps: keys 1 and 2 checked first, a repeated key refused
        return (f"Cbor.decodeMap({expr}, {e} -> {_dec(t.key, f'{e}.get(1)', depth + 1)}, "
                f"{e} -> {_dec(t.value, f'{e}.get(2)', depth + 1)})")
    raise TypeError(t)


def _emit_enum(name: str, members: dict[str, int]) -> list[str]:
    consts = ", ".join(f"{m.upper()}({v})" for m, v in members.items())
    return [
        f"enum {name} {{",
        f"    {consts};",
        "    final long wire;",
        f"    {name}(long $w) {{ this.wire = $w; }}",
        f"    static {name} fromWire(long $v) {{",
        "        for (var $e : values()) {",
        "            if ($e.wire == $v) {",
        "                return $e;",
        "            }",
        "        }",
        f"        throw Cbor.DecodeError.unknownEnum(\"{name}\", $v);",
        "    }",
        "}",
    ]


def _codec(msg) -> str:
    """The class that holds `msg`'s codec. `$` keeps its name from any message's."""
    return f"{msg.name}$Codec"


def _emit_message(msg, forward_compat: bool = False) -> list[str]:
    """The message's class: its fields, and a toCbor and fromCbor that call its codec."""
    out = [f"class {msg.name} {{"]
    for f in msg.fields:
        out.append(f"    public {_field_type(f)} {f.name};")
    if forward_compat:
        out.append("    public java.util.List<KV> wireResidual = new java.util.ArrayList<>();")
    out.append(f"    Cbor toCbor() {{ return {_codec(msg)}.toCbor(this); }}")
    out.append(f"    static {msg.name} fromCbor(Cbor $c) {{ return {_codec(msg)}.fromCbor($c); }}")
    out.append("}")
    return out


def _emit_codec(msg, forward_compat: bool = False) -> list[str]:
    """The message's codec, a class beside it, where none of its fields is in scope."""
    codec = _codec(msg)
    out = [f"final class {codec} {{", f"    private {codec}() {{}}"]
    out.append(f"    static Cbor toCbor({msg.name} $self) {{")
    out.append("        var $m = new java.util.ArrayList<KV>();")
    for f in msg.wire_fields():
        value = f"$self.{f.name}"
        if f.optional:
            enc = f"{value} != null ? {_enc(f.type, value)} : Cbor.NUL"
        else:
            enc = _enc(f.type, value)
        out.append(f"        $m.add(new KV({f.tag}, {enc}));")
    if forward_compat:
        out.append("        $m.addAll($self.wireResidual);")  # Cbor.encode sorts -> canonical
    out.append("        return Cbor.map($m);")
    out.append("    }")
    out.append(f"    static {msg.name} fromCbor(Cbor $c) {{")
    # A message is a map even when it has no field to read (CD-E5).
    out.append("        if ($c.kind != Cbor.MAP) {")
    out.append("            throw Cbor.DecodeError.wrongType(\"map\");")
    out.append("        }")
    out.append(f"        {msg.name} $v = new {msg.name}();")
    for f in msg.fields:
        if f.transient:
            continue  # native-only; left at Java default
        if f.optional == MISSING_OK:  # an absent key reads as null, like a present null
            out.append(f"        {{ Cbor $f = $c.getOpt({f.tag}); "
                       f"$v.{f.name} = ($f == null || $f.isNull()) ? null : {_dec(f.type, '$f')}; }}")
        elif f.optional:
            out.append(f"        {{ Cbor $f = $c.get({f.tag}); "
                       f"$v.{f.name} = $f.isNull() ? null : {_dec(f.type, '$f')}; }}")
        else:
            out.append(f"        $v.{f.name} = {_dec(f.type, f'$c.get({f.tag})')};")
    if forward_compat:  # every entry whose key no field has
        known = " && ".join(f"$kv.k != {f.tag}" for f in msg.wire_fields())
        out.append("        for (KV $kv : $c.mapEntries()) {")
        if known:
            out += [f"            if ({known}) {{", "                $v.wireResidual.add($kv);",
                    "            }"]
        else:
            out.append("            $v.wireResidual.add($kv);")
        out.append("        }")
    out.append("        return $v;")
    out.append("    }")
    out.append("}")
    return out


def emit_types(schema: Schema, forward_compat: bool = False) -> str:
    out = ["// GENERATED native Java types + codec — do not edit. Pairs with Cbor.java.",
           "// Each message's codec is its own class, <Message>$Codec, where no field hides a name.",
           "package taut;", ""]
    for e in schema.enums.values():
        out += _emit_enum(e.name, e.members) + [""]
    for m in schema.messages.values():
        out += _emit_message(m, forward_compat) + [""]
        out += _emit_codec(m, forward_compat) + [""]
    return "\n".join(out) + "\n"
