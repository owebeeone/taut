"""Java's immutable native facts and typed adapter projection (Java 8 ABI)."""
from __future__ import annotations
import hashlib
import json
from . import java
from ..facts import Scalar, EnumRef, MsgRef, ListOf, MapOf, MISSING_OK
from ..ir.export import schema_json

D = 'taut.validation.descriptors.'

def q(value):
    return json.dumps(value, ensure_ascii=True)

def literal(value):
    if value is None: return 'null'
    if type(value) is bool: return str(value).lower()
    if type(value) is str: return q(value)
    if type(value) is bytes: return 'new '+D+'ImmutableBytes(new byte[]{'+', '.join(str(n if n<128 else n-256) for n in value)+'})'
    if type(value) is int: return str(value) + 'L'
    if type(value) is float: return repr(value)
    if isinstance(value, dict) or hasattr(value, 'items'):
        return D+'Snapshots.entries('+', '.join(x for k,v in value.items() for x in (q(k),literal(v)))+')'
    if isinstance(value,(tuple,list)):
        return 'java.util.Arrays.asList('+', '.join(map(literal,value))+')'
    raise ValueError(f'Java portable metadata unsupported: {value!r}')

def seq(ty, values):
    return 'java.util.Arrays.<'+ty+'>asList('+', '.join(values)+')'

def mapping(ty, values):
    return '$map('+seq('String',[q(k) for k in values])+', '+seq(ty,list(values.values()))+')'

def fingerprint(value):
    # Message descriptors publish field-number order. Author declaration order
    # and the order of equivalent Case nominations are not compatibility facts.
    # Copy the records so hashing never mutates the export used by the emitter.
    if 'fields' in value and 'name' in value:
        value = dict(value, fields=[dict(field) for field in
                                   sorted(value['fields'], key=lambda field: field['tag'])])
        for field in value['fields']:
            if 'cases' in field:
                field['cases'] = sorted(field['cases'], key=lambda case:
                                        (case['controlling_field'], case['enum'], case['member']))
    return hashlib.sha256(json.dumps(value,sort_keys=True,default=dict).encode()).hexdigest()

def preflight(schema, validation, external):
    from ..ir.validate import validate
    errors=validate(schema, targets=("java",))
    declared=set(schema.enums)|set(schema.messages)
    if set(external)-declared: errors.append(f'unknown Java external types {sorted(set(external)-declared)}')
    import unicodedata
    def java_identifier(value):
        def start(c): return unicodedata.category(c) in ('Lu','Ll','Lt','Lm','Lo','Nl','Sc','Pc')
        def part(c): return start(c) or unicodedata.category(c) in ('Mn','Mc','Nd','Cf')
        return bool(value) and start(value[0]) and all(part(c) for c in value[1:])
    names={}
    for name in declared:
        access=java._type_name(name)
        if not java_identifier(access): errors.append(f"{name}: unsupported Java identifier projection {access}")
        if access in java.RESERVED_TYPE_NAMES or access=='taut': errors.append(f'{name}: Java runtime/type collision {access}')
        if access in names: errors.append(f'{name}: Java escaped type collision with {names[access]}')
        names[access]=name
    for m in schema.messages.values():
        attrs={}
        for f in m.fields:
            access=java._field_name(f.name)
            if not java_identifier(access): errors.append(f"{m.name}.{f.name}: unsupported Java identifier projection {access}")
            if access in java.RESERVED_FIELD_NAMES: errors.append(f'{m.name}.{f.name}: Java reserved field {access}')
            if access in attrs: errors.append(f'{m.name}.{f.name}: Java field collision after escaping with {attrs[access]}')
            attrs[access]=f.name
    for e in schema.enums.values():
        constants=[java._enum_member(n) for n in e.members]
        if not all(java_identifier(n) for n in constants): errors.append(f"{e.name}: unsupported Java enum identifier projection")
        if len(set(constants))!=len(constants): errors.append(f'{e.name}: Java enum members collide after uppercase projection')
    def refs(t):
        if isinstance(t,(MsgRef,EnumRef)): return {t.name}
        if isinstance(t,ListOf): return refs(t.elem)
        if isinstance(t,MapOf): return refs(t.key)|refs(t.value)
        return set()
    for name in external:
        if name in schema.messages:
            missing=set().union(*(refs(f.type) for f in schema.messages[name].fields))-external.keys()
            if missing: errors.append(f'Java external {name} requires mappings for {sorted(missing)}; bind the full dependency graph to avoid duplicate native types')
    for name,binding in external.items():
        from .java_runtime import OWNER, CAPABILITIES
        if not isinstance(binding,dict): errors.append(f'{name}: Java external binding requires typed contract metadata'); continue
        required={'type','owner','descriptor_contract','codec_contract','capabilities'}
        if set(binding)!=required or binding.get('type')!='taut.'+java._type_name(name) or binding.get('owner')!=OWNER or type(binding.get('descriptor_contract')) is not int or binding.get('descriptor_contract')!=1 or type(binding.get('codec_contract')) is not int or binding.get('codec_contract')!=1 or not CAPABILITIES<=set(binding.get('capabilities',())):
            errors.append(f'{name}: incompatible Java external artifact; require taut.{java._type_name(name)}, owner={OWNER}, descriptor=1, codec=1 and {sorted(CAPABILITIES)}; regenerate/rebind')
    if errors: raise ValueError('; '.join(errors))

