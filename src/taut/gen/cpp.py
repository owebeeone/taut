"""Generate C++ native types + a compile-time corpus oracle from the IR (P6).

Two generated headers (trial/cpp/generated/):
  - types.hpp  : one `enum class` per IR enum, one `struct` per message with a
                 `constexpr to_cbor(Buf&)` and the fail-closed `try_from_cbor`, which
                 returns a DecodeResult. These are the M3 native C++ types
                 (idiomatic struct/enum, transient fields present-but-off-the-wire).
  - corpus.hpp : per vector, a `consteval` that constructs the *typed value* and
                 encodes it, plus `static_assert(eq_hex(value.to_cbor(), golden))`,
                 and a `consteval` that decodes the golden bytes back through
                 `try_decode` and `try_from_cbor` and re-encodes them.

So the static_assert oracle runs through the native types, at compile time, with
zero runtime cost — the C++ form of the conformance corpus (build prompt §5a).

Names. A message's code compiles whatever its fields are called (TautV010Plan.md §0; the
parity fixture's `Names`), because no name the generator chooses can meet a field:
  - every parameter and local it declares in a struct starts with `__`, which C++
    reserves for the implementation, so no field is named like one;
  - every name it takes from outside the struct (the runtime's types and helpers, the
    schema's enums and messages, the struct itself, their `try_` functions) is qualified
    from the global namespace, `::taut::`, so no member can hide it. `std::` needs no
    such care: the name before a `::` is looked up as a namespace or a type, never as a
    data member.
A field still cannot take a member function's name (`to_cbor`, `try_from_cbor`), and the
`wire_` prefix is taut's (`ir/validate.py`).

`emit(schema, references)` is given the reference values by the caller (importing
corpus.build here would be a cycle).
"""

from __future__ import annotations

import struct
from pathlib import Path

from ..ir.model import MISSING_OK, EnumRef, ListOf, MapOf, MsgRef, Scalar, Schema, TypeRef
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


def _is_container(t: TypeRef) -> bool:
    """A list or map: decoded by filling it, where a scalar, enum or message is one expression."""
    return isinstance(t, (ListOf, MapOf))


# Every name a struct takes from outside it, qualified (the module docstring).
_NS = "::taut::"
# The parameters and the value `try_from_cbor` builds: `__` names, like every generated local.
_BUF = "__b"  # to_cbor's Buf
_SRC = "__c"  # try_from_cbor's Cbor
_OUT = "__v"  # the value try_from_cbor builds


def _loop_var(stem: str, depth: int) -> str:
    """A container loop's variable: `__` and the stem at a field's own level, numbered below
    it, so a nested loop never shadows the loop that encloses it."""
    return f"__{stem}" if depth == 0 else f"__{stem}{depth}"


def _holds_map(schema: Schema, t: TypeRef, seen: frozenset[str] = frozenset()) -> bool:
    """Whether a value of type `t` holds a std::map, directly or in a message it holds."""
    if isinstance(t, MapOf):
        return True
    if isinstance(t, ListOf):
        return _holds_map(schema, t.elem, seen)
    if isinstance(t, MsgRef) and t.name not in seen:
        return any(_holds_map(schema, f.type, seen | {t.name}) for f in schema.messages[t.name].fields)
    return False


def _literal(schema: Schema, msg) -> bool:
    """Whether `msg`'s struct is a literal type, so its functions can be constexpr. libc++'s
    std::map is not one, so neither is a message that holds a map, directly or in a message:
    a constexpr function that returns one does not compile."""
    return not _holds_map(schema, MsgRef(msg.name))


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

def _base_type(t: TypeRef, ns: str = _NS) -> str:
    """The native type of `t`; `ns` qualifies an enum or message: `::taut::` inside a struct
    (the module docstring), `taut::` in the corpus."""
    if isinstance(t, Scalar):
        return {"int": "long long", "float": "double", "str": "std::string_view", "bytes": "std::string_view", "bool": "bool"}[t.kind]
    if isinstance(t, (EnumRef, MsgRef)):
        return f"{ns}{t.name}"
    if isinstance(t, ListOf):
        return f"std::vector<{_base_type(t.elem, ns)}>"
    if isinstance(t, MapOf):
        return f"std::map<{_base_type(t.key, ns)}, {_base_type(t.value, ns)}>"
    raise TypeError(t)


