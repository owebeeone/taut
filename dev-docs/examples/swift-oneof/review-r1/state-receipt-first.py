from pathlib import Path
import json
from taut.gen.scaffold import emit
from taut.gen.swift_runtime import FILES
from taut.ir.dsl import schema,Msg,F,INT
import taut.gen.python_runtime as common
root=Path(__file__).parent/'receipt-first-cases'
root.mkdir(parents=True,exist_ok=True)
s=schema(Record=Msg(value=F(1,INT)))
results=[]
for selected in ('flat','imported','package'):
 for enabled in (False,True):
  d=root/(selected+'-'+str(enabled))
  emit(s,d,langs=['swift'],services=[],runtime=True,validation=enabled)
  original=common.apply_outputs
  def forced(writes,deletes):
   original(writes,set())
   receipt=d/'swift/.taut-swift-runtime.json'
   assert receipt in deletes
   receipt.unlink()
   raise OSError('persisted owner-receipt-first cutoff')
  kwargs={} if selected=='flat' else {'runtime_bindings':{'swift':{'module':'TautFoundation'}}}
  if selected=='package': kwargs['runtime_mode']='package'
  common.apply_outputs=forced
  try: emit(s,d,langs=['swift'],services=[],validation=enabled,**kwargs)
  except OSError: pass
  finally: common.apply_outputs=original
  before={p.name:p.read_bytes() for p in (d/'swift').iterdir() if p.is_file()}
  try:
   emit(s,d,langs=['swift'],services=[],validation=enabled,**kwargs)
   status='success'
  except ValueError as exc: status=str(exc)
  after={p.name:p.read_bytes() for p in (d/'swift').iterdir() if p.is_file()}
  result=dict(selected=selected,validation=enabled,result=status,unchanged=before==after,leftovers=sorted(set(after)&set(FILES)),source_root=json.loads(after['.taut-swift-outputs.json'])['source_root'])
  results.append(result)
print(json.dumps(results,indent=2))
(Path(__file__).parent/'receipt-first-results.json').write_text(json.dumps(results,indent=2))