def emit_types(schema, *, forward_compat=False, validation=False, external_types=None, identity=None):
    if type(validation) is not bool:
        raise TypeError('Java validation option must be Boolean')
    external=dict(external_types or {})
    preflight(schema, validation, external)
    doc=schema_json(schema)
    identity=identity or 'schema_'+fingerprint(doc)[:16]
    holder='$Taut_'+hashlib.sha256(identity.encode()).hexdigest()[:16]
    en={e.name:'$E'+str(i) for i,e in enumerate(schema.enums.values())}
    mn={m.name:'$M'+str(i) for i,m in enumerate(schema.messages.values())}
    an={m.name:'$A'+str(i) for i,m in enumerate(schema.messages.values())}
    def ref(name): return holder+'.'+(mn.get(name) or en[name])
    def td(t):
        if isinstance(t,Scalar): args=[q(t.kind),'null','null','null','null','null','null']
        elif isinstance(t,MsgRef): args=[q('message'),q(t.name),'null','null','null','() -> '+ref(t.name),'null']
        elif isinstance(t,EnumRef): args=[q('enum'),q(t.name),'null','null','null','null','() -> '+ref(t.name)]
        elif isinstance(t,ListOf): args=[q('list'),'null',td(t.elem),'null','null','null','null']
        elif isinstance(t,MapOf): args=[q('map'),'null','null',td(t.key),td(t.value),'null','null']
        else: raise TypeError(t)
        return 'new '+D+'TypeDescriptor('+', '.join(args)+')'
    def va(t,desc):
        ty=java._java_ty(t,boxed=True)
        base=D+'ValueAdapter.'
        if isinstance(t,Scalar): return base+'scalar('+desc+', '+ty+'.class)'
        if isinstance(t,EnumRef):
            cases=' '.join('case '+java._enum_member(n)+': return '+q(n)+';' for n in schema.enums[t.name].members)
            return base+'enumeration('+desc+', '+ty+'.class, $e -> { switch($e) { '+cases+' default: throw new taut.validation.ConfigurationException("invalid enum"); } })'
        if isinstance(t,MsgRef): return base+'message('+desc+', '+ty+'.class, () -> '+holder+'.'+an[t.name]+')'
        if isinstance(t,ListOf): return base+'list('+desc+', '+va(t.elem,desc+'.element()')+')'
        if isinstance(t,MapOf):
            enc=java._enc(t.key,'$key')
            return base+'map('+desc+', '+va(t.key,desc+'.key()')+', $key -> Cbor.encode('+enc+'), '+va(t.value,desc+'.value()')+')'
        raise TypeError(t)
    out=['// GENERATED native Java types + codec; Java 8 foundation ABI.',
         '// generator=java-oneof-reference.1; owner=taut.java.foundation; descriptor=1; codec=1', 'package taut;', '']
    for e in schema.enums.values():
        if e.name in external: continue
        lines=java._emit_enum(java._type_name(e.name),e.members)
        lines.insert(-1,'    public static '+D+'EnumDescriptor descriptor() { return '+holder+'.'+en[e.name]+'; }')
        out+=lines+['']
    for m in schema.messages.values():
        if m.name in external: continue
        lines=java._emit_message(schema,m,forward_compat)
        lines.insert(-1,'    public static '+D+'MessageDescriptor descriptor() { return '+holder+'.'+mn[m.name]+'; }')
        lines.insert(-1,'    static '+D+'MessageAdapter<'+java._type_name(m.name)+'> $adapter() { return '+holder+'.'+an[m.name]+'; }')
        if validation:
            codec=java._codec(m)
            lines[-1:-1]=[
                '    public taut.validation.ValidationReport validate() { return validate(true); }',
                '    public taut.validation.ValidationReport validate(boolean $recursive) { return '+codec+'.$validate(this,$recursive); }',
                '    public boolean isValid() { return isValid(true); }',
                '    public boolean isValid(boolean $recursive) { return '+codec+'.$isValid(this,$recursive); }']
        out+=lines+['']
        lines=java._emit_codec(m,forward_compat)
        if validation:
            name=java._type_name(m.name)
            lines[-1:-1]=[
                '    static taut.validation.ValidationReport $validate('+name+' $value, boolean $recursive) { return taut.validation.ValidationEngine.validate($value, '+holder+'.'+an[m.name]+', $recursive); }',
                '    static boolean $isValid('+name+' $value, boolean $recursive) { return taut.validation.ValidationEngine.isValid($value, '+holder+'.'+an[m.name]+', $recursive); }']
        out+=lines+['']
    out+=['final class '+holder+' {', '    private '+holder+'() {}',
          '    private static <T> java.util.Map<String,T> $map(java.util.List<String> $keys,java.util.List<T> $values) { java.util.Map<String,T> $result=new java.util.LinkedHashMap<String,T>(); for(int $i=0;$i<$keys.size();$i++) $result.put($keys.get($i),$values.get($i)); return $result; }',
          '    static { '+D+'RuntimeContract.require('+q(identity)+', "taut.java.foundation", 1, 1, "descriptors.v1", "codec.v1", "oneof.v1"); }']
    for e,edoc in zip(schema.enums.values(),doc['enums']):
        value=java._type_name(e.name)+'.descriptor()' if e.name in external else 'new '+D+'EnumDescriptor('+', '.join([q(e.name),q(identity+'.'+e.name),mapping('Long',{n:literal(v) for n,v in e.members.items()}),literal(e.options),literal({n:{} for n in e.members}),q(fingerprint(edoc))])+')'
        out+=['    static final '+D+'EnumDescriptor '+en[e.name]+' = '+value+';']
    field_names={}
    for m in schema.messages.values():
        if m.name in external: continue
        for i,f in enumerate(sorted(m.fields,key=lambda f:f.tag)):
            name=mn[m.name]+'F'+str(i);field_names[m.name,f.name]=name
            presence='missing_ok' if f.optional==MISSING_OK else 'nullable' if f.optional else 'required'
            args=[q(f.name),'null' if f.virtual else q(java._field_name(f.name)),str(f.tag),td(f.type),q(presence),literal(f.transient),literal(f.virtual),literal(f.options)]
            out+=['    static final '+D+'FieldDescriptor '+name+' = new '+D+'FieldDescriptor('+', '.join(args)+');']
    for m,mdoc in zip(schema.messages.values(),doc['messages']):
        if m.name in external:
            out+=['    static final '+D+'MessageDescriptor '+mn[m.name]+' = '+java._type_name(m.name)+'.descriptor();']; continue
        groups=[];constraints=[]
        for ctrl in sorted(m.fields,key=lambda f:f.tag):
            if not ctrl.oneof: continue
            rule=ctrl.oneof; members={member:'null' for member in schema.enums[rule.enum].members}
            for f in m.fields:
                for case in f.cases:
                    if case.controlling_field==ctrl.name: members[case.member]=q(f.name)
            groups.append('new '+D+'OneOfDescriptor('+', '.join([q(ctrl.name),en[rule.enum],literal(rule.virtual),literal(rule.exhaustive),mapping('String',members)])+')')
            constraints.append('new '+D+'ConstraintDescriptor("taut.oneof.v1", '+literal({'controlling_field':ctrl.name})+')')
        args=[q(m.name),q(identity+'.'+m.name),'1',seq(D+'FieldDescriptor',[field_names[m.name,f.name] for f in sorted(m.fields,key=lambda f:f.tag)]),seq(D+'OneOfDescriptor',groups),seq(D+'ConstraintDescriptor',constraints),seq('Long',[literal(n) for n in m.reserved_tags]),seq('String',[q(n) for n in m.reserved_names]),literal(m.next_id),literal(m.options),literal(mdoc['effective']),q(fingerprint(mdoc))]
        out+=['    static final '+D+'MessageDescriptor '+mn[m.name]+' = new '+D+'MessageDescriptor('+', '.join(args)+');']
    for m in schema.messages.values():
        ty=java._type_name(m.name)
        if m.name in external: value=ty+'.$adapter()'
        else:
            fields=[]
            for f in sorted(m.fields,key=lambda f:f.tag):
                fd=field_names[m.name,f.name]
                read='null' if f.virtual else '$self -> $self.'+java._field_name(f.name)
                fields.append('new '+D+'FieldBinding<'+ty+', '+java._java_ty(f.type,boxed=True)+'>('+fd+', '+read+', '+va(f.type,fd+'.type()')+')')
            value='new '+D+'MessageAdapter<'+ty+'>('+ty+'.class, '+mn[m.name]+', '+seq(D+'FieldBinding<'+ty+',?>',fields)+')'
        out+=['    static final '+D+'MessageAdapter<'+ty+'> '+an[m.name]+' = '+value+';']
    for e,edoc in zip(schema.enums.values(),doc['enums']):
        if e.name in external: out+=['    static { if (!'+en[e.name]+'.fingerprint().equals('+q(fingerprint(edoc))+')) throw new taut.validation.ConfigurationException('+q(e.name+': imported enum facts mismatch')+'); }']
    for m,mdoc in zip(schema.messages.values(),doc['messages']):
        if m.name in external: out+=['    static { if (!'+mn[m.name]+'.fingerprint().equals('+q(fingerprint(mdoc))+')) throw new taut.validation.ConfigurationException('+q(m.name+': imported message facts mismatch')+'); }']
    args=['1',str(doc['version']),q(identity),mapping(D+'MessageDescriptor',mn),mapping(D+'EnumDescriptor',en),literal(schema.options),literal(doc['effective'])]
    out+=['    static final '+D+'SchemaDescriptor $schema = new '+D+'SchemaDescriptor('+', '.join(args)+');',
          '    static final '+D+'SchemaBinding $binding = new '+D+'SchemaBinding($schema, '+mapping(D+'MessageAdapter<?>',an)+');', '}']
    return '\n'.join(out)+'\n'
