from pathlib import Path
import json,hashlib,zipfile,shutil
repo=Path('D:/projects/limbo/taut-dev/taut');scratch=Path(__file__).parent
destination=repo/'dev-docs/examples/swift-oneof/results-r1';destination.mkdir(exist_ok=True)
def copy(source,name=None):
 target=destination/(name or source.name);target.write_bytes(source.read_bytes())
digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
source=json.loads((scratch/'source-before-alias-final-focused.json').read_text())
assert source==json.loads((scratch/'source-after-alias-final-focused.json').read_text())
old=json.loads((scratch/'source-before-final-focused.json').read_text())
assert old==json.loads((scratch/'source-after-first-focused.json').read_text())
for label in ('go-shared-final','swift-affected-final','wheel-prelock-final'):
 receipt=json.loads((scratch/('final-'+label+'.json')).read_text())
 assert receipt['exit']==0 and receipt['source_unchanged'] and receipt['source_inventory_sha256']==source['source_hash']
 assert not any(receipt['counts'][n] for n in ('failures','errors','skipped'))
for path in scratch.iterdir():
 if path.is_file() and path.suffix in ('.json','.log','.xml','.py','.ps1'):copy(path)
for directory,name in [('module-shadow','module-shadow-results.json'),('baseline-module-names','baseline-module-names-results.json'),
                       ('dangling-probe','dangling-before-results.json'),('dangling-probe-fixed','dangling-after-results.json'),
                       ('final-example','native-example-before-alias.json'),('alias-final-example','native-example-final.json')]:
 copy(scratch/directory/'results.json',name)
wheel=next((scratch/'final-wheel-prelock-final-temp').rglob('*.whl'))
resources={name:digest(repo/'src/taut/gen/runtime'/name) for name in ('cbor.swift','ext.swift','swift/paths.swift','swift/descriptors.swift','swift/reports.swift','swift/validation.swift')}
with zipfile.ZipFile(wheel) as archive:
 for name,sha in resources.items():assert hashlib.sha256(archive.read('taut/gen/runtime/'+name)).hexdigest()==sha
 for name in ('owned_runtime.py','scaffold.py','swift_metadata.py'):
  assert archive.read('taut/gen/'+name)==(repo/'src/taut/gen'/name).read_bytes()
value=dict(status='FOCUSED GATES PASS; findings remain open until original-axis closure at corrected settled tuple',
 source_parent=source['source_parent'],source_inventory_sha256=source['source_hash'],source_count=30,changed_production_count=12,
 source_inventory='dev-docs/examples/swift-oneof/results-r1/source-before-alias-final-focused.json',
 final_runs={name:json.loads((scratch/('final-'+name+'.json')).read_text()) for name in ('go-shared-final','swift-affected-final','wheel-prelock-final')},
 native_examples=dict(executions=5,all_exit_zero=True,receipt='dev-docs/examples/swift-oneof/results-r1/native-example-final.json'),
 full_swift_before_final_alias=dict(tests=186,failures=0,skips=0,deselected=1,source_inventory_sha256=old['source_hash'],
   receipt='dev-docs/examples/swift-oneof/results-r1/final-swift.json',
   limit='Retained at its original source hash; final delta only one unknown-runtime alias condition and two Go/Swift regression cases. Final affected Swift101, Go/shared405, wheel11 and five examples use final hash. Canonical Swift/native generator bytes unchanged by that final delta.'),
 wheel=dict(path=str(wheel),sha256=digest(wheel),canonical_resources=resources,
   isolated_generation=True,native_source_package_default_flat=True,current_owned_planner_scaffold_metadata_bytes_verified=True),
 go_preservation=json.loads((scratch/'go-equivalence-r1-final.json').read_text()),
 protections='dev-docs/examples/swift-oneof/results-r1/protected-after-focused.json',
 overlap='Counts overlap; never sum.405=387Go-file cases (145existing+242newsharedGo/Swiftstate)+12scaffold+4map+2help.101Swift is focused,55nonselected.11=1Swiftwheel+9previousowneraliases+1pairplan.186priorfullSwift=156feature+30existing;1duplicateparitydeselected.',
 development_attempts=['Original namespace and flat receipt-first r0 failures remain in verbatim reports and review-r0 evidence.',
 'State230, additional10 and names38 development results precede final two Swift reservation controls and final dangling-alias hardening; they are not relabeled final source.',
 'Initial baseline-module-name harness directly invoked the raw old emitter, bypassed its normal reserved-name preflight, and wrongly expected Swift to compile. Original script retained; corrected probe records native failure and unchanged old Swift reservation. Foundation message/enum old-success controls pass.',
 'Dangling junction probe reproduced exists=False/is_alias=True false cleanup success before the final one-line fix; fixed probe and BOTH actual Windows junction regressions now refuse unchanged. No symlink privilege skip was weakened.'],
 global_limit='No full broad/all16 repeat. Completed r0 package remains at c0276593/a8f37984 with2260pass/3baselinefail/5skip/8duplicateexclusions; all16GREEN. No new-source broad-green claim.',
 reviewer_closure='SAME TWO original reviewers, no self-closure, no new agents, remediation round1')
(repo/'dev-docs/SwiftOneOfCheckpoint-FocusedResults-1.json').write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')
inventory={p.name:dict(sha256=digest(p),size=p.stat().st_size) for p in sorted(destination.iterdir()) if p.is_file()}
(destination/'evidence-inventory.json').write_text(json.dumps(dict(files=inventory,count=len(inventory),self_hash='omitted recursively'),indent=2)+'\n',encoding='utf-8')
print('Filed',len(inventory),'R1 evidence files; wheel',value['wheel']['sha256'])
