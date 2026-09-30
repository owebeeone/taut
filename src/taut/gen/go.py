"""Go code generator — native structs + a deterministic-CBOR codec, mirroring the
Rust/C++/Swift generators. Pairs with the vendored `cbor.go` runtime (emitted by
`tautc gen --lang go --with-runtime`); both are `package taut`. Go's `Encode`
sorts map keys, so forward-compat residual just rides along (no merge).

Field/enum names are PascalCased (Go requires capitalized identifiers to export)
— which also means they can never collide with Go's (lowercase) keywords.

Types. `int` is `int64`, `str` `string`, `bytes` `[]byte`, `bool` `bool` and `float`
`float64`; an enum is a named `int64` and a message a struct. `list<T>` is `[]T` and
`map<K,V>` is `map[K]V`, nested as deep as the IR nests them (`list<list<int>>` is
`[][]int64`).

Optional. An optional field of type `T` is `*T`, whatever `T` is: a nil pointer is
null and any other pointer is the value. So an optional list is `*[]T` and an optional
map `*map[K]V`, and a pointer to an empty or nil slice or map is the empty array, not
null. A nil slice or map never means null: Go code treats nil and empty alike, and a
non-optional list or map encodes nil as the empty array.

Codec. One recursion over the type (`_emit_encode`, `_emit_decode`) generates every
legal shape (`taut/ir/validate.py`) at any depth; a list or map names its temporaries
after its depth, so an inner one never shadows an outer one. `ToCbor` appends each
field in IR order. `TryXFromCbor` decodes the fields in IR order with the checks of
`taut.wire.codec`, in its order (TautCheckedDecode.md CD-E5): a message is a map, a
list an array, a map an array of entry maps each holding keys 1 and 2 before either
is decoded, a repeated map key is `DuplicateMapKey` with the key as text (§8 question
9), and a wrong type is `WrongType` with its payload word. The output is gofmt-clean:
every block is braced over its own lines, and struct fields and enum constants are
aligned as gofmt aligns them.

Fail-closed (CD-E4, question 5). The decode entry points are `TryXFromBytes` and
`TryXFromCbor` for a message, and `TryXFromCbor` and `TryXFromWire` for an enum, and each
returns `(value, error)`, with a `*DecodeError` for bad input; no generated code panics.

Bounds (D26, TautCheckedDecode.md CD-B3; TautOptions.md OPT-L6). Each message gets
`XMaxDepth` and `XMaxEncodedLen`, its effective `max_depth` and `max_encoded_len` as
`options.effective` resolves them when the code is generated (-1 for no length bound), and
`TryXFromBytes`, a decode from bytes rooted at the message, which applies both through the
runtime's `TryDecodeWith` and then reads the tree with `TryXFromCbor`. It joins the `Try`
family rather than taking a `DecodeX` name, which would redeclare the runtime's
`DecodeError` for a message named `Error`, as glade's schema has.
"""

from __future__ import annotations

from typing import cast

from ..ir.model import MISSING_OK, EnumRef, FieldDef, ListOf, MapOf, MessageDef, MsgRef, Scalar, Schema, TypeRef
from ..ir.options import effective

_SCALAR_TYPES = {"int": "int64", "str": "string", "bytes": "[]byte", "bool": "bool", "float": "float64"}
_SCALAR_ENCODERS = {"int": "CInt", "str": "CText", "bytes": "CBytes", "bool": "CBool", "float": "CFloat"}
_SCALAR_DECODERS = {"int": "TryInt", "str": "TryText", "bytes": "TryBytes", "bool": "TryBool", "float": "TryFloat"}
_MAP_KEYS = ("int", "str", "bool")


def _pascal(name: str) -> str:
    return "".join(p[:1].upper() + p[1:] for p in name.split("_") if p)


def _go_ty(t: TypeRef) -> str:
    if isinstance(t, Scalar):
        return _SCALAR_TYPES[t.kind]
    if isinstance(t, (EnumRef, MsgRef)):
        return t.name
    if isinstance(t, ListOf):
        return f"[]{_go_ty(t.elem)}"
    if isinstance(t, MapOf):
        return f"map[{_go_ty(t.key)}]{_go_ty(t.value)}"
    raise TypeError(t)


def _field_type(f: FieldDef) -> str:
    base = _go_ty(f.type)
    return f"*{base}" if f.optional else base


def _map_key(t: MapOf) -> Scalar:
    """A map's key type: int, str or bool (validate allows no other)."""
    if not (isinstance(t.key, Scalar) and t.key.kind in _MAP_KEYS):
        raise TypeError(t)
    return t.key


