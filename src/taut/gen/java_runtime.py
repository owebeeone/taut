"""Java canonical closure, contracts and positively identified output ownership."""
from __future__ import annotations
import hashlib
import json
import os
import re
from pathlib import Path
from .python_runtime import _is_alias, _physical_path

OWNER = 'taut.java.foundation'
BUILD = 'java-oneof-reference.1'
CAPABILITIES = {'descriptors.v1', 'codec.v1', 'oneof.v1'}
_CANONICAL = Path(__file__).parent / 'runtime'
FILES = {'Cbor.java': 'Cbor.java', 'Ext.java': 'Ext.java'}
FILES.update({p.relative_to(_CANONICAL / 'java').as_posix(): p.relative_to(_CANONICAL).as_posix()
              for p in sorted((_CANONICAL / 'java').rglob('*.java'))})
ENGINE = 'taut/validation/ValidationEngine.java'


def canonical_path(value, *, directory=True):
    """One physical identity, after checking the original lexical path for aliases.

    Do not resolve first: doing so would hide a junction/reparse obstruction.
    Path.absolute alone preserves '..' and cannot identify an ownership root.
    """
    lexical = Path(value).absolute()
    for index, component in enumerate((lexical, *lexical.parents)):
        if _is_alias(component) or ((directory or index) and component.exists() and not component.is_dir()):
            raise ValueError(f'{component}: unsafe/obstructed Java output directory; use a fresh root or explicit migration')
    return _physical_path(lexical)


def user_identity(value):
    path = Path(value)
    if not path.is_absolute():
        raise ValueError(f'{value}: unsafe Java source user identity; use an absolute schema owner or explicit migration')
    return os.path.normcase(str(canonical_path(path, directory=False)))


def remaining_users(users, current_user):
    normalized = {}
    for name, entry in users.items():
        identity = user_identity(name)
        if identity == current_user:
            continue  # all equivalent spellings of this known schema are replaced
        if identity in normalized and normalized[identity] != entry:
            raise ValueError(f'ambiguous Java source user identity {name}; use a fresh owner root or explicit migration')
        normalized[identity] = entry
    return normalized


def binding(bindings, directory, mode):
    config = dict((bindings or {}).get('java', {}))
    allowed = {'owner', 'module', 'source_root', 'artifact', 'descriptor_contract', 'codec_contract', 'capabilities'}
    if config.keys() - allowed:
        raise ValueError(f'unknown Java runtime binding keys {sorted(config.keys() - allowed)}')
    caps = config.get('capabilities', sorted(CAPABILITIES))
    if (config.get('owner', OWNER) != OWNER or config.get('module', 'taut') != 'taut'
        or type(config.get('descriptor_contract', 1)) is not int or config.get('descriptor_contract', 1) != 1
        or type(config.get('codec_contract', 1)) is not int or config.get('codec_contract', 1) != 1
        or not isinstance(caps, (list, tuple, set)) or any(not isinstance(c, str) for c in caps) or not CAPABILITIES <= set(caps) or not set(caps) <= CAPABILITIES):
        raise ValueError(f'Java runtime {config}: required owner={OWNER}, module=taut, descriptor=1, codec=1, capabilities={sorted(CAPABILITIES)}; regenerate/rebind owner')
    if 'artifact' in config:
        verify_artifact(Path(config['artifact']))
    root = canonical_path(config.get('source_root', directory))
    return 'taut', root, 'source_root' in config


def digest(content):
    return hashlib.sha256(content).hexdigest()


def encoded(value):
    return (json.dumps(value, indent=2, sort_keys=True) + '\n').encode()


def manifest(path, kind):
    if _is_alias(path) or (path.exists() and not path.is_file()):
        raise ValueError(f'{path}: unsafe Java ownership metadata path; use a fresh root or migration')
    if not path.exists():
        return dict(kind=kind, owner=OWNER, descriptor=1, codec=1, generator=BUILD, files={}, users={})
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
        if (data['kind'] != kind or data['owner'] != OWNER or type(data['descriptor']) is not int or data['descriptor'] != 1
            or type(data['codec']) is not int or data['codec'] != 1 or data['generator'] != BUILD
            or not isinstance(data['files'], dict) or not isinstance(data['users'], dict)):
            raise ValueError('incompatible ownership/contracts/generation policy')
        if kind == 'java-runtime' and data['files'].keys() - FILES.keys():
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
        raise ValueError(f'{path}: unsafe Java ownership: {exc}; use a fresh root or explicit migration') from exc


