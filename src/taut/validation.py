"""Explicit validation over generated descriptors. No compiler or field discovery."""
from __future__ import annotations

import base64
from dataclasses import dataclass

from .contracts import ConfigurationError
from .descriptors import SchemaBinding
from .rules import ONEOF_RULE
from .wire import cbor


@dataclass(frozen=True, slots=True)
class PathSegment:
    kind: str
    field_name: str | None = None
    index: int | None = None
    key_type: str | None = None
    key_cbor_base64: str | None = None

    def __post_init__(self):
        if self.kind == "field":
            good = type(self.field_name) is str and self.index is self.key_type is self.key_cbor_base64 is None
        elif self.kind == "index":
            good = type(self.index) is int and self.index >= 0 and self.field_name is self.key_type is self.key_cbor_base64 is None
        elif self.kind == "key":
            good = self.field_name is self.index is None and self.key_type in ("str", "int", "bool") and type(self.key_cbor_base64) is str
            if good:
                try:
                    encoded = base64.b64decode(self.key_cbor_base64, validate=True)
                    good = base64.b64encode(encoded).decode("ascii") == self.key_cbor_base64
                    decoded = cbor.loads(encoded)
                    good = good and type(decoded) is {"str": str, "int": int, "bool": bool}[self.key_type]
                    good = good and cbor.dumps(decoded) == encoded
                except ValueError:
                    good = False
        else:
            good = False
        if not good:
            raise ValueError("invalid validation path segment")

    @staticmethod
    def for_field(name):
        return PathSegment("field", field_name=name)

    @staticmethod
    def for_index(index):
        return PathSegment("index", index=index)

    @staticmethod
    def for_key(key_type, canonical_bytes):
        return PathSegment("key", key_type=key_type,
                           key_cbor_base64=base64.b64encode(bytes(canonical_bytes)).decode("ascii"))


def _path(path):
    result = tuple(path)
    if not all(isinstance(p, PathSegment) for p in result):
        raise TypeError("path requires immutable PathSegments")
    return result


@dataclass(frozen=True, slots=True)
class ValidationIssue:
    code: str
    rule: str
    path: tuple[PathSegment, ...]
    message: str

    def __post_init__(self):
        if any(type(v) is not str for v in (self.code, self.rule, self.message)):
            raise TypeError("diagnostic code/rule/message must be strings")
        object.__setattr__(self, "path", _path(self.path))


@dataclass(frozen=True, slots=True)
class DeferredCheck:
    rule: str
    path: tuple[PathSegment, ...]
    reason_code: str
    message: str

    def __post_init__(self):
        if any(type(v) is not str for v in (self.rule, self.reason_code, self.message)):
            raise TypeError("deferred rule/reason/message must be strings")
        object.__setattr__(self, "path", _path(self.path))


@dataclass(frozen=True, slots=True)
class ValidationReport:
    issues: tuple[ValidationIssue, ...] = ()
    deferred_checks: tuple[DeferredCheck, ...] = ()
    scope: str = "recursive"

    def __post_init__(self):
        object.__setattr__(self, "issues", tuple(self.issues))
        object.__setattr__(self, "deferred_checks", tuple(self.deferred_checks))
        if self.scope not in ("local", "recursive"):
            raise ValueError("scope must be local or recursive")
        if not all(isinstance(i, ValidationIssue) for i in self.issues) or not all(
                isinstance(d, DeferredCheck) for d in self.deferred_checks):
            raise TypeError("report collections require shared diagnostic types")

    def is_valid(self):
        return not self.issues

    def is_complete(self):
        return not self.deferred_checks


def _issue(code, path, message, rule="validation.shape.v1"):
    return (False, code, rule, path, message)


def _read(value, field, path):
    try:
        return getattr(value, field.attribute), None
    except AttributeError:
        return None, _issue("validation.type_mismatch", path, "generated slot is uninitialized")


def _group_events(value, desc, binding, group, path):
    ctrl = desc.fields_by_name[group.controlling_field]
    if group.virtual:
        yield (True, "oneof.virtual_deferred", ONEOF_RULE,
               path + (PathSegment.for_field(ctrl.name),), "virtual selection is deferred")
        return
    tag, error = _read(value, ctrl, path + (PathSegment.for_field(ctrl.name),))
    enum_cls = binding.enum_classes[ctrl.type.reference]
    if error or type(tag) is not enum_cls:
        yield _issue("oneof.invalid_discriminator", path + (PathSegment.for_field(ctrl.name),),
                     "expected a member of the controlling enum", ONEOF_RULE)
        return
    selected = group.members[tag.name]
    payloads = frozenset(p for p in group.members.values() if p is not None)
    for f in desc.fields:
        if f.name not in payloads:
            continue
        payload, error = _read(value, f, path + (PathSegment.for_field(f.name),))
        if error:
            yield error
        if f.name == selected and payload is None:
            yield _issue("oneof.payload_missing", path + (PathSegment.for_field(f.name),),
                         "selected payload is absent", ONEOF_RULE)
        elif f.name != selected and payload is not None:
            yield _issue("oneof.payload_unexpected", path + (PathSegment.for_field(f.name),),
                         "nonselected payload is present", ONEOF_RULE)


