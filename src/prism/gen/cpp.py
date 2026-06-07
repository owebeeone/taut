"""Generate C++ native types + a compile-time corpus oracle from the IR (P6).

Two generated headers (trial/cpp/generated/):
  - types.hpp  : one `enum class` per IR enum, one `struct` per message with a
                 `constexpr to_cbor(Buf&)`. These are the M3 native C++ types
                 (idiomatic struct/enum, transient fields present-but-off-the-wire).
  - corpus.hpp : per vector, a `consteval` that constructs the *typed value* and
                 encodes it, plus `static_assert(eq_hex(value.to_cbor(), golden))`.

So the static_assert oracle runs through the native types, at compile time, with
zero runtime cost — the C++ form of the conformance corpus (build prompt §5a).

`emit(schema, references)` is given the reference values by the caller (importing
corpus.build here would be a cycle).
"""

from __future__ import annotations

from pathlib import Path

from ..ir.model import EnumRef, ListOf, MsgRef, Scalar, Schema, TypeRef
from ..wire import codec

_PRISM = Path(__file__).resolve().parents[3]      # .../glial-dev/prism
_REPO = _PRISM.parent                              # trial/ is a sibling
_GEN = _REPO / "trial" / "cpp" / "generated"
TYPES_PATH = _GEN / "types.hpp"
CORPUS_PATH = _GEN / "corpus.hpp"


def _variant(member: str) -> str:
    return "".join(p.capitalize() for p in member.split("_"))


def _ident(name: str) -> str:
    return "".join(c if c.isalnum() else "_" for c in name)


def _lit(data: bytes) -> str:
    """A string_view literal with explicit length, safe for any byte."""
    out = []
    for byte in data:
        if byte == 0x22:
            out.append('\\"')
        elif byte == 0x5C:
            out.append("\\\\")
        elif 0x20 <= byte < 0x7F:
            out.append(chr(byte))
        else:
            out.append(f'\\x{byte:02x}""')
    return f'std::string_view("{"".join(out)}", {len(data)})'


# --- native type declarations -------------------------------------------------

def _base_type(t: TypeRef) -> str:
    if isinstance(t, Scalar):
        return {"int": "long long", "str": "std::string_view", "bytes": "std::string_view", "bool": "bool"}[t.kind]
    if isinstance(t, (EnumRef, MsgRef)):
        return t.name
    if isinstance(t, ListOf):
        return f"std::vector<{_base_type(t.elem)}>"
    raise TypeError(t)


def _field_type(f) -> str:
    base = _base_type(f.type)
    return f"std::optional<{base}>" if f.optional else base


def _encode_scalar(t: TypeRef, expr: str) -> str:
    if isinstance(t, Scalar):
        return {
            "int": f"b.integer({expr});",
            "bool": f"b.boolean({expr});",
            "str": f"b.text({expr});",
            "bytes": f"b.bytes({expr});",
        }[t.kind]
    if isinstance(t, EnumRef):
        return f"b.integer(static_cast<long long>({expr}));"
    if isinstance(t, MsgRef):
        return f"{expr}.to_cbor(b);"
    raise TypeError(t)


def _decode_expr(t: TypeRef, acc: str) -> str:
    if isinstance(t, Scalar):
        return {"int": f"{acc}.as_int()", "bool": f"{acc}.as_bool()",
                "str": f"{acc}.as_text()", "bytes": f"{acc}.as_bytes()"}[t.kind]
    if isinstance(t, EnumRef):
        return f"static_cast<{t.name}>({acc}.as_int())"
    if isinstance(t, MsgRef):
        return f"prism::{t.name}::from_cbor({acc})"
    raise TypeError(t)


def _emit_from_cbor(msg) -> list[str]:
    lines = [f"  static constexpr {msg.name} from_cbor(const Cbor& c) {{", f"    {msg.name} v{{}};"]
    for f in msg.fields:
        if f.transient:
            continue  # native-only; left default
        if f.optional:
            lines.append(f"    {{ const auto& f = c.get({f.tag}); if (!f.is_null()) v.{f.name} = {_decode_expr(f.type, 'f')}; }}")
        elif isinstance(f.type, ListOf):
            lines.append(f"    for (const auto& x : c.get({f.tag}).as_array()) v.{f.name}.push_back({_decode_expr(f.type.elem, 'x')});")
        else:
            lines.append(f"    v.{f.name} = {_decode_expr(f.type, f'c.get({f.tag})')};")
    lines.append("    return v;")
    lines.append("  }")
    return lines


