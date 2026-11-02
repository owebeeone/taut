from pathlib import Path
import hashlib,json,shutil,subprocess
from taut.gen.scaffold import emit
from taut.ir.dsl import F,Msg,INT,Ref,schema
HERE=Path(__file__).resolve().parent
ROOT=HERE/'cpp-original-counterexample'
original=HERE.parent/'review-r0/code/scratch/first-member-exact/main.cpp'
emit(schema(Child=Msg(n=F(1,INT)),Parent=Msg(child=F(1,Ref('Child')))),ROOT,langs=['cpp'],services=[],runtime=True,validation=True)
probe=ROOT/'main.cpp';shutil.copyfile(original,probe)
exe=ROOT/'probe.exe'
command=[shutil.which('clang++'),'-std=c++20','-fno-rtti','-I',str(ROOT/'cpp'),str(probe),str(ROOT/'cpp/foundation.cpp'),'-o',str(exe)]
compiled=subprocess.run(command,capture_output=True,text=True)
assert compiled.returncode==0,compiled.stdout+compiled.stderr
result=subprocess.run([str(exe)],capture_output=True,text=True)
assert result.returncode==0,result.stderr
assert result.stdout.strip()=='same_address=1 valid=1 complete=1 fast=1 issues=0',result.stdout
(HERE/'cpp-original-counterexample.json').write_text(json.dumps({'original_probe':str(original),'copied_probe_sha256':hashlib.sha256(probe.read_bytes()).hexdigest(),'unchanged_probe':probe.read_bytes()==original.read_bytes(),'command':command,'stdout':result.stdout,'runtime_sha256':hashlib.sha256((ROOT/'cpp/taut/validation.hpp').read_bytes()).hexdigest()},indent=2)+'\n')
print(result.stdout,end='')
