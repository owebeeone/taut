"""Native C++20 behavior, package/link owner, descriptors and noexcept boundaries."""
import dataclasses
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import types
import pytest
from taut.gen.scaffold import emit, python_api
from taut.gen.cpp_runtime import build_foundation, canonical_sources, OWNER, CAPABILITIES
from taut.ir.load import load_schema
from taut.ir.dsl import Enum,F,Msg,Ref,STR,INT,schema
from taut.ir.export import schema_json
from taut.ir.load import schema_from_json

ROOT=Path(__file__).resolve().parents[2]
EXAMPLE=ROOT/'dev-docs/examples/cpp-oneof'
SCHEMA=load_schema(EXAMPLE/'content.taut.py')

def run(args, *, ok=True):
    result=subprocess.run(list(map(str,args)),capture_output=True,encoding='utf-8')
    if ok:assert result.returncode==0,result.stdout+result.stderr
    return result

def compile_cpp(directory,source,*,include=(),objects=(),ok=True):
    directory.mkdir(parents=True,exist_ok=True)
    p=directory/'main.cpp';p.write_text(source,encoding='utf-8')
    compiler=shutil.which('clang++') or shutil.which('c++') or shutil.which('g++')
    assert compiler,'activated C++ readiness compiler required'
    executable=directory/('main.exe' if os.name=='nt' else 'main')
    result=run([compiler,'-std=c++20','-fno-rtti',*[a for root in include for a in ('-I',root)],p,*objects,'-o',executable],ok=ok)
    return executable,result

@pytest.fixture(scope='module')
def package(tmp_path_factory):return build_foundation(tmp_path_factory.mktemp('cpp-package')/'foundation')

def python_rows():
    # The common reference is the accepted Python instance projection.
    from test_java_oneof import python_rows as reference
    return reference()

@pytest.mark.parametrize('mode',['source','package',None])
def test_reference_behavior(tmp_path,package,mode):
    emit(SCHEMA,tmp_path,langs=['cpp'],services=[],runtime_mode=mode,validation=True,
         runtime_bindings={'cpp':{'artifact':str(package)}} if mode!='source' else None)
    d=tmp_path/'cpp';include=d if mode=='source' else package/'include'
    obj=d/'foundation.cpp' if mode=='source' else package/'taut-foundation.lib'
    executable,_=compile_cpp(tmp_path/'build',(EXAMPLE/'Conformance.cpp').read_text(),include=[d,include],objects=[obj])
    assert run([executable]).stdout.splitlines()==python_rows()
    if mode=='source':
        for name,data in canonical_sources().items():assert (d/name).read_bytes()==data
    else:assert not (d/'taut/cbor.hpp').exists()

@pytest.mark.parametrize('mode',['source','package',None])
def test_disabled_metadata_codec(tmp_path,package,mode):
    emit(SCHEMA,tmp_path,langs=['cpp'],services=[],runtime_mode=mode)
    d=tmp_path/'cpp';text=(d/'api.hpp').read_text()
    assert ' validate(' not in text and ' is_valid(' not in text
    assert not (d/'taut/validation.hpp').exists()
    include=d if mode=='source' else package/'include'
    obj=d/'foundation.cpp' if mode=='source' else package/'taut-foundation.lib'
    executable,_=compile_cpp(tmp_path/'build','#include "api.hpp"\n#include <cassert>\nint main(){assert(taut::Content::descriptor().fields().size()==6);taut::Content c{};c.kind=taut::Kind::Empty;taut::Buf b;c.to_cbor(b);assert(b.n);}',include=[d,include],objects=[obj])
    run([executable])

@pytest.mark.parametrize('mode',['source','package'])
def test_allocation_fault_noexcept(tmp_path,package,mode):
    emit(SCHEMA,tmp_path,langs=['cpp'],services=[],runtime_mode=mode,validation=True)
    d=tmp_path/'cpp';include=d if mode=='source' else package/'include'
    obj=d/'foundation.cpp' if mode=='source' else package/'taut-foundation.lib'
    executable,_=compile_cpp(tmp_path/'build',(EXAMPLE/'AllocationFault.cpp').read_text(),include=[d,include],objects=[obj])
    run([executable])

