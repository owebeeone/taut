"""Rust implementation of the Python reference corpus and delivery contract."""
from pathlib import Path
import json
import subprocess

import pytest

from taut.gen.scaffold import emit, rust_api
from taut.ir.dsl import BOOL, INT, STR, Case, Enum, F, List, Map, Msg, OneOf, Ref, schema
from taut.ir.load import load_schema
from taut.ir.model import Scalar, MsgRef, EnumRef, ListOf, MapOf

ROOT = Path(__file__).resolve().parents[2]
RUNTIME = ROOT / 'src/taut/gen/runtime'
EXAMPLE = ROOT / 'dev-docs/examples/python-oneof/content.taut.py'


def run(args, *, success=True):
    result = subprocess.run(list(map(str, args)), capture_output=True, text=True)
    if success:
        assert result.returncode == 0, result.stdout + result.stderr
    else:
        assert result.returncode != 0, result.stdout + result.stderr
    return result


def program(directory, source, *, validation=True, dependencies=(), name='probe', library=False):
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / (name + '.rs')
    path.write_text(source, encoding='utf-8', newline='\n')
    target = directory / (('lib' + name + '.rlib') if library else name + '.exe')
    args = ['rustc', '--edition=2021', '--crate-name', name, path, '-o', target]
    if library:
        args += ['--crate-type=lib']
    for dependency, artifact in dependencies:
        args += ['--extern', f'{dependency}={artifact}', '-L', f'dependency={artifact.parent}']
    run(args)
    return target


@pytest.fixture(scope='module')
def foundation(tmp_path_factory):
    directory = tmp_path_factory.mktemp('rust-foundation-package')
    crate = ROOT / 'rust/taut-foundation/src/lib.rs'
    target = directory / 'libtaut_foundation.rlib'
    run(['rustc', '--edition=2021', '--crate-name', 'taut_foundation', '--crate-type=lib',
         '--cfg', 'feature="validation"', crate, '-o', target])
    return target


@pytest.fixture(scope='module')
def foundation_descriptors(tmp_path_factory):
    directory=tmp_path_factory.mktemp('rust-foundation-without-engine')
    target=directory/'libtaut_foundation.rlib'
    run(['rustc','--edition=2021','--crate-name','taut_foundation','--crate-type=lib',
        ROOT/'rust/taut-foundation/src/lib.rs','-o',target])
    return target


def native_schema():
    return load_schema(EXAMPLE)


def source_modules(validation=True):
    return 'extern crate alloc; pub mod cbor; pub use cbor::descriptors; ' + ('pub mod validation; ' if validation else '') + 'pub mod api;\n'


BEHAVIOR = r'''
use api::*;
use foundation::validation::*;
fn parity(value: &Content, good: bool) {
    for recursive in [false, true] {
        let options = ValidationOptions { recursive };
        let report = value.validate_with_options(options);
        assert_eq!(value.is_valid_with_options(options), report.is_valid() && report.is_complete());
        assert_eq!(value.is_valid_with_options(options), good);
    }
}
fn main() {
    for value in [
        Content { kind: ContentKind::Number, number: Some(0), ..Default::default() },
        Content { kind: ContentKind::Flag, flag: Some(false), ..Default::default() },
        Content { kind: ContentKind::Text, text: Some(String::new()), ..Default::default() },
        Content { kind: ContentKind::Items, items: Some(Vec::new()), ..Default::default() },
        Content { kind: ContentKind::Empty, ..Default::default() },
    ] { parity(&value, true); }
    let mut draft = Content { kind: ContentKind::Number, text: Some("extra".into()), ..Default::default() };
    let snapshot = draft.validate();
    assert_eq!(snapshot.issues().iter().map(|i| i.code()).collect::<Vec<_>>(), vec!["oneof.payload_unexpected", "oneof.payload_missing"]);
    assert_eq!(snapshot.issues()[0].rule(), "taut.oneof.v1");
    assert_eq!(snapshot.issues()[0].path()[0].field_name(), Some("text"));
    let bytes = foundation::cbor::encode(&draft.to_cbor());
    draft = Content::decode(&bytes).unwrap();
    assert_eq!(draft.text.as_deref(), Some("extra"));
    parity(&draft, false);
    draft.text = None; draft.number = Some(0); parity(&draft, true);
    assert_eq!(snapshot.issues().len(), 2);
    assert_eq!(draft.to_cbor().map_entries().len(), 5);
    let invalid = Content::default();
    let envelope = Envelope { content: invalid.clone() };
    assert!(!envelope.is_valid());
    assert!(envelope.is_valid_with_options(ValidationOptions { recursive: false }));
    assert_eq!(envelope.validate_with_options(ValidationOptions { recursive: false }).scope(), "local");
    assert_eq!(envelope.validate().issues()[0].path()[0].field_name(), Some("content"));
    let mut virtual_root = VirtualEnvelope { content: Some(invalid.clone()) };
    assert_eq!(virtual_root.validate().deferred_checks().len(), 1);
    assert_eq!(virtual_root.validate().issues().len(), 1);
    virtual_root.content.as_mut().unwrap().text = Some("".into());
    let report = virtual_root.validate();
    assert!(report.is_valid()); assert!(!report.is_complete()); assert!(!virtual_root.is_valid());
    assert_eq!(report.deferred_checks()[0].reason_code(), "oneof.virtual_deferred");
    let tree = Tree { content: None, children: vec![Tree { content: Some(invalid.clone()), children: vec![] }] };
    assert_eq!(tree.validate().issues()[0].path()[1].index(), Some(0));
    let mut by_key = std::collections::BTreeMap::new();
    by_key.insert("aa".into(), invalid.clone()); by_key.insert("b".into(), invalid);
    let collection = Collection { entries: vec![], by_key };
    assert_eq!(collection.validate().issues()[0].path()[1].key_cbor_base64(), Some("YWI="));
    assert_eq!(collection.validate().issues()[1].path()[1].key_cbor_base64(), Some("YmFh"));
    assert!(core::ptr::eq(Content::descriptor(), Content::descriptor()));
    assert_eq!(SCHEMA_DESCRIPTOR.ir_version(), 3);
    let report = ValidationReport::new(vec![ValidationIssue::new("future.code", "future.rule", vec![PathSegment::for_index(2)], "future")], vec![], "local");
    assert!(!report.is_valid()); assert!(report.is_complete());
    println!("presence/drafts/snapshots/recursive/virtual/map/metadata/open-reports PASS");
}
'''


