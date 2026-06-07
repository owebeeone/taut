"""Swift code generator — native types + a deterministic-CBOR codec, mirroring
the Rust/C++ generators. Pairs with the vendored `cbor.swift` runtime (emitted by
`tautc gen --with-runtime`). Swift's `encode` sorts map keys, so forward-compat
residual just rides along (no merge needed, unlike C++).
"""

from __future__ import annotations

from ..ir.model import EnumRef, FieldDef, ListOf, MapOf, MsgRef, Scalar, Schema, TypeRef

# Swift reserved words — field names / enum cases that collide get backtick-escaped
# (e.g. razel's `VersionInfo.protocol`).
_SWIFT_KEYWORDS = frozenset("""
associatedtype class deinit enum extension fileprivate func import init inout
internal let open operator private protocol public rethrows static struct
subscript typealias var break case continue default defer do else fallthrough
for guard if in repeat return switch where while as catch false is nil super
self Self throw throws true try _ Any Protocol Type
""".split())


def _id(name: str) -> str:
    return f"`{name}`" if name in _SWIFT_KEYWORDS else name


def _swift_ty(t: TypeRef) -> str:
    if isinstance(t, Scalar):
        return {"int": "Int64", "str": "String", "bytes": "[UInt8]", "bool": "Bool"}[t.kind]
    if isinstance(t, (EnumRef, MsgRef)):
        return t.name
    if isinstance(t, ListOf):
        return f"[{_swift_ty(t.elem)}]"
    if isinstance(t, MapOf):
        return f"[{_swift_ty(t.key)}: {_swift_ty(t.value)}]"
    raise TypeError(t)


def _field_type(f: FieldDef) -> str:
    base = _swift_ty(f.type)
    return f"{base}?" if f.optional else base


def _default(t: TypeRef) -> str:
    if isinstance(t, Scalar):
        return {"int": "0", "str": '""', "bytes": "[]", "bool": "false"}[t.kind]
    if isinstance(t, ListOf):
        return "[]"
    if isinstance(t, EnumRef):
        return f"{t.name}(rawValue: 0)!"
    raise TypeError(f"no Swift default for transient field of type {t!r}")


def _encode(t: TypeRef, expr: str) -> str:
    if isinstance(t, Scalar):
        return {
            "int": f"Cbor.int({expr})",
            "str": f"Cbor.text({expr})",
            "bytes": f"Cbor.bytes({expr})",
            "bool": f"Cbor.bool({expr})",
        }[t.kind]
    if isinstance(t, EnumRef):
        return f"Cbor.int({expr}.rawValue)"
    if isinstance(t, MsgRef):
        return f"{expr}.toCbor()"
    if isinstance(t, ListOf):
        return f"Cbor.array({expr}.map {{ {_encode(t.elem, '$0')} }})"
    if isinstance(t, MapOf):
        cmp = ("(($0.key ? 1 : 0) < ($1.key ? 1 : 0))"
               if isinstance(t.key, Scalar) and t.key.kind == "bool" else "$0.key < $1.key")
        return (f"Cbor.array({expr}.sorted {{ {cmp} }}.map {{ "
                f"Cbor.map([(1, {_encode(t.key, '$0.key')}), (2, {_encode(t.value, '$0.value')})]) }})")
    raise TypeError(t)


def _decode(t: TypeRef, expr: str) -> str:
    if isinstance(t, Scalar):
        return {
            "int": f"{expr}.intVal",
            "str": f"{expr}.textVal",
            "bytes": f"{expr}.bytesVal",
            "bool": f"{expr}.boolVal",
        }[t.kind]
    if isinstance(t, EnumRef):
        return f"{t.name}(rawValue: {expr}.intVal)!"
    if isinstance(t, MsgRef):
        return f"{t.name}.fromCbor({expr})"
    if isinstance(t, ListOf):
        return f"{expr}.arrayVal.map {{ {_decode(t.elem, '$0')} }}"
    if isinstance(t, MapOf):
        return (f"Dictionary(uniqueKeysWithValues: {expr}.arrayVal.map {{ "
                f"({_decode(t.key, '$0.get(1)')}, {_decode(t.value, '$0.get(2)')}) }})")
    raise TypeError(t)


def _emit_enum(name: str, members: dict[str, int]) -> list[str]:
    out = [f"public enum {name}: Int64 {{"]
    for m, v in members.items():
        out.append(f"    case {_id(m)} = {v}")
    out.append("}")
    return out


def _emit_message(msg, forward_compat: bool = False) -> list[str]:
    out = [f"public struct {msg.name} {{"]
    for f in msg.fields:
        out.append(f"    public var {_id(f.name)}: {_field_type(f)}")
    if forward_compat:
        out.append("    public var wire_residual: [(Int64, Cbor)]")
    out.append("")
    # explicit public init (so values are constructible cross-module)
    params = []
    for f in msg.fields:
        ft = _field_type(f)
        if f.transient:
            params.append(f"{_id(f.name)}: {ft} = {'nil' if f.optional else _default(f.type)}")
        elif f.optional:
            params.append(f"{_id(f.name)}: {ft} = nil")
        else:
            params.append(f"{_id(f.name)}: {ft}")
    if forward_compat:
        params.append("wire_residual: [(Int64, Cbor)] = []")
    out.append(f"    public init({', '.join(params)}) {{")
    for f in msg.fields:
        out.append(f"        self.{_id(f.name)} = {_id(f.name)}")
    if forward_compat:
        out.append("        self.wire_residual = wire_residual")
    out.append("    }")
    # toCbor (wire fields; residual rides along — encode() sorts keys -> canonical)
    out.append("    public func toCbor() -> Cbor {")
    entries = []
    for f in msg.wire_fields():
        n = _id(f.name)
        if f.optional:
            enc = f"({n}.map {{ {_encode(f.type, '$0')} }} ?? Cbor.null)"
        else:
            enc = _encode(f.type, n)
        entries.append(f"({f.tag}, {enc})")
    arr = "[" + ", ".join(entries) + "]"
    out.append(f"        return Cbor.map({arr}{' + wire_residual' if forward_compat else ''})")
    out.append("    }")
    # fromCbor
    out.append(f"    public static func fromCbor(_ c: Cbor) -> {msg.name} {{")
    args = []
    for f in msg.fields:
        if f.transient:
            continue  # native-only; init default applies
        if f.optional:
            args.append(f"{_id(f.name)}: {{ let v = c.get({f.tag}); return v.isNull ? nil : {_decode(f.type, 'v')} }}()")
        else:
            args.append(f"{_id(f.name)}: {_decode(f.type, f'c.get({f.tag})')}")
    if forward_compat:
        known = ", ".join(str(f.tag) for f in msg.wire_fields())
        args.append(f"wire_residual: c.mapEntries.filter {{ ![{known}].contains($0.0) }}")
    out.append(f"        return {msg.name}(")
    out.append("            " + ",\n            ".join(args))
    out.append("        )")
    out.append("    }")
    out.append("}")
    return out


def emit_types(schema: Schema, forward_compat: bool = False) -> str:
    out = ["// GENERATED native Swift types + codec — do not edit.",
           "// Pairs with the vendored cbor.swift runtime (same module).", ""]
    for e in schema.enums.values():
        out += _emit_enum(e.name, e.members) + [""]
    for m in schema.messages.values():
        out += _emit_message(m, forward_compat) + [""]
    return "\n".join(out) + "\n"
