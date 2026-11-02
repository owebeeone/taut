"""Native JavaScript static descriptor values and generated access attachments."""
from __future__ import annotations
import hashlib
import json
import re
from . import js
from ..facts import Scalar, EnumRef, MsgRef, ListOf, MapOf, MISSING_OK
from ..ir.export import schema_json


def q(value):
    return json.dumps(value, ensure_ascii=True)


def literal(value):
    if value is None: return 'null'
    if type(value) is bool: return str(value).lower()
    if type(value) is str: return q(value)
    if type(value) is int: return str(value) if abs(value) <= 2**53-1 else str(value)+'n'
    if type(value) is float: return repr(value)
    if isinstance(value, (tuple,list,bytes)): return '['+', '.join(map(literal,value))+']'
    if hasattr(value, 'items'): return 'Object.fromEntries(['+', '.join('['+q(k)+', '+literal(v)+']' for k,v in value.items())+'])'
    raise ValueError(f'unsupported JS metadata {value!r}')


def fingerprint(value):
    if 'fields' in value and 'name' in value:
        value = dict(value, fields=[dict(f) for f in sorted(value['fields'], key=lambda f:f['tag'])])
        for f in value['fields']:
            if 'cases' in f: f['cases'] = sorted(f['cases'], key=lambda c:(c['controlling_field'],c['enum'],c['member']))
    return hashlib.sha256(json.dumps(value,sort_keys=True,default=dict).encode()).hexdigest()


def preflight(schema, validation, external):
    from ..ir.validate import validate
    errors = validate(schema, targets=('js',))
    declared = set(schema.messages)|set(schema.enums)
    if set(external)-declared: errors.append(f'unknown JavaScript external types {sorted(set(external)-declared)}')
    for name in declared:
        if not re.fullmatch(r'[A-Za-z_$][A-Za-z0-9_$]*', js._type_name(name)):
            errors.append(f'{name}: unsupported JavaScript type identifier')
        if js._type_name(name).startswith('$taut'):
            errors.append(f'{name}: generated runtime identifier collision')
    for m in schema.messages.values():
        for f in m.fields:
            if validation and f.name in ('validate','isValid'):
                errors.append(f'{m.name}.{f.name}: field collides with enabled validation method')
    def refs(t):
        if isinstance(t,(MsgRef,EnumRef)): return {t.name}
        if isinstance(t,ListOf): return refs(t.elem)
        if isinstance(t,MapOf): return refs(t.key)|refs(t.value)
        return set()
    for name,b in external.items():
        if not isinstance(b,dict) or b.keys()-{'module','export'} or not isinstance(b.get('module'),str) or not b['module'] or not re.fullmatch(r'[A-Za-z_$][A-Za-z0-9_$]*',b.get('export',name)):
            errors.append(f'{name}: JS external binding requires module and optional export identifier')
        if name in schema.messages:
            missing=set().union(*(refs(f.type) for f in schema.messages[name].fields))-external.keys()
            if missing: errors.append(f'{name}: JS external dependency graph requires mappings for {sorted(missing)}')
    if errors: raise ValueError('; '.join(errors))


