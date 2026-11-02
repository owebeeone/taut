"""Explicit generation/build demonstration; applications contain only Swift.

Run from an activated shell with --out pointing to a fresh owned directory.
No package installation, publication or target discovery occurs.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
from taut.gen.scaffold import emit
from taut.gen.swift_runtime import build_foundation, canonical_sources
from taut.ir.load import load_schema

HERE = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--out', required=True)
    args = parser.parse_args()
    from taut.gen.python_runtime import validate_namespace_path
    validate_namespace_path(args.out)
    root = Path(args.out).absolute()
    if root.exists() and any(root.iterdir()): raise ValueError('choose a fresh output directory')
    root.mkdir(parents=True, exist_ok=True)
    schema = load_schema(HERE / 'content.taut.py')
    package = build_foundation(root / 'package-foundation')
    receipt = {}
    def execute(directory, native, sources, owner=None):
        directory.mkdir(parents=True, exist_ok=True)
        main = directory / 'main.swift'; main.write_text(native, encoding='utf-8')
        binary = directory / ('app.exe' if os.name == 'nt' else 'app')
        command = ['swiftc', *(['-I', str(owner), '-L', str(owner), '-lTautFoundation'] if owner else []),
                   *map(str, sources), str(main), '-o', str(binary)]
        compiled = subprocess.run(command, capture_output=True, text=True)
        if compiled.returncode: raise RuntimeError(compiled.stderr)
        env = dict(os.environ)
        for name in ('PATH', 'LD_LIBRARY_PATH'):
            env[name] = (str(owner) + os.pathsep if owner else '') + env.get(name, '')
        result = subprocess.run([str(binary)], capture_output=True, text=True, env=env)
        if result.returncode: raise RuntimeError(result.stdout + result.stderr)
        return dict(command=command, exit=0, stdout=result.stdout,
                    api_sha256={str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources})
    for mode in ('source', 'package', 'supplied'):
        directory = root / mode
        binding = {'swift': {'module': 'TautFoundation', 'artifact': str(package)}} if mode != 'source' else None
        emit(schema, directory, langs=['swift'], services=[], runtime_mode=None if mode == 'supplied' else mode,
             validation=True, runtime_bindings=binding)
        owner = build_foundation(root / 'source-foundation', source_directory=directory / 'swift') if mode == 'source' else package
        receipt[mode] = execute(directory / 'app', (HERE / 'Conformance.swift').read_text(), [directory / 'swift/api.swift'], owner)
        assert receipt[mode]['stdout'] == (HERE / 'expected.tsv').read_text()
    # Default supplied mode retains the original flat application-module route.
    # The exact same canonical bytes are compiled once, with no imported owner.
    for enabled in (False, True):
        directory = root / ('flat-on' if enabled else 'flat-off')
        emit(schema, directory, langs=['swift'], services=[], validation=enabled)
        supplied = directory / 'supplied'; supplied.mkdir()
        for name, content in canonical_sources(validation=enabled).items(): (supplied / name).write_bytes(content)
        native = 'let draft=Content(kind:.text)\nprecondition(Content.descriptor.fields.count == 6)\nprecondition(Content.schemaDescriptor.messages.count == 5)\n'
        if enabled: native += 'let report:ValidationReport=draft.validate()\nprecondition(!report.isValid && !draft.isValid())\ndraft.text=""\nprecondition(draft.isValid())\n'
        native += 'precondition(try! Content.decode(encode(draft.toCbor())).kind == .text)\nprint("flat supplied PASS")\n'
        receipt[directory.name] = execute(directory / 'app', native, [*supplied.glob('*.swift'), directory / 'swift/api.swift'])
    (root / 'results.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print('PASS: source, package, explicitly imported supplied, default flat supplied OFF/ON (five native executions)')


if __name__ == '__main__': main()