@pytest.mark.parametrize('mode', ['source', 'package', None])
def test_native_behavior_both_distributions_and_supplied(tmp_path, foundation, mode):
    emit(native_schema(), tmp_path, langs=['rust'], services=[], validation=True, runtime_mode=mode)
    d = tmp_path / 'rust'
    if mode == 'source':
        prefix = source_modules() + 'use crate as foundation;\n'
        dependencies = ()
    elif mode == 'package':
        prefix = 'extern crate alloc; mod api; use taut_foundation as foundation;\n'
        dependencies = [('taut_foundation', foundation)]
    else:
        prefix = 'extern crate alloc; pub use taut_foundation::{cbor,descriptors,validation}; mod api; use taut_foundation as foundation;\n'
        dependencies = [('taut_foundation', foundation)]
        assert not (d/'cbor.rs').exists()
    result = run([program(d, prefix + BEHAVIOR, dependencies=dependencies)])
    assert 'PASS' in result.stdout


@pytest.mark.parametrize('mode', ['source', 'package', None])
def test_descriptor_only_no_std_without_engine(tmp_path, foundation_descriptors, mode):
    foundation=foundation_descriptors
    emit(native_schema(), tmp_path, langs=['rust'], services=[], runtime_mode=mode)
    d = tmp_path/'rust'
    text = (d/'api.rs').read_text()
    assert 'pub fn descriptor()' in text
    assert 'pub fn validate(' not in text and 'pub fn is_valid(' not in text
    assert not (d/'validation.rs').exists()
    if mode == 'source':
        prefix, dependencies = source_modules(False), ()
    elif mode == 'package':
        prefix, dependencies = 'extern crate alloc; pub mod api;', [('taut_foundation', foundation)]
    else:
        prefix, dependencies = 'extern crate alloc; pub use taut_foundation::{cbor,descriptors}; pub mod api;', [('taut_foundation', foundation)]
    program(d, '#![no_std]\n' + prefix + '\npub fn descriptor() -> &\'static ' + ('taut_foundation' if mode == 'package' else 'crate') + '::descriptors::MessageDescriptor { api::Content::descriptor() }', dependencies=dependencies, library=True)


def snapshot(directory):
    return {p.relative_to(directory).as_posix(): p.read_bytes() for p in directory.rglob('*') if p.is_file()}


@pytest.mark.parametrize('obstruction', ['api.rs', 'cbor.rs', 'descriptors.rs', 'validation.rs', 'ext.rs'])
def test_unknown_outputs_refuse_before_writes(tmp_path, obstruction):
    d = tmp_path/'rust'; d.mkdir()
    (d/obstruction).write_text('handwritten')
    before = snapshot(tmp_path)
    with pytest.raises(ValueError, match='unknown/handwritten'):
        emit(native_schema(), tmp_path, langs=['rust'], services=[], runtime_mode='source', validation=True)
    assert snapshot(tmp_path) == before


def test_shared_source_consumers_keep_owner_and_engine(tmp_path):
    owner = tmp_path/'owner'
    binds = {'rust': {'module': 'taut_foundation', 'source_root': str(owner)}}
    with pytest.raises(ValueError, match='unavailable'):
        emit(native_schema(), tmp_path/'b', langs=['rust'], services=[], runtime_mode='package', runtime_bindings=binds, validation=True)
    emit(native_schema(), tmp_path/'a', langs=['rust'], services=[], runtime_mode='source', runtime_bindings=binds, validation=True)
    emit(native_schema(), tmp_path/'b', langs=['rust'], services=[], runtime_mode='package', runtime_bindings=binds, validation=True)
    emit(native_schema(), tmp_path/'a', langs=['rust'], services=[], runtime_mode='package', validation=False)
    assert (owner/'validation.rs').exists()
    emit(native_schema(), tmp_path/'b', langs=['rust'], services=[], runtime_mode='package', runtime_bindings=binds, validation=False)
    assert (owner/'descriptors.rs').exists() and not (owner/'validation.rs').exists()
    assert 'pub fn validate(' not in (tmp_path/'b/rust/api.rs').read_text()


def test_modified_owner_mode_change_is_unchanged(tmp_path):
    emit(native_schema(), tmp_path, langs=['rust'], services=[], runtime_mode='source', validation=True)
    (tmp_path/'rust/descriptors.rs').write_text('modified')
    before = snapshot(tmp_path)
    with pytest.raises(ValueError, match='modified/missing'):
        emit(native_schema(), tmp_path, langs=['rust'], services=[], runtime_mode='package')
    assert snapshot(tmp_path) == before


@pytest.mark.parametrize('key,value', [('owner','split'), ('descriptor_contract',2), ('codec_contract',2), ('capabilities',['unknown.rule'])])
def test_bad_runtime_binding_rejected_before_writes(tmp_path, key, value):
    with pytest.raises(ValueError, match='Rust runtime'):
        emit(native_schema(), tmp_path, langs=['rust'], services=[], runtime_mode='package', runtime_bindings={'rust': {key:value}})
    assert not list(tmp_path.iterdir())


def test_recursive_inline_owned_values_use_box_and_static_links(tmp_path):
    s = schema(Node=Msg(child=F(1, Ref.Node, optional=True)))
    emit(s, tmp_path, langs=['rust'], services=[], runtime_mode='source', validation=True)
    d = tmp_path/'rust'
    binary = program(d, source_modules() + '''fn main() {
        let value = api::Node { child: Some(Box::new(api::Node { child: None })) };
        assert!(value.is_valid());
        let bytes = cbor::encode(&value.to_cbor());
        assert_eq!(api::Node::decode(&bytes).unwrap(), value);
        match api::Node::descriptor().fields()[0].field_type() {
            descriptors::TypeDescriptor::Message(get) => assert!(core::ptr::eq(get(), api::Node::descriptor())),
            _ => panic!("wrong recursive link"),
        }
    }''')
    run([binary])


def test_rust_keywords_and_private_python_style_are_target_specific(tmp_path):
    s = schema(M=Msg(**{'type': F(1, INT), '__private': F(2, STR), 'validate': F(3, BOOL)}))
    emit(s, tmp_path, langs=['rust'], services=[], runtime_mode='source', validation=True)
    d = tmp_path/'rust'
    run([program(d, source_modules() + '''fn main() {
        let m = api::M { r#type: 0, __private: String::new(), validate: false };
        assert!(m.is_valid()); assert!(m.validate().is_valid());
        assert_eq!(api::M::descriptor().fields()[0].name(), "type");
        assert_eq!(api::M::descriptor().fields()[0].access_identity(), Some("r#type"));
    }''')])


