"""Generate Rust native types + codec from the IR — taut's text codegen for a
compiled target (P5). Emits `trial/rs/src/generated.rs`:

  - one Rust enum per IR enum (with wire() and a fallible from_wire())
  - one Rust struct per IR message (with to_cbor() and a fallible from_cbor());
    transient fields are present in the struct but never on the wire (Default on
    decode)
  - a `roundtrip(message, bytes)` dispatcher
  - the golden corpus as `VECTORS: &[(name, message, hex)]`

Decode is fail-closed everywhere: `from_wire`, `from_cbor`, `decode` and `roundtrip`
return `Result<_, DecodeError>` and never panic on input. The legacy (panicking) codec
was removed at v0.10.0 (TautCheckedDecode.md question 5).

Decode is bounded (TautCheckedDecode.md CD-B3; TautOptions.md OPT-D4, OPT-L6). Each
message's `MAX_DEPTH` and `MAX_ENCODED_LEN` are its effective `max_depth` and
`max_encoded_len`, resolved here by `options.effective`, and its `decode` reads bytes
under them: the whole call is bounded by its root, whatever it nests. The file's own
values, at module level, serve a root that is not a message.

Rust has no std JSON parser, so generating data/types beats pulling a crate — and
native structs are exactly what a compiled target wants ahead of time.
"""

from __future__ import annotations

import json
from pathlib import Path
from types import MappingProxyType

from ..ir.load import load_schema
from ..ir.model import MISSING_OK, EnumRef, FieldDef, ListOf, MapOf, MsgRef, Scalar, Schema, TypeRef
from ..ir.options import effective

_TAUT = Path(__file__).resolve().parents[3]      # .../glial-dev/taut
_REPO = _TAUT.parent                              # .../glial-dev (trial/ is a sibling)
IR_PATH = _TAUT / "ir" / "griplab.taut.py"
GOLDEN_PATH = _TAUT / "corpus" / "griplab.golden.json"
OUT_PATH = _REPO / "trial" / "rs" / "src" / "generated.rs"

RESERVED_FIELD_NAMES: MappingProxyType[str, str] = MappingProxyType({})
"""None: the code reads a field through `self.` or names it in a struct literal, where nothing
it declares meets the field (the `wire_` prefix is taut's, `ir/validate.py`)."""

RESERVED_TYPE_NAMES = MappingProxyType({
    **dict.fromkeys("Cbor DecodeError".split(), "a runtime type"),
    **dict.fromkeys("Option Result String Vec".split(), "a prelude type the code names"),
    **dict.fromkeys("bool f64 i64 u8 usize".split(), "a primitive type the code names"),
    "std": "the root of the code's `std::` paths",
    "Default": "the trait of a transient field's `Default::default()`",
})
"""Message and enum names the generated module cannot take: a struct or enum there shadows the
runtime types it imports and the prelude and primitive types, `std` and `Default` its code names."""


def _variant(member: str) -> str:
    return "".join(p.capitalize() for p in member.split("_"))


def _rust_type(t: TypeRef) -> str:
    # `int` is `i64`, the frozen wire int subset; decode refuses a wider wire int as
    # `IntOverflow` rather than wrap it. (A 128-bit int would be a new type, not a
    # widening of `int`.)
    if isinstance(t, Scalar):
        return {"int": "i64", "str": "String", "bytes": "Vec<u8>",
                "bool": "bool", "float": "f64"}[t.kind]
    if isinstance(t, EnumRef):
        return t.name
    if isinstance(t, MsgRef):
        return t.name
    if isinstance(t, ListOf):
        return f"Vec<{_rust_type(t.elem)}>"
    if isinstance(t, MapOf):
        return f"std::collections::BTreeMap<{_rust_type(t.key)}, {_rust_type(t.value)}>"
    raise TypeError(t)


def _encode_ref(t: TypeRef, e: str) -> str:
    """Encode a value bound by reference (map iteration gives &K / &V)."""
    if isinstance(t, Scalar):
        return {"int": f"Cbor::Int(*{e})", "bool": f"Cbor::Bool(*{e})",
                "float": f"Cbor::Float(*{e})", "str": f"Cbor::Text({e}.clone())",
                "bytes": f"Cbor::Bytes({e}.clone())"}[t.kind]
    if isinstance(t, EnumRef):
        return f"Cbor::Int({e}.wire())"
    if isinstance(t, MsgRef):
        return f"{e}.to_cbor()"
    raise TypeError(t)


