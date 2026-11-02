"""Static native metadata, borrowed typed adapters and external dependency guards."""
from __future__ import annotations
import hashlib
import json
import re
from collections.abc import Mapping
from ..ir.model import Scalar, EnumRef, MsgRef, ListOf, MapOf, MISSING_OK
from ..ir.export import schema_json
from ..ir.options import effective_map
from .kotlin_metadata import fingerprint as portable_fingerprint

def fingerprint(schema,name,forward_compat=False):
    portable=portable_fingerprint(schema,name)
    return (hashlib.sha256((portable+':forward_compat='+str(forward_compat)).encode()).hexdigest()
            if name in schema.messages else portable)

KEYWORDS=set('alignas alignof and and_eq asm auto bitand bitor bool break case catch char char8_t char16_t char32_t class compl concept const consteval constexpr constinit const_cast continue co_await co_return co_yield decltype default delete do double dynamic_cast else enum explicit export extern false float for friend goto if inline int long mutable namespace new noexcept not not_eq nullptr operator or or_eq private protected public register reinterpret_cast requires return short signed sizeof static static_assert static_cast struct switch template this thread_local throw true try typedef typeid typename union unsigned using virtual void volatile wchar_t while xor xor_eq'.split())

def q(value):
    # UTF-8 bytes with explicit length, including embedded NUL and non-ASCII.
    from .cpp import _lit
    return _lit(value.encode('utf-8'))

