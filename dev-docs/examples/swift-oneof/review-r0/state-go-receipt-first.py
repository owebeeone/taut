from pathlib import Path
import json
from taut.gen.scaffold import emit
from taut.gen.go_runtime import FILES
from taut.ir.dsl import schema,Msg,F,INT
import taut.gen.python_runtime as common
root=Path(__file__).parent/'go-receipt-first-cases';root.mkdir(parents=True,exist_ok=True)
s=schema(Record=Msg(value=F(1,INT)));results=[]
for mode in ('package',None):
 for enabled in (False,True):
  d=root/(str(mode)+'-'+str(enabled))
  emit(s,d,langs=['go'],services=[],runtime=True,validation=enabled)
  original=common.apply_outputs
  def forced(writes,deletes):
   original(writes,set())
   receipt=d/'go/.taut-go-runtime.json';assert receipt in deletes;receipt.unlink()
   raise OSError('persisted owner-receipt-first cutoff')
  config={'go':{'import_path':'foundation.local/runtime'}}
  common.apply_outputs=forced
  try: emit(s,d,langs=['go'],services=[],runtime_mode=mode,validation=enabled,runtime_bindings=config)
  except OSError: pass
  finally: common.apply_outputs=original
  before={p.name:p.read_bytes() for p in (d/'go').iterdir() if p.is_file()}
  try:
   emit(s,d,langs=['go'],services=[],runtime_mode=mode,validation=enabled,runtime_bindings=config)
   status='success'
  except ValueError as exc: status=str(exc)
  after={p.name:p.read_bytes() for p in (d/'go').iterdir() if p.is_file()}
  results.append(dict(mode=mode,validation=enabled,result=status,unchanged=before==after,leftovers=sorted(set(after)&set(FILES))))
print(json.dumps(results,indent=2));(Path(__file__).parent/'go-receipt-first-results.json').write_text(json.dumps(results,indent=2))
