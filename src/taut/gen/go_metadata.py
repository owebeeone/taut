"""Native Go fact tables and captureless typed field adapters."""
from __future__ import annotations
import hashlib
import json
import re
import unicodedata
from pathlib import Path
from . import go
from .go_runtime import OWNER, CAPABILITIES, import_path
from ..facts import Scalar, EnumRef, MsgRef, ListOf, MapOf, MISSING_OK
from ..ir.export import schema_json


def q(value):
    # JSON's surrogate-pair escapes are not legal Go Unicode escapes. Emit
    # scalar Unicode as UTF-8 while retaining JSON/Go quote/control escaping.
    return json.dumps(value, ensure_ascii=False)


def fingerprint(value, *, forward_compat=False):
    value=json.loads(json.dumps(value, default=dict))
    if 'fields' in value:
        value = dict(value, fields=[dict(f) for f in sorted(value['fields'], key=lambda f: f['tag'])])
        for f in value['fields']:
            if 'cases' in f:
                f['cases'] = sorted(f['cases'], key=lambda c: (c['controlling_field'], c['enum'], c['member']))
    if 'messages' in value:
        value = dict(value, messages=sorted(value['messages'], key=lambda x: x['name']), enums=sorted(value['enums'], key=lambda x: x['name']))
        value['messages'] = [dict(m, fields=sorted(m['fields'], key=lambda f: f['tag'])) for m in value['messages']]
        for m in value['messages']:
            for f in m['fields']:
                if 'cases' in f:
                    f['cases'] = sorted(f['cases'], key=lambda c: (c['controlling_field'], c['enum'], c['member']))
    portable=hashlib.sha256(json.dumps(value, sort_keys=True, default=dict).encode()).hexdigest()
    # Residual preservation is an effective codec fact selected outside IR.
    return (hashlib.sha256((portable+':forward_compat='+str(forward_compat)).encode()).hexdigest()
            if 'fields' in value and 'name' in value else portable)


def literal(v):
    if v is None: return 'nil'
    if type(v) is bool: return str(v).lower()
    if type(v) is str: return q(v)
    if type(v) is int: return 'int64('+str(v)+')'
    if type(v) is float: return 'float64('+repr(v)+')'
    if type(v) is bytes: return '[]byte{'+', '.join(map(str,v))+'}'
    if hasattr(v, 'items'): return 'map[string]any{'+', '.join(q(k)+': '+literal(x) for k,x in v.items())+'}'
    if isinstance(v, (tuple,list)): return '[]any{'+', '.join(map(literal,v))+'}'
    raise TypeError(v)