def _scalar_matches(kind, value):
    if kind == "int":
        return type(value) is int and cbor.INT_MIN <= value <= cbor.INT_MAX
    if kind == "float":
        return type(value) is float
    return type(value) is {"str": str, "bool": bool, "bytes": bytes}[kind]


def _walk_type(value, t, binding, path, ancestors):
    if t.kind == "message":
        if type(value) is not binding.message_classes[t.reference]:
            yield _issue("validation.type_mismatch", path, "expected generated child message")
            return
        child_binding = binding.message_binding(t.reference)
        child_desc = binding.schema.messages[t.reference]
        yield from _walk(value, child_desc, child_binding, path, ancestors, True)
    elif t.kind == "list":
        if type(value) is not list:
            yield _issue("validation.type_mismatch", path, "expected list")
            return
        if id(value) in ancestors:
            yield _issue("validation.ownership_cycle", path, "active ancestor encountered")
            return
        ancestors.add(id(value))
        try:
            for i, child in enumerate(value):
                yield from _walk_type(child, t.element, binding, path + (PathSegment.for_index(i),), ancestors)
        finally:
            ancestors.remove(id(value))
    elif t.kind == "map":
        if type(value) is not dict:
            yield _issue("validation.type_mismatch", path, "expected map")
            return
        if id(value) in ancestors:
            yield _issue("validation.ownership_cycle", path, "active ancestor encountered")
            return
        entries = []
        for key, child in value.items():
            if not _scalar_matches(t.key.kind, key):
                yield _issue("validation.type_mismatch", path, "invalid map key type/range")
            else:
                entries.append((cbor.dumps(key), child))
        ancestors.add(id(value))
        try:
            for encoded, child in sorted(entries, key=lambda pair: pair[0]):
                keypath = path + (PathSegment.for_key(t.key.kind, encoded),)
                yield from _walk_type(child, t.value, binding, keypath, ancestors)
        finally:
            ancestors.remove(id(value))
    elif t.kind == "enum":
        if type(value) is not binding.enum_classes[t.reference]:
            yield _issue("validation.type_mismatch", path, "expected generated enum member")
    elif not _scalar_matches(t.kind, value):
        yield _issue("validation.type_mismatch", path, f"expected {t.kind}")


def _walk(value, desc, binding, path, ancestors, recursive):
    if id(value) in ancestors:
        yield _issue("validation.ownership_cycle", path, "active ancestor encountered")
        return
    ancestors.add(id(value))
    try:
        for f in desc.fields:
            group = desc.groups_by_field.get(f.name)
            if group:
                yield from _group_events(value, desc, binding, group, path)
            if recursive and not f.virtual:
                fieldpath = path + (PathSegment.for_field(f.name),)
                child, error = _read(value, f, fieldpath)
                if error:
                    if not group:
                        yield error
                elif child is not None and not group:
                    yield from _walk_type(child, f.type, binding, fieldpath, ancestors)
    finally:
        ancestors.remove(id(value))


def _events(value, descriptor, binding, recursive):
    if type(recursive) is not bool:
        raise TypeError("recursive must be Boolean")
    if not isinstance(binding, SchemaBinding):
        raise ConfigurationError("expected shared SchemaBinding; rebind runtime owner")
    binding.check_pair(value, descriptor)
    return _walk(value, descriptor, binding, (), set(), recursive)


def validate_record(value, descriptor, binding, *, recursive=True):
    issues, deferred = [], []
    for is_deferred, code, rule, path, message in _events(value, descriptor, binding, recursive):
        if is_deferred:
            deferred.append(DeferredCheck(rule, path, code, message))
        else:
            issues.append(ValidationIssue(code, rule, path, message))
    return ValidationReport(issues, deferred, "recursive" if recursive else "local")


def is_record_valid(value, descriptor, binding, *, recursive=True):
    events = _events(value, descriptor, binding, recursive)
    try:
        return next(events, None) is None
    finally:
        events.close()
