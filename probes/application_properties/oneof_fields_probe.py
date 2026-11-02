"""Explicit OneOf(enum) discriminator + field-local Case syntax experiment.

This is not the production DSL. Normalize into the existing isolated constraint
IR before code generation/transport; raw standard IR export cannot retain these
new source markers until native Taut IR support is implemented.
"""

from dataclasses import dataclass, fields, replace
import re
import sys

# A schema imports this module by name even when the generator is invoked as a
# script. Keep one class identity for enum-member/case objects in both paths.
if __name__ == "__main__":
    sys.modules.setdefault("oneof_fields_probe", sys.modules[__name__])

from taut.ir.model import EnumDef, EnumRef, FieldDef, MessageDef
from taut.ir.dsl import Enum as _Enum
from taut_app_probe import AnnotatedField, AnnotatedMessage, F as _F, Msg as _Msg, annotate, app, properties
from graph_contract_probe import Contract

NAMESPACE = "taut.oneof.probe"


@dataclass(frozen=True)
class EnumMember:
    enum: EnumDef
    name: str

    @property
    def value(self):
        return self.enum.members[self.name]


@dataclass(frozen=True)
class EnumObject(EnumDef):
    def __getattr__(self, member):
        if member.startswith("_") or member not in self.members:
            raise AttributeError(f"Unknown enum member {member!r}")
        if not self.name:
            raise ValueError("Name the enum before creating member references")
        return EnumMember(self, member)


def Enum(*args, **members):
    definition = _Enum(*args, **members)
    collisions = set(definition.members) & (set(EnumDef.__annotations__) | set(dir(EnumObject)))
    if collisions:
        raise ValueError(f"Enum members collide with definition attributes: {sorted(collisions)}")
    return EnumObject(definition.name, dict(definition.members), dict(definition.options))


@dataclass(frozen=True)
class OneOf:
    enum: object
    virtual: bool = False
    exhaustive: bool = False

    def __post_init__(self):
        if type(self.virtual) is not bool:
            raise TypeError("OneOf virtual must be True or False")
        if type(self.exhaustive) is not bool:
            raise TypeError("OneOf exhaustive must be True or False")


@dataclass(frozen=True, init=False)
class Case:
    tag: str
    member: object

    def __init__(self, *args, **nomination):
        if nomination:
            if args or len(nomination) != 1:
                raise TypeError("Case needs exactly one controlling-field nomination")
            tag, member = next(iter(nomination.items()))
            if not isinstance(member, EnumMember):
                raise TypeError("Keyword Case requires a qualified enum-member reference")
        elif len(args) == 2:
            # Keep the earlier probe spelling only as a comparison input.
            tag, member = args
        else:
            raise TypeError("Use Case(field=Enum.member)")
        object.__setattr__(self, "tag", tag)
        object.__setattr__(self, "member", member)


@dataclass(frozen=True)
class CaseField(AnnotatedField):
    oneof: bool = False
    virtual: bool = False
    exhaustive: bool = False
    cases: tuple[Case, ...] = ()


def F(*args, **kwargs):
    cases = tuple(arg for arg in args if isinstance(arg, Case))
    arguments = [arg for arg in args if not isinstance(arg, Case)]
    markers = [index for index, arg in enumerate(arguments) if isinstance(arg, OneOf)]
    if len(markers) > 1 or (markers and cases):
        raise ValueError("A field cannot be both discriminator and payload")
    virtual = False
    exhaustive = False
    if markers:
        virtual = arguments[markers[0]].virtual
        exhaustive = arguments[markers[0]].exhaustive
        expected = 2 if arguments and isinstance(arguments[0], str) else 1
        if markers[0] != expected:
            raise ValueError("OneOf must wrap the field's type")
        target = arguments[markers[0]].enum
        if isinstance(target, EnumDef):
            if not target.name:
                raise ValueError("Name the enum before using it in OneOf")
            target = EnumRef(target.name)
        arguments[markers[0]] = target
        if kwargs.get("optional", False):
            raise ValueError("OneOf discriminator must be non-nullable")
    if cases:
        if "optional" in kwargs and kwargs["optional"] is False:
            raise ValueError("Case payload storage must be nullable")
        kwargs.setdefault("optional", True)
    definition = _F(*arguments, **kwargs)
    if not markers and not cases:
        return definition
    values = {item.name: getattr(definition, item.name) for item in fields(FieldDef)}
    return CaseField(**values, app_properties=getattr(definition, "app_properties", ()), oneof=bool(markers), virtual=virtual, exhaustive=exhaustive, cases=cases)


def Msg(*args, **kwargs):
    if any(isinstance(arg, Case) for arg in args):
        raise ValueError("Case belongs on a payload field; standalone cases are not supported")
    return _Msg(*args, **kwargs)


def _plain_field(field):
    values = {item.name: getattr(field, item.name) for item in fields(FieldDef)}
    metadata = getattr(field, "app_properties", ())
    if metadata:
        return AnnotatedField(**values, app_properties=metadata)
    return FieldDef(**values)


