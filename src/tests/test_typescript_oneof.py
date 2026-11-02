"""Real tsc/transpile/runtime tests of canonical TypeScript descriptors/validation."""
from pathlib import Path
import dataclasses
import hashlib
import json
import os
import shutil
import subprocess
import tarfile
import sys
import types
import pytest
from taut.gen.typescript_metadata import emit_types
from taut.gen import typescript_runtime as rt
from taut.gen.typescript_package import build_foundation, verify_artifact
from taut.gen.python_runtime import apply_outputs, output_locks
from taut.ir.dsl import STR, INT, BOOL, BYTES, FLOAT, Enum, F, Msg, OneOf, Case, List, Map, Ref, schema
from taut.ir.load import load_schema

ROOT=Path(__file__).resolve().parents[2]
EXAMPLE=ROOT/'dev-docs/examples/python-oneof/content.taut.py'

def run(args, *, success=True, cwd=None):
    result=subprocess.run(list(map(str,args)),capture_output=True,text=True,encoding='utf-8',cwd=cwd)
    assert (result.returncode==0)==success, result.stdout+result.stderr
    return result

def emit_direct(s,directory,*,validation=False,mode='source',source_root=None,external_types=None,runtime_module=None,validation_module=None):
    directory=Path(directory); source_root=Path(source_root or directory)
    config={'typescript':{'source_root':str(source_root)}} if source_root!=directory else {}
    if runtime_module: config.setdefault('typescript',{})['module']=runtime_module
    if validation_module: config.setdefault('typescript',{})['validation_module']=validation_module
    module,engine,source_root,consume=rt.binding(config,directory,mode,validation=validation)
    texts={'api.ts':emit_types(s,validation=validation,external_types=external_types,runtime_module=module,validation_module=engine)}
    with output_locks([directory,source_root]):
        writes,deletes=rt.plan_outputs(directory,texts,mode=mode,validation=validation,source_root=source_root,consume_source=consume,external=bool(external_types))
        apply_outputs(writes,deletes)
    return directory/'api.ts'

def compile_program(directory,source,*,success=True,execute=True,name='main',module='commonjs',declaration=False):
    directory=Path(directory); main=directory/(name+'.ts');main.write_text(source,encoding='utf-8')
    args=[shutil.which('tsc'),'--target','ES2022','--module',module,'--strict','--skipLibCheck','--rewriteRelativeImportExtensions','--outDir',directory/'built','--rootDir',directory,main]
    if declaration:args.append('--declaration')
    built=run(args,success=success)
    if not success:return built
    if execute:return run(['node',directory/'built'/(name+'.js')]).stdout
    return directory/'built'/(name+'.js')

@pytest.fixture(scope='module')
def foundation(tmp_path_factory):
    directory=tmp_path_factory.mktemp('typescript-package')
    artifact=build_foundation(directory)
    return directory/'package',artifact

