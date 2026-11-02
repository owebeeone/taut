"""Round-one regressions for the original ECMA review counterexamples."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import pytest

from test_typescript_oneof import (ROOT, compile_program, emit_direct, run, foundation, shape_package)
from taut.ir.dsl import STR, Enum, F, Msg, OneOf, Case, Ref, schema


@pytest.fixture(scope='module')
def original_r0_owner(tmp_path_factory):
    directory=tmp_path_factory.mktemp('original-r0-ts-owner');source=directory/'source';source.mkdir()
    from taut.gen.typescript_runtime import FILES
    # An exported review tree can point explicitly at its read-only origin Git
    # repository. Only immutable r0 blobs are read; working source is never used.
    repository=Path(os.environ.get('TAUT_R0_REPOSITORY',ROOT)).resolve()
    hashes={}
    import hashlib
    for name,resource in FILES.items():
        data=subprocess.check_output(['git','-c','safe.directory='+repository.as_posix(),'-C',str(repository),'show',
            '68c24a899345367f3026372d3c67737751215a0e:src/taut/gen/runtime/'+resource])
        (source/name).write_bytes(data);hashes[name]=hashlib.sha256(data).hexdigest()
    assert b'function requireFoundation(actual: unknown = Foundation): void' in (source/'descriptors.ts').read_bytes()
    (source/'tsconfig.json').write_text(json.dumps({'compilerOptions':{'target':'ES2022','module':'commonjs','strict':True,
        'skipLibCheck':True,'declaration':True,'rewriteRelativeImportExtensions':True,'outDir':'../cjs'},'include':['*.ts']}))
    run([shutil.which('tsc'),'--project',source/'tsconfig.json'])
    (directory/'r0-source-hashes.json').write_text(json.dumps(hashes,indent=2)+'\n')
    return directory/'cjs'


@pytest.mark.parametrize('validation',[False,True])
@pytest.mark.parametrize('split',[False,True])
@pytest.mark.parametrize('missing_token',[False,True])
def test_actual_r0_guard_cannot_ignore_selected_namespace(tmp_path,foundation,original_r0_owner,validation,split,missing_token):
    modern=foundation[0]/'cjs';facade=tmp_path/'old-guard.cjs'
    copied=tmp_path/'second-r0-owner';shutil.copytree(original_r0_owner,copied)
    facade.write_text('const a=require('+json.dumps((original_r0_owner/'foundation.js').as_posix())+');const b=require("./second-r0-owner/foundation.js");module.exports={...a,...a.Foundation'+
        (',CborFloat:b.CborFloat,DecodeError:b.DecodeError,EncodeError:b.EncodeError,encode:b.encode,decode:b.decode,codec:b.codec,schema:b.schema,jsoncodec:b.jsoncodec' if split else '')+'};'+('delete module.exports.Foundation;' if missing_token else '')+'\n')
    # New declarations are fixed at compile time; runtime substitution is the
    # exact old committed r0 implementation, including its void-return guard.
    facade.with_suffix('.d.cts').write_text('export * from '+json.dumps((modern/'foundation.js').as_posix())+';\n')
    # The unchanged r0 checker accepts the facade's compatible-looking labels;
    # the new generated return-identity requirement must still reject it.
    run(['node','-e','const x=require('+json.dumps(facade.as_posix())+');if(x.requireFoundation(x)!==undefined)throw Error("not the original void guard");'])
    emit_direct(schema(Item=Msg(value=F(1,STR))),tmp_path/'generated',validation=validation,mode='package',
                runtime_module=facade.as_posix(),validation_module=(original_r0_owner/'validation.js').as_posix())
    program=compile_program(tmp_path,'import "./generated/api.ts";throw Error("old guard accepted");',execute=False,name='old-guard-application')
    result=run(['node',program],success=False)
    assert ('valid owner token' if missing_token else 'namespace-checked guard support') in result.stderr
    assert 'old guard accepted' not in result.stderr


def owner_path(tmp_path, owner, shape_package):
    if owner=='library':return shape_package[0]/'foundation/cjs'
    emit_direct(schema(Seed=Msg(value=F(1,STR))),tmp_path/'seed',validation=True,source_root=tmp_path/'source-owner')
    compile_program(tmp_path,'export * from "./source-owner/foundation.ts";export * from "./source-owner/validation.ts";',name='owner',execute=False,declaration=True)
    return tmp_path/'built/source-owner'


@pytest.mark.parametrize('owner',['source','library'])
@pytest.mark.parametrize('validation',[False,True])
@pytest.mark.parametrize('swap',['nominal','cbor-functions','codec','schema','jsoncodec','partial-codec','report','descriptor','all-codec'])
def test_selected_facade_checks_actual_exports(tmp_path,shape_package,owner,validation,swap):
    actual=owner_path(tmp_path,owner,shape_package);foreign=tmp_path/'foreign';shutil.copytree(actual,foreign)
    facade=tmp_path/'facade.cjs'
    changes={
        'nominal':'x.CborFloat=b.CborFloat;x.DecodeError=b.DecodeError;x.EncodeError=b.EncodeError;',
        'cbor-functions':'x.encode=b.encode;x.decode=b.decode;',
        'codec':'x.codec=b.codec;', 'schema':'x.schema=b.schema;', 'jsoncodec':'x.jsoncodec=b.jsoncodec;',
        'partial-codec':'x.codec={...a.codec};delete x.codec.encodeRef;',
        'report':'x.ValidationReport=b.ValidationReport;', 'descriptor':'x.MessageDescriptor=b.MessageDescriptor;',
        'all-codec':'Object.assign(x,{CborFloat:b.CborFloat,DecodeError:b.DecodeError,EncodeError:b.EncodeError,encode:b.encode,decode:b.decode,codec:b.codec,schema:b.schema,jsoncodec:b.jsoncodec});',
    }[swap]
    facade.write_text('const a=require('+json.dumps((actual/'foundation.js').as_posix())+');const b=require("./foreign/foundation.js");const x={...a};'+changes+'module.exports=x;\n')
    facade.with_suffix('.d.cts').write_text('export * from '+json.dumps((actual/'foundation.js').as_posix())+';\n')
    emit_direct(schema(Item=Msg(value=F(1,STR))),tmp_path/'generated',validation=validation,mode='package',
                runtime_module=facade.as_posix(),validation_module=(actual/'validation.js').as_posix())
    # The same declaration surface remains strictly compilable. Actual module
    # import must refuse the selected split/partial facade before use is possible.
    program=compile_program(tmp_path,'import "./generated/api.ts";throw Error("accepted split facade");',execute=False,name='application')
    result=run(['node',program],success=False)
    assert 'selected TypeScript foundation' in result.stderr
    assert 'accepted split facade' not in result.stderr


@pytest.mark.parametrize('owner',['source','library'])
@pytest.mark.parametrize('validation',[False,True])
def test_genuine_selected_namespace_wrappers_preserve_identity(tmp_path,shape_package,owner,validation):
    actual=owner_path(tmp_path,owner,shape_package);facade=tmp_path/'facade.cjs'
    facade.write_text('const a=require('+json.dumps((actual/'foundation.js').as_posix())+');module.exports={...a,codec:{...a.codec},schema:{...a.schema},jsoncodec:{...a.jsoncodec},ext:{...a.ext}};\n')
    facade.with_suffix('.d.cts').write_text('export * from '+json.dumps((actual/'foundation.js').as_posix())+';\n')
    emit_direct(schema(Item=Msg(value=F(1,STR))),tmp_path/'generated',validation=validation,mode='package',
                runtime_module=facade.as_posix(),validation_module=(actual/'validation.js').as_posix())
    code='import * as a from "./generated/api.ts";import * as f from '+json.dumps(facade.as_posix())+';f.requireFoundation(f);'+\
        ('const v=new a.Item({value:"ok",__unknown__:new Map([[9,new f.CborFloat(1.5)]])});if(!v.isValid())throw Error();' if validation else 'const v:a.ItemFields={value:"ok",__unknown__:new Map([[9,new f.CborFloat(1.5)]])};')+\
        'if(!(a.ItemDescriptor instanceof f.MessageDescriptor) || f.codec.decode(a.CODEC_SCHEMA,"Item",f.codec.encode(a.CODEC_SCHEMA,"Item",v)).value!=="ok")throw Error();console.log("genuine facade PASS");'
    assert 'genuine facade PASS' in compile_program(tmp_path,code,name='genuine')


@pytest.mark.parametrize('owner',['source','library'])
@pytest.mark.parametrize('slot',['kind','value','ordinary'])
def test_unreadable_bound_fields_are_located_and_independent(tmp_path,shape_package,owner,slot):
    kind=Enum('Kind',yes=0,no=1)
    s=schema(kind,Child=Msg(kind=F(1,OneOf(kind)),value=F(2,STR,Case(kind=kind.yes)),ordinary=F(3,STR),
        other=F(4,OneOf(kind)),extra=F(5,STR,Case(other=kind.yes))),Parent=Msg(child=F(1,Ref.Child)))
    if owner=='source':
        emit_direct(s,tmp_path/'generated',validation=True);module='./generated/foundation.ts';engine='./generated/validation.ts'
    else:
        actual=shape_package[0]/'foundation/cjs';module=(actual/'foundation.js').as_posix();engine=(actual/'validation.js').as_posix()
        emit_direct(s,tmp_path/'generated',validation=True,mode='package',runtime_module=module,validation_module=engine)
    source='import {Child,Parent} from "./generated/api.ts";import * as f from '+json.dumps(module)+';'+\
        'const c=new Child({kind:"yes",value:"ok",ordinary:"ok",other:"yes"});const p=new Parent({child:c});'+\
        f'Object.defineProperty(c,{json.dumps(slot)},{{get(){{throw Error("application getter");}},configurable:true}});'+\
        'const report=p.validate();const rows=report.issues.map(i=>[i.code,i.path.map(s=>s.fieldName).join(".")]);'+\
        f'const expected=[[{json.dumps("oneof.invalid_discriminator" if slot=="kind" else "validation.type_mismatch")},{json.dumps("child."+slot)}],["oneof.payload_missing","child.extra"]];'+\
        'if(JSON.stringify(rows)!==JSON.stringify(expected) || p.isValid() || !p.isValid({recursive:false}) || p.validate({recursive:false}).issues.length!==0)throw Error(JSON.stringify(rows));'+\
        f'const local=c.validate({{recursive:false}});if(local.issues.length!=={1 if slot=="ordinary" else 2} || c.isValid({{recursive:false}}))throw Error("local scope");'+\
        f'const config=new f.ConfigurationError("binding configuration");Object.defineProperty(c,{json.dumps(slot)},{{get(){{throw config;}},configurable:true}});'+\
        'for(const call of [()=>p.validate(),()=>p.isValid()]){let seen=false;try{call();}catch(e){if(e!==config)throw e;seen=true;}if(!seen)throw Error("swallowed configuration failure");}'+\
        'console.log("getter boundary PASS");'
    assert 'getter boundary PASS' in compile_program(tmp_path,source,name='getter')
    # Instrument only report constructors after schema publication: fast mode
    # must retain its shared predicate route without constructing reports/issues.
    actual_reports=(tmp_path/'built/generated/reports.js') if owner=='source' else shape_package[0]/'foundation/cjs/reports.js'
    fast=tmp_path/'fast.cjs'
    fast.write_text('const a=require('+json.dumps(str(tmp_path/'built/generated/api.js'))+');const reports=require('+json.dumps(str(actual_reports))+');const saved={};try{for(const k of ["ValidationReport","ValidationIssue","DeferredCheck"]){saved[k]=reports[k];reports[k]=new Proxy(reports[k],{construct(){throw Error("fast allocated report");}});}const c=new a.Child({kind:"yes",value:"ok",ordinary:"ok",other:"yes"});Object.defineProperty(c,'+json.dumps(slot)+',{get(){throw Error("input");}});if(new a.Parent({child:c}).isValid())throw Error("fast accepted");}finally{Object.assign(reports,saved);}console.log("fast PASS");')
    assert 'fast PASS' in run(['node',fast]).stdout


@pytest.mark.parametrize('owner',['source','library'])
@pytest.mark.parametrize('fault',['duplicate','missing','unknown','extra-parameter','missing-parameter','number','boolean','array','coercible','future-rule','top-shape','symbol'])
def test_constraint_publication_rejects_malformed_normalized_facts(tmp_path,shape_package,owner,fault):
    if owner=='source':
        emit_direct(schema(Seed=Msg(value=F(1,STR))),tmp_path/'generated');module='./generated/foundation.ts'
    else:module=(shape_package[0]/'foundation/cjs/foundation.js').as_posix()
    first={
        'duplicate':'{rule:f.ONEOF_RULE,parameters:{controlling_field:"right"}}',
        'missing':'null',
        'unknown':'{rule:f.ONEOF_RULE,parameters:{controlling_field:"missing"}}',
        'extra-parameter':'{rule:f.ONEOF_RULE,parameters:{controlling_field:"left",unsupported:true}}',
        'missing-parameter':'{rule:f.ONEOF_RULE,parameters:{}}',
        'number':'{rule:f.ONEOF_RULE,parameters:{controlling_field:1}}',
        'boolean':'{rule:f.ONEOF_RULE,parameters:{controlling_field:true}}',
        'array':'{rule:f.ONEOF_RULE,parameters:{controlling_field:["left"]}}',
        'coercible':'{rule:f.ONEOF_RULE,parameters:{controlling_field:{toString:()=>"left"}}}',
        'future-rule':'{rule:"future.unsupported",parameters:{controlling_field:"left"}}',
        'top-shape':'{rule:f.ONEOF_RULE,parameters:{controlling_field:"left"},extra:true}',
        'symbol':'{rule:f.ONEOF_RULE,parameters:{controlling_field:"left",[Symbol("unsupported")]:true}}',
    }[fault]
    source='import * as f from '+json.dumps(module)+';'+CONSTRAINT_SETUP+\
        'let rejected=false;try{const first='+first+';const constraints=first===null?[new f.ConstraintDescriptor(f.ONEOF_RULE,{controlling_field:"right"})]:[first as f.ConstraintDescriptor,new f.ConstraintDescriptor(f.ONEOF_RULE,{controlling_field:"right"})];const d=descriptor(constraints);publish(d);}catch(e){if(!(e instanceof f.ConfigurationError))throw e;rejected=true;}if(!rejected)throw Error("accepted malformed constraint");console.log("grammar PASS");'
    assert 'grammar PASS' in compile_program(tmp_path,source,name='grammar')


CONSTRAINT_SETUP=r'''
const opts={max_depth:32,max_encoded_len:null};
const e=new f.EnumDescriptor("E","E",{a:0n,b:1n});
function descriptor(constraints:readonly f.ConstraintDescriptor[],virtual=false) {
 const fields=[new f.FieldDescriptor("left","left",1,{kind:"enum",enum:()=>e},"required"),new f.FieldDescriptor("right",virtual?null:"right",2,{kind:"enum",enum:()=>e},"required",false,virtual)];
 const groups=[new f.OneOfDescriptor("left",e,false,false,{a:null,b:null}),new f.OneOfDescriptor("right",e,virtual,false,{a:null,b:null})];
 return new f.MessageDescriptor("X","X",1,fields,groups,constraints,[],[],null,{},opts);
}
function publish(d:f.MessageDescriptor) {
 const b=new f.MessageBinding<{left:string;right:string}>(d,(v,i)=>i===0?v.left:v.right,(v:unknown):v is {left:string;right:string}=>typeof v==="object"&&v!==null);
 f.publish(new f.SchemaDescriptor("schema",3,{X:d},{E:e},{},opts),[b]);return b;
}
'''


@pytest.mark.parametrize('owner',['source','library'])
@pytest.mark.parametrize('virtual',[False,True])
def test_strict_mutable_constraints_become_owned_canonical_snapshots(tmp_path,shape_package,owner,virtual):
    if owner=='source':
        emit_direct(schema(Seed=Msg(value=F(1,STR))),tmp_path/'generated',validation=True)
        module='./generated/foundation.ts';engine='./generated/validation.ts'
    else:
        actual=shape_package[0]/'foundation/cjs';module=(actual/'foundation.js').as_posix();engine=(actual/'validation.js').as_posix()
    source='import * as f from '+json.dumps(module)+';import * as engine from '+json.dumps(engine)+';'+CONSTRAINT_SETUP+\
        'const supplied={rule:f.ONEOF_RULE,parameters:{controlling_field:"left"}};const right={rule:f.ONEOF_RULE,parameters:{controlling_field:"right"}};'+\
        f'const d=descriptor([supplied,right],{str(virtual).lower()});const b=publish(d);'+\
        'supplied.rule="future.unsupported.rule";supplied.parameters.controlling_field="missing";right.parameters.controlling_field="left";'+\
        'if(d.constraints[0]===supplied || !(d.constraints[0] instanceof f.ConstraintDescriptor) || !Object.isFrozen(d.constraints[0]) || !Object.isFrozen(d.constraints[0].parameters) || d.constraints[0].rule!==f.ONEOF_RULE || d.constraints[0].parameters.controlling_field!=="left" || d.constraints[1].parameters.controlling_field!=="right")throw Error("mutable published facts");'+\
        f'const r=engine.validateRecord({{left:"a",right:"a"}},b);if(!r.isValid() || r.isComplete()==={str(virtual).lower()} || engine.isRecordValid({{left:"a",right:"a"}},b)==={str(virtual).lower()})throw Error("valid independent/virtual groups");'+\
        'console.log("immutable canonical constraints PASS");'
    assert 'immutable canonical constraints PASS' in compile_program(tmp_path,source,name='mutable-strict')


def test_actual_typescript_package_help_states_payload_default_and_fresh_output():
    help=' '.join(run([sys.executable,'-m','taut.gen.typescript_package','--help']).stdout.split())
    for phrase in ('OUTPUT','fresh output directory','--without-validation','descriptor/codec-only artifact','validation is included by default'):
        assert phrase in help
