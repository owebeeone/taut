import json,sys,types,subprocess,hashlib
from pathlib import Path
from taut.gen import go_runtime as current
from taut.gen.scaffold import go_api
from taut.gen.python_runtime import apply_outputs
from taut.ir.load import load_schema
repo=Path('D:/projects/limbo/taut-dev/taut');scratch=Path(__file__).parent
tag='-'+sys.argv[1] if len(sys.argv)>1 else ''
show=lambda name:subprocess.check_output(['git','-c','safe.directory='+repo.as_posix(),'-C',str(repo),'show','83291c2c7c7b126e41625bd29623870330f3b0d6:'+name])
source=show('src/taut/gen/go_runtime.py')
old=types.ModuleType('taut.gen.go_accepted_r1');old.__file__=current.__file__;old.__package__='taut.gen';sys.modules[old.__name__]=old
exec(compile(source,old.__file__,'exec'),old.__dict__)
unchanged={name:hashlib.sha256(show(name)).hexdigest() for name in ('src/taut/gen/go.py','src/taut/gen/go_metadata.py')}
assert all(hashlib.sha256((repo/name).read_bytes()).hexdigest()==sha for name,sha in unchanged.items())
schema=load_schema(repo/'dev-docs/examples/go-oneof/content.taut.py');checks=[]
for enabled in (False,True):
 root=scratch/('go-equivalence'+tag+'-'+str(enabled));assert not root.exists()
 directory=root/'schema';owner=root/'owner';path=directory/'.taut-go-outputs.json'
 text=go_api(schema,validation=enabled,identity='equivalent',runtime_import='app.local/foundation')
 for step,(mode,consume) in enumerate([('source',False),('source',False),('package',True),('package',False),('source',False)]):
  args=dict(mode=mode,validation=enabled,source_root=owner,consume_source=consume)
  before=old.plan_outputs(directory,{'api.go':text},**args);after=current.plan_outputs(directory,{'api.go':text},**args)
  assert before[1]==after[1] and before[0].keys()==after[0].keys()
  deltas={}
  for target,content in before[0].items():
   if content==after[0][target]:continue
   assert target==path
   a,b=json.loads(content),json.loads(after[0][target]);deltas=dict(before=a.pop('retiring_source_roots',None),after=b.pop('retiring_source_roots',None))
   assert a==b
   assert all(value is None or value==[str(owner.resolve())] for value in deltas.values())
  checks.append(dict(validation=enabled,step=step,mode=mode,consume_source=consume,
                     exact_maps_equal=before==after,retirement_provenance_only_delta=deltas,
                     all_other_write_bytes_equal=True,deletion_sets_equal=True))
  apply_outputs(*after)
value=dict(baseline='83291c2c7c7b126e41625bd29623870330f3b0d6',original_kernel_sha256=hashlib.sha256(source).hexdigest(),
 current_owned_kernel_sha256=hashlib.sha256((repo/'src/taut/gen/owned_runtime.py').read_bytes()).hexdigest(),
 unchanged_go_emitter_and_metadata=unchanged,checks=checks,
 exact_maps=sum(row['exact_maps_equal'] for row in checks),provenance_only_deltas=sum(not row['exact_maps_equal'] for row in checks))
(scratch/('go-equivalence-r1'+tag+'.json')).write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')
print(json.dumps(value,indent=2))
