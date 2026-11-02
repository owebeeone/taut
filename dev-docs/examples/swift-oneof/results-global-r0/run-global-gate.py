"""ONE settled all-nine Swift r0 global gate; saved workspace is read/run only."""
from pathlib import Path
import dataclasses
import hashlib
import json
import os
import subprocess
import sys
import time
import traceback
import xml.etree.ElementTree as ET

HERE=Path(__file__).resolve().parent
WORKSPACE=Path('D:/projects/limbo/taut-dev')
REPOS={'taut':WORKSPACE/'taut','shape_ts':WORKSPACE/'taut-shape-ts','workspace':WORKSPACE,
       'shape_python':WORKSPACE/'taut-shape-py','shape_rust':WORKSPACE/'taut-shape-rs'}
EXPECTED={'taut':'c02765930f06cfcb19a522843aa54582db514706',
 'workspace':'a8f37984471654902149d136b7a13a588346b58f',
 'shape_python':'c08c2a1b5197f761c5b0b835c588da512130ceda',
 'shape_rust':'8e92b89ed3a4f218a5a4e018fbfee6301fcc14b4',
 'shape_ts':'1aaeab65e4564a462044d2f5d824cd2f375aae97'}
BASELINE={('test_dev_docs','test_proto_api_surface_extensions_doc_exists_and_covers_contract'),
 ('test_go','test_go_runtime_and_parity_runner_are_gofmt_clean'),
 ('test_go','test_generated_go_is_gofmt_clean')}
POLICY=[]

def save(name,data):
    (HERE/name).write_text(json.dumps(data,indent=2,sort_keys=True)+'\n',encoding='utf-8',newline='\n')
def git(repo,*args,raw=False):
    value=subprocess.check_output(['git','-c','safe.directory='+repo.as_posix(),'-C',str(repo),*args])
    return value if raw else value.decode('utf-8').strip()
def heads():return {name:git(path,'rev-parse','HEAD') for name,path in REPOS.items()}
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def selected(name,path):
    if name=='workspace':
        return path.startswith(('scripts/','gwz.conf/')) or path in ('AGENTS.md','AGENTS_GWZ.md')
    if path.startswith('dev-docs/'):
        return name=='taut' and path.startswith('dev-docs/examples/') and '/results/' not in path and not path.endswith(('.md','.log','.png','.svg','.pdf'))
    return True
def inventory():
    rows={}
    for name,repo in REPOS.items():
        files=[p for p in git(repo,'ls-tree','-r','--name-only',EXPECTED[name]).splitlines() if selected(name,p)]
        for i in range(0,len(files),75):
            changed=git(repo,'diff','--name-only',EXPECTED[name],'--',*files[i:i+75])
            if changed:raise RuntimeError(f'{name}: frozen source changed: {changed}')
        rows[name]={p:digest(repo/p) for p in files}
        new=[p for p in git(repo,'ls-files','--others','--exclude-standard').splitlines()
             if p.startswith(('src/','corpus/','ir/','rust/','scripts/'))]
        if new:raise RuntimeError(f'{name}: unexpected untracked production files: {new}')
    return rows

PREP=None
def protected():
    groups={'user_sources':{p:{'sha256':h} for p,h in PREP['protection']['user_five'].items()},
            'excluded_python_artifacts':{p:{'sha256':h} for p,h in PREP['protection']['excluded35_hashes'].items()}}
    result={}
    for group,items in groups.items():
        result[group]={}
        for name,record in items.items():
            actual=digest(REPOS['taut']/name)
            if actual!=record['sha256']:raise RuntimeError(f'protected {group} changed: {name}')
            result[group][name]=actual
    assert len(result['user_sources'])==5 and len(result['excluded_python_artifacts'])==35
    result['indices']={}
    result['locks_and_manifests']={}
    for name,repo in REPOS.items():
        index=Path(git(repo,'rev-parse','--git-path','index'))
        if not index.is_absolute():index=repo/index
        result['indices'][name]=digest(index)
        files=git(repo,'ls-tree','-r','--name-only',EXPECTED[name]).splitlines()
        for p in files:
            if Path(p).name in ('Cargo.lock','pnpm-lock.yaml','uv.lock','package-lock.json','pyproject.toml','package.json'):
                result['locks_and_manifests'][name+':'+p]=digest(repo/p)
    for p in (WORKSPACE/'gwz.conf').rglob('*'):
        if p.is_file():result['locks_and_manifests']['workspace:'+p.relative_to(WORKSPACE).as_posix()]=digest(p)
    return result

