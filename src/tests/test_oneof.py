"""Python reference conformance corpus 1: native authoring, metadata and behavior."""
import copy
import dataclasses
import json
import sys
import types
from pathlib import Path

import pytest

from taut.contracts import ConfigurationError, require_contract
from taut.descriptors import MessageDescriptor, SchemaBinding, TypeDescriptor
from taut.gen.scaffold import python_api, emit
from taut.ir.dsl import BOOL, INT, STR, Case, Enum, F, List, Map, Msg, OneOf, Ref, schema
from taut.ir.export import schema_json
from taut.ir.load import load_schema, schema_from_json
from taut.ir.model import CaseRule, EnumRef, OneOfRule
from taut.ir.validate import validate, validate_or_raise
from taut.validation import (DeferredCheck, PathSegment, ValidationIssue, ValidationReport,
                             is_record_valid, validate_record)
from taut.wire import cbor, codec, jsoncodec

ROOT = Path(__file__).resolve().parents[2]
EXAMPLE = ROOT / "dev-docs/examples/python-oneof/content.taut.py"
CORPUS_VERSION = "python-oneof-conformance.1"


def module(s=None, validation=True, **kwargs):
    m = types.ModuleType("_oneof_test_" + str(len(sys.modules)))
    sys.modules[m.__name__] = m
    exec(python_api(s or load_schema(EXAMPLE), validation=validation, **kwargs), m.__dict__)
    return m


def codes(report):
    return [(i.code, tuple(p.field_name if p.kind == "field" else p.index if p.kind == "index"
                           else (p.key_type, p.key_cbor_base64) for p in i.path)) for i in report.issues]


@pytest.mark.parametrize("virtual", [False, True])
@pytest.mark.parametrize("exhaustive", [False, True])
def test_flags_and_native_ir_roundtrip(virtual, exhaustive):
    e = Enum("Choice", a=0, b=1)
    s = schema(e, Record=Msg(tag=F(1, OneOf(e, virtual=virtual, exhaustive=exhaustive)),
                            data=F(2, STR, Case(tag=e.a), Case(tag=e.b))))
    validate_or_raise(s)
    doc = schema_json(s)
    assert doc["version"] == 3
    assert schema_from_json(doc) == s
    m = module(s)
    value = m.Record(**({} if virtual else {"tag": m.Choice.a}), data="")
    report = value.validate()
    assert report.is_valid() and report.is_complete() is not virtual
    assert value.is_valid() is not virtual


@pytest.mark.parametrize("bad", [None, 0, 1, "false", [], {}])
@pytest.mark.parametrize("flag", ["virtual", "exhaustive"])
def test_flags_require_actual_booleans(flag, bad):
    with pytest.raises(TypeError):
        OneOf(Enum("Choice", a=0), **{flag: bad})


@pytest.mark.parametrize("case", ["unknown_control", "ordinary_control", "wrong_enum", "duplicate",
                                  "multiple_controls", "exhaustive", "empty", "optional_tag"])
def test_schema_rejections(case, tmp_path):
    e, other = Enum("Choice", a=0, b=1), Enum("OtherChoice", a=0)
    controls = {"tag": F(1, OneOf(e))}
    payloads = {"data": F(3, STR, Case(tag=e.a))}
    if case == "unknown_control":
        payloads = {"data": F(3, STR, Case(no_such=e.a))}
    elif case == "ordinary_control":
        controls = {"tag": F(1, e)}
    elif case == "wrong_enum":
        payloads = {"data": F(3, STR, Case(tag=other.a))}
    elif case == "duplicate":
        payloads["extra"] = F(4, INT, Case(tag=e.a))
    elif case == "multiple_controls":
        controls["other"] = F(2, OneOf(e))
        payloads = {"data": F(3, STR, Case(tag=e.a), Case(other=e.b))}
    elif case == "exhaustive":
        controls = {"tag": F(1, OneOf(e, exhaustive=True))}
    elif case == "empty":
        e = Enum("Choice")
        controls, payloads = {"tag": F(1, OneOf(e))}, {}
    elif case == "optional_tag":
        controls = {"tag": F(1, OneOf(e), optional=True)}
    s = schema(e, other, Record=Msg(**controls, **payloads))
    assert validate(s)
    with pytest.raises(ValueError):
        emit(s, tmp_path, langs=["python"])
    assert not list(tmp_path.iterdir())