def external(names,header='child.hpp'):
    return {n:dict(header=header,type='taut::'+n,owner=OWNER,descriptor_contract=1,codec_contract=1,capabilities=sorted(CAPABILITIES)) for n in names}

@pytest.mark.parametrize('child_mode,parent_mode',[('source','source'),('package','package'),('source','package'),('package','source')])
def test_independent_disabled_child_shared_owner(tmp_path,package,child_mode,parent_mode):
    child=dataclasses.replace(SCHEMA,messages={'Content':SCHEMA.messages['Content']})
    parent=dataclasses.replace(child,messages={**child.messages,**schema(Parent=Msg(child=F(1,Ref('Content')))).messages})
    owner=tmp_path/'owner';bindings={'cpp':{'source_root':str(owner)}}
    use_source='source' in (child_mode,parent_mode)
    if use_source:
        emit(schema(OwnerUser=Msg()),tmp_path/'owner-user',langs=['cpp'],services=[],runtime=True,validation=True,runtime_bindings=bindings)
    else:bindings={'cpp':{'artifact':str(package)}}
    emit(child,tmp_path/'child',langs=['cpp'],services=[],runtime_mode=child_mode,runtime_bindings=bindings if use_source else None,schema_identity='child')
    cd=tmp_path/'child/cpp';shutil.copyfile(cd/'api.hpp',cd/'child.hpp')
    # Build an independent TU before the parent exists, against one actual owner.
    include=owner if use_source else package/'include'
    child_tu=tmp_path/'child.cpp';child_tu.write_text('#include "child.hpp"\n#include "taut/reports.hpp"\nconst taut::MessageDescriptor* child_descriptor(){return &taut::Content::descriptor();}\ntaut::validation::ValidationReport child_report(){return {};}')
    child_obj=tmp_path/'child.obj'
    run([shutil.which('clang++'),'-std=c++20','-fno-rtti','-I',cd,'-I',include,'-c',child_tu,'-o',child_obj])
    before=(cd/'child.hpp').read_bytes()
    emit(parent,tmp_path/'parent',langs=['cpp'],services=[],runtime_mode=parent_mode,validation=True,runtime_bindings=bindings,
         schema_identity='parent',cpp_external_types=external(('Kind','Content')))
    pd=tmp_path/'parent/cpp'
    source='''#include "api.hpp"
#include <cassert>
#include <type_traits>
const taut::MessageDescriptor* child_descriptor();
taut::validation::ValidationReport child_report();
static_assert(std::is_same_v<decltype(taut::Parent{}.validate()),decltype(child_report())>);
int main(){auto c=std::make_shared<taut::Content>();c->kind=taut::Kind::Text;taut::Parent p{c};assert(child_descriptor()==&taut::Content::descriptor());assert(!p.is_valid());assert(p.is_valid(false));c->text="";assert(p.is_valid());}
'''
    owner_obj=owner/'foundation.cpp' if use_source else package/'taut-foundation.lib'
    executable,_=compile_cpp(tmp_path/'build',source,include=[pd,cd,include],objects=[child_obj,owner_obj]);run([executable])
    assert (cd/'child.hpp').read_bytes()==before
    assert 'Content::validate' not in before.decode()

def tree(root):return {p.relative_to(root).as_posix():p.read_bytes() for p in root.rglob('*') if p.is_file()}

@pytest.mark.parametrize('file',['api.hpp','foundation.cpp','taut/cbor.hpp','taut/descriptors.hpp','taut/reports.hpp','taut/validation.hpp'])
def test_modified_handwritten_preserved(tmp_path,file):
    for existing in (False,True):
        root=tmp_path/str(existing)
        if existing:emit(SCHEMA,root,langs=['cpp'],services=[],runtime=True,validation=True)
        path=root/'cpp'/file;path.parent.mkdir(parents=True,exist_ok=True);path.write_text('// user content')
        before=tree(tmp_path)
        with pytest.raises(ValueError):emit(SCHEMA,root,langs=['cpp'],services=[],runtime=True,validation=False)
        assert tree(tmp_path)==before

