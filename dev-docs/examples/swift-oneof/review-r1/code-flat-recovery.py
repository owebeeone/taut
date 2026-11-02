from pathlib import Path
import json
import taut.gen.python_runtime as common
from taut.gen.scaffold import emit
from taut.gen import swift_runtime,go_runtime
from taut.ir.dsl import schema,Msg,F,INT
root=Path('D:/projects/limbo/swift-oneof-scratch/review-r1/code-raw/scratch/probes/flat-recovery');root.mkdir(parents=True,exist_ok=True)
s=schema(Record=Msg(value=F(1,INT)));rows=[]
def snapshot(d):return {p.relative_to(d).as_posix():p.read_bytes() for p in d.rglob('*') if p.is_file()}
for lang,profile in [('go',go_runtime),('swift',swift_runtime)]:
 for oldflag in [False,True]:
  for newflag in [False,True]:
   for separate in [False,True]:
    d=root/lang/str(oldflag)/str(newflag)/str(separate);out=d/'app';owner=d/'source-owner' if separate else out/lang
    config={lang:{'source_root':str(owner),'module' if lang=='swift' else 'import_path':'TautFoundation' if lang=='swift' else 'fixture.local/foundation'}} if separate else None
    emit(s,out,langs=[lang],services=[],runtime=True,validation=oldflag,runtime_bindings=config)
    (owner/'handwritten.txt').write_text('retain')
    receipt=out/lang/('.taut-'+lang+'-outputs.json');owner_receipt=owner/('.taut-'+lang+'-runtime.json');original=common.apply_outputs
    def interrupt(writes,deletes):
     original(writes,set());data=json.loads(receipt.read_text());assert data['retiring_source_roots']==[str(owner.resolve())] and owner_receipt in deletes
     owner_receipt.unlink();raise OSError('owner receipt persisted first')
    common.apply_outputs=interrupt
    try:
     try:emit(s,out,langs=[lang],services=[],validation=newflag)
     except OSError:pass
     else:raise AssertionError('did not interrupt')
    finally:common.apply_outputs=original
    before=snapshot(d)
    try:emit(s,out,langs=[lang],services=[],validation=newflag)
    except ValueError as e:
     assert 'unknown/handwritten' in str(e) and snapshot(d)==before and (owner/'handwritten.txt').read_text()=='retain'
     assert not list(d.rglob('.taut-generation.lock'))
     rows.append(dict(language=lang,old_validation=oldflag,new_validation=newflag,separate=separate,refused=True,unchanged=True,error=str(e)))
    else:raise AssertionError('default flat falsely succeeded')
 # Fresh caller-supplied files remain legal; later clean retirement clears proof.
 d=root/lang/'fresh';out=d/'app';owner=out/lang;owner.mkdir(parents=True)
 for n,data in profile.canonical_sources().items():(owner/n).write_bytes(data)
 before={n:(owner/n).read_bytes() for n in profile.FILES}
 for flag in [False,True,False]:emit(s,out,langs=[lang],services=[],validation=flag);assert all((owner/n).read_bytes()==data for n,data in before.items())
 rows.append(dict(language=lang,fresh_repeated_nonowning=True,preserved=True))
 d=root/lang/'clean';out=d/'app';owner=out/lang
 emit(s,out,langs=[lang],services=[],runtime=True,validation=True);emit(s,out,langs=[lang],services=[])
 receipt=owner/('.taut-'+lang+'-outputs.json');assert json.loads(receipt.read_text())['retiring_source_roots']==[str(owner.resolve())]
 emit(s,out,langs=[lang],services=[]);assert 'retiring_source_roots' not in json.loads(receipt.read_text())
 rows.append(dict(language=lang,clean_retirement_cleared=True))
(root/'results.json').write_text(json.dumps(rows,indent=2),encoding='utf-8');print('PASS:16 actual default-flat receipt-first retries refuse unchanged;fresh repeated nonowning and clean provenance clearing work for both targets')