def _field_type(f: FieldDef) -> str:
    base = _rust_type(f.type)
    return f"Option<{base}>" if f.optional else base


def _encode(t: TypeRef, expr: str) -> str:
    if isinstance(t, Scalar):
        return {
            "int": f"Cbor::Int({expr})",
            "str": f"Cbor::Text({expr}.clone())",
            "bytes": f"Cbor::Bytes({expr}.clone())",
            "bool": f"Cbor::Bool({expr})",
            "float": f"Cbor::Float({expr})",
        }[t.kind]
    if isinstance(t, EnumRef):
        return f"Cbor::Int({expr}.wire())"
    if isinstance(t, MsgRef):
        return f"{expr}.to_cbor()"
    if isinstance(t, ListOf):
        enc = _encode_ref(t.elem, "x") if isinstance(t.elem, (Scalar, EnumRef, MsgRef)) else _encode(t.elem, "x")
        return f"Cbor::Array({expr}.iter().map(|x| {enc}).collect())"
    if isinstance(t, MapOf):  # BTreeMap iterates in ascending key order -> deterministic
        return (f"Cbor::Array({expr}.iter().map(|(k, v)| "
                f"Cbor::Map(vec![(1, {_encode_ref(t.key, 'k')}), (2, {_encode_ref(t.value, 'v')})])).collect())")
    raise TypeError(t)


def _encode_optional(t: TypeRef, expr: str) -> str:
    if isinstance(t, (Scalar, EnumRef, MsgRef)):
        return _encode_ref(t, expr)
    return _encode(t, expr)


# --- fail-closed decode -------------------------------------------------------
# Every decode expression propagates a typed `DecodeError` with `?`; none panics.

def _decode_try(t: TypeRef, expr: str) -> str:
    """A `?`-propagating decode expression against the fallible runtime API.

    Scalars use the `try_*` accessors (each `-> Result<_, DecodeError>`); enums
    use the fallible `from_wire`; nested messages recurse through the fallible
    `from_cbor`. A list builds a `Result<Vec<_>>` and `?`s it out; a map is
    `_decode_try_map`."""
    if isinstance(t, Scalar):
        return {
            "int": f"{expr}.try_int()?",
            "str": f"{expr}.try_text()?",
            "bytes": f"{expr}.try_bytes()?",
            "bool": f"{expr}.try_bool()?",
            "float": f"{expr}.try_float()?",
        }[t.kind]
    if isinstance(t, EnumRef):
        return f"{t.name}::from_wire({expr}.try_int()?)?"
    if isinstance(t, MsgRef):
        return f"{t.name}::from_cbor({expr})?"
    if isinstance(t, ListOf):
        return (f"{expr}.try_array()?.iter().map(|x| {_decode_try_elem(t.elem, 'x')})"
                f".collect::<Result<Vec<_>, DecodeError>>()?")
    if isinstance(t, MapOf):
        return _decode_try_map(t, expr)
    raise TypeError(t)


# The `map<K,V>` key kinds (validate allows no other). A repeated key is reported as
# itself: the runtime's `MapKey` converts from each kind's Rust type (`k.into()`), and
# its text is question 9's, an int in decimal, a str as itself, a bool as `true` or
# `false` (TautCheckedDecode.md §8).
_MAP_KEY_KINDS = frozenset({"int", "str", "bool"})


def _decode_try_map(t: MapOf, expr: str) -> str:
    """A `map<K,V>` block expression: an array of `{1: key, 2: value}` entry maps
    (D24), read entry by entry in order (CD-E5). Each entry must be a map holding
    key 1 and then key 2 before either is decoded; then its key is decoded, a
    repeated key is `DuplicateMapKey` with the key itself, and only then its value
    is decoded. The block `return`s its error, from `from_cbor` or from a list
    element's closure."""
    key = t.key
    if not isinstance(key, Scalar) or key.kind not in _MAP_KEY_KINDS:
        raise TypeError(t)   # validate allows only int, str and bool keys
    return ("{ let mut m = std::collections::BTreeMap::new(); "
            f"for e in {expr}.try_array()? {{ let ek = e.try_get(1)?; let ev = e.try_get(2)?; "
            f"let k = {_decode_try(key, 'ek')}; "
            "if m.contains_key(&k) { return Err(DecodeError::DuplicateMapKey(k.into())); } "
            f"m.insert(k, {_decode_try(t.value, 'ev')}); }} m }}")


