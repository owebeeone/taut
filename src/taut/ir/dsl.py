"""The Python-as-DSL surface for authoring IR — a restricted declarative subset.

No logic, no control flow: an `.taut.py` module composes these helpers into a
`SCHEMA`. A validator (later) enforces the restriction; for now the helpers are
the surface. Loaded by `load.py`.
"""

from __future__ import annotations

import keyword

from .model import (
    EnumDef,
    EnumRef,
    ExtensionDef,
    FieldDef,
    ListOf,
    MapOf,
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
FLOAT = Scalar("float")


def _validate_identifier(name: str, kind: str) -> None:
    if not isinstance(name, str):
        raise TypeError(f"{kind} name must be a string")
    if not name.isidentifier() or keyword.iskeyword(name):
        raise ValueError(f"{kind} name must be a Python identifier: {name!r}")


def _field_named(name: str, field: FieldDef) -> FieldDef:
    _validate_identifier(name, "field")
    if not isinstance(field, FieldDef):
        raise TypeError(f"field {name!r} must be declared with F(...)")
    if field.name == "":
        return FieldDef(
            name=name,
            tag=field.tag,
            type=field.type,
            optional=field.optional,
            transient=field.transient,
            merge=field.merge,
        )
    if field.name != name:
        raise TypeError(f"field name mismatch: keyword {name!r} names field {field.name!r}")
    return field


def _message_named(name: str, message: MessageDef) -> MessageDef:
    _validate_identifier(name, "declaration")
    if not isinstance(message, MessageDef):
        raise TypeError(f"declaration {name!r} must be declared with Msg(...)")
    if message.name == "":
        return MessageDef(
            name=name,
            fields=message.fields,
            reserved_tags=message.reserved_tags,
            reserved_names=message.reserved_names,
            next_id=message.next_id,
        )
    if message.name != name:
        raise TypeError(f"declaration name mismatch: keyword {name!r} names {message.name!r}")
    return message


def _enum_named(name: str, enum: EnumDef) -> EnumDef:
    _validate_identifier(name, "declaration")
    if not isinstance(enum, EnumDef):
        raise TypeError(f"declaration {name!r} must be declared with Enum(...)")
    if enum.name == "":
        return EnumDef(name=name, members=dict(enum.members))
    if enum.name != name:
        raise TypeError(f"declaration name mismatch: keyword {name!r} names {enum.name!r}")
    return enum


def _declaration_named(name: str, decl: EnumDef | MessageDef) -> EnumDef | MessageDef:
    if isinstance(decl, MessageDef):
        return _message_named(name, decl)
    if isinstance(decl, EnumDef):
        return _enum_named(name, decl)
    _validate_identifier(name, "declaration")
    raise TypeError(f"declaration {name!r} must be declared with Enum(...) or Msg(...)")


def Enum(*args, **members: int) -> EnumDef:
    if len(args) == 1 and isinstance(args[0], str):
        name = args[0]
    elif len(args) == 0:
        name = ""
    else:
        raise TypeError("Enum expects Enum(name, **members) or Enum(**members)")
    return EnumDef(name=name, members=dict(members))


class _RefFactory:
    def __call__(self, name: str) -> MsgRef:
        if not isinstance(name, str):
            raise TypeError("ref name must be a string")
        return MsgRef(name)

    def __getattr__(self, name: str) -> MsgRef:
        _validate_identifier(name, "ref")
        return self(name)


Ref = _RefFactory()


def List(elem: TypeRef) -> ListOf:
    return ListOf(elem)


def Map(key: TypeRef, value: TypeRef) -> MapOf:
    """A keyed collection. `key` is a scalar (int/str/bool); `value` is any scalar,
    enum, or message. Wire: a key-sorted array of {1: key, 2: value} entries."""
    return MapOf(key, value)


def F(
    *args,
    optional: bool = False,
    transient: bool = False,
    merge: str | None = None,
) -> FieldDef:
    if len(args) == 3 and isinstance(args[0], str):
        name, tag, type = args
    elif len(args) == 2 and isinstance(args[0], int) and not isinstance(args[0], bool):
        name = ""
        tag, type = args
    else:
        raise TypeError("F expects F(name, tag, type) or F(tag, type)")
    if not isinstance(tag, int) or isinstance(tag, bool):
        raise TypeError("field tag must be an integer")
    return FieldDef(name=name, tag=tag, type=type, optional=optional, transient=transient, merge=merge)


def Msg(*args, reserved=(), next_id: int | None = None, **named_fields) -> MessageDef:
    """A message. `reserved` mixes retired tags (int) and names (str), like
    protobuf's `reserved`; `next_id` is the next tag to allocate (validated to be
    above every used/reserved tag)."""
    if args and isinstance(args[0], str):
        name = args[0]
        fields = args[1:]
    else:
        name = ""
        fields = args
    if isinstance(named_fields.get("name"), str):
        if name:
            raise TypeError("message name provided twice")
        name = named_fields.pop("name")
    checked_fields = []
    for field in fields:
        if not isinstance(field, FieldDef):
            raise TypeError("message fields must be declared with F(...)")
        if field.name == "":
            raise TypeError("anonymous field requires a Msg(...) keyword name")
        checked_fields.append(field)
    checked_fields.extend(
        _field_named(field_name, field)
        for field_name, field in named_fields.items()
    )
    rtags = tuple(r for r in reserved if isinstance(r, int) and not isinstance(r, bool))
    rnames = tuple(r for r in reserved if isinstance(r, str))
    return MessageDef(name=name, fields=tuple(checked_fields), reserved_tags=rtags,
                      reserved_names=rnames, next_id=next_id)


def Params(**named_params: TypeRef) -> tuple[tuple[str, TypeRef], ...]:
    for name in named_params:
        _validate_identifier(name, "param")
    return tuple(named_params.items())


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
    if isinstance(tref, MapOf):
        return MapOf(_resolve(tref.key, enum_names), _resolve(tref.value, enum_names))
    return tref


def _resolve_method(m: MethodDef, enum_names: set[str]) -> MethodDef:
    return MethodDef(
        name=m.name,
        role=m.role,
        shape=m.shape,
        out=tuple((slot, _resolve(t, enum_names)) for slot, t in m.out),
        params=tuple((pn, _resolve(pt, enum_names)) for pn, pt in m.params),
    )


def schema(*decls, **named_decls) -> Schema:
    named_declarations = tuple(_declaration_named(name, decl) for name, decl in named_decls.items())
    checked_decls = []
    for decl in decls:
        if isinstance(decl, MessageDef) and decl.name == "":
            raise TypeError("anonymous message requires a schema(...) keyword name")
        if isinstance(decl, EnumDef) and decl.name == "":
            raise TypeError("anonymous enum requires a schema(...) keyword name")
        checked_decls.append(decl)
    decls = tuple(checked_decls) + named_declarations
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