def test_ir_old_version_cannot_hide_constraints_and_future_rejected():
    doc = schema_json(load_schema(EXAMPLE))
    for version in (1, 2, 4):
        bad = copy.deepcopy(doc)
        bad["version"] = version
        with pytest.raises(ValueError):
            schema_from_json(bad)
    doc["messages"][0]["fields"][0]["oneof"]["virtual"] = 1
    with pytest.raises(ValueError, match="Boolean"):
        schema_from_json(doc)


@pytest.mark.parametrize("validation", [False, True])
def test_mandatory_immutable_inventory(validation):
    s = load_schema(EXAMPLE)
    m = module(s, validation)
    d = m.Content.DESCRIPTOR
    assert isinstance(d, MessageDescriptor)
    assert [f.name for f in dataclasses.fields(m.Content)] == ["kind", "text", "number", "flag", "items"]
    assert [f.number for f in d.fields] == [1, 2, 3, 4, 5]
    assert d.next_id == 6 and d.descriptor_contract_version == 1
    assert d.oneofs[0].members["empty"] is None
    assert d.fields[0].type.kind == "enum"
    assert d.fields[-1].type.element.kind == "int"
    assert hasattr(m.Content, "validate") is validation
    s.enums["ContentKind"].members["surprise"] = 99
    assert "surprise" not in d.oneofs[0].enum.members
    with pytest.raises(TypeError):
        d.oneofs[0].members["text"] = "number"
    with pytest.raises(dataclasses.FrozenInstanceError):
        d.name = "Changed"
    with pytest.raises(TypeError):
        m.BINDING.message_classes["Content"] = object
    assert m.Content(m.ContentKind.empty).DESCRIPTOR is d
    assert not hasattr(m.Content(m.ContentKind.empty), "__dict__")
    m.Content(m.ContentKind.empty).text = "mutable"
    assert m.VirtualEnvelope.DESCRIPTOR.fields[0].virtual
    assert m.VirtualEnvelope.DESCRIPTOR.fields[0].attribute is None
    assert "kind" not in m.VirtualEnvelope.__slots__


@pytest.mark.parametrize("selection,payload,value", [("number", "number", 0), ("flag", "flag", False),
    ("text", "text", ""), ("items", "items", []), ("empty", None, None)])
def test_presence_and_sparse_json_dense_cbor(selection, payload, value):
    m = module()
    v = m.Content(m.ContentKind[selection], **({payload: value} if payload else {}))
    assert v.is_valid()
    native = {"kind": selection, "text": v.text, "number": v.number, "flag": v.flag, "items": v.items}
    obj = jsoncodec.to_json_value(m.SCHEMA, "Content", native)
    assert set(obj) == {"kind"} | ({payload} if payload else set())
    assert len(cbor.loads(codec.encode(m.SCHEMA, "Content", native))) == 5
    assert jsoncodec.from_json_value(m.SCHEMA, "Content", obj) == native
    assert jsoncodec.from_json_value(m.SCHEMA, "Content", dict(obj, text=obj.get("text"))) == native


def test_invalid_serialize_repair_and_report_snapshot():
    m = module()
    value = m.Content(m.ContentKind.number, text="extra")
    before = value.validate()
    assert codes(before) == [("oneof.payload_unexpected", ("text",)), ("oneof.payload_missing", ("number",))]
    native = {"kind": "number", "text": value.text, "number": value.number, "flag": None, "items": None}
    encoded = codec.encode(m.SCHEMA, "Content", native)
    assert codec.decode(m.SCHEMA, "Content", encoded) == native
    assert jsoncodec.to_json(m.SCHEMA, "Content", native) == '{"kind":"number","text":"extra"}'
    value.text, value.number = None, 42
    assert value.is_valid()
    assert len(before.issues) == 2
    assert before.scope == "recursive"
    with pytest.raises(dataclasses.FrozenInstanceError):
        before.issues[0].path[0].field_name = "changed"
    with pytest.raises(codec.DecodeError):
        jsoncodec.from_json_value(m.SCHEMA, "Content", {"number": "42"})
    with pytest.raises(codec.DecodeError):
        jsoncodec.from_json_value(m.SCHEMA, "Content", {"kind": None})


