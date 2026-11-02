"""Rust immutable metadata and safe typed adapters from the native compiler IR."""
from __future__ import annotations
import hashlib
import json
import re
from collections.abc import Mapping

from ..ir.export import schema_json
from ..ir.model import Scalar, MsgRef, EnumRef, ListOf, MapOf
from ..ir.options import effective_map
from . import rust
from .rust_external import imports
from ..rules import check_rules

KEYWORDS = set('as break const continue crate else enum extern false fn for if impl in let loop match mod move mut pub ref return self Self static struct super trait true type unsafe use where while async await dyn abstract become box do final macro override priv typeof unsized virtual yield try gen'.split())
METADATA_NAMES = set('OptionValue Options TypeDescriptor FieldDescriptor EnumMemberDescriptor EnumDescriptor OneOfMemberDescriptor OneOfDescriptor ConstraintDescriptor MessageDescriptor SchemaDescriptor SchemaBinding FieldState PrimitiveValue KeyRef ChildVisitor RecordAccess Bound FoundationOwner'.split())


def field_id(name):
    return rust._field_name(name)


def quoted(value):
    return re.sub(r'\\u([0-9a-fA-F]{4})', r'\\u{\1}', json.dumps(value, ensure_ascii=False))


def option(value):
    if value is None:
        return "OptionValue::Null"
    if type(value) is bool:
        return "OptionValue::Bool(" + str(value).lower() + ")"
    if type(value) is int:
        return f"OptionValue::Int({value})"
    if type(value) is float:
        return f"OptionValue::Float({value!r})"
    if type(value) is str:
        return f"OptionValue::String({quoted(value)})"
    if type(value) is bytes:
        return "OptionValue::Bytes(&[" + ", ".join(map(str, value)) + "])"
    if isinstance(value, Mapping):
        return "OptionValue::Map(" + options(value) + ")"
    if isinstance(value, (list, tuple)):
        return "OptionValue::List(&[" + ", ".join(option(v) for v in value) + "])"
    raise TypeError(f"unsupported Rust metadata {value!r}")


def options(values):
    return "&[" + ", ".join(f"({quoted(k)}, {option(v)})" for k, v in values.items()) + "]"


def type_descriptor(t):
    if isinstance(t, Scalar):
        return "TypeDescriptor::" + {"int": "Int", "str": "String", "bool": "Bool", "bytes": "Bytes", "float": "Float"}[t.kind]
    if isinstance(t, (EnumRef, MsgRef)):
        return f"TypeDescriptor::{'Enum' if isinstance(t, EnumRef) else 'Message'}({t.name}::descriptor)"
    if isinstance(t, ListOf):
        return f"TypeDescriptor::List(&{type_descriptor(t.elem)})"
    if isinstance(t, MapOf):
        return f"TypeDescriptor::Map(&{type_descriptor(t.key)}, &{type_descriptor(t.value)})"
    raise TypeError(t)


def fingerprint(schema, name):
    data = schema_json(schema)
    kind = "messages" if name in schema.messages else "enums"
    # Qualified registry identities do not change portable per-type facts.
    record = next(item for item in data[kind] if item['name'] == name)
    if kind == 'messages':
        # Publication is ordered by schema field number, not author declaration
        # order; equivalent dependency facts must not become a false mismatch.
        record['fields'].sort(key=lambda field: field['tag'])
        for field in record['fields']:
            if 'cases' in field:
                field['cases'].sort(key=lambda case: (case['controlling_field'],case['enum'],case['member']))
    return hashlib.sha256(json.dumps(record, sort_keys=True).encode()).hexdigest()


def has_children(t):
    return isinstance(t, MsgRef) or (isinstance(t, ListOf) and has_children(t.elem)) or (isinstance(t, MapOf) and has_children(t.value))


