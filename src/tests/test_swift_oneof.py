"""Executed Swift module/nominal-owner, semantic, artifact and output-state proofs."""
import dataclasses
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import pytest
from taut.gen.scaffold import emit, emit_all, swift_api
from taut.gen.swift_runtime import build_foundation, canonical_sources, OWNER, CAPABILITIES
from taut.ir.dsl import Enum, F, Msg, Ref, List, Map, OneOf, Case, STR, INT, BOOL, schema
from taut.ir.load import load_schema
from taut.ir.export import schema_json

ROOT = Path(__file__).resolve().parents[2]
EXAMPLE = ROOT / 'dev-docs/examples/swift-oneof'
SCHEMA = load_schema(EXAMPLE / 'content.taut.py')


def run(args, *, roots=(), ok=True):
    env = dict(os.environ)
    for name in ('PATH', 'LD_LIBRARY_PATH'):
        env[name] = os.pathsep.join(map(str, roots)) + os.pathsep + env.get(name, '')
    result = subprocess.run(list(map(str, args)), capture_output=True, encoding='utf-8', env=env)
    if ok: assert result.returncode == 0, result.stdout + result.stderr
    return result


def compile_module(directory, name, sources, owners=(), *, ok=True):
    directory.mkdir(parents=True, exist_ok=True)
    library = directory / (name + '.dll' if os.name == 'nt' else 'lib' + name + '.so')
    command = ['swiftc', '-emit-library', '-emit-module', '-module-name', name,
               *[part for root, module in owners for part in ('-I', root, '-L', root, '-l' + module)],
               *sources, '-o', library, '-emit-module-path', directory / (name + '.swiftmodule')]
    return library, run(command, roots=[r for r, _ in owners], ok=ok)


def executable(directory, source, sources=(), owners=(), *, ok=True):
    directory.mkdir(parents=True, exist_ok=True)
    main = directory / 'main.swift'; main.write_text(source, encoding='utf-8')
    binary = directory / ('main.exe' if os.name == 'nt' else 'main')
    result = run(['swiftc', *[part for root, module in owners for part in ('-I', root, '-L', root, '-l' + module)],
                  *sources, main, '-o', binary], roots=[r for r, _ in owners], ok=ok)
    return binary, result


@pytest.fixture(scope='module')
def package(tmp_path_factory):
    assert shutil.which('swiftc'), 'activated native Swift readiness toolchain required'
    return build_foundation(tmp_path_factory.mktemp('swift-package') / 'foundation')


@pytest.fixture(scope='module')
def off_package(tmp_path_factory):
    return build_foundation(tmp_path_factory.mktemp('swift-off-package') / 'foundation', validation=False)


@pytest.mark.parametrize('mode', ['source', 'package', None])
def test_python_normalized_conformance(tmp_path, package, mode):
    config = {'swift': {'module': 'TautFoundation', 'artifact': str(package)}} if mode != 'source' else None
    emit(SCHEMA, tmp_path, langs=['swift'], services=[], runtime_mode=mode, validation=True, runtime_bindings=config)
    owner = build_foundation(tmp_path / 'built', source_directory=tmp_path / 'swift') if mode == 'source' else package
    binary, _ = executable(tmp_path / 'app', (EXAMPLE / 'Conformance.swift').read_text(),
                           [tmp_path / 'swift/api.swift'], [(owner, 'TautFoundation')])
    from test_java_oneof import python_rows
    assert run([binary], roots=[owner]).stdout.splitlines() == python_rows()
    if mode == 'source':
        for name, content in canonical_sources().items(): assert (tmp_path / 'swift' / name).read_bytes() == content
    else: assert not (tmp_path / 'swift/cbor.swift').exists()


@pytest.mark.parametrize('mode', ['source', 'package', None])
def test_disabled_metadata_codec_without_engine(tmp_path, off_package, mode):
    binding = {'swift': {'module': 'TautFoundation'}}
    emit(SCHEMA, tmp_path, langs=['swift'], services=[], runtime_mode=mode, runtime_bindings=binding)
    owner = build_foundation(tmp_path / 'built', validation=False, source_directory=tmp_path / 'swift') if mode == 'source' else off_package
    text = (tmp_path / 'swift/api.swift').read_text()
    assert 'func validate(' not in text and 'func isValid(' not in text
    assert not (tmp_path / 'swift/validation.swift').exists() and not (tmp_path / 'swift/reports.swift').exists()
    binary, _ = executable(tmp_path / 'app', '''import TautFoundation
let d=Content.descriptor
precondition(d.fields.count == 6 && d.oneofs.count == 1)
let child=d.fields[3].type.messageDescriptor()
precondition(child.fingerprint == d.fingerprint)
let c=Content(kind:.text)
let copy=try! Content.decode(encode(c.toCbor()))
precondition(copy.text == nil && Content.schemaDescriptor.enums.count == 1)
''', [tmp_path / 'swift/api.swift'], [(owner, 'TautFoundation')])
    run([binary], roots=[owner])


def external(names, module='ChildSchema'):
    return {name: dict(module=module, type=name, owner=OWNER, descriptor_contract=1, codec_contract=1,
                       capabilities=sorted(CAPABILITIES)) for name in names}