def test_recursive_scope_wrong_tag_extra_children_virtual_and_shared_paths():
    m = module()
    child = m.Content(m.ContentKind.number)
    wrapper = m.Envelope(child)
    assert wrapper.is_valid(recursive=False)
    assert wrapper.validate(recursive=False) == ValidationReport(scope="local")
    assert codes(wrapper.validate()) == [("oneof.payload_missing", ("content", "number"))]
    virtual = m.VirtualEnvelope(content=child)
    report = virtual.validate()
    assert codes(report) == [("oneof.payload_missing", ("content", "number"))]
    assert len(report.deferred_checks) == 1
    child.number = 0
    assert virtual.validate().is_valid() and not virtual.validate().is_complete()
    assert not virtual.is_valid()
    child.kind, child.number = "wrong enum", None
    shared = m.Collection([child, child], {"z": child, "a": child})
    report = shared.validate()
    assert len(report.issues) == 4
    assert all(i.code == "oneof.invalid_discriminator" for i in report.issues)
    assert [p.path[-2].key_cbor_base64 for p in report.issues[2:]] == ["YWE=", "YXo="]
    shared.by_key.clear()
    assert len(report.issues) == 4


def test_bad_tag_independent_groups_and_nonselected_child():
    e = Enum("Choice", child=0, empty=1)
    s = schema(e,
        Child=Msg(tag=F(1, OneOf(e)), data=F(2, STR, Case(tag=e.child))),
        Parent=Msg(tag=F(1, OneOf(e)), other=F(2, OneOf(e)),
                   child=F(3, Ref.Child, Case(tag=e.child)), text=F(4, STR, Case(other=e.child))))
    m = module(s)
    v = m.Parent("wrong", m.Choice.child, child=m.Child(m.Choice.child))
    assert codes(v.validate()) == [("oneof.invalid_discriminator", ("tag",)),
                                   ("oneof.payload_missing", ("text",)),
                                   ("oneof.payload_missing", ("child", "data"))]
    v.tag = m.Choice.empty
    assert ("oneof.payload_unexpected", ("child",)) in codes(v.validate())
    assert ("oneof.payload_missing", ("child", "data")) in codes(v.validate())


def test_recursive_schema_cycles_and_dynamic_misuse():
    m = module()
    root = m.Tree(None, [])
    root.children.extend([root, m.Tree(m.Content(m.ContentKind.text), [])])
    report = root.validate()
    assert codes(report) == [("validation.ownership_cycle", ("children", 0)),
                             ("oneof.payload_missing", ("children", 1, "content", "text"))]
    root.children = [object()]
    assert codes(root.validate()) == [("validation.type_mismatch", ("children", 0))]
    root.children = "wrong"
    assert codes(root.validate()) == [("validation.type_mismatch", ("children",))]


@pytest.mark.parametrize("recursive", [False, True])
@pytest.mark.parametrize("shape", ["valid", "missing", "extra", "tag", "virtual", "cycle", "bad_list"])
def test_fast_report_equivalence(shape, recursive):
    m = module()
    v = m.Content(m.ContentKind.text, text="ok")
    if shape == "missing": v.text = None
    if shape == "extra": v.number = 0
    if shape == "tag": v.kind = 0
    if shape == "virtual": v = m.VirtualEnvelope(content=v)
    if shape == "cycle":
        v = m.Tree(None, [])
        v.children.append(v)
    if shape == "bad_list": v = m.Collection("wrong", {})
    r = v.validate(recursive=recursive)
    assert v.is_valid(recursive=recursive) == (r.is_valid() and r.is_complete())


