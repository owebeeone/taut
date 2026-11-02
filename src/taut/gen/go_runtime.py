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
    import sys
    from .owned_runtime import manifest as owned_manifest
    return owned_manifest(sys.modules[__name__], path, kind)


LABEL = 'Go'
TARGET = 'go'


def runtime_imports(texts):
    import re
    return {m for text in texts.values() for m in re.findall(r'^\s*tautrt\s+"([^"]+)"', text, re.M)}


def plan_outputs(directory, texts, *, mode, validation, source_root, consume_source=False, external=False):
    import sys
    from .owned_runtime import plan_outputs as plan_owned_outputs
    return plan_owned_outputs(sys.modules[__name__], directory, texts, mode=mode,
        validation=validation, source_root=source_root, consume_source=consume_source, external=external)