def test_shared_users_transitions(tmp_path):
    owner=tmp_path/'owner';bindings={'cpp':{'source_root':str(owner)}}
    for name in ('a','b'):emit(SCHEMA,tmp_path/name,langs=['cpp'],services=[],runtime=True,validation=True,runtime_bindings=bindings)
    emit(SCHEMA,tmp_path/'a',langs=['cpp'],services=[],runtime_mode='package')
    assert (owner/'taut/validation.hpp').exists()
    emit(SCHEMA,tmp_path/'b',langs=['cpp'],services=[],runtime=True,runtime_bindings=bindings)
    assert not (owner/'taut/validation.hpp').exists() and (owner/'taut/descriptors.hpp').exists()
    emit(SCHEMA,tmp_path/'b',langs=['cpp'],services=[],runtime_mode='package')
    assert not [p for p in owner.rglob('*') if p.is_file()]

def test_unavailable_previous_owner_refused(tmp_path):
    owner=tmp_path/'owner';bindings={'cpp':{'source_root':str(owner)}}
    emit(SCHEMA,tmp_path/'schema',langs=['cpp'],services=[],runtime=True,runtime_bindings=bindings)
    # A missing old registry cannot be silently treated as a disposable owner.
    (owner/'.taut-cpp-runtime.json').unlink()
    before=tree(tmp_path)
    with pytest.raises(ValueError,match='previous.*unavailable'):
        emit(SCHEMA,tmp_path/'schema',langs=['cpp'],services=[],runtime_mode='package')
    assert tree(tmp_path)==before

@pytest.mark.parametrize('name',['descriptor','taut_binding','validate','is_valid','switch'])
def test_generated_native_collisions_prewrite(tmp_path,name):
    s=schema(Record=Msg(**{name:F(1,INT)}))
    with pytest.raises(ValueError,match='collision'):
        emit(s,tmp_path,langs=['cpp'],services=[],runtime=True,validation=True)
    assert not list(tmp_path.iterdir())

@pytest.mark.parametrize('name',['descriptor','taut_binding','validate','is_valid','FieldBinding','EnumMemberDescriptor','OneOfMemberDescriptor','CompatibleMessage','CompatibleEnum'])
def test_type_and_own_method_collisions_prewrite(tmp_path,name):
    s=schema(**{name:Msg(value=F(1,INT))})
    with pytest.raises(ValueError,match='collision'):
        emit(s,tmp_path,langs=['cpp'],services=[],runtime=True,validation=True)
    assert not list(tmp_path.iterdir())

@pytest.mark.parametrize('name',['validate','is_valid'])
def test_message_validation_name_allowed_when_disabled(tmp_path,name):
    s=schema(**{name:Msg(value=F(1,INT))})
    emit(s,tmp_path,langs=['cpp'],services=[],runtime=True)
    d=tmp_path/'cpp'
    executable,_=compile_cpp(tmp_path/'build','#include "api.hpp"\n#include <cassert>\nint main(){taut::'+name+' v{7};assert(v.value==7);assert(taut::'+name+'::descriptor().name()=="'+name+'");}',include=[d],objects=[d/'foundation.cpp']);run([executable])

@pytest.mark.parametrize('name',['metadata','name','__private','validate','is_valid'])
def test_native_legal_names_and_disabled_methods(tmp_path,name):
    s=schema(Record=Msg(**{name:F(1,INT)}))
    emit(s,tmp_path,langs=['cpp'],services=[],runtime=True,validation=False)
    d=tmp_path/'cpp'
    executable,_=compile_cpp(tmp_path/'build','#include "api.hpp"\n#include <cassert>\nint main(){taut::Record r{7};assert(r.'+name+'==7);assert(taut::Record::descriptor().fields()[0].name()=="'+name+'");}',include=[d],objects=[d/'foundation.cpp'])
    run([executable])

