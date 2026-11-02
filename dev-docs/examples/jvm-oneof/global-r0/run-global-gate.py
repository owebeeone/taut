"""Single read-only broad/parity gate; requires an explicitly supplied frozen tuple."""
from pathlib import Path
import argparse
import dataclasses
import hashlib
import json
import os
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

LIMBO=Path('D:/projects/limbo')
REPOS={'taut':LIMBO/'taut-dev/taut','workspace':LIMBO/'taut-dev',
       'shape_python':LIMBO/'taut-dev/taut-shape-py','shape_rust':LIMBO/'taut-dev/taut-shape-rs'}
HERE=Path(__file__).resolve().parent
BASELINE={('test_dev_docs','test_proto_api_surface_extensions_doc_exists_and_covers_contract'),
          ('test_go','test_go_runtime_and_parity_runner_are_gofmt_clean'),
          ('test_go','test_generated_go_is_gofmt_clean')}

def git(repo,*args):
    return subprocess.check_output(['git','-c','safe.directory='+str(repo),'-C',str(repo),*args],text=True,encoding='utf-8').strip()

def inventory(commit):
    root=REPOS['taut']
    paths=git(root,'ls-tree','-r','--name-only',commit).splitlines()
    selected=[p for p in paths if p.startswith(('src/','corpus/','rust/')) or p=='pyproject.toml' or (p.startswith('dev-docs/examples/') and p.endswith(('.taut.py','.kt','.java','.json')))]
    # A clean normalized diff is required before reading working bytes. Actual
    # SHA256s are also compared afterwards to catch source changes during a run.
    changed=git(root,'diff','--name-only',commit,'--','src','corpus','rust','pyproject.toml',*[p for p in selected if p.startswith('dev-docs/')])
    if changed: raise RuntimeError('Frozen source differs before/after gate: '+changed)
    return {p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in selected}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tuple',type=Path,required=True)
    args=parser.parse_args()
    expected=json.loads(args.tuple.read_text())
    before={name:git(path,'rev-parse','HEAD') for name,path in REPOS.items()}
    if before!=expected: raise RuntimeError(f'Required frozen tuple {expected}; found {before}')
    source=inventory(expected['taut'])
    (HERE/'source-before.json').write_text(json.dumps(source,indent=2)+'\n')
    (HERE/'tuple-before.json').write_text(json.dumps(before,indent=2)+'\n')
    started=time.time()
    print('Starting single all16-variant parity gate on '+expected['taut'],flush=True)
    from taut.corpus import parity
    outcome=parity.run_gate(require_all=True,jobs=2)
    parity_text='\n'.join(outcome.lines)+'\n'
    (HERE/'codec-parity.log').write_text(parity_text,encoding='utf-8')
    (HERE/'codec-parity.json').write_text(json.dumps({'violations':outcome.violations,'reports':{n:dataclasses.asdict(r) for n,r in outcome.reports.items()}},indent=2)+'\n')
    print(parity_text,flush=True)
    print('Starting broad repository regression (-m not gate); all16 gate is not duplicated by marked tests',flush=True)
    broad=[sys.executable,'-m','pytest',str(REPOS['taut']/'src/tests'),'-q','-m','not gate','-p','no:cacheprovider','--basetemp',str(HERE/'pytest-temp'),'--junitxml',str(HERE/'broad-results.xml')]
    with (HERE/'broad-regression-tests.log').open('w',encoding='utf-8') as log:
        completed=subprocess.run(broad,cwd=HERE,stdout=log,stderr=subprocess.STDOUT)
    after={name:git(path,'rev-parse','HEAD') for name,path in REPOS.items()}
    after_source=inventory(expected['taut'])
    (HERE/'source-after.json').write_text(json.dumps(after_source,indent=2)+'\n')
    (HERE/'tuple-after.json').write_text(json.dumps(after,indent=2)+'\n')
    xml=ET.parse(HERE/'broad-results.xml')
    cases=list(xml.getroot().iter('testcase'))
    failures=[]
    for case in cases:
        if case.find('failure') is not None or case.find('error') is not None:
            failures.append((case.attrib.get('classname','').split('.')[-1],case.attrib['name']))
    new_failures=sorted(set(failures)-BASELINE)
    result={'tuple':expected,'tuple_unchanged':after==before,'source_unchanged':source==after_source,
            'parity_variants':len(outcome.reports),'parity_violations':outcome.violations,
            'broad_command':broad,'broad_exit_code':completed.returncode,
            'broad_tests':len(cases),'broad_failures':failures,'new_failures':new_failures,
            'baseline_failures':sorted(set(failures)&BASELINE),
            'passed':sum(c.find('failure') is None and c.find('error') is None and c.find('skipped') is None for c in cases),
            'skipped':sum(c.find('skipped') is not None for c in cases),'elapsed_seconds':round(time.time()-started,2)}
    (HERE/'global-results.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2),flush=True)
    return int(bool(outcome.violations or len(outcome.reports)!=16 or new_failures or after!=before or source!=after_source or completed.returncode not in (0,1)))

if __name__=='__main__': raise SystemExit(main())
