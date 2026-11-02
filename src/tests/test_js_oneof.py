"""Real CommonJS execution, Python-normalized conformance and physical owner proofs."""
import dataclasses
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import types
import pytest
from taut.gen.scaffold import emit, emit_all, python_api
from taut.gen.js_runtime import (OWNER, FILES, ENGINE, canonical_sources, canonical_path,
                                 build_foundation, verify_artifact)
from taut.ir.dsl import STR, INT, BOOL, Enum, F, Msg, Ref, OneOf, Case, List, Map, schema
from taut.ir.load import load_schema, schema_from_json
from taut.ir.export import schema_json

ROOT=Path(__file__).resolve().parents[2]
EXAMPLE=ROOT/'dev-docs/examples/js-oneof'
SCHEMA=load_schema(EXAMPLE/'content.taut.py')


def node(code, *, ok=True, cwd=None):
    r=subprocess.run(['node','-e',code],cwd=cwd,capture_output=True,encoding='utf-8')
    if ok: assert r.returncode==0,r.stdout+r.stderr
    return r


def req(path): return 'require('+json.dumps(str(path).replace('\\','/'))+')'


def python_rows():
    m=types.ModuleType('_js_oneof_reference');sys.modules[m.__name__]=m
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
    report('independent',m.Multi(left=None,right=m.Kind.number));report('plain',m.Plain(0,None,None))
    return rows


@pytest.fixture(scope='module')
def package(tmp_path_factory):
    root=tmp_path_factory.mktemp('js-foundation')
    artifact=build_foundation(root/'foundation.tgz',npm=shutil.which('npm.cmd') or shutil.which('npm'))
    with tarfile.open(artifact) as archive:
        for member in archive.getmembers():
            target=root/'unpacked'/member.name
            target.parent.mkdir(parents=True,exist_ok=True)
            target.write_bytes(archive.extractfile(member).read())
    return artifact,root/'unpacked/package'


@pytest.mark.parametrize('mode',['source','package',None])
def test_python_normalized_conformance(tmp_path,package,mode):
    artifact,owner=package
    bindings=None if mode=='source' else {'js':{'module':str(owner).replace('\\','/'),'artifact':str(artifact)}}
    emit(SCHEMA,tmp_path,langs=['js'],services=[],runtime_mode=mode,validation=True,runtime_bindings=bindings)
    d=tmp_path/'js';codec=d/'cbor.js' if mode=='source' else owner/'cbor.js'
    r=subprocess.run(['node',EXAMPLE/'conformance.js',d/'api.js',codec],capture_output=True,encoding='utf-8')
    assert r.returncode==0,r.stdout+r.stderr
    assert r.stdout.splitlines()==python_rows()
    if mode=='source':
        for name,data in canonical_sources().items(): assert (d/name).read_bytes()==data
    else: assert not (d/'cbor.js').exists()


@pytest.mark.parametrize('validation',[False,True])
def test_metadata_complete_deeply_immutable(tmp_path,validation):
    emit(SCHEMA,tmp_path,langs=['js'],services=[],runtime=True,validation=validation)
    d=tmp_path/'js'
    node('"use strict";const assert=require("node:assert/strict");const a='+req(d/'api.js')+';'+'''
      const d=a.ContentDescriptor;assert.equal(a.Content.descriptor(),d);
      assert.equal(d.fields.length,6);assert.equal(d.nextId,9);assert.deepEqual(d.reservedNumbers,[7]);
      assert.deepEqual(d.reservedNames,["retired"]);assert.equal(d.fields[0].type.kind,"enum");
      assert.equal(a.VirtualDescriptor.fields[0].virtual,true);assert.equal(a.VirtualDescriptor.fields[0].attribute,null);
      assert.equal(d.oneofs[0].members.empty,null);assert.equal(d.constraints[0].rule,"taut.oneof.v1");
      assert.equal(d.effectiveOptions.max_depth,32);assert.equal(a.$tautSchema.irVersion,3);
      for(const change of [()=>d.fields.push(1),()=>d.fields[0].options.x=1,()=>d.oneofs[0].members.empty="text",()=>a.$tautSchema.messages.Content=null,()=>a.$tautBinding.adapters.Content.read.kind=()=>1]) assert.throws(change,TypeError);
      assert.equal(Object.getPrototypeOf(a.$tautSchema.messages),null);
      assert.equal(Object.hasOwn(new a.Virtual(),"kind"),false);
    ''')
    text=(d/'api.js').read_text()
    assert ('  validate(' in text) is validation
    assert (d/ENGINE).exists() is validation
    if not validation:
        assert 'validation.js' not in text
        node('const a='+req(d/'api.js')+';a.Content.descriptor();if(Object.keys(require.cache).some(k=>k.endsWith("validation.js")))throw Error("engine imported");')