def _sorts(t: TypeRef) -> bool:
    """Whether encoding `t` sorts map keys (and so needs the `sort` import)."""
    if isinstance(t, ListOf):
        return _sorts(t.elem)
    if isinstance(t, MapOf):
        return True
    return False


def _depth(name: str, depth: int) -> str:
    """A temporary's name at a nesting depth: `a`, then `a1`, `a2`..."""
    return f"{name}{depth or ''}"


def _operand(expr: str) -> str:
    """`expr` as the operand of a selector or an index: a dereference is parenthesized."""
    return f"({expr})" if expr.startswith("*") else expr


def _aligned(rows: list[tuple[str, str]]) -> list[str]:
    """`name rest` lines, one tab in, the names padded to one column as gofmt aligns them."""
    width = max((len(name) for name, _ in rows), default=0)
    return [f"\t{name.ljust(width)} {rest}" for name, rest in rows]


def _emit_err_check(out: list[str], ind: str, result: str = "v") -> None:
    out.append(f"{ind}if err != nil {{")
    out.append(f"{ind}\treturn {result}, err")
    out.append(f"{ind}}}")


# --- encode ------------------------------------------------------------------------------

def _enc_leaf(t: TypeRef, expr: str) -> str:
    """The Cbor expression for `expr`, a scalar, enum or message value."""
    if isinstance(t, Scalar):
        return f"{_SCALAR_ENCODERS[t.kind]}({expr})"
    if isinstance(t, EnumRef):
        return f"CInt(int64({expr}))"
    if isinstance(t, MsgRef):
        return f"{_operand(expr)}.ToCbor()"
    raise TypeError(t)


def _emit_encode(out: list[str], t: TypeRef, expr: str, ind: str, depth: int = 0) -> str:
    """Emit at indent `ind` the statements that encode the Go value `expr` of type `t`, and
    return the Cbor expression for it. A list is an array of its items; a map is an array
    of `{1: key, 2: value}` entry maps in ascending key order (false before true)."""
    if isinstance(t, ListOf):
        a, e = _depth("a", depth), _depth("e", depth)
        out.append(f"{ind}{a} := make([]Cbor, 0, len({expr}))")
        out.append(f"{ind}for _, {e} := range {expr} {{")
        item = _emit_encode(out, t.elem, e, ind + "\t", depth + 1)
        out.append(f"{ind}\t{a} = append({a}, {item})")
        out.append(f"{ind}}}")
        return f"CArr({a})"
    if isinstance(t, MapOf):
        key = _map_key(t)
        ks, k, a = _depth("ks", depth), _depth("k", depth), _depth("a", depth)
        less = f"!{ks}[i] && {ks}[j]" if key.kind == "bool" else f"{ks}[i] < {ks}[j]"
        out.append(f"{ind}{ks} := make([]{_go_ty(key)}, 0, len({expr}))")
        out.append(f"{ind}for {k} := range {expr} {{")
        out.append(f"{ind}\t{ks} = append({ks}, {k})")
        out.append(f"{ind}}}")
        out.append(f"{ind}sort.Slice({ks}, func(i, j int) bool {{ return {less} }})")
        out.append(f"{ind}{a} := make([]Cbor, 0, len({ks}))")
        out.append(f"{ind}for _, {k} := range {ks} {{")
        value = _emit_encode(out, t.value, f"{_operand(expr)}[{k}]", ind + "\t", depth + 1)
        out.append(f"{ind}\t{a} = append({a}, CMap([]KV{{{{K: 1, V: {_enc_leaf(key, k)}}}, {{K: 2, V: {value}}}}}))")
        out.append(f"{ind}}}")
        return f"CArr({a})"
    return _enc_leaf(t, expr)