def _decode_try_elem(t: TypeRef, expr: str) -> str:
    """A `.collect::<Result<..>>()`-friendly closure body for a list element.

    A nested message's `from_cbor` already yields `Result<_, DecodeError>`, so
    it is returned bare (no `Ok(..?)` wrapper — which would be a redundant
    `needless_question_mark`); everything else is a fallible scalar/enum, wrapped
    once in `Ok(..)`. This keeps the *generated* fail-closed code clippy-clean
    for every consumer, not just those that add a lint allow."""
    if isinstance(t, MsgRef):
        return f"{t.name}::from_cbor({expr})"
    return f"Ok({_decode_try(t, expr)})"


def _emit_enum(name: str, members: dict[str, int]) -> list[str]:
    variants = [(_variant(m), v) for m, v in members.items()]
    out = ["#[derive(Clone, Copy, Debug, PartialEq, Default)]", f"pub enum {name} {{"]
    for i, (vn, _) in enumerate(variants):
        out.append(f"    {'#[default] ' if i == 0 else ''}{vn},")
    out.append("}")
    out.append(f"impl {name} {{")
    out.append("    pub fn wire(self) -> i64 { match self {")
    for vn, v in variants:
        out.append(f"        Self::{vn} => {v},")
    out.append("    } }")
    # An unknown wire value is a typed error, never a panic.
    out.append("    pub fn from_wire(v: i64) -> Result<Self, DecodeError> { Ok(match v {")
    for vn, v in variants:
        out.append(f"        {v} => Self::{vn},")
    out.append(f'        _ => return Err(DecodeError::UnknownEnum {{ enum_name: "{name}", value: v }}),')
    out.append("    }) }")
    out.append("}")
    return out


def _bound_consts(schema: Schema, message: str | None, indent: str) -> list[str]:
    """`MAX_DEPTH` and `MAX_ENCODED_LEN` for a decode rooted at `message`, or, for None, at a
    type that is not a message: the effective values, resolved once, here (TautOptions.md
    OPT-D3), `max_encoded_len`'s None being no length bound."""
    depth = effective(schema, "max_depth", message=message)
    length = effective(schema, "max_encoded_len", message=message)
    return [f"{indent}pub const MAX_DEPTH: usize = {depth};",
            f"{indent}pub const MAX_ENCODED_LEN: Option<usize> = {'None' if length is None else f'Some({length})'};"]


def _emit_file_bounds(schema: Schema) -> list[str]:
    """The file's bounds at module level, for a decode rooted at a type that is not a message,
    such as an RPC slot's `list<T>` (TautOptions.md OPT-D4)."""
    return ["// The file's bounds, for a decode rooted at a type that is not a message:",
            "// `cbor::try_decode_with(bytes, MAX_DEPTH, MAX_ENCODED_LEN)`.",
            *_bound_consts(schema, None, "")]


def _emit_message(msg, schema: Schema, forward_compat: bool = False) -> list[str]:
    out = ["#[derive(Clone, Debug, PartialEq, Default)]", f"pub struct {msg.name} {{"]
    for f in msg.fields:
        out.append(f"    pub {f.name}: {_field_type(f)},")
    if forward_compat:
        # unknown/newer-version fields, preserved verbatim (empty when none):
        # (map-key, value) pairs, the keys `i64` CBOR field tags.
        out.append("    pub wire_residual: Vec<(i64, Cbor)>,")
    out.append("}")
    out.append(f"impl {msg.name} {{")
    out += _bound_consts(schema, msg.name, "    ")
    # encoded (tag, expr) pairs for the known wire fields (deterministic minimal CBOR).
    pairs = []
    for f in msg.wire_fields():
        if f.optional:
            enc = f"match &self.{f.name} {{ Some(v) => {_encode_optional(f.type, 'v')}, None => Cbor::Null }}"
        else:
            enc = _encode(f.type, f"self.{f.name}")
        pairs.append((f.tag, enc))
    # to_cbor (wire fields only; re-emits residual when forward-compat)
    out.append("    pub fn to_cbor(&self) -> Cbor {")
    if forward_compat:
        out.append("        let mut m = vec![")
        for tag, enc in pairs:
            out.append(f"            ({tag}, {enc}),")
        out.append("        ];")
        out.append("        for (t, v) in &self.wire_residual { m.push((*t, v.clone())); }")
        out.append("        Cbor::Map(m)")
    else:
        out.append("        Cbor::Map(vec![")
        for tag, enc in pairs:
            out.append(f"            ({tag}, {enc}),")
        out.append("        ])")
    out.append("    }")
    out += _from_cbor(msg, forward_compat)
    # The typed entry point from bytes: the raw decode under this root's bounds, then from_cbor.
    out += ["    pub fn decode(bytes: &[u8]) -> Result<Self, DecodeError> {",
            "        Self::from_cbor(&crate::cbor::try_decode_with(bytes, Self::MAX_DEPTH, Self::MAX_ENCODED_LEN)?)",
            "    }"]
    out.append("}")
    return out


