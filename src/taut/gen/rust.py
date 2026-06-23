"""Generate Rust native types + codec from the IR — taut's text codegen for a
compiled target (P5). Emits `trial/rs/src/generated.rs`:

  - one Rust enum per IR enum (with wire()/from_wire())
  - one Rust struct per IR message (with to_cbor()/from_cbor()); transient fields
    are present in the struct but never on the wire (Default on decode)
  - a `roundtrip(message, bytes)` dispatcher
  - the golden corpus as `VECTORS: &[(name, message, hex)]`

Rust has no std JSON parser, so generating data/types beats pulling a crate — and
native structs are exactly what a compiled target wants ahead of time.
"""

from __future__ import annotations

import json
from pathlib import Path

from ..ir.load import load_schema
from ..ir.model import EnumRef, FieldDef, ListOf, MapOf, MsgRef, Scalar, Schema, TypeRef

_TAUT = Path(__file__).resolve().parents[3]      # .../glial-dev/taut
_REPO = _TAUT.parent                              # .../glial-dev (trial/ is a sibling)
IR_PATH = _TAUT / "ir" / "griplab.taut.py"
GOLDEN_PATH = _TAUT / "corpus" / "griplab.golden.json"
OUT_PATH = _REPO / "trial" / "rs" / "src" / "generated.rs"


def _variant(member: str) -> str:
    return "".join(p.capitalize() for p in member.split("_"))


def _rust_type(t: TypeRef) -> str:
    if isinstance(t, Scalar):
        return {"int": "i64", "str": "String", "bytes": "Vec<u8>", "bool": "bool", "float": "f64"}[t.kind]
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


def _decode(t: TypeRef, expr: str) -> str:
    if isinstance(t, Scalar):
        return {
            "int": f"{expr}.int()",
            "str": f"{expr}.text()",
            "bytes": f"{expr}.bytes()",
            "bool": f"{expr}.boolean()",
            "float": f"{expr}.float()",
        }[t.kind]
    if isinstance(t, EnumRef):
        return f"{t.name}::from_wire({expr}.int())"
    if isinstance(t, MsgRef):
        return f"{t.name}::from_cbor({expr})"
    if isinstance(t, ListOf):
        return f"{expr}.array().iter().map(|x| {_decode(t.elem, 'x')}).collect()"
    if isinstance(t, MapOf):
        return (f"{expr}.array().iter().map(|e| "
                f"({_decode(t.key, 'e.get(1)')}, {_decode(t.value, 'e.get(2)')})).collect()")
    raise TypeError(t)


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
    out.append("    pub fn from_wire(v: i64) -> Self { match v {")
    for vn, v in variants:
        out.append(f"        {v} => Self::{vn},")
    out.append(f'        _ => panic!("bad {name} wire value {{}}", v),')
    out.append("    } }")
    out.append("}")
    return out


def _emit_message(msg, forward_compat: bool = False) -> list[str]:
    out = ["#[derive(Clone, Debug, PartialEq, Default)]", f"pub struct {msg.name} {{"]
    for f in msg.fields:
        out.append(f"    pub {f.name}: {_field_type(f)},")
    if forward_compat:
        # unknown/newer-version fields, preserved verbatim (empty when none)
        out.append("    pub wire_residual: Vec<(i64, Cbor)>,")
    out.append("}")
    out.append(f"impl {msg.name} {{")
    # encoded (tag, expr) pairs for the known wire fields
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
    # from_cbor
    out.append("    pub fn from_cbor(c: &Cbor) -> Self {")
    out.append("        Self {")
    for f in msg.fields:
        if f.transient:
            dec = "Default::default()"
        elif f.optional:
            dec = (f"{{ let v = c.get({f.tag}); "
                   f"if v.is_null() {{ None }} else {{ Some({_decode(f.type, 'v')}) }} }}")
        else:
            dec = _decode(f.type, f"c.get({f.tag})")
        out.append(f"            {f.name}: {dec},")
    if forward_compat:
        known = [str(f.tag) for f in msg.wire_fields()]
        pred = f"!matches!(*t, {' | '.join(known)})" if known else "true"
        out.append(f"            wire_residual: c.map_entries().iter()"
                   f".filter(|(t, _)| {pred}).map(|(t, v)| (*t, v.clone())).collect(),")
    out.append("        }")
    out.append("    }")
    out.append("}")
    return out


def _emit(schema: Schema, golden: dict) -> str:
    lines = [
        "// GENERATED from taut/ir + corpus by taut/src/taut/gen/rust.py — do not edit.",
        "#![allow(dead_code)]",
        "use crate::cbor::Cbor;",
        "",
    ]
    for e in schema.enums.values():
        lines += _emit_enum(e.name, e.members) + [""]
    for m in schema.messages.values():
        lines += _emit_message(m) + [""]

    # roundtrip dispatcher: bytes -> typed struct -> bytes
    lines.append("pub fn roundtrip(message: &str, bytes: &[u8]) -> Vec<u8> {")
    lines.append("    let c = crate::cbor::decode(bytes);")
    lines.append("    match message {")
    for m in schema.messages.values():
        lines.append(f'        "{m.name}" => crate::cbor::encode(&{m.name}::from_cbor(&c).to_cbor()),')
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