def test_mutual_recursion_and_primitive_borrows(tmp_path):
    from taut.ir.dsl import BOOL,BYTES,FLOAT,List,Map
    s=schema(A=Msg(b=F(1,Ref('B'),optional=True)),B=Msg(a=F(1,Ref('A'),optional=True),text=F(2,STR),blob=F(3,BYTES),number=F(4,INT),flag=F(5,BOOL),ratio=F(6,FLOAT),flags=F(7,List(BOOL))))
    emit(s,tmp_path,langs=['cpp'],services=[],runtime=True,validation=True)
    d=tmp_path/'cpp'
    source='''#include "api.hpp"
#include <cassert>
int main(){const char bytes[]="borrowed";taut::B b{};b.text=bytes;b.blob=bytes;b.number=42;b.flag=false;b.ratio=1.5;b.flags={true,false};auto ref=taut::ValueRef::borrow(b);assert(ref.field(1).text().data()==bytes);assert(ref.field(2).text().data()==bytes);assert(ref.field(3).integer()==42);assert(!ref.field(4).boolean());assert(ref.field(5).floating()==1.5);assert(ref.field(6).item(0).boolean());assert(!ref.field(6).item(1).boolean());auto a=std::make_shared<taut::A>();auto child=std::make_shared<taut::B>(b);a->b=child;child->a=a;assert(!a->is_valid());assert(a->validate().issues()[0].code()=="validation.ownership_cycle");assert(a->is_valid(false));child->a.reset();}
'''
    executable,_=compile_cpp(tmp_path/'build',source,include=[d],objects=[d/'foundation.cpp']);run([executable])

@pytest.mark.parametrize('replacement',['descriptor','codec','capabilities','guard','owner'])
def test_actual_replaced_link_artifact_rejected(tmp_path,package,replacement):
    emit(SCHEMA,tmp_path,langs=['cpp'],services=[],runtime_mode='package',validation=True)
    values=dict(owner='taut.cpp.foundation',descriptor=1,codec=1,capabilities=7,guard='0x5441555443505031ULL')
    if replacement=='owner':values[replacement]='other.owner'
    elif replacement=='guard':values[replacement]='0'
    else:values[replacement]=0
    # Generation already finished against the actual canonical package. Replace
    # only the compiled owner's linked export; checker source/labels cannot help.
    cpp=tmp_path/'replacement.cpp';cpp.write_text('#include "taut/foundation.hpp"\nnamespace taut {const FoundationContract& foundation_contract() noexcept {static constexpr FoundationContract c{"'+values['owner']+'",'+str(values['descriptor'])+','+str(values['codec'])+',1,'+str(values['capabilities'])+','+values['guard']+',"old.actual.artifact"};return c;}}')
    executable,_=compile_cpp(tmp_path/'build','#include "api.hpp"\nint main(){return taut::Content{}.is_valid(false)?0:2;}',include=[tmp_path/'cpp',package/'include'],objects=[cpp])
    result=run([executable],ok=False)
    assert result.returncode!=0 and 'incompatible actual C++ foundation export' in result.stderr

def test_unequal_compatible_build(tmp_path,package):
    emit(SCHEMA,tmp_path,langs=['cpp'],services=[],runtime_mode='package',validation=True)
    cpp=tmp_path/'patch.cpp';cpp.write_text('#include "taut/foundation.hpp"\nnamespace taut {const FoundationContract& foundation_contract() noexcept {static constexpr FoundationContract c{"taut.cpp.foundation",1,1,1,7,0x5441555443505031ULL,"compatible.patch.99"};return c;}}')
    executable,_=compile_cpp(tmp_path/'build','#include "api.hpp"\n#include <cassert>\nint main(){taut::Content c{};c.kind=taut::Kind::Empty;assert(c.is_valid());}',include=[tmp_path/'cpp',package/'include'],objects=[cpp]);run([executable])

def test_actual_old_checker_cannot_ignore_new_requirements(tmp_path,package):
    emit(SCHEMA,tmp_path,langs=['cpp'],services=[],runtime_mode='package',validation=True)
    stale=tmp_path/'stale/taut';stale.mkdir(parents=True)
    (stale/'foundation.hpp').write_text('''#pragma once
#include <string_view>
#include <cstdint>
#include <stdexcept>
namespace taut {
struct FoundationContract{std::string_view owner;unsigned descriptor,codec,adapter,capabilities;std::uint64_t guard;std::string_view build;};
const FoundationContract& foundation_contract() noexcept;
inline void require_foundation() {} // Actual old checker ignores all requirements.
}
''')
    cpp=tmp_path/'old.cpp';cpp.write_text('#include "taut/foundation.hpp"\nnamespace taut {const FoundationContract& foundation_contract() noexcept {static constexpr FoundationContract c{"taut.cpp.foundation",1,0,1,7,0x5441555443505031ULL,"old.checker"};return c;}}')
    executable,_=compile_cpp(tmp_path/'build','#include "api.hpp"\nint main(){}',include=[tmp_path/'cpp',stale.parent,package/'include'],objects=[cpp])
    result=run([executable],ok=False)
    assert result.returncode!=0 and 'incompatible actual C++ foundation export' in result.stderr