@pytest.mark.parametrize('child_mode,parent_mode', [('source', 'source'), ('package', 'package'), ('source', 'package'), ('package', 'source')])
def test_independent_disabled_child_actual_nominal_owner(tmp_path, package, child_mode, parent_mode):
    k = Enum('ChildKind', text=0, empty=1)
    child = schema(k, Child=Msg(kind=F(1, OneOf(k)), text=F(2, STR, Case(kind=k.text))))
    parent = dataclasses.replace(child, messages={**child.messages, **schema(Parent=Msg(child=F(1, Ref('Child')))).messages})
    owner = tmp_path / 'owner'; use_source = 'source' in (child_mode, parent_mode)
    config = {'swift': {'module': 'TautFoundation', **({'source_root': str(owner)} if use_source else {'artifact': str(package)})}}
    if use_source:
        emit(schema(Owner=Msg()), tmp_path / 'owner-user', langs=['swift'], services=[], runtime=True, validation=True, runtime_bindings=config)
        built = build_foundation(tmp_path / 'built', source_directory=owner)
    else: built = package
    emit(child, tmp_path / 'child', langs=['swift'], services=[], runtime_mode=child_mode, runtime_bindings=config)
    child_file = tmp_path / 'child/swift/api.swift'; before = child_file.read_bytes()
    child_lib = tmp_path / 'child-lib'
    compile_module(child_lib, 'ChildSchema', [child_file], [(built, 'TautFoundation')])
    emit(parent, tmp_path / 'parent', langs=['swift'], services=[], runtime_mode=parent_mode, validation=True,
         runtime_bindings=config, swift_external_types=external(('Child', 'ChildKind')))
    parent_lib = tmp_path / 'parent-lib'
    compile_module(parent_lib, 'ParentSchema', [tmp_path / 'parent/swift/api.swift'], [(built, 'TautFoundation'), (child_lib, 'ChildSchema')])
    binary, _ = executable(tmp_path / 'app', '''import TautFoundation
import ChildSchema
import ParentSchema
let p=Parent(child:Child(kind:.text))
let report:TautFoundation.ValidationReport=p.validate()
precondition(report.issues.count == 1 && report.issues[0].path.map {$0.fieldName ?? ""} == ["child","text"])
precondition(!p.isValid() && p.isValid(recursive:false))
let codec:TautFoundation.Cbor=p.child.toCbor()
let _:TautFoundation.MessageDescriptor=Child.descriptor
let _:ChildSchema.Child=p.child
precondition(try! codec.tryGet(1).tryInt() == 0)
''', owners=[(built, 'TautFoundation'), (child_lib, 'ChildSchema'), (parent_lib, 'ParentSchema')])
    run([binary], roots=[built, child_lib, parent_lib])
    assert child_file.read_bytes() == before
    assert 'func validate(' not in before.decode()


def test_native_struct_class_mutual_recursion_shared_values_and_snapshots(tmp_path, package):
    k = Enum('K', text=0)
    s = schema(k, Leaf=Msg(kind=F(1, OneOf(k)), text=F(2, STR, Case(kind=k.text))),
               A=Msg(b=F(1, Ref('B'), optional=True), child=F(2, Ref('Leaf'))),
               B=Msg(a=F(1, Ref('A'), optional=True)),
               Tree=Msg(children=F(1, List(Ref('Tree'))), child=F(2, Ref('Leaf'))),
               Box=Msg(child=F(1, Ref('Leaf'))))
    emit(s, tmp_path, langs=['swift'], services=[], validation=True, runtime_bindings={'swift': {'module': 'TautFoundation'}})
    text = (tmp_path / 'swift/api.swift').read_text()
    for name in ('Leaf', 'Tree', 'Box'): assert 'public struct ' + name in text
    for name in ('A', 'B'): assert 'public final class ' + name in text
    binary, _ = executable(tmp_path / 'app', '''import TautFoundation
let bad=Leaf(kind:.text)
let a=A(child:bad); let b=B(a:a); a.b=b
let cycle=a.validate()
precondition(cycle.issues.map {$0.code} == ["validation.ownership_cycle","oneof.payload_missing"])
a.b=nil; a.child.text=""
precondition(a.isValid() && cycle.issues.count == 2)
var leaf=Leaf(kind:.text); var copy=leaf; copy.text=""; precondition(!leaf.isValid() && copy.isValid())
let tree=Tree(children:[Tree(children:[],child:bad)],child:bad)
let prefix=Array(tree.children.prefix(1))
let root=Tree(children:prefix + [tree],child:bad)
precondition(root.validate().issues.count == 4)
precondition(!root.validate().issues.contains {$0.code == "validation.ownership_cycle"})
let box=Box(child:bad); precondition(box.validate().issues.count == 1)
''', [tmp_path / 'swift/api.swift'], [(package, 'TautFoundation')])
    run([binary], roots=[package])
    _, failure = executable(tmp_path / 'old-struct', 'struct Old { var child:Old? }', ok=False)
    assert failure.returncode != 0 and 'recursively contains' in failure.stderr


@pytest.mark.parametrize('virtual,exhaustive', [(False, False), (False, True), (True, False), (True, True)])
def test_all_oneof_modes_and_metadata_member_names(tmp_path, package, virtual, exhaustive):
    k = Enum('K', name=0, members=1, options=2, case=3)
    s = schema(k, R=Msg(kind=F(1, OneOf(k, virtual=virtual, exhaustive=exhaustive)),
                       payload=F(2, STR, Case(kind=k.case.name), Case(kind=k.case.members), Case(kind=k.case.options), Case(kind=k.case.case))))
    emit(s, tmp_path, langs=['swift'], services=[], validation=True, runtime_bindings={'swift': {'module': 'TautFoundation'}})
    initializer = 'R(payload:"")' if virtual else 'R(kind:.name,payload:"")'
    binary, _ = executable(tmp_path / 'app', 'import TautFoundation\nlet r=' + initializer + '\nlet report=r.validate()\nprecondition(report.isValid)\nprecondition(report.isComplete == ' + str(not virtual).lower() + ')\nprecondition(r.isValid() == report.isComplete)\nprecondition(K.descriptor.members["case"] == 3)\n', [tmp_path / 'swift/api.swift'], [(package, 'TautFoundation')])
    run([binary], roots=[package])


@pytest.mark.parametrize('field,validation', [('descriptor', False), ('tautBinding', False), ('validate', True), ('isValid', True)])
def test_native_names_refuse_before_writes(tmp_path, field, validation):
    with pytest.raises(ValueError, match='collision'):
        emit(schema(R=Msg(**{field: F(1, INT)})), tmp_path, langs=['swift'], services=[], validation=validation, runtime_bindings={'swift': {'module': 'TautFoundation'}})
    assert not list(tmp_path.iterdir())


def test_validation_method_names_allowed_off_and_native_keyword_escaping(tmp_path, off_package):
    k = Enum('K', **{'case': 0})
    s = schema(k, R=Msg(validate=F(1, INT), isValid=F(2, BOOL), protocol=F(3, Ref('K'))))
    emit(s, tmp_path, langs=['swift'], services=[], runtime_bindings={'swift': {'module': 'TautFoundation'}})
    binary, _ = executable(tmp_path / 'app', 'import TautFoundation\nlet r=R(validate:0,isValid:false,protocol:.case)\nprecondition(try! R.decode(encode(r.toCbor())).validate == 0)\n', [tmp_path / 'swift/api.swift'], [(off_package, 'TautFoundation')])
    run([binary], roots=[off_package])


def snapshot(root):
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob('*') if p.is_file()}


