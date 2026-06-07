"""The IR — flat, small, declarative. The single authored/governed artifact.

Carries enums, messages (fields: name, tag, type, optional, transient), and
nothing imperative. Type refs are a closed set: scalars, enum refs, message refs,
and lists. This is deliberately tiny enough to read whole.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .shapes import is_streaming


# --- type refs (closed set) ---------------------------------------------------

@dataclass(frozen=True)
class Scalar:
    kind: str   # 'int' | 'str' | 'bytes' | 'bool'


@dataclass(frozen=True)
class EnumRef:
    name: str


@dataclass(frozen=True)
class MsgRef:
    name: str


@dataclass(frozen=True)
class ListOf:
    elem: "TypeRef"


TypeRef = Scalar | EnumRef | MsgRef | ListOf


# --- declarations -------------------------------------------------------------

@dataclass(frozen=True)
class EnumDef:
    name: str
    members: dict[str, int]   # native member name -> integer wire value


@dataclass(frozen=True)
class FieldDef:
    name: str
    tag: int
    type: TypeRef
    optional: bool = False
    transient: bool = False    # present in the native type, never on the wire
    merge: str | None = None   # CRDT merge type for this field: "lww" | "counter"
                               # (design metadata; does not affect the wire encoding)


@dataclass(frozen=True)
class MessageDef:
    name: str
    fields: tuple[FieldDef, ...]
    reserved_tags: tuple[int, ...] = ()    # retired tags — never reusable
    reserved_names: tuple[str, ...] = ()   # retired field names — never reusable
    next_id: int | None = None             # declared next tag to allocate (> every used/reserved tag)

    def wire_fields(self) -> tuple[FieldDef, ...]:
        return tuple(f for f in self.fields if not f.transient)


# --- services (P2) ------------------------------------------------------------

@dataclass(frozen=True)
class MethodDef:
    """One endpoint = the minimal contract `(name, in, out, shape)` (D22).

    - `shape` is the **sole discriminator** (a name in the open shape registry);
      `unary` is the degenerate "delivered once" shape.
    - `params` is `in` — the named inputs (the handler's kwargs), over existing
      messages/scalars; no synthetic args-messages.
    - `out` binds a type to each of the shape's delivery slots (`SHAPES[shape]
      ["events"]`). For `unary` that's the single return (slot `value`); for
      `swmr` it's `{snapshot, delta}`; etc.

    `kind`/`output`/`events` are **derived views**, not stored fields — computed
    from `shape` + `out`, they can never disagree, so the old "unary-with-a-shape"
    illegal state is unrepresentable rather than prose-policed.
    """

    name: str
    role: str                                    # out | in | ctl | td | hdl | query | dx
    shape: str                                   # sole discriminator; "unary" = once
    out: tuple[tuple[str, TypeRef], ...] = ()    # slot -> type, slots ⊆ SHAPES[shape]["events"]
    params: tuple[tuple[str, TypeRef], ...] = () # `in`

    def streams(self) -> bool:
        return is_streaming(self.shape)

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
