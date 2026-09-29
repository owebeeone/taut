"""Options: typed properties declared with a taut schema, as in protobuf (D27, TautOptions.md).

One definition per option (OPT-D1) in the registry `OPTIONS`. The `option` namespace reaches each
option's typed constructor, which builds a declared `OptionValue` (OPT-L1). The model stores what
each level declared (OPT-L3); `effective()` computes the value an element sees (OPT-D3).
Imports only `model.py`.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from .model import EnumRef, ListOf, MapOf, MessageDef, MsgRef, Scalar, Schema, TypeRef

# Where an option may be declared: file, message, field and enum; enum_value, service and method
# are reserved, so that their first option needs no new IR version (OPT-I2).
LEVELS = ("file", "message", "field", "enum", "enum_value", "service", "method")

# What an option's value changes (OPT-D1, OPT-D2): what decodes (wire), the generated code only
# (codegen), nothing (metadata), or what readers compute from the same bytes (semantic, question 7).
CLASSES = ("wire", "codegen", "metadata", "semantic")

DEFAULT_MAX_DEPTH = 32               # max_depth where no level declares one (OPT-D5)
MAX_DEPTH_CEILING = 128              # a runtime constant, not an option (OPT-D5)
MAX_ENCODED_LEN_CEILING = 2**31 - 1  # on declared values, not the runtimes' inputs (OPT-D6)


@dataclass(frozen=True)
class OptionDef:
    """One option's definition (OPT-D1)."""

    name: str                   # "max_depth"; custom options, later, "ns.name"
    value_type: type            # int, bool or str
    levels: frozenset[str]      # where it may be declared, among LEVELS
    default: object             # the effective value where no level declares one (None: no value)
    klass: str                  # one of CLASSES
    inherits: tuple[str, ...]   # levels consulted, most specific first; () for none
    targets: frozenset[str] | None = None   # codegen: the generators it concerns; None for all


@dataclass(frozen=True)
class OptionValue:
    """A declared option, built by its typed constructor: `option.max_depth(16)` (OPT-D1)."""

    name: str
    value: object


OPTIONS: dict[str, OptionDef] = {
    "max_depth": OptionDef("max_depth", int, frozenset({"file", "message"}),
                           default=DEFAULT_MAX_DEPTH, klass="wire", inherits=("message", "file")),
    "max_encoded_len": OptionDef("max_encoded_len", int, frozenset({"file", "message"}),
                                 default=None, klass="wire", inherits=("message", "file")),
}

# The inclusive range of an int option's declared values (OPT-D5, OPT-D6).
_RANGES: dict[str, tuple[int, int]] = {
    "max_depth": (1, MAX_DEPTH_CEILING),
    "max_encoded_len": (1, MAX_ENCODED_LEN_CEILING),
}


def _unknown(name: str) -> str:
    return f"unknown option {name!r}; known options: {', '.join(OPTIONS)}"


def _definition(name: str) -> OptionDef:
    defn = OPTIONS.get(name)
    if defn is None:
        raise KeyError(_unknown(name))
    return defn


def check_value(name: str, value: object) -> None:
    """Refuse a value that option `name` cannot take (OPT-D5, OPT-D6): another type, a bool where an
    int is due, or a value out of range. Each typed constructor runs it; so may any later check of
    values that no constructor built. An unregistered name raises `KeyError`."""
    defn = _definition(name)
    if not isinstance(value, defn.value_type) or (
        isinstance(value, bool) and defn.value_type is not bool
    ):
        raise TypeError(f"option {name} takes {defn.value_type.__name__} values, not {value!r}")
    bounds = _RANGES.get(name)
    if bounds is not None and not (isinstance(value, int) and bounds[0] <= value <= bounds[1]):
        low, high = bounds
        raise ValueError(f"option {name} takes a value from {low} to {high}, not {value!r}")


def _constructor(defn: OptionDef) -> Callable[[object], OptionValue]:
    def construct(value: object, /) -> OptionValue:
        check_value(defn.name, value)
        return OptionValue(defn.name, value)

    construct.__name__ = defn.name
    construct.__qualname__ = f"option.{defn.name}"
    return construct


