"""Executable Java-8 OneOf/reference parity, runtime distributions and ownership."""
import dataclasses
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import types
import zipfile
import pytest
from taut.gen.scaffold import emit, emit_all, python_api
from taut.gen.java_runtime import (OWNER, CAPABILITIES, FILES, ENGINE, canonical_sources,
                                   build_foundation, verify_artifact, canonical_path)
from taut.ir.dsl import STR, INT, Enum, F, Msg, Ref, schema
from taut.ir.load import load_schema
from taut.wire import cbor

ROOT=Path(__file__).resolve().parents[2]
EXAMPLE=ROOT/'dev-docs/examples/java-oneof'
SCHEMA=load_schema(EXAMPLE/'content.taut.py')


def run(args, *, ok=True, cwd=None):
    r=subprocess.run(list(map(str,args)),cwd=cwd,capture_output=True,encoding='utf-8')
    if ok: assert r.returncode==0,r.stdout+r.stderr
    return r


def compile_java(directory, sources, *, dependencies=(), ok=True):
    directory.mkdir(parents=True,exist_ok=True)
    javac=shutil.which('javac')
    assert javac,'Java readiness toolchain is required'
    args=[javac,'--release','8','-encoding','UTF-8','-d',directory]
    if dependencies:args+=['-cp',os.pathsep.join(map(str,dependencies))]
    return run([*args,*sources],ok=ok)


def execute(classes, main='taut.Conformance', *, dependencies=(), ok=True):
    return run(['java','-Dfile.encoding=UTF-8','-cp',os.pathsep.join(map(str,(classes,*dependencies))),main],ok=ok)


@pytest.fixture(scope='module')
def jar(tmp_path_factory):
    return build_foundation(tmp_path_factory.mktemp('java-foundation')/'foundation.jar')


@pytest.fixture(scope='module')
def descriptor_jar(tmp_path_factory):
    return build_foundation(tmp_path_factory.mktemp('java-descriptors')/'foundation.jar',validation=False)


def python_rows():
    m=types.ModuleType('_java_oneof_reference');sys.modules[m.__name__]=m
    exec(python_api(SCHEMA,validation=True),m.__dict__)
    rows=[]
    def report(name,value,recursive=True):
        r=value.validate(recursive=recursive)
        assert value.is_valid(recursive=recursive)==(r.is_valid() and r.is_complete())
        def path(p):
            return '/'.join('f='+s.field_name if s.kind=='field' else 'i='+str(s.index) if s.kind=='index' else 'k='+s.key_type+','+s.key_cbor_base64 for s in p)
        row=[name,r.scope,str(r.is_valid()).lower(),str(r.is_complete()).lower()]
        row+=['I:'+i.code+':'+i.rule+':'+path(i.path) for i in r.issues]
        row+=['D:'+d.reason_code+':'+d.rule+':'+path(d.path) for d in r.deferred_checks]
        rows.append('\t'.join(row))
    def content(kind):return m.Content(kind=kind)
    c=content(m.Kind.text);report('missing',c);c.text='';report('empty',c);c.number=0;report('extra',c);report('roundtrip',c)
    c.kind=m.Kind.number;c.text=None;report('zero',c)
    c.kind=m.Kind.flag;c.number=None;c.flag=False;report('false',c)
    c.flag=None;c.kind=m.Kind.items;c.items=[];report('empty-list',c)
    c.items=None;c.kind=m.Kind.empty;report('payload-free',c)
    c.kind=None;c.child=content(m.Kind.text);report('bad-tag-child',c)
    c.kind=m.Kind.empty;report('nonselected-child',c)
    c.kind=m.Kind.child;c.child=c;report('cycle',c)
    bad=content(m.Kind.text)
    w=m.Wrapper(bad,[bad,bad],{'z':bad,'':bad,'aa':bad},{-1:bad,24:bad,0:bad},{True:bad,False:bad})
    report('wrapper',w);report('local',w,False)
    v=m.Virtual(child=bad);report('virtual-child',v);bad.text='';report('virtual-repaired',v);report('virtual-local',v,False)
    report('independent',m.Multi(left=None,right=m.Kind.number))
    report('plain',m.Plain(0,None,None))
    return rows


