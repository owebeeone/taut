"""The Python-as-DSL surface for authoring IR — a restricted declarative subset.

No logic, no control flow: an `.prism.py` module composes these helpers into a
`SCHEMA`. A validator (later) enforces the restriction; for now the helpers are
the surface. Loaded by `load.py`.
"""

from __future__ import annotations

from .model import (
    EnumDef,
    EnumRef,
    FieldDef,
    ListOf,
    MessageDef,
    MethodDef,
    MsgRef,
    Scalar,
    Schema,
    ServiceDef,
    TypeRef,
)

# scalars
INT = Scalar("int")
STR = Scalar("str")
BYTES = Scalar("bytes")
BOOL = Scalar("bool")


def Enum(name: str, **members: int) -> EnumDef:
    return EnumDef(name=name, members=dict(members))


def Ref(name: str) -> MsgRef:
    return MsgRef(name)


def List(elem: TypeRef) -> ListOf:
    return ListOf(elem)


def F(name: str, tag: int, type: TypeRef, *, optional: bool = False, transient: bool = False,
      merge: str | None = None) -> FieldDef:
    return FieldDef(name=name, tag=tag, type=type, optional=optional, transient=transient, merge=merge)


def Msg(name: str, *fields: FieldDef, reserved=(), next_id: int | None = None) -> MessageDef:
    """A message. `reserved` mixes retired tags (int) and names (str), like
    protobuf's `reserved`; `next_id` is the next tag to allocate (validated to be
    above every used/reserved tag)."""
    rtags = tuple(r for r in reserved if isinstance(r, int) and not isinstance(r, bool))
    rnames = tuple(r for r in reserved if isinstance(r, str))
    return MessageDef(name=name, fields=tuple(fields), reserved_tags=rtags,
                      reserved_names=rnames, next_id=next_id)


def method(
    name: str,
    *,
    kind: str,
    role: str,
    params: tuple = (),
    output: TypeRef | None = None,
    shape: str | None = None,
    events: dict[str, TypeRef] | None = None,
) -> MethodDef:
    return MethodDef(
        name=name,
        kind=kind,
        role=role,
        params=tuple(params),
        output=output,
        shape=shape,
        events=tuple((events or {}).items()),
    )


def service(name: str, *methods: MethodDef) -> ServiceDef:
    return ServiceDef(name=name, methods=tuple(methods))


def _resolve(tref: TypeRef, enum_names: set[str]) -> TypeRef:
    """Author writes Ref(name) for both enums and messages; resolve enum refs."""
    if isinstance(tref, MsgRef):
        return EnumRef(tref.name) if tref.name in enum_names else tref
    if isinstance(tref, ListOf):
        return ListOf(_resolve(tref.elem, enum_names))
    return tref


def _resolve_method(m: MethodDef, enum_names: set[str]) -> MethodDef:
    return MethodDef(
        name=m.name,
        kind=m.kind,
        role=m.role,
        params=tuple((pn, _resolve(pt, enum_names)) for pn, pt in m.params),
        output=_resolve(m.output, enum_names) if m.output is not None else None,
        shape=m.shape,
        events=tuple((en, _resolve(et, enum_names)) for en, et in m.events),
    )


def schema(*decls) -> Schema:
    enums = {d.name: d for d in decls if isinstance(d, EnumDef)}
    enum_names = set(enums)
    messages = {}
    for d in decls:
        if isinstance(d, MessageDef):
            fields = tuple(
                FieldDef(f.name, f.tag, _resolve(f.type, enum_names), f.optional, f.transient, f.merge)
                for f in d.fields
            )
            messages[d.name] = MessageDef(d.name, fields, d.reserved_tags, d.reserved_names, d.next_id)
    services = {}
    for d in decls:
        if isinstance(d, ServiceDef):
            methods = tuple(_resolve_method(m, enum_names) for m in d.methods)
            services[d.name] = ServiceDef(d.name, methods)
    return Schema(enums=enums, messages=messages, services=services)