BEHAVIOR=r'''
import * as api from "./generated/api.ts";
import * as f from "FOUNDATION";
const check=(v:unknown)=>{if(!v) throw new Error("assertion failed");};
const equal=(a:unknown,b:unknown)=>check(JSON.stringify(a)===JSON.stringify(b));
function parity(value:api.Content,expected:boolean) {
  for(const recursive of [false,true]) {const r=value.validate({recursive});check(value.isValid({recursive})===(r.isValid()&&r.isComplete())); check(value.isValid({recursive})===expected);}
}
for(const value of [new api.Content({kind:"number",number:0n}),new api.Content({kind:"flag",flag:false}),new api.Content({kind:"text",text:""}),new api.Content({kind:"items",items:[]}),new api.Content({kind:"empty"})]) parity(value,true);
let draft=new api.Content({kind:"number",text:"extra"});
const snapshot=draft.validate(); equal(snapshot.issues.map(i=>i.code),["oneof.payload_unexpected","oneof.payload_missing"]);
check(snapshot.issues[0].rule==="taut.oneof.v1");check(snapshot.issues[0].path[0].fieldName==="text");
const wire=f.codec.encode(api.CODEC_SCHEMA,"Content",draft); const decoded=f.codec.decode(api.CODEC_SCHEMA,"Content",wire);
check(decoded.text==="extra"&&decoded.number===null); check((f.decode(wire) as Map<number,unknown>).size===5);
const json=f.jsoncodec.toJsonValue(api.CODEC_SCHEMA,"Content",draft);equal({...json},{kind:"number",text:"extra"});
check(f.jsoncodec.fromJsonValue(api.CODEC_SCHEMA,"Content",{kind:"number"}).number===null);
draft=new api.Content(decoded);parity(draft,false);draft.text=null;draft.number=0n;parity(draft,true);check(snapshot.issues.length===2);
const bad=new api.Content({kind:"text"}), wrapper=new api.Envelope({content:bad});
check(!wrapper.isValid()&&wrapper.isValid({recursive:false}));check(wrapper.validate({recursive:false}).scope==="local");
equal(wrapper.validate().issues[0].path.map(p=>p.fieldName),["content","text"]);
const virtual=new api.VirtualEnvelope({content:bad}); let report=virtual.validate();
check(report.issues.length===1&&report.deferredChecks.length===1&&!virtual.isValid());
bad.text="";report=virtual.validate();check(report.isValid()&&!report.isComplete()&&!virtual.isValid());
check(report.deferredChecks[0].reasonCode==="oneof.virtual_deferred");check(report.deferredChecks[0].path[0].fieldName==="kind");bad.text=null;
const tree=new api.Tree({content:null,children:[new api.Tree({content:bad,children:[]})]});check(tree.validate().issues[0].path[1].index===0);
const collection=new api.Collection({entries:[bad,bad],by_key:new Map([["aa",bad],["b",bad]])});
const paths=collection.validate().issues.map(i=>i.path); check(paths.length===4&&paths[0][1].index===0&&paths[1][1].index===1);
check(paths[2][1].keyType==="str"&&paths[2][1].keyCborBase64==="YWI=");check(paths[3][1].keyCborBase64==="YmFh");
const cycle=new api.Tree({content:null,children:[]});cycle.children=[cycle];check(cycle.validate().issues[0].code==="validation.ownership_cycle");check(!cycle.isValid()&&cycle.isValid({recursive:false}));
const descriptor=api.ContentDescriptor;check(descriptor===api.Content.descriptor());equal(descriptor.fields.map(x=>x.number),[1,2,3,4,5]);check(descriptor.nextId===6);
check(api.VirtualEnvelopeDescriptor.fields[0].virtual&&api.VirtualEnvelopeDescriptor.fields[0].attribute===null);
check(Object.isFrozen(descriptor)&&Object.isFrozen(descriptor.fields)&&Object.isFrozen(descriptor.options)&&Object.isFrozen(descriptor.oneofs[0].members));
check(Object.isFrozen(snapshot)&&Object.isFrozen(snapshot.issues)&&Object.isFrozen(snapshot.issues[0].path));
const path=[f.PathSegment.forIndex(2)];const issue=new f.ValidationIssue("future.code","future.rule",path,"future");path.length=0;check(issue.path[0].index===2);
const open=new f.ValidationReport([issue],[],"local");check(!open.isValid()&&open.isComplete());
check(f.PathSegment.forIndex(2147483648).index===2147483648);const bytes=new Uint8Array([0x61,0x62]);const key=f.PathSegment.forKey("str",bytes);bytes[1]=0x63;check(key.keyCborBase64==="YWI=");
for(const thunk of [()=>f.PathSegment.forIndex(-1),()=>f.PathSegment.forIndex(2**53),()=>f.PathSegment.forKey("int",new Uint8Array([0x18,0x00])),()=>draft.validate({recursive:1} as any),()=>draft.validate(null as any)]) {let threw=false;try{thunk();}catch{threw=true;}check(threw);}
const fields:api.ContentFields={kind:"text",text:"native"}; const migrated=new api.Content(fields);fields.text="changed";check(migrated.text==="native");check(!("validate" in fields));
const nestedFields={content:bad};const nested=new api.Envelope(nestedFields);check(nested.content===bad);
(bad as any).kind="invalid";equal(bad.validate().issues.map(i=>i.code),["oneof.invalid_discriminator"]);
(wrapper as any).content=7;check(wrapper.validate().issues[0].code==="validation.type_mismatch");
console.log("presence/drafts/snapshots/recursive/virtual/cycles/maps/metadata/migration PASS");
'''

@pytest.mark.parametrize('mode',['source','package',None])
def test_native_behavior_source_package_supplied(tmp_path,foundation,mode):
    package,_=foundation
    module=(package/'cjs/foundation.js').as_posix();engine=(package/'cjs/validation.js').as_posix()
    emit_direct(load_schema(EXAMPLE),tmp_path/'generated',validation=True,mode=mode,
                runtime_module=module if mode!='source' else None,validation_module=engine if mode!='source' else None)
    source=BEHAVIOR.replace('FOUNDATION','./generated/foundation.ts' if mode=='source' else module)
    assert 'migration PASS' in compile_program(tmp_path,source)

@pytest.mark.parametrize('validation',[False,True])
def test_interface_class_typecheck_migration(tmp_path,validation):
    s=schema(Item=Msg(value=F(1,STR)))
    emit_direct(s,tmp_path/'generated',validation=validation)
    if validation:
        source='import {Item} from "./generated/api.ts"; const value:Item={value:"plain"};'
        assert 'missing' in compile_program(tmp_path,source,success=False).stdout
    else:
        source='import {Item,ItemDescriptor} from "./generated/api.ts"; const value:Item={value:"plain"}; if(ItemDescriptor.fields[0].name!=="value")throw Error(); console.log(value.value);'
        assert 'plain' in compile_program(tmp_path,source)
        assert not (tmp_path/'generated/validation.ts').exists()

def test_package_provenance_and_dual_module_identity(foundation,tmp_path):
    package,artifact=foundation;p=verify_artifact(artifact,validation=True)
    for name,content in rt.canonical_sources().items(): assert p['sources'][name]==hashlib.sha256(content).hexdigest()
    script=tmp_path/'identity.mjs';script.write_text('import {createRequire} from "node:module";const require=createRequire(import.meta.url);'+
        f'const c=require({json.dumps(str(package/"cjs/foundation.js"))}); const e=await import({json.dumps((package/"esm/foundation.js").as_uri())});'+
        'for(const k of ["Foundation","MessageDescriptor","ValidationReport","DecodeError","CborFloat"])if(c[k]!==e[k])throw Error(k);console.log("identity PASS");')
    assert 'identity PASS' in run(['node',script]).stdout

