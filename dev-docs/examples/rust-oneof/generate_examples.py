"""Generate, compile and run the real Rust source/package/descriptor-only routes."""
from pathlib import Path
import json
import subprocess
import sys
import argparse

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'src'))
from taut.gen.scaffold import emit,rust_api
from taut.ir.load import load_schema
from taut.wire import jsoncodec

HERE=Path(__file__).resolve().parent
SCHEMA=ROOT/'dev-docs/examples/python-oneof/content.taut.py'


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--update-goldens',action='store_true')
    args=parser.parse_args()
    s=load_schema(SCHEMA)
    if args.update_goldens:
        goldens=HERE/'goldens';goldens.mkdir(exist_ok=True)
        for mode in ('source','package'):
            for enabled in (False,True):
                (goldens/f'{mode}-{"on" if enabled else "off"}.rs').write_text(
                    rust_api(s,validation=enabled,runtime_path='taut_foundation' if mode=='package' else 'crate'),encoding='utf-8',newline='\n')
    for mode in ('source','package','disabled'):
        directory=HERE/'generated'/mode
        enabled=mode!='disabled'
        emit(s,directory,langs=['rust'],services=[],runtime_mode='package' if mode=='package' else 'source',validation=enabled)
        d=directory/'rust'
        if mode=='package':
            prelude='extern crate alloc; mod api; use taut_foundation as foundation;\n'
            deps=f'[dependencies]\ntaut-foundation={{path={json.dumps((ROOT/"rust/taut-foundation").as_posix())},features=["validation"]}}\n'
        else:
            prelude='extern crate alloc; pub mod cbor; pub use cbor::descriptors; '+('pub mod validation; ' if enabled else '')+'mod api; use crate as foundation;\n'
            deps=''
        body=(HERE/'main.rs').read_text() if enabled else '''fn main(){
            let value=api::Content{kind:api::ContentKind::Empty,..Default::default()};
            let bytes=foundation::cbor::encode(&value.to_cbor());
            assert_eq!(api::Content::decode(&bytes).unwrap(),value);
            println!("descriptor-only: {} fields; validation engine absent",api::Content::descriptor().fields().len());
        }'''
        (d/'main.rs').write_text(prelude+body,encoding='utf-8',newline='\n')
        (directory/'Cargo.toml').write_text(f'[package]\nname="taut-oneof-{mode}-example"\nversion="0.0.0"\nedition="2021"\n[[bin]]\nname="inspect"\npath="rust/main.rs"\n{deps}\n[workspace]\n',encoding='utf-8',newline='\n')
        result=subprocess.run(['cargo','run','--quiet','--offline','--manifest-path',str(directory/'Cargo.toml')],check=True,text=True,capture_output=True)
        results=HERE/'results';results.mkdir(exist_ok=True)
        (results/f'{mode}-examples.log').write_text(result.stdout,encoding='utf-8',newline='\n')
        print(f'=== {mode} ===\n{result.stdout}',end='')
        if enabled:
            encoded=next(line.split('=',1)[1] for line in result.stdout.splitlines() if line.startswith('draft_cbor='))
            wire=bytes.fromhex(encoded)
            text=jsoncodec.cbor_to_json(s,'Content',wire)
            assert json.loads(text)=={'kind':'number','text':'extra'}
            (results/'invalid-draft.cbor').write_bytes(wire)
            (results/'invalid-draft.json').write_text(text+'\n',encoding='utf-8',newline='\n')
    print('Rust CBOR -> existing Taut JSON bridge preserves the populated invalid payload:',text)


if __name__=='__main__': main()
