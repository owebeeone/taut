"""Immutable schema metadata and generated, typed attribute bindings.

References use stable registry keys, so recursive schemas never expand a tree.
Only ``publish`` attaches metadata, after checking the entire graph.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from types import MappingProxyType
from typing import Mapping

from .contracts import ConfigurationError, DESCRIPTOR_CONTRACT, require_contract
from .facts import (Scalar, EnumRef, MsgRef, ListOf, MapOf, immutable, wire_effective,
                    freeze_schema)
from .rules import ONEOF_RULE, check_rules


@dataclass(frozen=True, slots=True)
class TypeDescriptor:
    kind: str
    reference: str | None = None
    element: TypeDescriptor | None = None
    key: TypeDescriptor | None = None
    value: TypeDescriptor | None = None

    def __post_init__(self):
        expected = {"int": (), "str": (), "bool": (), "bytes": (), "float": (),
                    "message": ("reference",), "enum": ("reference",),
                    "list": ("element",), "map": ("key", "value")}
        actual = tuple(k for k in ("reference", "element", "key", "value") if getattr(self, k) is not None)
        if self.kind not in expected or actual != expected[self.kind]:
            raise ConfigurationError(f"invalid TypeDescriptor {self.kind}: {actual}")


@dataclass(frozen=True, slots=True)
class FieldDescriptor:
    name: str
    attribute: str | None
    number: int
    type: TypeDescriptor
    presence: str
    transient: bool = False
    virtual: bool = False
    options: Mapping = field(default_factory=dict)

    def __post_init__(self):
        object.__setattr__(self, "options", immutable(self.options))


@dataclass(frozen=True, slots=True)
class EnumDescriptor:
    name: str
    qualified_name: str
    members: Mapping
    options: Mapping = field(default_factory=dict)
    member_options: Mapping = field(default_factory=dict)

    def __post_init__(self):
        for k in ("members", "options", "member_options"):
            object.__setattr__(self, k, immutable(getattr(self, k)))


@dataclass(frozen=True, slots=True)
class OneOfDescriptor:
    controlling_field: str
    enum: EnumDescriptor
    virtual: bool
    exhaustive: bool
    members: Mapping

    def __post_init__(self):
        object.__setattr__(self, "members", immutable(self.members))


@dataclass(frozen=True, slots=True)
class ConstraintDescriptor:
    rule: str
    parameters: Mapping = field(default_factory=dict)

    def __post_init__(self):
        object.__setattr__(self, "parameters", immutable(self.parameters))


@dataclass(frozen=True, slots=True)
class MessageDescriptor:
    name: str
    qualified_name: str
    descriptor_contract_version: int
    fields: tuple[FieldDescriptor, ...]
    oneofs: tuple[OneOfDescriptor, ...] = ()
    constraints: tuple[ConstraintDescriptor, ...] = ()
    reserved_numbers: tuple[int, ...] = ()
    reserved_names: tuple[str, ...] = ()
    next_id: int | None = None
    options: Mapping = field(default_factory=dict)
    effective_options: Mapping = field(default_factory=dict)
    fields_by_name: Mapping = field(init=False, repr=False, compare=False)
    groups_by_field: Mapping = field(init=False, repr=False, compare=False)

    def __post_init__(self):
        for k in ("fields", "oneofs", "constraints", "reserved_numbers", "reserved_names"):
            object.__setattr__(self, k, tuple(getattr(self, k)))
        for k in ("options", "effective_options"):
            object.__setattr__(self, k, immutable(getattr(self, k)))
        object.__setattr__(self, "fields_by_name", MappingProxyType({f.name: f for f in self.fields}))
        object.__setattr__(self, "groups_by_field", MappingProxyType({g.controlling_field: g for g in self.oneofs}))


@dataclass(frozen=True, slots=True)
class SchemaDescriptor:
    descriptor_contract_version: int
    ir_version: int
    identity: str
    messages: Mapping
    enums: Mapping
    options: Mapping = field(default_factory=dict)
    effective_options: Mapping = field(default_factory=dict)

    def __post_init__(self):
        for k in ("messages", "enums"):
            object.__setattr__(self, k, MappingProxyType(dict(getattr(self, k))))
        for k in ("options", "effective_options"):
            object.__setattr__(self, k, immutable(getattr(self, k)))


@dataclass(frozen=True, slots=True)
class SchemaBinding:
    schema: SchemaDescriptor
    message_classes: Mapping
    enum_classes: Mapping
    external_bindings: Mapping = field(default_factory=dict)

    def __post_init__(self):
        from .records import has_record_field
        for k in ("message_classes", "enum_classes", "external_bindings"):
            object.__setattr__(self, k, MappingProxyType(dict(getattr(self, k))))
        require_contract(artifact=self.schema.identity, descriptor=self.schema.descriptor_contract_version)
        if type(self.schema.ir_version) is not int or self.schema.ir_version not in (1, 2, 3):
            raise ConfigurationError(f"{self.schema.identity}: unsupported IR version {self.schema.ir_version}")
        if set(self.message_classes) != set(self.schema.messages) or set(self.enum_classes) != set(self.schema.enums):
            raise ConfigurationError(f"{self.schema.identity}: incomplete typed bindings; regenerate")
        for name, desc in self.schema.messages.items():
            require_contract(artifact=desc.qualified_name, descriptor=desc.descriptor_contract_version)
            cls = self.message_classes[name]
            if not isinstance(cls, type):
                raise ConfigurationError(f"{name}: message binding must be a generated class")
            for f in desc.fields:
                if (f.attribute is not None and f.attribute not in getattr(cls, "__slots__", ())
                        and not has_record_field(cls, f.attribute)):
                    raise ConfigurationError(f"{name}.{f.name}: missing generated slot {f.attribute}")
                if (f.presence not in ("required", "nullable", "missing_ok")
                        or type(f.number) is not int or f.number <= 0
                        or type(f.virtual) is not bool or type(f.transient) is not bool
                        or (f.virtual != (f.attribute is None))):
                    raise ConfigurationError(f"{name}.{f.name}: invalid field descriptor configuration")
                self._check_type(f.type)
            if len(desc.fields_by_name) != len(desc.fields) or len({f.number for f in desc.fields}) != len(desc.fields):
                raise ConfigurationError(f"{name}: duplicate field name/number")
            if list(desc.fields) != sorted(desc.fields, key=lambda f: f.number):
                raise ConfigurationError(f"{name}: fields must be in field-number order")
            payload_owners = set()
            if len(desc.groups_by_field) != len(desc.oneofs):
                raise ConfigurationError(f"{name}: duplicate oneof controller")
            for g in desc.oneofs:
                ctrl = desc.fields_by_name.get(g.controlling_field)
                if (ctrl is None or ctrl.type.kind != "enum" or
                        self.schema.enums.get(ctrl.type.reference) is not g.enum or
                        type(g.virtual) is not bool or type(g.exhaustive) is not bool or
                        ctrl.virtual != g.virtual or ctrl.presence != "required" or
                        set(g.members) != set(g.enum.members)):
                    raise ConfigurationError(f"{name}: invalid oneof descriptor links/configuration")
                if g.exhaustive and None in g.members.values():
                    raise ConfigurationError(f"{name}: exhaustive oneof contains payload-free choice")
                for payload in set(g.members.values()) - {None}:
                    if payload not in desc.fields_by_name or payload in payload_owners:
                        raise ConfigurationError(f"{name}: invalid/shared oneof payload {payload}")
                    payload_owners.add(payload)
                    if desc.fields_by_name[payload].presence == "required":
                        raise ConfigurationError(f"{name}.{payload}: oneof payload must be nullable")
            constraint_controls = set()
            for c in desc.constraints:
                if not isinstance(c, ConstraintDescriptor):
                    raise ConfigurationError(f"{name}: invalid constraint descriptor record")
                if c.rule != ONEOF_RULE:
                    raise ConfigurationError(f"{name}: unsupported constraint {c.rule}; regenerate/rebind runtime")
                if set(c.parameters) != {"controlling_field"} or type(c.parameters.get("controlling_field")) is not str:
                    raise ConfigurationError(f"{name}: unsupported oneof constraint parameters {dict(c.parameters)}")
                control = c.parameters["controlling_field"]
                if control not in desc.groups_by_field or control in constraint_controls:
                    raise ConfigurationError(f"{name}: dangling/duplicate oneof constraint controller {control}")
                constraint_controls.add(control)
            if constraint_controls != set(desc.groups_by_field):
                raise ConfigurationError(f"{name}: oneof groups and constraint declarations differ")
        for name, cls in self.enum_classes.items():
            if not isinstance(cls, type) or not issubclass(cls, Enum):
                raise ConfigurationError(f"{name}: enum binding must be the generated enum")
            if {k: v.value for k, v in cls.__members__.items()} != dict(self.schema.enums[name].members):
                raise ConfigurationError(f"{name}: enum binding differs from descriptor")
        for name, other in self.external_bindings.items():
            if (not isinstance(other, SchemaBinding) or name not in other.schema.messages
                    or other.schema.messages[name] is not self.schema.messages.get(name)
                    or other.message_classes[name] is not self.message_classes.get(name)):
                raise ConfigurationError(f"{name}: incompatible external descriptor/binding owner")

    def _check_type(self, t):
        if not isinstance(t, TypeDescriptor):
            raise ConfigurationError("typed descriptor link must be a TypeDescriptor")
        if t.kind == "map" and (not isinstance(t.key, TypeDescriptor) or t.key.kind not in ("int", "str", "bool")):
            raise ConfigurationError("map descriptor requires an int/str/bool key")
        if t.kind == "message" and t.reference not in self.schema.messages:
            raise ConfigurationError(f"dangling/wrong-category message link {t.reference}")
        if t.kind == "enum" and t.reference not in self.schema.enums:
            raise ConfigurationError(f"dangling/wrong-category enum link {t.reference}")
        for child in (t.element, t.key, t.value):
            if child is not None:
                self._check_type(child)

    def message_binding(self, name):
        return self.external_bindings.get(name, self)

    def check_pair(self, value, descriptor):
        if (not isinstance(descriptor, MessageDescriptor)
                or self.schema.messages.get(descriptor.name) is not descriptor):
            raise ConfigurationError("mismatched descriptor/binding; use the generated shared owner")
        if type(value) is not self.message_classes[descriptor.name]:
            raise ConfigurationError(f"{descriptor.name}: root does not match its typed binding")


def _type(t):
    if isinstance(t, Scalar):
        return TypeDescriptor(t.kind)
    if isinstance(t, (EnumRef, MsgRef)):
        return TypeDescriptor("enum" if isinstance(t, EnumRef) else "message", t.name)
    if isinstance(t, ListOf):
        return TypeDescriptor("list", element=_type(t.elem))
    if isinstance(t, MapOf):
        return TypeDescriptor("map", key=_type(t.key), value=_type(t.value))
    raise ConfigurationError(f"unsupported schema type {t}")


def publish(schema, message_classes, enum_classes, *, identity, ir_version=2, external=(), attributes=None):
    """Publish static facts, never create live message instances or reflect fields."""
    errors = check_rules(schema)
    if errors:
        raise ConfigurationError("; ".join(errors))
    schema = freeze_schema(schema)
    external = frozenset(external)
    enums = {n: EnumDescriptor(n, f"{identity}.{n}", e.members, e.options,
                              {m: {} for m in e.members}) for n, e in schema.enums.items()}
    messages = {}
    external_bindings = {}
    for name in external:
        cls = message_classes.get(name, enum_classes.get(name))
        desc = getattr(cls, "DESCRIPTOR", None)
        binding = getattr(cls, "__taut_binding__", None)
        if not isinstance(binding, SchemaBinding):
            raise ConfigurationError(f"{name}: missing compatible descriptor/binding (or split runtime owner); regenerate/rebind child")
        if name in message_classes:
            if not isinstance(desc, MessageDescriptor):
                raise ConfigurationError(f"{name}: missing shared MessageDescriptor; regenerate/rebind child")
            messages[name] = desc
            external_bindings[name] = binding
        else:
            if not isinstance(desc, EnumDescriptor):
                raise ConfigurationError(f"{name}: missing shared EnumDescriptor; regenerate/rebind child")
            expected = enums[name]
            if (desc.members, desc.options, desc.member_options) != (expected.members, expected.options, expected.member_options):
                raise ConfigurationError(f"{name}: external enum differs from dependency schema; regenerate/rebind")
            enums[name] = desc
    for name, msg in schema.messages.items():
        attrs = (attributes or {}).get(name, {})
        if set(attrs) - {f.name for f in msg.fields if not f.virtual}:
            raise ConfigurationError(f"{name}: attribute binding names unknown or virtual field")
        fields = tuple(FieldDescriptor(f.name, None if f.virtual else attrs.get(f.name, f.name), f.tag, _type(f.type),
                                       "required" if f.optional is False else
                                       "nullable" if f.optional is True else "missing_ok",
                                       f.transient, f.virtual, f.options)
                       for f in sorted(msg.fields, key=lambda f: f.tag))
        groups = []
        for f in sorted(msg.fields, key=lambda f: f.tag):
            if f.oneof:
                members = {m: None for m in enums[f.oneof.enum].members}
                for payload in msg.fields:
                    for case in payload.cases:
                        if case.controlling_field == f.name:
                            members[case.member] = payload.name
                groups.append(OneOfDescriptor(f.name, enums[f.oneof.enum], f.oneof.virtual,
                                              f.oneof.exhaustive, members))
        desc = MessageDescriptor(name, f"{identity}.{name}", DESCRIPTOR_CONTRACT, fields,
                                 tuple(groups), tuple(ConstraintDescriptor(ONEOF_RULE,
                                 {"controlling_field": g.controlling_field}) for g in groups),
                                 msg.reserved_tags, msg.reserved_names, msg.next_id, msg.options,
                                 {k: wire_effective(schema, k, message=name)
                                  for k in ("max_depth", "max_encoded_len")})
        if name in external:
            old = messages[name]
            # Identity differs across generation units; the portable field/rule facts must agree.
            if (old.fields, old.reserved_numbers, old.reserved_names, old.next_id,
                old.options, old.effective_options) != (desc.fields, desc.reserved_numbers,
                desc.reserved_names, desc.next_id, desc.options, desc.effective_options) or tuple(
                    (g.controlling_field, g.enum.members, g.virtual, g.exhaustive, g.members) for g in old.oneofs
                ) != tuple((g.controlling_field, g.enum.members, g.virtual, g.exhaustive, g.members) for g in desc.oneofs):
                raise ConfigurationError(f"{name}: external descriptor differs from dependency schema; regenerate/rebind")
        else:
            messages[name] = desc
    registry = SchemaDescriptor(DESCRIPTOR_CONTRACT, ir_version, identity, messages, enums,
                                schema.options, {k: wire_effective(schema, k)
                                for k in ("max_depth", "max_encoded_len")})
    binding = SchemaBinding(registry, message_classes, enum_classes, external_bindings)
    # All checks complete before attaching any public descriptors.
    for name, cls in {**message_classes, **enum_classes}.items():
        if name not in external:
            cls.DESCRIPTOR = messages[name] if name in messages else enums[name]
            cls.__taut_binding__ = binding
    return registry, binding