def preflight(schema, validation, external):
    from ..ir.validate import validate
    errors = validate(schema, targets=('go',))
    declared = set(schema.messages) | set(schema.enums)
    if external.keys()-declared: errors.append(f'unknown Go external types {sorted(external.keys()-declared)}')
    def identifier(s):
        return bool(s) and (s[0]=='_' or unicodedata.category(s[0]).startswith('L')) and all(c=='_' or unicodedata.category(c).startswith('L') or unicodedata.category(c)=='Nd' for c in s)
    names = {n: where for n,where,_ in go._package_names(schema)}
    extra = {'DescribeSchema', 'ValidationOptions', 'tautrt', 'tautsort', 'tautbytes'}
    runtime_text = ''.join(p.read_text() for p in (Path(__file__).parent/'runtime'/'go').glob('*.go'))
    runtime_names = set(re.findall(r'^func\s+(\w+)|^type\s+(\w+)|^const\s+(\w+)', runtime_text, re.M))
    extra |= {n for row in runtime_names for n in row if n}
    extra |= {name.rsplit('/',1)[-1] for name in re.findall(r'^\s*"([a-z/]+)"', runtime_text,re.M)}
    for symbol,where,_ in go._package_names(schema):
        if symbol in extra:
            errors.append(f'{where}: Go generated/runtime symbol collision {symbol}')
    for name in declared:
        if not identifier(name) or name in ('break','default','func','interface','select','case','defer','go','map','struct','chan','else','goto','package','switch','const','fallthrough','if','range','type','continue','for','import','return','var'):
            errors.append(f'{name}: invalid Go type identifier')
        if name in extra or name.startswith(('tautdep','tautSchema','tautDesc','tautBind')):
            errors.append(f'{name}: Go generated/runtime symbol collision')
        derived = ['Describe'+name]
        if name in schema.messages: derived += ['TautBinding'+name]
        for symbol in derived:
            if symbol in names or symbol in extra: errors.append(f'{name}: Go generated symbol collision {symbol}')
            extra.add(symbol)
    for m in schema.messages.values():
        reserved = {'Descriptor'} | ({'Validate','ValidateWithOptions','IsValid','IsValidWithOptions'} if validation else set())
        for f in m.fields:
            n=go.field_name(f.name)
            if not identifier(n) or n in reserved: errors.append(f'{m.name}.{f.name}: Go generated field/method collision or invalid identifier {n}')
    for e in schema.enums.values():
        native=[e.name+go._pascal(n) for n in e.members]
        if len(set(native))!=len(native) or not all(identifier(n) for n in native): errors.append(f'{e.name}: Go enum member identifier collision')
    def refs(t):
        if isinstance(t,(MsgRef,EnumRef)): return {t.name}
        if isinstance(t,ListOf): return refs(t.elem)
        if isinstance(t,MapOf): return refs(t.key)|refs(t.value)
        return set()
    for name,b in external.items():
        if not isinstance(b,dict): errors.append(f'{name}: Go external type requires explicit typed artifact binding'); continue
        required={'import_path','type','owner','descriptor_contract','codec_contract','capabilities'}
        try:
            import_path(b.get('import_path'))
            valid = (set(b)==required and b['type']==name and b['owner']==OWNER
                and type(b['descriptor_contract']) is int and b['descriptor_contract']==1
                and type(b['codec_contract']) is int and b['codec_contract']==1
                and isinstance(b['capabilities'],(tuple,list,set)) and set(b['capabilities'])==CAPABILITIES)
        except (TypeError,ValueError): valid=False
        if not valid: errors.append(f'{name}: Go external requires import_path, type={name}, owner={OWNER}, descriptor=1 codec=1 capabilities={sorted(CAPABILITIES)}')
        if name and not name[0].isupper(): errors.append(f'{name}: Go independently imported type must be exported')
        if name in schema.messages:
            needed=set().union(*(refs(f.type) for f in schema.messages[name].fields))
            if needed-external.keys(): errors.append(f'{name}: bind the full Go external dependency graph {sorted(needed-external.keys())}')
    if external and any(not b.get('import_path') for b in external.values() if isinstance(b,dict)): errors.append('Go external dependency import_path required')
    if errors: raise ValueError('; '.join(errors))