@pytest.mark.parametrize('tamper', ['schema', 'runtime', 'owner', 'unknown'])
def test_unknown_modified_outputs_refuse_unchanged(tmp_path, tamper):
    emit(SCHEMA, tmp_path, langs=['swift'], services=[], runtime=True, validation=True, runtime_bindings={'swift': {'module': 'TautFoundation'}})
    target = {'schema': 'api.swift', 'runtime': 'descriptors.swift', 'owner': '.taut-swift-runtime.json', 'unknown': 'handwritten.swift'}[tamper]
    (tmp_path / 'swift' / target).write_text('handwritten or modified')
    before = snapshot(tmp_path)
    if tamper == 'unknown':
        # Arbitrary application files coexist; known runtime filenames do not.
        emit(SCHEMA, tmp_path, langs=['swift'], services=[], runtime=True, validation=False, runtime_bindings={'swift': {'module': 'TautFoundation'}})
        assert (tmp_path / 'swift/handwritten.swift').read_text() == 'handwritten or modified'
    else:
        with pytest.raises((ValueError, json.JSONDecodeError)): emit(SCHEMA, tmp_path, langs=['swift'], services=[], runtime=True, runtime_bindings={'swift': {'module': 'TautFoundation'}})
        assert snapshot(tmp_path) == before


@pytest.mark.parametrize('mode', ['package', None])
def test_retirement_other_users_engine_and_import_remap(tmp_path, mode):
    owner = tmp_path / 'owner'; cfg = {'swift': {'module': 'TautFoundation', 'source_root': str(owner)}}
    emit(SCHEMA, tmp_path / 'a', langs=['swift'], services=[], runtime=True, validation=True, runtime_bindings=cfg)
    emit(SCHEMA, tmp_path / 'b', langs=['swift'], services=[], runtime=True, runtime_bindings=cfg)
    emit(SCHEMA, tmp_path / 'a', langs=['swift'], services=[], runtime_mode=mode,
         runtime_bindings={'swift': {'module': 'TautFoundation'}})
    assert (owner / 'descriptors.swift').exists() and not (owner / 'validation.swift').exists()
    emit(SCHEMA, tmp_path / 'b', langs=['swift'], services=[], runtime_mode=mode,
         runtime_bindings={'swift': {'module': 'TautFoundation'}})
    assert not (owner / 'descriptors.swift').exists()
    emit(SCHEMA, tmp_path / 'a', langs=['swift'], services=[], runtime=True, runtime_bindings=cfg)
    before = snapshot(tmp_path)
    with pytest.raises(ValueError, match='remap'):
        emit(SCHEMA, tmp_path / 'a', langs=['swift'], services=[], runtime=True,
             runtime_bindings={'swift': {'module': 'OtherFoundation', 'source_root': str(owner)}})
    assert snapshot(tmp_path) == before


@pytest.mark.parametrize('cutoff', range(1, 11))
@pytest.mark.parametrize('mode', ['package', None])
@pytest.mark.parametrize('validation', [False, True])
def test_interrupted_retirement_recovers_or_refuses_unchanged(tmp_path, monkeypatch, cutoff, mode, validation):
    from taut.gen.swift_runtime import FILES
    emit(SCHEMA, tmp_path, langs=['swift'], services=[], runtime=True, validation=validation, runtime_bindings={'swift': {'module': 'TautFoundation'}})
    original, unlink, count = os.replace, Path.unlink, [0]
    owner = tmp_path / 'swift'
    def persisted():
        count[0] += 1
        if count[0] == cutoff: raise OSError('interrupted Swift retirement')
    def fail(source, destination):
        original(source, destination)
        if Path(destination).parent == owner: persisted()
    def deleting(path, *args, **kwargs):
        existed = path.exists(); unlink(path, *args, **kwargs)
        if existed and path.parent == owner and path.name in {*FILES, '.taut-swift-runtime.json'}: persisted()
    with monkeypatch.context() as m:
        m.setattr(os, 'replace', fail); m.setattr(Path, 'unlink', deleting)
        try: emit(SCHEMA, tmp_path, langs=['swift'], services=[], runtime_mode=mode, runtime_bindings={'swift': {'module': 'TautFoundation'}})
        except OSError: pass
    before = snapshot(tmp_path)
    try: emit(SCHEMA, tmp_path, langs=['swift'], services=[], runtime_mode=mode, runtime_bindings={'swift': {'module': 'TautFoundation'}})
    except ValueError:
        assert snapshot(tmp_path) == before
    else:
        assert not (tmp_path / 'swift/cbor.swift').exists()


@pytest.mark.parametrize('suffix', ['.', ' ', ':stream', '\\.. \\child', '\\NUL\\child'])
def test_raw_windows_paths_before_coercion(tmp_path, suffix):
    if os.name != 'nt': pytest.skip('Windows namespace policy')
    class RawPath:
        def __fspath__(self): return '\\\\?\\' + str(tmp_path / 'raw') + suffix
    with pytest.raises(ValueError): emit(SCHEMA, RawPath(), langs=['swift'], services=[], runtime=True, runtime_bindings={'swift': {'module': 'TautFoundation'}})
    assert not list(tmp_path.iterdir())


def test_programmatic_and_cli_flags_no_target_execution(tmp_path, monkeypatch):
    import taut.gen.scaffold as scaffold
    from taut.ir.dsl import service
    s = schema(service('Test'), Api=Msg())
    # emit_all's existing service positional argument stays unchanged.
    monkeypatch.setattr(subprocess, 'run', lambda *a, **k: pytest.fail('generation executed target/build tooling'))
    emit_all(s, 'Test', tmp_path, langs=['swift'], runtime=True, validation=True)
    assert 'func validate(' in (tmp_path / 'swift/api.swift').read_text()
    assert (tmp_path / 'swift/validation.swift').exists()
    with pytest.raises(ValueError): emit(s, tmp_path / 'bad', langs=['swift'], runtime=True, runtime_mode='package', runtime_bindings={'swift': {'module': 'TautFoundation'}})


