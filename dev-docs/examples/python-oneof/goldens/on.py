"""GENERATED native Python types — do not edit."""
# Generator build: python-oneof-reference.1; descriptor=1; codec=1; owner=taut.python.foundation
from __future__ import annotations
from dataclasses import dataclass as _taut_dataclass, field as _taut_field
from enum import Enum as _taut_Enum
from typing import ClassVar as _taut_ClassVar
try:
    from taut.contracts import require_contract as _taut_require_contract
    _taut_require_contract(artifact='schema_9c886c43d8695c4e', descriptor=1, codec=1, capabilities=('descriptors.v1', 'codec.v1', 'oneof.v1'), generator='python-oneof-reference.1')
    from taut import facts as _taut_facts
    from taut.descriptors import publish as _taut_publish, MessageDescriptor as _taut_MessageDescriptor
except ImportError as _taut_error:
    raise ImportError('schema_9c886c43d8695c4e: compatible taut foundation required (owner=taut.python.foundation, descriptor=1, codec=1); supply compatible runtime and regenerate/rebind artifacts') from _taut_error
try:
    from taut.validation import (ValidationReport as _taut_ValidationReport,
        validate_record as _taut_validate, is_record_valid as _taut_is_valid)
except ImportError as _taut_error:
    raise ImportError('schema_9c886c43d8695c4e: required validation engine is missing/incompatible; regenerate source owner with validation or rebind compatible package runtime') from _taut_error

class ContentKind(_taut_Enum):
    text = 0
    number = 1
    flag = 2
    items = 3
    empty = 4

@_taut_dataclass(slots=True)
class Content:
    DESCRIPTOR: _taut_ClassVar[_taut_MessageDescriptor]
    kind: ContentKind
    text: str | None = _taut_field(default=None, kw_only=True)
    number: int | None = _taut_field(default=None, kw_only=True)
    flag: bool | None = _taut_field(default=None, kw_only=True)
    items: list[int] | None = _taut_field(default=None, kw_only=True)

    def validate(self, *, recursive: bool = True) -> _taut_ValidationReport:
        return _taut_validate(self, self.DESCRIPTOR, self.__taut_binding__, recursive=recursive)

    def is_valid(self, *, recursive: bool = True) -> bool:
        return _taut_is_valid(self, self.DESCRIPTOR, self.__taut_binding__, recursive=recursive)

@_taut_dataclass(slots=True)
class Envelope:
    DESCRIPTOR: _taut_ClassVar[_taut_MessageDescriptor]
    content: Content

    def validate(self, *, recursive: bool = True) -> _taut_ValidationReport:
        return _taut_validate(self, self.DESCRIPTOR, self.__taut_binding__, recursive=recursive)

    def is_valid(self, *, recursive: bool = True) -> bool:
        return _taut_is_valid(self, self.DESCRIPTOR, self.__taut_binding__, recursive=recursive)

@_taut_dataclass(slots=True)
class VirtualEnvelope:
    DESCRIPTOR: _taut_ClassVar[_taut_MessageDescriptor]
    content: Content | None = _taut_field(default=None, kw_only=True)

    def validate(self, *, recursive: bool = True) -> _taut_ValidationReport:
        return _taut_validate(self, self.DESCRIPTOR, self.__taut_binding__, recursive=recursive)

    def is_valid(self, *, recursive: bool = True) -> bool:
        return _taut_is_valid(self, self.DESCRIPTOR, self.__taut_binding__, recursive=recursive)

@_taut_dataclass(slots=True)
class Collection:
    DESCRIPTOR: _taut_ClassVar[_taut_MessageDescriptor]
    entries: list[Content]
    by_key: dict[str, Content]

    def validate(self, *, recursive: bool = True) -> _taut_ValidationReport:
        return _taut_validate(self, self.DESCRIPTOR, self.__taut_binding__, recursive=recursive)

    def is_valid(self, *, recursive: bool = True) -> bool:
        return _taut_is_valid(self, self.DESCRIPTOR, self.__taut_binding__, recursive=recursive)

@_taut_dataclass(slots=True)
class Tree:
    DESCRIPTOR: _taut_ClassVar[_taut_MessageDescriptor]
    content: Content | None
    children: list[Tree]

    def validate(self, *, recursive: bool = True) -> _taut_ValidationReport:
        return _taut_validate(self, self.DESCRIPTOR, self.__taut_binding__, recursive=recursive)

    def is_valid(self, *, recursive: bool = True) -> bool:
        return _taut_is_valid(self, self.DESCRIPTOR, self.__taut_binding__, recursive=recursive)

