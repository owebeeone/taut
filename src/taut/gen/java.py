"""Java code generator — plain classes + a deterministic-CBOR codec, paired with
the vendored `Cbor.java` runtime (`tautc gen --lang java --with-runtime`). Per the
v0.3 call: mutable public fields, default `equals` (keep it simple). Enums carry
the wire value; optionals use boxed/reference types; forward-compat residual rides
along (Cbor.encode sorts map keys).

Note: classes are emitted package-private into one `api.java` (same `package taut`
as the runtime) — the simple single-file form. A public/multi-file projection is a
later refinement; Java also can't name a field after a keyword (no escape), unlike
the backtick languages.
"""

from __future__ import annotations

from ..ir.model import EnumRef, FieldDef, ListOf, MapOf, MsgRef, Scalar, Schema, TypeRef


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


def _enc(t: TypeRef, expr: str) -> str:
    if isinstance(t, Scalar):
        return {"int": f"Cbor.int_({expr})", "str": f"Cbor.text({expr})",
                "bytes": f"Cbor.bytes({expr})", "bool": f"Cbor.bool({expr})",
                "float": f"Cbor.float_({expr})"}[t.kind]
    if isinstance(t, EnumRef):
        return f"Cbor.int_({expr}.wire)"
    if isinstance(t, MsgRef):
        return f"{expr}.toCbor()"
    if isinstance(t, ListOf):
        return f"Cbor.arr({expr}.stream().map(e -> {_enc(t.elem, 'e')}).toList())"
    if isinstance(t, MapOf):  # TreeMap -> ascending keys
        return (f"Cbor.arr(new java.util.TreeMap<>({expr}).entrySet().stream().map(e -> "
                f"Cbor.map(java.util.List.of(new KV(1, {_enc(t.key, 'e.getKey()')}), "
                f"new KV(2, {_enc(t.value, 'e.getValue()')})))).toList())")
    raise TypeError(t)


def _dec(t: TypeRef, expr: str) -> str:
    if isinstance(t, Scalar):
        return {"int": f"{expr}.asInt()", "str": f"{expr}.asText()",
                "bytes": f"{expr}.asBytes()", "bool": f"{expr}.asBool()",
                "float": f"{expr}.asFloat()"}[t.kind]
    if isinstance(t, EnumRef):
        return f"{t.name}.fromWire({expr}.asInt())"
    if isinstance(t, MsgRef):
        return f"{t.name}.fromCbor({expr})"
    if isinstance(t, ListOf):
        return f"{expr}.asArray().stream().map(e -> {_dec(t.elem, 'e')}).toList()"
    if isinstance(t, MapOf):
        return (f"{expr}.asArray().stream().collect(java.util.stream.Collectors.toMap("
                f"e -> {_dec(t.key, 'e.get(1)')}, e -> {_dec(t.value, 'e.get(2)')}, "
                f"(a, b) -> {{ throw Cbor.DecodeError.duplicateMapKey(0); }}, "
                f"java.util.LinkedHashMap::new))")
    raise TypeError(t)


def _emit_enum(name: str, members: dict[str, int]) -> list[str]:
    consts = ", ".join(f"{m.upper()}({v})" for m, v in members.items())
    return [
        f"enum {name} {{",
        f"    {consts};",
        "    final long wire;",
        f"    {name}(long w) {{ this.wire = w; }}",
        f"    static {name} fromWire(long v) {{ for (var e : values()) if (e.wire == v) return e; throw Cbor.DecodeError.unknownEnum(\"{name}\", v); }}",
        "}",
    ]


def _emit_message(msg, forward_compat: bool = False) -> list[str]:
    out = [f"class {msg.name} {{"]
    for f in msg.fields:
        out.append(f"    public {_field_type(f)} {f.name};")
    if forward_compat:
        out.append("    public java.util.List<KV> wireResidual = new java.util.ArrayList<>();")
    # toCbor
    out.append("    Cbor toCbor() {")
    out.append("        java.util.List<KV> m = new java.util.ArrayList<>();")
    for f in msg.wire_fields():
        if f.optional:
            enc = f"{f.name} != null ? {_enc(f.type, f.name)} : Cbor.NUL"
        else:
            enc = _enc(f.type, f.name)
        out.append(f"        m.add(new KV({f.tag}, {enc}));")
    if forward_compat:
        out.append("        m.addAll(wireResidual);")  # Cbor.encode sorts -> canonical
    out.append("        return Cbor.map(m);")
    out.append("    }")
    # fromCbor
    out.append(f"    static {msg.name} fromCbor(Cbor c) {{")
    out.append(f"        {msg.name} v = new {msg.name}();")
    for f in msg.fields:
        if f.transient:
            continue  # native-only; left at Java default
        if f.optional:
            out.append(f"        {{ Cbor f = c.get({f.tag}); v.{f.name} = f.isNull() ? null : {_dec(f.type, 'f')}; }}")
        else:
            out.append(f"        v.{f.name} = {_dec(f.type, f'c.get({f.tag})')};")
    if forward_compat:
        cond = " && ".join(f"kv.k != {f.tag}" for f in msg.wire_fields()) or "true"
        out.append(f"        for (KV kv : c.mapEntries()) if ({cond}) v.wireResidual.add(kv);")
    out.append("        return v;")
    out.append("    }")
    out.append("}")
    return out


def emit_types(schema: Schema, forward_compat: bool = False) -> str:
    out = ["// GENERATED native Java types + codec — do not edit. Pairs with Cbor.java.",
           "package taut;", ""]
    for e in schema.enums.values():
        out += _emit_enum(e.name, e.members) + [""]
    for m in schema.messages.values():
        out += _emit_message(m, forward_compat) + [""]
    return "\n".join(out) + "\n"