def test_actual_old_child_diagnostic_and_split_link_owner(tmp_path,package):
    child=schema(Child=Msg(n=F(1,INT)))
    parent=dataclasses.replace(child,messages={**child.messages,**schema(Parent=Msg(child=F(1,Ref('Child')))).messages})
    emit(parent,tmp_path,langs=['cpp'],services=[],runtime_mode='package',validation=True,cpp_external_types=external(('Child',),'old.hpp'))
    d=tmp_path/'cpp'
    (d/'old.hpp').write_text('#pragma once\n#include "taut/cbor.hpp"\nnamespace taut {struct Child {long long n{};void to_cbor(Buf&)const{};static DecodeResult<Child> try_from_cbor(const Cbor&){return DecodeResult<Child>::success({});}};}')
    _,result=compile_cpp(tmp_path/'old-build','#include "api.hpp"\nint main(){}',include=[d,package/'include'],objects=[package/'taut-foundation.lib'],ok=False)
    assert result.returncode!=0 and 'requires mandatory descriptor/typed adapter contract 1; regenerate/rebind dependency' in result.stderr
    # Source/source private owners both supplying definitions are a link error.
    first=tmp_path/'first.cpp';second=tmp_path/'second.cpp'
    first.write_bytes((package/'foundation.cpp').read_bytes());second.write_bytes(first.read_bytes())
    _,result=compile_cpp(tmp_path/'split-build','int main(){}',include=[package/'include'],objects=[first,second],ok=False)
    diagnostic=result.stdout+result.stderr
    assert result.returncode!=0 and ('already defined' in diagnostic or 'duplicate symbol' in diagnostic or 'multiple definition' in diagnostic)

def test_metadata_like_enum_members_via_native_ir(tmp_path):
    from taut.facts import EnumDef,EnumRef,OneOfRule,CaseRule,MessageDef,FieldDef,Schema,Scalar
    e=EnumDef('MetadataChoice',{'name':0,'metadata':1,'empty':2})
    fields=(FieldDef('tag',1,EnumRef(e.name),oneof=OneOfRule(e.name)),FieldDef('value',2,Scalar('str'),optional=True,cases=(CaseRule('tag',e.name,'name'),CaseRule('tag',e.name,'metadata'))))
    s=Schema({e.name:e},{'Record':MessageDef('Record',fields)})
    emit(s,tmp_path,langs=['cpp'],services=[],runtime=True,validation=True)
    d=tmp_path/'cpp'
    source='#include "api.hpp"\n#include <cassert>\nint main(){taut::Record r{};r.tag=taut::MetadataChoice::Name;assert(!r.is_valid());r.value="";assert(r.is_valid());r.tag=taut::MetadataChoice::Metadata;assert(r.is_valid());assert(taut::EnumTraits<taut::MetadataChoice>::descriptor().find(0)->name=="name");}'
    executable,_=compile_cpp(tmp_path/'build',source,include=[d],objects=[d/'foundation.cpp']);run([executable])

def test_engine_free_actual_package_and_required_engine_refusal(tmp_path):
    package=build_foundation(tmp_path/'foundation',validation=False)
    assert not (package/'include/taut/validation.hpp').exists()
    emit(SCHEMA,tmp_path/'off',langs=['cpp'],services=[],runtime_mode='package',runtime_bindings={'cpp':{'artifact':str(package)}})
    d=tmp_path/'off/cpp'
    executable,_=compile_cpp(tmp_path/'build','#include "api.hpp"\n#include <cassert>\nint main(){assert(taut::Content::descriptor().fields().size()==6);}',include=[d,package/'include'],objects=[package/'taut-foundation.lib']);run([executable])
    before=tree(tmp_path)
    with pytest.raises(ValueError,match='contracts/capabilities'):
        emit(SCHEMA,tmp_path/'on',langs=['cpp'],services=[],runtime_mode='package',validation=True,runtime_bindings={'cpp':{'artifact':str(package)}})
    assert tree(tmp_path)==before

