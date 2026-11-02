"""Actual compiler-wheel closure and isolated native C++/Go source/package builds."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile
import pytest
from taut.gen.scaffold import emit
from taut.ir.dsl import INT,F,Msg,schema
from taut.gen.cpp_runtime import FILES as CPP_FILES
from taut.gen.go_runtime import FILES as GO_FILES

ROOT=Path(__file__).resolve().parents[2]

def test_pair_plans_all_targets_before_mutation(tmp_path):
    go=tmp_path/'go';go.mkdir();(go/'api.go').write_text('// handwritten Go')
    before={p.relative_to(tmp_path).as_posix():p.read_bytes() for p in tmp_path.rglob('*') if p.is_file()}
    with pytest.raises(ValueError):emit(schema(Record=Msg(value=F(1,INT))),tmp_path,langs=['cpp','go'],services=[],runtime=True,validation=True)
    assert {p.relative_to(tmp_path).as_posix():p.read_bytes() for p in tmp_path.rglob('*') if p.is_file()}==before

@pytest.mark.skipif(os.name!='nt',reason='Windows previous-owner junction contract')
@pytest.mark.parametrize('target',['python','rust','java','kotlin','js','typescript','cpp','go','swift'])
def test_previous_owner_alias_rejected_before_lock_mutation(tmp_path,monkeypatch,target):
    record=schema(Record=Msg(value=F(1,INT)))
    actual=tmp_path/'owner';output=tmp_path/'schema'
    config={'source_root':str(actual)}
    if target=='rust':config['module']='taut_foundation'
    if target=='go':config['import_path']='example.local/foundation'
    emit(record,output,langs=[target],services=[],runtime=True,runtime_bindings={target:config})
    alias=tmp_path/'alias'
    checked(['cmd','/c','mklink','/J',alias,actual])
    manifest=output/target/('.taut-'+target+'-outputs.json');data=json.loads(manifest.read_text());data['source_root']=str(alias);manifest.write_text(json.dumps(data))
    before={p.relative_to(tmp_path).as_posix():p.read_bytes() for p in tmp_path.rglob('*') if p.is_file()}
    attempted=[];original=Path.open
    def observe(path,*args,**kwargs):
        if args and args[0]=='xb' and path.name=='.taut-generation.lock':attempted.append(path)
        return original(path,*args,**kwargs)
    monkeypatch.setattr(Path,'open',observe)
    with pytest.raises(ValueError,match='previous runtime owner'):
        emit(record,output,langs=[target],services=[],runtime_mode='package',runtime_bindings={'go':{'import_path':'example.local/package'}} if target=='go' else {'swift':{'module':'TautFoundation'}} if target=='swift' else None)
    assert attempted==[]
    assert {p.relative_to(tmp_path).as_posix():p.read_bytes() for p in tmp_path.rglob('*') if p.is_file()}==before

def checked(args,**kwargs):
    result=subprocess.run(list(map(str,args)),capture_output=True,encoding='utf-8',**kwargs)
    assert result.returncode==0,result.stdout+result.stderr
    return result.stdout

def test_compiler_wheel_isolated_native_source_package(tmp_path):
    import build
    source=tmp_path/'compiler'
    shutil.copytree(ROOT/'src/taut',source/'src/taut',ignore=shutil.ignore_patterns('__pycache__'))
    for name in ('pyproject.toml','README.md','LICENSE'):shutil.copyfile(ROOT/name,source/name)
    env=dict(os.environ,SETUPTOOLS_SCM_PRETEND_VERSION_FOR_TAUT_PROTO='0.10.0+local.cpp.go.probe',
             PYTHONPATH=str(Path(build.__file__).resolve().parent.parent))
    checked([sys.executable,'-m','build','--wheel','--no-isolation','--outdir',tmp_path/'dist'],cwd=source,env=env)
    wheel=next((tmp_path/'dist').glob('*.whl'));unpacked=tmp_path/'unpacked'
    with zipfile.ZipFile(wheel) as archive:
        for resource in set(CPP_FILES.values())|set(GO_FILES.values()):
            assert archive.read('taut/gen/runtime/'+resource)==(ROOT/'src/taut/gen/runtime'/resource).read_bytes()
        archive.extractall(unpacked)
    generated=tmp_path/'generated'
    checked([sys.executable,'-I','-S','-c','''import sys
from pathlib import Path
sys.path.insert(0,sys.argv[1])
assert Path(__import__('taut').__file__).is_relative_to(Path(sys.argv[1]))
from taut.gen.scaffold import emit
from taut.ir.dsl import Enum,F,Msg,STR,OneOf,Case,schema
from taut.gen.cpp_runtime import build_foundation as cpp_package
from taut.gen.go_runtime import build_foundation as go_package
root=Path(sys.argv[2])
e=Enum('Choice',yes=0,no=1)
s=schema(e,Record=Msg(tag=F(1,OneOf(e)),data=F(2,STR,Case(tag=e.yes))))
emit(s,root/'source',langs=['cpp','go'],services=[],runtime_mode='source',validation=True)
cp=cpp_package(root/'cpp-foundation')
gp=go_package(root/'go-foundation','foundation.local/wheel')
emit(s,root/'package',langs=['cpp','go'],services=[],runtime_mode='package',validation=True,
 runtime_bindings={'cpp':{'artifact':str(cp)},'go':{'import_path':'foundation.local/wheel','artifact':str(gp)}})
''',unpacked,generated])
    for mode in ('source','package'):
        d=generated/mode/'cpp'
        native=d/'probe.cpp';native.write_text('#include "api.hpp"\n#include <cassert>\nint main(){taut::Record r{};r.tag=taut::Choice::Yes;assert(!r.is_valid());r.data="";assert(r.is_valid());}\n')
        include=d if mode=='source' else generated/'cpp-foundation/include'
        owner=d/'foundation.cpp' if mode=='source' else generated/'cpp-foundation/taut-foundation.lib'
        exe=d/('probe.exe' if os.name=='nt' else 'probe')
        checked([shutil.which('clang++') or shutil.which('c++'),'-std=c++20','-fno-rtti','-I',include,native,owner,'-o',exe]);checked([exe])
        app_root=generated/mode
        (app_root/'go.mod').write_text('module example.local/wheel\n\ngo 1.20\n'+('require foundation.local/wheel v0.0.0\nreplace foundation.local/wheel => '+json.dumps((generated/'go-foundation').as_posix())+'\n' if mode=='package' else ''))
        app=app_root/'app';app.mkdir()
        (app/'main.go').write_text('package main\nimport a "example.local/wheel/go"\nfunc main(){r:=a.Record{Tag:a.ChoiceYes};if r.IsValid(){panic("missing")};s:="";r.Data=&s;if !r.IsValid(){panic("repair")}}\n')
        go_env=dict(os.environ,GO111MODULE='on',GOWORK='off',GOPROXY='off',GOSUMDB='off',GOTOOLCHAIN='local')
        checked(['go','run','./app'],cwd=app_root,env=go_env)
