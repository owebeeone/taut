from pathlib import Path
import subprocess,json,os
from taut.gen.scaffold import emit
from taut.gen.swift_runtime import canonical_sources,build_foundation
from taut.ir.dsl import schema,Msg,F,INT,Enum
root=Path('D:/projects/limbo/swift-oneof-scratch/review-r1/code-raw/scratch/probes/native-replay');root.mkdir(parents=True,exist_ok=True)
rows=[]
def run(cmd,owner=None):
 env=dict(os.environ)
 if owner:
  for k in ['PATH','LD_LIBRARY_PATH']:env[k]=str(owner)+os.pathsep+env.get(k,'')
 p=subprocess.run(list(map(str,cmd)),capture_output=True,text=True,encoding='utf-8',env=env)
 rows.append(dict(command=list(map(str,cmd)),exit=p.returncode,stdout=p.stdout,stderr=p.stderr));assert p.returncode==0,p.stderr
for enabled in (False,True):
 owner=build_foundation(root/('owner-on' if enabled else 'owner-off'),validation=enabled)
 supplied=root/('flat-on' if enabled else 'flat-off');supplied.mkdir()
 for n,data in canonical_sources(validation=enabled).items():(supplied/n).write_bytes(data)
 def application(name,kind,mode,flat=False):
  s=schema(Enum(name,one=0,two=1)) if kind=='enum' else schema(**{name:Msg(value=F(1,INT))})
  d=root/(name+'-'+kind)/str(enabled)/('flat' if flat else str(mode));cfg=None if flat else {'swift':{'module':'TautFoundation',**({'artifact':str(owner)} if mode!='source' else {})}}
  emit(s,d,langs=['swift'],services=[],validation=enabled,runtime_mode=mode,runtime_bindings=cfg)
  if mode=='source':assert all((d/'swift'/n).read_bytes()==v for n,v in canonical_sources(validation=enabled).items())
  if kind=='enum':native='precondition('+name+'.descriptor.members["one"] == 0)\nprecondition(try! '+name+'.fromCbor(Cbor.int(1)) == .two)\n'
  else:native='let r='+name+'(value:0)\nprecondition('+name+'.descriptor.name == "'+name+'")\nprecondition(try! '+name+'.decode(encode(r.toCbor())).value == 0)\n'+('precondition(r.isValid() && r.validate().isComplete)\n' if enabled else '')
  main=d/'main.swift';main.write_text(('' if flat else 'import TautFoundation\n')+native+'print("'+name+' '+str(mode)+' '+str(enabled)+' PASS")\n',encoding='utf-8')
  binary=d/'app.exe';link=list(supplied.glob('*.swift')) if flat else ['-I',owner,'-L',owner,'-lTautFoundation']
  run(['swiftc',*link,d/'swift/api.swift',main,'-o',binary],None if flat else owner);run([binary],None if flat else owner)
 for name in ['Data','NSLock','ObjectIdentifier','AnyObject','Void']:
  application(name,'message',None,flat=True);application(name,'message',None)
 for mode in ['source','package']:application('Void','message',mode)
 for kind in ['message','enum']:
  for mode in ['source','package',None]:application('Foundation',kind,mode)
for enabled in (False,True):
 for kind in ['message','enum']:
  s=schema(Foundation=Msg(value=F(1,INT))) if kind=='message' else schema(Enum('Foundation',one=0))
  d=root/'flat-refusals'/str(enabled)/kind;attempts=[];original=Path.open
  def observe(self,*args,**kwargs):
   if args and args[0]=='xb' and self.name=='.taut-generation.lock':attempts.append(str(self))
   return original(self,*args,**kwargs)
  Path.open=observe
  try:
   try:emit(s,d,langs=['swift'],services=[],validation=enabled)
   except ValueError as e:
    assert 'explicit imported runtime module' in str(e) and not d.exists() and not attempts
    rows.append(dict(flat_foundation=kind,validation=enabled,refused=True,before_lock=True,error=str(e)))
   else:raise AssertionError('flat Foundation accepted')
  finally:Path.open=original
(root/'results.json').write_text(json.dumps(rows,indent=2),encoding='utf-8');print('PASS:20 original-name apps;4 Void source/package apps;12 Foundation imported apps;4 prelock flat refusals')