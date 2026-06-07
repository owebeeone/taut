"""The Python-as-DSL surface for authoring IR — a restricted declarative subset.

No logic, no control flow: an `.taut.py` module composes these helpers into a
`SCHEMA`. A validator (later) enforces the restriction; for now the helpers are
the surface. Loaded by `load.py`.
"""

from __future__ import annotations

from .model import (
    EnumDef,
    EnumRef,
    ExtensionDef,
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
from .shapes import sole_slot

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
    role: str,
    shape: str = "unary",
    params: tuple = (),
    out: "TypeRef | dict[str, TypeRef] | None" = None,
) -> MethodDef:
    """An endpoint `(name, in, out, shape)`. `shape` is the sole discriminator and
    defaults to `unary` (delivered once). `out` may be a single type (bound to the
    shape's sole slot) or a `{slot: type}` map for multi-slot shapes (swmr/crdt)."""
    if out is None:
        out_items: tuple = ()
    elif isinstance(out, dict):
        out_items = tuple(out.items())
    else:  # a bare TypeRef -> bind to the shape's sole slot
        out_items = ((sole_slot(shape), out),)
    return MethodDef(name=name, role=role, shape=shape, out=out_items, params=tuple(params))


def service(name: str, *methods: MethodDef) -> ServiceDef:
    return ServiceDef(name=name, methods=tuple(methods))


def extension(message: str, *, tag: int) -> ExtensionDef:
    """Declare a side-channel: `message` rides any host message at band `tag`."""
    return ExtensionDef(message=message, tag=tag)


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
        role=m.role,
        shape=m.shape,
        out=tuple((slot, _resolve(t, enum_names)) for slot, t in m.out),
        params=tuple((pn, _resolve(pt, enum_names)) for pn, pt in m.params),
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
    extensions = tuple(d for d in decls if isinstance(d, ExtensionDef))
    return Schema(enums=enums, messages=messages, services=services, extensions=extensions)
