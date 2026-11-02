"""The IR — flat, small, declarative. The single authored/governed artifact.

Carries enums, messages (fields: name, tag, type, optional, transient), and
nothing imperative. Type refs are a closed set: scalars, enum refs, message refs,
and lists. This is deliberately tiny enough to read whole.

The file, each message, field and enum also carry `options`: the option values
declared at that level (TautOptions.md OPT-L3). Effective values are computed by
`options.effective()`, never stored.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType

BAND_START = 1 << 20


def immutable(value):
    """Deep snapshot of portable metadata, with no mutable backing exposed."""
    from collections.abc import Mapping
    if isinstance(value, Mapping):
        return MappingProxyType({k: immutable(v) for k, v in value.items()})
    if isinstance(value, (tuple, list)):
        return tuple(immutable(v) for v in value)
    if value is None or type(value) in (str, int, float, bool, bytes):
        return value
    raise TypeError(f"unsupported metadata value {type(value).__name__}")


def wire_effective(schema, name, *, message=None):
    declared = schema.messages[message].options if message is not None else {}
    if name not in ("max_depth", "max_encoded_len"):
        raise ValueError(f"unsupported wire option {name}; regenerate/rebind runtime")
    return declared.get(name, schema.options.get(name, 32 if name == "max_depth" else None))




# --- type refs (closed set) ---------------------------------------------------

@dataclass(frozen=True)
class Scalar:
    kind: str   # 'int' | 'str' | 'bytes' | 'bool' | 'float'


@dataclass(frozen=True)
class EnumRef:
    name: str


@dataclass(frozen=True)
class MsgRef:
    name: str


@dataclass(frozen=True)
class ListOf:
    elem: "TypeRef"


@dataclass(frozen=True)
class MapOf:
    key: "TypeRef"     # scalar int | str | bool
    value: "TypeRef"   # scalar | enum | message (not list/map)


TypeRef = Scalar | EnumRef | MsgRef | ListOf | MapOf


# --- declarations -------------------------------------------------------------

@dataclass(frozen=True)
class EnumDef:
    name: str
    members: dict[str, int]   # native member name -> integer wire value
    options: dict[str, object] = field(default_factory=dict)   # declared here (OPT-L3)

    def __getattr__(self, name: str) -> "EnumMemberRef":
        if name in self.members:
            return EnumMemberRef(self.name, name)
        raise AttributeError(name)


@dataclass(frozen=True)
class EnumMemberRef:
    enum: str
    member: str


@dataclass(frozen=True)
class OneOfRule:
    enum: str
    virtual: bool = False
    exhaustive: bool = False


@dataclass(frozen=True)
class CaseRule:
    controlling_field: str
    enum: str
    member: str


# Presence, a field's `optional`: False (the default) requires the key and a non-null value; True
# requires the key and lets its value be null; MISSING_OK also reads an absent key as null. The
# encoder always writes the key. MISSING_OK is truthy, so `if f.optional` still means "may be null",
# and this string is also its IR form.
MISSING_OK = "missing_ok"


def is_presence(value: object) -> bool:
    """True for the three values a field's `optional` may take."""
    return isinstance(value, bool) or (isinstance(value, str) and value == MISSING_OK)


@dataclass(frozen=True)
class FieldDef:
    name: str
    tag: int
    type: TypeRef
    optional: bool | str = False   # False, True or MISSING_OK (above)
    transient: bool = False    # present in the native type, never on the wire
    merge: str | None = None   # CRDT merge type for this field: "lww" | "counter"
                               # (design metadata; does not affect the wire encoding)
    options: dict[str, object] = field(default_factory=dict)   # declared here (OPT-L3)
    oneof: OneOfRule | None = None
    cases: tuple[CaseRule, ...] = ()

    @property
    def virtual(self) -> bool:
        return self.oneof is not None and self.oneof.virtual


@dataclass(frozen=True)
class MessageDef:
    name: str
    fields: tuple[FieldDef, ...]
    reserved_tags: tuple[int, ...] = ()    # retired tags — never reusable
    reserved_names: tuple[str, ...] = ()   # retired field names — never reusable
    next_id: int | None = None             # declared next tag to allocate (> every used/reserved tag)
    options: dict[str, object] = field(default_factory=dict)   # declared here (OPT-L3)

    def wire_fields(self) -> tuple[FieldDef, ...]:
        return tuple(f for f in self.fields if not f.transient and not f.virtual)


# --- services (P2) ------------------------------------------------------------

@dataclass(frozen=True)
class MethodDef:
    """One endpoint = the minimal contract `(name, in, out, shape)` (D22).

    - `shape` is the **sole discriminator** (an active canonical registry name);
      `unary` is the degenerate "delivered once" shape.
    - `params` is `in` — the named inputs (the handler's kwargs), over existing
      messages/scalars; no synthetic args-messages.
    - `out` binds a type to each of the shape's delivery slots
      (`SHAPES[shape].events`). For `unary` that's the single return (slot `value`); for
      `swmr` it's `{snapshot, delta}`; etc.

    `kind`/`output`/`events` are **derived views**, not stored fields — computed
    from `shape` + `out`, they can never disagree, so the old "unary-with-a-shape"
    illegal state is unrepresentable rather than prose-policed.
    """

    name: str
    role: str                                    # out | in | ctl | td | hdl | query | dx
    shape: str                                   # sole discriminator; "unary" = once
    out: tuple[tuple[str, TypeRef], ...] = ()    # slot -> type, slots ⊆ SHAPES[shape].events
    params: tuple[tuple[str, TypeRef], ...] = () # `in`

    def streams(self) -> bool:
        return self.shape != 'unary'

    @property
    def output(self) -> TypeRef | None:
        """Derived: the single return type of a once-delivered (`unary`) method."""
        if self.streams():
            return None
        return self.out[0][1] if self.out else None

    @property
    def events(self) -> tuple[tuple[str, TypeRef], ...]:
        """Derived: the slot->type bindings of a streamed method (empty for unary)."""
        return self.out if self.streams() else ()


@dataclass(frozen=True)
class ServiceDef:
    name: str
    methods: tuple[MethodDef, ...]


@dataclass(frozen=True)
class ExtensionDef:
    """A side-channel: a message attachable to any host message at a band tag.

    Infra reads/writes it on the wire; the app's schema doesn't include it, so the
    app ignores it (and preserves it via unknown-field forwarding)."""

    message: str
    tag: int


@dataclass(frozen=True)
class Schema:
    enums: dict[str, EnumDef]
    messages: dict[str, MessageDef]
    services: dict[str, ServiceDef] = field(default_factory=dict)
    extensions: tuple[ExtensionDef, ...] = ()
    options: dict[str, object] = field(default_factory=dict)   # file level (OPT-L3)


def freeze_schema(schema):
    """Snapshot emitted codec facts. Does not load or execute authored schemas."""
    from dataclasses import replace
    enums = {k: replace(e, members=immutable(e.members), options=immutable(e.options))
             for k, e in schema.enums.items()}
    messages = {k: replace(m, fields=tuple(replace(f, options=immutable(f.options),
                                                   cases=tuple(f.cases)) for f in m.fields),
                           reserved_tags=tuple(m.reserved_tags), reserved_names=tuple(m.reserved_names),
                           options=immutable(m.options)) for k, m in schema.messages.items()}
    return replace(schema, enums=MappingProxyType(enums), messages=MappingProxyType(messages),
                   services=MappingProxyType(dict(schema.services)), options=immutable(schema.options))
