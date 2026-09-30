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
member `toCbor`, nor a message or enum like a name the module already has:
`ir/validate.py` refuses RESERVED_FIELD_NAMES, RESERVED_TYPE_NAMES and `name_clashes`.
Decode is fail-closed: `fromCbor` returns or throws `CborError`.

Each message is also a decode root (TautCheckedDecode.md CD-B3; TautOptions.md OPT-L6): its
effective bounds, as `taut.ir.options.effective` resolves them when the code is generated,
are the static constants `maxDepth` and `maxEncodedLen` (nil: no length bound), and its
`decode(_:)` reads bytes through the runtime's `Cbor.tryDecode` under both, then `fromCbor`.
A message nested inside does not change the bounds of the call (OPT-D4): `fromCbor` reads a
decoded tree and applies none. `decode` names its own members through `Self`, so an instance
field of the same name (a Swift type may have both) hides none of them.
"""

from __future__ import annotations

from types import MappingProxyType

from ..ir.model import (
    MISSING_OK, EnumRef, FieldDef, ListOf, MapOf, MessageDef, MsgRef, Scalar, Schema, TypeRef,
)
from ..ir.options import effective
from .names import Clash

RESERVED_FIELD_NAMES = MappingProxyType({
    "Cbor": "a runtime type the struct's code names",
    "CborError": "a runtime type a message's fromCbor names when it has no wire field",
    "toCbor": "a member function",
})
"""Field names a struct cannot take: inside it an instance member hides a type of its name, even
where a static member names the type, and a property cannot share its name with a method. A
field named like a message or enum is `name_clashes`'s."""

RESERVED_TYPE_NAMES = MappingProxyType({
    **dict.fromkeys("Cbor CborError".split(), "a runtime type"),
    **dict.fromkeys("""append16 append32 append64 checkExtensionTag checkedCount dec decodeUtf8
        enc encFloat encode enter extClear extGet extSet head hostMap negativeOverflowValue readArg
        requireBytes tryDecode""".split(), "a runtime function"),
    **dict.fromkeys("defaultMaxDepth extensionBandStart maxDepthCeiling".split(),
                    "a runtime constant"),
    **dict.fromkeys("""Array ArraySlice Bool CustomStringConvertible Double Equatable Float Float16
        Hashable Int Int64 Set String Swift UInt16 UInt32 UInt64 UInt8 Unicode precondition
        stride""".split(), "a standard library name the code uses"),
    **dict.fromkeys("decode fromCbor maxDepth maxEncodedLen toCbor".split(),
                    "a member every message has, which hides the type inside one"),
    **dict.fromkeys("wire_c wire_raw wire_v".split(), "a parameter or local that hides the type"),
    **dict.fromkeys("hash hashValue rawValue".split(),
                    "a member every enum has, which hides the type inside one"),
})
"""Message and enum names Swift cannot take in the module the generated code shares with its
runtime (`cbor.swift`, `ext.swift`): every name the runtime declares, private ones too, a standard
library name the code uses, which a type of the module's shadows, and a member, parameter or
local that hides the type where the code names it. Not `Error`: the runtime's `CborError`
conforms to `Swift.Error`, spelled out, so a message or enum may take the name, as glade's
message `Error` does."""

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
_BYTES = "wire_bytes"  # a decode's parameter, the bytes it reads


def _id(name: str) -> str:
    return f"`{name}`" if name in _SWIFT_KEYWORDS else name


def name_clashes(schema: Schema) -> list[Clash]:
    """A field named like any declared message or enum: inside its struct it hides the type
    wherever the code names one (its own message, a field's message or enum). An enum named like
    one of its members, whose case hides the enum inside it."""
    clashes: list[Clash] = []
    for m in schema.messages.values():
        for f in m.fields:
            if f.name in schema.messages or f.name in schema.enums:
                kind = "message" if f.name in schema.messages else "enum"
                clashes.append((f"{m.name}.{f.name}", "field", f"a declared {kind}'s name"))
    for e in schema.enums.values():
        if e.name in e.members:
            clashes.append((f"enum {e.name}", "enum", "one of its members' name"))
    return clashes


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
    out += _emit_decode(msg, schema)
    out.append("}")
    return out


def _emit_decode(msg: MessageDef, schema: Schema) -> list[str]:
    """The message as a decode root: its effective bounds, and `decode` from bytes under them."""
    depth = effective(schema, "max_depth", message=msg.name)
    length = effective(schema, "max_encoded_len", message=msg.name)
    return [
        f"    public static let maxDepth: Int = {depth}",
        f"    public static let maxEncodedLen: Int? = {'nil' if length is None else length}",
        f"    public static func decode(_ {_BYTES}: [UInt8]) throws -> {msg.name} {{",
        f"        return try Self.fromCbor(Cbor.tryDecode({_BYTES}, maxDepth: Self.maxDepth, "
        "maxEncodedLen: Self.maxEncodedLen))",
        "    }",
    ]


def emit_types(schema: Schema, forward_compat: bool = False) -> str:
    out = ["// GENERATED native Swift types + codec — do not edit.",
           "// Pairs with the vendored cbor.swift runtime (same module).", ""]
    for e in schema.enums.values():
        out += _emit_enum(e.name, e.members) + [""]
    for m in schema.messages.values():
        out += _emit_message(m, schema, forward_compat) + [""]
    return "\n".join(out) + "\n"