def workspace_status(name):
    command=['gwz','--target','@root','--target','taut','--target','taut-shape-py','--target','taut-shape-rs','--target','taut-shape-ts','status','--json']
    completed=subprocess.run(command,cwd=WORKSPACE,capture_output=True,text=True,encoding='utf-8')
    if completed.returncode:raise RuntimeError('GWZ readonly status failed: '+completed.stdout+completed.stderr)
    data=json.loads(completed.stdout);save(name,data)
    if data['errors']:raise RuntimeError('GWZ errors: '+str(data['errors']))
    changes=data['workspace_git_status'];root=changes['root_status']
    if root['staged'] or root['unstaged'] or changes['root_file_changes']:raise RuntimeError('workspace root index/worktree changed')
    for row in data['members']:
        status=row['git_status']
        if status['staged'] or status['unstaged']:raise RuntimeError('member staged/modified: '+row['member_path'])
    excluded=set({p:{'sha256':h} for p,h in PREP['protection']['excluded35_hashes'].items()})
    evidence=[]
    for row in changes['file_changes']:
        path=row['repo_path']
        if row['member_path']=='taut' and path in excluded:continue
        if (row['member_path']=='taut' and path in {'dev-docs/SwiftOneOfCheckpoint-ReviewCode-0.md','dev-docs/SwiftOneOfCheckpoint-ReviewState-0.md','dev-docs/SwiftOneOfCheckpoint-Verdict-0.md','dev-docs/SwiftOneOfCheckpoint-Acceptance-0.json'}
            and path.endswith(('.md','.json','.log')) and row['index_status']==' ' and row['worktree_status']=='?'):
            evidence.append(path);continue
        raise RuntimeError('unclassified workspace file change: '+str(row))
    return {'permitted_untracked_review_evidence':evidence,'protected_old_untracked_count':len(excluded)}

def receipt_identity():
    manifest=json.loads((REPOS['taut']/'dev-docs/examples/typescript-oneof/TypeScript-OwnedFiles.json').read_text())
    corrected=json.loads((REPOS['taut']/'dev-docs/examples/typescript-oneof/TypeScript-OwnedFiles-R1.json').read_text())
    final_hashes=dict(manifest['shape_production_sha256'],**corrected['sha256']['taut-shape-ts'])
    for name,expected in final_hashes.items():
        if digest(REPOS['shape_ts']/name)!=expected:raise RuntimeError('actual library receipt differs: '+name)
    logs={}
    for name,expected in corrected['sha256']['taut'].items():
        if '/results-r1/library-' in name:
            actual=digest(REPOS['taut']/name)
            if actual!=expected:raise RuntimeError('accepted corrected library receipt changed: '+name)
            logs[name]=actual
    lock=digest(REPOS['shape_ts']/'pnpm-lock.yaml')
    if lock!=manifest['frozen_dependency_lock_sha256']:raise RuntimeError('frozen shape dependency lock differs')
    return {'production_files_match_prior_315_typecheck_build_receipt':len(final_hashes),
      'source_tuple':EXPECTED['shape_ts'],'frozen_dependency_lock_sha256':lock,
      'association':'R0 full28 inventory overridden by accepted R1 changed11 hashes; final merged source checked against actual accepted library HEAD',
      'corrected_receipt_manifest':'dev-docs/examples/typescript-oneof/TypeScript-OwnedFiles-R1.json',
      'corrected_library_receipt_hashes':logs,
      'scope':'prior exact-source 315/typecheck/build receipts reused; no new standalone library gate; broad may execute actual composition tests'}

def baseline_source():
    proof=json.loads(Path('D:/projects/limbo/jvm-oneof-scratch/global-gate-r0/baseline-source-proof.json').read_text())
    result={}
    for name,row in proof.items():
        if name=='missing_document':continue
        actual=digest(REPOS['taut']/name);same=actual==row['baseline_sha256']
        result[name]={'current_sha256':actual,'original_baseline_sha256':row['baseline_sha256'],'identical':same}
        if name=='src/taut/gen/go.py':
            result[name]['association']='intentionally changed by current native metadata migration; not claimed baseline-identical; LF formatting regression stays enabled'
        elif not same:raise RuntimeError('baseline-relevant preserved source changed: '+name)
    path='dev-docs/TautProtoApiSurfaceExtensions.md'
    result['historical_missing_document']={'path':path,'exists_now':(REPOS['taut']/path).exists(),
        'in_settled_tree':bool(git(REPOS['taut'],'ls-tree','--name-only',EXPECTED['taut'],'--',path)),
        'prior_absence_proof':proof['missing_document']}
    return result


