"""Build a local Kotlin foundation jar from the source-bundle canonical closure.

No Maven coordinate, installer, dependency resolver or publication is involved.
Consumers explicitly put this artifact on kotlinc/java's classpath.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import zipfile

from .kotlin_runtime import FILES, OWNER, BUILD


def build_foundation(directory, *, validation=True, kotlinc=None, java=None):
    from ..corpus.toolchains import find_kotlin_tools
    if type(validation) is not bool:
        raise ValueError('Kotlin package validation option must be Boolean')
    if kotlinc is None:
        found = find_kotlin_tools()
        if found is None:
            raise ValueError('Kotlin foundation build requires configured kotlinc and java; no installation/discovery fallback')
        kotlinc, java = found
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    canonical = Path(__file__).parent / 'runtime'
    sources = {name: canonical / resource for name, resource in FILES.items()
               if validation or name != 'validation.kt'}
    # Staging is a build output, never a second maintained implementation.
    staging = directory / 'canonical-sources'
    staging.mkdir(exist_ok=True)
    for name, path in sources.items():
        shutil.copyfile(path, staging / name)
    artifact = directory / 'taut-kotlin-foundation.jar'
    completed = subprocess.run([str(kotlinc), *(str(staging / n) for n in sources),
                                '-jvm-target', '1.8', '-d', str(artifact)],
                               capture_output=True, text=True, encoding='utf-8')
    if completed.returncode:
        raise RuntimeError(f'Kotlin foundation compilation failed:\n{completed.stdout}\n{completed.stderr}')
    provenance = dict(owner=OWNER, build=BUILD, descriptor_contract=1, codec_contract=1,
                      capabilities=['codec.v1', 'descriptors.v1', 'oneof.v1'], validation=validation,
                      sources={name: hashlib.sha256(path.read_bytes()).hexdigest() for name,path in sources.items()})
    encoded = json.dumps(provenance, indent=2, sort_keys=True) + '\n'
    with zipfile.ZipFile(artifact, 'a') as jar:
        jar.writestr('META-INF/taut-kotlin-foundation.json', encoded)
    (directory / 'provenance.json').write_text(encoded, encoding='utf-8')
    return artifact


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    parser.add_argument('--without-validation', action='store_true')
    args = parser.parse_args()
    print(build_foundation(args.directory, validation=not args.without_validation))
