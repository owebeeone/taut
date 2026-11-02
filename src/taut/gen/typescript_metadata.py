"""Native TypeScript projection, immutable descriptor values and typed readers."""
from __future__ import annotations
import hashlib
import json
import re
from collections.abc import Mapping
from ..ir.export import schema_json
from ..ir.model import Scalar, EnumRef, MsgRef, ListOf, MapOf
from ..ir.options import effective_map
from .kotlin_metadata import fingerprint


def q(value):
    return json.dumps(value, ensure_ascii=True)


def value(v):
    if isinstance(v, Mapping):
        return '{' + ','.join('['+q(k)+']:'+value(x) for k,x in v.items()) + '}'
    if isinstance(v, (tuple,list)):
        return '[' + ','.join(value(x) for x in v) + ']'
    if isinstance(v,bytes):
        return 'new Uint8Array(' + value(list(v)) + ')'
    return json.dumps(v,ensure_ascii=True,allow_nan=False)


def ty(t, message_types=None):
    if isinstance(t,Scalar): return {'int':'bigint','str':'string','bool':'boolean','bytes':'globalThis.Uint8Array','float':'number'}[t.kind]
    if isinstance(t,MsgRef): return (message_types or {}).get(t.name,t.name)
    if isinstance(t,EnumRef): return t.name
    if isinstance(t,ListOf): return f'globalThis.Array<{ty(t.elem,message_types)}>'
    if isinstance(t,MapOf): return f'globalThis.Map<{ty(t.key,message_types)}, {ty(t.value,message_types)}>'
    raise TypeError(t)


def td(t):
    if isinstance(t,Scalar): return '{kind:'+q(t.kind)+'}'
    if isinstance(t,MsgRef): return '{kind:"message", binding:()=>'+t.name+'Binding}'
    if isinstance(t,EnumRef): return '{kind:"enum", enum:()=>'+t.name+'Descriptor}'
    if isinstance(t,ListOf): return '{kind:"list", element:'+td(t.elem)+'}'
    if isinstance(t,MapOf): return '{kind:"map", key:'+td(t.key)+', value:'+td(t.value)+'}'
    raise TypeError(t)


def data_type(t, *, validation=False, external_types=None, namespace='api'):
    """Truthful codec/transport data projection; never promise constructed methods."""
    if t is None:return 'void'
    if isinstance(t,MsgRef):return namespace+'.'+t.name+('Fields' if validation and t.name not in (external_types or {}) else '')
    if isinstance(t,EnumRef):return namespace+'.'+t.name
    if isinstance(t,ListOf):return 'globalThis.Array<'+data_type(t.elem,validation=validation,external_types=external_types,namespace=namespace)+'>'
    if isinstance(t,MapOf):return 'globalThis.Map<'+data_type(t.key,validation=validation,external_types=external_types,namespace=namespace)+', '+data_type(t.value,validation=validation,external_types=external_types,namespace=namespace)+'>'
    return ty(t)


def module_specifier(module):
    if not isinstance(module,str) or not module or '\\' in module or any(ord(c)<32 for c in module):
        raise ValueError(f'invalid TypeScript module specifier {module!r}')
    return module