def test_options_pairing_and_general_reports(monkeypatch):
    m = module()
    value = m.Content(m.ContentKind.empty)
    for arg in (None, 0, "yes", {}):
        with pytest.raises(TypeError): value.validate(recursive=arg)
        with pytest.raises(TypeError): value.is_valid(recursive=arg)
    with pytest.raises(TypeError): value.validate(False)
    with pytest.raises(ConfigurationError): validate_record(value, m.Tree.DESCRIPTOR, m.BINDING)
    with pytest.raises(ConfigurationError): validate_record(object(), m.Content.DESCRIPTOR, m.BINDING)
    p = [PathSegment.for_field("custom")]
    issue = ValidationIssue("app.rule.failed", "app.rule.v2", p, "example")
    issues = [issue]
    report = ValidationReport(issues)
    p.clear(); issues.clear()
    assert report.issues[0].path[0].field_name == "custom"
    require_contract(artifact="compatible patch", generator="0.10.999")
    for kwargs in ({"descriptor": 99}, {"codec": 99}, {"owner": "private"}, {"capabilities": ["future.v3"]}):
        with pytest.raises(ConfigurationError, match="regenerate"): require_contract(artifact="bad", **kwargs)
    # Fast path must not construct reports or issues.
    monkeypatch.setattr("taut.validation.ValidationReport", lambda *a: pytest.fail("fast report allocation"))
    monkeypatch.setattr("taut.validation.ValidationIssue", lambda *a: pytest.fail("fast issue allocation"))
    assert value.is_valid()
    value.text = "extra"
    assert not value.is_valid()


@pytest.mark.parametrize("name", ["DESCRIPTOR", "validate", "is_valid", "_taut_private"])
def test_field_name_collision_modes(name, tmp_path):
    s = schema(Record=Msg(**{name: F(1, INT)}))
    if name in ("validate", "is_valid"):
        m = module(s, validation=False)
        assert getattr(m.Record(3), name) == 3
    with pytest.raises(ValueError, match="collision"):
        emit(s, tmp_path, langs=["python"], validation=True)
    assert not list(tmp_path.iterdir())


def test_descriptor_bad_links_and_rule_configuration():
    with pytest.raises(ConfigurationError): TypeDescriptor("str", reference="bad")
    m = module()
    broken = dataclasses.replace(m.Content.DESCRIPTOR, descriptor_contract_version=99)
    registry = dataclasses.replace(m.SCHEMA_DESCRIPTOR, messages=dict(m.SCHEMA_DESCRIPTOR.messages, Content=broken))
    with pytest.raises(ConfigurationError): SchemaBinding(registry, m.BINDING.message_classes, m.BINDING.enum_classes)


def test_inventory_options_reserved_names_field_order_and_types():
    from taut.ir.dsl import BYTES, FLOAT, option
    e = Enum("Choice", yes=0, no=1)
    s = schema(option.max_depth(48), e,
        Record=Msg(option.max_encoded_len(2048),
                   tag=F(5, OneOf(e)), items=F(8, List(INT), Case(tag=e.yes)),
                   data=F(2, BYTES, optional=True, transient=True),
                   ratio=F(3, FLOAT), enabled=F(4, BOOL),
                   by_id=F(6, Map(INT, Ref.Record)),
                   reserved=[1, "retired"], next_id=10))
    m = module(s)
    desc = m.Record.DESCRIPTOR
    assert [f.number for f in desc.fields] == [2, 3, 4, 5, 6, 8]
    assert desc.reserved_numbers == (1,) and desc.reserved_names == ("retired",)
    assert desc.options == {"max_encoded_len": 2048}
    assert desc.effective_options == {"max_depth": 48, "max_encoded_len": 2048}
    assert desc.fields[0].transient and desc.fields[0].presence == "nullable"
    assert desc.fields[-2].type.value.reference == "Record"
    assert m.SCHEMA_DESCRIPTOR.effective_options["max_depth"] == 48
    assert m.SCHEMA_DESCRIPTOR.enums["Choice"].member_options == {"yes": {}, "no": {}}
    with pytest.raises(TypeError): m.SCHEMA.messages["Record"].options["max_encoded_len"] = 9
    with pytest.raises(TypeError): m.SCHEMA.enums["Choice"].members["yes"] = 9