def test_source_binding_requires_one_actual_module(tmp_path):
    with pytest.raises(ValueError, match='explicit module'):
        emit(SCHEMA, tmp_path, langs=['swift'], services=[], runtime_mode='package')
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize('case', ['forward_compat', 'bounds', 'rules', 'enum'])
def test_actual_separately_built_child_replacement_is_rejected(tmp_path, package, case):
    from taut.ir.dsl import option
    k = Enum('K', text=0, empty=1)
    original = schema(k, Child=Msg(kind=F(1, OneOf(k)), text=F(2, STR, Case(kind=k.text))))
    parent = dataclasses.replace(original, messages={**original.messages, **schema(Parent=Msg(child=F(1, Ref('Child')))).messages})
    emit(original, tmp_path / 'child', langs=['swift'], services=[], runtime_bindings={'swift': {'module': 'TautFoundation'}})
    child_lib = tmp_path / 'child-lib'
    compile_module(child_lib, 'ChildSchema', [tmp_path / 'child/swift/api.swift'], [(package, 'TautFoundation')])
    emit(parent, tmp_path / 'parent', langs=['swift'], services=[], validation=True,
         swift_external_types=external(('K', 'Child')), runtime_bindings={'swift': {'module': 'TautFoundation'}})
    binary, _ = executable(tmp_path / 'app', 'import TautFoundation\nlet p=Parent(child:Child(kind:.text))\nprecondition(!p.isValid())\n',
                           [tmp_path / 'parent/swift/api.swift'], [(package, 'TautFoundation'), (child_lib, 'ChildSchema')])
    run([binary], roots=[package, child_lib])
    changed = original
    if case == 'bounds': changed = schema(option.max_depth(9), k, Child=original.messages['Child'])
    if case == 'rules': changed = schema(k, Child=Msg(kind=F(1, Ref('K')), text=F(2, STR, optional=True)))
    if case == 'enum':
        other = Enum('K', text=0, empty=2)
        changed = schema(other, Child=Msg(kind=F(1, OneOf(other)), text=F(2, STR, Case(kind=other.text))))
    emit(changed, tmp_path / 'replacement', langs=['swift'], services=[], forward_compat=case == 'forward_compat', runtime_bindings={'swift': {'module': 'TautFoundation'}})
    compile_module(child_lib, 'ChildSchema', [tmp_path / 'replacement/swift/api.swift'], [(package, 'TautFoundation')])
    # Rebuild against the actual replacement module's native layout while
    # retaining the original generated parent's expected facts. Swift does not
    # promise binary layout resilience for an arbitrary changed child struct.
    binary, _ = executable(tmp_path / 'relinked', 'import TautFoundation\n_ = Parent.descriptor\nlet p=Parent(child:Child(kind:.text))\nprecondition(!p.isValid())\n',
                           [tmp_path / 'parent/swift/api.swift'], [(package, 'TautFoundation'), (child_lib, 'ChildSchema')])
    result = run([binary], roots=[package, child_lib], ok=False)
    assert result.returncode != 0 and 'mismatch' in result.stderr + result.stdout


@pytest.mark.parametrize('case', ['alias', 'owner', 'capabilities', 'codec'])
def test_actual_selected_facade_exports_and_old_noop_guards(tmp_path, package, case):
    facade = tmp_path / 'facade'; facade.mkdir()
    # A harmless exported function gives Windows an import library even when
    # this module otherwise consists entirely of true re-exports.
    text = '@_exported import TautFoundation\npublic func facadeAnchor() {}\n'
    if case != 'alias':
        text += '''public func requireFoundation(_ artifact:String,_ owner:String,_ descriptor:Int,_ codec:Int,_ capabilities:Set<String>) -> TautFoundation.FoundationEvidence {
return TautFoundation.FoundationEvidence("taut.swift.foundation",1,1,["codec.v1","descriptors.v1","oneof.v1"])
}
public func confirmFoundation(_ evidence:TautFoundation.FoundationEvidence,_ owner:String,_ descriptor:Int,_ codec:Int,_ capabilities:Set<String>) {}
'''
        text += {'owner': 'public let foundationOwner="foreign.owner"\n',
                 'codec': 'public let codecContract=99\n',
                 'capabilities': 'public func foundationCapabilities()->Set<String> { [] }\n'}[case]
    (facade / 'Facade.swift').write_text(text)
    compile_module(facade, 'Facade', [facade / 'Facade.swift'], [(package, 'TautFoundation')])
    emit(schema(R=Msg(value=F(1, INT))), tmp_path / 'schema', langs=['swift'], services=[], validation=True,
         runtime_mode='package', runtime_bindings={'swift': {'module': 'Facade'}})
    binary, _ = executable(tmp_path / 'app', 'import TautFoundation\nimport Facade\nlet r=R(value:0)\nlet report:TautFoundation.ValidationReport=r.validate()\nprecondition(report.isValid && report.isComplete)\nlet c:TautFoundation.Cbor=r.toCbor()\nprecondition(try! c.tryGet(1).tryInt() == 0)\n',
                           [tmp_path / 'schema/swift/api.swift'], [(package, 'TautFoundation'), (facade, 'Facade')])
    result = run([binary], roots=[package, facade], ok=case == 'alias')
    if case != 'alias': assert result.returncode != 0 and 'actual selected Swift foundation' in result.stderr + result.stdout


def test_owned_metadata_lazy_links_general_reports_and_unequal_build(tmp_path, package):
    source = '''import TautFoundation
func descriptor(_ fingerprint:String)->MessageDescriptor {
 MessageDescriptor("Child","child.Child",[],[],[],[],[],nil,[:],["max_depth":.int(32),"max_encoded_len":.null],fingerprint)
}
var selected=descriptor("one")
let link=TypeDescriptor.message("Child",{selected})
precondition(link.messageDescriptor().fingerprint == "one")
selected=descriptor("two")
precondition(link.messageDescriptor().fingerprint == "one")
var path=[PathSegment.forField("original")]
let issue=ValidationIssue("app.custom","app.rule.v8",path,"snapshot")
var issues=[issue]; let r=ValidationReport(issues)
path[0] = .forField("changed"); issues.removeAll()
precondition(r.issues[0].path[0].fieldName == "original" && !r.isValid && r.isComplete)
var options:[String:MetadataValue] = ["owned":.array([.int(1)])]
let e=EnumDescriptor("K","K",["name":0],options,[:],"e")
options["owned"] = .null
precondition(e.options["owned"] == .array([.int(1)]))
'''
    binary, _ = executable(tmp_path / 'app', source, owners=[(package, 'TautFoundation')])
    run([binary], roots=[package])
    renamed = tmp_path / 'compatible'; renamed.mkdir()
    for name, content in canonical_sources().items():
        if name == 'descriptors.swift': content = content.replace(b'swift-oneof-reference.1', b'compatible.patch.27')
        (renamed / name).write_bytes(content)
    owner = build_foundation(tmp_path / 'built', source_directory=renamed)
    emit(schema(R=Msg()), tmp_path / 'schema', langs=['swift'], services=[], validation=True,
         runtime_mode='package', runtime_bindings={'swift': {'module': 'TautFoundation', 'artifact': str(owner)}})
    binary, _ = executable(tmp_path / 'compatible-app', 'import TautFoundation\nprecondition(foundationBuild == "compatible.patch.27" && R().isValid())\n',
                           [tmp_path / 'schema/swift/api.swift'], [(owner, 'TautFoundation')])
    run([binary], roots=[owner])