def test_options_dynamic_misuse_and_snapshots(tmp_path):
    emit(SCHEMA,tmp_path,langs=['js'],services=[],runtime=True,validation=True)
    d=tmp_path/'js'
    node('"use strict";const assert=require("node:assert/strict");const a='+req(d/'api.js')+';const r='+req(d/'reports.js')+';'+'''
      const c=new a.Content({kind:a.Kind.text});const v=new a.Virtual({child:c});
      assert.equal(v.validate().scope,"recursive");assert.equal(v.validate({}).issues.length,1);
      for(const options of [null,false,0,"x",[],{recursive:null},{recursive:undefined},{extra:true},new Map()]) {
        assert.throws(()=>v.validate(options),TypeError);assert.throws(()=>v.isValid(options),TypeError);
      }
      const before=c.validate();c.text="";assert.equal(c.isValid(),true);assert.equal(before.issues.length,1);
      assert.throws(()=>before.issues.pop(),TypeError);assert.throws(()=>before.issues[0].path.push(1),TypeError);
      c.text=14;assert.equal(c.validate().issues[0].code,"validation.type_mismatch");
      c.child={};assert.equal(c.validate().issues.at(-1).path.at(-1).fieldName,"child");
      const root=a.Content.prototype.validate.call({});assert.equal(root.issues[0].path.length,0);
      delete c.text;assert.equal(c.validate().issues[0].code,"validation.type_mismatch");
      const path=[r.PathSegment.forField("x")],issue=new r.ValidationIssue("future.test","future.rule",path,"test");path.pop();
      const issues=[issue],report=new r.ValidationReport(issues);issues.pop();assert.equal(report.issues.length,1);
      assert.equal(report.isValid(),false);assert.equal(report.isComplete(),true);
      assert.equal(issue.path[0].index,null);assert.equal(issue.path[0].keyType,null);
      for(const i of [-1,1.5,Number.MAX_SAFE_INTEGER+1,NaN,true])assert.throws(()=>r.PathSegment.forIndex(i),TypeError);
      assert.throws(()=>new r.PathSegment("key",null,null,"int","AA"),TypeError);
    ''')


@pytest.mark.parametrize('virtual',[False,True])
@pytest.mark.parametrize('exhaustive',[False,True])
def test_flags_and_native_normalization(tmp_path,virtual,exhaustive):
    e=Enum('Choice',a=0,b=1)
    s=schema(e,Record=Msg(tag=F(1,OneOf(e,virtual=virtual,exhaustive=exhaustive)),data=F(2,STR,Case(tag=e.a),Case(tag=e.b))))
    emit(s,tmp_path,langs=['js'],services=[],runtime=True,validation=True)
    node('const a='+req(tmp_path/'js/api.js')+';const v=new a.Record({tag:a.Choice.a,data:""});if(v.isValid()!=='+str(not virtual).lower()+')throw Error("flags");')


@pytest.mark.parametrize('mode',['source','package'])
@pytest.mark.parametrize('validation',[False,True])
def test_i64_enum_extrema_and_metadata_member_names(tmp_path,package,mode,validation):
    e=Enum('Choice',a=0,b=1)
    doc=schema_json(schema(e,Record=Msg(tag=F(1,e))))
    doc['enums'][0]['members']={'name':-(2**63),'__proto__':2**63-1}
    doc['enums'][0]['member_options']={n:{} for n in doc['enums'][0]['members']}
    doc['messages'][0]['fields'][0]['oneof']={'enum':'Choice','virtual':False,'exhaustive':False};doc['version']=3
    s=schema_from_json(doc)
    artifact,owner=package
    bindings=None if mode=='source' else {'js':{'module':str(owner).replace('\\','/'),'artifact':str(artifact)}}
    emit(s,tmp_path,langs=['js'],services=[],runtime_mode=mode,validation=validation,runtime_bindings=bindings)
    codec=tmp_path/'js/cbor.js' if mode=='source' else owner/'cbor.js'
    node('const assert=require("node:assert/strict");const a='+req(tmp_path/'js/api.js')+';const c='+req(codec)+';'+'''
       for(const tag of [a.Choice.name,a.Choice.__proto__]) {
         assert.equal(typeof tag,"bigint");const v=new a.Record({tag});
         assert.equal(a.Record.decode(c.encode(v.toCbor())).tag,tag);
         if(v.isValid)assert.equal(v.isValid(),true);
       }
    ''')