@pytest.mark.parametrize('field',['switch','__private','metadata','name','__proto__','prototype','then','descriptor'])
def test_names_and_escaped_properties(tmp_path,field):
    s=schema(Named=Msg(**{field:F(1,STR)}));emit_direct(s,tmp_path/'generated',validation=True)
    assert 'PASS' in compile_program(tmp_path,'import {Named,NamedDescriptor} from "./generated/api.ts";'+
         f'const v=new Named({{[{json.dumps(field)}]:""}}); if(!v.isValid() || v[{json.dumps(field)}]!=="" || NamedDescriptor.fields[0].name!=={json.dumps(field)})throw Error(); console.log("PASS");')

@pytest.mark.parametrize('name',['validate','isValid','constructor'])
def test_actual_method_collisions(tmp_path,name):
    s=schema(Named=Msg(**{name:F(1,STR)}));emit_direct(s,tmp_path/'off',validation=False)
    with pytest.raises(ValueError,match='collision'):emit_direct(s,tmp_path/'on',validation=True)
    assert not (tmp_path/'on').exists()

@pytest.mark.parametrize('case',['api','runtime','unknown','version'])
def test_modified_unknown_outputs_fail_atomically(tmp_path,case):
    d=tmp_path/'generated';emit_direct(load_schema(EXAMPLE),d,validation=True)
    if case=='api':(d/'api.ts').write_text('hand edit')
    if case=='runtime':(d/'descriptors.ts').write_text('hand edit')
    if case in ('unknown','version'):
        path=d/'.taut-typescript-runtime.json';data=json.loads(path.read_text())
        if case=='unknown':data['files'].pop('cbor.ts')
        else:data['descriptor']=2
        path.write_text(json.dumps(data))
    before={str(p):p.read_bytes() for p in d.rglob('*') if p.is_file()}
    with pytest.raises(ValueError):emit_direct(load_schema(EXAMPLE),d,mode='package')
    assert before=={str(p):p.read_bytes() for p in d.rglob('*') if p.is_file()}

def test_shared_source_users_and_modes(tmp_path):
    s=load_schema(EXAMPLE);a,b,root=(tmp_path/x for x in ['a','b','owner'])
    emit_direct(s,a,source_root=root,validation=True);emit_direct(s,b,source_root=root)
    emit_direct(s,b,source_root=root/'inside/..')
    emit_direct(s,b,mode='package');assert (root/'validation.ts').exists()
    emit_direct(s,a,validation=False,source_root=root);assert not (root/'validation.ts').exists()
    emit_direct(s,a,mode='package');assert not (root/'cbor.ts').exists()

def test_separate_disabled_child_build_and_facts_checks(tmp_path):
    child=schema(Child=Msg(value=F(1,STR),count=F(2,INT)))
    emit_direct(child,tmp_path/'child',validation=False,source_root=tmp_path/'owner')
    # A first separate build creates the child's public declaration artifact.
    compile_program(tmp_path,'export * from "./child/api.ts";',execute=False,name='child-build')
    parent=schema(Child=child.messages['Child'],Parent=Msg(child=F(1,Ref.Child)))
    emit_direct(parent,tmp_path/'parent',validation=True,source_root=tmp_path/'owner',external_types={'Child':'../child/api.ts'})
    source='import {Parent} from "./parent/api.ts";import {ChildDescriptor} from "./child/api.ts";const value={value:"",count:0n};const p=new Parent({child:value});if(!p.isValid() || "validate" in value || Parent.descriptor().fields[0].type.kind!=="message")throw Error();console.log("PASS");'
    assert 'PASS' in compile_program(tmp_path,source)

def test_reports_match_python_normalized(tmp_path):
    from taut.gen.python import emit_types as py_emit
    s=load_schema(EXAMPLE)
    s=dataclasses.replace(s,messages=dict(s.messages,Keyed=schema(Keyed=Msg(by_int=F(1,Map(INT,Ref.Content)),by_bool=F(2,Map(BOOL,Ref.Content)))).messages['Keyed']))
    native=types.ModuleType('_typescript_normalized_python');sys.modules[native.__name__]=native
    exec(py_emit(s,validation=True),native.__dict__)
    bad=native.Content(native.ContentKind.text)
    values=[native.Content(native.ContentKind.number,text='extra'),native.Content(native.ContentKind.empty),
            native.Envelope(bad),native.VirtualEnvelope(content=bad),
            native.Collection([bad,bad],{'aa':bad,'b':bad}),
            native.Keyed({-(1<<63):bad,(1<<63)-1:bad,0:bad},{True:bad,False:bad})]
    cycle=native.Tree(None,[]);cycle.children=[cycle];values.append(cycle)
    expected=[]
    for v in values:
        for recursive in (False,True):
            r=v.validate(recursive=recursive)
            data=dataclasses.asdict(r)
            for i in data['issues']:i.pop('message')
            for d in data['deferred_checks']:d.pop('message')
            data.update(valid=r.is_valid(),complete=r.is_complete(),fast=v.is_valid(recursive=recursive));expected.append(data)
    emit_direct(s,tmp_path/'generated',validation=True)
    source=r'''
import * as a from "./generated/api.ts";
const bad=new a.Content({kind:"text"});const cycle=new a.Tree({content:null,children:[]});cycle.children=[cycle];
const values=[new a.Content({kind:"number",text:"extra"}),new a.Content({kind:"empty"}),new a.Envelope({content:bad}),new a.VirtualEnvelope({content:bad}),new a.Collection({entries:[bad,bad],by_key:new Map([["aa",bad],["b",bad]])}),new a.Keyed({by_int:new Map([[-9223372036854775808n,bad],[9223372036854775807n,bad],[0n,bad]]),by_bool:new Map([[true,bad],[false,bad]])}),cycle];
const path=(p:any)=>p.map((s:any)=>({kind:s.kind,field_name:s.fieldName,index:s.index,key_type:s.keyType,key_cbor_base64:s.keyCborBase64}));
const results=values.flatMap(v=>[false,true].map(recursive=>{const r=v.validate({recursive});return {issues:r.issues.map(i=>({code:i.code,rule:i.rule,path:path(i.path)})),deferred_checks:r.deferredChecks.map(d=>({rule:d.rule,path:path(d.path),reason_code:d.reasonCode})),scope:r.scope,valid:r.isValid(),complete:r.isComplete(),fast:v.isValid({recursive})};}));console.log(JSON.stringify(results));
'''
    actual=json.loads(compile_program(tmp_path,source))
    assert actual==json.loads(json.dumps(expected))

