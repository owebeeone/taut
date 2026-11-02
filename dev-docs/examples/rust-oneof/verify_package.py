"""Build and use the local .crate artifact without registry access or publication."""
from pathlib import Path
import json
import shutil
import subprocess
import tarfile

ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).resolve().parent


def main():
    manifest=ROOT/'rust/taut-foundation/Cargo.toml'
    subprocess.run(['cargo','package','--manifest-path',str(manifest),'--offline','--allow-dirty','--no-verify'],check=True)
    artifact=ROOT/'rust/taut-foundation/target/package/taut-foundation-0.10.0.crate'
    dest=HERE/'package-artifacts';dest.mkdir(exist_ok=True)
    shutil.copy2(artifact,dest/artifact.name)
    scratch=HERE/'scratch/package-proof';scratch.mkdir(parents=True,exist_ok=True)
    with tarfile.open(artifact) as archive:
        members=archive.getnames()
        assert not any('/gen/' in n or '/compiler/' in n or 'shape' in n or n.endswith('.py') for n in members)
        archive.extractall(scratch,filter='data')
    owner=scratch/'taut-foundation-0.10.0'
    app=scratch/'app';app.mkdir(exist_ok=True)
    (app/'Cargo.toml').write_text(f'''[package]
name="packaged-foundation-proof"
version="0.0.0"
edition="2021"
[[bin]]
name="proof"
path="main.rs"
[dependencies]
taut-foundation={{path={json.dumps(owner.as_posix())},features=["validation"]}}
[workspace]
''')
    (app/'main.rs').write_text('''fn main(){
        let value=taut_foundation::cbor::Cbor::Int(42);
        assert_eq!(taut_foundation::cbor::encode(&value),vec![0x18,42]);
        let report=taut_foundation::validation::ValidationReport::default();
        assert!(report.is_valid() && report.is_complete());
        assert_eq!(taut_foundation::descriptors::DESCRIPTOR_CONTRACT,1);
        println!("extracted foundation package: codec/descriptors/reports, no compiler or shape engine PASS");
    }''')
    result=subprocess.run(['cargo','run','--quiet','--offline','--manifest-path',str(app/'Cargo.toml')],check=True,capture_output=True,text=True)
    result_data={'artifact':artifact.name,'files':members,'compiler_or_shape_dependency':False,
                 'application_output':result.stdout.strip()}
    (HERE/'results/package-verification.json').write_text(json.dumps(result_data,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(result.stdout,end='')


if __name__=='__main__':main()