def visit(t, expr, depth=0):
    if isinstance(t, MsgRef):
        return [f"if !visitor.record(&{t.name}::taut_binding().bind({expr})) {{ return false; }}"]
    if isinstance(t, ListOf) and has_children(t.elem):
        v = f"item{depth}"
        collection = expr.removeprefix('&')
        return [f"for (index{depth}, {v}) in {collection}.iter().enumerate() {{", f"visitor.push_index(index{depth});",
                *visit(t.elem, v, depth + 1), "visitor.pop();", "}"]
    if isinstance(t, MapOf) and has_children(t.value):
        k, v = f"key{depth}", f"item{depth}"
        key = {"str": f"KeyRef::String({k})", "int": f"KeyRef::Int(*{k})", "bool": f"KeyRef::Bool(*{k})"}[t.key.kind]
        collection = expr.removeprefix('&')
        return [f"let mut entries{depth}: Vec<_> = {collection}.iter().map(|({k}, {v})| ({key}.canonical_bytes(), {k}, {v})).collect();",
                f"entries{depth}.sort_by(|a, b| a.0.cmp(&b.0));", f"for (_, {k}, {v}) in entries{depth} {{",
                f"visitor.push_key({key});", *visit(t.value, v, depth + 1), "visitor.pop();", "}"]
    return []