@pytest.mark.parametrize('mode',['source','package',None])
def test_reference_behavior_real_java8(tmp_path,jar,mode):
    emit(SCHEMA,tmp_path,langs=['java'],services=[],runtime_mode=mode,validation=True,
         runtime_bindings={'java':{'artifact':str(jar)}} if mode!='source' else None)
    d=tmp_path/'java';shutil.copyfile(EXAMPLE/'Conformance.java',d/'Conformance.java')
    deps=() if mode=='source' else (jar,)
    classes=tmp_path/'classes';compile_java(classes,sorted(d.rglob('*.java')),dependencies=deps)
    output=execute(classes,dependencies=deps).stdout.splitlines()
    assert output==python_rows()
    text=(d/'api.java').read_text(encoding='utf-8')
    assert 'class Content {' in text and 'public class Content' not in text
    assert 'public Kind kind;' not in text[text.index('class Virtual {'):text.index('final class Virtual$Codec')]
    assert not any(s in text for s in ['java.lang.reflect','MethodHandles','getDeclaredField'])
    if mode=='source':
        for name,data in canonical_sources().items():assert (d/name).read_bytes()==data
    else: assert not (d/'Cbor.java').exists()


@pytest.mark.parametrize('mode',['source','package',None])
def test_descriptor_without_engine(tmp_path,descriptor_jar,mode):
    emit(SCHEMA,tmp_path,langs=['java'],services=[],runtime_mode=mode)
    d=tmp_path/'java';text=(d/'api.java').read_text(encoding='utf-8')
    assert 'public static taut.validation.descriptors.MessageDescriptor descriptor()' in text
    assert ' validate(' not in text and ' isValid(' not in text
    assert not (d/ENGINE).exists()
    harness=d/'Inspect.java';harness.write_text('package taut; public class Inspect { public static void main(String[] a) { System.out.println(Content.descriptor().fields().size()); Content c=new Content();c.kind=Kind.EMPTY;System.out.println(Cbor.encode(c.toCbor()).length>0); } }',encoding='utf-8')
    deps=() if mode=='source' else (descriptor_jar,)
    classes=tmp_path/'classes';compile_java(classes,sorted(d.rglob('*.java')),dependencies=deps)
    assert execute(classes,'taut.Inspect',dependencies=deps).stdout.splitlines()==['6','true']
    assert not (classes/'taut/validation/ValidationEngine.class').exists()


def external(names):
    return {n:dict(type='taut.'+n,owner=OWNER,descriptor_contract=1,codec_contract=1,capabilities=sorted(CAPABILITIES)) for n in names}


@pytest.mark.parametrize('child_mode,parent_mode',[('source','source'),('package','package'),('source','package'),('package','source')])
def test_independent_disabled_child_shared_nominal_owner(tmp_path,jar,child_mode,parent_mode):
    # No dependency regeneration: child is compiled once before parent generation.
    child=dataclasses.replace(SCHEMA,messages={'Content':SCHEMA.messages['Content']})
    parent=dataclasses.replace(child,messages={**child.messages,**schema(Parent=Msg(child=F(1,Ref('Content')))).messages})
    owner=tmp_path/'owner'
    bindings={'java':{'source_root':str(owner)}} if 'source' in (child_mode,parent_mode) else {'java':{'artifact':str(jar)}}
    if child_mode=='package' and parent_mode=='source':
        emit(schema(EngineUser=Msg()),tmp_path/'engine-user',langs=['java'],services=[],runtime_mode='source',validation=True,runtime_bindings=bindings)
    emit(child,tmp_path/'child',langs=['java'],services=[],runtime_mode=child_mode,runtime_bindings=bindings,schema_identity='child')
    cd=tmp_path/'child/java';before=(cd/'api.java').read_bytes()
    # One foundation artifact/class directory supplies codec, metadata and reports.
    if child_mode=='source':
        foundation=tmp_path/'foundation';compile_java(foundation,sorted(owner.rglob('*.java')))
        # Enabled parent's engine must be supplied by chosen owner, never child methods.
        # Generate an enabled source owner user before parent link, then compile owner once.
        emit(schema(EngineUser=Msg()),tmp_path/'engine-user',langs=['java'],services=[],runtime_mode='source',validation=True,runtime_bindings=bindings)
        compile_java(foundation,sorted(owner.rglob('*.java')))
    elif parent_mode=='source':
        emit(schema(EngineUser=Msg()),tmp_path/'engine-user',langs=['java'],services=[],runtime_mode='source',validation=True,runtime_bindings=bindings)
        foundation=tmp_path/'foundation';compile_java(foundation,sorted(owner.rglob('*.java')))
    else: foundation=jar
    child_classes=tmp_path/'child-classes';compile_java(child_classes,[cd/'api.java'],dependencies=(foundation,))
    emit(parent,tmp_path/'parent',langs=['java'],services=[],runtime_mode=parent_mode,validation=True,
         runtime_bindings=bindings,java_external_types=external(['Kind','Content']),schema_identity='parent')
    pd=tmp_path/'parent/java'
    assert (cd/'api.java').read_bytes()==before
    harness=pd/'Independent.java';harness.write_text('''package taut;
import taut.validation.*;
import taut.validation.descriptors.*;
public class Independent {
 public static void main(String[] a) {
  Content c=new Content();c.kind=Kind.TEXT;Parent p=new Parent();p.child=c;
  ValidationReport r=p.validate();ValidationIssue i=r.issues().get(0);
  if(!i.code().equals("oneof.payload_missing") || p.isValid() || !p.isValid(false))throw new AssertionError();
  if(Parent.descriptor().fields().get(0).type().message()!=Content.descriptor())throw new AssertionError("split descriptor");
  if(!i.getClass().equals(ValidationIssue.class) || !r.getClass().equals(ValidationReport.class))throw new AssertionError("split report");
  Content c2=Content.decode(Cbor.encode(c.toCbor()));if(c2.kind!=Kind.TEXT)throw new AssertionError("split codec");
  System.out.println("independent PASS");
 }
}''',encoding='utf-8')
    pc=tmp_path/'parent-classes';compile_java(pc,sorted(pd.rglob('*.java')),dependencies=(child_classes,foundation))
    assert 'PASS' in execute(pc,'taut.Independent',dependencies=(child_classes,foundation)).stdout


