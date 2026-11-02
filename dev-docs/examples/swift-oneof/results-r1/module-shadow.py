import json, subprocess
from pathlib import Path
from taut.ir.dsl import schema, Msg, F, INT
from taut.gen.scaffold import swift_api
from taut.gen.swift_runtime import canonical_sources
root=Path(__file__).parent/'module-shadow'
root.mkdir(exist_ok=True)
rows=[]
for name in ('Foundation','Swift'):
 for qualified in (False,True):
  d=root/(name+'-'+str(qualified));d.mkdir(exist_ok=True)
  try: text=swift_api(schema(**{name:Msg(value=F(1,INT))}))
  except ValueError as e:
   rows.append(dict(name=name,qualified=qualified,generation_error=str(e)));continue
  paths=[]
  for n,b in canonical_sources(validation=False).items():
   t=b.decode()
   if qualified:
    import re
    for before,after in [('Data','Foundation.Data'),('NSLock','Foundation.NSLock'),('ObjectIdentifier','Swift.ObjectIdentifier'),('AnyObject','Swift.AnyObject')]:
     t=re.sub(r'\b'+before+r'\b',after,t)
   p=d/n;p.write_text(t,encoding='utf-8');paths.append(p)
  p=d/'api.swift';p.write_text(text.replace('guardOwner: Void','guardOwner: ()'),encoding='utf-8');paths.append(p)
  p=d/'main.swift';p.write_text('let x = '+name+'(value: 1)\nprecondition(x.value == 1)\n',encoding='utf-8');paths.append(p)
  command=['swiftc',*map(str,paths),'-o',str(d/'app.exe')]
  r=subprocess.run(command,capture_output=True,text=True)
  rows.append(dict(name=name,qualified=qualified,command=command,exit=r.returncode,stderr=r.stderr))
(root/'results.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
for row in rows: print(row['name'],row['qualified'],row.get('exit',row.get('generation_error')),row.get('stderr','')[:1500])
