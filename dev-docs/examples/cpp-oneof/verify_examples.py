"""Generate, compile and execute C++ source/package/supplied examples; no installs."""
from pathlib import Path
import argparse
import shutil
import subprocess
import sys
import tempfile
import zipfile

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
sys.path.insert(0,str(ROOT/'src'))
from taut.gen.scaffold import emit
from taut.gen.cpp_runtime import build_foundation,verify_artifact,canonical_sources
from taut.ir.load import load_schema

def checked(args):
    result=subprocess.run(list(map(str,args)),capture_output=True,encoding='utf-8')
    if result.returncode:raise RuntimeError(result.stdout+result.stderr)
    return result.stdout

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,help='fresh output directory (default: a new directory in Limbo/cpp-go-oneof-scratch)')
    args=parser.parse_args()
    scratch=ROOT.parents[1]/'cpp-go-oneof-scratch';scratch.mkdir(exist_ok=True)
    if args.out:
        if args.out.exists():raise ValueError('Choose a fresh --out directory')
        root=args.out.resolve();root.mkdir(parents=True)
    else:root=Path(tempfile.mkdtemp(prefix='cpp-examples-',dir=scratch))
    compiler=shutil.which('clang++') or shutil.which('c++')
    if not compiler:raise RuntimeError('Activate the existing Taut C++ toolchain')
    package=build_foundation(root/'built-foundation')
    with zipfile.ZipFile(root/'foundation.zip','w') as archive:
        for path in package.rglob('*'):
            if path.is_file():archive.write(path,path.relative_to(package).as_posix())
    extracted=root/'extracted-foundation'
    with zipfile.ZipFile(root/'foundation.zip') as archive:archive.extractall(extracted)
    verify_artifact(extracted,validation=True)
    schema=load_schema(HERE/'content.taut.py')
    reports=[]
    for mode in ('source','package',None):
        name=mode or 'supplied';output=root/name
        emit(schema,output,langs=['cpp'],services=[],runtime_mode=mode,validation=True,
             runtime_bindings={'cpp':{'artifact':str(extracted)}} if mode!='source' else None)
        directory=output/'cpp'
        include=directory if mode=='source' else extracted/'include'
        owner=directory/'foundation.cpp' if mode=='source' else extracted/'taut-foundation.lib'
        if mode=='source':
            for filename,data in canonical_sources().items():assert (directory/filename).read_bytes()==data
        for filename in ('Example.cpp','Conformance.cpp','AllocationFault.cpp'):
            executable=output/(Path(filename).stem+'.exe')
            checked([compiler,'-std=c++20','-fno-rtti','-I',directory,'-I',include,HERE/filename,owner,'-o',executable])
            result=checked([executable])
            if filename=='Conformance.cpp':reports.append(result)
            if filename=='Example.cpp':print(name+': '+result.strip())
    assert len(set(reports))==1
    (root/'normalized-reports.txt').write_text(reports[0],encoding='utf-8')
    print('PASS: source, extracted compiled package, supplied runtime and allocation-fault fallback; '+str(root))

if __name__=='__main__':main()
