"""Build a local compiler wheel, verify real package data, generate/compile/run both JVM targets."""
import os
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile
import pytest
from taut.gen.java_runtime import FILES as JAVA_FILES
from taut.gen.kotlin_runtime import FILES as KOTLIN_FILES

ROOT=Path(__file__).resolve().parents[2]
RUNTIME=ROOT/'src/taut/gen/runtime'


def checked(args,**kwargs):
    r=subprocess.run(list(map(str,args)),capture_output=True,encoding='utf-8',**kwargs)
    assert r.returncode==0,r.stdout+r.stderr
    return r.stdout


def test_compiler_wheel_contains_exact_jvm_closures_and_generates_usable_sources(tmp_path):
    import importlib.util
    if importlib.util.find_spec('build') is None:
        pytest.fail('Use the existing Python3.11 build environment from toolchain readiness; no dependency installation is needed')
    source=tmp_path/'compiler'
    shutil.copytree(ROOT/'src/taut',source/'src/taut',ignore=shutil.ignore_patterns('__pycache__'))
    for name in ('pyproject.toml','README.md','LICENSE'):
        shutil.copyfile(ROOT/name,source/name)
    env=dict(os.environ,SETUPTOOLS_SCM_PRETEND_VERSION_FOR_TAUT_PROTO='0.10.0+local.jvm.probe')
    checked([sys.executable,'-m','build','--wheel','--no-isolation','--outdir',tmp_path/'dist'],cwd=source,env=env)
    wheel=next((tmp_path/'dist').glob('*.whl'))
    unpacked=tmp_path/'unpacked'
    with zipfile.ZipFile(wheel) as archive:
        for resource in set(JAVA_FILES.values())|set(KOTLIN_FILES.values()):
            assert archive.read('taut/gen/runtime/'+resource)==(RUNTIME/resource).read_bytes(),resource
        archive.extractall(unpacked)
    generated=tmp_path/'generated'
    code='''import sys
from pathlib import Path
sys.path.insert(0,sys.argv[1])
from taut.gen.scaffold import emit
from taut.ir.dsl import *
assert Path(__import__('taut').__file__).is_relative_to(Path(sys.argv[1]))
e=Enum('Choice',yes=0,no=1)
s=schema(e,Record=Msg(kind=F(1,OneOf(e)),text=F(2,STR,Case(kind=e.yes))))
emit(s,Path(sys.argv[2]),langs=['java','kotlin'],services=[],runtime_mode='source',validation=True)
'''
    checked([sys.executable,'-I','-S','-c',code,unpacked,generated])
    java=generated/'java'
    (java/'WheelProbe.java').write_text('package taut; public class WheelProbe{public static void main(String[]a){Record r=new Record();r.kind=Choice.YES;if(r.isValid() || !r.validate().issues().get(0).code().equals("oneof.payload_missing"))throw new AssertionError();r.text="";if(!r.isValid())throw new AssertionError();System.out.println("wheel-java PASS");}}',encoding='utf-8')
    classes=tmp_path/'classes';classes.mkdir()
    checked(['javac','--release','8','-encoding','UTF-8','-d',classes,*sorted(java.rglob('*.java'))])
    assert 'PASS' in checked(['java','-cp',classes,'taut.WheelProbe'])
    kotlin=generated/'kotlin'
    (kotlin/'WheelProbe.kt').write_text('package taut\nfun main(){val r=Record(Choice.yes);check(!r.isValid());check(r.validate().issues[0].code=="oneof.payload_missing");r.text="";check(r.isValid());println("wheel-kotlin PASS")}\n',encoding='utf-8')
    compiler=os.environ.get('KOTLINC') or shutil.which('kotlinc')
    assert compiler,'Use the existing toolchain readiness Kotlin compiler'
    jar=tmp_path/'kotlin.jar'
    checked([compiler,*sorted(kotlin.rglob('*.kt')),'-jvm-target','1.8','-include-runtime','-d',jar])
    assert 'PASS' in checked(['java','-cp',jar,'taut.WheelProbeKt'])
