"""JavaScript canonical closure, contracts and positively identified output ownership."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
from .python_runtime import _is_alias, _physical_path, validate_namespace_path

OWNER = 'taut.javascript.foundation'
BUILD = 'javascript-oneof-reference.1'
CAPABILITIES = {'descriptors.v1', 'codec.v1', 'oneof.v1'}
_CANONICAL = Path(__file__).parent / 'runtime'
FILES = {'cbor.js':'cbor.js', 'ext.js':'ext.js', 'contracts.js':'js-contracts.js',
         'descriptors.js':'js-descriptors.js', 'reports.js':'js-reports.js',
         'validation.js':'js-validation.js'}
ENGINE = 'validation.js'



def canonical_path(value, *, directory=True):
    """One physical identity, after checking the original lexical path for aliases.

    Do not resolve first: doing so would hide a junction/reparse obstruction.
    Path.absolute alone preserves '..' and cannot identify an ownership root.
    """
    validate_namespace_path(value)
    lexical = Path(value).absolute()
    for index, component in enumerate((lexical, *lexical.parents)):
        if _is_alias(component) or ((directory or index) and component.exists() and not component.is_dir()):
            raise ValueError(f'{component}: unsafe/obstructed JavaScript output directory; use a fresh root or explicit migration')
    return _physical_path(lexical)


def user_identity(value):
    validate_namespace_path(value)
    path = Path(value)
    if not path.is_absolute():
        raise ValueError(f'{value}: unsafe JavaScript source user identity; use an absolute schema owner or explicit migration')
    return os.path.normcase(str(canonical_path(path, directory=False)))


def remaining_users(users, current_user):
    normalized = {}
    for name, entry in users.items():
        identity = user_identity(name)
        if identity == current_user:
            continue  # all equivalent spellings of this known schema are replaced
        if identity in normalized and normalized[identity] != entry:
            raise ValueError(f'ambiguous JavaScript source user identity {name}; use a fresh owner root or explicit migration')
        normalized[identity] = entry
    return normalized


def binding(bindings, directory, mode):
    config = dict((bindings or {}).get('js', {}))
    allowed = {'owner', 'module', 'source_root', 'artifact', 'descriptor_contract', 'codec_contract', 'capabilities'}
    if config.keys() - allowed:
        raise ValueError(f'unknown JavaScript runtime binding keys {sorted(config.keys() - allowed)}')
    caps = config.get('capabilities', sorted(CAPABILITIES))
    if (config.get('owner', OWNER) != OWNER
        or type(config.get('descriptor_contract', 1)) is not int or config.get('descriptor_contract', 1) != 1
        or type(config.get('codec_contract', 1)) is not int or config.get('codec_contract', 1) != 1
        or not isinstance(caps, (list, tuple, set)) or any(not isinstance(c,str) for c in caps) or set(caps) != CAPABILITIES):
        raise ValueError('JavaScript runtime requires compatible owner/descriptor/codec/capabilities; regenerate/rebind')
    root = canonical_path(config.get('source_root', directory))
    package_default = mode == 'package' and 'source_root' not in config
    default = 'taut-js-foundation' if package_default else os.path.relpath(root, canonical_path(directory)).replace('\\', '/')
    if not package_default and default != '.' and not default.startswith(('./', '../', '/')): default = './' + default
    module = config.get('module', default)
    if not isinstance(module, str) or not module or module.endswith('/') or '\\' in module or any(ord(c)<32 for c in module):
        raise ValueError('invalid JavaScript runtime module specifier')
    if mode == 'source' and module != default:
        path = Path(module)
        if not (path.is_absolute() or module.startswith(('./','../'))) or canonical_path(path if path.is_absolute() else directory/path) != root:
            raise ValueError('JavaScript source module must name the actual shared source owner')
    if 'artifact' in config: verify_artifact(Path(config['artifact']))
    return module, root, 'source_root' in config


def digest(content):
    return hashlib.sha256(content).hexdigest()


def encoded(value):
    return (json.dumps(value, indent=2, sort_keys=True) + '\n').encode()


def manifest(path, kind):
    if _is_alias(path) or (path.exists() and not path.is_file()):
        raise ValueError(f'{path}: unsafe JavaScript ownership metadata path; use a fresh root or migration')
    if not path.exists():
        return dict(kind=kind, owner=OWNER, descriptor=1, codec=1, generator=BUILD, files={}, users={})
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
        if (data['kind'] != kind or data['owner'] != OWNER or type(data['descriptor']) is not int or data['descriptor'] != 1
            or type(data['codec']) is not int or data['codec'] != 1 or data['generator'] != BUILD
            or not isinstance(data['files'], dict) or not isinstance(data['users'], dict)):
            raise ValueError('incompatible ownership/contracts/generation policy')
        if kind == 'js-runtime' and data['files'].keys() - FILES.keys():
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
        raise ValueError(f'{path}: unsafe JavaScript ownership: {exc}; use a fresh root or explicit migration') from exc


def plan_outputs(directory, texts, *, mode, validation, source_root, consume_source=False, external=False):
    directory, source_root = canonical_path(directory), canonical_path(source_root)
    path = directory / '.taut-js-outputs.json'
    old = manifest(path, 'js-schema')
    writes = {directory / name: text.encode('utf-8') for name, text in texts.items()}
    if len(writes) != len(texts):
        raise ValueError(f'conflicting JavaScript schema output paths in {directory}; use distinct target filenames')
    deletes = {directory / name for name in old['files'] if name not in texts}
    for target in writes:
        name = target.relative_to(directory).as_posix()
        if _is_alias(target) or (target.exists() and name not in old['files']):
            raise ValueError(f'unknown/handwritten JavaScript output {target}; use a fresh directory or migration')
    roots = {source_root}
    if old.get('source_root'):
        roots.add(canonical_path(old['source_root']))
    user = user_identity(path)
    canonical = Path(__file__).parent / 'runtime'
    for root in roots:
        owner_path = root / '.taut-js-runtime.json'
        runtime = manifest(owner_path, 'js-runtime')
        if mode in ('source', 'package') or consume_source or owner_path.exists():
            for filename in FILES:
                candidate = root / filename
                if candidate.exists() and filename not in runtime['files']:
                    raise ValueError(f'unknown/handwritten JavaScript runtime {candidate}; use a fresh owner root or explicit migration')
        consuming = (mode != 'source' or external) and consume_source
        if root == source_root and consuming and not owner_path.exists():
            raise ValueError(f'{owner_path}: bound JavaScript source owner unavailable; generate owner first or bind package')
        runtime['users'] = remaining_users(runtime['users'], user)
        if root == source_root and mode == 'source':
            runtime['users'][user] = {'validation': validation}
        elif root == source_root and owner_path.exists() and consume_source:
            runtime['users'][user] = {'validation': validation, 'consumer': True}
        desired = dict(FILES)
        if not any(u['validation'] for u in runtime['users'].values()):
            desired.pop(ENGINE)
        if not runtime['users']:
            desired = {}
        if desired and root == source_root and mode == 'source':
            contents = {}
            for name, resource in desired.items():
                target = root / name
                if target.exists() and name not in runtime['files']:
                    raise ValueError(f'unknown/handwritten JavaScript runtime {target}; refusing adoption')
                resource_path = canonical / resource
                contents[name] = resource_path.read_bytes()
                if target in writes:
                    raise ValueError(f'JavaScript schema/runtime output collision {target}')
                writes[target] = contents[name]
        elif desired:
            missing = desired.keys() - runtime['files'].keys()
            if missing:
                raise ValueError(f'JavaScript source owner {root} missing {sorted(missing)}; regenerate owner with required capabilities')
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


def canonical_sources(*, validation=True):
    return {name: (_CANONICAL / resource).read_bytes() for name, resource in FILES.items()
            if validation or name != ENGINE}


def build_foundation(destination, *, validation=True, npm='npm'):
    """Build a local npm tarball from canonical bytes, without installation/publication."""
    import subprocess
    import tempfile
    import shutil
    destination = canonical_path(destination, directory=False)
    if destination.exists(): raise ValueError(f'{destination}: artifact already exists')
    payload = canonical_sources(validation=validation)
    payload['index.js'] = b'"use strict";\nmodule.exports = Object.freeze({...require("./descriptors.js"), ...require("./reports.js"), cbor:require("./cbor.js"), ext:require("./ext.js")});\n'
    package = dict(name='taut-js-foundation',version='0.0.0-reference.1',private=True,
                   type='commonjs',main='./index.js',exports={'.':'./index.js',
                   **{'./'+n:'./'+n for n in payload if n != 'index.js'}})
    metadata = dict(owner=OWNER,build=BUILD,descriptor=1,codec=1,capabilities=sorted(CAPABILITIES),
                    validation=validation,files={n:digest(v) for n,v in payload.items()})
    payload['taut-foundation.json'] = encoded(metadata)
    payload['package.json'] = encoded(package)
    with tempfile.TemporaryDirectory(prefix='taut-js-foundation-') as temp:
        root=Path(temp)
        for name,data in payload.items(): (root/name).write_bytes(data)
        executable = shutil.which(str(npm))
        if not executable: raise ValueError('npm must be available to build a local package; no automatic installation')
        subprocess.run([executable,'pack','--ignore-scripts','--json'],cwd=root,check=True,capture_output=True,text=True)
        archive=next(root.glob('*.tgz'))
        destination.parent.mkdir(parents=True,exist_ok=True)
        destination.write_bytes(archive.read_bytes())
    verify_artifact(destination,validation=validation)
    return destination


def verify_artifact(path, *, validation=False):
    import tarfile
    try:
        with tarfile.open(path,'r:gz') as archive:
            members=archive.getmembers(); names=[m.name for m in members]
            if len(names)!=len(set(names)) or any(not m.isfile() or not m.name.startswith('package/') or '..' in m.name.split('/') for m in members):
                raise ValueError('unsafe/duplicate artifact entries')
            def read(name): return archive.extractfile('package/'+name).read()
            data=json.loads(read('taut-foundation.json'))
            if (data['owner']!=OWNER or type(data['descriptor']) is not int or data['descriptor']!=1 or type(data['codec']) is not int or data['codec']!=1 or set(data['capabilities'])!=CAPABILITIES or type(data['validation']) is not bool or validation and not data['validation']):
                raise ValueError('incompatible runtime contracts/capabilities')
            required=set(FILES)-(set() if data['validation'] else {ENGINE})
            if set(data['files']) != required|{'index.js'} or set(names)!={'package/'+n for n in data['files']}|{'package/package.json','package/taut-foundation.json'}:
                raise ValueError('runtime payload inventory mismatch')
            for name,expected in data['files'].items():
                if digest(read(name))!=expected: raise ValueError(f'modified runtime artifact {name}')
            package=json.loads(read('package.json'))
            if package.get('type')!='commonjs' or any(package['exports'].get('./'+n)!='./'+n for n in required) or package['exports'].get('.')!='./index.js':
                raise ValueError('missing foundation CommonJS exports')
            return data
    except (OSError,KeyError,TypeError,ValueError,tarfile.TarError) as exc:
        raise ValueError(f'{path}: incompatible JavaScript foundation artifact: {exc}; regenerate/rebind') from exc