@pytest.mark.parametrize('config',[{'owner':'split'}, {'module':'other'}, {'descriptor_contract':2}, {'codec_contract':0}, {'descriptor_contract':True}, {'capabilities':['future']}, {'unknown':1}])
def test_bad_binding_preflight_no_writes(tmp_path,config):
    with pytest.raises(ValueError):emit(SCHEMA,tmp_path,langs=['java'],runtime_mode='source',runtime_bindings={'java':config})
    assert not list(tmp_path.iterdir())


def test_artifact_provenance_and_no_engine_rejection(tmp_path,jar,descriptor_jar):
    data=verify_artifact(jar,validation=True)
    assert set(data['sources'])==set(FILES)
    with zipfile.ZipFile(jar) as z:
        for name,content in canonical_sources().items():assert z.read('META-INF/taut-sources/'+name)==content
        payload={n:z.read(n) for n in z.namelist()}
    with pytest.raises(ValueError,match='validation engine'):
        emit(SCHEMA,tmp_path/'no-engine',langs=['java'],validation=True,runtime_mode='package',runtime_bindings={'java':{'artifact':str(descriptor_jar)}})
    payload['taut/Cbor.class']+=b'corrupt'
    broken=tmp_path/'broken.jar'
    with zipfile.ZipFile(broken,'w') as z:
        for n,v in payload.items():z.writestr(n,v)
    with pytest.raises(ValueError,match='modified foundation class'):verify_artifact(broken)
    assert not (tmp_path/'no-engine').exists()


@pytest.mark.parametrize('case',['api','runtime','nested','unknown','version'])
def test_modified_unknown_files_are_atomic(tmp_path,case):
    emit(SCHEMA,tmp_path,langs=['java'],services=[],runtime_mode='source',validation=True)
    d=tmp_path/'java'
    if case=='api':(d/'api.java').write_text('hand edited',encoding='utf-8')
    if case=='runtime':(d/'Cbor.java').write_text('hand edited',encoding='utf-8')
    if case=='nested':(d/'taut/validation/descriptors/FieldDescriptor.java').write_text('hand edited',encoding='utf-8')
    if case=='unknown':
        m=d/'.taut-java-runtime.json';data=json.loads(m.read_text());data['files'].pop('Cbor.java');m.write_text(json.dumps(data))
    if case=='version':
        m=d/'.taut-java-runtime.json';data=json.loads(m.read_text());data['descriptor']=2;m.write_text(json.dumps(data))
    before={str(p):p.read_bytes() for p in d.rglob('*') if p.is_file()}
    with pytest.raises(ValueError):emit(SCHEMA,tmp_path,langs=['java'],services=[],runtime_mode='package')
    assert {str(p):p.read_bytes() for p in d.rglob('*') if p.is_file()}==before