@pytest.mark.parametrize('s', [schema(SCHEMA_DESCRIPTOR=Msg()), schema(_taut_metadata=Msg()), schema(E=Enum(a_b=0, a__b=1)), schema(Self=Msg())])
def test_actual_generated_symbol_collisions(tmp_path, s):
    with pytest.raises(ValueError, match='Rust generated'):
        emit(s, tmp_path, langs=['rust'], services=[])
    assert not list(tmp_path.iterdir())


def test_reports_match_python_reference_corpus(tmp_path):
    # Reuse the Python checkpoint's native schema and emitted reference classes.
    from test_oneof import module, CORPUS_VERSION
    assert CORPUS_VERSION == 'python-oneof-conformance.1'
    s = native_schema()
    py = module(s)
    # dict union permits overriding each draft's independently nullable payloads.
    def draft(kind, **payload):
        return {'kind':kind, 'text':None, 'number':None, 'flag':None, 'items':None} | payload
    cases = [
        ('zero','Content',draft('number',number=0)), ('false','Content',draft('flag',flag=False)),
        ('empty_text','Content',draft('text',text='')), ('empty_list','Content',draft('items',items=[])),
        ('payload_free','Content',draft('empty')), ('missing','Content',draft('number')),
        ('extra','Content',draft('number',number=0,text='extra')),
        ('all_extra','Content',draft('empty',number=0,text='',flag=False,items=[])),
        ('child','Envelope',{'content':draft('number')}),
        ('virtual_invalid','VirtualEnvelope',{'content':draft('number')}),
        ('virtual_repaired','VirtualEnvelope',{'content':draft('number',number=0)}),
        ('paths','Collection',{'entries':[draft('text'),draft('number')], 'by_key':{'aa':draft('number'),'b':draft('text')}}),
        ('tree','Tree',{'content':None,'children':[{'content':draft('text'),'children':[]}]}),
    ]
    def build(t, value, rust=False):
        if value is None:
            return 'None' if rust else None
        if isinstance(t, Scalar):
            if not rust: return value
            if t.kind == 'str': return json.dumps(value) + '.into()'
            if t.kind == 'bool': return str(value).lower()
            return str(value)
        if isinstance(t, EnumRef):
            if rust:
                from taut.gen.rust import _variant
                return f'{t.name}::{_variant(value)}'
            return getattr(getattr(py,t.name),value)
        if isinstance(t, ListOf):
            values = [build(t.elem,v,rust) for v in value]
            return 'vec![' + ','.join(values) + ']' if rust else values
        if isinstance(t, MapOf):
            if rust:
                return 'std::collections::BTreeMap::from([' + ','.join('('+build(t.key,k,True)+','+build(t.value,v,True)+')' for k,v in value.items()) + '])'
            return {build(t.key,k):build(t.value,v) for k,v in value.items()}
        message = s.messages[t.name]
        fields = {}
        for f in message.fields:
            if f.virtual: continue
            item = build(f.type,value.get(f.name),rust)
            if rust and f.optional and value.get(f.name) is not None: item = 'Some(' + item + ')'
            fields[f.name] = item
        return t.name+'{'+','.join(k+':'+v for k,v in fields.items())+'}' if rust else getattr(py,t.name)(**fields)
    def normal_path(path):
        return '/'.join('F:'+p.field_name if p.kind == 'field' else 'I:'+str(p.index) if p.kind == 'index' else 'K:'+p.key_type+':'+p.key_cbor_base64 for p in path)
    expected = []
    for name, message, value in cases:
        obj = build(MsgRef(message),value)
        for recursive in (False,True):
            report = obj.validate(recursive=recursive)
            expected.append('\t'.join([name,report.scope,str(report.is_valid()).lower(),str(report.is_complete()).lower(),str(obj.is_valid(recursive=recursive)).lower(),
                ';'.join(i.code+'@'+i.rule+'@'+normal_path(i.path) for i in report.issues),
                ';'.join(d.reason_code+'@'+d.rule+'@'+normal_path(d.path) for d in report.deferred_checks)]))
    emit(s,tmp_path,langs=['rust'],services=[],runtime_mode='source',validation=True)
    d=tmp_path/'rust'
    source=source_modules()+r'''
use api::*; use validation::*;
fn path(segments: &[PathSegment]) -> String {
    segments.iter().map(|p| match p.kind() {
        "field" => format!("F:{}",p.field_name().unwrap()),
        "index" => format!("I:{}",p.index().unwrap()),
        _ => format!("K:{}:{}",p.key_type().unwrap(),p.key_cbor_base64().unwrap()),
    }).collect::<Vec<_>>().join("/")
}
fn show(name: &str, report: ValidationReport, fast: bool) {
    let issues=report.issues().iter().map(|i|format!("{}@{}@{}",i.code(),i.rule(),path(i.path()))).collect::<Vec<_>>().join(";");
    let deferred=report.deferred_checks().iter().map(|i|format!("{}@{}@{}",i.reason_code(),i.rule(),path(i.path()))).collect::<Vec<_>>().join(";");
    println!("{}\t{}\t{}\t{}\t{}\t{}\t{}",name,report.scope(),report.is_valid(),report.is_complete(),fast,issues,deferred);
}
fn main(){
'''
    for name,message,value in cases:
        source += '{let value='+build(MsgRef(message),value,True)+'; for recursive in [false,true] { let options=ValidationOptions{recursive}; show('+json.dumps(name)+',value.validate_with_options(options),value.is_valid_with_options(options)); }}\n'
    source += '}\n'
    observed=run([program(d,source)]).stdout.splitlines()
    assert observed == expected


@pytest.mark.parametrize('virtual',[False,True])
@pytest.mark.parametrize('exhaustive',[False,True])
def test_all_virtual_exhaustive_flags_and_shared_nominations(tmp_path,virtual,exhaustive):
    e=Enum('Choice',a=0,b=1)
    s=schema(e,Record=Msg(tag=F(1,OneOf(e,virtual=virtual,exhaustive=exhaustive)),
        data=F(2,STR,Case(tag=e.a),Case(tag=e.b))))
    emit(s,tmp_path,langs=['rust'],services=[],runtime_mode='source',validation=True)
    source=source_modules()+'fn main(){ let value=api::Record{'+('' if virtual else 'tag:api::Choice::B,')+'data:Some(String::new())}; let report=value.validate(); assert!(report.is_valid()); assert_eq!(report.is_complete(),'+str(not virtual).lower()+'); assert_eq!(value.is_valid(),'+str(not virtual).lower()+'); }'
    run([program(tmp_path/'rust',source)])