class _OptionNamespace:
    """`option.<name>(value)`: each registered option's typed constructor, after `Ref`'s pattern
    (OPT-L1). An unknown name fails at import; calling `option(...)` itself is reserved for custom
    options (question 6)."""

    def __call__(self, *args: object, **kwargs: object) -> OptionValue:
        raise TypeError('custom options are reserved: option("ns.name", value) is not available; '
                        f"use option.<name>(value), one of: {', '.join(OPTIONS)}")

    def __getattr__(self, name: str) -> Callable[[object], OptionValue]:
        defn = OPTIONS.get(name)
        if defn is None:
            raise AttributeError(_unknown(name))
        return _constructor(defn)


option = _OptionNamespace()


def _enclosing(schema: Schema, message: str | None) -> dict[str, dict[str, object]]:
    """The declarations at each level that lexically encloses the element, its own included: a
    message sits in its file only (OPT-D3)."""
    if message is None:
        return {"file": schema.options}
    msg = schema.messages.get(message)
    if msg is None:
        raise KeyError(f"unknown message {message!r}")
    return {"message": msg.options, "file": schema.options}


def _resolve(defn: OptionDef, declared: dict[str, dict[str, object]]) -> object:
    for level in defn.inherits:
        values = declared.get(level, {})
        if defn.name in values:
            return values[defn.name]
    return defn.default


def effective(schema: Schema, name: str, *, message: str | None = None) -> object:
    """Option `name`'s effective value at `message`, or at file level for None (OPT-D3): the value
    declared at the first level of its `inherits` that declares one, walking out from the element,
    else its default. Enclosure is lexical: a message used by another inherits nothing from it.
    An unregistered option or an unknown message raises `KeyError`."""
    return _resolve(_definition(name), _enclosing(schema, message))


def effective_map(schema: Schema, *, message: str | None = None) -> dict[str, object]:
    """Every wire and codegen option defined for the level, message or (for None) file, resolved,
    defaults included (OPT-I2), in registry order."""
    declared = _enclosing(schema, message)
    level = "file" if message is None else "message"
    return {
        name: _resolve(defn, declared)
        for name, defn in OPTIONS.items()
        if defn.klass in ("wire", "codegen") and level in defn.levels
    }


# --- roots and the two floors (OPT-D4, OPT-D5, OPT-D6) ------------------------------------------

def roots(schema: Schema) -> list[tuple[str, TypeRef]]:
    """Every type a decode call may be rooted at (OPT-D4, OPT-D5), each once, with a label: every
    message, by its name, then each type a method binds as a param or out slot that is not listed
    yet, labelled as `validate` labels the slot (`Svc.method param p`, `Svc.method out[slot]`). A
    slot typed as a message is that message's root."""
    found: list[tuple[str, TypeRef]] = [(name, MsgRef(name)) for name in schema.messages]
    for svc in schema.services.values():
        for meth in svc.methods:
            ctx = f"{svc.name}.{meth.name}"
            slots = [(f"{ctx} param {pn}", pt) for pn, pt in meth.params]
            slots += [(f"{ctx} out[{slot}]", t) for slot, t in meth.out]
            for label, tref in slots:
                if all(tref != seen for _, seen in found):
                    found.append((label, tref))
    return found


def root_effective(schema: Schema, name: str, root: TypeRef) -> object:
    """Option `name`'s effective value for a decode call rooted at `root` (OPT-D4): a message's
    own, as `effective` resolves it; for a root that is not a message, such as an RPC slot typed
    `list<Tree>`, the file's, else the default."""
    if isinstance(root, MsgRef):
        return effective(schema, name, message=root.name)
    return effective(schema, name)


def _message(schema: Schema, name: str) -> MessageDef:
    msg = schema.messages.get(name)
    if msg is None:
        raise KeyError(f"unknown message {name!r}")
    return msg