def emit_metadata(schema, *, validation=False, external_types=None, identity=None, runtime_path="crate"):
    external = external_types or {}
    imports(schema, external_types)  # validate all supplied names/paths before use
    def references(t):
        if isinstance(t, (MsgRef, EnumRef)):
            return {t.name}
        if isinstance(t, ListOf):
            return references(t.elem)
        if isinstance(t, MapOf):
            return references(t.key) | references(t.value)
        return set()
    for name in external:
        if name in schema.messages:
            missing = set().union(*(references(f.type) for f in schema.messages[name].fields)) - external.keys()
            if missing:
                raise ValueError(f"Rust external {name} requires ownership mappings for {sorted(missing)}; bind the full dependency type graph")
    facts = schema_json(schema)
    identity = identity or "schema_" + hashlib.sha256(json.dumps(facts, sort_keys=True).encode()).hexdigest()[:16]
    d, v = runtime_path + "::cbor::descriptors", runtime_path + "::validation"
    capabilities = ['descriptors.v1','codec.v1']
    if any(f.oneof or f.cases for m in schema.messages.values() for f in m.fields):
        capabilities.append('oneof.v1')
    out = [f"// Generator build rust-oneof-reference.1; descriptor=1; codec=1; owner=taut.rust.foundation",
           f"const _: () = assert!({d}::DESCRIPTOR_CONTRACT == 1, \"Taut descriptor contract mismatch: rebind runtime\");",
           f"const _: () = assert!({d}::CODEC_CONTRACT == 1, \"Taut codec contract mismatch: rebind runtime\");"]
    if validation:
        out += [f"const _: () = assert!({v}::VALIDATION_CONTRACT == 1, \"Taut validation engine contract mismatch: rebind runtime\");"]
    for name in external:
        out += [f"const _: fn() -> &'static {d}::{'SchemaBinding<' + name + '>' if name in schema.messages else 'EnumDescriptor'} = {name}::{'taut_binding' if name in schema.messages else 'descriptor'};",
                f"const _: () = assert!({name}::TAUT_DESCRIPTOR_CONTRACT == 1 && {name}::TAUT_CODEC_CONTRACT == 1, \"Taut child {name} contract mismatch: regenerate/rebind child\");"]
    for name in schema.enums:
        if name in external:
            continue
        out += [f"impl {name} {{", "pub const TAUT_DESCRIPTOR_CONTRACT: u32 = 1;", "pub const TAUT_CODEC_CONTRACT: u32 = 1;",
                f"pub const TAUT_FACTS_FINGERPRINT: &'static str = {quoted(fingerprint(schema, name))};",
                f"pub fn descriptor() -> &'static {d}::EnumDescriptor {{ let descriptor = _taut_metadata::ENUM_{name}; descriptor.check(); descriptor }}", "}"]
    for name in schema.messages:
        if name in external:
            continue
        out += [f"impl {name} {{", "pub const TAUT_DESCRIPTOR_CONTRACT: u32 = 1;", "pub const TAUT_CODEC_CONTRACT: u32 = 1;",
                f"pub const TAUT_FACTS_FINGERPRINT: &'static str = {quoted(fingerprint(schema, name))};",
                f"pub fn descriptor() -> &'static {d}::MessageDescriptor {{",
                f"_taut_metadata::BINDING_{name}.descriptor()", "}",
                f"pub fn taut_binding() -> &'static {d}::SchemaBinding<Self> {{ _taut_metadata::BINDING_{name} }}"]
        if validation:
            out += [f"pub fn validate(&self) -> {v}::ValidationReport {{ self.validate_with_options(Default::default()) }}",
                    f"pub fn validate_with_options(&self, options: {v}::ValidationOptions) -> {v}::ValidationReport {{ {v}::validate_record(&Self::taut_binding().bind(self), options) }}",
                    "pub fn is_valid(&self) -> bool { self.is_valid_with_options(Default::default()) }",
                    f"pub fn is_valid_with_options(&self, options: {v}::ValidationOptions) -> bool {{ {v}::is_record_valid(&Self::taut_binding().bind(self), options) }}"]
        out += ["}"]
    out += [f"pub static SCHEMA_DESCRIPTOR: &{d}::SchemaDescriptor = &{d}::SchemaDescriptor::new(1, {facts['version']}, {quoted(identity)},",
            "&[" + ", ".join(n + "::descriptor" for n in schema.messages) + "],",
            "&[" + ", ".join(n + "::descriptor" for n in schema.enums) + "],",
            "_taut_metadata::FILE_OPTIONS, _taut_metadata::FILE_EFFECTIVE);"]
    out += ["#[allow(non_upper_case_globals, unused_variables, unused_imports)]", "mod _taut_metadata {", "use super::*;",
            f"use {d}::*;", f"pub const FILE_OPTIONS: Options = {options(schema.options)};",
            f"pub const FILE_EFFECTIVE: Options = {options(effective_map(schema))};", "pub fn check_external() {",
            f"require_contract({quoted(identity)}, \"taut.rust.foundation\", 1, 1, &[" + ', '.join(map(quoted,capabilities)) + "]);"]
    for name in external:
        out += [f"assert_eq!({name}::TAUT_FACTS_FINGERPRINT, {quoted(fingerprint(schema, name))}, \"Taut external {name} facts mismatch: regenerate/rebind child\");",
                f"{name}::descriptor().check();"]
    out += ["}"]
    for name, e in schema.enums.items():
        if name in external:
            continue
        members = ", ".join(f"EnumMemberDescriptor::new({quoted(m)}, {n}, &[])" for m, n in e.members.items())
        out += [f"pub static ENUM_{name}: &EnumDescriptor = &EnumDescriptor::new({quoted(name)}, {quoted(identity + '.' + name)}, &[{members}], {options(e.options)});"]
    for name, m in schema.messages.items():
        if name in external:
            continue
        fields = sorted(m.fields, key=lambda f: f.tag)
        out += [f"pub static BINDING_{name}: &SchemaBinding<{name}> = &SchemaBinding::new(MessageDescriptor::new({quoted(name)}, {quoted(identity + '.' + name)}, 1, &["]
        for f in fields:
            attr = "None" if f.virtual else f"Some({quoted(field_id(f.name))})"
            presence = "required" if f.optional is False else "nullable" if f.optional is True else "missing_ok"
            out += [f"FieldDescriptor::new({quoted(f.name)}, {attr}, {f.tag}, {type_descriptor(f.type)}, {quoted(presence)}, {str(f.transient).lower()}, {str(f.virtual).lower()}, {options(f.options)}),"]
        out += ["], &["]
        controls = [f for f in fields if f.oneof]
        for f in controls:
            r = f.oneof
            payloads = {c.member: p.name for p in fields for c in p.cases if c.controlling_field == f.name}
            members = ", ".join(f"OneOfMemberDescriptor::new({quoted(k)}, {n}, " + (f"Some({quoted(payloads[k])})" if k in payloads else "None") + ")" for k, n in schema.enums[r.enum].members.items())
            out += [f"OneOfDescriptor::new({quoted(f.name)}, {r.enum}::descriptor, {str(r.virtual).lower()}, {str(r.exhaustive).lower()}, &[{members}]),"]
        constraints = ", ".join(f"ConstraintDescriptor::new(ONEOF_RULE, {options({'controlling_field': f.name})})" for f in controls)
        numbers = "&[" + ", ".join(map(str, m.reserved_tags)) + "]"
        names = "&[" + ", ".join(map(quoted, m.reserved_names)) + "]"
        out += [f"], &[{constraints}], {numbers}, {names}, {'None' if m.next_id is None else f'Some({m.next_id})'}, {options(m.options)}, {options(effective_map(schema, message=name))}), check_external, |value, index| {{"]
        if fields:
            out += ["match index {"]
        for index, f in enumerate(fields):
            if f.virtual:
                state = "FieldState::new(false, None)"
            elif isinstance(f.type, Scalar):
                kind = {'int':'Int','str':'String','bool':'Bool','bytes':'Bytes','float':'Float'}[f.type.kind]
                if f.optional:
                    expression = 'v' if f.type.kind in ('str','bytes') else '*v'
                    state = f"match &value.{field_id(f.name)} {{ Some(v) => FieldState::from_primitive(PrimitiveValue::{kind}({expression})), None => FieldState::new(false, None) }}"
                else:
                    expression = ('&' if f.type.kind in ('str','bytes') else '') + f'value.{field_id(f.name)}'
                    state = f"FieldState::from_primitive(PrimitiveValue::{kind}({expression}))"
            else:
                present = f"value.{field_id(f.name)}.is_some()" if f.optional else "true"
                tag = f"value.{field_id(f.name)}.as_ref().map(|v| v.wire())" if f.optional else f"Some(value.{field_id(f.name)}.wire())"
                state = f"FieldState::new({present}, {tag if isinstance(f.type, EnumRef) else 'None'})"
            out += [f"{index} => {state},"]
        if fields:
            out += ["_ => panic!(\"Taut typed binding field mismatch: regenerate artifact\"),", "}"]
        else:
            out += ["panic!(\"Taut typed binding field mismatch: regenerate artifact\")"]
        out += ["}, |value, index, visitor| {"]
        for index, f in enumerate(fields):
            if f.virtual or not has_children(f.type):
                continue
            out += [f"if index == {index} {{"]
            if f.optional:
                out += [f"if let Some(child) = &value.{field_id(f.name)} {{", *visit(f.type, "child"), "}"]
            else:
                out += visit(f.type, f"&value.{field_id(f.name)}")
            out += ["}"]
        out += ["true });"]
    out += ["}"]
    return "\n".join(out) + "\n"