def emit_types(schema, *, forward_compat=False, validation=False, external_types=None, identity=None, runtime_import=''):
    if type(validation) is not bool: raise TypeError('Go validation option must be Boolean')
    external = dict(external_types or {})
    preflight(schema, validation, external)
    if not isinstance(runtime_import,str): raise ValueError('Go runtime_import must be a string')
    if runtime_import: import_path(runtime_import)
    if external and not runtime_import: raise ValueError('Go external types require an explicit shared runtime import_path')
    doc=schema_json(schema)
    identity=identity or 'schema_'+fingerprint(doc)[:16]
    suffix=hashlib.sha256(identity.encode()).hexdigest()[:16]
    holder='tautSchema'+suffix
    mn={n:'tautDesc'+suffix+'M'+str(i) for i,n in enumerate(schema.messages)}
    en={n:'tautDesc'+suffix+'E'+str(i) for i,n in enumerate(schema.enums)}
    bn={n:'tautBind'+suffix+'M'+str(i) for i,n in enumerate(schema.messages)}
    r='tautrt.' if runtime_import else ''
    imports={}
    if runtime_import: imports['tautrt']=runtime_import
    paths={b['import_path'] for b in external.values()}
    dep={path:'tautdep'+str(i) for i,path in enumerate(sorted(paths))}
    imports.update({alias:path for path,alias in dep.items()})
    has_maps=any(go._sorts(f.type) for m in schema.messages.values() if m.name not in external for f in m.fields)
    if has_maps: imports.update(tautsort='sort', tautbytes='bytes')
    def seq(ty,values): return '[]'+ty+'{'+', '.join(values)+'}'
    def mapping(ty,values): return 'map[string]'+ty+'{'+', '.join(q(k)+': '+v for k,v in values.items())+'}'
    def qualify(text):
        # Only codec statements go through this token qualification. Portable
        # names/string facts are emitted separately and remain unchanged.
        names=['Cbor','KV','CInt','CText','CBytes','CBool','CFloat','CArr','CMap','CNull','UnknownEnumError','DuplicateMapKeyError','TryDecodeWith']
        if r: text=re.sub(r'\b('+ '|'.join(names)+r')\b',lambda m:r+m[0],text)
        return text.replace('sort.Slice','tautsort.Slice')
    out=['// GENERATED Go codec + mandatory descriptor ABI 1; generator=go-oneof-reference.1', 'package taut','']
    # Native codec bodies stay the original implementation.
    codec=[]
    for e in schema.enums.values():
        if e.name not in external: codec+=go._emit_enum(e.name,e.members)+['']
    for m in schema.messages.values():
        if m.name not in external: codec+=go._emit_message(schema,m,forward_compat)+['']
    out += [qualify('\n'.join(codec))]
    def func(signature, body):
        return [signature+' {', *['\t'+line for line in body], '}', '']
    if validation: out+=['type ValidationOptions = '+r+'ValidationOptions', ''] if r else []
    for name,b in external.items():
        module=dep[b['import_path']]
        out+=['type '+name+' = '+module+'.'+b['type'], '']
        out+=func(f'func Try{name}FromCbor(c {r}Cbor) ({name}, error)',[f'return {module}.Try{name}FromCbor(c)'])
        if name in schema.enums:
            out+=[f'const {name}{go._pascal(n)} = {module}.{name}{go._pascal(n)}' for n in schema.enums[name].members]
            out+=['']+func(f'func Try{name}FromWire(v int64) ({name}, error)',[f'return {module}.Try{name}FromWire(v)'])
        else:
            out+=func(f'func Try{name}FromBytes(v []byte) ({name}, error)',[f'return {module}.Try{name}FromBytes(v)'])
    for name in schema.enums:
        out += func(f'func Describe{name}() {r}EnumDescriptor',['return '+en[name]])
    for name in schema.messages:
        out += func(f'func Describe{name}() {r}MessageDescriptor',['return '+mn[name]])
        out += func(f'func TautBinding{name}() {r}MessageBinding',['return '+bn[name]])
        if name in external: continue
        out += func(f'func (*{name}) Descriptor() {r}MessageDescriptor',[f'return Describe{name}()'])
        if validation:
            out += func(f'func (v *{name}) Validate() {r}ValidationReport',['return v.ValidateWithOptions(ValidationOptions{Recursive: true})'])
            out += func(f'func (v *{name}) ValidateWithOptions(o ValidationOptions) {r}ValidationReport',[f'return {r}ValidateRecord(v, TautBinding{name}(), o.Recursive)'])
            out += func(f'func (v *{name}) IsValid() bool',['return v.IsValidWithOptions(ValidationOptions{Recursive: true})'])
            out += func(f'func (v *{name}) IsValidWithOptions(o ValidationOptions) bool',[f'return {r}IsRecordValid(v, TautBinding{name}(), o.Recursive)'])
    out += func(f'func DescribeSchema() {r}SchemaDescriptor',['return '+holder])
    out += [f'var {holder} {r}SchemaDescriptor']
    out += [f'var {v} {r}EnumDescriptor' for v in en.values()]
    out += [f'var {v} {r}MessageDescriptor' for v in mn.values()]
    out += [f'var {v} {r}MessageBinding' for v in bn.values()]
    def td(t):
        if isinstance(t,Scalar): return r+'PrimitiveType('+q(t.kind)+')'
        if isinstance(t,EnumRef): return r+'EnumType('+q(t.name)+', Describe'+t.name+')'
        if isinstance(t,MsgRef): return r+'MessageType('+q(t.name)+', Describe'+t.name+')'
        if isinstance(t,ListOf): return r+'ListType('+td(t.elem)+')'
        if isinstance(t,MapOf): return r+'MapType('+td(t.key)+', '+td(t.value)+')'
        raise TypeError(t)
    out+=['', 'func init() {',f'var guard {r}ContractGuard = {r}RequireFoundation({q(identity)}, {q(OWNER)}, 1, 1, "descriptors.v1", "codec.v1", "oneof.v1")',
        f'{r}ConfirmFoundation(guard, {r}FoundationOwner, {r}DescriptorContract, {r}CodecContract, {r}FoundationCapabilities())']
    for e,ed in zip(schema.enums.values(),doc['enums']):
        if e.name in external:
            val=r+'RequireEnumDescriptor('+dep[external[e.name]['import_path']]+'.Describe'+e.name+'(), '+q(fingerprint(ed))+')'
        else:
            args=[q(e.name),q(identity+'.'+e.name),mapping('int64',{n:str(v) for n,v in e.members.items()}),literal(e.options),literal(ed['member_options']),q(fingerprint(ed))]
            val=r+'NewEnumDescriptor('+', '.join(args)+')'
        out += [en[e.name]+' = '+val]
    for m,md in zip(schema.messages.values(),doc['messages']):
        if m.name in external:
            out += [mn[m.name]+' = '+r+'RequireMessageDescriptor('+dep[external[m.name]['import_path']]+'.Describe'+m.name+'(), '+q(fingerprint(md,forward_compat=forward_compat))+')']; continue
        fields=[]
        for f in sorted(m.fields,key=lambda f:f.tag):
            presence='missing_ok' if f.optional==MISSING_OK else 'nullable' if f.optional else 'required'
            args=[q(f.name),q('' if f.virtual else go.field_name(f.name)),str(f.tag),td(f.type),q(presence),literal(f.transient),literal(f.virtual),literal(f.options)]
            fields.append(r+'NewFieldDescriptor('+', '.join(args)+')')
        groups=[]; constraints=[]
        for ctrl in sorted(m.fields,key=lambda f:f.tag):
            if not ctrl.oneof: continue
            group=ctrl.oneof; members={n:'' for n in schema.enums[group.enum].members}
            for f in m.fields:
                for case in f.cases:
                    if case.controlling_field==ctrl.name: members[case.member]=f.name
            groups.append(r+'NewOneOfDescriptor('+', '.join([q(ctrl.name),en[group.enum],literal(group.virtual),literal(group.exhaustive),mapping('string',{n:q(v) for n,v in members.items()})])+')')
            constraints.append(r+'NewConstraintDescriptor("taut.oneof.v1", '+literal({'controlling_field':ctrl.name})+')')
        next_id='nil' if m.next_id is None else 'func() *int64 { n := int64('+str(m.next_id)+'); return &n }()'
        args=[q(m.name),q(identity+'.'+m.name),seq(r+'FieldDescriptor',fields),seq(r+'OneOfDescriptor',groups),seq(r+'ConstraintDescriptor',constraints),seq('int64',map(str,m.reserved_tags)),seq('string',map(q,m.reserved_names)),next_id,literal(m.options),literal(md['effective']),q(fingerprint(md,forward_compat=forward_compat))]
        out += [mn[m.name]+' = '+r+'NewMessageDescriptor('+', '.join(args)+')']
    def stop(open_collections):
        return ['visitor.Leave('+identity+')' for identity in reversed(open_collections)]+['return false']
    def walk(t, expr, path, depth=0, open_collections=()):
        if isinstance(t,MsgRef):
            if expr.startswith('(*') and expr.endswith(')'): expr=expr[1:-1]
            return [f'if !visitor.Record(&({expr}), TautBinding{t.name}(), {path}) {{', *['\t'+line for line in stop(open_collections)], '}']
        if isinstance(t,EnumRef):
            cases=', '.join(str(v) for v in schema.enums[t.name].members.values())
            return [f'switch int64({expr}) {{', f'case {cases}:', 'default:', f'\tif !visitor.Issue("validation.type_mismatch", "validation.shape.v1", {path}, "invalid generated enum") {{', *['\t\t'+line for line in stop(open_collections)], '\t}', '}']
        identity='identity'+str(depth); entered='entered'+str(depth); keep='keep'+str(depth)
        def collection(kind, body):
            value=expr[1:-1] if expr.startswith('(*') and expr.endswith(')') else expr
            return [f'{identity} := {r}{kind}Identity({value})',f'{entered}, {keep} := visitor.Enter({identity}, {path})',f'if !{keep} {{',*['\t'+line for line in stop(open_collections)],'}',f'if {entered} {{',*['\t'+line for line in body],f'\tvisitor.Leave({identity})','}']
        if isinstance(t,ListOf):
            i='idx'+str(depth); p='path'+str(depth)
            inner=walk(t.elem,expr+'['+i+']',p,depth+1,(*open_collections,identity))
            if not inner: return []
            ranged=expr[1:-1] if expr.startswith('(*') and expr.endswith(')') else expr
            return collection('List',[f'for {i} := range {ranged} {{',f'\t{p} := {r}ChildPath({path}, {r}IndexPath(uint64({i})))',*['\t'+line for line in inner],'}'])
        if isinstance(t,MapOf):
            k='key'+str(depth); ks='keys'+str(depth); p='path'+str(depth); v='child'+str(depth)
            keytype=go._go_ty(t.key); encoder=r+go._SCALAR_ENCODERS[t.key.kind]
            inner=walk(t.value,v,p,depth+1,(*open_collections,identity))
            if not inner: return []
            ranged=expr[1:-1] if expr.startswith('(*') and expr.endswith(')') else expr
            return collection('Map',[f'{ks} := make([]{keytype}, 0, len({ranged}))', f'for {k} := range {ranged} {{', f'\t{ks} = append({ks}, {k})', '}',
                f'tautsort.Slice({ks}, func(i, j int) bool {{', f'\treturn tautbytes.Compare({r}Encode({encoder}({ks}[i])), {r}Encode({encoder}({ks}[j]))) < 0', '})',
                f'for _, {k} := range {ks} {{',f'\t{v} := {expr}[{k}]',f'\t{p} := {r}ChildPath({path}, {r}KeyPath({q(t.key.kind)}, {r}Encode({encoder}({k}))))',*['\t'+line for line in inner],'}'])
        return []
    for m in schema.messages.values():
        if m.name in external:
            out += [bn[m.name]+' = '+r+'RequireMessageBinding('+dep[external[m.name]['import_path']]+'.TautBinding'+m.name+'(), '+mn[m.name]+', '+q(fingerprint(next(md for md in doc['messages'] if md['name']==m.name),forward_compat=forward_compat))+')']; continue
        fields=sorted(m.fields,key=lambda f:f.tag)
        present=['func(v *'+m.name+', i int) bool {', '\tswitch i {']
        for i,f in enumerate(fields): present += [f'\tcase {i}:', '\t\treturn '+('false' if f.virtual else 'v.'+go.field_name(f.name)+' != nil' if f.optional else 'true')]
        present+=['\t}', '\treturn false', '}']
        enums=['func(v *'+m.name+', i int) (int64, bool) {', '\tswitch i {']
        for i,f in enumerate(fields):
            if isinstance(f.type,EnumRef) and not f.virtual:
                value='v.'+go.field_name(f.name)
                if f.optional: enums += [f'\tcase {i}:', f'\t\tif {value} == nil {{', '\t\t\treturn 0, false', '\t\t}', f'\t\treturn int64(*{value}), true']
                else: enums += [f'\tcase {i}:', f'\t\treturn int64({value}), true']
        enums+=['\t}', '\treturn 0, false', '}']
        reads=['func(v *'+m.name+', i int) any {', '\tswitch i {']
        for i,f in enumerate(fields):
            if f.virtual: continue
            value='v.'+go.field_name(f.name)
            reads += [f'\tcase {i}:']
            if f.optional:
                reads += [f'\t\tif {value} == nil {{', '\t\t\treturn nil', '\t\t}', f'\t\treturn *{value}']
            else: reads += [f'\t\treturn {value}']
        reads += ['\t}', '\treturn nil', '}']
        walks=['func(v *'+m.name+f', i int, visitor {r}Traversal, path []{r}PathSegment) bool {{', '\tswitch i {']
        for i,f in enumerate(fields):
            if f.virtual: continue
            expr='v.'+go.field_name(f.name)
            inner=walk(f.type,'(*'+expr+')' if f.optional else expr,'path')
            if inner:
                walks += [f'\tcase {i}:']
                if f.optional:
                    walks += [f'\t\tif {expr} != nil {{']+['\t\t\t'+line for line in inner]+['\t\t}']
                else:
                    walks += ['\t\t'+line for line in inner]
        walks+=['\t}', '\treturn true', '}']
        out += [bn[m.name]+' = '+r+'NewMessageBinding['+m.name+']('+mn[m.name]+', '+ '\n'.join(present)+', '+ '\n'.join(enums)+', '+ '\n'.join(reads)+', '+ '\n'.join(walks)+')']
    out += [holder+' = '+r+'NewSchemaDescriptor('+', '.join([str(doc['version']),q(identity),mapping(r+'MessageDescriptor',mn),mapping(r+'EnumDescriptor',en),literal(schema.options),literal(doc['effective'])])+')','}']
    # Only import bytes when a map adapter traverses values (scalar codec map
    # ordering itself remains the established native ordering).
    init_start=out.index('func init() {')
    out[init_start+1:-1]=['\t'+line.replace('\n','\n\t') for line in out[init_start+1:-1]]
    text='\n'.join(out)+'\n'
    if 'tautbytes.Compare' not in text: imports.pop('tautbytes',None)
    if 'tautsort.Slice' not in text: imports.pop('tautsort',None)
    import_block='\nimport (\n'+''.join('\t'+alias+' '+q(path)+'\n' for alias,path in sorted(imports.items(),key=lambda x:x[1]))+')\n' if imports else ''
    return text.replace('package taut\n','package taut\n'+import_block,1)