def test_shared_users_modes_equivalent_roots_and_handwritten_survive(tmp_path):
    root=tmp_path/'owner';binding={'java':{'source_root':str(root)}}
    a,b=tmp_path/'a',tmp_path/'b'
    emit(SCHEMA,a,langs=['java'],services=[],runtime_mode='source',validation=True,runtime_bindings=binding)
    emit(SCHEMA,b,langs=['java'],services=[],runtime_mode='source',runtime_bindings=binding)
    (root/'handwritten.txt').write_text('preserve')
    # Same physical root written through an equivalent spelling remains one owner.
    equivalent={'java':{'source_root':str(root/'inside/..')}}
    emit(SCHEMA,b,langs=['java'],services=[],runtime_mode='source',runtime_bindings=equivalent)
    emit(SCHEMA,a,langs=['java'],services=[],runtime_mode='package',runtime_bindings={})
    assert (root/'Cbor.java').exists() and not (root/ENGINE).exists()
    assert (root/'handwritten.txt').read_text()=='preserve'
    emit(SCHEMA,b,langs=['java'],services=[],runtime_mode='package')
    assert not (root/'Cbor.java').exists() and (root/'handwritten.txt').exists()
    emit(SCHEMA,a,langs=['java'],services=[],runtime_mode='source',validation=False)
    assert ' validate(' not in (a/'java/api.java').read_text(encoding='utf-8')
    assert not (a/'java'/ENGINE).exists()


@pytest.mark.parametrize('field',['switch','java','taut','descriptor','validate','isValid','__name','var','record'])
def test_names_escape_and_legal_field_method_coexistence(tmp_path,field):
    s=schema(Named=Msg(**{field:F(1,STR)}))
    emit(s,tmp_path,langs=['java'],services=[],runtime=True,validation=True)
    d=tmp_path/'java';attr=field+'_' if field=='switch' else field
    (d/'Names.java').write_text('package taut; public class Names { public static void main(String[]a){ Named v=new Named();v.'+attr+'="";if(!v.isValid() || !Named.descriptor().fields().get(0).attribute().equals("'+attr+'"))throw new AssertionError();System.out.println("PASS");}}',encoding='utf-8')
    classes=tmp_path/'classes';compile_java(classes,sorted(d.rglob('*.java')))
    assert 'PASS' in execute(classes,'taut.Names').stdout


@pytest.mark.parametrize('s',[schema(Named=Msg(**{'switch':F(1,STR),'switch_':F(2,STR)})),schema(Enum('Upper',a=0,A=1)),schema(Cbor=Msg()),schema(taut=Msg())])
def test_name_preflight_atomic(tmp_path,s):
    with pytest.raises(ValueError,match='Java'):emit(s,tmp_path,langs=['java'],runtime=True)
    assert not list(tmp_path.iterdir())


def test_old_child_missing_descriptors_fails_build(tmp_path,jar):
    child=dataclasses.replace(SCHEMA,messages={'Content':SCHEMA.messages['Content']})
    parent=dataclasses.replace(child,messages={**child.messages,**schema(Parent=Msg(child=F(1,Ref('Content')))).messages})
    emit(parent,tmp_path,langs=['java'],services=[],validation=True,runtime_mode='package',java_external_types=external(['Kind','Content']))
    d=tmp_path/'java';(d/'Old.java').write_text('package taut; enum Kind { TEXT,NUMBER,EMPTY,CHILD,FLAG,ITEMS; final long wire=0;static Kind fromWire(long v){return TEXT;}} class Content {Cbor toCbor(){return Cbor.NUL;}static Content fromCbor(Cbor c){return new Content();}}',encoding='utf-8')
    r=compile_java(tmp_path/'classes',sorted(d.rglob('*.java')),dependencies=(jar,),ok=False)
    assert r.returncode and 'descriptor' in r.stderr and '$adapter' in r.stderr