def test_independent_groups_and_nonselected_children(tmp_path):
    e=Enum('Choice',child=0,empty=1)
    s=schema(e,Child=Msg(tag=F(1,OneOf(e)),data=F(2,STR,Case(tag=e.child))),
        Parent=Msg(tag=F(1,OneOf(e)),other=F(2,OneOf(e)),
            child=F(3,Ref.Child,Case(tag=e.child)),text=F(4,STR,Case(other=e.child))))
    emit(s,tmp_path,langs=['rust'],services=[],runtime_mode='source',validation=True)
    run([program(tmp_path/'rust',source_modules()+'''fn main(){
        let value=api::Parent{tag:api::Choice::Empty,other:api::Choice::Child,
            child:Some(api::Child{tag:api::Choice::Child,data:None}),text:None};
        let report=value.validate();
        assert_eq!(report.issues().iter().map(|i|i.code()).collect::<Vec<_>>(),
            vec!["oneof.payload_unexpected","oneof.payload_missing","oneof.payload_missing"]);
        assert_eq!(report.issues()[2].path().iter().map(|p|p.field_name().unwrap()).collect::<Vec<_>>(),vec!["child","data"]);
        assert_eq!(value.validate_with_options(validation::ValidationOptions{recursive:false}).issues().len(),2);
        assert!(!value.is_valid());
    }''')])


@pytest.mark.parametrize('child_mode,parent_mode', [('source','source'),('source','package'),('package','source'),('package','package')])
def test_independently_generated_child_without_methods_and_shared_owner(tmp_path,child_mode,parent_mode):
    e=Enum('Kind',number=0,empty=1)
    child=schema(e,Child=Msg(kind=F(1,OneOf(e)),number=F(2,INT,Case(kind=e.number))))
    parent=schema(*child.enums.values(),*child.messages.values(),Parent=Msg(child=F(1,Ref.Child)))
    owner=tmp_path/'foundation'
    bindings={'rust':{'module':'taut_foundation','source_root':str(owner)}}
    # A source-only foundation owner is bootstrapped separately from the child.
    # Enabled/disabled is a property of each schema's instance methods.
    emit(schema(Seed=Msg()),tmp_path/'seed',langs=['rust'],services=[],runtime_mode='source',validation=True,runtime_bindings=bindings)
    (owner/'lib.rs').write_text('#![no_std]\nextern crate alloc; pub mod cbor; pub use cbor::descriptors; pub mod validation;')
    owner_artifact=program(owner,(owner/'lib.rs').read_text(),name='taut_foundation',library=True)
    emit(child,tmp_path/'child',langs=['rust'],services=[],runtime_mode=child_mode,runtime_bindings=bindings)
    child_dir=tmp_path/'child/rust'
    child_artifact=program(child_dir,'#![no_std]\nextern crate alloc; pub mod api;',name='child',library=True,dependencies=[('taut_foundation',owner_artifact)])
    assert 'pub fn validate(' not in (child_dir/'api.rs').read_text()
    before_child=(child_dir/'api.rs').read_bytes()
    emit(parent,tmp_path/'parent',langs=['rust'],services=[],runtime_mode=parent_mode,validation=True,
        runtime_bindings=bindings,rust_external_types={'Kind':'child::api::Kind','Child':'child::api::Child'})
    d=tmp_path/'parent/rust'
    assert not (d/'cbor.rs').exists()
    run([program(d,'''extern crate alloc; mod api;
        fn main(){
            let value=api::Parent{child:api::Child{kind:api::Kind::Number,number:None}};
            let report:taut_foundation::validation::ValidationReport=value.validate();
            assert_eq!(report.issues()[0].path()[0].field_name(),Some("child"));
            assert!(value.is_valid_with_options(taut_foundation::validation::ValidationOptions{recursive:false}));
            let _:taut_foundation::cbor::Cbor=value.child.to_cbor();
            assert!(core::ptr::eq(api::Child::descriptor(),child::api::Child::descriptor()));
            let aggregate=taut_foundation::validation::ValidationReport::new(report.issues().to_vec(),vec![],"recursive");
            assert!(!aggregate.is_valid());
        }''',dependencies=[('child',child_artifact),('taut_foundation',owner_artifact)])])
    assert (child_dir/'api.rs').read_bytes()==before_child


def test_runtime_binding_rejects_old_children_and_split_nominal_owner(tmp_path,foundation):
    child=schema(Child=Msg(number=F(1,INT)))
    parent=schema(*child.messages.values(),Parent=Msg(child=F(1,Ref.Child)))
    emit(child,tmp_path/'child',langs=['rust'],services=[],runtime_mode='source')
    child_dir=tmp_path/'child/rust'
    private_owner=program(child_dir,source_modules(False),name='child',library=True)
    emit(parent,tmp_path/'parent',langs=['rust'],services=[],runtime_mode='package',validation=True,
        rust_external_types={'Child':'child::api::Child'})
    d=tmp_path/'parent/rust'
    (d/'main.rs').write_text('extern crate alloc; mod api; fn main() {}')
    result=run(['rustc','--edition=2021',d/'main.rs','--extern',f'child={private_owner}',
        '--extern',f'taut_foundation={foundation}','-L',f'dependency={private_owner.parent}','-o',d/'split.exe'],success=False)
    assert 'mismatched types' in result.stderr and 'SchemaBinding' in result.stderr
    # A prior generated child with only codecs cannot supply the mandatory ABI.
    old=program(tmp_path/'old','''pub mod api { #[derive(Clone,Debug,Default,PartialEq)] pub struct Child{pub number:i64} }''',name='old',library=True)
    emit(parent,tmp_path/'old_parent',langs=['rust'],services=[],runtime_mode='package',validation=True,
        rust_external_types={'Child':'old::api::Child'})
    old_d=tmp_path/'old_parent/rust'
    (old_d/'main.rs').write_text('extern crate alloc; mod api; fn main(){}')
    result=run(['rustc','--edition=2021',old_d/'main.rs','--extern',f'old={old}',
        '--extern',f'taut_foundation={foundation}','-L',f'dependency={foundation.parent}','-o',old_d/'old.exe'],success=False)
    assert 'taut_binding' in result.stderr and 'TAUT_DESCRIPTOR_CONTRACT' in result.stderr