def test_boundary_long_map_key_paths_owned_snapshot(tmp_path):
    emit(SCHEMA,tmp_path,langs=['cpp'],services=[],runtime=True,validation=True)
    d=tmp_path/'cpp'
    source='''#include "api.hpp"
#include <cassert>
#include <limits>
int main(){auto bad=std::make_shared<taut::Content>();bad->kind=taut::Kind::Text;
taut::Wrapper w{};w.by_int={{std::numeric_limits<long long>::min(),bad},{std::numeric_limits<long long>::max(),bad},{0,bad}};
std::string long_key(1000,'x');w.by_text={{long_key,bad}};
auto report=w.validate();assert(report.issues().size()==4);
const auto zero=taut::validation::PathSegment::for_key("int",std::string_view("\\x00",1));
const auto max=taut::validation::PathSegment::for_key("int",std::string_view("\\x1b\\x7f\\xff\\xff\\xff\\xff\\xff\\xff\\xff",9));
const auto min=taut::validation::PathSegment::for_key("int",std::string_view("\\x3b\\x7f\\xff\\xff\\xff\\xff\\xff\\xff\\xff",9));
assert(report.issues()[1].path()[1].key_cbor_base64()==zero.key_cbor_base64());
assert(report.issues()[2].path()[1].key_cbor_base64()==max.key_cbor_base64());
assert(report.issues()[3].path()[1].key_cbor_base64()==min.key_cbor_base64());
const std::string owned(*report.issues()[0].path()[1].key_cbor_base64());w.by_text.clear();long_key.clear();assert(report.issues()[0].path()[1].key_cbor_base64()==owned);
try{taut::validation::PathSegment::for_key("bool",std::string_view("\\x00",1));assert(false);}catch(const std::invalid_argument&){}
}
'''
    executable,_=compile_cpp(tmp_path/'build',source,include=[d],objects=[d/'foundation.cpp']);run([executable])

@pytest.mark.parametrize('mode',['source','package'])
def test_msvc_native_execution(tmp_path,package,mode):
    cl=shutil.which('cl')
    if cl is None:pytest.skip('MSVC is only available on the activated Windows toolchain')
    emit(SCHEMA,tmp_path,langs=['cpp'],services=[],runtime_mode=mode,validation=True)
    d=tmp_path/'cpp';include=d if mode=='source' else package/'include'
    objects=[package/'taut-foundation.lib']
    if mode=='source':
        obj=tmp_path/'foundation.obj'
        run([cl,'/nologo','/std:c++20','/EHsc','/GR-','/I'+str(d),'/c',d/'foundation.cpp','/Fo:'+str(obj)])
        objects=[obj]
    cpp=tmp_path/'main.cpp';cpp.write_bytes((EXAMPLE/'Conformance.cpp').read_bytes())
    exe=tmp_path/'msvc.exe'
    run([cl,'/nologo','/std:c++20','/EHsc','/GR-','/I'+str(d),'/I'+str(include),cpp,'/Fo:'+str(tmp_path/'main.obj'),'/Fe:'+str(exe),*objects])
    assert run([exe]).stdout.splitlines()==python_rows()

def test_immediate_metadata_rejects_mutable_backing(tmp_path,package):
    source='''#include "taut/descriptors.hpp"
taut::EnumMemberDescriptor members[]={{"a",0,{}}};
taut::EnumDescriptor descriptor{"E","E",members,{},"fingerprint"};
int main(){}
'''
    _,result=compile_cpp(tmp_path/'build',source,include=[package/'include'],ok=False)
    assert result.returncode!=0 and ('constant expression' in result.stderr or 'consteval' in result.stderr)