def test_inconsistent_import_facts_rejected_at_publication(tmp_path,jar):
    child=dataclasses.replace(SCHEMA,messages={'Content':SCHEMA.messages['Content']})
    emit(child,tmp_path/'child',langs=['java'],services=[],runtime_mode='package')
    cc=tmp_path/'cc';compile_java(cc,[tmp_path/'child/java/api.java'],dependencies=(jar,))
    changed=dataclasses.replace(child.messages['Content'],reserved_names=('different',))
    parent=dataclasses.replace(child,messages={'Content':changed,**schema(Parent=Msg(child=F(1,Ref('Content')))).messages})
    emit(parent,tmp_path/'parent',langs=['java'],services=[],runtime_mode='package',validation=True,java_external_types=external(['Kind','Content']))
    d=tmp_path/'parent/java';(d/'Mismatch.java').write_text('package taut; public class Mismatch{public static void main(String[]a){Parent.descriptor();}}',encoding='utf-8')
    pc=tmp_path/'pc';compile_java(pc,sorted(d.rglob('*.java')),dependencies=(cc,jar))
    r=execute(pc,'taut.Mismatch',dependencies=(cc,jar),ok=False)
    assert r.returncode and 'imported message facts mismatch' in r.stderr and 'regenerate/rebind' in r.stderr

@pytest.mark.parametrize('args',[['--runtime','source','--runtime','package'],['--with-runtime','--runtime','package']])
def test_cli_conflicts_before_writes(tmp_path,args):
    from taut import cli
    with pytest.raises(ValueError,match='conflicting runtime'):
        cli.main(['gen',str(EXAMPLE/'content.taut.py'),'-o',str(tmp_path),'-l','java','--api-only',*args])
    assert not list(tmp_path.iterdir())


def test_cli_agreeing_alias_and_programmatic_forwarding(tmp_path):
    from taut import cli
    assert cli.main(['gen',str(EXAMPLE/'content.taut.py'),'-o',str(tmp_path/'cli'),'-l','java','--api-only','--with-runtime','--runtime','source','--runtime','source','--with-validation'])==0
    assert (tmp_path/'cli/java'/ENGINE).exists()
    from taut.ir.dsl import service, method
    # emit_all forwards the same keyword-only settings through the shared driver.
    from taut.facts import ServiceDef
    s=dataclasses.replace(SCHEMA,services={'Example':ServiceDef('Example',())})
    emit_all(s,'Example',tmp_path/'all',langs=['java'],runtime_mode='source',validation=True,runtime_bindings={'java':{'source_root':str(tmp_path/'owner')}})
    assert (tmp_path/'owner'/ENGINE).exists()
    assert 'validate(boolean $recursive)' in (tmp_path/'all/java/api.java').read_text(encoding='utf-8')


@pytest.mark.parametrize('kwargs',[{'runtime':1},{'validation':1},{'runtime':True,'runtime_mode':'package'},{'runtime_mode':'auto'}])
def test_bad_programmatic_modes_are_atomic(tmp_path,kwargs):
    with pytest.raises((TypeError,ValueError)):emit(SCHEMA,tmp_path,langs=['java'],**kwargs)
    assert not list(tmp_path.iterdir())


@pytest.mark.skipif(os.name!='nt',reason='Windows namespace filesystem semantics')
@pytest.mark.parametrize('component',['trailing.','trailing ','NUL','COM1','stream:name'])
def test_windows_ambiguous_roots_rejected(tmp_path,component):
    root='\\\\?\\'+str(tmp_path/component)
    with pytest.raises(ValueError,match='Windows namespace'):
        emit(SCHEMA,tmp_path/'schema',langs=['java'],runtime=True,runtime_bindings={'java':{'source_root':root}})
    assert not (tmp_path/'schema').exists()


def test_symlink_and_parent_obstructions_preflight(tmp_path):
    obstruction=tmp_path/'owner';obstruction.write_text('handwritten')
    with pytest.raises(ValueError,match='obstructed'):
        emit(SCHEMA,tmp_path/'schema',langs=['java'],runtime=True,runtime_bindings={'java':{'source_root':str(obstruction/'nested')}})
    assert obstruction.read_text()=='handwritten' and not (tmp_path/'schema').exists()


def test_external_mapping_contract_preflight(tmp_path):
    bad=external(['Content']);bad['Content']['descriptor_contract']=2
    with pytest.raises(ValueError,match='incompatible Java external'):
        emit(SCHEMA,tmp_path,langs=['java'],java_external_types=bad)
    assert not list(tmp_path.iterdir())