def _emit_to_cbor(msg: MessageDef, forward_compat: bool) -> list[str]:
    fields = msg.wire_fields()
    out = [f"func (x {msg.name}) ToCbor() Cbor {{", f"\tm := make([]KV, 0, {len(fields)})"]
    for f in fields:
        value = f"x.{_pascal(f.name)}"
        if f.optional:
            # Always written: null when unset (the key is never omitted).
            out.append(f"\tif {value} == nil {{")
            out.append(f"\t\tm = append(m, KV{{K: {f.tag}, V: CNull()}})")
            out.append("\t} else {")
            item = _emit_encode(out, f.type, f"*{value}", "\t\t")
            out.append(f"\t\tm = append(m, KV{{K: {f.tag}, V: {item}}})")
            out.append("\t}")
        elif isinstance(f.type, (ListOf, MapOf)):
            out.append("\t{")
            item = _emit_encode(out, f.type, value, "\t\t")
            out.append(f"\t\tm = append(m, KV{{K: {f.tag}, V: {item}}})")
            out.append("\t}")
        else:
            out.append(f"\tm = append(m, KV{{K: {f.tag}, V: {_enc_leaf(f.type, value)}}})")
    if forward_compat:
        out.append("\tm = append(m, x.WireResidual...)")  # Encode sorts -> canonical
    out.append("\treturn CMap(m)")
    out.append("}")
    return out


# --- decode ------------------------------------------------------------------------------

def _try_dec_leaf(t: TypeRef, expr: str) -> str:
    """A Go expression returning `(native_value, error)` for `expr`, the Cbor of a scalar,
    enum or message."""
    if isinstance(t, Scalar):
        return f"{expr}.{_SCALAR_DECODERS[t.kind]}()"
    if isinstance(t, (EnumRef, MsgRef)):
        return f"Try{t.name}FromCbor({expr})"
    raise TypeError(t)


def _emit_decode(out: list[str], t: TypeRef, expr: str, ind: str, depth: int = 0) -> str:
    """Emit at indent `ind` the statements that decode `expr`, a Cbor, as type `t` into a
    new variable, and return its name (`x`, then `x1`, `x2`... by depth). Any error returns
    `v, err` from the enclosing `TryXFromCbor`."""
    x = _depth("x", depth)
    if isinstance(t, ListOf):
        arr, e = _depth("arr", depth), _depth("e", depth)
        out.append(f"{ind}{arr}, err := {expr}.TryArray()")
        _emit_err_check(out, ind)
        out.append(f"{ind}var {x} {_go_ty(t)}")
        out.append(f"{ind}for _, {e} := range {arr} {{")
        item = _emit_decode(out, t.elem, e, ind + "\t", depth + 1)
        out.append(f"{ind}\t{x} = append({x}, {item})")
        out.append(f"{ind}}}")
        return x
    if isinstance(t, MapOf):
        # An array of entry maps; each entry has keys 1 and 2 before either is decoded,
        # and a repeated key is refused (the last one never wins).
        key = _map_key(t)
        arr, e = _depth("arr", depth), _depth("e", depth)
        kc, vc, k = _depth("kc", depth), _depth("vc", depth), _depth("k", depth)
        body = ind + "\t"
        out.append(f"{ind}{arr}, err := {expr}.TryArray()")
        _emit_err_check(out, ind)
        out.append(f"{ind}{x} := {_go_ty(t)}{{}}")
        out.append(f"{ind}for _, {e} := range {arr} {{")
        out.append(f"{body}{kc}, err := {e}.Require(1)")
        _emit_err_check(out, body)
        out.append(f"{body}{vc}, err := {e}.Require(2)")
        _emit_err_check(out, body)
        out.append(f"{body}{k}, err := {_try_dec_leaf(key, kc)}")
        _emit_err_check(out, body)
        out.append(f"{body}if _, dup := {x}[{k}]; dup {{")
        out.append(f"{body}\treturn v, DuplicateMapKeyError({k})")   # the key as text, any K
        out.append(f"{body}}}")
        value = _emit_decode(out, t.value, vc, body, depth + 1)
        out.append(f"{body}{x}[{k}] = {value}")
        out.append(f"{ind}}}")
        return x
    out.append(f"{ind}{x}, err := {_try_dec_leaf(t, expr)}")
    _emit_err_check(out, ind)
    return x


