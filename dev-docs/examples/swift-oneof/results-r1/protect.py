from pathlib import Path
import json,hashlib
repo=Path('D:/projects/limbo/taut-dev/taut');workspace=repo.parent;scratch=Path(__file__).parent
original=json.loads((scratch.parent/'global-gate-r0/protected-after.json').read_text())
repos={'taut':repo,'workspace':workspace,'shape_python':workspace/'taut-shape-py','shape_rust':workspace/'taut-shape-rs','shape_ts':workspace/'taut-shape-ts'}
digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
current={}
for section,values in original.items():
 current[section]={}
 for name,sha in values.items():
  if section=='indices':p=repos[name]/'.git/index'
  elif section=='locks_and_manifests':
   key,path=name.split(':',1);p=repos[key]/path
  else:p=repo/name
  current[section][name]=digest(p) if p.exists() else None
assert current==original,[(s,n) for s,v in current.items() for n,h in v.items() if h!=original[s][n]]
(scratch/'protected-after-focused.json').write_text(json.dumps(current,indent=2)+'\n',encoding='utf-8')
print('Protected5/excluded35/5rawindices/47locks+manifests unchanged')
