"""Materialize exact committed sibling inputs for Gearu's isolated candidate."""
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent
remote = sys.argv[1] == '--remote'
source = None if remote else Path(sys.argv[1]).resolve()
if source == ROOT:
    raise SystemExit('sibling preparation is only for an isolated Gearu candidate')
inputs = json.loads((ROOT/'release-inputs.json').read_text())
for name, sha in inputs.items():
    if name not in ('taut-shape','taut-shape-py','taut-shape-rs','taut-shape-ts'):
        raise SystemExit('unexpected release input: '+name)
    original = source.parent/name if source else None
    target = ROOT.parent/name
    def git(directory, *args):
        return subprocess.check_output(['git','-c','safe.directory='+directory.as_posix(),
                                        '-C',str(directory),*args], text=True).strip()
    if not target.exists():
        if original:
            subprocess.run(['git','-c','safe.directory='+original.as_posix(),
                            '-c','safe.directory='+(original/'.git').as_posix(),
                            'clone','--shared','--no-checkout',original.as_posix(),target.as_posix()],check=True)
        else:
            subprocess.run(['git','clone','--no-checkout',
                            'https://github.com/owebeeone/'+name+'.git',str(target)],check=True)
        git(target,'config','core.autocrlf','false')
        git(target,'checkout','--detach',sha)
    if git(target,'rev-parse','HEAD') != sha or git(target,'status','--porcelain'):
        raise SystemExit('sibling input differs from committed release pin: '+name)
    print(name, sha, flush=True)
subprocess.run([shutil.which('pnpm'), 'install', '--frozen-lockfile'],
               cwd=ROOT.parent/'taut-shape-ts', check=True)
