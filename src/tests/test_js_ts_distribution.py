"""Shared JS/TS CLI, service bindings and real compiler-wheel distribution checks."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile
import pytest
from taut import cli
from taut.gen.scaffold import emit, emit_all
from taut.gen.js_runtime import FILES as JS_FILES
from taut.gen.typescript_runtime import FILES as TS_FILES
from taut.gen.typescript_package import build_foundation
from taut.ir.dsl import INT, STR, F, Msg, Ref, List, Map, Params, method, service, schema

ROOT=Path(__file__).resolve().parents[2]
RUNTIME=ROOT/'src/taut/gen/runtime'


def run(args,**kwargs):
    r=subprocess.run(list(map(str,args)),capture_output=True,encoding='utf-8',**kwargs)
    assert r.returncode==0,r.stdout+r.stderr
    return r.stdout


def service_schema():
    return schema(Msg('Item',F('n',1,INT)), service('Svc',
        method('get',role='out',params=Params(id=INT),out=Ref('Item')),
        method('watch',role='out',shape='log',params=Params(id=INT),out=Ref('Item'))))


@pytest.mark.parametrize('lang',['js','typescript'])
@pytest.mark.parametrize('mode',['source','package',None])
def test_cli_modes_and_keyword_forwarding(tmp_path,lang,mode):
    from taut.ir.export import schema_json
    s=service_schema();ir=tmp_path/'service.ir.json';ir.write_text(json.dumps(schema_json(s)))
    args=['gen',str(ir),'--out',str(tmp_path/'cli'),'--lang',lang,'--api-only','--with-validation']
    if mode:args+=['--runtime',mode,'--runtime',mode]
    assert cli.main(args)==0
    emit_all(s,'Svc',tmp_path/'program',langs=[lang],runtime_mode=mode,validation=True)
    ext='js' if lang=='js' else 'ts'
    assert 'validate(' in (tmp_path/'program'/lang/f'api.{ext}').read_text()
    assert (tmp_path/'program'/lang/f'client.{ext}').exists()


@pytest.mark.parametrize('flags',[['--runtime','package','--with-runtime'],['--runtime','package','--runtime','source']])
def test_cli_conflicts_preserve_outputs(tmp_path,flags):
    before=list(tmp_path.iterdir())
    with pytest.raises(ValueError,match='conflicting'):
        cli.main(['gen','missing.ir.json','--out',str(tmp_path/'output'),'--lang','js,typescript',*flags])
    assert list(tmp_path.iterdir())==before


def test_shared_help_preserves_jvm_and_ecma_methods_defaults_and_artifact_formats():
    text=' '.join(run([sys.executable,'-m','taut.cli','gen','--help']).split())
    for phrase in ('Python/Rust/Java/Kotlin/JavaScript/TypeScript',
                   'JS/TS/JVM methods: validate/isValid', 'Python/Rust: validate/is_valid',
                   'default: off', 'descriptors always emitted',
                   '--js-external-types JSON_FILE', '--typescript-external-types JSON_FILE',
                   'data_export defaults to ExportFields', 'enums to Export',
                   'Java accepts optional artifact jar', 'JS/TS accept optional artifact tgz',
                   'TS also validation_module', 'Python/Java module=taut', 'Kotlin packages fixed',
                   'Rust module defaults', 'source_root defaults', 'never installs it'):
        assert phrase in text,phrase


@pytest.fixture(scope='module')
def ts_package(tmp_path_factory):
    root=tmp_path_factory.mktemp('shared-ts-package');build_foundation(root)
    return root/'package'


@pytest.mark.parametrize('mode,shared_source',[('source',False),('source',True),('package',False),(None,False)])
def test_typescript_services_strict_compile_and_run_in_bound_modes(tmp_path,ts_package,mode,shared_source):
    s=service_schema();output=tmp_path/'generated';directory=output/'typescript'
    config={}
    if mode=='source' and shared_source:config={'source_root':str(tmp_path/'owner')}
    if mode!='source':
        config={'module':str(ts_package/'cjs/foundation.js').replace('\\','/'),
                'validation_module':str(ts_package/'cjs/validation.js').replace('\\','/')}
    emit(s,output,langs=['typescript'],runtime_mode=mode,validation=True,
         runtime_bindings={'typescript':config})
    assert (directory/'taut_client.ts').exists() is (mode=='source')
    if mode=='source':
        root=tmp_path/'owner' if shared_source else directory
        text=(directory/'taut_client.ts').read_text()
        relative=os.path.relpath(root/'codec.ts',directory).replace('\\','/')
        if not relative.startswith('.'):relative='./'+relative
        assert json.dumps(relative) in text
    # Optional canonical socket client retains Buffer from Node; no new type install.
    ambient=tmp_path/'node.d.ts';ambient.write_text('declare const Buffer: {from(value: Uint8Array | string, encoding?: string): Uint8Array & {toString(encoding: string): string}};')
    harness=tmp_path/'main.ts';harness.write_text('''import { SvcClient } from "./generated/typescript/client.ts";
import { register } from "./generated/typescript/server.ts";
const calls: unknown[]=[];
const transport={call:async (method:string,args?:Record<string,unknown>)=>{calls.push([method,args]);return {n:7n};},subscribe:(_m:string,_a:Record<string,unknown>,on:(e:string,v:unknown)=>void)=>{on("append",{n:9n});return ()=>{};}};
const client=new SvcClient(transport);
client.get(3n).then(value=>{if(value.n!==7n||calls.length!==1)throw Error("typed client");});
client.watch(1n,(event,value)=>{if(event!=="append"||(value as {n:bigint}).n!==9n)throw Error("stream");});
let registered=0;register({registerMethod:()=>registered++},{services:{Svc:{methods:[{name:"get"},{name:"watch"}]}}},{get:async (_id:bigint)=>({n:0n}),watch:()=>null});
if(registered!==2)throw Error("register");
''')
    sources=[harness,ambient]
    if mode=='source':sources.append(directory/'taut_client.ts')
    run([shutil.which('tsc'),'--target','ES2022','--module','commonjs','--strict','--skipLibCheck','--rewriteRelativeImportExtensions','--rootDir',tmp_path,'--outDir',tmp_path/'built',*sources])
    run(['node',tmp_path/'built/main.js'])


@pytest.mark.parametrize('validation',[False,True])
@pytest.mark.parametrize('external_child',[False,True])
def test_nested_service_data_types_and_plain_decoded_values(tmp_path,validation,external_child):
    child=schema(Msg('Child',F('n',1,INT)))
    s=schema(Msg('Child',F('n',1,INT)),
             Msg('Payload',F('child',1,Ref('Child')),F('children',2,List(Ref('Child'))),F('by_name',3,Map(STR,Ref('Child')))),
             service('DataSvc',method('echo',role='out',params=Params(value=Ref('Payload')),out=Ref('Payload'))))
    owner=tmp_path/'owner';binding={'typescript':{'source_root':str(owner)}}
    mappings=None
    if external_child:
        emit(child,tmp_path/'child',langs=['typescript'],services=[],runtime=True,validation=True,runtime_bindings=binding)
        mappings={'Child':{'module':'../../child/typescript/api.ts','export':'Child'}}
    emit(s,tmp_path/'generated',langs=['typescript'],runtime=True,validation=validation,runtime_bindings=binding,typescript_external_types=mappings)
    directory=tmp_path/'generated/typescript'
    api_text=(directory/'api.ts').read_text()
    if external_child:assert 'import type { ChildFields as Child }' in api_text
    client_text=(directory/'client.ts').read_text()
    projected='PayloadFields' if validation else 'Payload'
    assert 'Promise<api.'+projected+'>' in client_text
    assert 'value: api.'+projected in client_text
    assert 'Promise<api.'+projected+'>' in (directory/'server.ts').read_text()
    main=tmp_path/'main.ts'
    extra='client.echo(new api.Payload(data));' if validation else ''
    main.write_text('''import * as api from "./generated/typescript/api.ts";
import * as f from "./owner/foundation.ts";
import {DataSvcClient} from "./generated/typescript/client.ts";
import {register} from "./generated/typescript/server.ts";
const data={child:{n:1n},children:[{n:2n}],by_name:new Map([["a",{n:3n}]])};
const wire=f.codec.encode(api.CODEC_SCHEMA,"Payload",data);
const transport={call:async (_name:string,_args?:Record<string,unknown>)=>f.codec.decode(api.CODEC_SCHEMA,"Payload",wire),subscribe:(_name:string,_args:Record<string,unknown>,_callback:(e:string,v:unknown)=>void)=>()=>{}};
const client=new DataSvcClient(transport);
client.echo(data).then(value=>{
 if(value.child.n!==1n||value.children[0].n!==2n||value.by_name.get("a")?.n!==3n)throw Error("nested data");
 for(const v of [value,value.child,value.children[0],value.by_name.get("a")!]) {
  if(Object.getPrototypeOf(v)!==Object.prototype||"validate" in v||"isValid" in v)throw Error("decoded data falsely constructed");
 }
});
let registered=0;
register({registerMethod:()=>registered++},{services:{DataSvc:{methods:[{name:"echo"}]}}},{echo:async value=>value});
if(registered!==1)throw Error("server registration");
'''+extra)
    tsc=[shutil.which('tsc'),'--target','ES2022','--module','commonjs','--strict','--skipLibCheck','--rewriteRelativeImportExtensions','--rootDir',tmp_path]
    run([*tsc,'--outDir',tmp_path/'built',main])
    run(['node',tmp_path/'built/main.js'])
    negative=tmp_path/'negative.ts'
    negative.write_text('''import {DataSvcClient} from "./generated/typescript/client.ts";
declare const client: DataSvcClient;
client.echo({child:{n:1n},children:[],by_name:new Map()}).then(value=>{
 value.validate();
 value.child.validate();
 value.children[0].isValid();
 value.by_name.get("a")!.validate();
});
''')
    failed=subprocess.run(list(map(str,[*tsc,'--noEmit',negative])),capture_output=True,encoding='utf-8')
    assert failed.returncode!=0
    assert (failed.stdout+failed.stderr).count('does not exist on type')>=4,failed.stdout+failed.stderr


def test_external_service_child_without_exported_data_shape_fails_typecheck(tmp_path):
    child=schema(Msg('Child',F('n',1,INT)))
    s=schema(Msg('Child',F('n',1,INT)),service('Svc',method('get',role='out',out=Ref('Child'))))
    binding={'typescript':{'source_root':str(tmp_path/'owner')}}
    emit(child,tmp_path/'child',langs=['typescript'],services=[],runtime=True,validation=True,runtime_bindings=binding)
    (tmp_path/'legacy-facade.ts').write_text('export {Child,ChildDescriptor,ChildBinding} from "./child/typescript/api.ts";')
    emit(s,tmp_path/'parent',langs=['typescript'],runtime=True,validation=True,runtime_bindings=binding,
         typescript_external_types={'Child':{'module':'../../legacy-facade.ts'}})
    r=subprocess.run(list(map(str,[shutil.which('tsc'),'--target','ES2022','--module','commonjs','--strict','--skipLibCheck','--rewriteRelativeImportExtensions','--noEmit',tmp_path/'parent/typescript/client.ts'])),capture_output=True,encoding='utf-8')
    assert r.returncode!=0 and 'ChildFields' in r.stdout+r.stderr and 'export' in r.stdout+r.stderr


def test_compiler_wheel_contains_js_ts_closures_and_generates_running_sources(tmp_path):
    import build
    source=tmp_path/'compiler'
    shutil.copytree(ROOT/'src/taut',source/'src/taut',ignore=shutil.ignore_patterns('__pycache__'))
    for name in ('pyproject.toml','README.md','LICENSE'):shutil.copyfile(ROOT/name,source/name)
    env=dict(os.environ,SETUPTOOLS_SCM_PRETEND_VERSION_FOR_TAUT_PROTO='0.10.0+local.js.ts.probe',
             PYTHONPATH=str(Path(build.__file__).resolve().parent.parent))
    run([sys.executable,'-m','build','--wheel','--no-isolation','--outdir',tmp_path/'dist'],cwd=source,env=env)
    wheel=next((tmp_path/'dist').glob('*.whl'));unpacked=tmp_path/'unpacked'
    with zipfile.ZipFile(wheel) as archive:
        for resource in set(JS_FILES.values())|set(TS_FILES.values())|{'typescript/taut_client.ts'}:
            assert archive.read('taut/gen/runtime/'+resource)==(RUNTIME/resource).read_bytes(),resource
        archive.extractall(unpacked)
    generated=tmp_path/'generated'
    run([sys.executable,'-I','-S','-c','''import sys
from pathlib import Path
sys.path.insert(0,sys.argv[1])
from taut.gen.scaffold import emit
from taut.ir.dsl import *
assert Path(__import__('taut').__file__).is_relative_to(Path(sys.argv[1]))
e=Enum('Choice',yes=0,no=1)
s=schema(e,Record=Msg(tag=F(1,OneOf(e)),data=F(2,STR,Case(tag=e.yes))))
emit(s,Path(sys.argv[2]),langs=['js','typescript'],services=[],runtime=True,validation=True)
''',unpacked,generated])
    run(['node','-e','const a=require('+json.dumps(str(generated/'js/api.js'))+');const v=new a.Record({tag:a.Choice.yes});if(v.isValid())throw Error("missing");v.data="";if(!v.isValid())throw Error("repair");'])
    main=generated/'typescript/main.ts';main.write_text('import {Record} from "./api.ts";const v=new Record({tag:"yes"});if(v.isValid())throw Error("missing");v.data="";if(!v.isValid())throw Error("repair");')
    run([shutil.which('tsc'),'--target','ES2022','--module','commonjs','--strict','--skipLibCheck','--rewriteRelativeImportExtensions','--outDir',tmp_path/'built',main])
    run(['node',tmp_path/'built/main.js'])


@pytest.mark.skipif(os.name!='nt',reason='Windows namespace spelling')
@pytest.mark.parametrize('target',['js','typescript','rust','java','kotlin'])
@pytest.mark.parametrize('suffix',['x:y','x:stream'])
def test_shared_namespace_guard_retains_ads_component_before_path_conversion(tmp_path,target,suffix):
    import importlib
    helper=importlib.import_module('taut.gen.'+target+'_runtime')
    spelling='\\\\?\\'+str(tmp_path)+'\\'+suffix
    with pytest.raises(ValueError,match='namespace path component'):
        helper.canonical_path(spelling)
    from taut.gen.python_runtime import _physical_path,validate_namespace_path
    with pytest.raises(ValueError,match='namespace path component'):validate_namespace_path(spelling)
    with pytest.raises(ValueError,match='namespace path component'):_physical_path(spelling)