def _field_type(f) -> str:
    base = _base_type(f.type)
    return f"std::optional<{base}>" if f.optional else base


def _encode_scalar(t: TypeRef, expr: str) -> str:
    if isinstance(t, Scalar):
        method = {"int": "integer", "float": "float_", "bool": "boolean", "str": "text", "bytes": "bytes"}[t.kind]
        return f"{_BUF}.{method}({expr});"
    if isinstance(t, EnumRef):
        return f"{_BUF}.integer(static_cast<long long>({expr}));"
    if isinstance(t, MsgRef):
        return f"{expr}.to_cbor({_BUF});"
    raise TypeError(t)


def _encode_stmts(t: TypeRef, expr: str, depth: int = 0) -> list[str]:
    """Encode `expr`, a value of type `t`, at any nesting. A list is its count, then each item.
    A map is its count, then one `{1: key, 2: value}` map per entry in ascending key order,
    which is std::map's own order."""
    if isinstance(t, ListOf):
        x = _loop_var("x", depth)
        item = " ".join(_encode_stmts(t.elem, x, depth + 1))
        return [f"{_BUF}.array({expr}.size());", f"for (const auto& {x} : {expr}) {{ {item} }}"]
    if isinstance(t, MapOf):
        k, v = _loop_var("k", depth), _loop_var("v", depth)
        key = " ".join(_encode_stmts(t.key, k, depth + 1))
        value = " ".join(_encode_stmts(t.value, v, depth + 1))
        return [f"{_BUF}.array({expr}.size());",
                f"for (const auto& [{k}, {v}] : {expr}) {{ {_BUF}.map(2); {_BUF}.uint(1); {key} "
                f"{_BUF}.uint(2); {value} }}"]
    return [_encode_scalar(t, expr)]


def _duplicate_key_error(key_type: TypeRef, key: str) -> str:
    """A `map<K,V>` field's repeated entry key, as text (TautCheckedDecode.md §8 question 9):
    K is int, str or bool (`ir/validate.py`), and a bool is `true` or `false`."""
    kind = key_type.kind if isinstance(key_type, Scalar) else "int"
    factory = {"str": "duplicate_map_text_key", "bool": "duplicate_map_bool_key"}.get(kind, "duplicate_map_key")
    return f"{_NS}DecodeError::{factory}({key})"


def _try_scalar_method(t: Scalar) -> str:
    return {"int": "try_int", "float": "try_float", "bool": "try_bool",
            "str": "try_text", "bytes": "try_bytes"}[t.kind]


def _result_type(msg_name: str) -> str:
    return f"{_NS}DecodeResult<{_NS}{msg_name}>"


def _return_if_failed(result: str, ret: str) -> str:
    """Return a failed DecodeResult's error from the `try_from_cbor` of message `ret`."""
    return f"if (!{result}) {{ return {_result_type(ret)}::fail({result}.error); }}"