def raw_verify(state,phase):
    rows={}
    pair_names=PREP['owned_allowlist']
    if len(pair_names)!=45 or len(PREP['files'])!=44:raise RuntimeError('Swift inventory count mismatch')
    for name,repo in REPOS.items():
        names=sorted(set(state[name]) | (set(pair_names) if name=='taut' else set()))
        request=''.join(EXPECTED[name]+':'+p+'\n' for p in names).encode()
        data=subprocess.check_output(['git','-c','safe.directory='+repo.as_posix(),'-C',str(repo),'cat-file','--batch'],input=request)
        pos=0;rows[name]={}
        for p in names:
            end=data.index(b'\n',pos);header=data[pos:end].split();size=int(header[2]);pos=end+1
            blob=data[pos:pos+size];pos+=size+1
            expected=hashlib.sha256(blob).hexdigest();actual=digest(repo/p)
            if expected!=actual:raise RuntimeError('raw committed blob mismatch: '+name+':'+p)
            if name=='taut' and p in PREP['files'] and actual!=PREP['files'][p]['sha256']:
                raise RuntimeError('Swift frozen Preparation hash mismatch: '+p)
            rows[name][p]={'blob_sha256':expected,'actual_sha256':actual,'matches_blob':True,'swift_owned':name=='taut' and p in pair_names}
    save('raw-source-blob-'+phase+'.json',{'source_tuple':EXPECTED,'files':rows,'counts':{k:len(v) for k,v in rows.items()},'swift_owned_count':sum(r['swift_owned'] for v in rows.values() for r in v.values()),'preparation_self_bound_by_commit':True})

