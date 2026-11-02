"""Generate, compile and run real source/local-module/supplied Go consumers."""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import subprocess
import tempfile
import zipfile
from taut.gen.scaffold import emit
from taut.gen.go_runtime import build_foundation, canonical_sources, _go_env
from taut.ir.load import load_schema

HERE=Path(__file__).resolve().parent
LIMBO=HERE.parents[4]


def run(out):
    out=Path(out).absolute()
    if out.exists() and any(out.iterdir()): raise ValueError('Use a fresh example output directory: '+str(out))
    out.mkdir(parents=True,exist_ok=True)
    built=build_foundation(out/'foundation-built','example.local/foundation')
    archive=out/'foundation.zip'
    with zipfile.ZipFile(archive,'w') as z:
        for p in built.iterdir(): z.write(p,p.name)
    owner=out/'foundation-extracted'
    with zipfile.ZipFile(archive) as z: z.extractall(owner)
    for name,data in canonical_sources().items(): assert (owner/name).read_bytes()==data
    schema=load_schema(HERE/'content.taut.py')
    results={}
    for mode in ('source','package',None):
        for validation in (False,True):
            label=(mode or 'supplied')+('-on' if validation else '-off')
            root=out/label
            bindings=None if mode=='source' else {'go':{'import_path':'example.local/foundation','artifact':str(owner)}}
            emit(schema,root,langs=['go'],services=[],runtime_mode=mode,validation=validation,runtime_bindings=bindings)
            extra='' if mode=='source' else 'require example.local/foundation v0.0.0\nreplace example.local/foundation => '+json.dumps(owner.as_posix())+'\n'
            (root/'go.mod').write_text('module example.local/application\n\ngo 1.18\n'+extra)
            (root/'app').mkdir()
            if validation:
                code=(HERE/'conformance.go').read_text().replace('@API@','example.local/application/go')
                if mode=='source': code=code.replace('\n\tr "@RUNTIME@"','').replace('r.','a.')
                else: code=code.replace('@RUNTIME@','example.local/foundation')
            else:
                code='package main\nimport ("fmt"; a "example.local/application/go")\nfunc main(){ var value *a.Content; if value.Descriptor()!=a.DescribeContent(){panic("descriptor identity")}; fmt.Printf("descriptor-only fields=%d IR=%d\\n",len(value.Descriptor().Fields()),a.DescribeSchema().IRVersion()) }\n'
            (root/'app/main.go').write_text(code)
            executable=root/('example.exe' if os.name=='nt' else 'example')
            built_app=subprocess.run(['go','build','-o',str(executable),'./app'],cwd=root,env=_go_env(),capture_output=True,text=True)
            if built_app.returncode: raise RuntimeError(label+' build:\n'+built_app.stderr)
            # Application execution needs only the native executable and OS.
            env=dict(os.environ,PATH=os.path.join(os.environ.get('SystemRoot','C:/Windows'),'System32') if os.name=='nt' else '/usr/bin:/bin')
            env.pop('PYTHONPATH',None);env.pop('GOROOT',None);env.pop('GOPATH',None)
            result=subprocess.run([str(executable)],cwd=root,env=env,capture_output=True,text=True,check=True)
            results[label]=result.stdout.splitlines()
            if mode=='source':
                for name,data in canonical_sources(validation=validation).items(): assert (root/'go'/name).read_bytes()==data
    for suffix in ('on','off'):
        assert results['source-'+suffix]==results['package-'+suffix]==results['supplied-'+suffix]
    (out/'results.json').write_text(json.dumps(results,indent=2)+'\n')
    print(json.dumps({'output':str(out),'native_executions':len(results),'status':'PASS'},indent=2))
    return results


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path)
    args=parser.parse_args()
    (LIMBO/'go-oneof-scratch').mkdir(exist_ok=True)
    root=args.out or Path(tempfile.mkdtemp(prefix='go-oneof-example-',dir=LIMBO/'go-oneof-scratch'))
    run(root)
