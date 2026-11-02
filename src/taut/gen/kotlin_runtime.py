"""Kotlin canonical closure, contracts and positively identified output ownership."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
from .python_runtime import _is_alias, _physical_path

OWNER = 'taut.kotlin.foundation'
BUILD = 'kotlin-oneof-reference.1'
CAPABILITIES = {'descriptors.v1', 'codec.v1', 'oneof.v1'}
FILES = {'cbor.kt': 'cbor.kt', 'ext.kt': 'ext.kt',
         'descriptors.kt': 'kotlin/descriptors.kt', 'validation.kt': 'kotlin/validation.kt'}


def canonical_path(value, *, directory=True):
    """One physical identity, after checking the original lexical path for aliases.

    Do not resolve first: doing so would hide a junction/reparse obstruction.
    Path.absolute alone preserves '..' and cannot identify an ownership root.
    """
    lexical = Path(value).absolute()
    for index, component in enumerate((lexical, *lexical.parents)):
        if _is_alias(component) or ((directory or index) and component.exists() and not component.is_dir()):
            raise ValueError(f'{component}: unsafe/obstructed Kotlin output directory; use a fresh root or explicit migration')
    return _physical_path(lexical)


def user_identity(value):
    path = Path(value)
    if not path.is_absolute():
        raise ValueError(f'{value}: unsafe Kotlin source user identity; use an absolute schema owner or explicit migration')
    return os.path.normcase(str(canonical_path(path, directory=False)))


def remaining_users(users, current_user):
    normalized = {}
    for name, entry in users.items():
        identity = user_identity(name)
        if identity == current_user:
            continue  # all equivalent spellings of this known schema are replaced
        if identity in normalized and normalized[identity] != entry:
            raise ValueError(f'ambiguous Kotlin source user identity {name}; use a fresh owner root or explicit migration')
        normalized[identity] = entry
    return normalized


def binding(bindings, directory, mode):
    config = dict((bindings or {}).get('kotlin', {}))
    allowed = {'owner', 'source_root', 'descriptor_contract', 'codec_contract', 'capabilities'}
    if config.keys() - allowed:
        raise ValueError(f'unknown Kotlin runtime binding keys {sorted(config.keys() - allowed)}')
    caps = config.get('capabilities', sorted(CAPABILITIES))
    if (config.get('owner', OWNER) != OWNER or type(config.get('descriptor_contract', 1)) is not int
        or config.get('descriptor_contract', 1) != 1 or type(config.get('codec_contract', 1)) is not int
        or config.get('codec_contract', 1) != 1 or not isinstance(caps, (list, tuple, set))
        or any(not isinstance(c, str) for c in caps) or set(caps) != CAPABILITIES):
        raise ValueError(f'Kotlin runtime {config}: required owner={OWNER}, descriptor=1, codec=1, capabilities={sorted(CAPABILITIES)}; regenerate/rebind owner')
    root = canonical_path(config.get('source_root', directory))
    return root, 'source_root' in config


def digest(content):
    return hashlib.sha256(content).hexdigest()


def encoded(value):
    return (json.dumps(value, indent=2, sort_keys=True) + '\n').encode()


def manifest(path, kind):
    if _is_alias(path) or (path.exists() and not path.is_file()):
        raise ValueError(f'{path}: unsafe Kotlin ownership metadata path; use a fresh root or migration')
    if not path.exists():
        return dict(kind=kind, owner=OWNER, descriptor=1, codec=1, generator=BUILD, files={}, users={})
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
        if (data['kind'] != kind or data['owner'] != OWNER or type(data['descriptor']) is not int or data['descriptor'] != 1
            or type(data['codec']) is not int or data['codec'] != 1 or data['generator'] != BUILD
            or not isinstance(data['files'], dict) or not isinstance(data['users'], dict)):
            raise ValueError('incompatible ownership/contracts/generation policy')
        if kind == 'kotlin-runtime' and data['files'].keys() - FILES.keys():
            raise ValueError('unsupported runtime source inventory')
        if any(not isinstance(user, dict) or type(user.get('validation')) is not bool for user in data['users'].values()):
            raise ValueError('invalid shared-user inventory')
        for name, expected in data['files'].items():
            candidate = path.parent / name
            if candidate == path or not candidate.resolve().is_relative_to(path.parent.resolve()):
                raise ValueError('ownership path escapes root')
            if _is_alias(candidate) or not candidate.is_file() or digest(candidate.read_bytes()) != expected:
                raise ValueError(f'modified/missing generator-owned file {candidate}')
        return data
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(f'{path}: unsafe Kotlin ownership: {exc}; use a fresh root or explicit migration') from exc


def plan_outputs(directory, texts, *, mode, validation, source_root, consume_source=False, external=False):
    directory, source_root = canonical_path(directory), canonical_path(source_root)
    path = directory / '.taut-kotlin-outputs.json'
    old = manifest(path, 'kotlin-schema')
    writes = {directory / name: text.encode('utf-8') for name, text in texts.items()}
    if len(writes) != len(texts):
        raise ValueError(f'conflicting Kotlin schema output paths in {directory}; use distinct target filenames')
    deletes = {directory / name for name in old['files'] if name not in texts}
    for target in writes:
        name = target.relative_to(directory).as_posix()
        if _is_alias(target) or (target.exists() and name not in old['files']):
            raise ValueError(f'unknown/handwritten Kotlin output {target}; use a fresh directory or migration')
    roots = {source_root}
    if old.get('source_root'):
        roots.add(canonical_path(old['source_root']))
    user = user_identity(path)
    canonical = Path(__file__).parent / 'runtime'
    for root in roots:
        owner_path = root / '.taut-kotlin-runtime.json'
        runtime = manifest(owner_path, 'kotlin-runtime')
        if mode in ('source', 'package') or consume_source or owner_path.exists():
            for filename in FILES:
                candidate = root / filename
                if candidate.exists() and filename not in runtime['files']:
                    raise ValueError(f'unknown/handwritten Kotlin runtime {candidate}; use a fresh owner root or explicit migration')
        consuming = (mode != 'source' or external) and consume_source
        if root == source_root and consuming and not owner_path.exists():
            raise ValueError(f'{owner_path}: bound Kotlin source owner unavailable; generate owner first or bind package')
        runtime['users'] = remaining_users(runtime['users'], user)
        if root == source_root and mode == 'source':
            runtime['users'][user] = {'validation': validation}
        elif root == source_root and owner_path.exists() and consume_source:
            runtime['users'][user] = {'validation': validation, 'consumer': True}
        desired = dict(FILES)
        if not any(u['validation'] for u in runtime['users'].values()):
            desired.pop('validation.kt')
        if not runtime['users']:
            desired = {}
        if desired and root == source_root and mode == 'source':
            contents = {}
            for name, resource in desired.items():
                target = root / name
                if target.exists() and name not in runtime['files']:
                    raise ValueError(f'unknown/handwritten Kotlin runtime {target}; refusing adoption')
                resource_path = canonical / resource
                contents[name] = resource_path.read_bytes()
                if target in writes:
                    raise ValueError(f'Kotlin schema/runtime output collision {target}')
                writes[target] = contents[name]
        elif desired:
            missing = desired.keys() - runtime['files'].keys()
            if missing:
                raise ValueError(f'Kotlin source owner {root} missing {sorted(missing)}; regenerate owner with required capabilities')
            contents = {name: (root / name).read_bytes() for name in desired}
        else:
            contents = {}
        deletes.update(root / name for name in runtime['files'].keys() - contents.keys())
        if owner_path.exists() or contents:
            runtime['files'] = {name: digest(content) for name, content in contents.items()}
            if contents:
                writes[owner_path] = encoded(runtime)
            else:
                deletes.add(owner_path)
    new = dict(old, files={name: digest(text.encode()) for name, text in texts.items()}, mode=mode or 'supplied',
               validation=validation, source_root=str(source_root) if mode == 'source' or consume_source else None)
    writes[path] = encoded(new)
    return writes, deletes