@pytest.mark.parametrize('name',['Map','Array','Uint8Array','Error'])
def test_native_global_type_names_escape(tmp_path,name):
    s=schema(**{name:Msg(value=F(1,STR))});emit_direct(s,tmp_path/'generated',validation=True)
    assert 'PASS' in compile_program(tmp_path,f'import {{ {name} as Native }} from "./generated/api.ts"; const v=new Native({{value:""}});if(!v.isValid())throw Error(); console.log("PASS");')

@pytest.mark.parametrize('virtual',[False,True])
@pytest.mark.parametrize('exhaustive',[False,True])
def test_all_rule_flags_and_complete_metadata(tmp_path,virtual,exhaustive):
    kind=Enum('Kind',yes=0,no=1)
    s=schema(kind,Item=Msg(kind=F(1,OneOf(kind,virtual=virtual,exhaustive=exhaustive)),
        yes=F(2,STR,Case(kind=kind.yes)),no=F(3,BOOL,Case(kind=kind.no)),
        bytes=F(4,BYTES),float=F(5,FLOAT),nums=F(6,List(INT)),mapping=F(7,Map(STR,INT)),next_id=9,reserved=(8,'old')))
    emit_direct(s,tmp_path/'generated',validation=True)
    kind_source='kind:"yes",' if not virtual else ''
    source='import {Item,ItemDescriptor as d} from "./generated/api.ts";'+f'const v=new Item({{{kind_source}yes:"",bytes:new Uint8Array(),float:1.5,nums:[],mapping:new Map()}});'+\
        f'if(d.fields.length!==7 || d.oneofs[0].virtual!=={str(virtual).lower()} || d.oneofs[0].exhaustive!=={str(exhaustive).lower()} || d.reservedNumbers[0]!==8 || d.reservedNames[0]!=="old" || d.nextId!==9 || v.validate().isComplete()==={str(virtual).lower()})throw Error(); console.log("PASS");'
    assert 'PASS' in compile_program(tmp_path,source)

@pytest.mark.parametrize('field',['name','metadata','options','members','case','__dunder'])
def test_enum_metadata_like_members_from_native_ir(tmp_path,field):
    from taut.ir.export import schema_json
    from taut.ir.load import schema_from_json
    kind=Enum('Kind',yes=0)
    facts=schema_json(schema(kind,Item=Msg(kind=F(1,OneOf(kind)),payload=F(2,STR,Case(kind=kind.yes)))))
    facts['enums'][0]['members']={field:0};facts['enums'][0]['member_options']={field:{}}
    facts['messages'][0]['fields'][1]['cases'][0]['member']=field
    emit_direct(schema_from_json(facts),tmp_path/'generated',validation=True)
    assert 'PASS' in compile_program(tmp_path,'import {Item,KindDescriptor} from "./generated/api.ts";'+f'const v=new Item({{kind:{json.dumps(field)},payload:""}});if(!v.isValid() || !Object.hasOwn(KindDescriptor.members,{json.dumps(field)}))throw Error();console.log("PASS");')