def normalize_oneofs(schema):
    """Normalize source markers to the earlier probe's explicit union contract.

    This internal reuse does not propose application annotations as the production
    representation of Taut-native oneof. It lets us compare the authoring forms
    against already compiled validators without changing the production compiler.
    """
    messages = {}
    for record in schema.messages.values():
        by_name = {field.name: field for field in record.fields}
        discriminators = {field.name: field for field in record.fields if getattr(field, "oneof", False)}
        if len(discriminators) > 1:
            raise ValueError("Multiple oneof groups are outside this initial syntax probe")
        groups = {}
        for name, field in discriminators.items():
            if field.optional or not isinstance(field.type, EnumRef):
                raise ValueError("OneOf must name a required enum field")
            if field.type.name not in schema.enums:
                raise ValueError("OneOf enum must be included in the schema")
            if not schema.enums[field.type.name].members:
                raise ValueError("OneOf enum must have at least one alternative")
            groups[name] = {}
        for field in record.fields:
            cases = getattr(field, "cases", ())
            tags = {case.tag for case in cases}
            if len(tags) > 1:
                raise ValueError("A payload cannot depend on different discriminators")
            for case in cases:
                _add_case(schema, by_name, groups, case, field.name)
        if not groups:
            messages[record.name] = record
            continue
        tag, cases = next(iter(groups.items()))
        enum = schema.enums[by_name[tag].type.name]
        exhaustive = discriminators[tag].exhaustive
        implicit_units = [member for member in enum.members if member not in cases]
        if exhaustive and implicit_units:
            raise ValueError("OneOf cases must cover every enum member")
        # Make implicit payload-free choices explicit in the normalized contract
        # so both validator backends check all payloads are absent for them.
        cases = {member: cases.get(member) for member in enum.members}
        normalized = AnnotatedMessage(
            **{item.name: getattr(record, item.name) for item in fields(MessageDef)},
            app_properties=getattr(record, "app_properties", ()),
        )
        virtual = getattr(discriminators[tag], "virtual", False)
        normalized = replace(normalized, fields=tuple(
            _plain_field(field) for field in record.fields if not (virtual and field.name == tag)))
        metadata = properties(normalized)
        coverage_namespace = NAMESPACE + ".coverage"
        if coverage_namespace in metadata:
            raise ValueError("OneOf already has a separate coverage declaration")
        metadata[coverage_namespace] = {
            "discriminator": tag, "exhaustive": exhaustive,
            "implicit_units": implicit_units,
        }
        constraints = dict(metadata.pop(NAMESPACE, {}))
        if "tagged" in constraints:
            raise ValueError("OneOf already has a separate tagged declaration")
        if virtual:
            # Keep the logical grouping in explicit probe metadata, but emit
            # no runtime field, wire field or validator for it in this cut.
            virtual_namespace = NAMESPACE + ".virtual"
            if virtual_namespace in metadata:
                raise ValueError("Virtual oneof already has a separate declaration")
            metadata[virtual_namespace] = {
                "discriminator": tag, "enum": enum.name, "cases": cases,
                "runtime_field": False, "wire_field": False, "validation": "deferred",
            }
        else:
            constraints["tagged"] = {"discriminator": tag, "cases": cases}
        # Replace the namespace, preserving annotations for other applications.
        normalized = replace(normalized, app_properties=())
        retained = [app(ns, value) for ns, value in metadata.items()]
        if constraints:
            retained.append(app(NAMESPACE, constraints))
        normalized = annotate(normalized, *retained)
        messages[record.name] = normalized
    # Source enum objects are authoring conveniences; portable normalized IR
    # retains enum definitions and qualified names, not Python object identity.
    enums = {name: EnumDef(value.name, dict(value.members), dict(value.options))
             for name, value in schema.enums.items()}
    return replace(schema, messages=messages, enums=enums)


def _add_case(schema, fields_by_name, groups, case, payload):
    if type(case.tag) is not str or case.tag not in groups:
        raise ValueError("Case must nominate a OneOf field in the same message")
    tag = fields_by_name[case.tag]
    enum = schema.enums[tag.type.name]
    member = case.member
    if isinstance(member, EnumMember):
        if (member.enum.name != enum.name or member.enum.members != enum.members
                or member.enum.options != enum.options):
            raise ValueError("Case member belongs to a different enum")
        member = member.name
    if type(member) is not str or member not in enum.members:
        raise ValueError("Case member is not in the nominated field's enum")
    if member in groups[case.tag]:
        raise ValueError("Duplicate oneof case ownership")
    if payload == case.tag:
        raise ValueError("Discriminator cannot be its own payload")
    groups[case.tag][member] = payload


def compile_validators(schema):
    normalized = normalize_oneofs(schema)
    contract = Contract(normalized, NAMESPACE)
    # The early graph compiler is reused only as a generic union emitter here.
    # It needs no graph index or reference checker for local oneof constraints.
    if contract.indices or contract.checks:
        raise ValueError("Local oneof generation does not accept graph-reference entries")
    if not contract.unions:
        return normalized, "// No non-virtual oneof validators; virtual-group validation is deferred.\n"
    lines = ["// Generated from oneof_fields.taut.py by the isolated syntax probe.",
             "// Validation is explicit; constructors and codecs do not call it.",
             "#[derive(Debug, PartialEq, Eq)]",
             "pub enum ProbeValidationError { InvalidPayload(&'static str) }", ""]
    for name in sorted(contract.unions):
        lines.extend(contract.emit_union(name))
    code = "\n".join(lines).replace("ProbeGraphError", "ProbeValidationError")
    for name in sorted(contract.unions):
        public_name = re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()
        code += f"\npub fn validate_{public_name}(value: &r::{name}) -> Result<(), ProbeValidationError> {{\n"
        code += f"    {contract.union_name(name)}(value)\n}}\n"
    return normalized, code


if __name__ == "__main__":
    import argparse
    from pathlib import Path
    from taut.ir.load import load_schema

    directory = Path(__file__).parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--schema", type=Path, default=directory / "oneof_fields.taut.py")
    parser.add_argument("--output", type=Path, default=directory / "oneof_fields.validation.rs")
    parser.add_argument("--check", action="store_true")
    arguments = parser.parse_args()
    _, generated = compile_validators(load_schema(arguments.schema))
    if arguments.check:
        if not arguments.output.exists() or arguments.output.read_text() != generated:
            raise SystemExit("Stale oneof syntax probe validator")
    else:
        arguments.output.write_text(generated)
        print(arguments.output)
