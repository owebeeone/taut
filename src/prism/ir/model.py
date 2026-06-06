"""The IR — flat, small, declarative. The single authored/governed artifact.

Carries enums, messages (fields: name, tag, type, optional, transient), and
nothing imperative. Type refs are a closed set: scalars, enum refs, message refs,
and lists. This is deliberately tiny enough to read whole.
"""

from __future__ import annotations

from dataclasses import dataclass, field


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


@dataclass(frozen=True)
class MessageDef:
    name: str
    fields: tuple[FieldDef, ...]

    def wire_fields(self) -> tuple[FieldDef, ...]:
        return tuple(f for f in self.fields if not f.transient)


# --- services (P2) ------------------------------------------------------------

@dataclass(frozen=True)
class MethodDef:
    """One endpoint. The IR unit is (source × shape × role-typed verb).

    - unary methods carry `output` (a TypeRef) and no shape.
    - server_stream methods carry a `shape` and `events` (event-name -> TypeRef),
      the per-shape derived streaming-kind; no `output`.
    `params` are the named inputs (matching the handler's kwargs), over existing
    messages/scalars — no synthetic args-messages.
    """

    name: str
    kind: str                                   # "unary" | "server_stream"
    role: str                                   # out | in | ctl | td | hdl | query | dx
    params: tuple[tuple[str, TypeRef], ...] = ()
    output: TypeRef | None = None               # unary
    shape: str | None = None                    # server_stream
    events: tuple[tuple[str, TypeRef], ...] = ()  # server_stream: event-name -> type


@dataclass(frozen=True)
class ServiceDef:
    name: str
    methods: tuple[MethodDef, ...]


@dataclass(frozen=True)
class Schema:
    enums: dict[str, EnumDef]
    messages: dict[str, MessageDef]
    services: dict[str, ServiceDef] = field(default_factory=dict)
