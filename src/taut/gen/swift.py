"""Swift code generator — native types + a deterministic-CBOR codec, mirroring
the Rust/C++ generators. Pairs with the vendored `cbor.swift` runtime (emitted by
`tautc gen --with-runtime`). Swift's `encode` sorts map keys, so forward-compat
residual just rides along (no merge needed, unlike C++).

No field can clash with a parameter, local or helper of the generated code (the Names
fixture): the parameters and locals it binds take the `wire_` prefix, which taut
reserves (no field may take it, ir/validate.py), and it reaches the runtime's helpers
as members of a `Cbor` value (`tryGet`, `tryDictionary`, ...), never as free functions,
which a field of the same name would hide. A field still cannot be named like a type
the code names (`Cbor`, its message, or the message or enum of a field) or like the
member `toCbor`. Decode is fail-closed: `fromCbor` returns or throws `CborError`.
"""

from __future__ import annotations

from ..ir.model import MISSING_OK, EnumRef, FieldDef, ListOf, MapOf, MsgRef, Scalar, Schema, TypeRef

# Swift reserved words — field names / enum cases that collide get backtick-escaped
# (e.g. razel's `VersionInfo.protocol`).
_SWIFT_KEYWORDS = frozenset("""
associatedtype class deinit enum extension fileprivate func import init inout
internal let open operator private protocol public rethrows static struct
subscript typealias var break case continue default defer do else fallthrough
for guard if in repeat return switch where while as catch false is nil super
self Self throw throws true try _ Any Protocol Type
""".split())

# The parameters and locals the generated code binds: `wire_` and a role.
_C = "wire_c"          # a fromCbor's parameter, the item it decodes
_V = "wire_v"          # a nullable field's item
_RAW = "wire_raw"      # an enum's wire value
_VALUE = "wire_value"  # the member that value names


def _id(name: str) -> str:
    return f"`{name}`" if name in _SWIFT_KEYWORDS else name


def _swift_ty(t: TypeRef) -> str:
    if isinstance(t, Scalar):
        return {"int": "Int64", "str": "String", "bytes": "[UInt8]", "bool": "Bool", "float": "Double"}[t.kind]
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


def _default(t: TypeRef, schema: Schema) -> str:
    if isinstance(t, Scalar):
        return {"int": "0", "str": '""', "bytes": "[]", "bool": "false", "float": "0.0"}[t.kind]
    if isinstance(t, ListOf):
        return "[]"
    if isinstance(t, EnumRef):
        # The default applies on every decode, so it is a member, never a `(rawValue: 0)!`
        # that traps for an enum without a 0: the member with wire value 0, else the first.
        members = schema.enums[t.name].members
        member = next((m for m, v in members.items() if v == 0), next(iter(members), None))
        if member is None:
            raise TypeError(f"no Swift default for transient field of the empty enum {t.name}")
        return f".{_id(member)}"
    raise TypeError(f"no Swift default for transient field of type {t!r}")


def _encode(t: TypeRef, expr: str) -> str:
    if isinstance(t, Scalar):
        return {
            "int": f"Cbor.int({expr})",
            "float": f"Cbor.float({expr})",
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
            "int": f"try {expr}.tryInt()",
            "float": f"try {expr}.tryFloat()",
            "str": f"try {expr}.tryText()",
            "bytes": f"try {expr}.tryBytes()",
            "bool": f"try {expr}.tryBool()",
        }[t.kind]
    if isinstance(t, EnumRef):
        return f"try {t.name}.fromCbor({expr})"
    if isinstance(t, MsgRef):
        return f"try {t.name}.fromCbor({expr})"
    if isinstance(t, ListOf):
        return f"try {expr}.tryArray().map {{ {_decode(t.elem, '$0')} }}"
    if isinstance(t, MapOf):
        return (f"try {expr}.tryDictionary("
                f"key: {{ {_decode(t.key, '$0')} }}, "
                f"value: {{ {_decode(t.value, '$0')} }})")
    raise TypeError(t)


def _emit_enum(name: str, members: dict[str, int]) -> list[str]:
    out = [f"public enum {name}: Int64 {{"]
    for m, v in members.items():
        out.append(f"    case {_id(m)} = {v}")
    out.append("")
    out.append(f"    public static func fromCbor(_ {_C}: Cbor) throws -> {name} {{")
    out.append(f"        let {_RAW} = try {_C}.tryInt()")
    out.append(f"        guard let {_VALUE} = {name}(rawValue: {_RAW}) else {{")
    out.append(f"            throw CborError.unknownEnum(\"{name}\", {_RAW})")
    out.append("        }")
    out.append(f"        return {_VALUE}")
    out.append("    }")
    out.append("}")
    return out


def _emit_message(msg, schema: Schema, forward_compat: bool = False) -> list[str]:
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
            params.append(f"{_id(f.name)}: {ft} = {'nil' if f.optional else _default(f.type, schema)}")
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
    out.append(f"    public static func fromCbor(_ {_C}: Cbor) throws -> {msg.name} {{")
    if not msg.wire_fields():
        # no field lookup refuses a non-map here, so check it (CD-E5: even an empty message)
        out.append(f"        guard case .map = {_C} else {{")
        out.append('            throw CborError.wrongType("map")')
        out.append("        }")
    args = []
    for f in msg.fields:
        if f.transient:
            continue  # native-only; init default applies
        if f.optional == MISSING_OK:
            # an absent key reads as null, like a present null; a non-map still fails
            args.append(f"{_id(f.name)}: try {{ guard let {_V} = try {_C}.tryGetOpt({f.tag}) else {{ return nil }}; if {_V}.isNull {{ return nil }}; return {_decode(f.type, _V)} }}()")
        elif f.optional:
            args.append(f"{_id(f.name)}: try {{ let {_V} = try {_C}.tryGet({f.tag}); if {_V}.isNull {{ return nil }}; return {_decode(f.type, _V)} }}()")
        else:
            args.append(f"{_id(f.name)}: {_decode(f.type, f'{_C}.tryGet({f.tag})')}")
    if forward_compat:
        known = ", ".join(str(f.tag) for f in msg.wire_fields())
        args.append(f"wire_residual: {_C}.mapEntries.filter {{ ![{known}].contains($0.0) }}")
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
        out += _emit_message(m, schema, forward_compat) + [""]
    return "\n".join(out) + "\n"