@pytest.mark.parametrize('virtual',[False,True])
@pytest.mark.parametrize('exhaustive',[False,True])
def test_virtual_exhaustive_and_many_members_one_payload(tmp_path,jar,virtual,exhaustive):
    from taut.ir.dsl import OneOf,Case
    e=Enum('Choice',first=0,second=1)
    s=schema(e,Value=Msg(tag=F(1,OneOf(e,virtual=virtual,exhaustive=exhaustive)),data=F(2,STR,Case(tag=e.first),Case(tag=e.second))))
    emit(s,tmp_path,langs=['java'],services=[],runtime_mode='package',validation=True)
    d=tmp_path/'java';assign='' if virtual else 'v.tag=Choice.SECOND;'
    (d/'Flags.java').write_text('package taut;public class Flags{public static void main(String[]a){Value v=new Value();'+assign+'v.data="";if(v.validate().isComplete()!='+str(not virtual).lower()+' || v.isValid()!='+str(not virtual).lower()+')throw new AssertionError();System.out.println("PASS");}}',encoding='utf-8')
    c=tmp_path/'c';compile_java(c,sorted(d.rglob('*.java')),dependencies=(jar,))
    assert 'PASS' in execute(c,'taut.Flags',dependencies=(jar,)).stdout


@pytest.mark.parametrize('member',['name','metadata','members','options','wire','values','descriptor'])
def test_java_member_projection_does_not_reserve_python_metadata(tmp_path,jar,member):
    # Native facts deliberately isolate target projection from user-owned authoring syntax.
    from taut.facts import EnumDef,EnumMemberRef
    from taut.ir.dsl import OneOf,Case
    e=EnumDef('MetadataChoice',{member:0})
    s=schema(e,Value=Msg(tag=F(1,OneOf(e)),data=F(2,STR,Case(tag=EnumMemberRef(e.name,member)))))
    emit(s,tmp_path,langs=['java'],services=[],runtime_mode='package',validation=True)
    d=tmp_path/'java'
    (d/'Members.java').write_text('package taut;public class Members{public static void main(String[]a){Value v=new Value();v.tag=MetadataChoice.'+member.upper()+';v.data="";if(!v.isValid())throw new AssertionError();System.out.println("PASS");}}',encoding='utf-8')
    c=tmp_path/'c';compile_java(c,sorted(d.rglob('*.java')),dependencies=(jar,))
    assert 'PASS' in execute(c,'taut.Members',dependencies=(jar,)).stdout


def test_wrong_typed_pair_is_a_compile_error(tmp_path,jar):
    emit(SCHEMA,tmp_path,langs=['java'],services=[],runtime_mode='package')
    d=tmp_path/'java';(d/'WrongPair.java').write_text('package taut;public class WrongPair{void f(){Content.$adapter().checkPair(new Plain(),Content.descriptor());}}',encoding='utf-8')
    r=compile_java(tmp_path/'c',sorted(d.rglob('*.java')),dependencies=(jar,),ok=False)
    assert r.returncode and 'incompatible types' in r.stderr

def test_partial_external_graph_is_rejected_before_writes(tmp_path):
    with pytest.raises(ValueError,match='full dependency graph'):
        emit(SCHEMA,tmp_path,langs=['java'],java_external_types=external(['Content']))
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize('validation',[False,True])
def test_attributed_generation_goldens(validation):
    from taut.gen.java import emit_types
    expected=EXAMPLE/('enabled.golden.java' if validation else 'disabled.golden.java')
    assert emit_types(SCHEMA,validation=validation)==expected.read_text(encoding='utf-8')

def test_actual_old_supplied_codec_export_is_rejected_by_compiler(tmp_path):
    sources=canonical_sources(validation=False)
    old=sources['Cbor.java'].decode('utf-8')
    start=old.index('    /** Codec-owned compatibility export:')
    end=old.index('    public static final int INT',start)
    sources['Cbor.java']=(old[:start]+old[end:]).encode('utf-8')
    for name,data in sources.items():
        p=tmp_path/'src'/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
    r=compile_java(tmp_path/'classes',sorted((tmp_path/'src').rglob('*.java')),ok=False)
    assert r.returncode and 'requireContract' in r.stderr and 'Cbor' in r.stderr