def test_malformed_known_constraint_is_configuration_error(tmp_path,package):
    source='''#include "taut/descriptors.hpp"
#include <cassert>
inline constexpr taut::ConstraintDescriptor constraints[]={{"taut.oneof.v1",{}}};
inline constexpr taut::MessageDescriptor bad{"Bad","Bad",{},{},constraints,{},{},{},{},{},"fp"};
int main(){try{taut::descriptor_detail::check_message(bad);assert(false);}catch(const std::logic_error& e){assert(std::string_view(e.what()).find("constraint grammar")!=std::string_view::npos);}}
'''
    executable,_=compile_cpp(tmp_path/'build',source,include=[package/'include']);run([executable])

@pytest.mark.parametrize('different',['equivalent','enum','effective','codec'])
def test_actual_external_facts_guard(tmp_path,package,different):
    child=dataclasses.replace(SCHEMA,messages={'Content':SCHEMA.messages['Content']})
    doc=schema_json(child)
    doc['messages'][0]['fields'].reverse()
    doc['enums'][0]['members']=dict(reversed(list(doc['enums'][0]['members'].items())))
    if different=='enum':doc['enums'][0]['members']['empty']=99
    if different=='effective':
        doc['options']={'max_depth':16};doc['effective']['max_depth']=16
        doc['messages'][0]['effective']['max_depth']=16
    actual=schema_from_json(doc)
    emit(actual,tmp_path/'child',langs=['cpp'],services=[],runtime_mode='package',schema_identity='child.patch.4',forward_compat=different=='codec')
    cd=tmp_path/'child/cpp';shutil.copyfile(cd/'api.hpp',cd/'child.hpp')
    parent=dataclasses.replace(child,messages={**child.messages,**schema(Parent=Msg(child=F(1,Ref('Content')))).messages})
    emit(parent,tmp_path/'parent',langs=['cpp'],services=[],runtime_mode='package',validation=True,schema_identity='parent.patch.7',cpp_external_types=external(('Kind','Content')))
    executable,_=compile_cpp(tmp_path/'build','#include "api.hpp"\nint main(){taut::Parent p{std::make_shared<taut::Content>()};return p.is_valid(false)?0:2;}',include=[tmp_path/'parent/cpp',cd,package/'include'],objects=[package/'taut-foundation.lib'])
    result=run([executable],ok=different=='equivalent')
    if different!='equivalent':assert result.returncode!=0 and 'incompatible imported C++ descriptor/codec facts' in result.stderr

@pytest.mark.parametrize('key,value',[('owner','wrong'),('descriptor_contract',True),('codec_contract',2),('capabilities',[]),('unknown',True)])
def test_binding_prewrite_configuration(tmp_path,key,value):
    with pytest.raises(ValueError):emit(SCHEMA,tmp_path,langs=['cpp'],services=[],runtime=True,runtime_bindings={'cpp':{key:value}})
    assert not list(tmp_path.iterdir())

def test_cli_runtime_alias_conflict_and_external_help(tmp_path):
    from taut.cli import main
    schema_path=ROOT/'dev-docs/examples/java-oneof/content.taut.py'
    args=['gen',str(schema_path),'--lang','cpp','--api-only','--out',str(tmp_path/'good')]
    assert main([*args,'--runtime','source','--runtime','source','--with-runtime','--with-validation'])==0
    assert 'Content::validate' in (tmp_path/'good/cpp/api.hpp').read_text()
    before=tree(tmp_path)
    with pytest.raises(ValueError,match='conflict'):main([*args,'--runtime','package','--with-runtime'])
    assert tree(tmp_path)==before
    result=run([sys.executable,'-m','taut.cli','gen','--help'])
    assert '--cpp-external-types' in result.stdout and '--go-external-types' in result.stdout
    assert 'C++' in result.stdout and 'Go' in result.stdout

def test_emit_all_keyword_forwarding(tmp_path):
    from taut.gen.scaffold import emit_all
    # A real existing service keeps optional service source under the schema owner.
    service_schema=load_schema(ROOT/'src/taut/corpus/api.taut.py') if (ROOT/'src/taut/corpus/api.taut.py').exists() else None
    if service_schema is None:
        from taut.corpus import build
        service_schema=load_schema(build.IR_PATH)
    service=next(iter(service_schema.services))
    emit_all(service_schema,service,tmp_path,langs=['cpp'],runtime_mode='source',validation=True)
    text=(tmp_path/'cpp/api.hpp').read_text()
    assert '::validate(bool recursive)' in text and (tmp_path/'cpp/client.hpp').exists()

