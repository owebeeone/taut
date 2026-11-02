"""Generate, compile and run the same example against source and local jar delivery."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import subprocess

from taut.corpus.toolchains import find_kotlin_tools
from taut.gen.scaffold import emit
from taut.gen.kotlin_package import build_foundation
from taut.gen.kotlin_runtime import FILES
from taut.ir.load import load_schema

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,required=True,help='fresh local build output')
    args=parser.parse_args()
    out=args.out.resolve()
    kotlinc,java=find_kotlin_tools() or (None,None)
    if kotlinc is None: raise SystemExit('configure the installed kotlinc/JDK before running')
    schema=load_schema(HERE.parent/'python-oneof/content.taut.py')
    artifact=build_foundation(out/'foundation',kotlinc=kotlinc,java=java)
    outputs={}
    for mode in ('source','package'):
        target=out/mode
        emit(schema,target,langs=['kotlin'],services=[],validation=True,runtime_mode=mode,
             schema_identity='kotlin-oneof-example')
        sources=sorted((target/'kotlin').glob('*.kt'))
        arguments=[*sources,HERE/'Example.kt','-jvm-target','1.8','-include-runtime','-d',target/'example.jar']
        if mode=='package': arguments += ['-classpath',artifact]
        argfile=target/'compile.args'
        argfile.write_text('\n'.join(json.dumps(str(a).replace('\\','/')) for a in arguments),encoding='utf-8')
        subprocess.run([kotlinc,'@'+str(argfile)],check=True)
        cp=[target/'example.jar']+([artifact] if mode=='package' else [])
        result=subprocess.run([java,'-cp',os.pathsep.join(map(str,cp)),'ExampleKt'],check=True,capture_output=True,text=True,encoding='utf-8')
        outputs[mode]=result.stdout
        print(mode+':\n'+result.stdout)
    assert outputs['source']==outputs['package']
    receipt=dict(outputs=outputs,canonical={n:hashlib.sha256((ROOT/'src/taut/gen/runtime'/r).read_bytes()).hexdigest() for n,r in FILES.items()},
                 owner='taut.kotlin.foundation',descriptor_contract=1,codec_contract=1,jvm_target='1.8')
    (out/'results.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')


if __name__=='__main__': main()