@pytest.mark.parametrize('replacement',['child','runtime','codec'])
def test_compiled_parent_rejects_substituted_actual_artifacts(tmp_path,jar,replacement):
    child=dataclasses.replace(SCHEMA,messages={'Content':SCHEMA.messages['Content']})
    parent=dataclasses.replace(child,messages={**child.messages,**schema(Parent=Msg(child=F(1,Ref('Content')))).messages})
    emit(child,tmp_path/'child',langs=['java'],services=[],runtime_mode='package')
    cc=tmp_path/'cc';compile_java(cc,[tmp_path/'child/java/api.java'],dependencies=(jar,))
    emit(parent,tmp_path/'parent',langs=['java'],services=[],runtime_mode='package',validation=True,java_external_types=external(['Kind','Content']))
    pd=tmp_path/'parent/java'
    (pd/'LateLink.java').write_text('package taut;public class LateLink{public static void main(String[]a){Parent p=new Parent();p.child=new Content();p.child.kind=Kind.EMPTY;if(!p.isValid())throw new AssertionError();System.out.println("PASS");}}',encoding='utf-8')
    pc=tmp_path/'pc';compile_java(pc,sorted(pd.rglob('*.java')),dependencies=(cc,jar))
    assert 'PASS' in execute(pc,'taut.LateLink',dependencies=(cc,jar)).stdout
    actual_child,actual_runtime=cc,jar
    if replacement=='child':
        changed=dataclasses.replace(child,messages={'Content':dataclasses.replace(child.messages['Content'],reserved_names=('replacement',))})
        emit(changed,tmp_path/'replacement',langs=['java'],services=[],runtime_mode='package')
        actual_child=tmp_path/'replacement-classes'
        compile_java(actual_child,[tmp_path/'replacement/java/api.java'],dependencies=(jar,))
    else:
        sources=canonical_sources()
        target='taut/validation/descriptors/RuntimeContract.java' if replacement=='runtime' else 'Cbor.java'
        text=sources[target].decode('utf-8')
        if replacement=='runtime':text=text.replace('OWNER="taut.java.foundation"','OWNER="taut.java.incompatible"')
        else:text=text.replace('codec != 1','codec != 2')
        sources[target]=text.encode('utf-8')
        for name,data in sources.items():
            p=tmp_path/'replacement-src'/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
        actual_runtime=tmp_path/'replacement-runtime'
        compile_java(actual_runtime,sorted((tmp_path/'replacement-src').rglob('*.java')))
    r=execute(pc,'taut.LateLink',dependencies=(actual_child,actual_runtime),ok=False)
    assert r.returncode and 'regenerate/rebind' in r.stderr
    if replacement=='child': assert 'imported message facts mismatch' in r.stderr
    if replacement=='runtime': assert 'required owner=taut.java.incompatible' in r.stderr
    if replacement=='codec': assert 'incompatible Java codec' in r.stderr


def test_java8_replacement_preserves_prior_codec_collection_behavior(tmp_path,jar):
    emit(SCHEMA,tmp_path,langs=['java'],services=[],runtime_mode='package')
    d=tmp_path/'java'
    (d/'CollectionsProbe.java').write_text('''package taut;
import java.util.*;
public class CollectionsProbe {
 public static void main(String[] a) {
  Content c=new Content();c.kind=Kind.ITEMS;c.items=new ArrayList<Long>();c.items.add(1L);
  Cbor tree=c.toCbor();
  try{tree.get(6).asArray().clear();throw new AssertionError("encoded list changed mutability");}catch(UnsupportedOperationException expected){}
  Content decoded=Content.fromCbor(tree);
  try{decoded.items.clear();throw new AssertionError("decoded list changed mutability");}catch(UnsupportedOperationException expected){}
  c.items.add(2L);if(c.items.size()!=2)throw new AssertionError("input was frozen");
  System.out.println("PASS");
 }
}''',encoding='utf-8')
    c=tmp_path/'c';compile_java(c,sorted(d.rglob('*.java')),dependencies=(jar,))
    assert 'PASS' in execute(c,'taut.CollectionsProbe',dependencies=(jar,)).stdout

