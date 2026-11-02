from pathlib import Path
import hashlib, json, os, subprocess, sys, time

root = Path('D:/projects/limbo/taut-dev')
scratch = Path('D:/projects/limbo/ecma-oneof-scratch/remediation-r1/shared')
r0 = json.loads(Path('D:/projects/limbo/ecma-oneof-scratch/frozen-r0/snapshot.json').read_text())

def digest(p):
    data = p.read_bytes()
    return {'sha256': hashlib.sha256(data).hexdigest(), 'size': len(data)}

def git(repo, *args):
    p = root / repo
    return subprocess.check_output(['git', '-c', 'safe.directory=' + p.as_posix(), '-C', str(p), *args], text=True)

def capture():
    result = {'refs': {}, 'files': {}, 'protected': {}, 'excluded': {}, 'indices': {}}
    for repo in ('taut', 'taut-shape-ts'):
        result['refs'][repo] = git(repo, 'rev-parse', 'HEAD').strip()
        paths = set(r0['files'][repo])
        paths.update(git(repo, 'diff', '--name-only').splitlines())
        paths.update(git(repo, 'ls-files', '--others', '--exclude-standard').splitlines())
        paths.difference_update(r0['excluded']['files'] if repo == 'taut' else ())
        # Reports may be updated while checks run; source and test bytes may not.
        paths = {p for p in paths if not p.startswith('dev-docs/')}
        result['files'][repo] = {p: digest(root/repo/p) for p in sorted(paths)}
        result['indices'][repo] = git(repo, 'diff', '--cached', '--name-only').splitlines()
    for p, expected in r0['preserved_user']['monitored_sources'].items():
        actual = digest(root/'taut'/p)
        assert actual['sha256'] == expected['sha256'], ('protected source changed', p)
        result['protected'][p] = actual
    for p, expected in r0['excluded']['files'].items():
        actual = digest(root/'taut'/p)
        assert actual == expected, ('excluded artifact changed', p)
        result['excluded'][p] = actual
    lock = root/'taut-shape-ts/pnpm-lock.yaml'
    result['lock'] = digest(lock)
    assert result['lock']['sha256'] == 'e110b44300bc75e28489500b7d2165b27414e2c6283853d7e4220b5fc27e06db'
    assert not any(result['indices'].values()), result['indices']
    return result

before = capture()
(scratch/'affected-before.json').write_text(json.dumps(before, indent=2, sort_keys=True)+'\n')
tests = ['src/tests/'+name for name in (
    'test_js_oneof.py', 'test_js_ts_distribution.py', 'test_js.py',
    'test_scaffold.py', 'test_cli.py', 'test_reserved_names.py')]
tests.append('src/tests/test_java_oneof.py::test_jvm_help_describes_supported_targets_json_files_and_defaults')
command = [sys.executable, '-m', 'pytest', *tests, '-q', '--tb=short',
           '--junitxml='+str(scratch/'affected.xml')]
start = time.time()
with (scratch/'affected.log').open('w', encoding='utf-8') as log:
    completed = subprocess.run(command, cwd=root/'taut', stdout=log, stderr=subprocess.STDOUT)
after = capture()
(scratch/'affected-after.json').write_text(json.dumps(after, indent=2, sort_keys=True)+'\n')
assert before == after, 'Source, index, protected files or references changed during affected gate'
receipt = {'command': command, 'cwd': str(root/'taut'), 'exit_code': completed.returncode,
           'elapsed_seconds': time.time()-start, 'source_stable': before == after,
           'environment': {k: os.environ.get(k) for k in ('PYTHONPATH', 'PYTEST_DISABLE_PLUGIN_AUTOLOAD')},
           'python': sys.version, 'scope': 'JS/shared affected gate plus complete existing JVM help test; not broad/all16'}
(scratch/'affected-receipt.json').write_text(json.dumps(receipt, indent=2, sort_keys=True)+'\n')
print(json.dumps(receipt, indent=2))
print((scratch/'affected.log').read_text()[-1800:])
raise SystemExit(completed.returncode)