def _emit_to_cbor(msg) -> list[str]:
    wire = sorted(msg.wire_fields(), key=lambda f: f.tag)
    lines = ["  constexpr void to_cbor(Buf& b) const {", f"    b.map({len(wire)});"]
    for f in wire:
        lines.append(f"    b.uint({f.tag});")
        if f.optional:
            lines.append(f"    if ({f.name}.has_value()) {{ {_encode_scalar(f.type, '*' + f.name)} }} else {{ b.null_(); }}")
        elif isinstance(f.type, ListOf):
            lines.append(f"    b.array({f.name}.size());")
            lines.append(f"    for (const auto& x : {f.name}) {{ {_encode_scalar(f.type.elem, 'x')} }}")
        else:
            lines.append(f"    {_encode_scalar(f.type, f.name)}")
    lines.append("  }")
    return lines


def _emit_types(schema: Schema) -> str:
    lines = [
        "// GENERATED native C++ types by prism/src/prism/gen/cpp.py — do not edit.",
        "#pragma once",
        "#include <optional>",
        "#include <string_view>",
        "#include <vector>",
        '#include "prism/cbor.hpp"',
        "",
        "namespace prism {",
        "",
    ]
    for e in schema.enums.values():
        lines.append(f"enum class {e.name} : long long {{")
        for member, val in e.members.items():
            lines.append(f"  {_variant(member)} = {val},")
        lines.append("};")
        lines.append("")
    for m in schema.messages.values():
        lines.append(f"struct {m.name} {{")
        for f in m.fields:
            lines.append(f"  {_field_type(f)} {f.name};")
        lines.extend(_emit_to_cbor(m))
        lines.extend(_emit_from_cbor(m))
        lines.append("};")
        lines.append("")
    lines.append("} // namespace prism")
    return "\n".join(lines) + "\n"


# --- corpus values (typed construction) ---------------------------------------

def _render(schema: Schema, t: TypeRef, v) -> str:
    if isinstance(t, Scalar):
        if t.kind == "int":
            return str(v)
        if t.kind == "bool":
            return "true" if v else "false"
        if t.kind == "str":
            return _lit(v.encode("utf-8"))
        return _lit(v)  # bytes
    if isinstance(t, EnumRef):
        return f"prism::{t.name}::{_variant(v)}"
    if isinstance(t, MsgRef):
        return _render_struct(schema, t.name, v)
    if isinstance(t, ListOf):
        return "{" + ", ".join(_render(schema, t.elem, e) for e in v) + "}"
    raise TypeError(t)


def _render_struct(schema: Schema, msg_name: str, value: dict) -> str:
    msg = schema.messages[msg_name]
    parts = []
    for f in msg.fields:
        if f.transient or f.name not in value:
            parts.append("{}")                        # transient/absent: value-init
        elif f.optional:
            parts.append("std::nullopt" if value[f.name] is None else _render(schema, f.type, value[f.name]))
        else:
            parts.append(_render(schema, f.type, value[f.name]))
    return f"prism::{msg_name}{{{', '.join(parts)}}}"


def _emit_corpus(schema: Schema, references: dict[str, tuple[str, dict]]) -> str:
    lines = [
        "// GENERATED compile-time corpus oracle by prism/src/prism/gen/cpp.py — do not edit.",
        "// Each static_assert constructs the native value and proves its encoding at COMPILE TIME.",
        "#pragma once",
        '#include "types.hpp"',
        "",
        "namespace prism::corpus {",
        "",
    ]
    count = 0
    for name in sorted(references):
        message, value = references[name]
        encoded = codec.encode(schema, message, value)
        fn = _ident(name)
        lines.append(f"// {name} ({message})")
        # encode: construct the native value, prove its bytes == golden
        lines.append(f"consteval prism::Buf encode_{fn}() {{")
        lines.append(f"  auto v = {_render_struct(schema, message, value)};")
        lines.append("  prism::Buf b; v.to_cbor(b); return b;")
        lines.append("}")
        lines.append(f'static_assert(prism::eq_hex(encode_{fn}(), "{encoded.hex()}"), "{name} encode");')
        # round-trip: parse golden -> from_cbor -> to_cbor, prove == golden
        lines.append(f"consteval prism::Buf roundtrip_{fn}() {{")
        lines.append(f"  std::string_view src = {_lit(encoded)};")
        lines.append(f"  auto v = prism::{message}::from_cbor(prism::parse(src));")
        lines.append("  prism::Buf b; v.to_cbor(b); return b;")
        lines.append("}")
        lines.append(f'static_assert(prism::eq(roundtrip_{fn}(), {_lit(encoded)}), "{name} roundtrip");')
        lines.append("")
        count += 1
    lines.append(f"inline constexpr int VECTOR_COUNT = {count};")
    lines.append("")
    lines.append("} // namespace prism::corpus")
    return "\n".join(lines) + "\n"


def emit(schema: Schema, references: dict[str, tuple[str, dict]]) -> None:
    _GEN.mkdir(parents=True, exist_ok=True)
    TYPES_PATH.write_text(_emit_types(schema))
    CORPUS_PATH.write_text(_emit_corpus(schema, references))