def plan_outputs(directory, texts, *, mode, validation, source_root, consume_source=False, external=False):
    directory, source_root = canonical_path(directory), canonical_path(source_root)
    path = directory / '.taut-java-outputs.json'
    old = manifest(path, 'java-schema')
    writes = {directory / name: text.encode('utf-8') for name, text in texts.items()}
    if len(writes) != len(texts):
        raise ValueError(f'conflicting Java schema output paths in {directory}; use distinct target filenames')
    deletes = {directory / name for name in old['files'] if name not in texts}
    for target in writes:
        name = target.relative_to(directory).as_posix()
        if _is_alias(target) or (target.exists() and name not in old['files']):
            raise ValueError(f'unknown/handwritten Java output {target}; use a fresh directory or migration')
    roots = {source_root}
    if old.get('source_root'):
        roots.add(canonical_path(old['source_root']))
    user = user_identity(path)
    canonical = Path(__file__).parent / 'runtime'
    for root in roots:
        owner_path = root / '.taut-java-runtime.json'
        runtime = manifest(owner_path, 'java-runtime')
        if mode in ('source', 'package') or consume_source or owner_path.exists():
            for filename in FILES:
                candidate = root / filename
                if candidate.exists() and filename not in runtime['files']:
                    raise ValueError(f'unknown/handwritten Java runtime {candidate}; use a fresh owner root or explicit migration')
        consuming = (mode != 'source' or external) and consume_source
        if root == source_root and consuming and not owner_path.exists():
            raise ValueError(f'{owner_path}: bound Java source owner unavailable; generate owner first or bind package')
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
                    raise ValueError(f'unknown/handwritten Java runtime {target}; refusing adoption')
                resource_path = canonical / resource
                contents[name] = resource_path.read_bytes()
                if target in writes:
                    raise ValueError(f'Java schema/runtime output collision {target}')
                writes[target] = contents[name]
        elif desired:
            missing = desired.keys() - runtime['files'].keys()
            if missing:
                raise ValueError(f'Java source owner {root} missing {sorted(missing)}; regenerate owner with required capabilities')
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
    """Exact canonical closure used for both source bundles and local jars."""
    return {name: (_CANONICAL / resource).read_bytes() for name, resource in FILES.items()
            if validation or name != ENGINE}


def build_foundation(destination, *, validation=True, javac='javac'):
    """Compile a local Java-8 foundation jar; no registry name, install or publication."""
    import subprocess
    import tempfile
    import zipfile
    destination = Path(destination)
    if destination.exists():
        raise ValueError(f'{destination}: local artifact destination exists; choose a fresh file')
    sources = canonical_sources(validation=validation)
    with tempfile.TemporaryDirectory(prefix='taut-java-foundation-') as temp:
        root = Path(temp)
        for name, content in sources.items():
            source = root / 'src' / name
            source.parent.mkdir(parents=True, exist_ok=True)
            source.write_bytes(content)
        classes = root / 'classes'
        classes.mkdir()
        subprocess.run([str(javac), '--release', '8', '-encoding', 'UTF-8', '-d', str(classes),
                        *(str(root / 'src' / name) for name in sources)], check=True, capture_output=True, text=True)
        payload = {p.relative_to(classes).as_posix(): p.read_bytes() for p in classes.rglob('*.class')}
        metadata = dict(owner=OWNER, build=BUILD, descriptor=1, codec=1,
                        capabilities=sorted(CAPABILITIES), validation=validation,
                        sources={name: digest(data) for name, data in sources.items()},
                        classes={name: digest(data) for name, data in payload.items()})
        destination.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(destination, 'x', compression=zipfile.ZIP_DEFLATED) as archive:
            for name, data in sorted(payload.items()):
                archive.writestr(name, data)
            for name, data in sorted(sources.items()):
                archive.writestr('META-INF/taut-sources/' + name, data)
            archive.writestr('META-INF/taut-foundation.json', encoded(metadata))
    verify_artifact(destination, validation=validation)
    return destination


def verify_artifact(path, *, validation=False):
    """Check configured local classpath provenance without executing the JVM in codegen."""
    import zipfile
    try:
        with zipfile.ZipFile(path) as archive:
            names = archive.namelist()
            if len(names) != len(set(names)):
                raise ValueError('duplicate artifact entries/owners')
            data = json.loads(archive.read('META-INF/taut-foundation.json'))
            if (data['owner'] != OWNER or type(data['descriptor']) is not int or data['descriptor'] != 1
                    or type(data['codec']) is not int or data['codec'] != 1
                    or not CAPABILITIES <= set(data['capabilities']) or type(data['validation']) is not bool
                    or validation and not data['validation']):
                raise ValueError('incompatible owner/descriptor/codec/capabilities or missing validation engine')
            if set(n for n in names if n.endswith('.class')) != set(data['classes']):
                raise ValueError('class payload inventory mismatch')
            for name, expected in data['classes'].items():
                if digest(archive.read(name)) != expected:
                    raise ValueError(f'modified foundation class {name}')
            required = set(FILES) - (set() if data['validation'] else {ENGINE})
            if set(data['sources']) != required:
                raise ValueError('canonical source inventory mismatch')
            for name, expected in data['sources'].items():
                if digest(archive.read('META-INF/taut-sources/' + name)) != expected:
                    raise ValueError(f'modified canonical source {name}')
            for required_class in ('taut/Cbor.class', 'taut/Ext.class',
                                   'taut/validation/descriptors/SchemaBinding.class',
                                   'taut/validation/ValidationReport.class'):
                if required_class not in data['classes']:
                    raise ValueError(f'missing foundation export {required_class}')
            return data
    except (OSError, KeyError, TypeError, ValueError, zipfile.BadZipFile) as exc:
        raise ValueError(f'{path}: incompatible Java foundation artifact: {exc}; regenerate/rebind') from exc
