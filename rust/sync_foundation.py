"""Derive the lightweight local crate from canonical compiler runtime resources."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'src/taut/gen/runtime'
TARGET = ROOT / 'rust/taut-foundation'
FILES = {'cbor.rs':'cbor_fail_closed.rs', 'ext.rs':'ext.rs',
         'descriptors.rs':'descriptors.rs', 'validation.rs':'validation.rs'}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check',action='store_true')
    args=parser.parse_args()
    provenance={'owner':'taut.rust.foundation','descriptor_contract':1,'codec_contract':1,
                'generator_build':'rust-oneof-reference.1','sources':{}}
    stale=[]
    for name,source in FILES.items():
        data=(SOURCE/source).read_bytes()
        target=TARGET/'src'/name
        provenance['sources']['src/'+name]={'canonical':(SOURCE/source).relative_to(ROOT).as_posix(),
                                          'sha256':hashlib.sha256(data).hexdigest()}
        if args.check:
            if not target.exists() or target.read_bytes()!=data: stale.append(str(target))
        else:
            target.parent.mkdir(parents=True,exist_ok=True)
            target.write_bytes(data)
    target=TARGET/'provenance.json'
    data=(json.dumps(provenance,indent=2,sort_keys=True)+'\n').encode()
    if args.check:
        if not target.exists() or target.read_bytes()!=data: stale.append(str(target))
    else:
        target.write_bytes(data)
    if stale: parser.exit(1,'stale foundation sources: '+', '.join(stale)+'\n')
    print('canonical Rust foundation source inventory matches' if args.check else 'derived Rust foundation crate refreshed')


if __name__=='__main__': main()
