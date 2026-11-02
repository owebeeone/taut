"""Build/extract a local TypeScript foundation artifact; never install or publish."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import tarfile
from .typescript_runtime import OWNER, BUILD, CAPABILITIES, canonical_sources


def build_foundation(directory, *, validation=True, tsc='tsc', node='node'):
    directory=Path(directory)
    if directory.exists() and any(directory.iterdir()):
        raise ValueError(f'{directory}: local package build requires a fresh directory')
    package=directory/'package'; source=package/'canonical-sources'; common=package/'cjs'; esm=package/'esm'
    source.mkdir(parents=True); esm.mkdir()
    sources=canonical_sources(validation=validation)
    for name,content in sources.items(): (source/name).write_bytes(content)
    config={'compilerOptions':{'target':'ES2022','module':'commonjs','strict':True,'skipLibCheck':True,
            'declaration':True,'rewriteRelativeImportExtensions':True,'outDir':'../cjs','lib':['ES2022','DOM']},'include':['*.ts']}
    (source/'tsconfig.json').write_text(json.dumps(config))
    compiler=shutil.which(str(tsc)) or str(tsc)
    result=subprocess.run([compiler,'--project',str(source/'tsconfig.json')],capture_output=True,text=True,encoding='utf-8')
    if result.returncode: raise RuntimeError(f'TypeScript foundation compile failed:\n{result.stdout}\n{result.stderr}')
    (common/'package.json').write_text('{"type":"commonjs"}\n')
    exports={}
    for filename in sources:
        name=Path(filename).stem
        # ESM is a facade over CJS, never a second evaluation of the implementation.
        result=subprocess.run([str(node),'-e','process.stdout.write(JSON.stringify(Object.keys(require(process.argv[1]))))',str((common/(name+'.js')).absolute())],capture_output=True,text=True)
        if result.returncode: raise RuntimeError(result.stderr)
        names=json.loads(result.stdout)
        if any(not re.fullmatch(r'[A-Za-z_$][A-Za-z0-9_$]*',n) for n in names): raise ValueError('invalid foundation export')
        facade='import owner from "../cjs/'+name+'.js";\n'+''.join('export const '+n+' = owner.'+n+';\n' for n in names)
        (esm/(name+'.js')).write_text(facade,encoding='utf-8')
        # Declarations refer to the canonical CJS declarations; type and runtime owners agree.
        (esm/(name+'.d.ts')).write_text('export * from "../cjs/'+name+'.js";\n')
        exports['.' if name=='foundation' else './'+name]={'types':'./cjs/'+name+'.d.ts','import':'./esm/'+name+'.js','require':'./cjs/'+name+'.js'}
    exports['./foundation']=exports['.']
    if validation: exports['./foundation/validation']=exports['./validation']
    manifest={'name':'@owebeeone/taut-shape','version':'0.0.0','private':True,'type':'module','exports':exports,
              'main':'./cjs/foundation.js','types':'./cjs/foundation.d.ts'}
    (package/'package.json').write_text(json.dumps(manifest,indent=2)+'\n')
    provenance=dict(owner=OWNER,build=BUILD,descriptor_contract=1,codec_contract=1,capabilities=sorted(CAPABILITIES),validation=validation,
                    sources={name:hashlib.sha256(content).hexdigest() for name,content in sources.items()})
    provenance['files']={p.relative_to(package).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in package.rglob('*') if p.is_file()}
    (package/'provenance.json').write_text(json.dumps(provenance,indent=2,sort_keys=True)+'\n')
    artifact=directory/'taut-typescript-foundation.tgz'
    with tarfile.open(artifact,'w:gz') as archive: archive.add(package,arcname='package')
    verify_artifact(artifact,validation=validation)
    return artifact


def verify_artifact(path, *, validation=False):
    path=Path(path)
    try:
        with tarfile.open(path,'r:gz') as archive:
            files={m.name:archive.extractfile(m).read() for m in archive.getmembers() if m.isfile()}
        p=json.loads(files['package/provenance.json'])
        if (p['owner']!=OWNER or type(p['descriptor_contract']) is not int or p['descriptor_contract']!=1
            or type(p['codec_contract']) is not int or p['codec_contract']!=1 or set(p['capabilities'])!=CAPABILITIES
            or (validation and not p['validation'])): raise ValueError('incompatible contracts/capabilities')
        for name,digest in p['files'].items():
            if hashlib.sha256(files['package/'+name]).hexdigest()!=digest: raise ValueError('artifact content/provenance mismatch: '+name)
        for name,digest in p['sources'].items():
            if hashlib.sha256(files['package/canonical-sources/'+name]).hexdigest()!=digest: raise ValueError('canonical source provenance mismatch: '+name)
        required={'foundation','descriptors','reports','cbor','codec','schema','jsoncodec','ext'}|({'validation'} if validation else set())
        if any('package/cjs/'+n+'.js' not in files for n in required): raise ValueError('missing package runtime exports')
        return p
    except (OSError,tarfile.TarError,KeyError,TypeError,ValueError) as exc:
        raise ValueError(f'{path}: incompatible TypeScript foundation artifact: {exc}; rebuild/rebind') from exc


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory',type=Path,metavar='OUTPUT',help='fresh output directory for the local foundation artifact')
    parser.add_argument('--without-validation',action='store_true',help='build a descriptor/codec-only artifact; validation is included by default')
    args=parser.parse_args()
    print(build_foundation(args.directory,validation=not args.without_validation))
