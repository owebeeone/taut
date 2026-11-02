"""Shared positively-owned runtime planning kernel, extracted from accepted Go.

Profiles vary resources/bindings, not transition or retirement semantics.
"""
from pathlib import Path
import json
from .python_runtime import _is_alias

def plan_outputs(profile, directory, texts, *, mode, validation, source_root, consume_source=False, external=False):
    canonical_path, manifest = profile.canonical_path, profile.manifest
    user_identity, remaining_users = profile.user_identity, profile.remaining_users
    FILES, VALIDATION_FILES = profile.FILES, profile.VALIDATION_FILES
    digest, encoded = profile.digest, profile.encoded
    label, language_target = profile.LABEL, profile.TARGET
    import re
    directory, source_root = canonical_path(directory), canonical_path(source_root)
    imports = profile.runtime_imports(texts)
    if len(imports) > 1:
        raise ValueError(f'conflicting {label} runtime import paths')
    runtime_import = next(iter(imports), '')
    path = directory / ('.taut-' + language_target + '-outputs.json')
    old = manifest(path, language_target + '-schema')
    writes = {directory / name: text.encode('utf-8') for name, text in texts.items()}
    if len(writes) != len(texts):
        raise ValueError(f'conflicting {label} schema output paths in {directory}; use distinct target filenames')
    deletes = {directory / name for name in old['files'] if name not in texts}
    for target in writes:
        name = target.relative_to(directory).as_posix()
        if _is_alias(target) or (target.exists() and name not in old['files']):
            raise ValueError(f'unknown/handwritten {label} output {target}; use a fresh directory or migration')
    roots = {source_root}
    if old.get('source_root'):
        roots.add(canonical_path(old['source_root']))
    user = user_identity(path)
    canonical = Path(__file__).parent / 'runtime'
    for root in roots:
        owner_path = root / ('.taut-' + language_target + '-runtime.json')
        if old.get('source_root') and root == canonical_path(old['source_root']) and not owner_path.exists():
            raise ValueError(f'{owner_path}: previous {label} runtime owner unavailable; use a fresh output root or explicit migration')
        runtime = manifest(owner_path, language_target + '-runtime')
        runtime['users'] = remaining_users(runtime['users'], user)
        # The default root variable can still name the old local owner while
        # package/imported supplied mode selects no source at all. Withdraw the
        # old user without relabeling that owner as the external package.
        selected_source = root == source_root and (mode == 'source' or consume_source)
        if selected_source and runtime['files'] and runtime.get('import_path') != runtime_import:
            raise ValueError(f'{owner_path}: cannot remap a {label} physical source owner to another import_path; use explicit migration')
        if selected_source:
            runtime['import_path'] = runtime_import
        if mode in ('source', 'package') or runtime_import or consume_source or owner_path.exists():
            for filename in FILES:
                candidate = root / filename
                if candidate.exists() and filename not in runtime['files']:
                    raise ValueError(f'unknown/handwritten {label} runtime {candidate}; use a fresh owner root or explicit migration')
        consuming = (mode != 'source' or external) and consume_source
        if root == source_root and consuming and not owner_path.exists():
            raise ValueError(f'{owner_path}: bound {label} source owner unavailable; generate owner first or bind package')
        if root == source_root and mode == 'source':
            runtime['users'][user] = {'validation': validation}
        elif root == source_root and owner_path.exists() and consume_source:
            runtime['users'][user] = {'validation': validation, 'consumer': True}
        desired = dict(FILES)
        if not any(u['validation'] for u in runtime['users'].values()):
            for filename in VALIDATION_FILES:
                desired.pop(filename)
        if not runtime['users']:
            desired = {}
        if desired and root == source_root and mode == 'source':
            contents = {}
            for name, resource in desired.items():
                target = root / name
                if target.exists() and name not in runtime['files']:
                    raise ValueError(f'unknown/handwritten {label} runtime {target}; refusing adoption')
                resource_path = canonical / resource
                contents[name] = resource_path.read_bytes()
                if target in writes:
                    raise ValueError(f'{label} schema/runtime output collision {target}')
                writes[target] = contents[name]
        elif desired:
            missing = desired.keys() - runtime['files'].keys()
            if missing:
                raise ValueError(f'{label} source owner {root} missing {sorted(missing)}; regenerate owner with required capabilities')
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


def manifest(profile, path, kind):
    OWNER, BUILD, FILES = profile.OWNER, profile.BUILD, profile.FILES
    digest = profile.digest
    label = profile.LABEL
    if _is_alias(path) or (path.exists() and not path.is_file()):
        raise ValueError(f'{path}: unsafe {label} ownership metadata path; use a fresh root or migration')
    if not path.exists():
        return dict(kind=kind, owner=OWNER, descriptor=1, codec=1, generator=BUILD, files={}, users={})
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
        if (data['kind'] != kind or data['owner'] != OWNER or type(data['descriptor']) is not int or data['descriptor'] != 1
            or type(data['codec']) is not int or data['codec'] != 1 or data['generator'] != BUILD
            or not isinstance(data['files'], dict) or not isinstance(data['users'], dict)):
            raise ValueError('incompatible ownership/contracts/generation policy')
        if kind == profile.TARGET + '-runtime' and data['files'].keys() - FILES.keys():
            raise ValueError('unsupported runtime source inventory')
        if any(not isinstance(user, dict) or user.keys() - {'validation', 'consumer'}
               or type(user.get('validation')) is not bool
               or ('consumer' in user and type(user['consumer']) is not bool)
               for user in data['users'].values()):
            raise ValueError('invalid shared-user inventory')
        for name, expected in data['files'].items():
            candidate = path.parent / name
            if candidate == path or not candidate.resolve().is_relative_to(path.parent.resolve()):
                raise ValueError('ownership path escapes root')
            if _is_alias(candidate) or not candidate.is_file() or digest(candidate.read_bytes()) != expected:
                raise ValueError(f'modified/missing generator-owned file {candidate}')
        return data
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(f'{path}: unsafe {label} ownership: {exc}; use a fresh root or explicit migration') from exc
