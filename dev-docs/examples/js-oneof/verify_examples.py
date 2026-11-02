"""Local source/package examples and canonical-byte proof; no installation/publication."""
from pathlib import Path
import hashlib
import json
import subprocess
import tarfile
import tempfile
from taut.gen.scaffold import emit
from taut.gen.js_runtime import build_foundation, canonical_sources, verify_artifact
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
    with tempfile.TemporaryDirectory(prefix='taut-js-examples-') as temp:
        scratch=Path(temp);artifact=build_foundation(scratch/'foundation.tgz')
        provenance=verify_artifact(artifact)
        owner=scratch/'package'
        with tarfile.open(artifact) as archive:
            for member in archive.getmembers():
                target=scratch/member.name;target.parent.mkdir(parents=True,exist_ok=True)
                target.write_bytes(archive.extractfile(member).read())
        for name,data in canonical_sources().items():assert (owner/name).read_bytes()==data
        outputs={}
        for mode in ('source','package'):
            output=scratch/mode
            bindings={'js':{'module':str(owner).replace('\\','/'),'artifact':str(artifact)}} if mode=='package' else None
            emit(schema,output,langs=['js'],services=[],runtime_mode=mode,validation=True,runtime_bindings=bindings)
            d=output/'js';codec=(d if mode=='source' else owner)/'cbor.js'
            outputs[mode]=checked(['node',ROOT/'conformance.js',d/'api.js',codec])
            (RESULTS/(mode+'-reports.tsv')).write_text(outputs[mode],encoding='utf-8')
            (RESULTS/(mode+'-example.log')).write_text(checked(['node',ROOT/'example.js',d/'api.js',codec]),encoding='utf-8')
            if mode=='source':
                (ROOT/'enabled.golden.js').write_bytes((d/'api.js').read_bytes())
                for name,data in canonical_sources().items():assert (d/name).read_bytes()==data
        assert outputs['source']==outputs['package']
        emit(schema,scratch/'off',langs=['js'],services=[],runtime_mode='source')
        d=scratch/'off/js';assert not (d/'validation.js').exists()
        (ROOT/'disabled.golden.js').write_bytes((d/'api.js').read_bytes())
        code='const a=require('+json.dumps(str(d/'api.js'))+');if(a.Content.descriptor()!==a.ContentDescriptor)throw Error("identity");if(typeof a.Content.prototype.validate!=="undefined")throw Error("methods");if(Object.keys(require.cache).some(k=>k.endsWith("validation.js")))throw Error("engine");console.log("engine-free descriptors PASS");'
        (RESULTS/'disabled.log').write_text(checked(['node','-e',code]),encoding='utf-8')
        (RESULTS/'package-provenance.json').write_text(json.dumps(provenance,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    (RESULTS/'canonical-inventory.json').write_text(json.dumps({n:hashlib.sha256(v).hexdigest() for n,v in canonical_sources().items()},indent=2,sort_keys=True)+'\n',encoding='utf-8')
    print('JavaScript source/package reports identical; Node codecs and validation PASS; engine-free descriptors PASS; npm pack canonical-byte provenance PASS')


if __name__=='__main__':main()