@pytest.mark.parametrize('target,expected', [('descriptor','Taut descriptor contract mismatch'),('rule','unsupported Taut rule'),('parameters','unsupported Taut oneof parameter')])
def test_runtime_rejects_unsupported_configuration(tmp_path,target,expected):
    emit(schema(M=Msg()),tmp_path,langs=['rust'],services=[],runtime_mode='source')
    constraints='&[]' if target=='descriptor' else '&[ConstraintDescriptor::new('+('"future.rule"' if target=='rule' else 'ONEOF_RULE')+', &[("ignored_parameter", OptionValue::Null)])]'
    source=source_modules(False)+f'''use cbor::descriptors::*;
    static BAD:MessageDescriptor=MessageDescriptor::new("M","test.M",{99 if target=='descriptor' else 1},&[],&[],{constraints},&[],&[],None,&[],&[]);
    fn main(){{ BAD.check(); }}'''
    result=run([program(tmp_path/'rust',source)],success=False)
    assert expected in result.stderr


@pytest.mark.parametrize('owner_mode,parent_mode',[('package','package'),('source','package'),('source','source')])
def test_actual_shape_library_aliases_application_foundation(tmp_path,owner_mode,parent_mode):
    shape_root=ROOT.parent/'taut-shape-rs/crates/taut-shape'
    library_schema=load_schema(ROOT.parent/'taut-shape/ir/shape_log.taut.py')
    choice=Enum('AppChoice',packet=0,empty=1)
    s=schema(*library_schema.enums.values(),*library_schema.messages.values(),choice,
        AppEnvelope=Msg(tag=F(1,OneOf(choice)),packet=F(2,Ref.LogRecord,Case(tag=choice.packet))))
    owner=ROOT/'rust/taut-foundation'
    bindings={'rust':{'module':'taut_shape'}}
    if owner_mode=='source':
        owner=tmp_path/'source-owner'
        binds={'rust':{'module':'taut_foundation','source_root':str(owner/'src')}}
        emit(schema(Seed=Msg()),tmp_path/'seed',langs=['rust'],services=[],runtime_mode='source',validation=True,runtime_bindings=binds)
        (owner/'src/lib.rs').write_bytes((ROOT/'rust/taut-foundation/src/lib.rs').read_bytes())
        (owner/'Cargo.toml').write_bytes((ROOT/'rust/taut-foundation/Cargo.toml').read_bytes())
        bindings['rust']['source_root']=str(owner/'src')
    external={name:f'taut_shape::generated::{name}' for name in set(library_schema.messages)|set(library_schema.enums)}
    app=tmp_path/'app'
    emit(s,app,langs=['rust'],services=[],runtime_mode=parent_mode,validation=True,
        runtime_bindings=bindings,rust_external_types=external)
    d=app/'rust'
    (d/'Cargo.toml').write_text(f'''[package]
name="actual-shape-owner-proof"
version="0.0.0"
edition="2021"
[lib]
path="lib.rs"
[dependencies]
taut-foundation={{version="0.10.0",features=["validation"]}}
taut-shape={{path={json.dumps(shape_root.as_posix())},default-features=false,features=["validation"]}}
[patch.crates-io]
taut-foundation={{path={json.dumps(owner.as_posix())}}}
[workspace]
''')
    (d/'lib.rs').write_text('''#![no_std]
extern crate alloc;
pub mod api;
#[cfg(test)] mod tests {
    use super::api::*;
    #[test] fn shape_and_generated_application_have_one_owner() {
        let value=AppEnvelope{tag:AppChoice::Packet,packet:Some(Default::default())};
        let report:taut_foundation::validation::ValidationReport=value.validate();
        let _:taut_shape::validation::ValidationReport=report;
        let wire:taut_foundation::cbor::Cbor=value.packet.as_ref().unwrap().to_cbor();
        let _:taut_shape::cbor::Cbor=wire;
        let _:taut_shape::cbor::DecodeError=taut_foundation::cbor::DecodeError::Truncated;
        let desc:&'static taut_foundation::descriptors::MessageDescriptor=LogRecord::descriptor();
        assert!(core::ptr::eq(desc,taut_shape::generated::LogRecord::descriptor()));
        let issues:alloc::vec::Vec<taut_shape::validation::ValidationIssue>=value.validate().issues().to_vec();
        let _:alloc::vec::Vec<taut_foundation::validation::ValidationIssue>=issues;
        assert!(value.is_valid());
    }
}
''')
    result=run(['cargo','test','--offline','--manifest-path',d/'Cargo.toml'])
    assert '1 passed' in result.stdout
    assert not (d/'cbor.rs').exists()


@pytest.mark.parametrize('mode',['source','package'])
@pytest.mark.parametrize('enabled',[False,True])
def test_runtime_mode_goldens(mode,enabled):
    path=ROOT/f'dev-docs/examples/rust-oneof/goldens/{mode}-{"on" if enabled else "off"}.rs'
    assert path.read_text()==rust_api(native_schema(),validation=enabled,runtime_path='taut_foundation' if mode=='package' else 'crate')


@pytest.mark.parametrize('key_type,keys,expected',[(INT,[-1,24,0],['AA==','GBg=','IA==']),(BOOL,[True,False],['9A==','9Q==']),(STR,['zz','b','a'],['YWE=','YWI=','Ynp6'])])
def test_canonical_map_keys_and_owned_report_snapshot(tmp_path,key_type,keys,expected):
    s=native_schema()
    s=schema(*s.enums.values(),Content=s.messages['Content'],Bag=Msg(by_key=F(1,Map(key_type,Ref.Content))))
    emit(s,tmp_path,langs=['rust'],services=[],runtime_mode='source',validation=True)
    render=lambda key:json.dumps(key)+'.into()' if isinstance(key,str) else str(key).lower()
    entries=','.join('('+render(key)+',api::Content::default())' for key in keys)
    result=run([program(tmp_path/'rust',source_modules()+'''fn main(){
        let mut value=api::Bag{by_key:std::collections::BTreeMap::from(['''+entries+'''])};
        let snapshot=value.validate();value.by_key.clear();
        assert!(value.is_valid());
        for issue in snapshot.issues(){println!("{}",issue.path()[1].key_cbor_base64().unwrap());}
    }''')])
    assert result.stdout.splitlines()==expected


def test_mixed_target_preflight_cannot_partially_write_python(tmp_path):
    d=tmp_path/'rust';d.mkdir()
    (d/'cbor.rs').write_text('handwritten owner')
    before=snapshot(tmp_path)
    with pytest.raises(ValueError,match='unknown/handwritten Rust runtime'):
        emit(native_schema(),tmp_path,langs=['python','rust'],services=[],runtime_mode='source',validation=True)
    assert snapshot(tmp_path)==before


def test_bound_handles_reject_wrong_live_value_at_compile_time(tmp_path):
    emit(native_schema(),tmp_path,langs=['rust'],services=[],runtime_mode='source')
    d=tmp_path/'rust'
    (d/'bad.rs').write_text(source_modules(False)+'''fn main(){
        let wrong=api::Envelope::default();
        let _=api::Content::taut_binding().bind(&wrong);
    }''')
    result=run(['rustc','--edition=2021',d/'bad.rs','-o',d/'bad.exe'],success=False)
    assert 'mismatched types' in result.stderr and 'Content' in result.stderr and 'Envelope' in result.stderr