@pytest.mark.parametrize('replacement',['changed-field','changed-effective','old','split-owner'])
def test_actual_separate_child_artifact_substitution(tmp_path,foundation,replacement):
    package,_=foundation;module=(package/'cjs/foundation.js').as_posix();engine=(package/'cjs/validation.js').as_posix()
    child=schema(Child=Msg(text=F(1,STR),count=F(2,INT)))
    emit_direct(child,tmp_path/'child-source',mode='package',runtime_module=module,validation_module=engine)
    artifact=compile_program(tmp_path,'export * from "./child-source/api.ts";',name='child',execute=False,declaration=True)
    child_module=artifact.parent/'child-source/api.js'
    # Parent compiles against a separately built declaration/JS artifact, with child source poisoned.
    (tmp_path/'child-source/api.ts').write_text('not valid TypeScript')
    reordered=dataclasses.replace(child.messages['Child'],fields=tuple(reversed(child.messages['Child'].fields)))
    parent=schema(Child=reordered,Parent=Msg(child=F(1,Ref.Child)))
    emit_direct(parent,tmp_path/'parent',validation=True,mode='package',runtime_module=module,validation_module=engine,external_types={'Child':child_module.as_posix()})
    program=compile_program(tmp_path,'import {Parent} from "./parent/api.ts";const v=new Parent({child:{text:"",count:0n}});if(!v.isValid())throw Error();console.log("PASS");',name='parent',execute=False)
    assert 'PASS' in run(['node',program]).stdout
    if replacement=='old':child_module.write_text('exports.ChildDescriptor={};exports.ChildBinding={};')
    else:
        changed=child
        if replacement=='changed-field':changed=schema(Child=Msg(text=F(1,STR),count=F(2,BOOL)))
        if replacement=='changed-effective':changed=dataclasses.replace(child,options={'max_depth':16})
        if replacement=='split-owner':
            copy=tmp_path/'split-package';shutil.copytree(package,copy);module=(copy/'cjs/foundation.js').as_posix();engine=(copy/'cjs/validation.js').as_posix()
        alt=tmp_path/'alternative';alt.mkdir()
        emit_direct(changed,alt/'child-source',mode='package',runtime_module=module,validation_module=engine)
        altartifact=compile_program(alt,'export * from "./child-source/api.ts";',execute=False,declaration=True,name='child')
        shutil.copyfile(altartifact.parent/'child-source/api.js',child_module)
    result=run(['node',program],success=False)
    assert 'external' in result.stderr and ('incompatible' in result.stderr or 'split' in result.stderr)

@pytest.mark.parametrize('replacement',['cbor','codec','schema','jsoncodec','descriptor','engine','compatible-build'])
def test_loaded_artifact_contracts_not_binding_claims(tmp_path,foundation,replacement):
    original,_=foundation;package=tmp_path/'package';shutil.copytree(original,package)
    module=(package/'cjs/foundation.js').as_posix();engine=(package/'cjs/validation.js').as_posix()
    emit_direct(schema(Item=Msg(value=F(1,STR))),tmp_path/'generated',mode='package',validation=True,runtime_module=module,validation_module=engine)
    program=compile_program(tmp_path,'import {Item} from "./generated/api.ts";if(!new Item({value:""}).isValid())throw Error();console.log("PASS");',execute=False)
    filename={'descriptor':'descriptors','engine':'validation','compatible-build':'descriptors'}.get(replacement,replacement)
    path=package/'cjs'/(filename+'.js');source=path.read_text()
    if replacement=='compatible-build':source=source.replace('typescript-oneof-reference.1','typescript-oneof-compatible.99')
    elif replacement=='descriptor':source=source.replace('descriptorContract: 1','descriptorContract: 2')
    elif replacement=='engine':source=source.replace('contract: 1','contract: 2')
    else:source=source.replace('contract: 1','contract: 2')
    path.write_text(source)
    result=run(['node',program],success=replacement=='compatible-build')
    if replacement!='compatible-build': assert 'incompatible' in result.stderr or 'compatible TypeScript foundation' in result.stderr

@pytest.fixture(scope='module')
def shape_package(tmp_path_factory):
    shape=ROOT.parent/'taut-shape-ts'
    run([shutil.which('pnpm'),'build'],cwd=shape)
    d=tmp_path_factory.mktemp('actual-typescript-shape-package')
    result=run([shutil.which('npm'),'pack','--ignore-scripts','--json','--pack-destination',d],cwd=shape)
    artifact=d/json.loads(result.stdout)[0]['filename']
    with tarfile.open(artifact,'r:gz') as archive:
        assert all((d/m.name).resolve().is_relative_to(d.resolve()) for m in archive.getmembers())
        archive.extractall(d,filter='data')
    return d/'package',artifact