def preflight(schema, validation, external):
    from ..ir.validate import validate
    from .cpp import RESERVED_FIELD_NAMES, RESERVED_TYPE_NAMES, _variant
    from .cpp_runtime import OWNER,CAPABILITIES
    errors=validate(schema,targets=('cpp',))
    known=set(schema.messages)|set(schema.enums)
    if external.keys()-known:errors.append(f'unknown C++ external mappings {sorted(external.keys()-known)}')
    def identifier(name):return bool(re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*',name)) and name not in KEYWORDS
    for name in known:
        if not identifier(name) or name in {'validation','descriptor_detail','EnumTraits','ValueRef','SchemaBinding','SchemaDescriptor','ReadOnlyRange','TypeKind','Fact','FactEntry','Options','TypeDescriptor','MessageDescriptor','EnumDescriptor','EnumMemberDescriptor','FieldDescriptor','FieldBinding','OneOfDescriptor','OneOfMemberDescriptor','ConstraintDescriptor','FoundationContract','CompatibleMessage','CompatibleEnum','require_foundation','foundation_contract'} or name.startswith('taut_meta_'):
            errors.append(f'C++ type/generated runtime symbol collision: {name}')
        if name in schema.messages and (name in {'descriptor','taut_binding'} or (validation and name in {'validate','is_valid'})):
            errors.append(f'C++ message/generated member collision: {name}')
    for m in schema.messages.values():
        reserved=set(RESERVED_FIELD_NAMES)|{'descriptor','taut_binding'}|({'validate','is_valid'} if validation else set())
        for f in m.fields:
            if not identifier(f.name) or f.name in reserved:
                errors.append(f'{m.name}.{f.name}: C++ keyword/generated member collision')
    for e in schema.enums.values():
        names=[_variant(n) for n in e.members]
        if len(names)!=len(set(names)) or any(not identifier(n) for n in names):errors.append(f'{e.name}: C++ enum member projection collision')
    def refs(t):
        if isinstance(t,(MsgRef,EnumRef)):return {t.name}
        if isinstance(t,ListOf):return refs(t.elem)
        if isinstance(t,MapOf):return refs(t.key)|refs(t.value)
        return set()
    for name,b in external.items():
        if not isinstance(b,dict):errors.append(f'{name}: C++ external mapping requires header/type/contracts');continue
        keys={'header','type','owner','descriptor_contract','codec_contract','capabilities'}
        if (set(b)!=keys or not isinstance(b.get('header'),str) or not re.fullmatch(r'[A-Za-z0-9_./-]+',b.get('header',''))
            or b.get('type')!='taut::'+name or b.get('owner')!=OWNER or type(b.get('descriptor_contract')) is not int
            or b.get('descriptor_contract')!=1 or type(b.get('codec_contract')) is not int or b.get('codec_contract')!=1
            or not isinstance(b.get('capabilities'),(list,tuple,set)) or any(not isinstance(c,str) for c in b.get('capabilities',())) or set(b.get('capabilities',()))!=CAPABILITIES):
            errors.append(f'{name}: incompatible C++ external artifact; require header, type=taut::{name}, owner={OWNER}, descriptor=1 codec=1 capabilities={sorted(CAPABILITIES)}; regenerate/rebind')
        if name in schema.messages:
            missing=set().union(*(refs(f.type) for f in schema.messages[name].fields))-external.keys()
            if missing:errors.append(f'C++ external {name} requires complete dependency mappings {sorted(missing)}')
    if errors:raise ValueError('; '.join(errors))


def emit(schema, *, validation=False, external_types=None, identity=None, forward_compat=False):
    external=external_types or {}
    preflight(schema,validation,external)
    doc=schema_json(schema)
    identity=identity or 'schema_'+hashlib.sha256(json.dumps(doc,sort_keys=True).encode()).hexdigest()[:16]
    holder='taut_meta_'+hashlib.sha256(identity.encode()).hexdigest()[:16]
    lines=['namespace '+holder+' {']
    count=0
    def array(ty, values):
        nonlocal count
        if not values:return '{}'
        count+=1;name='table_'+str(count)
        lines.append('inline constexpr '+ty+' '+name+'[] = {'+', '.join(values)+'};')
        return name
    def fact(value):
        if value is None:return 'Fact{Fact::Tag::Null}'
        if type(value) is bool:return 'Fact{Fact::Tag::Bool,'+str(value).lower()+'}'
        if type(value) is int:return 'Fact{Fact::Tag::Int,false,'+integer(value)+'}'
        if type(value) is float:return 'Fact{Fact::Tag::Float,false,0,'+repr(value)+'}'
        if isinstance(value,(str,bytes)):
            from .cpp import _lit
            return 'Fact{Fact::Tag::'+('String' if isinstance(value,str) else 'Bytes')+',false,0,0,'+_lit(value.encode() if isinstance(value,str) else value)+'}'
        if isinstance(value,Mapping):return 'Fact{Fact::Tag::Map,false,0,0,{},{},'+options(value)+'}'
        if isinstance(value,(tuple,list)):return 'Fact{Fact::Tag::List,false,0,0,{},'+array('Fact',[fact(v) for v in value])+'}'
        raise ValueError(f'unsupported C++ fact {value!r}')
    def integer(n):return '(-9223372036854775807LL - 1)' if n==-(1<<63) else str(n)+'LL'
    def options(values):return array('FactEntry',['{'+q(k)+','+fact(v)+'}' for k,v in sorted(values.items())])
    def en(name):return 'EnumTraits<::taut::'+name+'>::descriptor'
    def mn(name):return '::taut::'+name+'::descriptor'
    def td(t):
        nonlocal count
        if isinstance(t,Scalar):value='TypeDescriptor{TypeKind::'+{'int':'Int','float':'Float','bool':'Bool','bytes':'Bytes','str':'String'}[t.kind]+'}'
        elif isinstance(t,EnumRef):value='TypeDescriptor{TypeKind::Enum,nullptr,nullptr,nullptr,nullptr,'+en(t.name)+'}'
        elif isinstance(t,MsgRef):value='TypeDescriptor{TypeKind::Message,nullptr,nullptr,nullptr,'+mn(t.name)+'}'
        elif isinstance(t,ListOf):value='TypeDescriptor{TypeKind::List,&'+td(t.elem)+'}'
        elif isinstance(t,MapOf):value='TypeDescriptor{TypeKind::Map,nullptr,&'+td(t.key)+',&'+td(t.value)+'}'
        else:raise TypeError(t)
        count+=1;name='type_'+str(count);lines.append('inline constexpr '+value.replace('TypeDescriptor{','TypeDescriptor '+name+'{')+';');return name
    for name in schema.enums:
        lines.append('const EnumDescriptor& enum_'+name+'() noexcept;')
    for name in schema.messages:
        lines.append('const MessageDescriptor& message_'+name+'() noexcept;')
        lines.append('const SchemaBinding& binding_'+name+'() noexcept;')
    lines.append('const SchemaDescriptor& schema() noexcept;')
    for e in schema.enums.values():
        if e.name in external:continue
        members=array('EnumMemberDescriptor',['{'+q(n)+','+integer(v)+',{}}' for n,v in sorted(e.members.items())])
        opts=options(e.options)
        lines.append('inline const EnumDescriptor& enum_'+e.name+'() noexcept { static constexpr EnumDescriptor value{'+','.join([q(e.name),q(identity+'.'+e.name),members,opts,q(fingerprint(schema,e.name,forward_compat))])+'};return value;}')
    for m in schema.messages.values():
        if m.name in external:continue
        field_values=[]
        for f in sorted(m.fields,key=lambda f:f.tag):
            ty=td(f.type);opts=options(f.options)
            field_values.append('FieldDescriptor{'+','.join([q(f.name),q('' if f.virtual else f.name),integer(f.tag),ty,q('missing_ok' if f.optional==MISSING_OK else 'nullable' if f.optional else 'required'),str(f.transient).lower(),str(f.virtual).lower(),opts])+'}')
        fields=array('FieldDescriptor',field_values)
        groups=[];constraints=[]
        for ctrl in sorted(m.fields,key=lambda f:f.tag):
            if not ctrl.oneof:continue
            members={n:'' for n in schema.enums[ctrl.oneof.enum].members}
            for f in m.fields:
                for c in f.cases:
                    if c.controlling_field==ctrl.name:members[c.member]=f.name
            mapped=array('OneOfMemberDescriptor',['{'+q(n)+','+q(p)+'}' for n,p in sorted(members.items())])
            groups.append('OneOfDescriptor{'+','.join([q(ctrl.name),en(ctrl.oneof.enum),str(ctrl.virtual).lower(),str(ctrl.oneof.exhaustive).lower(),mapped])+'}')
            constraints.append('{'+q('taut.oneof.v1')+','+options({'controlling_field':ctrl.name})+'}')
        groups=array('OneOfDescriptor',groups);constraints=array('ConstraintDescriptor',constraints)
        nums=array('long long',[integer(n) for n in sorted(m.reserved_tags)])
        names=array('std::string_view',[q(n) for n in sorted(m.reserved_names)])
        opts=options(m.options);effective=options(effective_map(schema,message=m.name))
        args=[q(m.name),q(identity+'.'+m.name),fields,groups,constraints,nums,names,'std::nullopt' if m.next_id is None else integer(m.next_id),opts,effective,q(fingerprint(schema,m.name,forward_compat))]
        lines.append('inline const MessageDescriptor& message_'+m.name+'() noexcept { static constexpr MessageDescriptor value{'+','.join(args)+'};return value;}')
        bindings=array('FieldBinding',['{nullptr}' if f.virtual else '{+[](const void* p) noexcept -> const ValueRef {return ValueRef::borrow(static_cast<const ::taut::'+m.name+'*>(p)->'+f.name+');}}' for f in sorted(m.fields,key=lambda f:f.tag)])
        lines.append('inline const SchemaBinding& binding_'+m.name+'() noexcept {static constexpr SchemaBinding value{'+mn(m.name)+','+bindings+',schema};return value;}')
    messages=array('const MessageDescriptor& (*)() noexcept',[]) # function-pointer array uses an alias below.
    lines.append('using MessageAccessor=const MessageDescriptor& (*)() noexcept;using EnumAccessor=const EnumDescriptor& (*)() noexcept;')
    messages=array('MessageAccessor',[mn(n) for n in sorted(schema.messages)])
    enums=array('EnumAccessor',[en(n) for n in sorted(schema.enums)])
    opts=options(schema.options);effective=options(effective_map(schema))
    lines.append('inline const SchemaDescriptor& schema() noexcept {static constexpr SchemaDescriptor value{1,'+str(doc['version'])+','+q(identity)+','+messages+','+enums+','+opts+','+effective+'};return value;}')
    # Inspect the selected compiled owner's export, rather than trusting a
    # possibly stale checker whose old implementation ignores new requirements.
    lines.append('inline const bool checked = [] { try {const auto& contract=::taut::foundation_contract();')
    lines.append('if(contract.owner!="taut.cpp.foundation" || contract.descriptor!=1 || contract.codec!=1 || contract.adapter!=1 || (contract.capabilities&7)!=7 || contract.guard!=0x5441555443505031ULL) throw std::logic_error("incompatible actual C++ foundation export: require owner taut.cpp.foundation descriptor=1 codec=1 adapter=1 capabilities=7 guard=v1; regenerate/rebind");')
    for name in schema.messages:
        lines.append('descriptor_detail::check_binding(::taut::'+name+'::taut_binding());')
    for name in external:
        ref=mn(name) if name in schema.messages else en(name)
        lines.append('if('+ref+'().fingerprint()!='+q(fingerprint(schema,name,forward_compat))+')throw std::logic_error("'+name+': incompatible imported C++ descriptor/codec facts; regenerate dependency");')
    lines+=['return true;}catch(const std::exception& error){std::fputs("taut C++ configuration: ",stderr);std::fputs(error.what(),stderr);std::fputc(\'\\n\',stderr);std::abort();}}();','}']
    for name in schema.messages:
        if name in external:continue
        lines+=['inline const MessageDescriptor& '+name+'::descriptor() noexcept {return '+holder+'::message_'+name+'();}',
                'inline const SchemaBinding& '+name+'::taut_binding() noexcept {return '+holder+'::binding_'+name+'();}']
        if validation:
            lines+=['inline validation::ValidationReport '+name+'::validate(bool recursive) const noexcept {return validation::validate_record(*this,recursive);}',
                    'inline bool '+name+'::is_valid(bool recursive) const noexcept {return validation::is_record_valid(*this,recursive);}']
    return holder,lines
