"""Swift module delivery from canonical resources and the shared ownership kernel."""
from __future__ import annotations
import json
import os
from pathlib import Path
import re
import sys
from . import go_runtime as _paths
from .python_runtime import _is_alias

OWNER = 'taut.swift.foundation'
BUILD = 'swift-oneof-reference.1'
TARGET = 'swift'
LABEL = 'Swift'
CAPABILITIES = {'codec.v1', 'descriptors.v1', 'oneof.v1'}
FILES = {'cbor.swift': 'cbor.swift', 'ext.swift': 'ext.swift',
         **{name + '.swift': 'swift/' + name + '.swift' for name in ('paths', 'descriptors', 'reports', 'validation')}}
VALIDATION_FILES = {'reports.swift', 'validation.swift'}
digest, encoded = _paths.digest, _paths.encoded


def _path_call(function, *args, **kwargs):
    try:
        return function(*args, **kwargs)
    except ValueError as exc:
        raise ValueError(str(exc).replace('Go ', 'Swift ')) from exc


def canonical_path(value, *, directory=True):
    return _path_call(_paths.canonical_path, value, directory=directory)


def user_identity(value):
    return _path_call(_paths.user_identity, value)


def remaining_users(users, current_user):
    return _path_call(_paths.remaining_users, users, current_user)


def module_name(value):
    from .swift import _SWIFT_KEYWORDS, is_identifier
    if not is_identifier(value):
        raise ValueError(f'invalid explicit Swift module name {value!r}')
    if value in _SWIFT_KEYWORDS:
        raise ValueError(f'invalid Swift keyword module name {value!r}')
    return value


def binding(bindings, directory, mode, *, validation=False):
    config = dict((bindings or {}).get('swift', {}))
    allowed = {'owner', 'module', 'source_root', 'artifact', 'descriptor_contract', 'codec_contract', 'capabilities'}
    if config.keys() - allowed:
        raise ValueError(f'unknown Swift runtime binding keys {sorted(config.keys()-allowed)}')
    caps = config.get('capabilities', sorted(CAPABILITIES))
    if (config.get('owner', OWNER) != OWNER or type(config.get('descriptor_contract', 1)) is not int
        or config.get('descriptor_contract', 1) != 1 or type(config.get('codec_contract', 1)) is not int
        or config.get('codec_contract', 1) != 1 or not isinstance(caps, (list, tuple, set))
        or set(caps) != CAPABILITIES):
        raise ValueError(f'Swift requires owner={OWNER}, descriptor=1 codec=1 capabilities={sorted(CAPABILITIES)}; regenerate/rebind')
    if mode == 'package' and not config.get('module'):
        raise ValueError('Swift package mode requires explicit module binding to the application-supplied foundation; no package is discovered or installed')
    module = config.get('module', 'TautFoundation' if mode == 'source' else '')
    if module:
        module_name(module)
    elif not isinstance(module, str) or mode is not None:
        raise ValueError('Swift source/package module must be an explicit valid module name')
    source_root = canonical_path(config.get('source_root', directory))
    if 'artifact' in config:
        verify_artifact(config['artifact'], module, validation=validation)
    return module, source_root, 'source_root' in config


def canonical_sources(*, validation=True):
    canonical = Path(__file__).parent / 'runtime'
    return {name: (canonical / resource).read_bytes() for name, resource in FILES.items()
            if validation or name not in VALIDATION_FILES}


def runtime_imports(texts):
    # Generated provenance names the selected foundation, independently of child imports.
    return {name for text in texts.values() for name in re.findall(r'^// taut-foundation-module: ([^\r\n]*)$', text, re.M)}


def manifest(path, kind):
    from .owned_runtime import manifest as owned_manifest
    return owned_manifest(sys.modules[__name__], path, kind)


def plan_outputs(directory, texts, *, mode, validation, source_root, consume_source=False, external=False):
    from .owned_runtime import plan_outputs as plan_owned_outputs
    return plan_owned_outputs(sys.modules[__name__], directory, texts, mode=mode,
        validation=validation, source_root=source_root, consume_source=consume_source, external=external)


def build_foundation(destination, module='TautFoundation', *, validation=True, source_directory=None):
    """Explicit local compiler/tooling operation; never called by schema emission."""
    import subprocess
    root = canonical_path(destination)
    module = module_name(module)
    if root.exists() and any(root.iterdir()):
        raise ValueError(f'Swift foundation destination must be empty: {root}')
    root.mkdir(parents=True, exist_ok=True)
    sources = canonical_sources(validation=validation)
    if source_directory is not None:
        source = canonical_path(source_directory)
        sources = {name: (source / name).read_bytes() for name in sources}
    for name, content in sources.items():
        (root / name).write_bytes(content)
    library = root / (module + '.dll' if os.name == 'nt' else 'lib' + module + '.so')
    result = subprocess.run(['swiftc', '-emit-library', '-emit-module', '-module-name', module,
        *map(str, (root / name for name in sources)), '-o', str(library),
        '-emit-module-path', str(root / (module + '.swiftmodule'))], capture_output=True, text=True)
    if result.returncode:
        raise ValueError('Swift foundation compile failed:\n' + result.stderr)
    inventory = {p.name: digest(p.read_bytes()) for p in root.iterdir() if p.is_file()}
    (root / '.taut-swift-foundation.json').write_bytes(encoded(dict(owner=OWNER, descriptor=1, codec=1,
        capabilities=sorted(CAPABILITIES), build=BUILD, module=module, validation=validation, files=inventory)))
    verify_artifact(root, module, validation=validation)
    return root


def verify_artifact(path, module, *, validation=False):
    root = canonical_path(path)
    module_name(module)
    try:
        if _is_alias(root / '.taut-swift-foundation.json'):
            raise ValueError('aliased Swift foundation provenance')
        data = json.loads((root / '.taut-swift-foundation.json').read_text())
        if (data['owner'] != OWNER or type(data['descriptor']) is not int or data['descriptor'] != 1
            or type(data['codec']) is not int or data['codec'] != 1 or data['module'] != module
            or set(data['capabilities']) != CAPABILITIES or type(data['validation']) is not bool
            or (validation and not data['validation']) or not isinstance(data['files'], dict)):
            raise ValueError('incompatible foundation contract/capabilities')
        expected = set(canonical_sources(validation=data['validation']))
        library = module + '.dll' if os.name == 'nt' else 'lib' + module + '.so'
        if not (expected | {library, module+'.swiftmodule'}).issubset(data['files']):
            raise ValueError('incomplete canonical source or native module/library inventory')
        for name, hash_value in data['files'].items():
            candidate = root / name
            if Path(name).name != name or _is_alias(candidate) or not candidate.is_file() or digest(candidate.read_bytes()) != hash_value:
                raise ValueError(f'missing/changed Swift actual artifact {name}')
        return data
    except (OSError, KeyError, TypeError, ValueError) as exc:
        raise ValueError(f'{root}: incompatible Swift actual artifact {module}: {exc}; regenerate/rebind') from exc