def _emit_from_cbor(msg: MessageDef, forward_compat: bool) -> list[str]:
    # The schema stage (TautCheckedDecode.md CD-E5): the message must be a map, even one
    # with no fields; then each field in IR order.
    out = [f"func Try{msg.name}FromCbor(c Cbor) ({msg.name}, error) {{",
           f"\tvar v {msg.name}",
           "\tif _, err := c.TryMap(); err != nil {",
           "\t\treturn v, err",
           "\t}"]
    for f in msg.wire_fields():  # a transient field is native-only: left as the Go zero value
        dst = f"v.{_pascal(f.name)}"
        out.append("\t{")
        if f.optional == MISSING_OK:
            # An absent key reads as null, like a present null; a wrong type still fails.
            out.append(f"\t\tfv, ok, err := c.Lookup({f.tag})")
            _emit_err_check(out, "\t\t")
            out.append("\t\tif ok && !fv.IsNull() {")
        elif f.optional:
            # The key is required (the encoder always writes it); its value may be null.
            out.append(f"\t\tfv, err := c.Require({f.tag})")
            _emit_err_check(out, "\t\t")
            out.append("\t\tif !fv.IsNull() {")
        else:
            out.append(f"\t\tfv, err := c.Require({f.tag})")
            _emit_err_check(out, "\t\t")
        if f.optional:
            x = _emit_decode(out, f.type, "fv", "\t\t\t")
            out.append(f"\t\t\t{dst} = &{x}")
            out.append("\t\t}")
        else:
            x = _emit_decode(out, f.type, "fv", "\t\t")
            out.append(f"\t\t{dst} = {x}")
        out.append("\t}")
    if forward_compat:
        cond = " && ".join(f"kv.K != {f.tag}" for f in msg.wire_fields()) or "true"
        out.append("\t{")
        out.append("\t\tentries, err := c.TryMap()")
        _emit_err_check(out, "\t\t")
        out.append("\t\tfor _, kv := range entries {")
        out.append(f"\t\t\tif {cond} {{")
        out.append("\t\t\t\tv.WireResidual = append(v.WireResidual, kv)")
        out.append("\t\t\t}")
        out.append("\t\t}")
        out.append("\t}")
    out.append("\treturn v, nil")
    out.append("}")
    return out


# --- declarations ------------------------------------------------------------------------

def _emit_enum(name: str, members: dict[str, int]) -> list[str]:
    consts = _aligned([(f"{name}{_pascal(m)}", f"{name} = {v}") for m, v in members.items()])
    out = [f"type {name} int64", ""]
    out += ["const (", *consts, ")"] if consts else ["const ()"]
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
    out.append(f"func Try{name}FromCbor(c Cbor) ({name}, error) {{")
    out.append("\tv, err := c.TryInt()")
    _emit_err_check(out, "\t", result="0")
    out.append(f"\treturn Try{name}FromWire(v)")
    out.append("}")
    return out


def _emit_typed_decode(schema: Schema, msg: MessageDef) -> list[str]:
    """`msg`'s bounds, its effective values at generation time (OPT-D3), and its decode from
    bytes, which applies them: the call's one root decides them (OPT-D4)."""
    name = msg.name
    depth, length = f"{name}MaxDepth", f"{name}MaxEncodedLen"
    max_depth = cast(int, effective(schema, "max_depth", message=name))
    max_encoded_len = cast("int | None", effective(schema, "max_encoded_len", message=name))
    return [f"// {name}'s bounds: its effective max_depth and max_encoded_len (-1: none).",
            "const (",
            *_aligned([(depth, f"= {max_depth}"),
                       (length, f"= {-1 if max_encoded_len is None else max_encoded_len}")]),
            ")",
            "",
            f"// Try{name}FromBytes decodes data rooted at {name}, under its bounds.",
            f"func Try{name}FromBytes(data []byte) ({name}, error) {{",
            f"\tc, err := TryDecodeWith(data, {depth}, {length})",
            "\tif err != nil {",
            f"\t\treturn {name}{{}}, err",
            "\t}",
            f"\treturn Try{name}FromCbor(c)",
            "}"]


def _emit_message(schema: Schema, msg: MessageDef, forward_compat: bool = False) -> list[str]:
    fields = [(_pascal(f.name), _field_type(f)) for f in msg.fields]
    if forward_compat:
        fields.append(("WireResidual", "[]KV"))
    out = [f"type {msg.name} struct {{", *_aligned(fields), "}", ""]
    out += _emit_to_cbor(msg, forward_compat)
    out.append("")
    out += _emit_from_cbor(msg, forward_compat)
    out.append("")
    out += _emit_typed_decode(schema, msg)
    return out


def emit_types(schema: Schema, forward_compat: bool = False) -> str:
    out = ["// GENERATED native Go types + codec — do not edit.",
           "// Pairs with the vendored cbor.go runtime (same package).",
           "package taut"]
    if any(_sorts(f.type) for m in schema.messages.values() for f in m.wire_fields()):
        out += ["", 'import "sort"']
    for e in schema.enums.values():
        out += ["", *_emit_enum(e.name, e.members)]
    for m in schema.messages.values():
        out += ["", *_emit_message(schema, m, forward_compat)]
    return "\n".join(out) + "\n"