@pytest.mark.parametrize('name',['record','var','yield','sealed','permits','switch'])
def test_java_type_contextual_keywords_escape(tmp_path,jar,name):
    s=schema(Msg(name,F('n',1,INT)))
    emit(s,tmp_path,langs=['java'],services=[],runtime_mode='package',validation=True)
    d=tmp_path/'java';access=name+'_'
    (d/'TypeName.java').write_text('package taut;public class TypeName{public static void main(String[]a){'+access+' v=new '+access+'();if(!v.isValid() || !'+access+'.descriptor().name().equals("'+name+'"))throw new AssertionError();System.out.println("PASS");}}',encoding='utf-8')
    c=tmp_path/'c';compile_java(c,sorted(d.rglob('*.java')),dependencies=(jar,))
    assert 'PASS' in execute(c,'taut.TypeName',dependencies=(jar,)).stdout


def test_underscore_enum_escape_and_collision(tmp_path,jar):
    from taut.facts import EnumDef
    s=schema(EnumDef('Under',{'_':0}),Value=Msg(tag=F(1,Ref('Under'))))
    emit(s,tmp_path/'ok',langs=['java'],services=[],runtime_mode='package')
    d=tmp_path/'ok/java';(d/'UnderProbe.java').write_text('package taut;public class UnderProbe{public static void main(String[]a){Value v=new Value();v.tag=Under.__;System.out.println(Cbor.encode(v.toCbor()).length>0);}}',encoding='utf-8')
    c=tmp_path/'c';compile_java(c,sorted(d.rglob('*.java')),dependencies=(jar,))
    assert execute(c,'taut.UnderProbe',dependencies=(jar,)).stdout.strip()=='true'
    with pytest.raises(ValueError,match='collide'):
        emit(schema(EnumDef('Under',{'_':0,'__':1})),tmp_path/'bad',langs=['java'])
    assert not (tmp_path/'bad').exists()

@pytest.mark.parametrize('bad',['virtual-flag','exhaustive-flag','wrong-enum','unknown-control','duplicate-member','two-controls','exhaustive-coverage'])
def test_java_native_invalid_rules_fail_complete_preflight(tmp_path,bad):
    from taut.facts import OneOfRule,CaseRule
    m=SCHEMA.messages['Content'];fields=list(m.fields)
    if bad=='virtual-flag':fields[0]=dataclasses.replace(fields[0],oneof=OneOfRule('Kind',virtual=1))
    elif bad=='exhaustive-flag':fields[0]=dataclasses.replace(fields[0],oneof=OneOfRule('Kind',exhaustive=1))
    elif bad=='wrong-enum':fields[1]=dataclasses.replace(fields[1],cases=(CaseRule('kind','Other','text'),))
    elif bad=='unknown-control':fields[1]=dataclasses.replace(fields[1],cases=(CaseRule('missing','Kind','text'),))
    elif bad=='duplicate-member':fields[2]=dataclasses.replace(fields[2],cases=(CaseRule('kind','Kind','text'),))
    elif bad=='two-controls':fields[1]=dataclasses.replace(fields[1],cases=(*fields[1].cases,CaseRule('missing','Kind','number')))
    else:fields[0]=dataclasses.replace(fields[0],oneof=OneOfRule('Kind',exhaustive=True))
    s=dataclasses.replace(SCHEMA,messages={**SCHEMA.messages,'Content':dataclasses.replace(m,fields=tuple(fields))})
    with pytest.raises(ValueError):emit(s,tmp_path,langs=['java'],runtime=True,validation=True)
    assert not list(tmp_path.iterdir())


def test_compatible_unequal_runtime_build_labels_link(tmp_path,jar):
    emit(SCHEMA,tmp_path/'app',langs=['java'],services=[],runtime_mode='package',validation=True)
    d=tmp_path/'app/java';(d/'Patch.java').write_text('package taut;public class Patch{public static void main(String[]a){Content c=new Content();c.kind=Kind.EMPTY;if(!c.isValid())throw new AssertionError();System.out.println("PASS");}}',encoding='utf-8')
    app=tmp_path/'app-classes';compile_java(app,sorted(d.rglob('*.java')),dependencies=(jar,))
    for name,data in canonical_sources().items():
        if name.endswith('RuntimeContract.java'):data=data.replace(b'java-oneof-reference.1',b'java-oneof-reference.patch2')
        p=tmp_path/'runtime-src'/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
    runtime=tmp_path/'runtime';compile_java(runtime,sorted((tmp_path/'runtime-src').rglob('*.java')))
    assert 'PASS' in execute(app,'taut.Patch',dependencies=(runtime,)).stdout
