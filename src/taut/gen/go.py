"""Go code generator — native structs + a deterministic-CBOR codec, mirroring the
Rust/C++/Swift generators. Pairs with the vendored `cbor.go` runtime (emitted by
`tautc gen --lang go --with-runtime`); both are `package taut`. Go's `Encode`
sorts map keys, so forward-compat residual just rides along (no merge).

Field/enum names are PascalCased (Go requires capitalized identifiers to export)
— which also means they can never collide with Go's (lowercase) keywords.
"""

from __future__ import annotations

from ..ir.model import EnumRef, FieldDef, ListOf, MapOf, MsgRef, Scalar, Schema, TypeRef


def _pascal(name: str) -> str:
    return "".join(p[:1].upper() + p[1:] for p in name.split("_") if p)


def _go_ty(t: TypeRef) -> str:
    if isinstance(t, Scalar):
        return {"int": "int64", "str": "string", "bytes": "[]byte", "bool": "bool", "float": "float64"}[t.kind]
    if isinstance(t, (EnumRef, MsgRef)):
        return t.name
    if isinstance(t, ListOf):
        return f"[]{_go_ty(t.elem)}"
    if isinstance(t, MapOf):
        return f"map[{_go_ty(t.key)}]{_go_ty(t.value)}"
    raise TypeError(t)


def _has_map(schema: Schema) -> bool:
    return any(isinstance(f.type, MapOf) for m in schema.messages.values() for f in m.fields)


def _field_type(f: FieldDef) -> str:
    base = _go_ty(f.type)
    return f"*{base}" if f.optional else base


def _enc(t: TypeRef, expr: str) -> str:
    """A Cbor expression encoding the (non-optional, non-list) value `expr`."""
    if isinstance(t, Scalar):
        return {"int": f"CInt({expr})", "str": f"CText({expr})",
                "bytes": f"CBytes({expr})", "bool": f"CBool({expr})",
                "float": f"CFloat({expr})"}[t.kind]
    if isinstance(t, EnumRef):
        return f"CInt(int64({expr}))"
    if isinstance(t, MsgRef):
        return f"{expr}.ToCbor()"
    raise TypeError(t)


def _dec(t: TypeRef, expr: str) -> str:
    """A Go expression decoding the Cbor `expr` into the native (single) value."""
    if isinstance(t, Scalar):
        return {"int": f"{expr}.Int()", "str": f"{expr}.Text()",
                "bytes": f"{expr}.Bytes()", "bool": f"{expr}.Bool()",
                "float": f"{expr}.Float()"}[t.kind]
    if isinstance(t, EnumRef):
        return f"{t.name}({expr}.Int())"
    if isinstance(t, MsgRef):
        return f"{t.name}FromCbor({expr})"
    raise TypeError(t)


def _emit_enum(name: str, members: dict[str, int]) -> list[str]:
    out = [f"type {name} int64", "", "const ("]
    for m, v in members.items():
        out.append(f"\t{name}{_pascal(m)} {name} = {v}")
    out.append(")")
    return out


def _emit_message(msg, forward_compat: bool = False) -> list[str]:
    out = [f"type {msg.name} struct {{"]
    for f in msg.fields:
        out.append(f"\t{_pascal(f.name)} {_field_type(f)}")
    if forward_compat:
        out.append("\tWireResidual []KV")
    out.append("}")
    out.append("")
    # ToCbor
    out.append(f"func (x {msg.name}) ToCbor() Cbor {{")
    out.append("\tm := []KV{")
    for f in msg.wire_fields():
        fn = f"x.{_pascal(f.name)}"
        if f.optional:
            val = f"func() Cbor {{ if {fn} != nil {{ return {_enc(f.type, '(*' + fn + ')')} }}; return CNull() }}()"
        elif isinstance(f.type, ListOf):
            val = (f"func() Cbor {{ a := []Cbor{{}}; for _, e := range {fn} {{ a = append(a, {_enc(f.type.elem, 'e')}) }}; return CArr(a) }}()")
        elif isinstance(f.type, MapOf):
            kt = _go_ty(f.type.key)
            less = ("!ks[i] && ks[j]" if isinstance(f.type.key, Scalar) and f.type.key.kind == "bool"
                    else "ks[i] < ks[j]")
            enck, encv = _enc(f.type.key, "k"), _enc(f.type.value, f"{fn}[k]")
            val = (f"func() Cbor {{ ks := make([]{kt}, 0, len({fn})); for k := range {fn} {{ ks = append(ks, k) }}; "
                   f"sort.Slice(ks, func(i, j int) bool {{ return {less} }}); a := []Cbor{{}}; "
                   f"for _, k := range ks {{ a = append(a, CMap([]KV{{{{K: 1, V: {enck}}}, {{K: 2, V: {encv}}}}})) }}; "
                   f"return CArr(a) }}()")
        else:
            val = _enc(f.type, fn)
        out.append(f"\t\t{{K: {f.tag}, V: {val}}},")
    out.append("\t}")
    if forward_compat:
        out.append("\tm = append(m, x.WireResidual...)") # Encode sorts -> canonical
    out.append("\treturn CMap(m)")
    out.append("}")
    out.append("")
    # FromCbor
    out.append(f"func {msg.name}FromCbor(c Cbor) {msg.name} {{")
    out.append(f"\tvar v {msg.name}")
    for f in msg.fields:
        if f.transient:
            continue  # native-only; left as the Go zero value
        fn = f"v.{_pascal(f.name)}"
        if f.optional:
            out.append(f"\tif fv := c.Get({f.tag}); !fv.IsNull() {{ t := {_dec(f.type, 'fv')}; {fn} = &t }}")
        elif isinstance(f.type, ListOf):
            out.append(f"\tfor _, e := range c.Get({f.tag}).Array() {{ {fn} = append({fn}, {_dec(f.type.elem, 'e')}) }}")
        elif isinstance(f.type, MapOf):
            kt, vt = _go_ty(f.type.key), _go_ty(f.type.value)
            deck, decv = _dec(f.type.key, "e.Get(1)"), _dec(f.type.value, "e.Get(2)")
            out.append(f"\t{fn} = map[{kt}]{vt}{{}}")
            out.append(f"\tfor _, e := range c.Get({f.tag}).Array() {{ {fn}[{deck}] = {decv} }}")
        else:
            out.append(f"\t{fn} = {_dec(f.type, f'c.Get({f.tag})')}")
    if forward_compat:
        cond = " && ".join(f"kv.K != {f.tag}" for f in msg.wire_fields()) or "true"
        out.append(f"\tfor _, kv := range c.MapEntries() {{ if {cond} {{ v.WireResidual = append(v.WireResidual, kv) }} }}")
    out.append("\treturn v")
    out.append("}")
    return out


def emit_types(schema: Schema, forward_compat: bool = False) -> str:
    out = ["// GENERATED native Go types + codec — do not edit.",
           "// Pairs with the vendored cbor.go runtime (same package).",
           "package taut", ""]
    if _has_map(schema):
        out += ['import "sort"', ""]
    for e in schema.enums.values():
        out += _emit_enum(e.name, e.members) + [""]
    for m in schema.messages.values():
        out += _emit_message(m, forward_compat) + [""]
    return "\n".join(out) + "\n"