@pytest.mark.parametrize("key_type,keys,encoded", [
    (INT, [-1, 24, 0], ["AA==", "GBg=", "IA=="]),
    (BOOL, [True, False], ["9A==", "9Q=="]),
    (STR, ["zz", "b", "a"], ["YWE=", "YWI=", "Ynp6"])])
def test_canonical_key_order_and_snapshot(key_type, keys, encoded):
    s = load_schema(EXAMPLE)
    bag = Msg(by_key=F(1, Map(key_type, Ref.Content)))
    s = schema(*s.enums.values(), Content=s.messages["Content"], Bag=bag)
    m = module(s)
    child = m.Content(m.ContentKind.number)
    value = m.Bag({k: child for k in keys})
    report = value.validate()
    assert [i.path[1].key_cbor_base64 for i in report.issues] == encoded
    value.by_key.clear()
    assert [i.path[1].key_cbor_base64 for i in report.issues] == encoded


def test_shared_reports_from_independent_schemas_and_unknown_rules():
    from taut.descriptors import ConstraintDescriptor
    a, b = module(), module()
    ar = a.Content(a.ContentKind.text).validate()
    br = b.Content(b.ContentKind.number).validate()
    aggregate = ValidationReport(ar.issues + br.issues)
    assert type(ar) is type(br) is type(aggregate) is ValidationReport
    assert type(ar.issues[0]) is type(br.issues[0]) is ValidationIssue
    altered = dataclasses.replace(a.Content.DESCRIPTOR, constraints=(ConstraintDescriptor("future.rule.v8"),))
    registry = dataclasses.replace(a.SCHEMA_DESCRIPTOR, messages=dict(a.SCHEMA_DESCRIPTOR.messages, Content=altered))
    with pytest.raises(ConfigurationError, match="unsupported constraint"):
        SchemaBinding(registry, a.BINDING.message_classes, a.BINDING.enum_classes)


def test_authoring_only_qualified_members_and_no_standalone_cases():
    e = Enum("Choice", a=0)
    with pytest.raises(TypeError): Case(tag="a")
    with pytest.raises(TypeError): Case(tag=e.a, other=e.a)
    with pytest.raises(TypeError): Msg(Case(tag=e.a))
    with pytest.raises(TypeError): OneOf("Choice")


def test_duplicate_names_and_invalid_key_configuration_fail_before_publication(tmp_path):
    with pytest.raises(ValueError, match="duplicate schema"):
        schema(Enum("Choice", a=0), Enum("Choice", b=1))
    s = schema(Msg("Record", F("value", 1, INT), F("value", 2, STR)))
    with pytest.raises(ValueError, match="duplicate field"):
        emit(s, tmp_path, langs=["python"])
    assert not list(tmp_path.iterdir())
    with pytest.raises(ValueError): PathSegment.for_key("str", b"\x00")
    with pytest.raises(ValueError): PathSegment.for_key("int", b"\x18\x00")


def test_keyword_field_bindings_preserve_schema_names_and_reject_real_collisions(tmp_path):
    e = Enum("Choice", data=0)
    s = schema(e, Msg("Record", F("kind", 1, OneOf(e)), F("from", 2, STR, Case(kind=e.data))))
    m = module(s)
    value = m.Record(m.Choice.data)
    assert value.DESCRIPTOR.fields_by_name["from"].attribute == "from_"
    assert codes(value.validate()) == [("oneof.payload_missing", ("from",))]
    value.from_ = "present"
    assert value.is_valid()
    bad = schema(Msg("Record", F("from", 1, INT), F("from_", 2, INT)))
    with pytest.raises(ValueError, match="escaping"):
        python_api(bad)
    with pytest.raises(ValueError):
        emit(bad, tmp_path, langs=["python"])
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize("validation", [False, True])
@pytest.mark.parametrize("runtime_mode", ["source", "package", None])
def test_private_fields_are_named_preflight_failures(tmp_path, validation, runtime_mode):
    s = schema(Msg("Record", F("__private", 1, INT)))
    with pytest.raises(ValueError, match="Record.__private"):
        emit(s, tmp_path, langs=["python"], validation=validation, runtime_mode=runtime_mode)
    assert not list(tmp_path.iterdir())