def test_boolean_path_does_not_construct_reports(tmp_path):
    sources = tmp_path / 'sources'; sources.mkdir()
    for name, content in canonical_sources().items():
        if name == 'reports.swift':
            content = content.replace(b'self.code = code;', b'preconditionFailure("diagnostic constructed"); self.code = code;')
            content = content.replace(b'self.rule = rule;', b'preconditionFailure("diagnostic constructed"); self.rule = rule;')
            content = content.replace(b'self.issues = issues;', b'preconditionFailure("report constructed"); self.issues = issues;')
        (sources / name).write_bytes(content)
    owner = build_foundation(tmp_path / 'built', source_directory=sources)
    emit(SCHEMA, tmp_path / 'schema', langs=['swift'], services=[], validation=True, runtime_bindings={'swift': {'module': 'TautFoundation'}})
    binary, _ = executable(tmp_path / 'app', 'import TautFoundation\nlet invalid=Content(kind:.text)\nprecondition(!invalid.isValid())\ninvalid.text=""\nprecondition(invalid.isValid())\nprecondition(!Virtual(child:invalid).isValid())\n',
                           [tmp_path / 'schema/swift/api.swift'], [(owner, 'TautFoundation')])
    run([binary], roots=[owner])


def test_old_child_artifact_and_wrong_category_fail_explicitly(tmp_path, package):
    child = schema(Child=Msg(value=F(1, INT)))
    parent = dataclasses.replace(child, messages={**child.messages, **schema(Parent=Msg(child=F(1, Ref('Child')))).messages})
    old = tmp_path / 'old'; old.mkdir()
    (old / 'Child.swift').write_text('''import TautFoundation
public struct Child {
public var value:Int64
public init(value:Int64) {self.value=value}
public func toCbor()->Cbor { .map([(1,.int(value))]) }
public static func fromCbor(_ c:Cbor)throws->Child { Child(value:try c.tryGet(1).tryInt()) }
}
''')
    compile_module(old, 'ChildSchema', [old / 'Child.swift'], [(package, 'TautFoundation')])
    emit(parent, tmp_path / 'parent', langs=['swift'], services=[], validation=True, swift_external_types=external(('Child',)), runtime_bindings={'swift': {'module': 'TautFoundation'}})
    _, result = executable(tmp_path / 'app', 'let p=Parent(child:Child(value:0))\n_ = p.isValid()\n',
                           [tmp_path / 'parent/swift/api.swift'], [(package, 'TautFoundation'), (old, 'ChildSchema')], ok=False)
    assert result.returncode != 0 and 'descriptor' in result.stderr and 'tautBinding' in result.stderr
    binary, _ = executable(tmp_path / 'wrong', '''import TautFoundation
let e=EnumDescriptor("Other","Other",["x":0],[:],[:],"e")
_ = TypeDescriptor.enumeration("Expected",{e}).enumDescriptor()
''', owners=[(package, 'TautFoundation')])
    result = run([binary], roots=[package], ok=False)
    assert result.returncode != 0 and 'incompatible Swift enum link' in result.stderr


def test_equivalent_reordered_actual_child_artifact_is_accepted(tmp_path, package):
    k = Enum('K', one=1, two=2, empty=3)
    child = schema(k, Child=Msg(kind=F(1, OneOf(k)), first=F(2, STR, Case(kind=k.one)), second=F(3, INT, Case(kind=k.two))))
    parent = dataclasses.replace(child, messages={**child.messages, **schema(Parent=Msg(child=F(1, Ref('Child')))).messages})
    emit(parent, tmp_path / 'parent', langs=['swift'], services=[], validation=True, swift_external_types=external(('K', 'Child')), runtime_bindings={'swift': {'module': 'TautFoundation'}})
    message = child.messages['Child']; enumeration = child.enums['K']
    reordered = dataclasses.replace(child, messages={'Child': dataclasses.replace(message, fields=tuple(reversed(message.fields)))},
                                    enums={'K': dataclasses.replace(enumeration, members=dict(reversed(list(enumeration.members.items()))))})
    emit(reordered, tmp_path / 'child', langs=['swift'], services=[], runtime_bindings={'swift': {'module': 'TautFoundation'}})
    owner = tmp_path / 'child-lib'
    compile_module(owner, 'ChildSchema', [tmp_path / 'child/swift/api.swift'], [(package, 'TautFoundation')])
    binary, _ = executable(tmp_path / 'app', 'import TautFoundation\nprecondition(Parent(child:Child(kind:.empty)).isValid())\n',
                           [tmp_path / 'parent/swift/api.swift'], [(package, 'TautFoundation'), (owner, 'ChildSchema')])
    run([binary], roots=[package, owner])


def test_legacy_supplied_same_module_default_and_multiple_schemas(tmp_path):
    emit(schema(First=Msg(value=F(1, INT))), tmp_path / 'first', langs=['swift'], services=[], validation=True)
    emit(schema(Second=Msg(value=F(1, INT))), tmp_path / 'second', langs=['swift'], services=[], validation=True)
    assert not (tmp_path / 'first/swift/cbor.swift').exists()
    assert 'import TautFoundation' not in (tmp_path / 'first/swift/api.swift').read_text()
    owner = tmp_path / 'supplied'; owner.mkdir()
    for name, content in canonical_sources().items(): (owner / name).write_bytes(content)
    # swiftc requires unique basenames within a module. Build copies retain
    # exactly the generated bytes; neither schema is rewritten/regenerated.
    first, second = tmp_path / 'First.swift', tmp_path / 'Second.swift'
    shutil.copyfile(tmp_path / 'first/swift/api.swift', first)
    shutil.copyfile(tmp_path / 'second/swift/api.swift', second)
    binary, _ = executable(tmp_path / 'app', 'let a=First(value:0); let b=Second(value:0)\nlet r:ValidationReport=a.validate()\nprecondition(r.isValid && b.isValid())\nlet reports:[ValidationReport]=[a.validate(),b.validate()]\nprecondition(reports.count == 2)\nprecondition(try! First.decode(encode(a.toCbor())).value == 0)\n',
                           [*owner.glob('*.swift'), first, second])
    run([binary])


