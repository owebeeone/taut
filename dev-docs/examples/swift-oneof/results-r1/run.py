import json,os,subprocess,sys,time,hashlib
from pathlib import Path
import xml.etree.ElementTree as ET
root=Path(__file__).parent
label,*arguments=sys.argv[1:]
source=json.loads((root/os.environ.get('TAUT_SOURCE_RECEIPT','source-before-final-focused.json')).read_text())
repo=Path('D:/projects/limbo/taut-dev/taut')
verify=lambda: all(hashlib.sha256((repo/name).read_bytes()).hexdigest()==entry['sha256'] for name,entry in source['files'].items())
assert verify()
xml=root/('final-'+label+'.xml')
command=[sys.executable,'-m','pytest',*arguments,'-q','-p','no:cacheprovider','--basetemp',str(root/('final-'+label+'-temp')),'--junitxml',str(xml)]
start=time.monotonic()
with (root/('final-'+label+'.log')).open('w',encoding='utf-8') as output:
 result=subprocess.run(command,cwd=root,stdout=output,stderr=subprocess.STDOUT)
receipt=dict(command=command,cwd=str(root),exit=result.returncode,elapsed_seconds=round(time.monotonic()-start,3),
 source_inventory_sha256=source['source_hash'],source_unchanged=verify(),python=sys.version,executable=sys.executable,
 environment={key:os.environ.get(key) for key in ('PYTHONPATH','PYTEST_DISABLE_PLUGIN_AUTOLOAD','TEMP','TMP','GOCACHE','GOMODCACHE','XDG_CONFIG_HOME')})
if xml.exists():
 suites=list(ET.parse(xml).getroot().iter('testsuite'))
 receipt['counts']={key:sum(int(s.get(key,0)) for s in suites) for key in ('tests','failures','errors','skipped')}
(root/('final-'+label+'.json')).write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
print(json.dumps(receipt,indent=2))
assert receipt['source_unchanged']
sys.exit(result.returncode)