@pytest.mark.parametrize('composition',['package-package','source-package','source-source'])
def test_actual_library_artifact_one_owner_composition(tmp_path,shape_package,composition):
    original,artifact=shape_package;package=tmp_path/'library';shutil.copytree(original,package)
    s=schema(Item=Msg(value=F(1,STR)))
    if composition=='package-package':
        module=(package/'foundation/cjs/foundation.js').as_posix();engine=(package/'foundation/cjs/validation.js').as_posix()
        emit_direct(s,tmp_path/'a',validation=True,mode='package',runtime_module=module,validation_module=engine)
        emit_direct(s,tmp_path/'b',validation=True,mode=None,runtime_module=module,validation_module=engine)
    else:
        emit_direct(s,tmp_path/'a',validation=True,source_root=tmp_path/'owner')
        # Compile the shared source owner once, then explicitly build library facades to it.
        compile_program(tmp_path,'export * from "./owner/foundation.ts";export * from "./owner/validation.ts";',execute=False,declaration=True,name='owner-build')
        compiled_owner=tmp_path/'built/owner'
        run(['node',ROOT.parent/'taut-shape-ts/scripts/build-foundation.mjs','--output',package/'foundation','--owner',compiled_owner])
        if composition=='source-package':
            module=(package/'foundation/cjs/foundation.js').as_posix();engine=(package/'foundation/cjs/validation.js').as_posix()
            emit_direct(s,tmp_path/'b',validation=True,mode='package',runtime_module=module,validation_module=engine)
        else:emit_direct(s,tmp_path/'b',validation=True,source_root=tmp_path/'owner')
    built=compile_program(tmp_path,'export * as a from "./a/api.ts";export * as b from "./b/api.ts";',execute=False,name='application')
    script=tmp_path/'composition.mjs'
    script.write_text('import {createRequire} from "node:module";const require=createRequire(import.meta.url);'+
        f'const {{a,b}}=require({json.dumps(str(built))});const f=require({json.dumps(str(package/"foundation/cjs/foundation.js"))});'+
        f'const ef=await import({json.dumps((package/"foundation/esm/foundation.js").as_uri())});const shape=await import({json.dumps((package/"dist/index.js").as_uri())});'+
        f'const generated=await import({json.dumps((package/"dist/taut/gen/shape_log.js").as_uri())});const cbor=await import({json.dumps((package/"dist/taut/cbor.js").as_uri())});'+
        'const check=v=>{if(!v)throw Error("identity/composition failed")};'+
        'check(a.ItemDescriptor instanceof f.MessageDescriptor&&b.ItemDescriptor instanceof f.MessageDescriptor);check(generated.LogCursorDescriptor instanceof f.MessageDescriptor);'+
        'for(const key of ["MessageDescriptor","ValidationIssue","ValidationReport","DecodeError","CborFloat","Foundation"])check(f[key]===ef[key]);check(cbor.DecodeError===f.DecodeError&&cbor.CborFloat===f.CborFloat);'+
        'const v=new a.Item({value:""});check(v.isValid()&&v.validate() instanceof f.ValidationReport);const w=new b.Item({value:""});check(w.validate() instanceof f.ValidationReport);'+
        'const node=new shape.LogNode();check(node.handle({type:"push",payload:new Uint8Array([1])}).length===0);check(node.handle({type:"read",streamId:"s",timeoutMs:0})[0].type==="read_response");console.log("actual library composition PASS");')
    assert 'composition PASS' in run(['node',script]).stdout
    # Both nominal generated output and actual library are package artifact bytes.
    provenance=json.loads((package/'foundation/provenance.json').read_text())
    for name,digest in provenance['sources'].items():
        assert hashlib.sha256((package/'foundation-src'/name).read_bytes()).hexdigest()==digest
        assert hashlib.sha256(rt.canonical_sources()[name]).hexdigest()==digest

def test_source_closure_descriptor_queries_without_engine_or_compiler(tmp_path):
    emit_direct(load_schema(EXAMPLE),tmp_path/'generated',validation=False)
    assert not (tmp_path/'generated/validation.ts').exists()
    source='import * as a from "./generated/api.ts";import * as f from "./generated/foundation.ts";const value:a.Content={kind:"text",text:"",number:null,flag:null,items:null};if("validate" in value || !(a.ContentDescriptor instanceof f.MessageDescriptor))throw Error(); const bytes=f.codec.encode(a.CODEC_SCHEMA,"Content",value);if(f.codec.decode(a.CODEC_SCHEMA,"Content",bytes).text!=="")throw Error();console.log("no engine/compiler PASS");'
    assert 'no engine/compiler PASS' in compile_program(tmp_path,source)
    assert not any('validation' in p.name or p.name in {'taut_client.ts','cli.py'} for p in (tmp_path/'generated').glob('*.ts'))

def test_object_intrinsic_class_collision_is_clear(tmp_path):
    s=schema(Object=Msg(value=F(1,STR)));emit_direct(s,tmp_path/'off')
    with pytest.raises(ValueError,match='Object.*intrinsic'):emit_direct(s,tmp_path/'on',validation=True)

@pytest.mark.parametrize('component',['trailing.','trailing ','CON','x:y'])
def test_windows_ambiguous_namespace_root_is_refused(tmp_path,component):
    if os.name!='nt':pytest.skip('Windows namespace test')
    raw='\\\\?\\'+str(tmp_path/'owner')+'\\'+component
    before={str(p):p.read_bytes() for p in tmp_path.rglob('*') if p.is_file()}
    with pytest.raises(ValueError,match='namespace'):
        rt.binding({'typescript':{'source_root':raw}},tmp_path/'schema','source')
    assert before=={str(p):p.read_bytes() for p in tmp_path.rglob('*') if p.is_file()}

def test_external_dependency_graph_and_enum_facts(tmp_path,foundation):
    package,_=foundation;module=(package/'cjs/foundation.js').as_posix();engine=(package/'cjs/validation.js').as_posix()
    kind=Enum('Kind',yes=0,no=1)
    child=schema(kind,Child=Msg(kind=F(1,OneOf(kind)),value=F(2,STR,Case(kind=kind.yes))))
    emit_direct(child,tmp_path/'child',mode='package',runtime_module=module,validation_module=engine)
    parent=dataclasses.replace(child,messages=dict(child.messages,Parent=schema(Parent=Msg(child=F(1,Ref.Child))).messages['Parent']))
    with pytest.raises(ValueError,match='full dependency graph'):
        emit_direct(parent,tmp_path/'incomplete',validation=True,mode='package',runtime_module=module,validation_module=engine,external_types={'Child':'../child/api.ts'})
    mapping={'Child':'../child/api.ts','Kind':'../child/api.ts'}
    emit_direct(parent,tmp_path/'parent',validation=True,mode='package',runtime_module=module,validation_module=engine,external_types=mapping)
    assert 'PASS' in compile_program(tmp_path,'import {Parent} from "./parent/api.ts";const p=new Parent({child:{kind:"yes",value:null}});if(p.isValid() || p.validate().issues[0].path[0].fieldName!=="child")throw Error();console.log("PASS");')
    changed=dataclasses.replace(parent,enums={'Kind':dataclasses.replace(parent.enums['Kind'],members={'yes':42,'no':1})})
    emit_direct(changed,tmp_path/'changed',validation=True,mode='package',runtime_module=module,validation_module=engine,external_types=mapping)
    program=compile_program(tmp_path,'import "./changed/api.ts";',name='changed-main',execute=False)
    assert 'external enum' in run(['node',program],success=False).stderr

