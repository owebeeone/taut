"""The Python-as-DSL surface for authoring IR — a restricted declarative subset.

No logic, no control flow: an `.taut.py` module composes these helpers into a
`SCHEMA`. A validator (later) enforces the restriction; for now the helpers are
the surface. Loaded by `load.py`.

Option values, as `option.max_depth(16)`, are positionals at file, message, field
and enum level (TautOptions.md OPT-L2); `option` is re-exported from `options.py`.
"""

from __future__ import annotations

import dataclasses
import keyword
from collections.abc import Iterable

from .model import (
    MISSING_OK,
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
    is_presence,
)
from .options import OptionValue, check_value
from .options import option as option   # re-exported: .taut.py modules import DSL names from here
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


def _declared_options(values: Iterable[OptionValue], where: str) -> dict[str, object]:
    """The option values declared at one level, by name (OPT-L2). The same option twice raises,
    as does a value its constructor would refuse; a wrong level is validate's (OPT-L4)."""
    declared: dict[str, object] = {}
    for value in values:
        check_value(value.name, value.value)
        if value.name in declared:
            raise TypeError(f"option {value.name!r} declared twice in {where}")
        declared[value.name] = value.value
    return declared


def _field_named(name: str, field: FieldDef) -> FieldDef:
    _validate_identifier(name, "field")
    if not isinstance(field, FieldDef):
        raise TypeError(f"field {name!r} must be declared with F(...)")
    if field.name == "":
        return dataclasses.replace(field, name=name)
    if field.name != name:
        raise TypeError(f"field name mismatch: keyword {name!r} names field {field.name!r}")
    return field


def _message_named(name: str, message: MessageDef) -> MessageDef:
    _validate_identifier(name, "declaration")
    if not isinstance(message, MessageDef):
        raise TypeError(f"declaration {name!r} must be declared with Msg(...)")
    if message.name == "":
        return dataclasses.replace(message, name=name)
    if message.name != name:
        raise TypeError(f"declaration name mismatch: keyword {name!r} names {message.name!r}")
    return message


def _enum_named(name: str, enum: EnumDef) -> EnumDef:
    _validate_identifier(name, "declaration")
    if not isinstance(enum, EnumDef):
        raise TypeError(f"declaration {name!r} must be declared with Enum(...)")
    if enum.name == "":
        return dataclasses.replace(enum, name=name, members=dict(enum.members))
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
    """An enum: `Enum(name, **members)` or `Enum(**members)`; option values follow the name
    (OPT-L2)."""
    if args and isinstance(args[0], str):
        name, option_values = args[0], args[1:]
    else:
        name, option_values = "", args
    if not all(isinstance(value, OptionValue) for value in option_values):
        raise TypeError("Enum expects Enum(name, *options, **members) or Enum(*options, **members)")
    where = f"enum {name!r}" if name else "an enum"
    return EnumDef(name=name, members=dict(members),
                   options=_declared_options(option_values, where))


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
    optional: bool | str = False,
    transient: bool = False,
    merge: str | None = None,
) -> FieldDef:
    """A field: `F(name, tag, type)` or `F(tag, type)`, then any option values (OPT-L2)."""
    end = len(args)
    while end > 0 and isinstance(args[end - 1], OptionValue):
        end -= 1
    fixed, option_values = args[:end], args[end:]
    if len(fixed) == 3 and isinstance(fixed[0], str):
        name, tag, type = fixed
    elif len(fixed) == 2 and isinstance(fixed[0], int) and not isinstance(fixed[0], bool):
        name = ""
        tag, type = fixed
    else:
        raise TypeError("F expects F(name, tag, type) or F(tag, type), then any option values")
    if not isinstance(tag, int) or isinstance(tag, bool):
        raise TypeError("field tag must be an integer")
    if not is_presence(optional):
        raise TypeError(f"optional must be False, True or MISSING_OK, not {optional!r}")
    where = f"field {name!r}" if name else f"the field with tag {tag}"
    return FieldDef(name=name, tag=tag, type=type, optional=optional, transient=transient,
                    merge=merge, options=_declared_options(option_values, where))


def Msg(*args, reserved=(), next_id: int | None = None, **named_fields) -> MessageDef:
    """A message. `reserved` mixes retired tags (int) and names (str), like
    protobuf's `reserved`; `next_id` is the next tag to allocate (validated to be
    above every used/reserved tag). Option values may sit among the positional
    fields, after the name (OPT-L2)."""
    if args and isinstance(args[0], str):
        name = args[0]
        items = args[1:]
    else:
        name = ""
        items = args
    if isinstance(named_fields.get("name"), str):
        if name:
            raise TypeError("message name provided twice")
        name = named_fields.pop("name")
    checked_fields = []
    option_values = []
    for item in items:
        if isinstance(item, OptionValue):
            option_values.append(item)
        elif not isinstance(item, FieldDef):
            raise TypeError("message fields must be declared with F(...)")
        elif item.name == "":
            raise TypeError("anonymous field requires a Msg(...) keyword name")
        else:
            checked_fields.append(item)
    checked_fields.extend(
        _field_named(field_name, field)
        for field_name, field in named_fields.items()
    )
    rtags = tuple(r for r in reserved if isinstance(r, int) and not isinstance(r, bool))
    rnames = tuple(r for r in reserved if isinstance(r, str))
    where = f"message {name!r}" if name else "a message"
    return MessageDef(name=name, fields=tuple(checked_fields), reserved_tags=rtags,
                      reserved_names=rnames, next_id=next_id,
                      options=_declared_options(option_values, where))


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
    return dataclasses.replace(
        m,
        out=tuple((slot, _resolve(t, enum_names)) for slot, t in m.out),
        params=tuple((pn, _resolve(pt, enum_names)) for pn, pt in m.params),
    )


_DECLARATIONS = (EnumDef, MessageDef, ServiceDef, ExtensionDef)


def schema(*decls, **named_decls) -> Schema:
    """A schema. Positionals are declarations or file-level option values, anything else raises
    (OPT-L2); keywords name messages and enums."""
    named_declarations = tuple(_declaration_named(name, decl) for name, decl in named_decls.items())
    checked_decls = []
    option_values = []
    for decl in decls:
        if isinstance(decl, OptionValue):
            option_values.append(decl)
        elif not isinstance(decl, _DECLARATIONS):
            raise TypeError("schema(...) takes declarations (Enum, Msg, service, extension) and "
                            f"option values, not {type(decl).__name__}")
        elif isinstance(decl, MessageDef) and decl.name == "":
            raise TypeError("anonymous message requires a schema(...) keyword name")
        elif isinstance(decl, EnumDef) and decl.name == "":
            raise TypeError("anonymous enum requires a schema(...) keyword name")
        else:
            checked_decls.append(decl)
    file_options = _declared_options(option_values, "schema(...)")
    decls = tuple(checked_decls) + named_declarations
    enums = {d.name: d for d in decls if isinstance(d, EnumDef)}
    enum_names = set(enums)
    messages = {}
    for d in decls:
        if isinstance(d, MessageDef):
            fields = tuple(
                dataclasses.replace(f, type=_resolve(f.type, enum_names)) for f in d.fields
            )
            messages[d.name] = dataclasses.replace(d, fields=fields)
    services = {}
    for d in decls:
        if isinstance(d, ServiceDef):
            methods = tuple(_resolve_method(m, enum_names) for m in d.methods)
            services[d.name] = dataclasses.replace(d, methods=methods)
    extensions = tuple(d for d in decls if isinstance(d, ExtensionDef))
    return Schema(enums=enums, messages=messages, services=services, extensions=extensions,
                  options=file_options)
