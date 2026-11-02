import importlib,json,stat,subprocess
from pathlib import Path
from taut.gen.scaffold import emit
from taut.gen.python_runtime import _is_alias
from taut.ir.dsl import schema,Msg,F,INT
root=Path(__file__).parent/'dangling-independent';root.mkdir(exist_ok=True)
results=[]
for language in ('go','swift'):
 profile=importlib.import_module('taut.gen.'+language+'_runtime')
 output=root/language
 record=schema(Record=Msg(value=F(1,INT)))
 emit(record,output,langs=[language],services=[],runtime=True)
 emit(record,output,langs=[language],services=[])
 owner=output/language;receipt=owner/('.taut-'+language+'-outputs.json')
 assert json.loads(receipt.read_text())['retiring_source_roots']==[str(owner.resolve())]
 target=output/'target';target.mkdir()
 alias=owner/next(iter(profile.FILES))
 command=['cmd','/c','mklink','/J',str(alias),str(target)]
 made=subprocess.run(command,capture_output=True,text=True);assert made.returncode==0,made.stdout+made.stderr
 target.rmdir()
 before={str(p.relative_to(output)):p.read_bytes() for p in output.rglob('*') if p.is_file()}
 observation=dict(exists=alias.exists(),is_symlink=alias.is_symlink(),lstat_reparse=bool(alias.lstat().st_file_attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT),is_alias=_is_alias(alias))
 try:
  emit(record,output,langs=[language],services=[])
  result='success'
 except ValueError as error:result=str(error)
 after={str(p.relative_to(output)):p.read_bytes() for p in output.rglob('*') if p.is_file()}
 assert result!='success' and 'unknown/handwritten' in result and before==after and _is_alias(alias)
 assert not list(output.rglob('.taut-generation.lock'))
 results.append(dict(language=language,command=command,observed=observation,result=result,unchanged=before==after,retiring_roots=json.loads(receipt.read_text())['retiring_source_roots']))
print(json.dumps(results,indent=2))
(Path(__file__).parent/'dangling-independent-results.json').write_text(json.dumps(results,indent=2))