@pytest.mark.parametrize('child_mode,parent_mode',[('source','source'),('package','package'),('source','package'),('package','source')])
def test_separate_disabled_child_one_actual_owner(tmp_path,package,child_mode,parent_mode):
    artifact,package_owner=package
    child=dataclasses.replace(SCHEMA,messages={'Content':SCHEMA.messages['Content']})
    parent=dataclasses.replace(child,messages={**child.messages,**schema(Parent=Msg(child=F(1,Ref('Content')))).messages})
    source_owner=tmp_path/'owner'
    if 'source' in (child_mode,parent_mode):
        binding={'js':{'source_root':str(source_owner)}}
        emit(schema(OwnerUser=Msg()),tmp_path/'owner-user',langs=['js'],services=[],runtime=True,validation=True,runtime_bindings=binding)
        owner=source_owner
    else:
        binding={'js':{'module':str(package_owner).replace('\\','/'),'artifact':str(artifact)}}
        owner=package_owner
    emit(child,tmp_path/'child',langs=['js'],services=[],runtime_mode=child_mode,runtime_bindings=binding,schema_identity='child')
    cd=tmp_path/'child/js/api.js';before=cd.read_bytes()
    external={n:{'module':str(cd).replace('\\','/')} for n in ('Kind','Content')}
    emit(parent,tmp_path/'parent',langs=['js'],services=[],runtime_mode=parent_mode,validation=True,
         runtime_bindings=binding,js_external_types=external,schema_identity='parent')
    assert cd.read_bytes()==before
    node('const assert=require("node:assert/strict");const child='+req(cd)+';const p='+req(tmp_path/'parent/js/api.js')+';const r='+req(owner/'reports.js')+';const codec='+req(owner/'cbor.js')+';'+'''
      const v=new p.Parent({child:new child.Content({kind:child.Kind.text})});
      const report=v.validate();assert(report instanceof r.ValidationReport);assert(report.issues[0] instanceof r.ValidationIssue);
      assert.equal(p.Content,child.Content);assert.equal(p.ContentDescriptor,child.ContentDescriptor);
      assert.equal(typeof child.Content.prototype.validate,"undefined");assert.equal(v.isValid({recursive:false}),true);
      assert.equal(report.issues[0].path[0].fieldName,"child");assert.equal(report.issues[0].path[1].fieldName,"text");
      assert.equal(child.Content.decode(codec.encode(v.child.toCbor())).kind,child.Kind.text);
    ''')


def test_split_owner_and_old_child_fail_before_validation(tmp_path):
    child=dataclasses.replace(SCHEMA,messages={'Content':SCHEMA.messages['Content']})
    parent=dataclasses.replace(child,messages={**child.messages,**schema(Parent=Msg(child=F(1,Ref('Content')))).messages})
    emit(child,tmp_path/'child',langs=['js'],services=[],runtime=True)
    cd=tmp_path/'child/js/api.js'
    emit(parent,tmp_path/'parent',langs=['js'],services=[],runtime=True,validation=True,
         js_external_types={n:{'module':str(cd).replace('\\','/')} for n in ('Kind','Content')})
    r=node(req(tmp_path/'parent/js/api.js'),ok=False)
    assert r.returncode and 'split-owner' in r.stderr
    cd.write_text('module.exports={Kind:{text:0},Content:class Content{}};')
    r=node(req(tmp_path/'parent/js/api.js'),ok=False)
    assert r.returncode and 'missing/old' in r.stderr


@pytest.mark.parametrize('mutation',['field_type','effective','case','enum'])
def test_external_compiled_artifact_substitution_rejected(tmp_path,mutation):
    child=dataclasses.replace(SCHEMA,messages={'Content':SCHEMA.messages['Content']})
    parent=dataclasses.replace(child,messages={**child.messages,**schema(Parent=Msg(child=F(1,Ref('Content')))).messages})
    owner=tmp_path/'owner';binding={'js':{'source_root':str(owner)}}
    emit(schema(OwnerUser=Msg()),tmp_path/'owner-user',langs=['js'],services=[],runtime=True,validation=True,runtime_bindings=binding)
    emit(child,tmp_path/'child',langs=['js'],services=[],runtime=True,runtime_bindings=binding)
    cd=tmp_path/'child/js/api.js'
    emit(parent,tmp_path/'parent',langs=['js'],services=[],runtime=True,validation=True,runtime_bindings=binding,
         js_external_types={n:{'module':str(cd).replace('\\','/')} for n in ('Kind','Content')})
    # Save an already-generated parent. Then substitute an independently generated artifact.
    doc=schema_json(child)
    if mutation=='field_type':doc['messages'][0]['fields'][1]['type']={'k':'scalar','scalar':'bytes'}
    if mutation=='effective':
        doc['options']={'max_depth':16};doc['effective']['max_depth']=16
        for message in doc['messages']:message['effective']['max_depth']=16
    if mutation=='case':doc['messages'][0]['fields'][1]['cases'][0]['member']='empty'
    if mutation=='enum':doc['enums'][0]['members']['text']=99
    replacement=schema_from_json(doc)
    emit(replacement,tmp_path/'replacement',langs=['js'],services=[],runtime=True,runtime_bindings=binding)
    cd.write_bytes((tmp_path/'replacement/js/api.js').read_bytes())
    r=node(req(tmp_path/'parent/js/api.js'),ok=False)
    assert r.returncode and 'incompatible external descriptor' in r.stderr


