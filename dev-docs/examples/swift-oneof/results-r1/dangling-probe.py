import json,subprocess,sys
from pathlib import Path
from taut.ir.dsl import schema,Msg,F,INT
from taut.gen.scaffold import emit
from taut.gen.python_runtime import _is_alias
from taut.gen.swift_runtime import FILES
root=Path(__file__).parent/('dangling-probe-'+sys.argv[1] if len(sys.argv)>1 else 'dangling-probe');root.mkdir(exist_ok=True)
record=schema(Record=Msg(value=F(1,INT)))
emit(record,root,langs=['swift'],services=[],runtime=True)
emit(record,root,langs=['swift'],services=[])
owner=root/'swift';receipt=owner/'.taut-swift-outputs.json'
assert json.loads(receipt.read_text())['retiring_source_roots']==[str(owner.resolve())]
target=root/'empty';target.mkdir()
alias=owner/'cbor.swift'
command=['cmd','/c','mklink','/J',str(alias),str(target)]
r=subprocess.run(command,capture_output=True,text=True);assert r.returncode==0,r.stderr
target.rmdir()
before=receipt.read_bytes()
try:emit(record,root,langs=['swift'],services=[]);status='success'
except ValueError as error:status=str(error)
result=dict(command=command,alias_exists=alias.exists(),is_alias=_is_alias(alias),result=status,
            receipt_unchanged=receipt.read_bytes()==before,retiring_roots=json.loads(receipt.read_text()).get('retiring_source_roots'))
(root/'results.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print(json.dumps(result,indent=2))