@pytest.mark.parametrize('defect',['contract','facts','published_contract'])
def test_old_child_contract_or_portable_facts_is_named(tmp_path,foundation,defect):
    child=schema(Child=Msg(number=F(1,INT)))
    parent=schema(*child.messages.values(),Parent=Msg(child=F(1,Ref.Child)))
    emit(child,tmp_path/'child',langs=['rust'],services=[],runtime_mode='package')
    d=tmp_path/'child/rust'
    text=(d/'api.rs').read_text()
    if defect=='contract':
        text=text.replace('TAUT_DESCRIPTOR_CONTRACT: u32 = 1','TAUT_DESCRIPTOR_CONTRACT: u32 = 99')
    elif defect=='facts':
        from taut.gen.rust_metadata import fingerprint
        text=text.replace(fingerprint(child,'Child'),'older-schema-facts')
    else:
        import re
        altered=re.sub(r'(MessageDescriptor::new\("Child", "[^"]+", )1,',r'\g<1>99,',text,count=1)
        assert altered!=text
        text=altered
    (d/'api.rs').write_text(text)
    artifact=program(d,'extern crate alloc;pub mod api;',name='child',library=True,dependencies=[('taut_foundation',foundation)])
    emit(parent,tmp_path/'parent',langs=['rust'],services=[],runtime_mode='package',validation=True,
        rust_external_types={'Child':'child::api::Child'})
    p=tmp_path/'parent/rust'
    (p/'main.rs').write_text('extern crate alloc;mod api;fn main(){api::Parent::descriptor();}')
    args=['rustc','--edition=2021',p/'main.rs','--extern',f'child={artifact}',
        '--extern',f'taut_foundation={foundation}','-L',f'dependency={artifact.parent}',
        '-L',f'dependency={foundation.parent}','-o',p/'bad.exe']
    if defect=='contract':
        result=run(args,success=False)
        assert 'Taut child Child contract mismatch' in result.stderr
    else:
        run(args)
        result=run([p/'bad.exe'],success=False)
        assert ('Taut external Child facts mismatch' if defect=='facts' else 'Taut descriptor contract mismatch') in result.stderr


@pytest.mark.parametrize('field,value',[('owner','unknown-owner'),('descriptor',2),('codec',2),('generator','unknown-policy')])
def test_incompatible_owned_inventory_is_unchanged(tmp_path,field,value):
    emit(native_schema(),tmp_path,langs=['rust'],services=[],runtime_mode='source',validation=True)
    manifest=tmp_path/'rust/.taut-rust-runtime.json'
    data=json.loads(manifest.read_text());data[field]=value
    manifest.write_text(json.dumps(data))
    before=snapshot(tmp_path)
    with pytest.raises(ValueError,match='unsafe Rust ownership'):
        emit(native_schema(),tmp_path,langs=['rust'],services=[],runtime_mode='package')
    assert snapshot(tmp_path)==before


def test_source_cleanup_rejects_directory_junction_before_any_write(tmp_path):
    import os
    if os.name!='nt':
        pytest.skip('Windows directory-junction adversity')
    owner=tmp_path/'owner'
    binds={'rust':{'source_root':str(owner)}}
    emit(native_schema(),tmp_path/'schema',langs=['rust'],services=[],runtime_mode='source',validation=True,runtime_bindings=binds)
    actual=tmp_path/'actual-owner'
    assert owner.resolve().is_relative_to(tmp_path.resolve()) and actual.absolute().is_relative_to(tmp_path.resolve())
    owner.rename(actual)
    result=subprocess.run(['cmd','/c','mklink','/J',str(owner),str(actual)],capture_output=True,text=True)
    assert result.returncode==0,result.stdout+result.stderr
    before=snapshot(tmp_path)
    with pytest.raises(ValueError,match='unsafe'):
        emit(native_schema(),tmp_path/'schema',langs=['rust'],services=[],runtime_mode='package')
    assert snapshot(tmp_path)==before


def test_unequal_patch_generator_is_accepted_by_contract(tmp_path):
    owner=tmp_path/'owner'
    emit(native_schema(),owner,langs=['rust'],services=[],runtime_mode='source',validation=True)
    d=owner/'rust'
    descriptors=d/'descriptors.rs'
    descriptors.write_text(descriptors.read_text().replace('rust-oneof-reference.1','0.10.999'))
    # This is a different built package revision, not a source ownership update.
    run([program(d,source_modules()+'''fn main(){
        assert_eq!(descriptors::GENERATOR_BUILD,"0.10.999");
        let value=api::Content{kind:api::ContentKind::Empty,..Default::default()};
        assert!(value.is_valid());
    }''')])


def test_rust_cli_modes_flags_and_emit_all_forwarding(tmp_path):
    from taut import cli
    from taut.gen.scaffold import emit_all
    for name,flags in [('off',['--runtime','package']),('on',['--with-validation','--runtime','package']),
                       ('alias',['--with-runtime','--runtime','source','--runtime','source'])]:
        assert cli.main(['gen',str(EXAMPLE),'-l','rust','--api-only','-o',str(tmp_path/name),*flags])==0
        text=(tmp_path/name/'rust/api.rs').read_text()
        assert ('pub fn validate(' in text)==(name=='on')
        assert ('taut_foundation::cbor' in text)==(name in ('on','off'))
    with pytest.raises(ValueError,match='conflicting runtime'):
        cli.main(['gen',str(EXAMPLE),'-l','rust','--api-only','-o',str(tmp_path/'conflict'),
            '--runtime','package','--with-runtime'])
    assert not (tmp_path/'conflict').exists()
    from taut.corpus.build import IR_PATH
    s=load_schema(IR_PATH)
    emit_all(s,'GripLab',tmp_path/'all',langs=['rust'],runtime_mode='package',validation=True)
    assert 'pub fn validate(' in (tmp_path/'all/rust/api.rs').read_text()
    assert not (tmp_path/'all/rust/cbor.rs').exists()