@pytest.mark.parametrize('fault',[1,3,7])
def test_interrupted_write_fails_closed(tmp_path,monkeypatch,fault):
    import taut.gen.python_runtime as common
    emit(SCHEMA,tmp_path,langs=['cpp'],services=[],runtime=True)
    handwritten=tmp_path/'cpp/keep.txt';handwritten.write_text('protected')
    original=common.os.replace if hasattr(common,'os') else os.replace
    count=0
    def fail(source,target):
        nonlocal count
        count+=1
        if count==fault:raise OSError('injected durable write interruption')
        return original(source,target)
    with monkeypatch.context() as context:
        context.setattr(os,'replace',fail)
        with pytest.raises(OSError,match='injected'):
            emit(SCHEMA,tmp_path,langs=['cpp'],services=[],runtime=True,validation=True)
    assert handwritten.read_text()=='protected'
    before=tree(tmp_path)
    if fault==1:
        # Nothing replaced: the original generation remains usable/retryable.
        emit(SCHEMA,tmp_path,langs=['cpp'],services=[],runtime=True)
    else:
        with pytest.raises(ValueError,match='modified|unknown|missing|unsafe'):
            emit(SCHEMA,tmp_path,langs=['cpp'],services=[],runtime=True,validation=True)
        assert tree(tmp_path)==before

def test_obstruction_and_existing_lock_preserved(tmp_path):
    d=tmp_path/'cpp';d.mkdir();(d/'taut').write_text('handwritten obstruction')
    before=tree(tmp_path)
    with pytest.raises(ValueError):emit(SCHEMA,tmp_path,langs=['cpp'],services=[],runtime=True)
    assert tree(tmp_path)==before
    root=tmp_path/'locked';root.mkdir();(root/'.taut-generation.lock').write_text('existing owner lock')
    before=tree(tmp_path)
    with pytest.raises(ValueError,match='lock'):
        emit(SCHEMA,tmp_path/'schema',langs=['cpp'],services=[],runtime=True,runtime_bindings={'cpp':{'source_root':str(root)}})
    assert tree(tmp_path)==before

@pytest.mark.skipif(os.name!='nt',reason='Windows namespace contract')
@pytest.mark.parametrize('suffix',['bad.','bad ','bad:ads'])
def test_raw_namespace_rejected_before_path_coercion(tmp_path,suffix):
    raw='\\\\?\\'+str(tmp_path)+'\\'+suffix
    with pytest.raises(ValueError,match='namespace'):
        emit(SCHEMA,raw,langs=['cpp'],services=[],runtime=True)
    with pytest.raises(ValueError,match='namespace'):
        emit(SCHEMA,tmp_path/'schema',langs=['cpp'],services=[],runtime=True,runtime_bindings={'cpp':{'source_root':raw}})
    assert not list(tmp_path.iterdir())

@pytest.mark.skipif(os.name!='nt',reason='Windows junction contract')
def test_junction_and_physical_equivalent_shared_users(tmp_path):
    actual=tmp_path/'actual';actual.mkdir();junction=tmp_path/'junction'
    run(['cmd','/c','mklink','/J',junction,actual])
    before=tree(tmp_path)
    with pytest.raises(ValueError,match='unsafe'):
        emit(SCHEMA,tmp_path/'schema',langs=['cpp'],services=[],runtime=True,runtime_bindings={'cpp':{'source_root':str(junction)}})
    assert tree(tmp_path)==before
    bindings={'cpp':{'source_root':str(actual)}}
    emit(SCHEMA,tmp_path/'a',langs=['cpp'],services=[],runtime=True,validation=True,runtime_bindings=bindings)
    alternate=actual/'unused'/'..'
    emit(SCHEMA,tmp_path/'a',langs=['cpp'],services=[],runtime=True,validation=False,runtime_bindings={'cpp':{'source_root':str(alternate)}})
    registry=json.loads((actual/'.taut-cpp-runtime.json').read_text())
    assert len(registry['users'])==1 and not (actual/'taut/validation.hpp').exists()