def _try_decode_value(t: TypeRef, acc: str, target: str, ret: str, tmp: str, depth: int = 0) -> list[str]:
    """The checked decode of `acc`, a Cbor, into `target`, at any nesting. The first error
    returns, in the reference's order (`wire/codec.py`): a map entry reads keys 1 and 2, then
    its key, refuses a repeated key and only then reads its value."""
    if isinstance(t, Scalar):
        method = _try_scalar_method(t)
        return [
            f"    auto {tmp} = ({acc}).{method}();",
            f"    {_return_if_failed(tmp, ret)}",
            f"    {target} = {tmp}.value;",
        ]
    if isinstance(t, EnumRef):
        wire = f"{tmp}_wire"
        enum = f"{tmp}_enum"
        return [
            f"    auto {wire} = ({acc}).try_int();",
            f"    {_return_if_failed(wire, ret)}",
            f"    auto {enum} = {_NS}{_try_enum_fn(t.name)}({wire}.value);",
            f"    {_return_if_failed(enum, ret)}",
            f"    {target} = {enum}.value;",
        ]
    if isinstance(t, MsgRef):
        nested = f"{tmp}_msg"
        return [
            f"    auto {nested} = {_NS}{t.name}::try_from_cbor({acc});",
            f"    {_return_if_failed(nested, ret)}",
            f"    {target} = {nested}.value;",
        ]
    if isinstance(t, ListOf):
        arr = f"{tmp}_arr"
        item = f"{tmp}_item"
        x = _loop_var("x", depth)
        lines = [
            f"    auto {arr} = ({acc}).try_array();",
            f"    {_return_if_failed(arr, ret)}",
            f"    {target}.clear();",
            f"    for (const auto& {x} : *{arr}.value) {{",
            f"      {_base_type(t.elem)} {item}{{}};",
        ]
        nested = _try_decode_value(t.elem, x, item, ret, f"{tmp}_elem", depth + 1)
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
        e = _loop_var("e", depth)
        lines = [
            f"    auto {arr} = ({acc}).try_array();",
            f"    {_return_if_failed(arr, ret)}",
            f"    {target}.clear();",
            f"    for (const auto& {e} : *{arr}.value) {{",
            f"      auto {key_cbor} = {e}.try_get(1);",
            f"      {_return_if_failed(key_cbor, ret)}",
            f"      auto {val_cbor} = {e}.try_get(2);",
            f"      {_return_if_failed(val_cbor, ret)}",
            f"      {_base_type(t.key)} {key}{{}};",
            f"      {_base_type(t.value)} {val}{{}};",
        ]
        key_lines = _try_decode_value(t.key, f"*{key_cbor}.value", key, ret, f"{tmp}_k", depth + 1)
        lines.extend("  " + line for line in key_lines)
        # A repeated entry key is refused after the key decodes, before its value (CD-E5).
        lines.extend([
            f"      if ({target}.count({key}) != 0) {{",
            f"        return {_result_type(ret)}::fail({_duplicate_key_error(t.key, key)});",
            "      }",
        ])
        value_lines = _try_decode_value(t.value, f"*{val_cbor}.value", val, ret, f"{tmp}_v", depth + 1)
        lines.extend("  " + line for line in value_lines)
        lines.extend([
            f"      {target}[{key}] = {val};",
            "    }",
        ])
        return lines
    raise TypeError(t)


def _field_encode_lines(f) -> list[str]:
    if f.optional:
        # parenthesize the deref: `(*x).to_cbor(__b)`, not `*x.to_cbor(__b)` (precedence)
        present = " ".join(_encode_stmts(f.type, f"(*{f.name})"))
        return [f"    if ({f.name}.has_value()) {{ {present} }} else {{ {_BUF}.null_(); }}"]
    return [f"    {stmt}" for stmt in _encode_stmts(f.type, f.name)]


