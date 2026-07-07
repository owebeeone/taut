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

import struct
from pathlib import Path

from ..ir.model import EnumRef, ListOf, MapOf, MsgRef, Scalar, Schema, TypeRef
from ..wire import codec

_TAUT = Path(__file__).resolve().parents[3]      # .../glial-dev/taut
_REPO = _TAUT.parent                              # trial/ is a sibling
_GEN = _REPO / "trial" / "cpp" / "generated"
TYPES_PATH = _GEN / "types.hpp"
CORPUS_PATH = _GEN / "corpus.hpp"


def _variant(member: str) -> str:
    return "".join(p.capitalize() for p in member.split("_"))


def _ident(name: str) -> str:
    return "".join(c if c.isalnum() else "_" for c in name)


def _try_enum_fn(name: str) -> str:
    return f"try_{_ident(name)}_from_wire"


def _uses_map(t: TypeRef) -> bool:
    if isinstance(t, MapOf):
        return True
    if isinstance(t, ListOf):
        return _uses_map(t.elem)
    return False


def _msg_constexpr_ok(msg) -> bool:
    return not any(_uses_map(f.type) for f in msg.fields)


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
        return {"int": "long long", "float": "double", "str": "std::string_view", "bytes": "std::string_view", "bool": "bool"}[t.kind]
    if isinstance(t, (EnumRef, MsgRef)):
        return t.name
    if isinstance(t, ListOf):
        return f"std::vector<{_base_type(t.elem)}>"
    if isinstance(t, MapOf):
        return f"std::map<{_base_type(t.key)}, {_base_type(t.value)}>"
    raise TypeError(t)


def _field_type(f) -> str:
    base = _base_type(f.type)
    return f"std::optional<{base}>" if f.optional else base