def test_report_engine_cannot_be_copied_behind_a_foreign_codec_alias(tmp_path,foundation):
    # Re-exporting the codec alone cannot conceal a duplicate report/engine owner.
    (tmp_path/'validation.rs').write_bytes((RUNTIME/'validation.rs').read_bytes())
    (tmp_path/'bad.rs').write_text('extern crate alloc;pub use taut_foundation::cbor;mod validation;fn main(){}')
    result=run(['rustc','--edition=2021',tmp_path/'bad.rs','--extern',f'taut_foundation={foundation}',
        '-L',f'dependency={foundation.parent}','-o',tmp_path/'bad.exe'],success=False)
    assert 'inherent' in result.stderr and ('outside of the crate' in result.stderr or 'outside of the type' in result.stderr)


def test_binding_cannot_accept_an_unrelated_published_descriptor(tmp_path):
    emit(native_schema(),tmp_path,langs=['rust'],services=[],runtime_mode='source')
    d=tmp_path/'rust'
    (d/'bad.rs').write_text(source_modules(False)+'''fn main(){
        let _=cbor::descriptors::SchemaBinding::<api::Content>::new(api::Tree::descriptor(),
            ||{}, |_,_|cbor::descriptors::FieldState::new(false,None),|_,_,_|true);
    }''')
    result=run(['rustc','--edition=2021',d/'bad.rs','-o',d/'bad.exe'],success=False)
    assert 'expected `MessageDescriptor`' in result.stderr and 'found `&MessageDescriptor`' in result.stderr


def test_external_source_request_upgrades_only_existing_selected_owner(tmp_path):
    child=schema(Child=Msg(number=F(1,INT)))
    parent=schema(*child.messages.values(),Parent=Msg(child=F(1,Ref.Child)))
    owner=tmp_path/'owner'
    binds={'rust':{'module':'taut_foundation','source_root':str(owner)}}
    emit(child,tmp_path/'child',langs=['rust'],services=[],runtime_mode='source',runtime_bindings=binds)
    before=(tmp_path/'child/rust/api.rs').read_bytes()
    assert not (owner/'validation.rs').exists()
    emit(parent,tmp_path/'parent',langs=['rust'],services=[],runtime_mode='source',validation=True,
        runtime_bindings=binds,rust_external_types={'Child':'dependency::Child'})
    assert (owner/'validation.rs').exists()
    assert not (tmp_path/'parent/rust/cbor.rs').exists()
    assert (tmp_path/'child/rust/api.rs').read_bytes()==before


def test_equivalent_reordered_dependency_facts_are_compatible(tmp_path,foundation):
    from dataclasses import replace
    e=Enum('Kind',a=0,b=1)
    child=schema(e,Child=Msg(tag=F(1,OneOf(e)),data=F(2,STR,Case(tag=e.a),Case(tag=e.b))))
    altered=replace(child.messages['Child'],fields=tuple(reversed(tuple(
        replace(f,cases=tuple(reversed(f.cases))) for f in child.messages['Child'].fields))))
    parent=schema(e,altered,Parent=Msg(child=F(1,Ref.Child)))
    emit(child,tmp_path/'child',langs=['rust'],services=[],runtime_mode='package')
    d=tmp_path/'child/rust'
    artifact=program(d,'extern crate alloc;pub mod api;',name='child',library=True,dependencies=[('taut_foundation',foundation)])
    emit(parent,tmp_path/'parent',langs=['rust'],services=[],runtime_mode='package',validation=True,
        rust_external_types={'Kind':'child::api::Kind','Child':'child::api::Child'})
    p=tmp_path/'parent/rust'
    run([program(p,'''extern crate alloc;mod api;fn main(){
        let value=api::Parent{child:api::Child{tag:api::Kind::B,data:Some(String::new())}};
        assert!(value.is_valid());
    }''',dependencies=[('child',artifact),('taut_foundation',foundation)])])


@pytest.mark.parametrize('defect',['owner','capability','engine'])
def test_actual_built_runtime_contracts_are_checked(tmp_path,defect):
    owner=tmp_path/'owner';owner.mkdir()
    for name,source in [('cbor.rs','cbor_fail_closed.rs'),('descriptors.rs','descriptors.rs'),('validation.rs','validation.rs')]:
        text=(RUNTIME/source).read_text()
        if name=='descriptors.rs' and defect=='owner':
            text=text.replace('"taut.rust.foundation"','"foreign.foundation"')
        if name=='descriptors.rs' and defect=='capability':
            text=text.replace('"codec.v1", "oneof.v1"','"codec.v1"')
        if name=='validation.rs' and defect=='engine':
            text=text.replace('VALIDATION_CONTRACT: u32 = 1','VALIDATION_CONTRACT: u32 = 99')
        (owner/name).write_text(text)
    artifact=program(owner,'extern crate alloc;pub mod cbor;pub use cbor::descriptors;pub mod validation;',name='taut_foundation',library=True)
    emit(native_schema(),tmp_path/'app',langs=['rust'],services=[],runtime_mode='package',validation=True)
    d=tmp_path/'app/rust'
    source='extern crate alloc;mod api;fn main(){ let value=api::Content{kind:api::ContentKind::Empty,..Default::default()};value.validate();}'
    if defect=='engine':
        (d/'bad.rs').write_text(source)
        result=run(['rustc','--edition=2021',d/'bad.rs','--extern',f'taut_foundation={artifact}',
            '-L',f'dependency={artifact.parent}','-o',d/'bad.exe'],success=False)
        assert 'Taut validation engine contract mismatch' in result.stderr
    else:
        result=run([program(d,source,dependencies=[('taut_foundation',artifact)])],success=False)
        assert 'regenerate artifact or rebind compatible runtime' in result.stderr
        assert 'foreign.foundation' in result.stderr if defect=='owner' else 'oneof.v1' in result.stderr