def emit_types(schema, *, validation=False, external_types=None, identity=None, runtime_path="crate", forward_compat=False):
    errors = check_rules(schema)
    if errors:
        raise ValueError("; ".join(errors))
    external = external_types or {}
    for name in set(schema.messages) | set(schema.enums):
        if name in KEYWORDS or name in METADATA_NAMES or name in {'_', 'alloc', '_taut_metadata', 'SCHEMA_DESCRIPTOR'} or name in rust.RESERVED_TYPE_NAMES:
            raise ValueError(f'Rust generated symbol collision: type {name}')
    for enum in schema.enums.values():
        variants = [rust._variant(member) for member in enum.members]
        if len(variants) != len(set(variants)) or any(v in KEYWORDS or not v for v in variants):
            raise ValueError(f'Rust generated enum variant collision: {enum.name}')
    from ..ir.validate import validate_or_raise
    validate_or_raise(schema, targets=('rust',))
    graph = {name: {f.type.name for f in m.fields if isinstance(f.type, MsgRef) and not f.virtual} for name, m in schema.messages.items()}
    dangling = set().union(*graph.values()) - set(graph) if graph else set()
    if dangling:
        raise ValueError(f"Rust dangling message references {sorted(dangling)}; supply the full dependency schema")
    def reaches(start, target, visited=None):
        visited = set() if visited is None else visited
        if start == target:
            return True
        if start in visited:
            return False
        visited.add(start)
        return any(reaches(child, target, visited) for child in graph[start])
    out = ["// GENERATED native Rust types + codec — do not edit.", "#![allow(dead_code, clippy::redundant_closure, clippy::needless_question_mark, clippy::collapsible_if)]",
           "extern crate alloc;", "#[allow(unused_imports)]", "use alloc::{boxed::Box, string::String, vec, vec::Vec};", f"use {runtime_path}::cbor::{{Cbor, DecodeError}};"]
    out += imports(schema, external)
    out += rust._emit_file_bounds(schema)
    for e in schema.enums.values():
        if e.name not in external:
            out += rust._emit_enum(e.name, e.members)
    for m in schema.messages.values():
        if m.name not in external:
            boxed = {f.name for f in m.fields if isinstance(f.type, MsgRef) and reaches(f.type.name, m.name)}
            out += rust._emit_message(m, schema, forward_compat, boxed_fields=boxed)
    body = "\n".join(out).replace("std::collections::", "alloc::collections::")
    if runtime_path != "crate":
        body = body.replace("crate::cbor::", runtime_path + "::cbor::")
    return body + "\n" + emit_metadata(schema, validation=validation, external_types=external,
                  identity=identity, runtime_path=runtime_path)
