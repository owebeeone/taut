"""Native Kotlin descriptor values and direct typed binding callbacks."""
from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping

from ..ir.export import schema_json
from ..ir.model import Scalar, EnumRef, MsgRef, ListOf, MapOf
from ..ir.options import effective_map
from ..rules import check_rules
from . import kotlin as kt
from .rust_metadata import fingerprint as portable_fingerprint, has_children

D = 'taut.validation.descriptors.'


def fingerprint(schema, name):
    portable = portable_fingerprint(schema, name)
    if name not in schema.messages:
        return portable
    # A child emitted under different inherited decode bounds is not the same
    # descriptor/codec artifact even when its own declaration is unchanged.
    effective = json.dumps(effective_map(schema, message=name), sort_keys=True)
    return hashlib.sha256((portable + ':' + effective).encode()).hexdigest()


def q(value):
    # Kotlin has no JSON \f escape and interpolates $. Quote character by
    # character so an existing literal backslash-f is preserved exactly too.
    escapes = {'"': '\\"', '\\': '\\\\', '$': '\\$', '\b': '\\b', '\t': '\\t', '\n': '\\n', '\r': '\\r'}
    return '"' + ''.join(escapes.get(c, f'\\u{ord(c):04x}' if ord(c) < 32 or 0xD800 <= ord(c) <= 0xDFFF or ord(c) in (0x2028,0x2029) else c) for c in value) + '"'


def value(v):
    if v is None:
        return 'null'
    if type(v) is bool:
        return str(v).lower()
    if type(v) is int:
        return str(v) + 'L' if v != -(1 << 63) else 'Long.MIN_VALUE'
    if type(v) is float:
        return repr(v)
    if isinstance(v, str):
        return q(v)
    if isinstance(v, Mapping):
        return opts(v)
    if isinstance(v, (tuple, list)):
        return 'listOf(' + ', '.join(value(x) for x in v) + ')'
    if isinstance(v, bytes):
        return 'byteArrayOf(' + ', '.join(str(x if x < 128 else x-256) for x in v) + ')'
    raise TypeError(f'unsupported Kotlin metadata option {v!r}')


def opts(v):
    return 'mapOf<String, Any?>(' + ', '.join(q(k) + ' to ' + value(x) for k, x in v.items()) + ')'


def td(t):
    if isinstance(t, Scalar):
        return f'{D}TypeDescriptor({q(t.kind)})'
    if isinstance(t, (MsgRef, EnumRef)):
        kind = 'message' if isinstance(t, MsgRef) else 'enum'
        target = f'{kt._id(t.name)}.tautBinding().rawDescriptor' if kind == 'message' else f'{kt._id(t.name)}.descriptor()'
        return f'{D}TypeDescriptor({q(kind)}, {kind} = {{ {target} }})'
    if isinstance(t, ListOf):
        return f'{D}TypeDescriptor("list", element = {td(t.elem)})'
    if isinstance(t, MapOf):
        return f'{D}TypeDescriptor("map", key = {td(t.key)}, value = {td(t.value)})'
    raise TypeError(t)


def imports(schema, mapping):
    if mapping is None:
        return []
    if not isinstance(mapping, dict):
        raise ValueError('Kotlin external types must be a name-to-qualified-type mapping')
    out = []
    for name, path in sorted(mapping.items()):
        if name not in set(schema.messages) | set(schema.enums):
            raise ValueError(f'unknown Kotlin external type {name}')
        if not isinstance(path, str) or not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)+', path):
            raise ValueError(f'invalid Kotlin external type path {path!r}')
        out.append(f'import {".".join(kt._id(p) for p in path.split("."))} as {kt._id(name)}')
    def refs(t):
        if isinstance(t, (MsgRef, EnumRef)): return {t.name}
        if isinstance(t, ListOf): return refs(t.elem)
        if isinstance(t, MapOf): return refs(t.key) | refs(t.value)
        return set()
    for name in mapping:
        if name in schema.messages:
            missing = set().union(*(refs(f.type) for f in schema.messages[name].fields)) - mapping.keys()
            if missing:
                raise ValueError(f'Kotlin external {name} requires mappings for {sorted(missing)}; bind full dependency graph')
    return out


