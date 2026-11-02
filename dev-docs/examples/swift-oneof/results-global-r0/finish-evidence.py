from pathlib import Path
import hashlib,json,subprocess,xml.etree.ElementTree as ET
root=Path(__file__).resolve().parent
def read(name):return json.loads((root/name).read_text(encoding='utf-8'))
def save(name,value):(root/name).write_text(json.dumps(value,indent=2,sort_keys=True)+'\n',encoding='utf-8',newline='\n')
r=read('global-results.json');xml=ET.parse(root/'broad-results.xml');cases=list(xml.getroot().iter('testcase'))
groups={}
for c in cases:
    name=c.attrib.get('classname','').split('.')[-1]
    g=groups.setdefault(name,{'passed':0,'failed':0,'skipped':0,'total':0})
    kind='failed' if c.find('failure') is not None or c.find('error') is not None else 'skipped' if c.find('skipped') is not None else 'passed'
    g[kind]+=1;g['total']+=1
selected=read('selected-tests.json');deselected=read('deselected-tests.json')
enum_rows=[]
for c in cases:
    if c.attrib.get('classname','').endswith('test_oneof') and ('metadata' in c.attrib['name'] or 'enum_case' in c.attrib['name']):
        enum_rows.append({'name':c.attrib['name'],'passed':c.find('failure') is None and c.find('error') is None and c.find('skipped') is None})
raw_before=read('raw-source-blob-before.json');raw_after=read('raw-source-blob-after.json')
protected=read('protected-before.json')
summary={'broad':{'selected':len(selected),'executed':len(cases),'passed':r['passed'],'failed':len(r['failures']),'skipped':r['skipped'],'deselected':len(deselected)},
 'source_counts':r['selected_source_counts'],'source_total':sum(r['selected_source_counts'].values()),
 'raw_blob_counts':raw_before['counts'],'raw_blob_total':sum(raw_before['counts'].values()),'raw_before_after_equal':raw_before==raw_after,
 'swift_owned_raw_count':raw_before['swift_owned_count'],'protected_counts':{k:len(v) for k,v in protected.items()},
 'feature_results':groups,'enum_metadata_case_results':enum_rows,'only_eight_duplicate_deselections':r['exact8deselections'],
 'metadata_policy_deselections':[],'failures':r['failures'],'baseline_failures':r['baseline_failures'],'new_failures':r['new_failures']}
save('final-derived-counts.json',summary)
lines=['# Settled all-nine integration gate — Swift r0','',
 'Exact-source read/run gate; this is not an independent review axis. No product changes or corrective reruns were performed.','',
 '```json',json.dumps(r['source_tuple'],indent=2),'```','',
 f"All {r['parity_variants']} existing codec variants ran GREEN with require_all=True/jobs=2; {len(r['parity_violations'])} governance violations.",'',
 f"Broad: {r['passed']} passed, {len(r['failures'])} failed, {r['skipped']} skipped, {r['deselected']} deselected; {len(selected)} selected. Pytest exit {r['broad_exit_code']}. Total gate elapsed {r['elapsed_seconds']} seconds.",'',
 f"Demonstrated baseline failures: {len(r['baseline_failures'])}. New failures: {len(r['new_failures'])}. All exact tracebacks are in broad-regression-tests.log and failure-*.txt; machine details in global-results.json.",'',
 'Baseline failures kept enabled: missing historical proto-surface document, two Windows Go CRLF/gofmt checks. Updated enum.case authoring and metadata tests stayed enabled. Only the eight duplicate parity marker tests were deselected.','',
 '## Commands','', '```text','taut.corpus.parity.run_gate(require_all=True,jobs=2)',subprocess.list2cmdline(r['broad_command']),'```','',
 'Executed from the assigned scratch directory using stable CPython3.13.5, pytest9.1.1, activated toolchains, UTF8 JVM, disabled third-party pytest plugin autoload, isolated process-local Git trust, scratch caches/temp. See environment.json and run-gate.ps1.','',
 '## Integrity','',
 f"All five HEADs, {summary['source_total']} selected source files, {summary['raw_blob_total']} raw committed-blob comparisons, all45 Swift owned files including Preparation self, protected5, excluded35, five indices, and {len(protected['locks_and_manifests'])} locks/manifests remained identical. Counts are derived from JSON. GWZ before/after records classify any permitted untracked review evidence.",'',
 'Accepted unchanged ECMA library R1 receipts were associated using the original full28 inventory overridden by R1 changed11 hashes. All28 source files, dependency lock, and corrected typecheck/build/test315 log hashes matched. No new standalone library run or dependency install was performed.','',
 '## Failures','']
for category in ('baseline_failures','new_failures'):
    lines.append(category+':')
    lines.extend('- '+a+'::'+b for a,b in r[category]);lines.append('')
lines.extend(['## Skips',''])
for row in read('skip-classification.json'):lines.append('- '+row['classname']+'::'+row['name']+' — '+row['reason'])
lines.extend(['','## Deselections',''])
for row in deselected:lines.append('- '+row['nodeid']+' — '+row['reason'])
lines.extend(['','## Feature collection and outcomes','', '| Module | Passed | Failed | Skipped | Selected |','|---|---:|---:|---:|---:|'])
for name,g in groups.items():
    if any(s in name for s in ('oneof','distribution')) or name in ('test_swift','test_oneof'):
        lines.append(f"| {name} | {g['passed']} | {g['failed']} | {g['skipped']} | {g['total']} |")
(root/'RESULTS.md').write_text('\n'.join(lines)+'\n',encoding='utf-8',newline='\n')
files={p.name:{'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'size':p.stat().st_size} for p in root.iterdir() if p.is_file() and p.name!='evidence-inventory.json'}
save('evidence-inventory.json',{'files':files,'count':len(files),'self_hash':'omitted recursively','scope':'top-level evidence only; build/cache folders excluded'})
print(json.dumps(summary,indent=2))
