import subprocess,types,sys,json,hashlib
from pathlib import Path
from taut.ir.dsl import schema,Msg,F,INT,Enum
from taut.gen.swift_runtime import canonical_sources
repo=Path('D:/projects/limbo/taut-dev/taut');root=Path(__file__).parent/'baseline-module-names';root.mkdir(exist_ok=True)
source=subprocess.check_output(['git','-c','safe.directory='+repo.as_posix(),'-C',str(repo),'show','83291c2c7c7b126e41625bd29623870330f3b0d6:src/taut/gen/swift.py'])
old=types.ModuleType('taut.gen.swift_r1_baseline');old.__package__='taut.gen';old.__file__=str(repo/'src/taut/gen/swift.py');sys.modules[old.__name__]=old
exec(compile(source,old.__file__,'exec'),old.__dict__)
rows=[]
for name in ('Foundation','Swift'):
 for kind in ('message','enum'):
  d=root/(name+'-'+kind);d.mkdir(exist_ok=True)
  record=schema(**{name:Msg(value=F(1,INT))}) if kind=='message' else schema(Enum(name,ok=1))
  try:text=old.emit_types(record)
  except ValueError as error:rows.append(dict(name=name,kind=kind,prewrite_error=str(error)));continue
  paths=[]
  for filename in ('cbor.swift','ext.swift'):
   p=d/filename;p.write_bytes((repo/'src/taut/gen/runtime'/filename).read_bytes());paths.append(p)
  p=d/'api.swift';p.write_text(text,encoding='utf-8');paths.append(p)
  p=d/'main.swift';p.write_text('let value = '+name+('(value: 1)\nprecondition(value.value == 1)\n' if kind=='message' else '.ok\nprecondition(value.rawValue == 1)\n'),encoding='utf-8');paths.append(p)
  command=['swiftc',*map(str,paths),'-o',str(d/'app.exe')]
  result=subprocess.run(command,capture_output=True,text=True)
  (d/'stderr.txt').write_text(result.stderr,encoding='utf-8')
  if name=='Swift':
   assert 'Swift' in old.RESERVED_TYPE_NAMES and result.returncode!=0
   rows.append(dict(name=name,kind=kind,old_reservation=old.RESERVED_TYPE_NAMES[name],
                    low_level_bypassed_preflight=True,command=command,compile_exit=result.returncode,stderr=result.stderr))
   continue
  assert result.returncode==0,result.stderr
  run=subprocess.run([str(d/'app.exe')],capture_output=True,text=True);assert run.returncode==0
  rows.append(dict(name=name,kind=kind,command=command,compile_exit=result.returncode,run_exit=run.returncode,stderr=result.stderr))
(root/'results.json').write_text(json.dumps(dict(baseline='83291c2c7c7b126e41625bd29623870330f3b0d6',emitter_sha256=hashlib.sha256(source).hexdigest(),rows=rows),indent=2),encoding='utf-8')
print('Foundation message/enum old compile+run PASS; Swift old reservation unchanged')
