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


def _try_dec(t: TypeRef, expr: str) -> str:
    """A Go expression returning `(native_value, error)` for Cbor `expr`."""
    if isinstance(t, Scalar):
        return {"int": f"{expr}.TryInt()", "str": f"{expr}.TryText()",
                "bytes": f"{expr}.TryBytes()", "bool": f"{expr}.TryBool()",
                "float": f"{expr}.TryFloat()"}[t.kind]
    if isinstance(t, EnumRef):
        return f"Try{t.name}FromCbor({expr})"
    if isinstance(t, MsgRef):
        return f"Try{t.name}FromCbor({expr})"
    raise TypeError(t)


def _emit_enum(name: str, members: dict[str, int]) -> list[str]:
    out = [f"type {name} int64", "", "const ("]
    for m, v in members.items():
        out.append(f"\t{name}{_pascal(m)} {name} = {v}")
    out.append(")")
    out.append("")
    out.append(f"func Try{name}FromWire(v int64) ({name}, error) {{")
    out.append("\tswitch v {")
    for m, v in members.items():
        out.append(f"\tcase {v}:")
        out.append(f"\t\treturn {name}{_pascal(m)}, nil")
    out.append("\tdefault:")
    out.append(f"\t\treturn 0, UnknownEnumError(\"{name}\", v)")
    out.append("\t}")
    out.append("}")
    out.append("")
    out.append(f"func {name}FromWire(v int64) {name} {{")
    out.append(f"\tx, err := Try{name}FromWire(v)")
    out.append("\tif err != nil { panic(err) }")
    out.append("\treturn x")
    out.append("}")
    out.append("")
    out.append(f"func Try{name}FromCbor(c Cbor) ({name}, error) {{")
    out.append("\tv, err := c.TryInt()")
    out.append("\tif err != nil { return 0, err }")
    out.append(f"\treturn Try{name}FromWire(v)")
    out.append("}")
    out.append("")
    out.append(f"func {name}FromCbor(c Cbor) {name} {{")
    out.append(f"\tx, err := Try{name}FromCbor(c)")
    out.append("\tif err != nil { panic(err) }")
    out.append("\treturn x")
    out.append("}")
    return out


def _emit_try_assign(out: list[str], dst: str, t: TypeRef, expr: str) -> None:
    out.append(f"\t\tx, err := {_try_dec(t, expr)}")
    out.append("\t\tif err != nil { return v, err }")
    out.append(f"\t\t{dst} = x")


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
    out.append(f"func Try{msg.name}FromCbor(c Cbor) ({msg.name}, error) {{")
    out.append(f"\tvar v {msg.name}")
    for f in msg.fields:
        if f.transient:
            continue  # native-only; left as the Go zero value
        fn = f"v.{_pascal(f.name)}"
        if f.optional:
            out.append("\t{")
            out.append(f"\t\tfv, ok, err := c.Lookup({f.tag})")
            out.append("\t\tif err != nil { return v, err }")
            out.append("\t\tif ok && !fv.IsNull() {")
            out.append(f"\t\t\tx, err := {_try_dec(f.type, 'fv')}")
            out.append("\t\t\tif err != nil { return v, err }")
            out.append(f"\t\t\t{fn} = &x")
            out.append("\t\t}")
            out.append("\t}")
        elif isinstance(f.type, ListOf):
            out.append("\t{")
            out.append(f"\t\tfv, err := c.Require({f.tag})")
            out.append("\t\tif err != nil { return v, err }")
            out.append("\t\tarr, err := fv.TryArray()")
            out.append("\t\tif err != nil { return v, err }")
            out.append("\t\tfor _, e := range arr {")
            out.append(f"\t\t\tx, err := {_try_dec(f.type.elem, 'e')}")
            out.append("\t\t\tif err != nil { return v, err }")
            out.append(f"\t\t\t{fn} = append({fn}, x)")
            out.append("\t\t}")
            out.append("\t}")
        elif isinstance(f.type, MapOf):
            kt, vt = _go_ty(f.type.key), _go_ty(f.type.value)
            out.append("\t{")
            out.append(f"\t\tfv, err := c.Require({f.tag})")
            out.append("\t\tif err != nil { return v, err }")
            out.append("\t\tarr, err := fv.TryArray()")
            out.append("\t\tif err != nil { return v, err }")
            out.append(f"\t\t{fn} = map[{kt}]{vt}{{}}")
            if isinstance(f.type.key, Scalar) and f.type.key.kind == "int":
                out.append(f"\t\tseen := map[{kt}]bool{{}}")
            out.append("\t\tfor _, e := range arr {")
            out.append("\t\t\tkc, err := e.Require(1)")
            out.append("\t\t\tif err != nil { return v, err }")
            out.append(f"\t\t\tk, err := {_try_dec(f.type.key, 'kc')}")
            out.append("\t\t\tif err != nil { return v, err }")
            if isinstance(f.type.key, Scalar) and f.type.key.kind == "int":
                out.append("\t\t\tif seen[k] { return v, &DecodeError{Tag: DecodeErrDuplicateMapKey, Key: k} }")
                out.append("\t\t\tseen[k] = true")
            out.append("\t\t\tvc, err := e.Require(2)")
            out.append("\t\t\tif err != nil { return v, err }")
            out.append(f"\t\t\tval, err := {_try_dec(f.type.value, 'vc')}")
            out.append("\t\t\tif err != nil { return v, err }")
            out.append(f"\t\t\t{fn}[k] = val")
            out.append("\t\t}")
            out.append("\t}")
        else:
            out.append("\t{")
            out.append(f"\t\tfv, err := c.Require({f.tag})")
            out.append("\t\tif err != nil { return v, err }")
            _emit_try_assign(out, fn, f.type, "fv")
            out.append("\t}")
    if forward_compat:
        cond = " && ".join(f"kv.K != {f.tag}" for f in msg.wire_fields()) or "true"
        out.append("\t{")
        out.append("\t\tentries, err := c.TryMap()")
        out.append("\t\tif err != nil { return v, err }")
        out.append(f"\t\tfor _, kv := range entries {{ if {cond} {{ v.WireResidual = append(v.WireResidual, kv) }} }}")
        out.append("\t}")
    out.append("\treturn v, nil")
    out.append("}")
    out.append("")
    out.append(f"func {msg.name}FromCbor(c Cbor) {msg.name} {{")
    out.append(f"\tv, err := Try{msg.name}FromCbor(c)")
    out.append("\tif err != nil { panic(err) }")
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