def emit_types(schema, *, forward_compat=False, validation=False, external_types=None,
               identity=None, runtime_module='.'):
    if type(validation) is not bool: raise TypeError('JS validation must be Boolean')
    external = dict(external_types or {})
    preflight(schema,validation,external)
    doc = schema_json(schema)
    identity = identity or 'schema_'+fingerprint(doc)[:16]
    out = ['"use strict";', '// GENERATED native JavaScript types + codec; mandatory descriptor ABI 1.',
           f'const $tautCodec = require({q(runtime_module+"/cbor.js")});',
           f'const {{ {", ".join(js._IMPORTS)} }} = $tautCodec;',
           f'const $tautD = require({q(runtime_module+"/descriptors.js")});',
           f'const $tautC = require({q(runtime_module+"/contracts.js")});',
           f'$tautC.requireContract({q(identity)}, "taut.javascript.foundation", 1, 1, ["codec.v1", "descriptors.v1", "oneof.v1"]);',
           'if (typeof $tautD.requireCodec !== "function") throw new $tautC.ConfigurationError("compatible JavaScript codec/descriptor foundation required; regenerate/rebind");',
           '$tautD.requireCodec($tautCodec);']
    if validation:
        out += [f'const $tautV = require({q(runtime_module+"/validation.js")});',
                'if ($tautV.engineContract !== 1 || $tautV.engineOwner !== $tautC.ownerToken || typeof $tautV.validateRecord !== "function" || typeof $tautV.isRecordValid !== "function") throw new $tautC.ConfigurationError("incompatible JavaScript validation engine/owner; regenerate/rebind");']
    exports=[]
    for i,(name,b) in enumerate(external.items()):
        n=js._type_name(name); ex=b.get('export',name)
        out.append(f'const $tautX{i} = require({q(b["module"])});')
        out.append(f'const {n} = $tautX{i}[{q(ex)}];')
        out.append(f'const {n}Descriptor = $tautX{i}[{q(ex+"Descriptor")}];')
        if name in schema.enums:
            out += [f'const {n}FromCbor = $tautX{i}[{q(ex+"FromCbor")}];',
                    f'const {n}FromWire = $tautX{i}[{q(ex+"FromWire")}];']
    for e in schema.enums.values():
        n=js._type_name(e.name)
        if e.name not in external: out += js._emit_enum(n,e.members)+['']
        exports += [(e.name,n),(e.name+'FromWire',n+'FromWire'),(e.name+'FromCbor',n+'FromCbor'),(e.name+'Descriptor',n+'Descriptor')]
    for m in schema.messages.values():
        n=js._type_name(m.name)
        if m.name not in external: out += js._emit_message(schema,m,forward_compat,validation=validation)+['']
        exports += [(m.name,n),(m.name+'Descriptor',n+'Descriptor')]
    def td(t):
        if isinstance(t,Scalar): args=[q(t.kind)]
        elif isinstance(t,(MsgRef,EnumRef)): args=[q('message' if isinstance(t,MsgRef) else 'enum'),q(t.name)]
        elif isinstance(t,ListOf): args=['"list"','null',td(t.elem)]
        elif isinstance(t,MapOf): args=['"map"','null','null',td(t.key),td(t.value)]
        else: raise TypeError(t)
        return 'new $tautD.TypeDescriptor('+', '.join(args)+')'
    for e,ed in zip(schema.enums.values(),doc['enums']):
        n=js._type_name(e.name)
        if e.name not in external:
            members='Object.fromEntries(['+', '.join('['+q(k)+', '+str(v)+'n]' for k,v in e.members.items())+'])'
            out.append(f'const {n}Descriptor = new $tautD.EnumDescriptor('+', '.join([q(e.name),q(identity+'.'+e.name),members,literal(e.options),literal(ed['member_options']),q(fingerprint(ed))])+');')
    for m,md in zip(schema.messages.values(),doc['messages']):
        n=js._type_name(m.name)
        if m.name in external: continue
        fields=[];groups=[];constraints=[]
        for f in sorted(m.fields,key=lambda f:f.tag):
            presence='missing_ok' if f.optional==MISSING_OK else 'nullable' if f.optional else 'required'
            fields.append('new $tautD.FieldDescriptor('+', '.join([q(f.name),'null' if f.virtual else q(f.name),str(f.tag),td(f.type),q(presence),literal(f.transient),literal(f.virtual),literal(f.options)])+')')
            if f.oneof:
                r=f.oneof;members={k:None for k in schema.enums[r.enum].members}
                for p in m.fields:
                    for c in p.cases:
                        if c.controlling_field==f.name: members[c.member]=p.name
                groups.append('new $tautD.OneOfDescriptor('+', '.join([q(f.name),js._type_name(r.enum)+'Descriptor',literal(r.virtual),literal(r.exhaustive),literal(members)])+')')
                constraints.append('new $tautD.ConstraintDescriptor("taut.oneof.v1", '+literal({'controlling_field':f.name})+')')
        out.append(f'const {n}Descriptor = new $tautD.MessageDescriptor('+', '.join([q(m.name),q(identity+'.'+m.name),'1','['+', '.join(fields)+']','['+', '.join(groups)+']','['+', '.join(constraints)+']',literal(m.reserved_tags),literal(m.reserved_names),literal(m.next_id),literal(m.options),literal(md['effective']),q(fingerprint(md))])+');')
    for name,b in external.items():
        d = next(v for v in doc['messages']+doc['enums'] if v['name']==name)
        expected = 'MessageDescriptor' if name in schema.messages else 'EnumDescriptor'
        out.append(f'if (!({js._type_name(name)}Descriptor instanceof $tautD.{expected}) || {js._type_name(name)}Descriptor.fingerprint !== {q(fingerprint(d))}) throw new $tautC.ConfigurationError({q(name+": missing/old/split-owner or incompatible external descriptor; regenerate/rebind")});')
    def mapping(items): return 'Object.fromEntries(['+', '.join('['+q(k)+', '+v+']' for k,v in items)+'])'
    out.append('const $tautSchema = new $tautD.SchemaDescriptor('+', '.join(['1',str(doc['version']),q(identity),mapping((n,js._type_name(n)+'Descriptor') for n in schema.messages),mapping((n,js._type_name(n)+'Descriptor') for n in schema.enums),literal(schema.options),literal(doc['effective'])])+');')
    adapters=[]; extbindings=[]
    for name,m in schema.messages.items():
        if name in external:
            i=list(external).index(name)
            adapters.append((name,f'$tautX{i}.$tautBinding.adapters[{q(name)}]'))
            extbindings.append((name,f'$tautX{i}.$tautBinding'))
        else:
            reads=mapping((f.name,'($self) => $self['+q(f.name)+']') for f in m.fields if not f.virtual)
            adapters.append((name,'{type:'+js._type_name(name)+', read:'+reads+'}'))
    out.append('const $tautBinding = new $tautD.SchemaBinding($tautSchema, '+mapping(adapters)+', '+mapping(extbindings)+');')
    exports += [('$tautBinding','$tautBinding'),('$tautSchema','$tautSchema')]
    out.append('module.exports = Object.freeze('+mapping(exports)+');')
    return '\n'.join(out)+'\n'
