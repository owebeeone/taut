"""Regenerate/run Java source, local package and engine-free examples. No install/publish."""
from pathlib import Path
import hashlib
import json
import shutil
import subprocess
import tempfile
from taut.gen.scaffold import emit
from taut.gen.java_runtime import build_foundation,canonical_sources,verify_artifact
from taut.ir.load import load_schema

ROOT=Path(__file__).resolve().parent
RESULTS=ROOT/'results'

def checked(args):
    r=subprocess.run(list(map(str,args)),capture_output=True,encoding='utf-8')
    if r.returncode:raise RuntimeError(r.stdout+r.stderr)
    return r.stdout

def main():
    RESULTS.mkdir(exist_ok=True)
    schema=load_schema(ROOT/'content.taut.py')
    with tempfile.TemporaryDirectory(prefix='taut-java-examples-') as temp:
        scratch=Path(temp)
        artifact=build_foundation(scratch/'foundation.jar')
        inventory=verify_artifact(artifact)
        (RESULTS/'package-provenance.json').write_text(json.dumps(inventory,indent=2,sort_keys=True)+'\n',encoding='utf-8')
        outputs={}
        for mode in ('source','package'):
            output=scratch/mode
            emit(schema,output,langs=['java'],services=[],runtime_mode=mode,validation=True,
                 runtime_bindings={'java':{'artifact':str(artifact)}} if mode=='package' else None)
            directory=output/'java';shutil.copyfile(ROOT/'Conformance.java',directory/'Conformance.java')
            classes=output/'classes';classes.mkdir()
            deps=[] if mode=='source' else ['-cp',str(artifact)]
            checked(['javac','--release','8','-encoding','UTF-8','-d',classes,*deps,*sorted(directory.rglob('*.java'))])
            cp=str(classes) if mode=='source' else str(classes)+__import__('os').pathsep+str(artifact)
            outputs[mode]=checked(['java','-cp',cp,'taut.Conformance'])
            (RESULTS/(mode+'-reports.tsv')).write_text(outputs[mode],encoding='utf-8')
            if mode=='source':
                (ROOT/'enabled.golden.java').write_bytes((directory/'api.java').read_bytes())
        assert outputs['source']==outputs['package']
        output=scratch/'disabled'
        emit(schema,output,langs=['java'],services=[],runtime_mode='source')
        directory=output/'java'
        (ROOT/'disabled.golden.java').write_bytes((directory/'api.java').read_bytes())
        (directory/'Inspect.java').write_text('package taut; public class Inspect{public static void main(String[]a){System.out.println(Content.descriptor().fields().size());Content v=new Content();v.kind=Kind.EMPTY;System.out.println(Cbor.encode(v.toCbor()).length>0);}}',encoding='utf-8')
        shutil.copyfile(ROOT/'AdapterProbe.java',directory/'AdapterProbe.java')
        classes=output/'classes';classes.mkdir()
        checked(['javac','--release','8','-encoding','UTF-8','-d',classes,*sorted(directory.rglob('*.java'))])
        (RESULTS/'disabled.log').write_text(checked(['java','-cp',classes,'taut.Inspect']),encoding='utf-8')
        (RESULTS/'adapter-probe.log').write_text(checked(['java','-cp',classes,'taut.AdapterProbe']),encoding='utf-8')
        assert not (classes/'taut/validation/ValidationEngine.class').exists()
    (RESULTS/'runtime-inventory.json').write_text(json.dumps({n:hashlib.sha256(v).hexdigest() for n,v in canonical_sources().items()},indent=2,sort_keys=True)+'\n',encoding='utf-8')
    print('Java source/package conformance: identical reports; Java8 compile/run PASS; disabled descriptors/codecs without engine PASS')

if __name__=='__main__':main()
