"""Go canonical closure, contracts and positively identified output ownership."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
from .python_runtime import _is_alias, _physical_path, validate_namespace_path

OWNER = 'taut.go.foundation'
BUILD = 'go-oneof-reference.1'
CAPABILITIES = {'descriptors.v1', 'codec.v1', 'oneof.v1'}
FILES = {'cbor.go': 'cbor.go', 'ext.go': 'ext.go', 'descriptors.go': 'go/descriptors.go', 'paths.go': 'go/paths.go', 'reports.go': 'go/reports.go', 'validation.go': 'go/validation.go'}
ENGINE = 'validation.go'
VALIDATION_FILES = {'validation.go', 'reports.go'}


def binding(bindings, directory, mode, *, validation=False):
    config = dict((bindings or {}).get('go', {}))
    allowed = {'owner', 'import_path', 'source_root', 'artifact', 'descriptor_contract', 'codec_contract', 'capabilities'}
    if config.keys() - allowed:
        raise ValueError(f'unknown Go runtime binding keys {sorted(config.keys()-allowed)}')
    caps = config.get('capabilities', sorted(CAPABILITIES))
    if (config.get('owner', OWNER) != OWNER
        or type(config.get('descriptor_contract', 1)) is not int or config.get('descriptor_contract', 1) != 1
        or type(config.get('codec_contract', 1)) is not int or config.get('codec_contract', 1) != 1
        or not isinstance(caps, (list, tuple, set)) or any(not isinstance(c, str) for c in caps)
        or set(caps) != CAPABILITIES):
        raise ValueError(f'Go requires owner={OWNER}, descriptor=1 codec=1 capabilities={sorted(CAPABILITIES)}; regenerate/rebind')
    module = config.get('import_path', '')
    if not isinstance(module,str):
        raise ValueError('Go import_path must be an explicit string')
    if module:
        import_path(module)
    root = canonical_path(config.get('source_root', directory))
    if mode == 'package' and not module:
        raise ValueError('Go package mode requires an explicit application-supplied import_path; no package is discovered or installed')
    if root != canonical_path(directory) and not module:
        raise ValueError('Go separate source_root requires its actual import_path')
    if root == canonical_path(directory) and module and mode == 'source':
        raise ValueError('Go imported source owner requires a separate source_root, to avoid importing its own package')
    if 'artifact' in config:
        verify_artifact(config['artifact'], module, validation=validation)
    return module, root, 'source_root' in config


def import_path(value):
    import re
    if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9_~.-]+(?:/[A-Za-z0-9_~.-]+)*', value) or any(p in ('.', '..') for p in value.split('/')):
        raise ValueError(f'invalid explicit Go import path: {value!r}')
    return value


def canonical_sources(*, validation=True):
    canonical = Path(__file__).parent / 'runtime'
    return {name: (canonical / resource).read_bytes() for name, resource in FILES.items()
            if validation or name not in VALIDATION_FILES}


def _go_env():
    return dict(os.environ, GO111MODULE='on', GOWORK='off', GOPROXY='off', GOSUMDB='off', GOTOOLCHAIN='local')


def build_foundation(destination, import_path_value, *, validation=True):
    """Build an explicit local Go module artifact from the same canonical closure.

    The caller chooses the module path. This does not install or publish it.
    """
    import subprocess
    module = import_path(import_path_value)
    root = canonical_path(destination)
    if root.exists() and any(root.iterdir()):
        raise ValueError(f'Go artifact destination must be empty: {root}')
    root.mkdir(parents=True, exist_ok=True)
    for name, content in canonical_sources(validation=validation).items():
        (root / name).write_bytes(content)
    (root / 'go.mod').write_text(f'module {module}\n\ngo 1.18\n', encoding='utf-8')
    inventory = {p.name: digest(p.read_bytes()) for p in root.iterdir() if p.is_file()}
    (root / '.taut-go-foundation.json').write_bytes(encoded(dict(owner=OWNER, descriptor=1, codec=1,
        capabilities=sorted(CAPABILITIES), build=BUILD, import_path=module, validation=validation, files=inventory)))
    subprocess.run(['go', 'test', './...'], cwd=root, env=_go_env(), check=True, capture_output=True)
    verify_artifact(root, module, validation=validation, execute=True)
    return root


def verify_artifact(path, module, *, validation=False, execute=False):
    """Preflight local provenance; optionally run an explicit build-time ABI probe.

    Generation never executes Go. Usability is checked on actual compiled exports
    by generated guards, with explicit execution here reserved for package/tests.
    """
    import re
    import subprocess
    import tempfile
    if not module:
        raise ValueError('Go artifact verification requires import_path')
    import_path(module)
    root = canonical_path(path)
    manifest_path = root / 'go.mod'
    if not manifest_path.is_file() or not re.search(r'^module\s+' + re.escape(module) + r'\s*$', manifest_path.read_text(), re.M):
        raise ValueError(f'{root}: Go artifact must export explicit module {module}; regenerate/rebind')
    try:
        provenance = json.loads((root / '.taut-go-foundation.json').read_text())
        if (provenance['owner'] != OWNER or type(provenance['descriptor']) is not int or provenance['descriptor'] != 1
            or type(provenance['codec']) is not int or provenance['codec'] != 1 or provenance['import_path'] != module
            or set(provenance['capabilities']) != CAPABILITIES or type(provenance['validation']) is not bool
            or (validation and not provenance['validation']) or not isinstance(provenance['files'], dict)):
            raise ValueError('incompatible contracts/capabilities')
        expected = set(canonical_sources(validation=provenance['validation'])) | {'go.mod'}
        if provenance['files'].keys() != expected:
            raise ValueError('incomplete foundation source inventory')
        if {p.name for p in root.glob('*.go')} != {name for name in expected if name.endswith('.go')}:
            raise ValueError('unknown Go foundation source exports')
        for name, hash_value in provenance['files'].items():
            candidate = root / name
            if _is_alias(candidate) or not candidate.is_file() or digest(candidate.read_bytes()) != hash_value:
                raise ValueError(f'missing/changed foundation export {name}')
    except (OSError, KeyError, TypeError, ValueError) as exc:
        raise ValueError(f'{root}: incompatible Go actual artifact provenance: {exc}; regenerate/rebind') from exc
    if not execute:
        return provenance
    with tempfile.TemporaryDirectory(prefix='go-foundation-probe-') as scratch:
        probe = Path(scratch)
        major = re.search(r'/v([2-9][0-9]*)$', module)
        version = 'v' + (major[1] if major else '0') + '.0.0'
        (probe / 'go.mod').write_text(f'module taut.probe.local/check\n\ngo 1.18\nrequire {module} {version}\nreplace {module} => {json.dumps(root.as_posix())}\n')
        engine = 'if !r.IsRecordValid(&v,b,true) || !r.ValidateRecord(&v,b,true).IsComplete() { panic("Go engine capability") };' if validation else ''
        (probe / 'main.go').write_text('package main\nimport r '+json.dumps(module)+'\nfunc main(){ '
            'var guard r.ContractGuard=r.RequireFoundation("artifact probe","taut.go.foundation",1,1,"codec.v1","descriptors.v1","oneof.v1"); _=guard; '
            'r.ConfirmFoundation(guard,r.FoundationOwner,r.DescriptorContract,r.CodecContract,r.FoundationCapabilities()); '
            'if r.FoundationOwner!="taut.go.foundation" || r.DescriptorContract!=1 || r.CodecContract!=1 { panic("incompatible Go actual runtime exports") }; '
            'd:=r.NewMessageDescriptor("Probe","Probe",nil,nil,nil,nil,nil,nil,nil,nil,"probe"); '
            'r.NewSchemaDescriptor(2,"Probe",map[string]r.MessageDescriptor{"Probe":d},nil,nil,nil); '
            'type value struct{}; v:=value{}; b:=r.NewMessageBinding[value](d,func(*value,int)bool{return false},func(*value,int)(int64,bool){return 0,false},func(*value,int)any{return nil},func(*value,int,r.Traversal,[]r.PathSegment)bool{return true}); '
            '_=v; _=b; '+engine+' c,err:=r.TryDecode(r.Encode(r.CInt(42))); if err!=nil || c.I!=42 { panic("Go codec capability") } }\n')
        result = subprocess.run(['go', 'run', '.'], cwd=probe, env=_go_env(), capture_output=True, text=True)
        if result.returncode:
            raise ValueError(f'{root}: incompatible Go actual artifact {module}, requires owner={OWNER} descriptor=1 codec=1 capabilities={sorted(CAPABILITIES)}; regenerate/rebind:\n{result.stderr}')


def canonical_path(value, *, directory=True):
    """One physical identity, after checking the original lexical path for aliases.

    Do not resolve first: doing so would hide a junction/reparse obstruction.
    Path.absolute alone preserves '..' and cannot identify an ownership root.
    """
    validate_namespace_path(value)
    lexical = Path(value).absolute()
    for index, component in enumerate((lexical, *lexical.parents)):
        if _is_alias(component) or ((directory or index) and component.exists() and not component.is_dir()):
            raise ValueError(f'{component}: unsafe/obstructed Go output directory; use a fresh root or explicit migration')
    return _physical_path(lexical)


def user_identity(value):
    validate_namespace_path(value)
    path = Path(value)
    if not path.is_absolute():
        raise ValueError(f'{value}: unsafe Go source user identity; use an absolute schema owner or explicit migration')
    return os.path.normcase(str(canonical_path(value, directory=False)))


def remaining_users(users, current_user):
    normalized = {}
    for name, entry in users.items():
        identity = user_identity(name)
        if identity == current_user:
            continue  # all equivalent spellings of this known schema are replaced
        if identity in normalized and normalized[identity] != entry:
            raise ValueError(f'ambiguous Go source user identity {name}; use a fresh owner root or explicit migration')
        normalized[identity] = entry
    return normalized


def digest(content):
    return hashlib.sha256(content).hexdigest()


def encoded(value):
    return (json.dumps(value, indent=2, sort_keys=True) + '\n').encode()


def manifest(path, kind):
    if _is_alias(path) or (path.exists() and not path.is_file()):
        raise ValueError(f'{path}: unsafe Go ownership metadata path; use a fresh root or migration')
    if not path.exists():
        return dict(kind=kind, owner=OWNER, descriptor=1, codec=1, generator=BUILD, files={}, users={})
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
        if (data['kind'] != kind or data['owner'] != OWNER or type(data['descriptor']) is not int or data['descriptor'] != 1
            or type(data['codec']) is not int or data['codec'] != 1 or data['generator'] != BUILD
            or not isinstance(data['files'], dict) or not isinstance(data['users'], dict)):
            raise ValueError('incompatible ownership/contracts/generation policy')
        if kind == 'go-runtime' and data['files'].keys() - FILES.keys():
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
        raise ValueError(f'{path}: unsafe Go ownership: {exc}; use a fresh root or explicit migration') from exc


def plan_outputs(directory, texts, *, mode, validation, source_root, consume_source=False, external=False):
    import re
    directory, source_root = canonical_path(directory), canonical_path(source_root)
    imports = {m for text in texts.values() for m in re.findall(r'^\s*tautrt\s+"([^"]+)"', text, re.M)}
    if len(imports) > 1:
        raise ValueError('conflicting Go runtime import paths')
    runtime_import = next(iter(imports), '')
    path = directory / '.taut-go-outputs.json'
    old = manifest(path, 'go-schema')
    writes = {directory / name: text.encode('utf-8') for name, text in texts.items()}
    if len(writes) != len(texts):
        raise ValueError(f'conflicting Go schema output paths in {directory}; use distinct target filenames')
    deletes = {directory / name for name in old['files'] if name not in texts}
    for target in writes:
        name = target.relative_to(directory).as_posix()
        if _is_alias(target) or (target.exists() and name not in old['files']):
            raise ValueError(f'unknown/handwritten Go output {target}; use a fresh directory or migration')
    roots = {source_root}
    if old.get('source_root'):
        roots.add(canonical_path(old['source_root']))
    user = user_identity(path)
    canonical = Path(__file__).parent / 'runtime'
    for root in roots:
        owner_path = root / '.taut-go-runtime.json'
        if old.get('source_root') and root == canonical_path(old['source_root']) and not owner_path.exists():
            raise ValueError(f'{owner_path}: previous Go runtime owner unavailable; use a fresh output root or explicit migration')
        runtime = manifest(owner_path, 'go-runtime')
        if root == source_root and runtime['files'] and runtime.get('import_path') != runtime_import:
            raise ValueError(f'{owner_path}: cannot remap a Go physical source owner to another import_path; use explicit migration')
        if root == source_root:
            runtime['import_path'] = runtime_import
        if mode in ('source', 'package') or consume_source or owner_path.exists():
            for filename in FILES:
                candidate = root / filename
                if candidate.exists() and filename not in runtime['files']:
                    raise ValueError(f'unknown/handwritten Go runtime {candidate}; use a fresh owner root or explicit migration')
        consuming = (mode != 'source' or external) and consume_source
        if root == source_root and consuming and not owner_path.exists():
            raise ValueError(f'{owner_path}: bound Go source owner unavailable; generate owner first or bind package')
        runtime['users'] = remaining_users(runtime['users'], user)
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
                    raise ValueError(f'unknown/handwritten Go runtime {target}; refusing adoption')
                resource_path = canonical / resource
                contents[name] = resource_path.read_bytes()
                if target in writes:
                    raise ValueError(f'Go schema/runtime output collision {target}')
                writes[target] = contents[name]
        elif desired:
            missing = desired.keys() - runtime['files'].keys()
            if missing:
                raise ValueError(f'Go source owner {root} missing {sorted(missing)}; regenerate owner with required capabilities')
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