def main():
    global PREP
    PREP=json.loads(git(REPOS['taut'],'show',EXPECTED['taut']+':dev-docs/SwiftOneOfCheckpoint-Preparation.json'))
    before=heads()
    if before!=EXPECTED:raise RuntimeError('wrong settled tuple: '+str(before))
    status_before=workspace_status('gwz-before.json')
    state=inventory();guard=protected()
    raw_verify(state,'before');
    save('expected-tuple.json',EXPECTED);save('tuple-before.json',before);save('source-before.json',state);save('protected-before.json',guard)
    save('actual-library-receipt-scope.json',receipt_identity());save('baseline-source-proof.json',baseline_source())
    save('environment.json',{'python':sys.version,'executable':sys.executable,'pytest':__import__('pytest').__version__,
        **{k:os.environ.get(k) for k in ('TEMP','TMP','PYTHONPATH','PYTHONUTF8','PYTHONDONTWRITEBYTECODE','JAVA_TOOL_OPTIONS','PYTEST_DISABLE_PLUGIN_AUTOLOAD','GIT_OPTIONAL_LOCKS','XDG_CONFIG_HOME','GIT_CONFIG_GLOBAL','GOCACHE','GOTMPDIR','npm_config_cache')}})
    if (HERE/'global-results.json').exists() or (HERE/'broad-results.xml').exists():raise RuntimeError('single-run directory already used')
    started=time.time()
    print('PRECHECK OK: exact5HEADs; source/protected5/excluded35/locks/indices; only permitted review evidence may appear',flush=True)
    print('START all16 codec parity: require_all=True,jobs=2',flush=True)
    from taut.corpus import parity
    outcome=parity.run_gate(require_all=True,jobs=2)
    text='\n'.join(outcome.lines)+'\n';(HERE/'codec-parity.log').write_text(text,encoding='utf-8')
    save('codec-parity.json',{'reports':{n:dataclasses.asdict(r) for n,r in outcome.reports.items()},'violations':outcome.violations})
    print(text,flush=True)
    if heads()!=before or inventory()!=state or protected()!=guard:raise RuntimeError('tuple/source/protected/indices changed during parity; broad not started')
    broad=[sys.executable,'-m','pytest',str(REPOS['taut']/'src/tests'),'-q','-m','not gate','-p','no:cacheprovider','-p','collection_receipt',
           '--basetemp',str(HERE/'pytest-temp'),'--junitxml',str(HERE/'broad-results.xml'),*['--deselect='+n for n in POLICY]]
    save('commands.json',{'parity':'taut.corpus.parity.run_gate(require_all=True,jobs=2)','broad':broad,
        'policy_deselections':{n:'no enum-policy exclusions authorized' for n in POLICY},
        'baseline_failures_remain_enabled':[list(n) for n in sorted(BASELINE)],'observation_plugin':'collection_receipt.py; no collection mutation'})
    print('START ONE broad gate: only8marked duplicate parity deselections; all enum cases enabled',flush=True)
    with (HERE/'broad-regression-tests.log').open('w',encoding='utf-8') as stream:
        completed=subprocess.run(broad,cwd=HERE,stdout=stream,stderr=subprocess.STDOUT)
    after=heads();after_state=inventory();after_guard=protected();status_after=workspace_status('gwz-after.json')
    raw_verify(after_state,'after');
    save('tuple-after.json',after);save('source-after.json',after_state);save('protected-after.json',after_guard)
    xml=ET.parse(HERE/'broad-results.xml');cases=list(xml.getroot().iter('testcase'))
    failures=[];skips=[];outcomes={}
    for case in cases:
        key=(case.attrib.get('classname','').split('.')[-1],case.attrib['name']);issue=case.find('failure')
        if issue is None:issue=case.find('error')
        skipped=case.find('skipped')
        outcomes[key]='failed' if issue is not None else 'skipped' if skipped is not None else 'passed'
        if issue is not None:
            failures.append(key)
            (HERE/('failure-'+key[0]+'-'+key[1]+'.txt')).write_text((issue.attrib.get('message','')+'\n'+(issue.text or '')),encoding='utf-8')
        if skipped is not None:skips.append(dict(classname=case.attrib.get('classname'),name=case.attrib['name'],reason=skipped.attrib.get('message',''),detail=skipped.text))
    deselected=json.loads((HERE/'deselected-tests.json').read_text());selected_ids=json.loads((HERE/'selected-tests.json').read_text())
    collection=json.loads((HERE/'new-target-collection.json').read_text())
    from collection_receipt import GATES
    actual_deselected={r['nodeid'] for r in deselected};wanted_deselected=set(POLICY)|GATES
    new=sorted(set(failures)-BASELINE)
    result={'source_tuple':EXPECTED,'tuple_before':before,'tuple_after':after,'heads_unchanged':before==after,
        'source_unchanged':state==after_state,'protected_indices_locks_unchanged':guard==after_guard,
        'selected_source_counts':{k:len(v) for k,v in state.items()},'status_before':status_before,'status_after':status_after,
        'parity_variants':len(outcome.reports),'parity_violations':outcome.violations,
        'broad_command':broad,'broad_exit_code':completed.returncode,'broad_tests':len(cases),'selected_count':len(selected_ids),
        'passed':sum(c.find('failure') is None and c.find('error') is None and c.find('skipped') is None for c in cases),
        'failures':failures,'baseline_failures':sorted(set(failures)&BASELINE),'new_failures':new,
        'skipped':len(skips),'deselected':len(deselected),'deselections_unclassified':[r for r in deselected if r['reason']=='UNCLASSIFIED'],
        'exact8deselections':actual_deselected==wanted_deselected and len(deselected)==8,
        'new_target_collection':collection['selected_counts'],
        'go145_selected':collection['selected_counts']['test_go_oneof.py']==145,
        'swift116_selected':collection['selected_counts']['test_swift_oneof.py']==116,
        'swift_feature_results':{name:sum(outcomes[k]==name for k in outcomes if k[0]=='test_swift_oneof') for name in ('passed','failed','skipped')},
        'go_feature_results':{name:sum(outcomes[k]==name for k in outcomes if k[0]=='test_go_oneof') for name in ('passed','failed','skipped')},
        'fixed_jvm_help_status':outcomes.get(('test_java_oneof','test_jvm_help_describes_supported_targets_json_files_and_defaults'),'missing'),
        'elapsed_seconds':round(time.time()-started,2),'actual_library':receipt_identity()}
    save('skip-classification.json',skips);save('global-results.json',result)
    print(json.dumps(result,indent=2),flush=True)
    return int(bool(outcome.violations or len(outcome.reports)!=16 or new or state!=after_state or guard!=after_guard or before!=after
        or completed.returncode not in (0,1) or not result['exact8deselections'] or not result['go145_selected'] or not result['swift116_selected'] or result['fixed_jvm_help_status']!='passed'))

if __name__=='__main__':
    try:raise SystemExit(main())
    except Exception:
        (HERE/'ABORTED.txt').write_text(traceback.format_exc(),encoding='utf-8')
        raise