def test_external_equivalent_order_and_patch_labels_accepted(tmp_path):
    child=dataclasses.replace(SCHEMA,messages={'Content':SCHEMA.messages['Content']})
    parent=dataclasses.replace(child,messages={**child.messages,**schema(Parent=Msg(child=F(1,Ref('Content')))).messages})
    owner=tmp_path/'owner';binding={'js':{'source_root':str(owner)}}
    emit(schema(OwnerUser=Msg()),tmp_path/'owner-user',langs=['js'],services=[],runtime=True,validation=True,runtime_bindings=binding)
    doc=schema_json(child);doc['messages'][0]['fields'].reverse();doc['enums'][0]['members']=dict(reversed(list(doc['enums'][0]['members'].items())))
    emit(schema_from_json(doc),tmp_path/'child',langs=['js'],services=[],runtime=True,runtime_bindings=binding,schema_identity='old-build')
    cd=tmp_path/'child/js/api.js'
    emit(parent,tmp_path/'parent',langs=['js'],services=[],runtime=True,validation=True,runtime_bindings=binding,schema_identity='new-build',
         js_external_types={n:{'module':str(cd).replace('\\','/')} for n in ('Kind','Content')})
    contract=owner/'contracts.js';contract.write_text(contract.read_text().replace('javascript-oneof-reference.1','compatible-patch.9'))
    node('const a='+req(tmp_path/'parent/js/api.js')+';if(new a.Parent({child:new a.Content({kind:a.Kind.empty})}).isValid()!==true)throw Error("compatibility");')


def test_canonical_i64_key_paths_and_collection_cycles(tmp_path):
    s=schema(Record=Msg(children=F(1,List(Ref('Record'))),values=F(2,Map(INT,Ref('Record')))))
    emit(s,tmp_path,langs=['js'],services=[],runtime=True,validation=True)
    d=tmp_path/'js'
    node('const assert=require("node:assert/strict");const a='+req(d/'api.js')+';const c='+req(d/'cbor.js')+';const r='+req(d/'reports.js')+';'+'''
      const bad=new a.Record({children:[],values:new Map()});bad.children.push(bad);
      const root=new a.Record({children:[],values:new Map([[9223372036854775807n,bad],[-9223372036854775808n,bad],[0n,bad]])});
      const report=root.validate();assert.equal(report.issues.length,3);assert.equal(root.isValid(),false);
      const encoded=[0n,9223372036854775807n,-9223372036854775808n].map(k=>Buffer.from(c.encode(c.CInt(k))).toString("base64"));
      assert.deepEqual(report.issues.map(i=>i.path[1].keyCborBase64),encoded);
      const bytes=c.encode(c.CInt(9223372036854775807n)),segment=r.PathSegment.forKey("int",bytes);bytes[0]=0;
      assert.equal(segment.keyCborBase64,encoded[1]);
      assert.throws(()=>r.PathSegment.forKey("bool",c.encode(c.CInt(1n))),TypeError);
      root.values=new Map([[1,bad]]);assert.equal(root.validate().issues[0].code,"validation.type_mismatch");
    ''')


@pytest.mark.parametrize('name',['__proto__','constructor','prototype','default','__private','metadata','name'])
def test_field_names_preserve_originals_without_prototype_changes(tmp_path,name):
    s=schema(Record=Msg(**{name:F(1,INT)}))
    emit(s,tmp_path,langs=['js'],services=[],runtime=True,validation=True)
    node('const assert=require("node:assert/strict");const a='+req(tmp_path/'js/api.js')+';const c='+req(tmp_path/'js/cbor.js')+';'+
         'const input=Object.fromEntries([['+json.dumps(name)+',9n]]),v=new a.Record(input);assert.equal(Object.getPrototypeOf(v),a.Record.prototype);assert.equal(v.isValid(),true);assert.equal(a.Record.decode(c.encode(v.toCbor()))['+json.dumps(name)+'],9n);assert.equal(a.RecordDescriptor.fields[0].name,'+json.dumps(name)+');')