@pytest.mark.parametrize('fault',['missing-link','wrong-category','descriptor-version','future-rule','codec-option'])
def test_bad_metadata_fails_before_validation(tmp_path,fault):
    emit_direct(schema(Plain=Msg(value=F(1,STR))),tmp_path/'generated')
    init={'missing-link':'const fields=[new f.FieldDescriptor("child","child",1,{kind:"message",binding:()=>undefined as any},"required")];',
          'wrong-category':'const fields=[new f.FieldDescriptor("kind","kind",1,{kind:"enum",enum:()=>({} as any)},"required")];',
          'descriptor-version':'const fields:f.FieldDescriptor[]=[];',
          'future-rule':'const fields:f.FieldDescriptor[]=[];',
          'codec-option':'const fields:f.FieldDescriptor[]=[];'}[fault]
    ver=2 if fault=='descriptor-version' else 1
    constraints='[new f.ConstraintDescriptor("future.unsupported.v1")]' if fault=='future-rule' else '[]'
    options='{max_depth:32,max_encoded_len:null,future:1}' if fault=='codec-option' else '{max_depth:32,max_encoded_len:null}'
    source='import * as f from "./generated/foundation.ts";'+init+f'const d=new f.MessageDescriptor("Bad","Bad",{ver},fields,[],{constraints},[],[],null,{{}},{options});'+\
        'const b=new f.MessageBinding<any>(d,()=>null,(v:unknown):v is any=>true);let failed=false;try{f.publish(new f.SchemaDescriptor("bad",3,{Bad:d},{},{},{max_depth:32,max_encoded_len:null}),[b]);}catch(e){if(!(e instanceof f.ConfigurationError))throw e;failed=true;}if(!failed)throw Error("accepted bad metadata");console.log("PASS");'
    assert 'PASS' in compile_program(tmp_path,source)

def test_dynamic_primitive_collection_misuse_is_located(tmp_path):
    s=schema(All=Msg(s=F(1,STR),i=F(2,INT),b=F(3,BOOL),bytes=F(4,BYTES),float=F(5,FLOAT),items=F(6,List(STR)),mapping=F(7,Map(INT,STR))))
    emit_direct(s,tmp_path/'generated',validation=True)
    source='import {All} from "./generated/api.ts";const v=new All({s:7,i:false,b:0,bytes:[],float:"1",items:[false],mapping:new Map([["wrong",1]])} as any);const r=v.validate();if(r.issues.length!==7 || r.issues.some(i=>i.code!=="validation.type_mismatch") || r.issues.map(i=>i.path[0].fieldName).join(",")!=="s,i,b,bytes,float,items,mapping" || v.isValid() || !v.isValid({recursive:false}))throw Error();console.log("PASS");'
    assert 'PASS' in compile_program(tmp_path,source)

