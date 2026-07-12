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


def _rust_type(t: TypeRef, fail_closed: bool = False) -> str:
    if isinstance(t, Scalar):
        return {"int": _rust_int_type(fail_closed), "str": "String", "bytes": "Vec<u8>",
                "bool": "bool", "float": "f64"}[t.kind]
    if isinstance(t, EnumRef):
        return t.name
    if isinstance(t, MsgRef):
        return t.name
    if isinstance(t, ListOf):
        return f"Vec<{_rust_type(t.elem, fail_closed)}>"
    if isinstance(t, MapOf):
        return f"std::collections::BTreeMap<{_rust_type(t.key, fail_closed)}, {_rust_type(t.value, fail_closed)}>"
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


def _field_type(f: FieldDef, fail_closed: bool = False) -> str:
    base = _rust_type(f.type, fail_closed)
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


# --- fail-closed (opt-in) decode ---------------------------------------------
# Mirror of `_decode` that propagates a typed `DecodeError` with `?` instead of
# panicking. Selected by the `fail_closed` flag (see `_emit_message`); the
# default path above is left byte-for-byte unchanged so a consumer that
# regenerates WITHOUT the flag gets today's output.

def _decode_try(t: TypeRef, expr: str) -> str:
    """A `?`-propagating decode expression against the fallible runtime API.

    Scalars use the `try_*` accessors (each `-> Result<_, DecodeError>`); enums
    use the fallible `from_wire`; nested messages recurse through the fallible
    `from_cbor`. Collections build a `Result<Vec<_>>` and `?` it out."""
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
        return (f"{expr}.try_array()?.iter().map(|e| "
                f"Ok(({_decode_try(t.key, 'e.try_get(1)?')}, {_decode_try(t.value, 'e.try_get(2)?')})))"
                f".collect::<Result<_, DecodeError>>()?")
    raise TypeError(t)


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


def _rust_int_type(fail_closed: bool) -> str:
    """Rust carrier for a taut `int` field: `i64` in both modes.

    The frozen wire int subset is `i64` (`[-2^63, 2^63-1]`). The default path
    truncates a wider CBOR int (`n as i64`); the fail-closed path keeps the same
    `i64` carrier but rejects an out-of-`i64` wire int as a typed `DecodeError`
    (never a silent wrap, a panic, or a wider carry) — so decode is fail-closed
    without changing the value model. (If 128-bit is ever needed it will be a
    distinct type, not a widening of `int`.)"""
    return "i64"


def _emit_enum(name: str, members: dict[str, int], fail_closed: bool = False) -> list[str]:
    variants = [(_variant(m), v) for m, v in members.items()]
    int_ty = _rust_int_type(fail_closed)
    out = ["#[derive(Clone, Copy, Debug, PartialEq, Default)]", f"pub enum {name} {{"]
    for i, (vn, _) in enumerate(variants):
        out.append(f"    {'#[default] ' if i == 0 else ''}{vn},")
    out.append("}")
    out.append(f"impl {name} {{")
    out.append(f"    pub fn wire(self) -> {int_ty} {{ match self {{")
    for vn, v in variants:
        out.append(f"        Self::{vn} => {v},")
    out.append("    } }")
    if fail_closed:
        # fail-closed: an unknown wire value is a typed error, never a panic.
        out.append(f"    pub fn from_wire(v: {int_ty}) -> Result<Self, DecodeError> {{ Ok(match v {{")
        for vn, v in variants:
            out.append(f"        {v} => Self::{vn},")
        out.append(f'        _ => return Err(DecodeError::UnknownEnum {{ enum_name: "{name}", value: v }}),')
        out.append("    }) }")
    else:
        out.append(f"    pub fn from_wire(v: {int_ty}) -> Self {{ match v {{")
        for vn, v in variants:
            out.append(f"        {v} => Self::{vn},")
        out.append(f'        _ => panic!("bad {name} wire value {{}}", v),')
        out.append("    } }")
    out.append("}")
    return out


def _emit_message(msg, forward_compat: bool = False, fail_closed: bool = False) -> list[str]:
    out = ["#[derive(Clone, Debug, PartialEq, Default)]", f"pub struct {msg.name} {{"]
    for f in msg.fields:
        out.append(f"    pub {f.name}: {_field_type(f, fail_closed)},")
    if forward_compat:
        # unknown/newer-version fields, preserved verbatim (empty when none).
        # These are (map-key, value) pairs — map keys stay i64 in both modes
        # (CBOR field tags; the value carrier is what widens under fail-closed).
        out.append("    pub wire_residual: Vec<(i64, Cbor)>,")
    out.append("}")
    out.append(f"impl {msg.name} {{")
    # encoded (tag, expr) pairs for the known wire fields. Encode is identical in
    # both modes (deterministic minimal CBOR) — only the field carrier widens.
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
    # from_cbor — panicking (default) or `Result`-returning (fail-closed).
    if fail_closed:
        out += _from_cbor_fail_closed(msg, forward_compat)
    else:
        out += _from_cbor_default(msg, forward_compat)
    out.append("}")
    return out


def _from_cbor_default(msg, forward_compat: bool) -> list[str]:
    """Today's infallible `from_cbor` (panics on malformed input). Unchanged."""
    out = ["    pub fn from_cbor(c: &Cbor) -> Self {", "        Self {"]
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
    out += ["        }", "    }"]
    return out


def _from_cbor_fail_closed(msg, forward_compat: bool) -> list[str]:
    """Fail-closed `from_cbor`: returns `Result<Self, DecodeError>`, propagates
    a typed error with `?` on every missing key / wrong type / unknown enum
    arm / short field, and never panics on any input."""
    out = ["    pub fn from_cbor(c: &Cbor) -> Result<Self, DecodeError> {", "        Ok(Self {"]
    for f in msg.fields:
        if f.transient:
            dec = "Default::default()"
        elif f.optional:
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
        # from_cbor is fallible (`Result<_, DecodeError>`); roundtrip input is
        # corpus bytes, so a decode failure panics with the message name.
        lines.append(
            f'        "{m.name}" => crate::cbor::encode('
            f'&{m.name}::from_cbor(&c).expect("decode: {m.name}").to_cbor()),'
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