@pytest.mark.parametrize('name',['validate','isValid','toCbor'])
def test_actual_method_collisions_refused_before_writes(tmp_path,name):
    s=schema(Record=Msg(**{name:F(1,INT)}))
    with pytest.raises(ValueError,match='collid|reserved'):
        emit(s,tmp_path,langs=['js'],services=[],runtime=True,validation=True)
    assert not list(tmp_path.iterdir())


def tree(root):return {p.relative_to(root).as_posix():p.read_bytes() for p in root.rglob('*') if p.is_file()}


@pytest.mark.parametrize('file',['api.js','cbor.js','contracts.js','descriptors.js','reports.js','validation.js'])
def test_modified_or_handwritten_files_unchanged(tmp_path,file):
    root=tmp_path/'fresh';d=root/'js';d.mkdir(parents=True);(d/file).write_text('// handwritten')
    before=tree(tmp_path)
    with pytest.raises(ValueError):emit(SCHEMA,root,langs=['js'],services=[],runtime=True,validation=True)
    assert tree(tmp_path)==before
    root=tmp_path/'modified';emit(SCHEMA,root,langs=['js'],services=[],runtime=True,validation=True)
    (root/'js'/file).write_text('// modified')
    before=tree(tmp_path)
    with pytest.raises(ValueError):emit(SCHEMA,root,langs=['js'],services=[],runtime=True,validation=False)
    assert tree(tmp_path)==before


def test_shared_users_transitions_preserve_engine_until_last_user(tmp_path):
    owner=tmp_path/'owner';binding={'js':{'source_root':str(owner)}}
    for name in ('a','b'):emit(SCHEMA,tmp_path/name,langs=['js'],services=[],runtime=True,validation=True,runtime_bindings=binding)
    emit(SCHEMA,tmp_path/'a',langs=['js'],services=[],runtime_mode='package',validation=False)
    assert (owner/ENGINE).exists()
    assert len(json.loads((owner/'.taut-js-runtime.json').read_text())['users'])==1
    emit(SCHEMA,tmp_path/'b',langs=['js'],services=[],runtime=True,validation=False,runtime_bindings=binding)
    assert not (owner/ENGINE).exists() and (owner/'descriptors.js').exists()
    assert ' validate(' not in (tmp_path/'b/js/api.js').read_text()
    emit(SCHEMA,tmp_path/'b',langs=['js'],services=[],runtime_mode='package')
    assert not list(owner.iterdir())


@pytest.mark.parametrize('mode',[None,'package'])
def test_unavailable_bound_source_owner_is_not_adopted(tmp_path,mode):
    with pytest.raises(ValueError,match='unavailable'):
        emit(SCHEMA,tmp_path/'output',langs=['js'],services=[],runtime_mode=mode,
             runtime_bindings={'js':{'source_root':str(tmp_path/'missing')}})
    assert not (tmp_path/'output').exists()


@pytest.mark.parametrize('kind',['file',pytest.param('symlink',marks=pytest.mark.posix)])
def test_obstructed_or_alias_owner_unchanged(tmp_path,kind):
    owner=tmp_path/'owner'
    if kind=='file': owner.write_text('obstruction')
    else:
        actual=tmp_path/'actual';actual.mkdir()
        try:owner.symlink_to(actual,target_is_directory=True)
        except OSError:pytest.skip('Windows symlink privilege unavailable; junction coverage is separate')
    before=tree(tmp_path)
    with pytest.raises(ValueError):emit(SCHEMA,tmp_path/'output',langs=['js'],services=[],runtime=True,runtime_bindings={'js':{'source_root':str(owner)}})
    assert tree(tmp_path)==before


@pytest.mark.parametrize('binding',[{'owner':'old'}, {'descriptor_contract':True}, {'codec_contract':0}, {'capabilities':['oneof.v9']}, {'unknown':'x'}])
def test_incompatible_claimed_bindings_leave_no_outputs(tmp_path,binding):
    with pytest.raises(ValueError):emit(SCHEMA,tmp_path,langs=['js'],services=[],runtime=True,runtime_bindings={'js':binding})
    assert not list(tmp_path.iterdir())


def test_actual_loaded_codec_contract_is_checked(tmp_path):
    emit(SCHEMA,tmp_path,langs=['js'],services=[],runtime=True)
    d=tmp_path/'js';p=d/'cbor.js';p.write_text(p.read_text().replace('get foundationOwner()', 'get oldFoundationOwner()'))
    r=node(req(d/'api.js'),ok=False)
    assert r.returncode and 'codec owner' in r.stderr


