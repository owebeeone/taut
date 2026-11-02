from pathlib import Path
import hashlib,json,subprocess,sys

HERE=Path(__file__).resolve().parent
ROOT=Path('D:/projects/limbo/taut-dev')
OLD=HERE.parent/'global-gate-r0'
REPOS={'taut':ROOT/'taut','workspace':ROOT,'shape_python':ROOT/'taut-shape-py','shape_rust':ROOT/'taut-shape-rs','shape_ts':ROOT/'taut-shape-ts'}
ALLOWED={'src/taut/gen/runtime/validation.hpp','src/taut/gen/runtime/go/paths.go','src/taut/gen/go_runtime.py','src/tests/test_cpp_oneof.py','src/tests/test_go_oneof.py','src/tests/test_map_gen.py','src/tests/test_scaffold.py'}
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def git(repo,*args):return subprocess.check_output(['git','-c','safe.directory='+repo.as_posix(),'-C',str(repo),*args]).decode().strip()
def capture(label):
    old=json.loads((OLD/'source-after.json').read_text())
    source={name:{p:digest(REPOS[name]/p) for p in files} for name,files in old.items()}
    changes={name:[p for p,h in files.items() if h!=old[name][p]] for name,files in source.items()}
    assert set(changes['taut'])==ALLOWED,changes
    assert all(not rows for name,rows in changes.items() if name!='taut'),changes
    oldguard=json.loads((OLD/'protected-after.json').read_text())
    guard={}
    for group in ('user_sources','excluded_python_artifacts'):
        guard[group]={p:digest(REPOS['taut']/p) for p in oldguard[group]}
    guard['indices']={}
    for name,repo in REPOS.items():
        p=Path(git(repo,'rev-parse','--git-path','index'))
        guard['indices'][name]=digest(p if p.is_absolute() else repo/p)
        assert not git(repo,'diff','--cached','--name-only'),name
    guard['locks_and_manifests']={}
    for namepath in oldguard['locks_and_manifests']:
        name,p=namepath.split(':',1)
        guard['locks_and_manifests'][namepath]=digest(REPOS[name]/p)
    assert guard==oldguard,'protected files, indices or locks differ from original gate'
    heads={name:git(repo,'rev-parse','HEAD') for name,repo in REPOS.items()}
    assert heads==json.loads((OLD/'tuple-after.json').read_text()),heads
    result={'heads':heads,'source':source,'protected':guard,'authorized_source_changes':changes['taut'],'basis':'original complete global r0 final snapshots; only seven authorized R1 source/test paths differ'}
    target=HERE/('audit-'+label+'.json')
    if target.exists():raise RuntimeError('receipt already exists: '+str(target))
    target.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    if label=='after':
        before=json.loads((HERE/'audit-before.json').read_text())
        assert result==before,'source/protected state changed during focused pair gates'
    print(json.dumps({'label':label,'source_files':sum(map(len,source.values())),'protected_user_files':len(guard['user_sources']),'excluded':len(guard['excluded_python_artifacts']),'source_changes':changes['taut'],'unchanged_during_gates':label=='after'}))
if __name__=='__main__':capture(sys.argv[1])