def test_mandatory_adapter_reads_every_primitive_without_engine(tmp_path):
    from taut.ir.dsl import BYTES,FLOAT
    e=Enum('Kind',yes=0)
    s=schema(e,Scalars=Msg(number=F(1,INT),text=F(2,STR),flag=F(3,BOOL),data=F(4,BYTES),
        ratio=F(5,FLOAT),kind=F(6,e),maybe=F(7,STR,optional=True)))
    emit(s,tmp_path,langs=['rust'],services=[],runtime_mode='source')
    run([program(tmp_path/'rust',source_modules(False)+'''use descriptors::{RecordAccess,PrimitiveValue};
    fn main(){
        let value=api::Scalars{number:0,text:String::new(),flag:false,data:vec![0,255],ratio:1.25,kind:api::Kind::Yes,maybe:None};
        let bound=api::Scalars::taut_binding().bind(&value);
        assert_eq!(bound.field_state(0).primitive(),Some(PrimitiveValue::Int(0)));
        assert_eq!(bound.field_state(1).primitive(),Some(PrimitiveValue::String("")));
        assert_eq!(bound.field_state(2).primitive(),Some(PrimitiveValue::Bool(false)));
        assert_eq!(bound.field_state(3).primitive(),Some(PrimitiveValue::Bytes(&[0,255])));
        assert_eq!(bound.field_state(4).primitive(),Some(PrimitiveValue::Float(1.25)));
        assert_eq!(bound.field_state(5).primitive(),Some(PrimitiveValue::Enum(0)));
        assert!(!bound.field_state(6).is_present());assert_eq!(bound.field_state(6).primitive(),None);
        match bound.field_state(3).primitive().unwrap(){PrimitiveValue::Bytes(bytes)=>assert!(core::ptr::eq(bytes.as_ptr(),value.data.as_ptr())),_=>panic!()}
        assert_eq!(core::mem::size_of::<descriptors::Bound<'_,api::Scalars>>(),2*core::mem::size_of::<usize>());
    }''')])
    d=tmp_path/'rust'
    (d/'bad.rs').write_text(source_modules(False)+'''use descriptors::RecordAccess;fn main(){
        let leaked;
        {let value=api::Scalars::default();let bound=api::Scalars::taut_binding().bind(&value);
         leaked=bound.field_state(1).primitive();}
        println!("{:?}",leaked);
    }''')
    result=run(['rustc','--edition=2021',d/'bad.rs','-o',d/'bad.exe'],success=False)
    assert 'does not live long enough' in result.stderr


@pytest.mark.parametrize('kind',['message','enum'])
@pytest.mark.parametrize('mode',['source','package'])
@pytest.mark.parametrize('enabled',[False,True])
def test_schema_types_named_box_compile_in_all_modes(tmp_path,foundation,kind,mode,enabled):
    if kind=='message':
        s=schema(Box=Msg(value=F(1,INT),next_id=2))
        body='let value=api::Box{value:0};let decoded=api::Box::from_cbor(&value.to_cbor()).unwrap();assert_eq!(decoded,value);'
    else:
        s=schema(Box=Enum(data=0),Packet=Msg(kind=F(1,Ref.Box)))
        body='let value=api::Packet{kind:api::Box::Data};let decoded=api::Packet::from_cbor(&value.to_cbor()).unwrap();assert_eq!(decoded,value);'
    emit(s,tmp_path,langs=['rust'],services=[],runtime_mode=mode,validation=enabled)
    prefix=source_modules(enabled) if mode=='source' else 'extern crate alloc;mod api;'
    body+='assert_eq!(api::Box::descriptor().name(),"Box");'
    if enabled:body+='assert!(value.is_valid());'
    run([program(tmp_path/'rust',prefix+'fn main(){'+body+'}',dependencies=[] if mode=='source' else [('taut_foundation',foundation)])])


def owner_application(directory,owner):
    prefix=f'''extern crate alloc;
        #[path={json.dumps((owner/'cbor.rs').as_posix())}]pub mod cbor;
        #[path={json.dumps((owner/'validation.rs').as_posix())}]pub mod validation;
        mod api;'''
    run([program(directory,prefix+'fn main(){let value=api::M{n:0};assert!(value.is_valid());}')])


def test_equivalent_source_root_retains_live_runtime_and_builds(tmp_path):
    s=schema(M=Msg(n=F(1,INT)))
    owner=tmp_path/'owner';app=tmp_path/'app'
    for root in (owner,owner/'..'/'owner'):
        emit(s,app,langs=['rust'],services=[],runtime_mode='source',validation=True,
            runtime_bindings={'rust':{'source_root':str(root)}})
    record=json.loads((owner/'.taut-rust-runtime.json').read_text())
    assert len(record['users'])==1
    assert set(record['files'])=={'cbor.rs','descriptors.rs','ext.rs','validation.rs'}
    assert all((owner/name).is_file() for name in record['files'])
    owner_application(app/'rust',owner)


def test_equivalent_shared_root_keeps_both_users_and_enabled_engine(tmp_path):
    s=schema(M=Msg(n=F(1,INT)))
    owner=tmp_path/'owner'
    def generate(user,root,enabled):
        emit(s,tmp_path/user,langs=['rust'],services=[],runtime_mode='source',validation=enabled,
            runtime_bindings={'rust':{'source_root':str(root)}})
    generate('a',owner,True);generate('b',owner,False)
    generate('a',owner/'..'/'owner',True)
    record=json.loads((owner/'.taut-rust-runtime.json').read_text())
    assert len(record['users'])==2 and sum(u['validation'] for u in record['users'].values())==1
    assert (owner/'validation.rs').exists()
    owner_application(tmp_path/'a/rust',owner)
    generate('b',owner,False)
    assert (owner/'validation.rs').exists()
    generate('a',owner,False)
    assert not (owner/'validation.rs').exists()
    assert len(json.loads((owner/'.taut-rust-runtime.json').read_text())['users'])==2


def test_equivalent_schema_output_spelling_has_one_user(tmp_path):
    s=schema(M=Msg(n=F(1,INT)))
    owner=tmp_path/'owner';app=tmp_path/'app'
    for destination in (app,app/'..'/'app'):
        emit(s,destination,langs=['rust'],services=[],runtime_mode='source',validation=True,
            runtime_bindings={'rust':{'source_root':str(owner)}})
    assert len(json.loads((owner/'.taut-rust-runtime.json').read_text())['users'])==1
    owner_application(app/'rust',owner)


def test_physical_write_delete_overlap_fails_before_mutation(tmp_path):
    from taut.gen.python_runtime import apply_outputs
    target=tmp_path/'keep.txt';target.write_text('original')
    step=tmp_path/'step';step.mkdir()
    before=snapshot(tmp_path)
    with pytest.raises(ValueError,match='conflicting physical output'):
        apply_outputs({target:b'replacement'},[step/'..'/'keep.txt'])
    assert snapshot(tmp_path)==before


def test_windows_extended_path_spelling_shares_owner_and_schema_identity(tmp_path):
    import os
    if os.name!='nt':pytest.skip('Windows extended drive-path spelling')
    s=schema(M=Msg(n=F(1,INT)))
    owner=tmp_path/'owner';app=tmp_path/'app'
    extended=lambda path:Path('\\\\?\\'+str(path))
    for destination,root in ((app,owner),(app,extended(owner)),(extended(app),owner)):
        emit(s,destination,langs=['rust'],services=[],runtime_mode='source',validation=True,
            runtime_bindings={'rust':{'source_root':str(root)}})
    record=json.loads((owner/'.taut-rust-runtime.json').read_text())
    assert len(record['users'])==1 and (owner/'validation.rs').exists()
    owner_application(app/'rust',owner)