def visit(t, expr, depth=0):
    if isinstance(t, MsgRef):
        return [f'if (!visitor.record({kt._id(t.name)}.tautBinding().bind({expr}))) return@SchemaBinding false']
    if isinstance(t, ListOf) and has_children(t.elem):
        item = f'item{depth}'
        return [f'for ((index{depth}, {item}) in {expr}.withIndex()) {{',
                f'visitor.pushIndex(index{depth}.toLong())', *visit(t.elem, item, depth+1), 'visitor.pop()', '}']
    if isinstance(t, MapOf) and has_children(t.value):
        key, item = f'key{depth}', f'item{depth}'
        enc = kt._enc(t.key, key)
        return [f'val entries{depth} = {expr}.entries.sortedWith(Comparator {{ a, b -> {D}compareCanonical(taut.encode({kt._enc(t.key, "a.key")}), taut.encode({kt._enc(t.key, "b.key")})) }})',
                f'for (({key}, {item}) in entries{depth}) {{',
                f'visitor.pushKey({q(t.key.kind)}, taut.encode({enc}))',
                *visit(t.value, item, depth+1), 'visitor.pop()', '}']
    return []


def emit_types(schema, *, forward_compat=False, validation=False, external_types=None, identity=None):
    if type(validation) is not bool:
        raise ValueError('Kotlin validation option must be Boolean')
    errors = check_rules(schema)
    if errors:
        raise ValueError('; '.join(errors))
    external = external_types or {}
    imported = imports(schema, external_types)
    from ..ir.validate import validate_or_raise
    validate_or_raise(schema, targets=('kotlin',))
    facts = schema_json(schema)
    identity = identity or 'schema_' + hashlib.sha256(json.dumps(facts, sort_keys=True).encode()).hexdigest()[:16]
    helper = '_TautMetadata_' + hashlib.sha256(identity.encode()).hexdigest()[:16]
    facade = 'TautSchema_' + helper.removeprefix('_TautMetadata_')
    reserved = {'descriptor', 'tautBinding', 'TAUT_DESCRIPTOR_CONTRACT', 'TAUT_CODEC_CONTRACT', 'TAUT_OWNER', 'TAUT_FACTS_FINGERPRINT'}
    for name in set(schema.messages) | set(schema.enums):
        if name in {'validation', helper, facade} or (validation and name == '_TautValidationEngine'):
            raise ValueError(f'Kotlin generated symbol collision: type {name}')
    for m in schema.messages.values():
        for f in m.fields:
            if f.name in reserved or (validation and f.name in {'validate', 'isValid', '_TautValidationEngine'}):
                raise ValueError(f'Kotlin generated symbol collision: {m.name}.{f.name}')
    for e in schema.enums.values():
        bad = set(e.members) & (reserved | {'wire', 'Companion', 'name', 'ordinal', 'values', 'valueOf', 'entries', 'fromWire'})
        if bad:
            raise ValueError(f'Kotlin generated enum symbol collision: {e.name}.{sorted(bad)[0]}')
    out = ['// GENERATED Kotlin; kotlin-oneof-reference.1; descriptor=1; codec=1; owner=taut.kotlin.foundation',
           f'@file:kotlin.jvm.JvmName({q(facade)})', 'package taut', '', *imported,
           *(['import taut.validation.ValidationEngine as _TautValidationEngine'] if validation else []), '']
    for name, enum in schema.enums.items():
        if name in external: continue
        companion = [f'        val TAUT_DESCRIPTOR_CONTRACT = 1', '        val TAUT_CODEC_CONTRACT = 1',
                     '        val TAUT_OWNER = "taut.kotlin.foundation"',
                     f'        val TAUT_FACTS_FINGERPRINT = {q(fingerprint(schema,name))}',
                     f'        fun descriptor(): {D}EnumDescriptor {{ {helper}.checkCompatibility(); return {helper}.enum_{name} }}']
        out += kt._emit_enum(name, enum.members, companion) + ['']
    for name, m in schema.messages.items():
        if name in external: continue
        companion = ['        val TAUT_DESCRIPTOR_CONTRACT = 1', '        val TAUT_CODEC_CONTRACT = 1',
                     '        val TAUT_OWNER = "taut.kotlin.foundation"',
                     f'        val TAUT_FACTS_FINGERPRINT = {q(fingerprint(schema,name))}',
                     f'        fun descriptor(): {D}MessageDescriptor = tautBinding().descriptor()',
                     f'        fun tautBinding(): {D}SchemaBinding<{kt._id(name)}> = {helper}.binding_{name}']
        out += kt._emit_message(m, kt._bounds(schema,name), forward_compat,
                                companion_lines=companion, validation=validation) + ['']
    out += [f'val TAUT_SCHEMA_{helper.removeprefix("_TautMetadata_")}: {D}SchemaDescriptor get() = {helper}.schema',
            f'private object {helper} {{', 'fun checkCompatibility() {',
            f'{D}Foundation.require({q(identity)}, "taut.kotlin.foundation", 1, 1, listOf("descriptors.v1", "codec.v1", "oneof.v1"))']
    for name in external:
        out += [f'{D}Foundation.require({q(name)}, {kt._id(name)}.TAUT_OWNER, {kt._id(name)}.TAUT_DESCRIPTOR_CONTRACT, {kt._id(name)}.TAUT_CODEC_CONTRACT, listOf("descriptors.v1", "codec.v1", "oneof.v1"))',
                f'if ({kt._id(name)}.TAUT_FACTS_FINGERPRINT != {q(fingerprint(schema,name))}) throw {D}ConfigurationError("Kotlin external {name} facts mismatch; regenerate/rebind child")']
    if validation:
        out += [f'if (taut.validation.ValidationEngine.contract != 1) throw {D}ConfigurationError("Kotlin validation contract mismatch; rebind runtime")']
    out += ['}']
    for name, enum in schema.enums.items():
        if name in external: continue
        members = ', '.join(f'{D}EnumMemberDescriptor({q(k)}, {value(v)})' for k,v in enum.members.items())
        out += [f'val enum_{name}: {D}EnumDescriptor by lazy {{ {D}EnumDescriptor({q(name)}, {q(identity+"."+name)}, listOf({members}), {opts(enum.options)}) }}']
    for name, m in schema.messages.items():
        if name in external: continue
        fields = sorted(m.fields, key=lambda f:f.tag)
        out += [f'val binding_{name}: {D}SchemaBinding<{kt._id(name)}> by lazy {{',
                f'{D}SchemaBinding<{kt._id(name)}>({D}MessageDescriptor({q(name)}, {q(identity+"."+name)}, 1, listOf(']
        for f in fields:
            presence = 'required' if f.optional is False else 'nullable' if f.optional is True else 'missing_ok'
            out += [f'{D}FieldDescriptor({q(f.name)}, {"null" if f.virtual else q(kt._id(f.name))}, {f.tag}, {td(f.type)}, {q(presence)}, {str(f.transient).lower()}, {str(f.virtual).lower()}, {opts(f.options)}),']
        out += ['), listOf(']
        controls = [f for f in fields if f.oneof]
        for f in controls:
            rule = f.oneof
            payload = {c.member:p.name for p in fields for c in p.cases if c.controlling_field==f.name}
            members = ', '.join(f'{D}OneOfMemberDescriptor({q(k)}, {value(v)}, {q(payload[k]) if k in payload else "null"})' for k,v in schema.enums[rule.enum].members.items())
            out += [f'{D}OneOfDescriptor({q(f.name)}, {{ {kt._id(rule.enum)}.descriptor() }}, {str(rule.virtual).lower()}, {str(rule.exhaustive).lower()}, listOf({members})),']
        constraints = ', '.join(f'{D}ConstraintDescriptor({D}ONEOF_RULE, {opts({"controlling_field":f.name})})' for f in controls)
        nums = 'listOf(' + ', '.join(map(str,m.reserved_tags)) + ')'
        names = 'listOf(' + ', '.join(map(q,m.reserved_names)) + ')'
        out += [f'), listOf({constraints}), {nums}, {names}, {"null" if m.next_id is None else m.next_id}, {opts(m.options)}, {opts(effective_map(schema,message=name))}), ::checkCompatibility, {{ value, index ->', 'when(index) {']
        for i,f in enumerate(fields):
            if f.virtual: continue
            expr = 'value.'+kt._id(f.name)
            if isinstance(f.type, EnumRef): expr += '?.wire' if f.optional else '.wire'
            out += [f'{i} -> {expr}']
        out += [f'else -> throw {D}ConfigurationError("{name}: invalid/virtual adapter field")', '}', '}, { value, index, visitor ->']
        for i,f in enumerate(fields):
            if f.virtual or not has_children(f.type): continue
            out += [f'if (index == {i}) {{']
            expr = 'value.' + kt._id(f.name)
            if f.optional:
                out += [f'val child = {expr}', 'if (child != null) {', *visit(f.type,'child'), '}']
            else:
                out += visit(f.type,expr)
            out += ['}']
        out += ['true', '})', '}']
    message_registry = ', '.join(f'{q(name)} to {kt._id(name)}.tautBinding().rawDescriptor' for name in schema.messages)
    enum_registry = ', '.join(f'{q(name)} to {kt._id(name)}.descriptor()' for name in schema.enums)
    out += [f'val schema: {D}SchemaDescriptor by lazy {{', 'checkCompatibility()',
            f'{D}SchemaDescriptor(1, {facts["version"]}, {q(identity)}, mapOf({message_registry}), mapOf({enum_registry}), {opts(schema.options)}, {opts(effective_map(schema))})', '}', '}']
    return '\n'.join(out) + '\n'