def _from_cbor(msg, forward_compat: bool) -> list[str]:
    """Fail-closed `from_cbor`: returns `Result<Self, DecodeError>`, propagates
    a typed error with `?` on every missing key / wrong type / unknown enum
    arm / short field, and never panics on any input."""
    out = ["    pub fn from_cbor(c: &Cbor) -> Result<Self, DecodeError> {"]
    if not msg.wire_fields():
        out.append('        if !c.is_map() { return Err(DecodeError::WrongType { expected: "map" }); }')
    out.append("        Ok(Self {")
    for f in msg.fields:
        if f.transient:
            dec = "Default::default()"
        elif f.optional:
            if f.optional == MISSING_OK:
                dec = (f"{{ let v = c.try_get_opt({f.tag})?; match v {{ None => None, Some(v) => "
                       f"if v.is_null() {{ None }} else {{ Some({_decode_try(f.type, 'v')}) }} }} }}")
            else:
                dec = (f"{{ let v = c.try_get({f.tag})?; "
                       f"if v.is_null() {{ None }} else {{ Some({_decode_try(f.type, 'v')}) }} }}")
        else:
            dec = _decode_try(f.type, f"c.try_get({f.tag})?")
        out.append(f"            {f.name}: {dec},")
    if forward_compat:
        known = [str(f.tag) for f in msg.wire_fields()]
        pred = f"!matches!(*t, {' | '.join(known)})" if known else "true"
        out.append(f"            wire_residual: c.map_entries().iter()"
                   f".filter(|(t, _)| {pred}).map(|(t, v)| (*t, v.clone())).collect(),")
    out += ["        })", "    }"]
    return out


def _emit(schema: Schema, golden: dict) -> str:
    lines = [
        "// GENERATED from taut/ir + corpus by taut/src/taut/gen/rust.py — do not edit.",
        "#![allow(dead_code)]",
        "use crate::cbor::{Cbor, DecodeError};",
        "",
        *_emit_file_bounds(schema),
        "",
    ]
    for e in schema.enums.values():
        lines += _emit_enum(e.name, e.members) + [""]
    for m in schema.messages.values():
        lines += _emit_message(m, schema) + [""]

    # roundtrip dispatcher: bytes -> typed struct -> bytes, fail-closed like the
    # package codegen (scaffold.rust_api), whose message decoders it shares.
    lines.append("/// `bytes` decoded as `message`, under its bounds, and encoded again. Malformed")
    lines.append("/// input is a `DecodeError`; a `message` the schema lacks is the caller's error and panics.")
    lines.append("pub fn roundtrip(message: &str, bytes: &[u8]) -> Result<Vec<u8>, DecodeError> {")
    lines.append("    match message {")
    for m in schema.messages.values():
        lines.append(
            f'        "{m.name}" => {m.name}::decode(bytes).map(|v| crate::cbor::encode(&v.to_cbor())),'
        )
    lines.append('        _ => panic!("unknown message {}", message),')
    lines.append("    }")
    lines.append("}")
    lines.append("")

    lines.append("pub static VECTORS: &[(&str, &str, &str)] = &[")
    for name in sorted(golden):
        entry = golden[name]
        lines.append(f'    ({json.dumps(name)}, "{entry["message"]}", "{entry["cbor"]}"),')
    lines.append("];")
    return "\n".join(lines) + "\n"


def emit() -> None:
    schema = load_schema(IR_PATH)
    golden = json.loads(GOLDEN_PATH.read_text())
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(_emit(schema, golden))