@pytest.mark.parametrize('artifact,old,new',[('cbor.js','foundationCodecContract: 1','foundationCodecContract: 0'),('validation.js','engineContract:1','engineContract:0')])
def test_actual_loaded_contract_substitution_is_rejected(tmp_path,artifact,old,new):
    emit(SCHEMA,tmp_path,langs=['js'],services=[],runtime=True,validation=True)
    d=tmp_path/'js';p=d/artifact;p.write_text(p.read_text().replace(old,new))
    r=node(req(d/'api.js'),ok=False)
    assert r.returncode and ('regenerate/rebind' in r.stderr or 'codec owner' in r.stderr)


def test_foreign_codec_cannot_hide_behind_descriptor_facade(tmp_path):
    emit(SCHEMA,tmp_path/'real',langs=['js'],services=[],runtime=True,validation=True)
    real=tmp_path/'real/js';facade=tmp_path/'facade';facade.mkdir()
    for name in ('contracts.js','descriptors.js','reports.js','validation.js'):
        (facade/name).write_text('module.exports='+req(real/name)+';')
    # Equal source and equal advertised owner labels cannot manufacture class identity.
    (facade/'cbor.js').write_bytes((real/'cbor.js').read_bytes())
    emit(SCHEMA,tmp_path/'consumer',langs=['js'],services=[],validation=True,
         runtime_bindings={'js':{'module':str(facade).replace('\\','/')}})
    r=node(req(tmp_path/'consumer/js/api.js'),ok=False)
    assert r.returncode and 'split/incompatible JavaScript codec owner' in r.stderr
    (facade/'cbor.js').write_text('module.exports='+req(real/'cbor.js')+';')
    node('const a='+req(tmp_path/'consumer/js/api.js')+';if(!new a.Content({kind:a.Kind.empty}).isValid())throw Error("facade");')


def test_cjs_dynamic_esm_import_and_two_schemas_share_actual_package_owner(tmp_path,package):
    artifact,owner=package;binding={'js':{'module':str(owner).replace('\\','/'),'artifact':str(artifact)}}
    for name in ('a','b'):emit(SCHEMA,tmp_path/name,langs=['js'],services=[],runtime_mode='package',validation=True,runtime_bindings=binding)
    node('const assert=require("node:assert/strict");const a='+req(tmp_path/'a/js/api.js')+';const b='+req(tmp_path/'b/js/api.js')+';const f='+req(owner/'index.js')+';'+'''
      const r1=new a.Content({kind:a.Kind.text}).validate(),r2=new b.Content({kind:b.Kind.text}).validate();
      assert.equal(r1.constructor,r2.constructor);assert.equal(r1.constructor,f.ValidationReport);
      assert.equal(a.ContentDescriptor.constructor,b.ContentDescriptor.constructor);assert.equal(a.ContentDescriptor.constructor,f.MessageDescriptor);
      import(require("node:url").pathToFileURL('''+json.dumps(str(owner/'index.js'))+''').href).then(esm=>{
        assert.equal(esm.default.ValidationReport,f.ValidationReport);assert.equal(esm.default.cbor.DecodeError,f.cbor.DecodeError);
        assert.equal(esm.default.cbor.EncodeError,f.cbor.EncodeError);
      }).catch(e=>{console.error(e);process.exitCode=1;});
    ''')


def test_actual_local_package_exports_and_default_module_resolution(tmp_path,package):
    artifact,owner=package
    application=tmp_path/'app'
    # Extracted local package placement is a proof, not dependency installation.
    shutil.copytree(owner,application/'node_modules/taut-js-foundation')
    emit(SCHEMA,application,langs=['js'],services=[],runtime_mode='package',validation=True,
         runtime_bindings={'js':{'artifact':str(artifact)}})
    node('const assert=require("node:assert/strict");const a=require("./js/api.js"),f=require("taut-js-foundation"),r=require("taut-js-foundation/reports.js");assert.equal(f.ValidationReport,r.ValidationReport);assert(new a.Content({kind:a.Kind.text}).validate() instanceof f.ValidationReport);assert.equal(f.cbor.DecodeError,require("taut-js-foundation/cbor.js").DecodeError);',cwd=application)