def nesting(schema: Schema, root: TypeRef) -> int:
    """The root's non-recursive nesting, the floor of its `max_depth` (OPT-D5): the deepest a value
    reaches, counted in arrays and maps as decode counts depth (a top-level container is 1),
    without a message repeating on the path. 0 for a scalar or enum; 1 + T's for `list<T>`;
    2 + V's for `map<K,V>`, whose wire is an array of `{1: key, 2: value}` maps; for a message,
    1 + the largest among its wire fields and the schema's extensions, which may ride any message,
    extension messages included; a message already on the path counts 0. So `Tree { kids:
    list<Tree> }` needs 2. An unknown message raises `KeyError`."""
    riders = tuple(MsgRef(ext.message) for ext in schema.extensions)
    reach: dict[str, frozenset[str]] = {}
    memo: dict[tuple[str, frozenset[str]], int] = {}

    def inside(name: str) -> tuple[TypeRef, ...]:
        return tuple(f.type for f in _message(schema, name).wire_fields()) + riders

    def reachable(name: str) -> frozenset[str]:
        """The messages a value of message `name` may hold, at any depth."""
        if name not in reach:
            found: set[str] = set()
            pending = list(inside(name))
            while pending:
                tref = pending.pop()
                if isinstance(tref, ListOf):
                    pending.append(tref.elem)
                elif isinstance(tref, MapOf):
                    pending.append(tref.value)
                elif isinstance(tref, MsgRef) and tref.name not in found:
                    found.add(tref.name)
                    pending.extend(inside(tref.name))
            reach[name] = frozenset(found)
        return reach[name]

    def depth(tref: TypeRef, path: frozenset[str]) -> int:
        if isinstance(tref, (Scalar, EnumRef)):
            return 0
        if isinstance(tref, ListOf):
            return 1 + depth(tref.elem, path)
        if isinstance(tref, MapOf):
            return 2 + depth(tref.value, path)
        if isinstance(tref, MsgRef):
            if tref.name in path:
                return 0
            # Only the messages on the path that this one can reach change its depth, so the
            # memo is keyed by those: without recursion, by the message alone.
            key = (tref.name, path & reachable(tref.name))
            if key not in memo:
                inner = path | {tref.name}
                memo[key] = 1 + max((depth(t, inner) for t in inside(tref.name)), default=0)
            return memo[key]
        raise TypeError(f"unknown type ref {tref!r}")

    return depth(root, frozenset())


# A scalar's shortest canonical encoding: 0, "", b"" and false take one byte; a float's
# shortest form is a half, f9 and two bytes.
_SHORTEST_SCALAR = {"int": 1, "str": 1, "bytes": 1, "bool": 1, "float": 3}


def _head_length(n: int) -> int:
    """The bytes of a canonical CBOR head (initial byte and shortest argument) for n >= 0."""
    if n < 24:
        return 1
    if n < 0x100:
        return 2
    if n < 0x10000:
        return 3
    if n < 0x100000000:
        return 5
    return 9


def _int_length(value: int) -> int:
    return _head_length(value if value >= 0 else -1 - value)


def smallest_encoding(schema: Schema, root: TypeRef) -> int | None:
    """The length in bytes of the root's smallest canonical encoding, the floor of a declared
    `max_encoded_len` (OPT-D6): every field at its shortest canonical value, which is zero (for a
    float, a 3-byte half), an empty string, byte string, list or map, an enum's member with the
    shortest encoding, or null for an optional field, whose key the encoder writes all the same,
    `MISSING_OK` included. Extensions and unknown fields are never required, so they add nothing.

    None when no value has a finite encoding: a required field whose type recurses without end,
    as in `Loop { next: Loop }` or a cycle of such fields, or an enum without members. An unknown
    message, enum or scalar kind raises `KeyError`."""
    memo: dict[str, int | None] = {}
    path: set[str] = set()

    def length(tref: TypeRef) -> int | None:
        if isinstance(tref, Scalar):
            if tref.kind not in _SHORTEST_SCALAR:
                raise KeyError(f"unknown scalar kind {tref.kind!r}")
            return _SHORTEST_SCALAR[tref.kind]
        if isinstance(tref, EnumRef):
            enum = schema.enums.get(tref.name)
            if enum is None:
                raise KeyError(f"unknown enum {tref.name!r}")
            return min((_int_length(v) for v in enum.members.values()), default=None)
        if isinstance(tref, (ListOf, MapOf)):
            return 1   # the empty array
        if isinstance(tref, MsgRef):
            if tref.name in path:
                return None   # a required field recursing without end: no finite value
            if tref.name not in memo:
                path.add(tref.name)
                memo[tref.name] = message_length(_message(schema, tref.name))
                path.discard(tref.name)
            return memo[tref.name]
        raise TypeError(f"unknown type ref {tref!r}")

    def message_length(msg: MessageDef) -> int | None:
        fields = msg.wire_fields()
        total = _head_length(len(fields))
        for f in fields:
            value = 1 if f.optional else length(f.type)   # an optional field's null is one byte
            if value is None:
                return None
            total += _head_length(f.tag) + value
        return total

    return length(root)
