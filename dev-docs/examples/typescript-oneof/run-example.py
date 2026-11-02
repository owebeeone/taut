"""Generate, strictly typecheck, transpile and execute source/package examples."""
from pathlib import Path
import argparse
import json
import shutil
import subprocess
import tarfile
from taut.gen.scaffold import emit
from taut.gen.typescript_package import build_foundation
from taut.ir.load import load_schema

HERE=Path(__file__).resolve().parent
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--out',required=True,type=Path)
args=parser.parse_args();out=args.out.absolute()
if out.exists() and any(out.iterdir()):raise SystemExit('use a fresh output directory')
out.mkdir(parents=True,exist_ok=True)
artifact=build_foundation(out/'local-package')
with tarfile.open(artifact,'r:gz') as archive:archive.extractall(out/'extracted',filter='data')
package=out/'extracted/package'
schema=load_schema(HERE/'content.taut.py')
results={}
for mode in ('source','package'):
    directory=out/mode
    module='./typescript/foundation.ts' if mode=='source' else (package/'cjs/foundation.js').as_posix()
    binding=None if mode=='source' else {'typescript':{'module':module,'validation_module':(package/'cjs/validation.js').as_posix(),'artifact':str(artifact)}}
    emit(schema,directory,langs=['typescript'],services=[],runtime_mode=mode,validation=True,runtime_bindings=binding)
    (directory/'main.ts').write_text((HERE/'main.ts').read_text().replace('FOUNDATION',module),encoding='utf-8')
    completed=subprocess.run([shutil.which('tsc'),'--target','ES2022','--module','commonjs','--strict','--skipLibCheck',
        '--rewriteRelativeImportExtensions','--rootDir',str(directory),'--outDir',str(directory/'built'),str(directory/'main.ts')],capture_output=True,text=True)
    if completed.returncode:raise RuntimeError(completed.stdout+completed.stderr)
    completed=subprocess.run(['node',str(directory/'built/main.js')],capture_output=True,text=True)
    if completed.returncode:raise RuntimeError(completed.stdout+completed.stderr)
    results[mode]=json.loads(completed.stdout)
if results['source']!=results['package']:raise AssertionError('distribution behavior differs')
(out/'results.json').write_text(json.dumps(results,indent=2)+'\n')
print(json.dumps(results,indent=2))