def test_internal_double_underscore_substrings_remain_ordinary_fields():
    m = module(schema(Record=Msg(part__name=F(1, INT))))
    value = m.Record(1)
    assert value.part__name == 1 and value.is_valid()
    assert value.DESCRIPTOR.fields_by_name["part__name"].attribute == "part__name"


@pytest.mark.parametrize("name", ["name", "members", "options"])
def test_enum_authoring_metadata_namespace_is_reserved_early(name):
    with pytest.raises(ValueError, match=rf"member '{name}'.*reserved.*metadata namespace"):
        Enum("Choice", **{name: 0})
    choice = Enum("Choice", ordinary=0)
    assert Case(tag=choice.ordinary) == CaseRule("tag", "Choice", "ordinary")


def test_compatibility_uses_normalized_constraint_facts_only():
    from taut.ir import compat
    from taut.ir.dsl import MISSING_OK
    choice = Enum("Choice", payload=0, alternate=1, empty=2)
    old = schema(choice, Record=Msg(kind=F(1, OneOf(choice)),
                                   data=F(2, STR, Case(kind=choice.payload), Case(kind=choice.alternate))))
    original = old.messages["Record"]
    variants = [dataclasses.replace(original, fields=original.fields + (F("later", 3, INT, optional=MISSING_OK),)),
                dataclasses.replace(original, fields=tuple(reversed(original.fields))),
                dataclasses.replace(original, fields=(original.fields[0],
                    dataclasses.replace(original.fields[1], cases=tuple(reversed(original.fields[1].cases)))))]
    for record in variants:
        new = dataclasses.replace(old, messages={"Record": record})
        validate_or_raise(new)
        assert compat.breaking(old, new) == []
        compat.check_or_raise(old, new)
    for replacement in (dataclasses.replace(original.fields[0], oneof=OneOfRule("Choice", virtual=True)),
                        dataclasses.replace(original.fields[0], oneof=OneOfRule("Choice", exhaustive=True)),
                        dataclasses.replace(original.fields[0], oneof=None)):
        new = dataclasses.replace(old, messages={"Record": dataclasses.replace(original, fields=(replacement, original.fields[1]))})
        assert any("constraints/projection" in c.detail for c in compat.breaking(old, new))
    changed = dataclasses.replace(original.fields[1], cases=(CaseRule("other", "Choice", "payload"),))
    new = dataclasses.replace(old, messages={"Record": dataclasses.replace(original, fields=(original.fields[0], changed))})
    assert any("constraints/projection" in c.detail for c in compat.breaking(old, new))


@pytest.mark.parametrize("defect", ["dangling", "extra_parameter", "missing_parameter", "missing_constraint",
                                   "missing_group", "duplicate_constraint"])
def test_known_rule_constraints_must_match_the_normalized_group(defect):
    from taut.descriptors import ConstraintDescriptor
    m = module()
    original = m.Content.DESCRIPTOR
    good = ConstraintDescriptor("taut.oneof.v1", {"controlling_field": "kind"})
    changes = {}
    if defect == "dangling": changes["constraints"] = (ConstraintDescriptor("taut.oneof.v1", {"controlling_field":"not_a_field", "version":999}),)
    if defect == "extra_parameter": changes["constraints"] = (ConstraintDescriptor("taut.oneof.v1", {"controlling_field":"kind", "version":999}),)
    if defect == "missing_parameter": changes["constraints"] = (ConstraintDescriptor("taut.oneof.v1"),)
    if defect == "missing_constraint": changes["constraints"] = ()
    if defect == "missing_group": changes["oneofs"] = ()
    if defect == "duplicate_constraint": changes["constraints"] = (good, good)
    altered = dataclasses.replace(original, **changes)
    registry = dataclasses.replace(m.SCHEMA_DESCRIPTOR, messages=dict(m.SCHEMA_DESCRIPTOR.messages, Content=altered))
    with pytest.raises(ConfigurationError):
        SchemaBinding(registry, m.BINDING.message_classes, m.BINDING.enum_classes)
    assert m.Content(m.ContentKind.empty).is_valid()