@pytest.mark.parametrize('enabled', [False, True])
def test_default_flat_supplied_independent_disabled_child(tmp_path, enabled):
    k = Enum('K', text=0, empty=1)
    child = schema(k, Child=Msg(kind=F(1, OneOf(k)), text=F(2, STR, Case(kind=k.text))))
    parent = dataclasses.replace(child, messages={**child.messages, **schema(Parent=Msg(child=F(1, Ref('Child')))).messages})
    emit(child, tmp_path / 'child', langs=['swift'], services=[])
    before = (tmp_path / 'child/swift/api.swift').read_bytes()
    # Empty dependency module explicitly means the same application module;
    # its separately generated type is reused, never regenerated or aliased.
    emit(parent, tmp_path / 'parent', langs=['swift'], services=[], validation=enabled,
         swift_external_types=external(('K', 'Child'), module=''))
    owner = tmp_path / 'supplied'; owner.mkdir()
    for name, content in canonical_sources(validation=enabled).items(): (owner / name).write_bytes(content)
    child_source, parent_source = tmp_path / 'Child.swift', tmp_path / 'Parent.swift'
    shutil.copyfile(tmp_path / 'child/swift/api.swift', child_source)
    shutil.copyfile(tmp_path / 'parent/swift/api.swift', parent_source)
    source = 'let p=Parent(child:Child(kind:.text))\nprecondition(Parent.schemaDescriptor.messages.count == 2)\n'
    if enabled: source += 'let r:ValidationReport=p.validate()\nprecondition(!r.isValid && !p.isValid() && p.isValid(recursive:false))\n'
    else: source += 'precondition(Parent.descriptor.fields[0].type.messageDescriptor().fingerprint == Child.descriptor.fingerprint)\n'
    source += 'let _:Cbor=p.toCbor()\n'
    binary, _ = executable(tmp_path / 'app', source, [*owner.glob('*.swift'), child_source, parent_source])
    run([binary])
    assert (tmp_path / 'child/swift/api.swift').read_bytes() == before
    assert child_source.read_bytes() == before
    assert 'func validate(' not in before.decode()


def test_binding_type_mismatch_and_general_invalid_constraints_are_configuration(tmp_path, package):
    emit(schema(One=Msg(value=F(1, INT)), Other=Msg(value=F(1, INT))), tmp_path / 'schema', langs=['swift'], services=[],
         runtime_bindings={'swift': {'module': 'TautFoundation'}})
    binary, _ = executable(tmp_path / 'mismatch', 'import TautFoundation\nlet b=One.tautBinding\n_ = MessageBinding<Other>(One.descriptor,{_,_ in true},{_,_ in nil},{_,_ in .null},{_,_,_,_ in true})\n',
                           [tmp_path / 'schema/swift/api.swift'], [(package, 'TautFoundation')])
    result = run([binary], roots=[package], ok=False)
    assert result.returncode != 0 and 'binding/descriptor type mismatch' in result.stderr
    binary, _ = executable(tmp_path / 'constraint', 'import TautFoundation\n_ = ConstraintDescriptor("app.unsupported.v9",[:])\n', owners=[(package, 'TautFoundation')])
    result = run([binary], roots=[package], ok=False)
    assert result.returncode != 0 and 'unsupported Swift constraint grammar' in result.stderr


def test_shared_enabled_consumer_retains_engine_until_last_use(tmp_path):
    owner = tmp_path / 'owner'; config = {'swift': {'module': 'TautFoundation', 'source_root': str(owner)}}
    emit(SCHEMA, tmp_path / 'source', langs=['swift'], services=[], runtime=True, validation=True, runtime_bindings=config)
    emit(SCHEMA, tmp_path / 'consumer', langs=['swift'], services=[], runtime_mode='package', validation=True, runtime_bindings=config)
    emit(SCHEMA, tmp_path / 'source', langs=['swift'], services=[], runtime=True, validation=False, runtime_bindings=config)
    assert (owner / 'validation.swift').exists() and (owner / 'reports.swift').exists()
    emit(SCHEMA, tmp_path / 'consumer', langs=['swift'], services=[], runtime_mode='package', validation=False, runtime_bindings=config)
    assert (owner / 'descriptors.swift').exists() and not (owner / 'validation.swift').exists()


@pytest.mark.parametrize('mode,alias,validation', [('source', False, False), ('source', True, True), ('package', False, True), (None, False, False)])
def test_cli_binding_flags_forward_exact_native_bytes(tmp_path, mode, alias, validation):
    ir = tmp_path / 'schema.ir.json'; ir.write_text(json.dumps(schema_json(SCHEMA)))
    config = {'swift': {'module': 'TautFoundation'}}
    binding = tmp_path / 'bindings.json'; binding.write_text(json.dumps(config))
    flags = (['--runtime', mode] if mode else []) + (['--with-runtime'] if alias else []) + (['--with-validation'] if validation else [])
    run([sys.executable, '-m', 'taut.cli', 'gen', ir, '--out', tmp_path / 'cli', '--lang', 'swift', '--api-only', '--runtime-bindings', binding, *flags])
    emit(SCHEMA, tmp_path / 'api', langs=['swift'], services=[], runtime_mode=mode, runtime=alias,
         validation=validation, runtime_bindings=config)
    assert (tmp_path / 'cli/swift/api.swift').read_bytes() == (tmp_path / 'api/swift/api.swift').read_bytes()


@pytest.mark.parametrize('args', [['--with-runtime', '--runtime', 'package'], ['--runtime', 'source', '--runtime', 'package'], ['--runtime', 'unknown']])
def test_cli_conflicts_refuse_before_outputs(tmp_path, args):
    ir = tmp_path / 'schema.ir.json'; ir.write_text(json.dumps(schema_json(SCHEMA)))
    result = run([sys.executable, '-m', 'taut.cli', 'gen', ir, '--out', tmp_path / 'output', '--lang', 'swift', '--api-only', *args], ok=False)
    assert result.returncode != 0 and not (tmp_path / 'output').exists()


def test_split_nominal_foundation_owners_reject_actual_child_module(tmp_path, package):
    other = build_foundation(tmp_path / 'other', module='OtherFoundation')
    child = schema(Child=Msg(value=F(1, INT)))
    parent = dataclasses.replace(child, messages={**child.messages, **schema(Parent=Msg(child=F(1, Ref('Child')))).messages})
    emit(child, tmp_path / 'child', langs=['swift'], services=[], runtime_bindings={'swift': {'module': 'OtherFoundation'}})
    child_lib = tmp_path / 'child-lib'
    compile_module(child_lib, 'ChildSchema', [tmp_path / 'child/swift/api.swift'], [(other, 'OtherFoundation')])
    emit(parent, tmp_path / 'parent', langs=['swift'], services=[], validation=True,
         runtime_bindings={'swift': {'module': 'TautFoundation'}}, swift_external_types=external(('Child',)))
    _, result = executable(tmp_path / 'app', 'let p=Parent(child:Child(value:0))\n_ = p.isValid()\n',
                           [tmp_path / 'parent/swift/api.swift'], [(package, 'TautFoundation'), (other, 'OtherFoundation'), (child_lib, 'ChildSchema')], ok=False)
    assert result.returncode != 0 and 'cannot convert' in result.stderr and 'MessageDescriptor' in result.stderr