def emit_types(schema, *, forward_compat=False, validation=False, external_types=None,
               identity=None, runtime_module='./foundation.ts', validation_module='./validation.ts'):
    from ..ir.validate import validate_or_raise
    validate_or_raise(schema,targets=('typescript',))
    if type(validation) is not bool: raise TypeError('TypeScript validation must be Boolean')
    module_specifier(runtime_module); module_specifier(validation_module)
    facts=schema_json(schema)
    identity=identity or 'schema_'+hashlib.sha256(json.dumps(facts,sort_keys=True).encode()).hexdigest()[:16]
    external=dict(external_types or {})
    known=set(schema.messages)|set(schema.enums)
    if external.keys()-known: raise ValueError(f'unknown TypeScript external types {sorted(external.keys()-known)}')
    def references(t):
        if isinstance(t,(MsgRef,EnumRef)):return {t.name}
        if isinstance(t,ListOf):return references(t.elem)
        if isinstance(t,MapOf):return references(t.key)|references(t.value)
        return set()
    for name in external:
        if name in schema.messages:
            missing=set().union(*(references(f.type) for f in schema.messages[name].fields))-external.keys()
            if missing:raise ValueError(f'TypeScript external {name} requires mappings for {sorted(missing)}; bind full dependency graph')
    message_types={name:name+'Fields' for name in schema.messages if validation and name not in external}
    symbols={'SchemaDescriptor','SCHEMA_DESCRIPTOR','CODEC_SCHEMA','globalThis'}
    keywords=set('break case catch class const continue debugger default delete do else enum export extends false finally for function if import in instanceof new null return super switch this throw true try typeof var void while with as implements interface let package private protected public static yield any boolean constructor declare get module require number set string symbol type from of unknown never bigint object undefined'.split())
    generated=[]
    for name in known:
        if not re.fullmatch(r'[A-Za-z_$][A-Za-z0-9_$]*',name) or name in keywords or name.startswith('_taut'):
            raise ValueError(f'TypeScript generated type name collision: {name}')
        if validation and name=='Object' and name in schema.messages:
            raise ValueError('TypeScript generated class symbol collision: Object (tsc CommonJS intrinsic)')
        generated.extend([name,name+'Descriptor'])
        if name in schema.messages: generated.extend([name+'Binding',name+'Fields'])
    if len(set(generated))!=len(generated) or symbols.intersection(generated): raise ValueError('TypeScript generated descriptor/fields/binding symbol collision')
    for m in schema.messages.values():
        for f in m.fields:
            if f.name=='__unknown__':raise ValueError(f'TypeScript native codec storage collision: {m.name}.__unknown__')
            if validation and not f.virtual and f.name in {'constructor','validate','isValid'}:
                raise ValueError(f'TypeScript generated class symbol collision: {m.name}.{f.name}')
    out=['// GENERATED TypeScript; typescript-oneof-reference.1; descriptor=1; codec=1; owner=taut.typescript.foundation',
         f'import * as _taut from {q(runtime_module)};']
    if validation: out += [f'import * as _tautEngine from {q(validation_module)};']
    for name,config in sorted(external.items()):
        if isinstance(config,str): config={'module':config}
        if not isinstance(config,dict) or config.keys()-{'module','export','data_export'}: raise ValueError(f'{name}: TypeScript external mapping requires module/export/data_export')
        module=module_specifier(config.get('module')); export=config.get('export',name)
        if not isinstance(export,str) or not re.fullmatch(r'[A-Za-z_$][A-Za-z0-9_$]*',export): raise ValueError(f'{name}: invalid external export')
        # Interface-only children have no constructor import.
        data_export=config.get('data_export',export+'Fields' if name in schema.messages else export)
        if not isinstance(data_export,str) or not re.fullmatch(r'[A-Za-z_$][A-Za-z0-9_$]*',data_export):raise ValueError(f'{name}: invalid external data export')
        out += [f'import type {{ {data_export} as {name} }} from {q(module)};',
                f'export type {{ {name} }};',
                f'import {{ {export}Descriptor as {name}Descriptor'+(f', {export}Binding as {name}Binding' if name in schema.messages else '')+f' }} from {q(module)};']
    out += ['if (typeof _taut.requireFoundation !== "function") throw new globalThis.Error("compatible TypeScript descriptor/codec foundation required; regenerate/rebind runtime");',
            'if (!_taut.Foundation || typeof _taut.Foundation !== "object" || _taut.Foundation.owner !== "taut.typescript.foundation" || _taut.Foundation.descriptorContract !== 1 || _taut.Foundation.codecContract !== 1 || !globalThis.Array.isArray(_taut.Foundation.capabilities) || ["codec.v1", "descriptors.v1", "oneof.v1"].some(c => !_taut.Foundation.capabilities.includes(c))) throw new globalThis.Error("selected TypeScript foundation lacks a valid owner token (incompatible owner/contracts); regenerate/rebind owner");',
            'if (_taut.requireFoundation(_taut) !== _taut.Foundation) throw new _taut.ConfigurationError("selected TypeScript foundation lacks namespace-checked guard support; regenerate/rebind owner");']
    if validation: out += ['if (_tautEngine.ValidationEngine?.contract !== 1 || _tautEngine.ValidationEngine.owner !== _taut.Foundation) throw new _taut.ConfigurationError("incompatible TypeScript validation engine/owner");']
    for name in external:
        out += [f'_taut.requireExternal({name+"Binding" if name in schema.messages else name+"Descriptor"}, {q(fingerprint(schema,name))}, {q(name)}, {q("message" if name in schema.messages else "enum")});']
    for name,e in schema.enums.items():
        if name in external: continue
        out += [f'export type {name} = '+ ' | '.join(q(n) for n in e.members)+';',
                f'export const {name}Descriptor = new _taut.EnumDescriptor({q(name)}, {q(identity+"."+name)}, '+
                '{'+','.join('['+q(k)+']:'+str(v)+'n' for k,v in e.members.items())+'}, '+value(e.options)+', '+value({n:{} for n in e.members})+', '+q(fingerprint(schema,name))+');']
    for name,m in schema.messages.items():
        if name in external: continue
        shape=name+'Fields' if validation else name
        out += [f'export interface {shape} {{']
        for f in m.fields:
            if f.virtual: continue
            optional='?' if f.cases else ''
            field=f.name if re.fullmatch(r'[A-Za-z_$][A-Za-z0-9_$]*',f.name) else q(f.name)
            out += [f'  {field}{optional}: {ty(f.type,message_types)}'+(' | null' if f.optional else '')+';']
        if validation:out += ['  __unknown__?: globalThis.Map<_taut.MapKey, _taut.CborValue>;']
        out += ['}']
        if not validation:out += [f'export type {name}Fields = {name} & {{ __unknown__?: globalThis.Map<_taut.MapKey, _taut.CborValue> }};']
        if validation:
            out += [f'export class {name} {{']
            out += ['  __unknown__?: globalThis.Map<_taut.MapKey, _taut.CborValue>;']
            for f in m.fields:
                if f.virtual: continue
                out += [f'  [{q(f.name)}]'+('?' if f.optional=='missing_ok' and not f.cases else '!')+f': {ty(f.type,message_types)}'+(' | null' if f.optional else '')+';']
            out += [f'  constructor(fields: {shape}) {{']
            for f in m.fields:
                if f.virtual: continue
                expr=f'fields[{q(f.name)}]'
                if f.cases: expr+=' ?? null'
                out += [f'    globalThis.Object.defineProperty(this, {q(f.name)}, {{value: {expr}, writable:true, enumerable:true, configurable:true}});']
            out += ['    if (fields.__unknown__ !== undefined) this.__unknown__ = fields.__unknown__;']
            out += ['  }',f'  validate(options?: _taut.ValidationOptions): _taut.ValidationReport {{ return _tautEngine.validateRecord(this, {name}Binding, options); }}',
                    f'  isValid(options?: _taut.ValidationOptions): boolean {{ return _tautEngine.isRecordValid(this, {name}Binding, options); }}',
                    f'  static descriptor(): _taut.MessageDescriptor {{ return {name}Descriptor; }}','}']
    for name,m in schema.messages.items():
        if name in external: continue
        fields=sorted(m.fields,key=lambda f:f.tag)
        out += [f'export const {name}Descriptor = new _taut.MessageDescriptor({q(name)}, {q(identity+"."+name)}, 1, [']
        for f in fields:
            p='required' if f.optional is False else 'nullable' if f.optional is True else 'missing_ok'
            out += [f'  new _taut.FieldDescriptor({q(f.name)}, {"null" if f.virtual else q(f.name)}, {f.tag}, {td(f.type)}, {q(p)}, {str(f.transient).lower()}, {str(f.virtual).lower()}, {value(f.options)}),']
        out += ['], [']
        controls=[f for f in fields if f.oneof]
        for f in controls:
            r=f.oneof; payload={c.member:p.name for p in fields for c in p.cases if c.controlling_field==f.name}
            out += [f'new _taut.OneOfDescriptor({q(f.name)}, {r.enum}Descriptor, {str(r.virtual).lower()}, {str(r.exhaustive).lower()}, {value({n:payload.get(n) for n in schema.enums[r.enum].members})}),']
        constraints=', '.join('new _taut.ConstraintDescriptor(_taut.ONEOF_RULE, '+value({'controlling_field':f.name})+')' for f in controls)
        out += [f'], [{constraints}], {value(list(m.reserved_tags))}, {value(list(m.reserved_names))}, {value(m.next_id)}, {value(m.options)}, {value(effective_map(schema,message=name))}, {q(fingerprint(schema,name))});',
                f'export const {name}Binding: _taut.MessageBinding<{message_types.get(name,name)}> = new _taut.MessageBinding<{message_types.get(name,name)}>({name}Descriptor, (value, index) => {{', '  switch(index) {']
        for i,f in enumerate(fields):
            if not f.virtual: out += [f'    case {i}: return value[{q(f.name)}];']
        out += ['    default: throw new _taut.ConfigurationError("invalid/virtual typed field access");','  }',
                f'}}, (value:unknown): value is {message_types.get(name,name)} => value !== null && typeof value === "object" && !globalThis.Array.isArray(value) && !(value instanceof globalThis.Map) && !(value instanceof globalThis.Uint8Array));']
    out += [f'export const SCHEMA_DESCRIPTOR = new _taut.SchemaDescriptor({q(identity)}, {facts["version"]}, '+
            '{'+','.join('['+q(n)+']:'+n+'Descriptor' for n in schema.messages)+'}, '+
            '{'+','.join('['+q(n)+']:'+n+'Descriptor' for n in schema.enums)+'}, '+value(schema.options)+', '+value(effective_map(schema))+');',
            '_taut.publish(SCHEMA_DESCRIPTOR, ['+', '.join(n+'Binding' for n in schema.messages)+']);']
    # Native immutable codec facts: application builds never parse authoring files.
    wire_facts={k:facts[k] for k in ('version','options','effective','enums','messages','services')}
    wire_facts['enums']=[dict(e,members={}) for e in facts['enums']]
    wire_facts['messages']=[{k:v for k,v in m.items() if k in {'name','options','effective','fields'}} for m in facts['messages']]
    for m in wire_facts['messages']:
        m['fields']=[{k:v for k,v in f.items() if k!='merge'} for f in m['fields']]
    encoded=value(wire_facts)
    for e in facts['enums']:
        needle='["name"]:'+q(e['name'])+',["options"]:'+value(e['options'])+',["members"]:{}'
        replacement='["name"]:'+q(e['name'])+',["options"]:'+value(e['options'])+',["members"]:{'+','.join('['+q(k)+']:'+str(v)+'n' for k,v in e['members'].items())+'}'
        encoded=encoded.replace(needle,replacement)
    out += ['export const CODEC_SCHEMA = new _taut.schema.SchemaIndex('+encoded+' as _taut.schema.Schema);']
    return '\n'.join(out)+'\n'
