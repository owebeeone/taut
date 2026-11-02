"""Real compiler-wheel resource closure and compiler-free native applications."""
import os
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile
from taut.gen.swift_runtime import FILES

ROOT = Path(__file__).resolve().parents[2]


def checked(args, **kwargs):
    result = subprocess.run(list(map(str, args)), capture_output=True, encoding='utf-8', **kwargs)
    assert result.returncode == 0, result.stdout + result.stderr
    return result.stdout


def test_compiler_wheel_isolated_swift_source_package(tmp_path):
    import build
    source = tmp_path / 'compiler'
    shutil.copytree(ROOT / 'src/taut', source / 'src/taut', ignore=shutil.ignore_patterns('__pycache__'))
    for name in ('pyproject.toml', 'README.md', 'LICENSE'): shutil.copyfile(ROOT / name, source / name)
    env = dict(os.environ, SETUPTOOLS_SCM_PRETEND_VERSION_FOR_TAUT_PROTO='0.10.0+local.swift.probe',
               PYTHONPATH=str(Path(build.__file__).resolve().parent.parent))
    checked([sys.executable, '-m', 'build', '--wheel', '--no-isolation', '--outdir', tmp_path / 'dist'], cwd=source, env=env)
    wheel = next((tmp_path / 'dist').glob('*.whl')); unpacked = tmp_path / 'unpacked'
    with zipfile.ZipFile(wheel) as archive:
        for resource in FILES.values():
            assert archive.read('taut/gen/runtime/' + resource) == (ROOT / 'src/taut/gen/runtime' / resource).read_bytes()
        archive.extractall(unpacked)
    generated = tmp_path / 'generated'
    checked([sys.executable, '-I', '-S', '-c', '''import sys
from pathlib import Path
sys.path.insert(0,sys.argv[1])
assert Path(__import__('taut').__file__).is_relative_to(Path(sys.argv[1]))
from taut.gen.scaffold import emit
from taut.gen.swift_runtime import build_foundation
from taut.ir.dsl import Enum,F,Msg,STR,OneOf,Case,schema
root=Path(sys.argv[2]); e=Enum('K',name=0,empty=1)
s=schema(e,Record=Msg(tag=F(1,OneOf(e)),data=F(2,STR,Case(tag=e.case.name))))
emit(s,root/'source',langs=['swift'],services=[],runtime_mode='source',validation=True)
build_foundation(root/'source-built',source_directory=root/'source/swift')
package=build_foundation(root/'package-built')
emit(s,root/'package',langs=['swift'],services=[],runtime_mode='package',validation=True,
 runtime_bindings={'swift':{'module':'TautFoundation','artifact':str(package)}})
emit(s,root/'flat',langs=['swift'],services=[],validation=True)
''', unpacked, generated])
    # From here the only build inputs are emitted Swift and one compiled owner.
    # No compiler installation or Python import path participates in the app.
    native_env = dict(os.environ, PYTHONPATH='')
    for mode in ('source', 'package', 'flat'):
        directory = generated / mode; owner = generated / (mode + '-built') if mode != 'flat' else None
        main = directory / 'main.swift'
        main.write_text(('import TautFoundation\n' if owner else '') + 'var r=Record(tag:.name)\nprecondition(!r.isValid())\nr.data=""\nprecondition(r.isValid())\nlet decoded=try! Record.decode(encode(r.toCbor()))\nprecondition(decoded.isValid())\nprint("compiler-free ' + mode + ' PASS")\n')
        binary = directory / ('app.exe' if os.name == 'nt' else 'app')
        link = ['-I', owner, '-L', owner, '-lTautFoundation'] if owner else [generated / 'source/swift' / name for name in FILES]
        checked(['swiftc', *link, directory / 'swift/api.swift', main, '-o', binary], env=native_env)
        if owner:
            native_env['PATH'] = str(owner) + os.pathsep + os.environ.get('PATH', '')
            native_env['LD_LIBRARY_PATH'] = str(owner) + os.pathsep + os.environ.get('LD_LIBRARY_PATH', '')
        else:
            assert not (directory / 'swift/cbor.swift').exists()
            assert 'import TautFoundation' not in (directory / 'swift/api.swift').read_text()
        assert checked([binary], env=native_env).strip() == 'compiler-free ' + mode + ' PASS'