def test_engine_free_package_descriptors_and_enabled_artifact_refusal(tmp_path):
    artifact=build_foundation(tmp_path/'off.tgz',validation=False)
    owner=tmp_path/'package'
    with tarfile.open(artifact) as archive:
        for member in archive.getmembers():
            target=tmp_path/member.name;target.parent.mkdir(parents=True,exist_ok=True)
            target.write_bytes(archive.extractfile(member).read())
    binding={'js':{'module':str(owner).replace('\\','/'),'artifact':str(artifact)}}
    emit(SCHEMA,tmp_path/'off',langs=['js'],services=[],runtime_mode='package',runtime_bindings=binding)
    node('const a='+req(tmp_path/'off/js/api.js')+';a.Content.descriptor();if(Object.keys(require.cache).some(k=>k.endsWith("validation.js")))throw Error("engine");')
    with pytest.raises(ValueError,match='contracts/capabilities'):
        emit(SCHEMA,tmp_path/'on',langs=['js'],services=[],runtime_mode='package',validation=True,runtime_bindings=binding)
    assert not (tmp_path/'on').exists()


@pytest.mark.skipif(os.name!='nt',reason='Windows physical-path contract')
def test_windows_junction_and_namespace_ambiguity_refused(tmp_path):
    actual=tmp_path/'actual';actual.mkdir();owner=tmp_path/'junction'
    r=subprocess.run(['cmd','/c','mklink','/J',str(owner),str(actual)],capture_output=True)
    assert r.returncode==0,r.stderr
    with pytest.raises(ValueError,match='unsafe'):
        emit(SCHEMA,tmp_path/'output',langs=['js'],services=[],runtime=True,runtime_bindings={'js':{'source_root':str(owner)}})
    assert not (tmp_path/'output').exists() and not list(actual.iterdir())
    for suffix in ('trailing.','trailing ','NUL','x:stream'):
        path='\\\\?\\'+str(tmp_path)+'\\'+suffix
        with pytest.raises(ValueError):canonical_path(path)


def test_equivalent_root_reuse_and_engine_preservation(tmp_path):
    owner=tmp_path/'owner';binding={'js':{'source_root':str(owner)}}
    emit(SCHEMA,tmp_path/'a',langs=['js'],services=[],runtime=True,validation=True,runtime_bindings=binding)
    alternate=owner/'unused'/'..'
    emit(SCHEMA,tmp_path/'a',langs=['js'],services=[],runtime=True,validation=False,runtime_bindings={'js':{'source_root':str(alternate)}})
    assert (owner/'descriptors.js').exists() and not (owner/ENGINE).exists()
    manifest=json.loads((owner/'.taut-js-runtime.json').read_text());assert len(manifest['users'])==1


def test_bad_descriptor_links_rules_and_versions_are_configuration_errors(tmp_path):
    emit(SCHEMA,tmp_path,langs=['js'],services=[],runtime=True)
    d=tmp_path/'js'
    node('const assert=require("node:assert/strict");const a='+req(d/'api.js')+';const d='+req(d/'descriptors.js')+';const c='+req(d/'contracts.js')+';'+'''
      function bind(message,version=1,ir=3) {
        const schema=new d.SchemaDescriptor(version,ir,"probe",{Record:message},{},{});
        return ()=>new d.SchemaBinding(schema,{Record:{type:class Record{},read:{x:v=>v.x}}});
      }
      const badLink=new d.MessageDescriptor("Record","p.Record",1,[new d.FieldDescriptor("x","x",1,new d.TypeDescriptor("message","Missing"),"required")]);
      assert.throws(bind(badLink),c.ConfigurationError);
      const unknown=new d.MessageDescriptor("Record","p.Record",1,[],[],[new d.ConstraintDescriptor("future.rule",{})]);
      assert.throws(bind(unknown),c.ConfigurationError);
      const plain=new d.MessageDescriptor("Record","p.Record",1,[]);
      assert.throws(bind(plain,2),c.ConfigurationError);assert.throws(bind(plain,1,99),c.ConfigurationError);
    ''')


@pytest.mark.parametrize('case',['unknown_control','ordinary_control','wrong_enum','duplicate','multiple_controls','exhaustive','empty','optional_tag'])
def test_native_schema_errors_before_any_writes(tmp_path,case):
    e,other=Enum('Choice',a=0,b=1),Enum('OtherChoice',a=0)
    controls={'tag':F(1,OneOf(e))};payloads={'data':F(3,STR,Case(tag=e.a))}
    if case=='unknown_control':payloads={'data':F(3,STR,Case(absent=e.a))}
    elif case=='ordinary_control':controls={'tag':F(1,e)}
    elif case=='wrong_enum':payloads={'data':F(3,STR,Case(tag=other.a))}
    elif case=='duplicate':payloads['extra']=F(4,INT,Case(tag=e.a))
    elif case=='multiple_controls':
        controls['other']=F(2,OneOf(e));payloads={'data':F(3,STR,Case(tag=e.a),Case(other=e.b))}
    elif case=='exhaustive':controls={'tag':F(1,OneOf(e,exhaustive=True))}
    elif case=='empty':e=Enum('Choice');controls={'tag':F(1,OneOf(e))};payloads={}
    elif case=='optional_tag':controls={'tag':F(1,OneOf(e),optional=True)}
    s=schema(e,other,Record=Msg(**controls,**payloads))
    with pytest.raises(ValueError):emit(s,tmp_path,langs=['js'],services=[],runtime=True,validation=True)
    assert not list(tmp_path.iterdir())


