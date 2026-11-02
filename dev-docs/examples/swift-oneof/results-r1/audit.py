from pathlib import Path
import hashlib,json,sys
repo=Path('D:/projects/limbo/taut-dev/taut');scratch=Path(__file__).parent
original=json.loads((scratch.parent/'source-before-settled-focused.json').read_text())
paths=set(original['files'])|{'src/tests/test_go_oneof.py'}
digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
files={name:dict(sha256=digest(repo/name),size=(repo/name).stat().st_size) for name in sorted(paths)}
assert all(digest(repo/name)==sha for name,sha in original['protected_user'].items())
assert all(digest(repo/name)==sha for name,sha in original['old35'].items())
allowed={'docs/SWIFT_API.md','src/taut/gen/swift_metadata.py','src/taut/gen/runtime/swift/paths.swift',
 'src/taut/gen/runtime/swift/descriptors.swift','src/taut/gen/owned_runtime.py','src/taut/gen/scaffold.py',
 'src/tests/test_swift_oneof.py','src/tests/test_go_oneof.py'}
allowed|={'dev-docs/examples/swift-oneof/golden/'+name+'.swift' for name in ('flat-off','flat-on','imported-off','imported-on')}
changed={name for name,entry in original['files'].items() if files[name]!=entry}|{'src/tests/test_go_oneof.py'}
assert changed==allowed,(changed^allowed)
value=dict(source_parent='c02765930f06cfcb19a522843aa54582db514706',workspace_parent='a8f37984471654902149d136b7a13a588346b58f',
 files=files,changed_production=sorted(changed),protected_user=original['protected_user'],excluded35=original['old35'],
 source_hash=hashlib.sha256(json.dumps(files,sort_keys=True).encode()).hexdigest())
destination=scratch/(sys.argv[1] if len(sys.argv)>1 else 'source-before-final-focused.json')
destination.write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')
print(destination.name,len(files),'source files;',len(changed),'changed production;',value['source_hash'])