def _emit_try_from_cbor(msg, forward_compat: bool = False, literal: bool = False) -> list[str]:
    """The fail-closed decode, the only one (TautCheckedDecode.md question 5): the value, or
    the first DecodeError in IR order. Constexpr when the struct is a literal type."""
    qual = "constexpr " if literal else ""
    result = _result_type(msg.name)
    lines = [
        f"  static {qual}{result} try_from_cbor(const {_NS}Cbor& {_SRC}) {{",
        f"    {_NS}{msg.name} {_OUT}{{}};",
        f"    auto __map = {_SRC}.try_map();  // a message is a map, even one with no fields",
        f"    if (!__map) {{ return {result}::fail(__map.error); }}",
    ]
    for f in msg.fields:
        if f.transient:
            continue
        field = f"__field_{f.tag}"
        if not f.optional:
            lines.append(f"    auto {field} = {_SRC}.try_get({f.tag});")
            lines.append(f"    {_return_if_failed(field, msg.name)}")
            lines.extend(_try_decode_value(f.type, f"*{field}.value", f"{_OUT}.{f.name}", msg.name,
                                           f"__decoded_{f.tag}"))
            continue
        if f.optional == MISSING_OK:  # an absent key reads as null, like a present null
            lines.append(f"    auto {field} = {_SRC}.try_get_opt({f.tag});")
            lines.append(f"    {_return_if_failed(field, msg.name)}")
            lines.append(f"    if ({field}.value == nullptr || {field}.value->is_null()) {{")
        else:
            lines.append(f"    auto {field} = {_SRC}.try_get({f.tag});")
            lines.append(f"    {_return_if_failed(field, msg.name)}")
            lines.append(f"    if ({field}.value->is_null()) {{")
        lines.append(f"      {_OUT}.{f.name} = std::nullopt;")
        lines.append("    } else {")
        tmp = f"__value_{f.tag}"
        lines.append(f"      {_base_type(f.type)} {tmp}{{}};")
        nested = _try_decode_value(f.type, f"*{field}.value", tmp, msg.name, f"__decoded_{f.tag}")
        lines.extend("  " + line for line in nested)
        lines.append(f"      {_OUT}.{f.name} = {tmp};")
        lines.append("    }")
    if forward_compat:
        kv = _loop_var("kv", 0)
        known = " && ".join(f"{kv}.first != {f.tag}" for f in msg.wire_fields()) or "true"
        lines.append(f"    for (const auto& {kv} : *__map.value) {{ if ({known}) {{ "
                     f"{_OUT}.wire_residual.push_back({kv}); }} }}")
    lines.append(f"    return {result}::success({_OUT});")
    lines.append("  }")
    return lines


def _emit_to_cbor(msg, forward_compat: bool = False, literal: bool = False) -> list[str]:
    wire = sorted(msg.wire_fields(), key=lambda f: f.tag)
    qual = "constexpr " if literal else ""
    lines = [f"  {qual}void to_cbor({_NS}Buf& {_BUF}) const {{"]
    if forward_compat:
        # merge residual (ascending) with known fields (ascending) -> canonical order
        lines.append(f"    {_BUF}.map({len(wire)} + wire_residual.size());")
        lines.append("    std::size_t __ri = 0;")
        emit_residual = (f"{{ {_BUF}.uint(static_cast<unsigned long long>(wire_residual[__ri].first)); "
                         f"{_NS}encode_value({_BUF}, wire_residual[__ri].second); ++__ri; }}")
        for f in wire:
            lines.append(f"    while (__ri < wire_residual.size() && wire_residual[__ri].first < {f.tag}) "
                         f"{emit_residual}")
            lines.append(f"    {_BUF}.uint({f.tag});")
            lines += _field_encode_lines(f)
        lines.append(f"    while (__ri < wire_residual.size()) {emit_residual}")
    else:
        lines.append(f"    {_BUF}.map({len(wire)});")
        for f in wire:
            lines.append(f"    {_BUF}.uint({f.tag});")
            lines += _field_encode_lines(f)
    lines.append("  }")
    return lines


def _emit_types(schema: Schema, forward_compat: bool = False) -> str:
    has_map = any(_uses_map(f.type) for m in schema.messages.values() for f in m.fields)
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
            lines.append(f"  std::vector<std::pair<long long, {_NS}Cbor>> wire_residual;")
        literal = _literal(schema, m)
        lines.extend(_emit_to_cbor(m, forward_compat, literal))
        lines.extend(_emit_try_from_cbor(m, forward_compat, literal))
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
        elif f.optional and value[f.name] is None:
            parts.append("std::nullopt")
        elif f.optional and _is_container(f.type):
            # a bare `{...}` would not engage the optional (`{}` is nullopt), so name the type
            parts.append(_base_type(f.type, "taut::") + _render(schema, f.type, value[f.name]))
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
        # round-trip: golden -> try_decode -> try_from_cbor -> to_cbor, prove == golden; a
        # refused golden leaves the Buf empty, so the static_assert names it
        lines.append(f"consteval taut::Buf roundtrip_{fn}() {{")
        lines.append(f"  auto c = taut::try_decode({_lit(encoded)});")
        lines.append(f"  auto v = taut::{message}::try_from_cbor(c.value);")
        lines.append("  taut::Buf b;")
        lines.append("  if (c && v) {")
        lines.append("    v.value.to_cbor(b);")
        lines.append("  }")
        lines.append("  return b;")
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