@pytest.mark.parametrize('child_validation',[False,True])
def test_external_child_actual_exported_data_shape_and_omitted_payloads(tmp_path,foundation,child_validation):
    package,_=foundation;module=(package/'cjs/foundation.js').as_posix();engine=(package/'cjs/validation.js').as_posix()
    kind=Enum('Kind',text=0,empty=1)
    child=schema(kind,Child=Msg(kind=F(1,OneOf(kind)),text=F(2,STR,Case(kind=kind.text))))
    emit_direct(child,tmp_path/'child-source',mode='package',validation=child_validation,runtime_module=module,validation_module=engine)
    artifact=compile_program(tmp_path,'export * from "./child-source/api.ts";',execute=False,declaration=True,name='child')
    compiled=artifact.parent/'child-source/api.js'
    parent=dataclasses.replace(child,messages=dict(child.messages,Parent=schema(Parent=Msg(child=F(1,Ref.Child),children=F(2,List(Ref.Child)),mapping=F(3,Map(STR,Ref.Child)))).messages['Parent']))
    mapping={'Child':compiled.as_posix(),'Kind':compiled.as_posix()}
    emit_direct(parent,tmp_path/'parent',mode='package',validation=True,runtime_module=module,validation_module=engine,external_types=mapping)
    text='import {Parent,type Child} from "./parent/api.ts";const child:Child={kind:"empty"};const v=new Parent({child,children:[child],mapping:new Map([["x",child]])});if(!v.isValid() || v.child!==child || "validate" in child)throw Error();child.kind="text";const r=v.validate();if(r.issues.length!==3 || r.issues.some(i=>i.code!=="oneof.payload_missing"))throw Error();console.log("PASS");'
    assert 'PASS' in compile_program(tmp_path,text,name='external-data')
    negative='import {Parent} from "./parent/api.ts";const v=new Parent({child:{kind:"empty"},children:[],mapping:new Map()});v.child.validate();'
    assert 'does not exist' in compile_program(tmp_path,negative,name='external-negative',success=False).stdout
    # The real service emitter imports the separately compiled child's actual Fields export.
    from taut.gen.scaffold import emit
    from taut.ir.dsl import Params,method,service
    parent=dataclasses.replace(parent,services=schema(service('Svc',method('get',role='out',params=Params(child=Ref.Child),out=Ref.Parent))).services)
    emit(parent,tmp_path/'service',langs=['typescript'],runtime_mode='package',validation=True,
         runtime_bindings={'typescript':{'module':module,'validation_module':engine}},typescript_external_types=mapping)
    # Absolute external artifact specifiers survive the additional service output directory.
    code='import {SvcClient} from "./service/typescript/client.ts";import {type Child,type ParentFields,CODEC_SCHEMA} from "./service/typescript/api.ts";'+\
        f'import * as f from {json.dumps(module)};'+\
        'const child:Child={kind:"empty"};const data:ParentFields={child,children:[child],mapping:new Map([["x",child]])};const decoded:ParentFields=f.codec.decode(CODEC_SCHEMA,"Parent",f.codec.encode(CODEC_SCHEMA,"Parent",data));const client=new SvcClient({call:async()=>decoded,subscribe:()=>()=>{}});client.get(child).then(result=>{if("validate" in result || "validate" in result.child || "validate" in result.children[0] || "validate" in result.mapping.get("x")!)throw Error();console.log("service plain data PASS");});'
    assert 'service plain data PASS' in compile_program(tmp_path,code,name='service-data')
    negative=code.replace('console.log("service plain data PASS");','result.child.validate();')
    assert 'does not exist' in compile_program(tmp_path,negative,name='service-negative',success=False).stdout

def test_nested_local_codec_data_never_claims_methods(tmp_path):
    s=schema(Child=Msg(value=F(1,STR)),Parent=Msg(child=F(1,Ref.Child),children=F(2,List(Ref.Child)),mapping=F(3,Map(STR,Ref.Child))))
    emit_direct(s,tmp_path/'generated',validation=True)
    source='import {Parent,Child,type ParentFields,CODEC_SCHEMA} from "./generated/api.ts";import * as f from "./generated/foundation.ts";const data:ParentFields={child:{value:""},children:[{value:""}],mapping:new Map([["x",{value:""}]])};const decoded:ParentFields=f.codec.decode(CODEC_SCHEMA,"Parent",f.codec.encode(CODEC_SCHEMA,"Parent",data));if("validate" in decoded || "validate" in decoded.child)throw Error();const v=new Parent(decoded);if(!v.isValid() || v.child!==decoded.child)throw Error();const withClass:ParentFields={child:new Child({value:""}),children:[],mapping:new Map()};if(!(withClass.child instanceof Child))throw Error();console.log("PASS");'
    assert 'PASS' in compile_program(tmp_path,source)
    negative='import {type ParentFields,type Child} from "./generated/api.ts";const data:ParentFields={child:{value:""},children:[],mapping:new Map()};const constructed:Child=data.child;'
    assert 'missing' in compile_program(tmp_path,negative,name='nested-negative',success=False).stdout

@pytest.mark.parametrize('validation',[False,True])
def test_fields_alias_collisions_fail_before_output(tmp_path,validation):
    s=schema(Foo=Msg(value=F(1,STR)),FooFields=Msg(value=F(1,STR)))
    with pytest.raises(ValueError,match='symbol collision'):emit_direct(s,tmp_path/'generated',validation=validation)
    assert not (tmp_path/'generated').exists()

@pytest.mark.parametrize('validation',[False,True])
def test_native_residual_roundtrip_and_exact_storage_collision(tmp_path,validation):
    emit_direct(schema(Item=Msg(value=F(1,INT))),tmp_path/'generated',validation=validation)
    source='import * as a from "./generated/api.ts";import * as f from "./generated/foundation.ts";const bytes=f.encode(new Map<f.MapKey,f.CborValue>([[1,42n],[2,"future"],[9007199254740992n,new Map([[1,true]])]]));const data:a.ItemFields=f.codec.decode(a.CODEC_SCHEMA,"Item",bytes);'+\
        ('const value=new a.Item(data);if(value.__unknown__!==data.__unknown__ || !value.isValid() || value.validate().issues.length!==0)throw Error();' if validation else 'const value=data;')+\
        'if(a.ItemDescriptor.fields.length!==1 || a.ItemDescriptor.fields[0].name!=="value")throw Error();const after=f.codec.encode(a.CODEC_SCHEMA,"Item",value);if(after.length!==bytes.length || after.some((b,i)=>b!==bytes[i]))throw Error("lost residual tags");console.log("residual PASS");'
    assert 'residual PASS' in compile_program(tmp_path,source)
    with pytest.raises(ValueError,match='codec storage collision'):
        emit_direct(schema(Bad=Msg(__unknown__=F(1,STR))),tmp_path/'collision',validation=validation)
    assert not (tmp_path/'collision').exists()