def test_actual_native_names_allow_nonpython_fields_and_qualified_runtime_names(tmp_path, package):
    s = schema(ValidationReport=Msg(__value=F(1, INT)), MetadataValue=Msg(value=F(1, INT)))
    emit(s, tmp_path, langs=['swift'], services=[], validation=True, runtime_bindings={'swift': {'module': 'TautFoundation'}})
    binary, _ = executable(tmp_path / 'app', 'import TautFoundation\nlet native=ValidationReport(__value:0)\nlet report:TautFoundation.ValidationReport=native.validate()\nprecondition(report.isValid && MetadataValue(value:0).isValid())\nprecondition(ValidationReport.descriptor.fields[0].name == "__value")\n',
                           [tmp_path / 'swift/api.swift'], [(package, 'TautFoundation')])
    run([binary], roots=[package])


@pytest.mark.parametrize('enabled', [False, True])
@pytest.mark.parametrize('module', ['', 'TautFoundation'])
def test_attributed_native_surface_goldens(enabled, module):
    s = load_schema(EXAMPLE / 'surface.taut.py')
    name = ('imported' if module else 'flat') + ('-on.swift' if enabled else '-off.swift')
    assert swift_api(s, validation=enabled, runtime_module=module) == (EXAMPLE / 'golden' / name).read_text()


def test_signed_i64_extreme_discriminators_and_zero_presence(tmp_path, package):
    k = Enum('K', low=-(1 << 63), high=(1 << 63)-1, zero=0)
    s = schema(k, R=Msg(kind=F(1, OneOf(k, exhaustive=True)), value=F(2, INT, Case(kind=k.low), Case(kind=k.high)),
                       flag=F(3, BOOL, Case(kind=k.zero))))
    emit(s, tmp_path, langs=['swift'], services=[], validation=True, runtime_bindings={'swift': {'module': 'TautFoundation'}})
    binary, _ = executable(tmp_path / 'app', '''import TautFoundation
var r=R(kind:.low,value:0)
precondition(r.isValid() && K.descriptor.members["low"] == Int64.min)
precondition(try! R.decode(encode(r.toCbor())).kind == .low)
r.kind = .high; precondition(r.isValid())
precondition(try! R.decode(encode(r.toCbor())).kind == .high)
r.kind = .zero; r.value=nil; r.flag=false
precondition(r.isValid())
''', [tmp_path / 'swift/api.swift'], [(package, 'TautFoundation')])
    run([binary], roots=[package])


def test_literal_backslash_and_control_metadata_identity_is_exact(tmp_path, package):
    identity = 'literal\\b\\u1234\\n"quoted"\x01'
    emit(schema(R=Msg(value=F(1, INT))), tmp_path, langs=['swift'], services=[], schema_identity=identity,
         runtime_bindings={'swift': {'module': 'TautFoundation'}})
    expected = '[' + ','.join(str(n) for n in (identity + '.R').encode()) + ']'
    binary, _ = executable(tmp_path / 'app', 'import TautFoundation\nprecondition(Array(R.descriptor.qualifiedName.utf8) == ' + expected + ')\n',
                           [tmp_path / 'swift/api.swift'], [(package, 'TautFoundation')])
    run([binary], roots=[package])


def test_empty_native_enum_rejected_before_outputs(tmp_path):
    with pytest.raises(ValueError, match='nonempty'):
        emit(schema(Enum('Empty')), tmp_path, langs=['swift'], services=[])
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize('case', ['exhaustive', 'duplicate', 'ownership', 'unknown', 'flag'])
def test_native_schema_rules_fail_before_outputs(tmp_path, case):
    k = Enum('K', one=0, two=1); other = Enum('Other', one=0)
    if case == 'exhaustive':
        s = schema(k, R=Msg(kind=F(1, OneOf(k, exhaustive=True)), value=F(2, STR, Case(kind=k.one))))
    elif case == 'duplicate':
        s = schema(k, R=Msg(kind=F(1, OneOf(k)), a=F(2, STR, Case(kind=k.one)), b=F(3, INT, Case(kind=k.one))))
    elif case == 'ownership':
        s = schema(k, other, R=Msg(kind=F(1, OneOf(k)), a=F(2, STR, Case(kind=other.one))))
    elif case == 'unknown':
        s = schema(k, R=Msg(kind=F(1, OneOf(k)), a=F(2, STR, Case(missing=k.one))))
    else:
        s = schema(k, R=Msg(kind=F(1, OneOf(k))))
        m = s.messages['R']; f = m.fields[0]
        s = dataclasses.replace(s, messages={'R': dataclasses.replace(m, fields=(dataclasses.replace(f, oneof=dataclasses.replace(f.oneof, virtual=1)),))})
    with pytest.raises(ValueError): emit(s, tmp_path, langs=['swift'], services=[], validation=True)
    assert not list(tmp_path.iterdir())


def test_native_emoji_identifiers_from_ir_preserve_report_names(tmp_path, package):
    from taut.ir.load import schema_from_json
    k = Enum('Compass', document=0, empty=1)
    doc = schema_json(schema(k, Content=Msg(kind=F(1, OneOf(k)), payload=F(2, STR, Case(kind=k.document)))))
    # Python's authoring namespace has its own identifier rules. Native IR
    # carries Swift identifiers directly, without changing the user's DSL.
    doc['enums'][0]['name'] = '🧭'
    doc['enums'][0]['members'] = {'📄': 0, 'empty': 1}
    doc['enums'][0]['member_options'] = {'📄': {}, 'empty': {}}
    doc['messages'][0]['name'] = '📦'
    ctrl, payload = doc['messages'][0]['fields']
    ctrl['type']['name'] = '🧭'; ctrl['oneof']['enum'] = '🧭'
    payload['name'] = '👩‍💻'; payload['cases'][0]['enum'] = '🧭'; payload['cases'][0]['member'] = '📄'
    s = schema_from_json(doc)
    emit(s, tmp_path, langs=['swift'], services=[], validation=True, runtime_bindings={'swift': {'module': 'TautFoundation'}})
    binary, _ = executable(tmp_path / 'app', '''import TautFoundation
var draft=📦(kind:.📄)
let issue=draft.validate().issues[0]
precondition(issue.path[0].fieldName == "👩‍💻")
precondition(📦.descriptor.name == "📦" && 🧭.descriptor.members["📄"] == 0)
draft.👩‍💻=""
precondition(draft.isValid() && (try! 📦.decode(encode(draft.toCbor()))).👩‍💻 == "")
''', [tmp_path / 'swift/api.swift'], [(package, 'TautFoundation')])
    run([binary], roots=[package])