def _encode_scalar(t: TypeRef, expr: str) -> str:
    if isinstance(t, Scalar):
        return {
            "int": f"b.integer({expr});",
            "float": f"b.float_({expr});",
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
        return {"int": f"{acc}.as_int()", "float": f"{acc}.as_float()", "bool": f"{acc}.as_bool()",
                "str": f"{acc}.as_text()", "bytes": f"{acc}.as_bytes()"}[t.kind]
    if isinstance(t, EnumRef):
        return f"static_cast<{t.name}>({acc}.as_int())"
    if isinstance(t, MsgRef):
        return f"taut::{t.name}::from_cbor({acc})"
    raise TypeError(t)


def _try_scalar_method(t: Scalar) -> str:
    return {"int": "try_int", "float": "try_float", "bool": "try_bool",
            "str": "try_text", "bytes": "try_bytes"}[t.kind]


def _try_decode_value(t: TypeRef, acc: str, target: str, ret: str, tmp: str) -> list[str]:
    if isinstance(t, Scalar):
        method = _try_scalar_method(t)
        return [
            f"    auto {tmp} = ({acc}).{method}();",
            f"    if (!{tmp}) return DecodeResult<{ret}>::fail({tmp}.error);",
            f"    {target} = {tmp}.value;",
        ]
    if isinstance(t, EnumRef):
        wire = f"{tmp}_wire"
        enum = f"{tmp}_enum"
        return [
            f"    auto {wire} = ({acc}).try_int();",
            f"    if (!{wire}) return DecodeResult<{ret}>::fail({wire}.error);",
            f"    auto {enum} = {_try_enum_fn(t.name)}({wire}.value);",
            f"    if (!{enum}) return DecodeResult<{ret}>::fail({enum}.error);",
            f"    {target} = {enum}.value;",
        ]
    if isinstance(t, MsgRef):
        nested = f"{tmp}_msg"
        return [
            f"    auto {nested} = {t.name}::try_from_cbor({acc});",
            f"    if (!{nested}) return DecodeResult<{ret}>::fail({nested}.error);",
            f"    {target} = {nested}.value;",
        ]
    if isinstance(t, ListOf):
        arr = f"{tmp}_arr"
        item = f"{tmp}_item"
        lines = [
            f"    auto {arr} = ({acc}).try_array();",
            f"    if (!{arr}) return DecodeResult<{ret}>::fail({arr}.error);",
            f"    {target}.clear();",
            f"    for (const auto& x : *{arr}.value) {{",
            f"      {_base_type(t.elem)} {item}{{}};",
        ]
        nested = _try_decode_value(t.elem, "x", item, ret, f"{tmp}_elem")
        lines.extend("  " + line for line in nested)
        lines.extend([
            f"      {target}.push_back({item});",
            "    }",
        ])
        return lines
    if isinstance(t, MapOf):
        arr = f"{tmp}_arr"
        key = f"{tmp}_key"
        val = f"{tmp}_val"
        key_cbor = f"{tmp}_key_cbor"
        val_cbor = f"{tmp}_val_cbor"
        lines = [
            f"    auto {arr} = ({acc}).try_array();",
            f"    if (!{arr}) return DecodeResult<{ret}>::fail({arr}.error);",
            f"    {target}.clear();",
            f"    for (const auto& e : *{arr}.value) {{",
            f"      auto {key_cbor} = e.try_get(1);",
            f"      if (!{key_cbor}) return DecodeResult<{ret}>::fail({key_cbor}.error);",
            f"      auto {val_cbor} = e.try_get(2);",
            f"      if (!{val_cbor}) return DecodeResult<{ret}>::fail({val_cbor}.error);",
            f"      {_base_type(t.key)} {key}{{}};",
            f"      {_base_type(t.value)} {val}{{}};",
        ]
        lines.extend("  " + line for line in _try_decode_value(t.key, f"*{key_cbor}.value", key, ret, f"{tmp}_k"))
        lines.extend("  " + line for line in _try_decode_value(t.value, f"*{val_cbor}.value", val, ret, f"{tmp}_v"))
        lines.extend([
            f"      {target}[{key}] = {val};",
            "    }",
        ])
        return lines
    raise TypeError(t)


def _field_encode_lines(f) -> list[str]:
    if f.optional:
        # parenthesize the deref: `(*x).to_cbor(b)`, not `*x.to_cbor(b)` (precedence)
        return [f"    if ({f.name}.has_value()) {{ {_encode_scalar(f.type, '(*' + f.name + ')')} }} else {{ b.null_(); }}"]
    if isinstance(f.type, ListOf):
        return [f"    b.array({f.name}.size());",
                f"    for (const auto& x : {f.name}) {{ {_encode_scalar(f.type.elem, 'x')} }}"]
    if isinstance(f.type, MapOf):  # std::map iterates in ascending key order
        mk, mv = _encode_scalar(f.type.key, "k"), _encode_scalar(f.type.value, "v")
        return [f"    b.array({f.name}.size());",
                f"    for (const auto& [k, v] : {f.name}) {{ b.map(2); b.uint(1); {mk} b.uint(2); {mv} }}"]
    return [f"    {_encode_scalar(f.type, f.name)}"]


def _emit_from_cbor(msg, forward_compat: bool = False) -> list[str]:
    qual = "constexpr " if _msg_constexpr_ok(msg) else ""
    lines = [f"  static {qual}{msg.name} from_cbor(const Cbor& c) {{", f"    {msg.name} v{{}};"]
    for f in msg.fields:
        if f.transient:
            continue  # native-only; left default
        if f.optional:
            lines.append(f"    {{ const auto& f = c.get({f.tag}); if (!f.is_null()) v.{f.name} = {_decode_expr(f.type, 'f')}; }}")
        elif isinstance(f.type, ListOf):
            lines.append(f"    for (const auto& x : c.get({f.tag}).as_array()) v.{f.name}.push_back({_decode_expr(f.type.elem, 'x')});")
        elif isinstance(f.type, MapOf):
            dk, dv = _decode_expr(f.type.key, "e.get(1)"), _decode_expr(f.type.value, "e.get(2)")
            lines.append(f"    for (const auto& e : c.get({f.tag}).as_array()) v.{f.name}[{dk}] = {dv};")
        else:
            lines.append(f"    v.{f.name} = {_decode_expr(f.type, f'c.get({f.tag})')};")
    if forward_compat:
        known = " && ".join(f"kv.first != {f.tag}" for f in msg.wire_fields()) or "true"
        lines.append(f"    for (const auto& kv : c.map) if ({known}) v.wire_residual.push_back(kv);")
    lines.append("    return v;")
    lines.append("  }")
    return lines


def _emit_try_from_cbor(msg, forward_compat: bool = False) -> list[str]:
    lines = [f"  static DecodeResult<{msg.name}> try_from_cbor(const Cbor& c) {{", f"    {msg.name} v{{}};"]
    for f in msg.fields:
        if f.transient:
            continue
        field = f"__field_{f.tag}"
        lines.append(f"    auto {field} = c.try_get({f.tag});")
        if f.optional:
            lines.append(f"    if (!{field}) return DecodeResult<{msg.name}>::fail({field}.error);")
            lines.append(f"    if ({field}.value->is_null()) {{")
            lines.append(f"      v.{f.name} = std::nullopt;")
            lines.append("    } else {")
            tmp = f"__value_{f.tag}"
            lines.append(f"      {_base_type(f.type)} {tmp}{{}};")
            nested = _try_decode_value(f.type, f"*{field}.value", tmp, msg.name, f"__decoded_{f.tag}")
            lines.extend("  " + line for line in nested)
            lines.append(f"      v.{f.name} = {tmp};")
            lines.append("    }")
        else:
            lines.append(f"    if (!{field}) return DecodeResult<{msg.name}>::fail({field}.error);")
            lines.extend(_try_decode_value(f.type, f"*{field}.value", f"v.{f.name}", msg.name, f"__decoded_{f.tag}"))
    if forward_compat:
        known = " && ".join(f"kv.first != {f.tag}" for f in msg.wire_fields()) or "true"
        lines.append("    auto __map = c.try_map();")
        lines.append(f"    if (!__map) return DecodeResult<{msg.name}>::fail(__map.error);")
        lines.append(f"    for (const auto& kv : *__map.value) if ({known}) v.wire_residual.push_back(kv);")
    lines.append(f"    return DecodeResult<{msg.name}>::success(v);")
    lines.append("  }")
    return lines


def _emit_to_cbor(msg, forward_compat: bool = False) -> list[str]:
    wire = sorted(msg.wire_fields(), key=lambda f: f.tag)
    qual = "constexpr " if _msg_constexpr_ok(msg) else ""
    lines = [f"  {qual}void to_cbor(Buf& b) const {{"]
    if forward_compat:
        # merge residual (ascending) with known fields (ascending) -> canonical order
        lines.append(f"    b.map({len(wire)} + wire_residual.size());")
        lines.append("    std::size_t __ri = 0;")
        flush = ("    while (__ri < wire_residual.size() && wire_residual[__ri].first < {tag}) "
                 "{{ b.uint(static_cast<unsigned long long>(wire_residual[__ri].first)); "
                 "encode_value(b, wire_residual[__ri].second); ++__ri; }}")
        for f in wire:
            lines.append(flush.format(tag=f.tag))
            lines.append(f"    b.uint({f.tag});")
            lines += _field_encode_lines(f)
        lines.append("    while (__ri < wire_residual.size()) "
                     "{ b.uint(static_cast<unsigned long long>(wire_residual[__ri].first)); "
                     "encode_value(b, wire_residual[__ri].second); ++__ri; }")
    else:
        lines.append(f"    b.map({len(wire)});")
        for f in wire:
            lines.append(f"    b.uint({f.tag});")
            lines += _field_encode_lines(f)
    lines.append("  }")
    return lines


def _emit_types(schema: Schema, forward_compat: bool = False) -> str:
    has_map = any(isinstance(f.type, MapOf) for m in schema.messages.values() for f in m.fields)
    lines = [
        "// GENERATED native C++ types by taut/src/taut/gen/cpp.py — do not edit.",
        "#pragma once",
        *(["#include <map>"] if has_map else []),
        "#include <optional>",
        "#include <string_view>",
        "#include <utility>",
        "#include <vector>",
        '#include "taut/cbor.hpp"',
        "",
        "namespace taut {",
        "",
    ]
    for e in schema.enums.values():
        lines.append(f"enum class {e.name} : long long {{")
        for member, val in e.members.items():
            lines.append(f"  {_variant(member)} = {val},")
        lines.append("};")
        lines.append(f"inline constexpr long long wire({e.name} v) {{ return static_cast<long long>(v); }}")
        lines.append(f"inline constexpr DecodeResult<{e.name}> {_try_enum_fn(e.name)}(long long v) {{")
        lines.append("  switch (v) {")
        for member, val in e.members.items():
            lines.append(f"    case {val}: return DecodeResult<{e.name}>::success({e.name}::{_variant(member)});")
        lines.append(f"    default: return DecodeResult<{e.name}>::fail(DecodeError::unknown_enum(\"{e.name}\", v));")
        lines.append("  }")
        lines.append("}")
        lines.append("")
    for m in schema.messages.values():
        lines.append(f"struct {m.name} {{")
        for f in m.fields:
            lines.append(f"  {_field_type(f)} {f.name};")
        if forward_compat:
            lines.append("  std::vector<std::pair<long long, Cbor>> wire_residual;")
        lines.extend(_emit_to_cbor(m, forward_compat))
        lines.extend(_emit_from_cbor(m, forward_compat))
        lines.extend(_emit_try_from_cbor(m, forward_compat))
        lines.append("};")
        lines.append("")
    lines.append("} // namespace taut")
    return "\n".join(lines) + "\n"


# --- corpus values (typed construction) ---------------------------------------

def _render(schema: Schema, t: TypeRef, v) -> str:
    if isinstance(t, Scalar):
        if t.kind == "int":
            return str(v)
        if t.kind == "float":
            bits = struct.unpack(">Q", struct.pack(">d", float(v)))[0]
            return f"taut::f64_from_bits(0x{bits:016x}ULL)"
        if t.kind == "bool":
            return "true" if v else "false"
        if t.kind == "str":
            return _lit(v.encode("utf-8"))
        return _lit(v)  # bytes
    if isinstance(t, EnumRef):
        return f"taut::{t.name}::{_variant(v)}"
    if isinstance(t, MsgRef):
        return _render_struct(schema, t.name, v)
    if isinstance(t, ListOf):
        return "{" + ", ".join(_render(schema, t.elem, e) for e in v) + "}"
    if isinstance(t, MapOf):
        items = v.items() if isinstance(v, dict) else v
        return "{" + ", ".join("{" + _render(schema, t.key, k) + ", " + _render(schema, t.value, val) + "}" for k, val in items) + "}"
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
    return f"taut::{msg_name}{{{', '.join(parts)}}}"


def _emit_corpus(schema: Schema, references: dict[str, tuple[str, dict]]) -> str:
    lines = [
        "// GENERATED compile-time corpus oracle by taut/src/taut/gen/cpp.py — do not edit.",
        "// Each static_assert constructs the native value and proves its encoding at COMPILE TIME.",
        "#pragma once",
        '#include "types.hpp"',
        "",
        "namespace taut::corpus {",
        "",
    ]
    count = 0
    for name in sorted(references):
        message, value = references[name]
        encoded = codec.encode(schema, message, value)
        fn = _ident(name)
        lines.append(f"// {name} ({message})")
        # encode: construct the native value, prove its bytes == golden
        lines.append(f"consteval taut::Buf encode_{fn}() {{")
        lines.append(f"  auto v = {_render_struct(schema, message, value)};")
        lines.append("  taut::Buf b; v.to_cbor(b); return b;")
        lines.append("}")
        lines.append(f'static_assert(taut::eq_hex(encode_{fn}(), "{encoded.hex()}"), "{name} encode");')
        # round-trip: parse golden -> from_cbor -> to_cbor, prove == golden
        lines.append(f"consteval taut::Buf roundtrip_{fn}() {{")
        lines.append(f"  std::string_view src = {_lit(encoded)};")
        lines.append(f"  auto v = taut::{message}::from_cbor(taut::parse(src));")
        lines.append("  taut::Buf b; v.to_cbor(b); return b;")
        lines.append("}")
        lines.append(f'static_assert(taut::eq(roundtrip_{fn}(), {_lit(encoded)}), "{name} roundtrip");')
        lines.append("")
        count += 1
    lines.append(f"inline constexpr int VECTOR_COUNT = {count};")
    lines.append("")
    lines.append("} // namespace taut::corpus")
    return "\n".join(lines) + "\n"


def emit(schema: Schema, references: dict[str, tuple[str, dict]]) -> None:
    _GEN.mkdir(parents=True, exist_ok=True)
    TYPES_PATH.write_text(_emit_types(schema))
    CORPUS_PATH.write_text(_emit_corpus(schema, references))