SCHEMA = _taut_facts.freeze_schema(_taut_facts.Schema(enums={'ContentKind': _taut_facts.EnumDef(name='ContentKind', members={'text': 0, 'number': 1, 'flag': 2, 'items': 3, 'empty': 4}, options={})}, messages={'Content': _taut_facts.MessageDef(name='Content', fields=(_taut_facts.FieldDef(name='kind', tag=1, type=_taut_facts.EnumRef(name='ContentKind'), optional=False, transient=False, merge=None, options={}, oneof=_taut_facts.OneOfRule(enum='ContentKind', virtual=False, exhaustive=False), cases=()), _taut_facts.FieldDef(name='text', tag=2, type=_taut_facts.Scalar(kind='str'), optional=True, transient=False, merge=None, options={}, oneof=None, cases=(_taut_facts.CaseRule(controlling_field='kind', enum='ContentKind', member='text'),)), _taut_facts.FieldDef(name='number', tag=3, type=_taut_facts.Scalar(kind='int'), optional=True, transient=False, merge=None, options={}, oneof=None, cases=(_taut_facts.CaseRule(controlling_field='kind', enum='ContentKind', member='number'),)), _taut_facts.FieldDef(name='flag', tag=4, type=_taut_facts.Scalar(kind='bool'), optional=True, transient=False, merge=None, options={}, oneof=None, cases=(_taut_facts.CaseRule(controlling_field='kind', enum='ContentKind', member='flag'),)), _taut_facts.FieldDef(name='items', tag=5, type=_taut_facts.ListOf(elem=_taut_facts.Scalar(kind='int')), optional=True, transient=False, merge=None, options={}, oneof=None, cases=(_taut_facts.CaseRule(controlling_field='kind', enum='ContentKind', member='items'),))), reserved_tags=(), reserved_names=(), next_id=6, options={}), 'Envelope': _taut_facts.MessageDef(name='Envelope', fields=(_taut_facts.FieldDef(name='content', tag=1, type=_taut_facts.MsgRef(name='Content'), optional=False, transient=False, merge=None, options={}, oneof=None, cases=()),), reserved_tags=(), reserved_names=(), next_id=None, options={}), 'VirtualEnvelope': _taut_facts.MessageDef(name='VirtualEnvelope', fields=(_taut_facts.FieldDef(name='kind', tag=1, type=_taut_facts.EnumRef(name='ContentKind'), optional=False, transient=False, merge=None, options={}, oneof=_taut_facts.OneOfRule(enum='ContentKind', virtual=True, exhaustive=False), cases=()), _taut_facts.FieldDef(name='content', tag=2, type=_taut_facts.MsgRef(name='Content'), optional=True, transient=False, merge=None, options={}, oneof=None, cases=(_taut_facts.CaseRule(controlling_field='kind', enum='ContentKind', member='text'),))), reserved_tags=(), reserved_names=(), next_id=3, options={}), 'Collection': _taut_facts.MessageDef(name='Collection', fields=(_taut_facts.FieldDef(name='entries', tag=1, type=_taut_facts.ListOf(elem=_taut_facts.MsgRef(name='Content')), optional=False, transient=False, merge=None, options={}, oneof=None, cases=()), _taut_facts.FieldDef(name='by_key', tag=2, type=_taut_facts.MapOf(key=_taut_facts.Scalar(kind='str'), value=_taut_facts.MsgRef(name='Content')), optional=False, transient=False, merge=None, options={}, oneof=None, cases=())), reserved_tags=(), reserved_names=(), next_id=None, options={}), 'Tree': _taut_facts.MessageDef(name='Tree', fields=(_taut_facts.FieldDef(name='content', tag=1, type=_taut_facts.MsgRef(name='Content'), optional=True, transient=False, merge=None, options={}, oneof=None, cases=()), _taut_facts.FieldDef(name='children', tag=2, type=_taut_facts.ListOf(elem=_taut_facts.MsgRef(name='Tree')), optional=False, transient=False, merge=None, options={}, oneof=None, cases=())), reserved_tags=(), reserved_names=(), next_id=None, options={})}, services={}, extensions=(), options={}))
SCHEMA_DESCRIPTOR, BINDING = _taut_publish(
    SCHEMA, {'Content': Content, 'Envelope': Envelope, 'VirtualEnvelope': VirtualEnvelope, 'Collection': Collection, 'Tree': Tree},
    {'ContentKind': ContentKind},
    identity='schema_9c886c43d8695c4e', ir_version=3, external=(),
    attributes={'Content': {'kind': 'kind', 'text': 'text', 'number': 'number', 'flag': 'flag', 'items': 'items'}, 'Envelope': {'content': 'content'}, 'VirtualEnvelope': {'content': 'content'}, 'Collection': {'entries': 'entries', 'by_key': 'by_key'}, 'Tree': {'content': 'content', 'children': 'children'}})

__all__ = ['ContentKind', 'Content', 'Envelope', 'VirtualEnvelope', 'Collection', 'Tree', 'SCHEMA', 'SCHEMA_DESCRIPTOR', 'BINDING']