def test_existing_valid_native_enum_case_spellings_remain_supported(tmp_path, package):
    e = Enum('NativeCases', rawValue=0, hashValue=1, hash=2, fromCbor=3, Cbor=4, Int64=5,
             EnumDescriptor=6, SchemaDescriptor=7, TautFoundation=8)
    emit(schema(e), tmp_path, langs=['swift'], services=[], runtime_bindings={'swift': {'module': 'TautFoundation'}})
    binary, _ = executable(tmp_path / 'app', '''import TautFoundation
precondition(try! NativeCases.fromCbor(Cbor.int(0)) == .rawValue)
precondition(NativeCases.descriptor.members["fromCbor"] == 3)
precondition(NativeCases.schemaDescriptor.enums.count == 1)
''', [tmp_path / 'swift/api.swift'], [(package, 'TautFoundation')])
    run([binary], roots=[package])


@pytest.mark.parametrize('name', ['validateRecord', 'isRecordValid'])
def test_flat_enabled_engine_helper_collisions_fail_prewrite(tmp_path, name):
    with pytest.raises(ValueError, match='collision'):
        emit(schema(R=Msg(**{name: F(1, INT)})), tmp_path, langs=['swift'], services=[], validation=True)
    assert not list(tmp_path.iterdir())


def test_imported_qualified_engine_helpers_allow_native_fields(tmp_path, package):
    fields = ['validateRecord', 'isRecordValid', 'MessageDescriptor', 'SchemaDescriptor', 'MessageBinding', 'ValidationReport']
    s = schema(R=Msg(**{n: F(i+1, INT) for i, n in enumerate(fields)}))
    emit(s, tmp_path, langs=['swift'], services=[], validation=True, runtime_bindings={'swift': {'module': 'TautFoundation'}})
    binary, _ = executable(tmp_path / 'app', 'import TautFoundation\nlet r=R(' + ','.join(n+':0' for n in fields) + ')\nprecondition(r.isValid() && r.validate().isComplete)\n',
                           [tmp_path / 'swift/api.swift'], [(package, 'TautFoundation')])
    run([binary], roots=[package])


@pytest.mark.parametrize('enabled', [False, True])
@pytest.mark.parametrize('name,placement', [(name, placement)
    for name in ('Data', 'NSLock', 'ObjectIdentifier', 'AnyObject', 'Void')
    for placement in ('flat', 'imported')] + [('Void', 'source'), ('Void', 'package')])
def test_native_helper_type_names_compile_in_each_runtime_scope(tmp_path, package, off_package, name, enabled, placement):
    record = schema(**{name: Msg(value=F(1, INT))})
    config = {'swift': {'module': 'TautFoundation'}} if placement != 'flat' else None
    emit(record, tmp_path, langs=['swift'], services=[], validation=enabled, runtime_bindings=config,
         runtime_mode=placement if placement in ('source', 'package') else None)
    owners, sources = [], [tmp_path / 'swift/api.swift']
    if placement == 'flat':
        supplied = tmp_path / 'supplied'; supplied.mkdir()
        for filename, content in canonical_sources(validation=enabled).items():
            target = supplied / filename; target.write_bytes(content); sources.append(target)
    else:
        owner = build_foundation(tmp_path / 'built', validation=enabled, source_directory=tmp_path / 'swift') if placement == 'source' else package if enabled else off_package
        owners = [(owner, 'TautFoundation')]
    binary, _ = executable(tmp_path / 'app',
        'let value = ' + name + '(value: 7)\nprecondition(value.value == 7)\n'
        'precondition(' + name + '.descriptor.fields.count == 1)\n'
        + ('precondition(value.isValid() && value.validate().isComplete)\n' if enabled else ''), sources, owners)
    run([binary], roots=[root for root, _ in owners])


@pytest.mark.parametrize('enabled', [False, True])
@pytest.mark.parametrize('placement', ['source', 'package', 'supplied'])
@pytest.mark.parametrize('kind', ['message', 'enum'])
def test_foundation_module_shadow_has_explicit_imported_route(tmp_path, package, off_package, enabled, placement, kind):
    record = schema(Foundation=Msg(value=F(1, INT))) if kind == 'message' else schema(Enum('Foundation', ok=1))
    emit(record, tmp_path, langs=['swift'], services=[], validation=enabled,
         runtime_mode=placement if placement != 'supplied' else None,
         runtime_bindings={'swift': {'module': 'TautFoundation'}})
    owner = build_foundation(tmp_path / 'built', validation=enabled, source_directory=tmp_path / 'swift') if placement == 'source' else package if enabled else off_package
    source = ('let value = Foundation(value: 7)\nprecondition(value.value == 7)\n'
              if kind == 'message' else 'let value = Foundation.ok\nprecondition(value.rawValue == 1)\n')
    binary, _ = executable(tmp_path / 'app', source + '_ = Foundation.descriptor\n',
                           [tmp_path / 'swift/api.swift'], [(owner, 'TautFoundation')])
    run([binary], roots=[owner])


@pytest.mark.parametrize('kind', ['message', 'enum'])
@pytest.mark.parametrize('name', ['Foundation', 'Swift'])
def test_foundation_flat_collision_refuses_before_locks(tmp_path, monkeypatch, kind, name):
    record = schema(**{name: Msg(value=F(1, INT))}) if kind == 'message' else schema(Enum(name, ok=1))
    attempted = []; original = Path.open
    def observe(path, *args, **kwargs):
        if args and args[0] == 'xb': attempted.append(path)
        return original(path, *args, **kwargs)
    monkeypatch.setattr(Path, 'open', observe)
    message = 'Foundation.*explicit imported runtime module' if name == 'Foundation' else 'Swift.*reserved'
    with pytest.raises(ValueError, match=message):
        emit(record, tmp_path / 'output', langs=['swift'], services=[])
    assert attempted == [] and not (tmp_path / 'output').exists()