def test_dynamic_scalar_collection_shapes_have_located_issues(tmp_path):
    emit(SCHEMA,tmp_path,langs=['js'],services=[],runtime=True,validation=True)
    d=tmp_path/'js'
    node('const assert=require("node:assert/strict");const a='+req(d/'api.js')+';'+'''
      const cases=[
        [new a.Content({kind:a.Kind.number,number:7}),["number"]],
        [new a.Content({kind:a.Kind.text,text:7}),["text"]],
        [new a.Content({kind:a.Kind.flag,flag:0}),["flag"]],
        [new a.Content({kind:a.Kind.items,items:[true]}),["items",0]],
        [new a.Content({kind:a.Kind.items,items:{}}),["items"]],
        [new a.Content({kind:a.Kind.child,child:{}}),["child"]],
        [new a.Plain({value:0n,blob:[],ratio:0}),["blob"]],
        [new a.Plain({value:0n,blob:null,ratio:0n}),["ratio"]],
        [new a.Wrapper({child:null,children:null,by_text:{},by_int:null,by_bool:null}),["by_text"]]
      ];
      for(const [v,path] of cases) {
        const report=v.validate();assert.equal(v.isValid(),false);
        assert.equal(report.issues[0].code,"validation.type_mismatch");
        assert.deepEqual(report.issues[0].path.map(p=>p.kind==="field"?p.fieldName:p.index),path);
        assert.equal(v.isValid({recursive:false}),true);
      }
      const v=new a.Content({kind:"text",child:new a.Content({kind:a.Kind.text})});
      assert.deepEqual(v.validate().issues.map(i=>i.code),["oneof.invalid_discriminator","oneof.payload_missing"]);
    ''')


@pytest.mark.parametrize('name',['class','default','eval','arguments'])
def test_type_keyword_escaping_preserves_exports_and_metadata(tmp_path,name):
    doc=schema_json(schema(Record=Msg(value=F(1,INT))))
    doc['messages'][0]['name']=name
    emit(schema_from_json(doc),tmp_path,langs=['js'],services=[],runtime=True,validation=True)
    node('const assert=require("node:assert/strict");const a='+req(tmp_path/'js/api.js')+';const v=new a['+json.dumps(name)+']({value:0n});assert.equal(v.isValid(),true);assert.equal(v.constructor.descriptor().name,'+json.dumps(name)+');')


def test_fast_path_does_not_construct_diagnostics_or_reports(tmp_path):
    emit(SCHEMA,tmp_path,langs=['js'],services=[],runtime=True,validation=True)
    d=tmp_path/'js'
    node('const assert=require("node:assert/strict");const rp='+json.dumps(str(d/'reports.js'))+';const reports=require(rp);const bad=class {constructor(){throw Error("report allocation");}};require.cache[require.resolve(rp)].exports={...reports,ValidationReport:bad,ValidationIssue:bad,DeferredCheck:bad};const a='+req(d/'api.js')+';'+'''
      assert.equal(new a.Content({kind:a.Kind.text}).isValid(),false);
      assert.equal(new a.Content({kind:a.Kind.text,text:""}).isValid(),true);
      assert.equal(new a.Virtual({child:new a.Content({kind:a.Kind.empty})}).isValid(),false);
      assert.throws(()=>new a.Content({kind:a.Kind.empty}).validate(),/report allocation/);
    ''')


def test_source_module_disagreement_refused_and_hidden_source_owner_works(tmp_path):
    with pytest.raises(ValueError,match='actual shared source owner'):
        emit(SCHEMA,tmp_path/'bad',langs=['js'],services=[],runtime=True,runtime_bindings={'js':{'module':'./elsewhere'}})
    assert not (tmp_path/'bad').exists()
    root=tmp_path/'output';owner=root/'js/.owner'
    emit(SCHEMA,root,langs=['js'],services=[],runtime=True,validation=True,runtime_bindings={'js':{'source_root':str(owner)}})
    node('const a='+req(root/'js/api.js')+';if(!new a.Content({kind:a.Kind.empty}).isValid())throw Error("hidden owner");')
