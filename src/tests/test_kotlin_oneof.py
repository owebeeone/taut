"""Executable Kotlin conformance, nominal identity and guarded delivery evidence."""
from pathlib import Path
import dataclasses
import hashlib
import json
import os
import subprocess
import zipfile

import pytest

from taut.gen import kotlin, kotlin_runtime
from taut.gen.kotlin_package import build_foundation
from taut.gen.python_runtime import apply_outputs, output_locks
from taut.ir.dsl import BOOL, BYTES, FLOAT, INT, STR, Case, Enum, F, List, Map, Msg, OneOf, Ref, schema
from taut.ir.load import load_schema

ROOT = Path(__file__).resolve().parents[2]
RUNTIME = ROOT / 'src/taut/gen/runtime'
EXAMPLE = ROOT / 'dev-docs/examples/python-oneof/content.taut.py'


def run(args, *, success=True):
    result = subprocess.run(list(map(str,args)), capture_output=True, text=True, encoding='utf-8')
    assert (result.returncode == 0) == success, result.stdout + result.stderr
    return result


@pytest.fixture(scope='module')
def tools():
    from taut.corpus.toolchains import find_kotlin_tools
    found = find_kotlin_tools()
    assert found is not None, 'Kotlin tests require configured kotlinc and java'
    return found


@pytest.fixture(scope='module')
def foundation(tmp_path_factory, tools):
    return build_foundation(tmp_path_factory.mktemp('kotlin-package'), kotlinc=tools[0], java=tools[1])


@pytest.fixture(scope='module')
def no_engine(tmp_path_factory, tools):
    return build_foundation(tmp_path_factory.mktemp('kotlin-no-engine'), validation=False,
                            kotlinc=tools[0], java=tools[1])


def emit_direct(s, directory, *, validation=False, mode=None, source_root=None, external_types=None, identity=None):
    """Same target helper ABI the shared scaffold invokes; keeps helper probes independent."""
    directory = Path(directory)
    source_root = source_root or directory
    texts = {'api.kt': kotlin.emit_types(s, validation=validation, external_types=external_types, identity=identity)}
    with output_locks([directory, source_root]):
        writes, deletes = kotlin_runtime.plan_outputs(directory, texts, mode=mode, validation=validation,
                                                      source_root=source_root,
                                                      consume_source=source_root != directory,
                                                      external=bool(external_types))
        apply_outputs(writes, deletes)
    return directory / 'api.kt'


def compile_program(directory, source, tools, *, sources=(), dependencies=(), success=True, name='main', execute=True):
    directory.mkdir(parents=True, exist_ok=True)
    main = directory / (name + '.kt')
    main.write_text(source, encoding='utf-8')
    artifact = directory / (name + '.jar')
    args = [tools[0], *sources, main, '-jvm-target', '1.8', '-include-runtime', '-d', artifact]
    if dependencies:
        args += ['-classpath', os.pathsep.join(map(str, dependencies))]
    # Windows batch parsing treats unquoted classpath semicolons as argument
    # separators. A compiler argfile preserves exact path/classpath values.
    argfile=directory/(name+'.args')
    argfile.write_text('\n'.join(json.dumps(str(arg).replace('\\','/')) for arg in args[1:]),encoding='utf-8')
    built = run([args[0],'@'+str(argfile)], success=success)
    if not success: return built
    if execute:
        result = run([tools[1], '-cp', os.pathsep.join(map(str,[artifact,*dependencies])), name[0].upper()+name[1:]+'Kt'])
        return result.stdout
    return artifact


BEHAVIOR = r'''
import taut.*
import taut.validation.*
import taut.validation.descriptors.*
fun main() {
    fun parity(value: Content, expected: Boolean) {
        for (recursive in listOf(false,true)) {
            val report = value.validate(recursive)
            check(value.isValid(recursive) == (report.isValid() && report.isComplete()))
            check(value.isValid(recursive) == expected)
        }
    }
    for (value in listOf(Content(ContentKind.number, number=0), Content(ContentKind.flag, flag=false),
                         Content(ContentKind.text, text=""), Content(ContentKind.items, items=emptyList()),
                         Content(ContentKind.empty))) parity(value, true)
    var draft = Content(ContentKind.number, text="extra")
    val snapshot = draft.validate()
    check(snapshot.issues.map { it.code } == listOf("oneof.payload_unexpected", "oneof.payload_missing"))
    check(snapshot.issues[0].rule == "taut.oneof.v1")
    check(snapshot.issues[0].path[0].fieldName == "text")
    draft = Content.decode(encode(draft.toCbor()))
    check(draft.text == "extra" && draft.number == null && draft.toCbor().mapEntries.size == 5)
    parity(draft,false); draft.text=null; draft.number=0; parity(draft,true)
    check(snapshot.issues.size == 2)
    val invalid = Content(ContentKind.text)
    val wrapper = Envelope(invalid)
    check(!wrapper.isValid() && wrapper.isValid(false)); check(wrapper.validate(false).scope == "local")
    check(wrapper.validate().issues[0].path.map { it.fieldName } == listOf("content","text"))
    val virtual = VirtualEnvelope(invalid)
    var report = virtual.validate()
    check(report.issues.size==1 && report.deferredChecks.size==1 && !virtual.isValid())
    invalid.text=""; report=virtual.validate()
    check(report.isValid() && !report.isComplete() && !virtual.isValid())
    check(report.deferredChecks[0].reasonCode=="oneof.virtual_deferred")
    check(report.deferredChecks[0].path[0].fieldName=="kind")
    invalid.text=null
    val tree=Tree(null,listOf(Tree(invalid,emptyList())))
    check(tree.validate().issues[0].path[1].index==0L)
    val collection=Collection(listOf(invalid,invalid), linkedMapOf("aa" to invalid,"b" to invalid))
    val paths=collection.validate().issues.map { it.path }
    check(paths.size==4 && paths[0][1].index==0L && paths[1][1].index==1L)
    check(paths[2][1].keyType=="str" && paths[2][1].keyCborBase64=="YWI=")
    check(paths[3][1].keyCborBase64=="YmFh")
    val cycle=Tree(null,emptyList()); cycle.children=listOf(cycle)
    val cyclic=cycle.validate()
    check(cyclic.issues.single().code=="validation.ownership_cycle")
    check(cyclic.issues.single().rule=="validation.shape.v1")
    check(!cycle.isValid() && cycle.isValid(false))
    val fields=Content.descriptor().fields
    check(Content.descriptor()===Content.descriptor() && fields.map { it.number } == listOf(1,2,3,4,5))
    check(fields[1].presence=="nullable" && Content.descriptor().nextId==6)
    check(VirtualEnvelope.descriptor().fields[0].virtual && VirtualEnvelope.descriptor().fields[0].attribute==null)
    try { (fields as MutableList<FieldDescriptor>).clear(); error("mutable fields") } catch (_:UnsupportedOperationException) {}
    try { (snapshot.issues as MutableList<ValidationIssue>).clear(); error("mutable report") } catch (_:UnsupportedOperationException) {}
    try { (snapshot.issues[0].path as MutableList<PathSegment>).clear(); error("mutable path") } catch (_:UnsupportedOperationException) {}
    val mutable=mutableListOf(PathSegment.forIndex(2)); val issue=ValidationIssue("future.code","future.rule",mutable,"future")
    mutable.clear(); check(issue.path.single().index==2L)
    val open=ValidationReport(listOf(issue),scope="local"); check(!open.isValid() && open.isComplete())
    val bytes=byteArrayOf(0x61,0x62); val key=PathSegment.forKey("str",bytes); bytes[1]=0x63
    check(key.keyCborBase64=="YWI=")
    check(PathSegment.forIndex(2147483648L).index==2147483648L)
    try { PathSegment.forIndex(-1); error("negative") } catch (_:IllegalArgumentException) {}
    try { PathSegment.forKey("int",byteArrayOf(0x18,0x00)); error("noncanonical") } catch (_:IllegalArgumentException) {} catch (_:DecodeError) {}
    println("presence/drafts/snapshots/recursive/virtual/cycles/maps/metadata/open-reports PASS")
}
'''


@pytest.mark.parametrize('mode', ['source', 'package', None])
def test_native_behavior_source_package_supplied(tmp_path, tools, foundation, mode):
    d = tmp_path / 'generated'
    emit_direct(load_schema(EXAMPLE),d,validation=True,mode=mode)
    sources = list(d.glob('*.kt'))
    output = compile_program(tmp_path,BEHAVIOR,tools,sources=sources,
                             dependencies=() if mode=='source' else (foundation,))
    assert 'open-reports PASS' in output


def test_foundation_package_exact_canonical_content(foundation, no_engine):
    with zipfile.ZipFile(foundation) as jar:
        data=json.loads(jar.read('META-INF/taut-kotlin-foundation.json'))
        assert data['owner']=='taut.kotlin.foundation'
        assert data['validation'] is True
        for name,resource in kotlin_runtime.FILES.items():
            assert data['sources'][name]==hashlib.sha256((RUNTIME/resource).read_bytes()).hexdigest()
        assert 'taut/validation/ValidationReport.class' in jar.namelist()
        assert not any('shape' in name.lower() or 'compiler' in name.lower() for name in jar.namelist())
        assert max(int.from_bytes(jar.read(n)[6:8],'big') for n in jar.namelist() if n.endswith('.class'))==52
    with zipfile.ZipFile(no_engine) as jar:
        assert 'taut/validation/descriptors/MessageDescriptor.class' in jar.namelist()
        assert 'taut/validation/ValidationEngine.class' not in jar.namelist()
        assert 'taut/validation/ValidationReport.class' not in jar.namelist()


@pytest.mark.parametrize('mode', ['source', 'package', None])
def test_descriptors_without_engine(tmp_path, tools, no_engine, mode):
    d=tmp_path/'generated'
    emit_direct(load_schema(EXAMPLE),d,mode=mode)
    assert not (d/'validation.kt').exists()
    program='''import taut.*
fun main() {
 check(Content.descriptor().fields.size==5)
 check(Content.tautBinding().bind(Content(ContentKind.number,number=0)).read(2)==0L)
 check(Content.decode(encode(Content(ContentKind.text).toCbor())).text==null)
 println("no-engine descriptors/invalid-draft-codec PASS")
}'''
    assert 'PASS' in compile_program(tmp_path,program,tools,sources=list(d.glob('*.kt')),
                                    dependencies=() if mode=='source' else (no_engine,))


def test_direct_primitive_reads_and_full_descriptor_inventory(tmp_path, tools, no_engine):
    kind=Enum('Tag',a=0,b=1)
    s=schema(kind, Msg('Record',F('n',7,INT),F('class',2,STR),F('bytes',3,BYTES),F('ok',4,BOOL),F('f',5,FLOAT),
                       F('tag',6,Ref.Tag),F('items',8,List(INT)),F('map',9,Map(INT,STR)),
                       F('next',10,Ref.Record,optional=True),reserved=(1,'old'),next_id=11))
    d=tmp_path/'generated'; emit_direct(s,d,mode='package')
    schema_name=__import__('re').search(r'val (TAUT_SCHEMA_[0-9a-f]+)',(d/'api.kt').read_text()).group(1)
    program='''import taut.*
fun main() {
 val bytes=byteArrayOf(1,2); val r=Record(3,"text",bytes,true,1.5,Tag.a,emptyList(),emptyMap())
 val bound=Record.tautBinding().bind(r)
 check(bound.read(0)=="text" && bound.read(1)===bytes && bound.read(2)==true && bound.read(3)==1.5 && bound.read(4)==0L && bound.read(5)==3L)
 val d=Record.descriptor(); check(d.reservedNumbers==listOf(1) && d.reservedNames==listOf("old") && d.nextId==11)
 check(d.fields[0].attribute=="`class`" && d.fields[0].name=="class")
 check(d.fields.last().type.message!!.invoke()===d)
 val schema=SCHEMA_ACCESSOR;check(schema.messages["Record"]===d && schema.enums["Tag"]===Tag.descriptor())
 check(d.effectiveOptions.containsKey("max_depth")); println("full-inventory/direct-reads/recursive-link PASS")
}'''.replace('SCHEMA_ACCESSOR',schema_name)
    assert 'PASS' in compile_program(tmp_path,program,tools,sources=[d/'api.kt'],dependencies=[no_engine])


@pytest.mark.parametrize('name',['descriptor','tautBinding','TAUT_OWNER','TAUT_FACTS_FINGERPRINT','validate','isValid'])
def test_preflight_generated_names(name):
    s=schema(Msg('Record',F(name,1,INT)))
    with pytest.raises(ValueError,match='collision'):
        kotlin.emit_types(s,validation=True)
    if name in {'validate','isValid'}:
        assert f'var {name}' in kotlin.emit_types(s)


@pytest.mark.parametrize('name',['wire','ordinal','Companion','entries','fromWire','descriptor'])
def test_preflight_enum_collisions(name):
    with pytest.raises(ValueError,match='collision'):
        kotlin.emit_types(schema(Enum('Tag',**{name:0})))


@pytest.mark.parametrize('config',[{'owner':'taut.java.foundation'},{'descriptor_contract':2},
                                  {'codec_contract':0},{'descriptor_contract':True},
                                  {'capabilities':['codec.v1']},{'module':'other'}])
def test_binding_contract_rejected_before_writes(tmp_path,config):
    with pytest.raises(ValueError,match='Kotlin'):
        kotlin_runtime.binding({'kotlin':config},tmp_path/'new','package')
    assert not list(tmp_path.iterdir())


def test_external_configuration_preflight():
    s=load_schema(EXAMPLE)
    for mapping in [{'missing':'taut.Child'},{'Content':'taut.Bad;injection'},{'Content':'taut.Content'}]:
        with pytest.raises(ValueError): kotlin.emit_types(s,external_types=mapping)


def tree_bytes(directory):
    return {p.relative_to(directory).as_posix():p.read_bytes() for p in directory.rglob('*') if p.is_file()}


@pytest.mark.parametrize('damage',['modified-api','modified-runtime','unknown-runtime','bad-contract','unknown-api'])
def test_guarded_outputs_fail_without_partial_writes(tmp_path,damage):
    d=tmp_path/'generated'; s=load_schema(EXAMPLE)
    if damage not in {'unknown-api','unknown-runtime'}:
        emit_direct(s,d,validation=True,mode='source')
    else: d.mkdir()
    if damage=='modified-api': (d/'api.kt').write_text('hand edit')
    if damage=='modified-runtime': (d/'descriptors.kt').write_text('hand edit')
    if damage=='unknown-api': (d/'api.kt').write_text('handwritten')
    if damage=='unknown-runtime': (d/'validation.kt').write_text('handwritten')
    if damage=='bad-contract':
        p=d/'.taut-kotlin-runtime.json'; data=json.loads(p.read_text()); data['descriptor']=2; p.write_text(json.dumps(data))
    before=tree_bytes(tmp_path)
    with pytest.raises(ValueError): emit_direct(s,d,validation=True,mode='source')
    assert tree_bytes(tmp_path)==before


def test_shared_source_users_and_all_mode_transitions(tmp_path):
    s=load_schema(EXAMPLE); a=tmp_path/'a'; b=tmp_path/'b'; owner=tmp_path/'owner'
    emit_direct(s,a,validation=True,mode='source',source_root=owner)
    emit_direct(s,b,validation=False,mode='source',source_root=owner)
    assert (owner/'validation.kt').exists()
    # Equivalent physical roots retain A's ownership; B cannot delete A's engine.
    alias=owner/'missing'/'..'
    emit_direct(s,b,mode='package',source_root=alias)
    assert (owner/'validation.kt').exists()
    emit_direct(s,a,validation=False,mode='source',source_root=owner)
    assert not (owner/'validation.kt').exists()
    emit_direct(s,a,mode='package')
    assert (owner/'descriptors.kt').exists() # supplied B still positively consumes source
    emit_direct(s,b,mode='package')
    assert not (owner/'descriptors.kt').exists()
    emit_direct(s,a,validation=True,mode='source')
    assert (a/'validation.kt').exists()
    emit_direct(s,a,mode='package')
    assert not (a/'validation.kt').exists() and not (a/'cbor.kt').exists()


def test_unknown_shared_user_cannot_be_silently_discarded(tmp_path):
    d=tmp_path/'generated'; s=load_schema(EXAMPLE); emit_direct(s,d,mode='source')
    p=d/'.taut-kotlin-runtime.json'; data=json.loads(p.read_text()); data['users']['relative-identity']={'validation':False}; p.write_text(json.dumps(data))
    before=tree_bytes(tmp_path)
    with pytest.raises(ValueError,match='identity'): emit_direct(s,d,mode='package')
    assert tree_bytes(tmp_path)==before


def child_schema():
    kind=Enum('ChildKind',text=0,empty=1)
    return schema(kind,Child=Msg(kind=F(1,OneOf(kind)),text=F(2,STR,Case(kind=kind.text))))


def parent_schema():
    child=child_schema()
    return dataclasses.replace(child,messages={**child.messages,
        'Parent':schema(Parent=Msg(child=F(1,Ref.Child),children=F(2,List(Ref.Child)),by_key=F(3,Map(INT,Ref.Child)))).messages['Parent']})


@pytest.fixture(scope='module')
def child_artifact(tmp_path_factory,tools,no_engine):
    d=tmp_path_factory.mktemp('kotlin-disabled-child')
    api=emit_direct(child_schema(),d,mode='package',identity='child')
    jar=d/'child.jar'
    run([tools[0],api,'-jvm-target','1.8','-classpath',no_engine,'-d',jar])
    return jar


@pytest.mark.parametrize('mode',['source','package',None])
def test_enabled_parent_disabled_independent_child_shared_identity(tmp_path,tools,foundation,child_artifact,mode):
    from taut.gen.scaffold import emit
    d=tmp_path/'generated'
    emit(parent_schema(),d,langs=['kotlin'],services=[],validation=True,runtime_mode=mode,
         kotlin_external_types={'Child':'taut.Child','ChildKind':'taut.ChildKind'},schema_identity='parent')
    api=d/'kotlin'/'api.kt'
    assert 'data class Child(' not in api.read_text() and 'enum class ChildKind(' not in api.read_text()
    child_before=child_artifact.read_bytes()
    program='''import taut.*
import taut.validation.*
import taut.validation.descriptors.*
fun main() {
 val child=Child(ChildKind.text)
 val parent=Parent(child,listOf(child),linkedMapOf(0L to child,-1L to child,24L to child))
 val report: ValidationReport=parent.validate()
 check(report.issues.size==5 && !parent.isValid() && parent.isValid(false))
 check(report.issues[0].path[0].fieldName=="child" && report.issues[1].path[1].index==0L)
 check(report.issues.drop(2).map { it.path[1].keyCborBase64 }==listOf("AA==","GBg=","IA=="))
 val childDescriptor:MessageDescriptor=Child.descriptor()
 check(Parent.descriptor().fields[0].type.message!!.invoke()===childDescriptor)
 child.text=""; check(parent.isValid()); check(report.issues.size==5)
 val cbor:Cbor=child.toCbor(); check(Foundation.codecIdentity(cbor)===cbor)
 check(Child.decode(encode(cbor)).text=="")
 println("independent-disabled-child/typed-owner/shared-report/shared-codec PASS")
}'''
    dependencies=[child_artifact] + ([] if mode=='source' else [foundation])
    assert 'PASS' in compile_program(tmp_path,program,tools,sources=list((d/'kotlin').glob('*.kt')),dependencies=dependencies)
    assert child_artifact.read_bytes()==child_before


def test_old_child_build_and_wrong_typed_pair_are_configuration_errors(tmp_path,tools,foundation):
    d=tmp_path/'generated'
    api=emit_direct(parent_schema(),d,validation=True,mode='package',external_types={'Child':'taut.Child','ChildKind':'taut.ChildKind'})
    old=tmp_path/'old.kt'
    old.write_text('''package taut
enum class ChildKind(val wire: Long) { text(0), empty(1); companion object { fun fromWire(v:Long)=text } }
class Child(var kind:ChildKind,var text:String?=null) {
 fun toCbor(): Cbor=Cbor.map(emptyList())
 companion object { fun fromCbor(c:Cbor)=Child(ChildKind.text) }
}''')
    result=compile_program(tmp_path,'fun main() {}',tools,sources=[api,old],dependencies=[foundation],success=False)
    assert 'tautBinding' in result.stderr and 'TAUT_' in result.stderr
    good=tmp_path/'good.kt'; good.write_text(kotlin.emit_types(child_schema()))
    result=compile_program(tmp_path,'import taut.*\nfun main() { Child.tautBinding().bind("wrong") }',tools,
                           sources=[good],dependencies=[foundation],success=False,name='pair')
    assert 'String' in result.stderr and 'Child' in result.stderr


def test_mismatched_child_facts_fail_before_validation(tmp_path,tools,foundation):
    s=child_schema(); d=tmp_path/'generated'
    emit_direct(parent_schema(),d,validation=True,mode='package',external_types={'Child':'taut.Child','ChildKind':'taut.ChildKind'})
    child=tmp_path/'child.kt'
    text=kotlin.emit_types(s).replace('val TAUT_FACTS_FINGERPRINT = "','val TAUT_FACTS_FINGERPRINT = "tampered_',1)
    child.write_text(text)
    program='''import taut.*
import taut.validation.descriptors.*
fun main() {
 try { Parent(Child(ChildKind.empty),emptyList(),emptyMap()).validate(); error("accepted") }
 catch (e:ConfigurationError) { check(e.message!!.contains("facts mismatch")); println("facts mismatch rejected PASS") }
}'''
    assert 'PASS' in compile_program(tmp_path,program,tools,sources=[d/'api.kt',child],dependencies=[foundation])


def test_shared_scaffold_cli_modes_and_keyword_forwarding(tmp_path,monkeypatch):
    from taut.gen.scaffold import emit, emit_all
    from taut.cli import main
    s=load_schema(EXAMPLE)
    emit(s,tmp_path/'enabled',langs=['kotlin'],services=[],runtime_mode='source',validation=True)
    assert (tmp_path/'enabled/kotlin/validation.kt').exists()
    emit(s,tmp_path/'disabled',langs=['kotlin'],services=[],runtime=True)
    assert not (tmp_path/'disabled/kotlin/validation.kt').exists()
    assert 'fun descriptor()' in (tmp_path/'disabled/kotlin/api.kt').read_text()
    for flags in [['--runtime','source','--runtime','package'],['--with-runtime','--runtime','package']]:
        with pytest.raises((SystemExit,ValueError)): main(['gen',str(EXAMPLE),'--out',str(tmp_path/'conflict'),'--lang','kotlin',*flags])
        assert not (tmp_path/'conflict').exists()
    assert main(['gen',str(EXAMPLE),'--out',str(tmp_path/'cli'),'--lang','kotlin','--runtime','source','--runtime','source','--with-validation'])==0
    assert (tmp_path/'cli/kotlin/validation.kt').exists()
    assert main(['gen',str(EXAMPLE),'--out',str(tmp_path/'supplied'),'--lang','kotlin'])==0
    assert not (tmp_path/'supplied/kotlin/cbor.kt').exists()
    # emit_all's three positional arguments stay compatible; all added controls
    # must reach emit as keywords, including the target-keyed bindings.
    from taut.gen import scaffold
    captured={}
    def record(*args,**kwargs): captured.update(kwargs);return []
    monkeypatch.setattr(scaffold,'emit',record)
    bindings={'kotlin':{'owner':'taut.kotlin.foundation'}}
    mapping={'Child':'taut.Child'}
    assert emit_all(s,'ignored',tmp_path/'forward',langs=['kotlin'],runtime_mode='package',validation=True,
                    runtime_bindings=bindings,kotlin_external_types=mapping)==[]
    assert captured['runtime_mode']=='package' and captured['validation'] is True
    assert captured['runtime_bindings'] is bindings and captured['kotlin_external_types'] is mapping


def test_scalar_semantics_matrix_matches_python_reference(tmp_path,tools,foundation):
    import sys
    import types
    from taut.gen.python import emit_types as python_types
    s=load_schema(EXAMPLE)
    module=types.ModuleType('_kotlin_python_reference');sys.modules[module.__name__]=module
    exec(python_types(s,validation=True),module.__dict__)
    rows=[]; expressions=[]
    for tag in module.ContentKind:
        for mask in range(16):
            data={k:v for i,(k,v) in enumerate([('text',''),('number',0),('flag',False),('items',[])]) if mask & (1<<i)}
            obj=module.Content(tag,**data)
            for recursive in (False,True):
                r=obj.validate(recursive=recursive)
                rows.append(dict(issues=[dict(code=i.code,rule=i.rule,path=[p.field_name for p in i.path]) for i in r.issues],
                                 deferred=[],valid=r.is_valid(),complete=r.is_complete(),scope=r.scope))
                values={'text':'""','number':'0L','flag':'false','items':'emptyList()'}
                expr='Content(ContentKind.'+tag.name+''.join(', '+k+'='+values[k] for k in data)+')'
                expressions.append(f'emit({expr}, {str(recursive).lower()})')
    d=tmp_path/'generated';emit_direct(s,d,validation=True,mode='package')
    source='''import taut.*
fun emit(v:Content, recursive:Boolean) {
 val r=v.validate(recursive)
 check(v.isValid(recursive)==(r.isValid() && r.isComplete()))
 val issues=r.issues.joinToString(",") { i -> "{\\"code\\":\\"${i.code}\\",\\"rule\\":\\"${i.rule}\\",\\"path\\":["+i.path.joinToString(",") { "\\"${it.fieldName}\\"" }+"]}" }
 println("{\\"issues\\":[$issues],\\"deferred\\":[],\\"valid\\":${r.isValid()},\\"complete\\":${r.isComplete()},\\"scope\\":\\"${r.scope}\\"}")
}
fun main() {
'''+'\n'.join(expressions)+'\n}'
    output=compile_program(tmp_path,source,tools,sources=[d/'api.kt'],dependencies=[foundation])
    assert [json.loads(line) for line in output.splitlines()]==rows


def test_groups_virtual_coverage_all_messages_and_nonselected_children(tmp_path,tools,foundation):
    choice=Enum('Choice',child=0,number=1,empty=2)
    flag=Enum('Flag',yes=0,no=1)
    child=child_schema()
    extra=schema(choice,flag,
        Branch=Msg(kind=F(1,OneOf(choice)),child=F(2,Ref.Child,Case(kind=choice.child)),
                   number=F(3,INT,Case(kind=choice.number)),other=F(4,OneOf(flag,exhaustive=True)),
                   yes=F(5,BOOL,Case(other=flag.yes)),no=F(6,STR,Case(other=flag.no))),
        VirtualAll=Msg(kind=F(1,OneOf(flag,virtual=True,exhaustive=True)),
                       yes=F(2,Ref.Child,Case(kind=flag.yes)),no=F(3,INT,Case(kind=flag.no))),
        VirtualSome=Msg(kind=F(1,OneOf(flag,virtual=True)),yes=F(2,INT,Case(kind=flag.yes))),
        Bare=Msg(), Wrapper=Msg(child=F(1,Ref.Child)),
        BooleanKeys=Msg(children=F(1,Map(BOOL,Ref.Child))))
    s=dataclasses.replace(extra,enums={**child.enums,**extra.enums},messages={**child.messages,**extra.messages})
    d=tmp_path/'generated';emit_direct(s,d,validation=True,mode='package')
    program='''import taut.*
fun main() {
 val c=Child(ChildKind.text)
 val b=Branch(Choice.number,c,null,Flag.yes)
 val r=b.validate(); check(r.issues.map { it.code }==listOf("oneof.payload_unexpected","oneof.payload_missing","oneof.payload_missing","oneof.payload_missing"))
 check(r.issues.map { it.path.joinToString(".") { it.fieldName ?: "?" } }==listOf("child","number","child.text","yes"))
 check(b.validate(false).issues.size==3)
 check(!b.isValid() && !b.isValid(false))
 b.child=null;b.number=0;b.yes=false;check(b.isValid())
 b.kind=Choice.empty;b.number=null;check(b.isValid())
 val v=VirtualAll(c,0L);check(v.validate().issues.size==1 && v.validate().deferredChecks.size==1)
 check(v.validate(false).isValid() && !v.isValid(false))
 check(!VirtualSome().isValid() && !VirtualSome().validate().isComplete())
 check(Bare().isValid() && Bare().isValid(false) && Bare().validate().isComplete())
 check(Wrapper(c).isValid(false) && !Wrapper(c).isValid())
 val keys=BooleanKeys(linkedMapOf(true to c,false to c)).validate().issues.map { it.path[1].keyCborBase64 }
 check(keys==listOf("9A==","9Q=="))
 check(VirtualAll.descriptor().oneofs[0].exhaustive)
 println("all-message-methods/independent-groups/nonselected-child/coverage/boolean-keys PASS")
}'''
    assert 'PASS' in compile_program(tmp_path,program,tools,sources=[d/'api.kt'],dependencies=[foundation])


def test_immutable_metadata_configuration_and_boolean_short_circuit(tmp_path,tools,foundation):
    program='''import taut.validation.*
import taut.validation.descriptors.*
class Draft(var kind:Long=0,var text:String?=null)
fun main() {
 val e=EnumDescriptor("Tag","probe.Tag",listOf(EnumMemberDescriptor("text",0)))
 val nested=mutableListOf<Any?>("before");val source=mutableMapOf<String,Any?>("nested" to nested,"bytes" to byteArrayOf(1,2))
 val fields=listOf(FieldDescriptor("kind","kind",1,TypeDescriptor("enum",enum={e}),"required",false,false),
                   FieldDescriptor("text","text",2,TypeDescriptor("str"),"nullable",false,false))
 val group=OneOfDescriptor("kind",{e},false,true,listOf(OneOfMemberDescriptor("text",0,"text")))
 fun descriptor(rule:String=ONEOF_RULE)=MessageDescriptor("Draft","probe.Draft",1,fields,listOf(group),
   listOf(ConstraintDescriptor(rule,mapOf("controlling_field" to "kind"))),emptyList(),emptyList(),3,source,emptyMap())
 val d=descriptor();nested.clear();source.clear()
 check((d.options["nested"] as List<*>).single()=="before")
 val stored=d.options["bytes"] as ImmutableBytes;val exposed=stored.bytes;exposed[0]=9;check(stored.bytes[0]==1.toByte())
 try { (d.options as MutableMap<String,Any?>).clear();error("mutable options") } catch (_:UnsupportedOperationException) {}
 try { (d.options["nested"] as MutableList<Any?>).clear();error("mutable nested") } catch (_:UnsupportedOperationException) {}
 var traversals=0
 val binding=SchemaBinding<Draft>(d,{}, {v,i->if(i==0)v.kind else v.text},{_,_,_->traversals++;true})
 val draft=Draft()
 check(!ValidationEngine.isValid(binding.bind(draft)));check(traversals==0)
 check(!ValidationEngine.validate(binding.bind(draft)).isValid());check(traversals==1)
 draft.text="";check(ValidationEngine.isValid(binding.bind(draft)))
 draft.kind=123;val invalid=ValidationEngine.validate(binding.bind(draft));check(invalid.issues.single().code=="oneof.invalid_discriminator")
 try { descriptor("future.unsupported").check();error("accepted rule") } catch(e:ConfigurationError) {check(e.message!!.contains("unsupported constraint"))}
 try { Foundation.require("old","taut.kotlin.foundation",2,1,emptyList());error("old") } catch(_:ConfigurationError) {}
 try { Foundation.require("split","taut.java.foundation",1,1,emptyList());error("split") } catch(_:ConfigurationError) {}
 try { Foundation.require("future","taut.kotlin.foundation",1,1,listOf("future.capability"));error("future") } catch(_:ConfigurationError) {}
 println("immutable-metadata/config-errors/fast-short-circuit PASS")
}'''
    assert 'PASS' in compile_program(tmp_path,program,tools,dependencies=[foundation])


@pytest.mark.parametrize('component',['trailing.','trailing ','NUL','COM1'])
@pytest.mark.skipif(os.name!='nt',reason='Windows namespace guard')
def test_windows_namespace_identity_rejected_before_mutation(tmp_path,component):
    unsafe=Path('\\\\?\\'+str(tmp_path/component))
    with pytest.raises(ValueError,match='namespace path component'):
        kotlin_runtime.canonical_path(unsafe)
    assert not list(tmp_path.iterdir())


def test_kotlin_native_enum_name_collision_independent_of_python_authoring():
    from taut.ir.model import EnumDef, Schema, EnumRef
    # Kotlin's Enum.name getter is a real native collision, unrelated to which
    # authoring accessor supplies EnumMemberRef in Python.
    with pytest.raises(ValueError,match='Kotlin generated enum symbol collision'):
        kotlin.emit_types(Schema(enums={'Tag':EnumDef('Tag',{'name':0})},messages={}))


def test_compatible_unequal_build_labels_and_codec_owner_guard(tmp_path,tools):
    d=tmp_path/'generated';emit_direct(load_schema(EXAMPLE),d,validation=True,mode='source')
    descriptor=d/'descriptors.kt'
    descriptor.write_text(descriptor.read_text().replace('kotlin-oneof-reference.1','kotlin-oneof-reference.99'))
    codec=d/'cbor.kt'
    codec.write_text(codec.read_text().replace('val owner = "taut.kotlin.foundation"','val owner = "wrong.codec.owner"'))
    program='''import taut.*
import taut.validation.descriptors.*
fun main() {
 check(Foundation.build=="kotlin-oneof-reference.99")
 try { Content(ContentKind.empty).isValid();error("bad codec owner accepted") }
 catch(e:ConfigurationError) { check(e.message!!.contains("wrong.codec.owner")); println("codec owner rejected PASS") }
}'''
    assert 'PASS' in compile_program(tmp_path,program,tools,sources=list(d.glob('*.kt')))
    codec.write_text(codec.read_text().replace('wrong.codec.owner','taut.kotlin.foundation'))
    program='''import taut.*
import taut.validation.descriptors.*
fun main() { check(Foundation.build=="kotlin-oneof-reference.99");check(Content(ContentKind.empty).isValid());println("compatible unequal build accepted PASS") }'''
    assert 'PASS' in compile_program(tmp_path,program,tools,sources=list(d.glob('*.kt')),name='patch')


def test_kotlin_escaping_valid_names_and_i64_enum_edges(tmp_path,tools,foundation):
    from taut.ir.model import EnumDef, Schema, EnumRef
    # Feed native facts to avoid coupling to the user's evolving Enum authoring
    # accessor. These names are legal Kotlin projections and keep original paths.
    enum=EnumDef('EscapedTag',{'metadata':-(1<<63),'when':(1<<63)-1})
    fields=schema(Names=Msg(__hidden=F(1,INT),taut=F(2,INT),metadata=F(3,INT),when=F(4,INT),tag=F(5,EnumRef('EscapedTag'))))
    keyword=schema(Msg('class',F('when',1,EnumRef('when'))))
    s=Schema(enums={'EscapedTag':enum,'when':EnumDef('when',{'metadata':0})},messages={**fields.messages,**keyword.messages})
    d=tmp_path/'generated';emit_direct(s,d,validation=True,mode='package',identity='dollar$\f\\f')
    program='''import taut.*
fun main() {
 val v=Names(0,0,0,0,EscapedTag.metadata);check(v.isValid())
 check(v.__hidden==0L && v.taut==0L && v.metadata==0L && v.`when`==0L)
 check(EscapedTag.metadata.wire==Long.MIN_VALUE && EscapedTag.`when`.wire==Long.MAX_VALUE)
 check(Names.descriptor().fields[3].name=="when" && Names.descriptor().fields[3].attribute=="`when`")
 check(Names.descriptor().qualifiedName.contains('$'))
 check(Names.decode(encode(v.toCbor())).tag==EscapedTag.metadata)
 val keyword=`class`(`when`.metadata);check(keyword.isValid())
 check(`class`.decode(encode(keyword.toCbor())).`when`==`when`.metadata)
 println("target-escaping/allowed-native-names/i64-enum-edges PASS")
}'''
    assert 'PASS' in compile_program(tmp_path,program,tools,sources=[d/'api.kt'],dependencies=[foundation])


def test_separately_linked_child_and_codec_replacements_are_checked_at_runtime(tmp_path,tools,foundation,child_artifact):
    d=tmp_path/'generated'
    api=emit_direct(parent_schema(),d,validation=True,mode='package',external_types={'Child':'taut.Child','ChildKind':'taut.ChildKind'})
    program='''import taut.*
import taut.validation.descriptors.*
fun main() {
 try {
  check(!Parent(Child(ChildKind.text),emptyList(),emptyMap()).validate().isValid())
  println("good child")
 } catch(e:ConfigurationError) { println(e.message) }
}'''
    main=compile_program(tmp_path,program,tools,sources=[api],dependencies=[child_artifact,foundation],execute=False)
    good=run([tools[1],'-cp',os.pathsep.join(map(str,[main,child_artifact,foundation])),'MainKt']).stdout
    assert good.strip()=='good child'
    child=tmp_path/'replacement-child.kt'
    child.write_text(kotlin.emit_types(child_schema()).replace('val TAUT_FACTS_FINGERPRINT = "','val TAUT_FACTS_FINGERPRINT = "replacement_',1))
    replacement=tmp_path/'replacement-child.jar'
    run([tools[0],child,'-jvm-target','1.8','-classpath',foundation,'-d',replacement])
    result=run([tools[1],'-cp',os.pathsep.join(map(str,[main,replacement,foundation])),'MainKt']).stdout
    assert 'facts mismatch' in result and 'good child' not in result
    codec=tmp_path/'replacement-codec.kt'
    codec.write_text((RUNTIME/'cbor.kt').read_text().replace('val owner = "taut.kotlin.foundation"','val owner = "replacement.codec.owner"'))
    badcodec=tmp_path/'replacement-codec.jar'
    run([tools[0],codec,'-jvm-target','1.8','-d',badcodec])
    result=run([tools[1],'-cp',os.pathsep.join(map(str,[main,badcodec,child_artifact,foundation])),'MainKt']).stdout
    assert 'replacement.codec.owner' in result and 'regenerate/rebind codec' in result and 'good child' not in result


def test_split_source_foundations_fail_target_build(tmp_path,tools):
    a=tmp_path/'a';b=tmp_path/'b'
    emit_direct(child_schema(),a,mode='source',identity='child')
    emit_direct(parent_schema(),b,validation=True,mode='source',identity='parent',
                external_types={'Child':'taut.Child','ChildKind':'taut.ChildKind'})
    result=compile_program(tmp_path,'fun main() {}',tools,sources=[*a.glob('*.kt'),*b.glob('*.kt')],success=False)
    assert 'redeclaration' in result.stderr.lower() or 'conflicting' in result.stderr.lower()


def test_recursive_virtual_cycle_and_key_reports_match_python_reference(tmp_path,tools,foundation):
    import sys
    import types
    from taut.gen.python import emit_types as python_types
    s=load_schema(EXAMPLE)
    m=types.ModuleType('_kotlin_recursive_reference');sys.modules[m.__name__]=m
    exec(python_types(s,validation=True),m.__dict__)
    bad=m.Content(m.ContentKind.text)
    cycle=m.Tree(None,[]);cycle.children=[cycle]
    cases=[(m.Envelope(bad),'Envelope(bad)'),(m.VirtualEnvelope(content=bad),'VirtualEnvelope(bad)'),
           (m.VirtualEnvelope(content=m.Content(m.ContentKind.text,text='')),'VirtualEnvelope(Content(ContentKind.text,text=""))'),
           (m.Collection([bad,bad],{'aa':bad,'b':bad}),'Collection(listOf(bad,bad),linkedMapOf("aa" to bad,"b" to bad))'),
           (m.Tree(None,[m.Tree(bad,[])]),'Tree(null,listOf(Tree(bad,emptyList())))'),(cycle,'cycle')]
    expected=[];calls=[]
    def path(items):
        return [dataclasses.asdict(p) for p in items]
    for obj,expr in cases:
        for recursive in (False,True):
            r=obj.validate(recursive=recursive)
            expected.append(dict(issues=[dict(code=i.code,rule=i.rule,path=path(i.path)) for i in r.issues],
                                 deferred=[dict(rule=i.rule,path=path(i.path),reason_code=i.reason_code) for i in r.deferred_checks],
                                 valid=r.is_valid(),complete=r.is_complete(),scope=r.scope))
            calls.append(f'emit({expr}.validate({str(recursive).lower()}), {expr}.isValid({str(recursive).lower()}))')
    source=r'''import taut.*
import taut.validation.*
fun q(s:String?):String=if(s==null) "null" else "\""+s+"\""
fun path(p:List<PathSegment>):String=p.joinToString(",","[","]") {
 "{\"kind\":"+q(it.kind)+",\"field_name\":"+q(it.fieldName)+",\"index\":"+(it.index?.toString()?:"null")+",\"key_type\":"+q(it.keyType)+",\"key_cbor_base64\":"+q(it.keyCborBase64)+"}"
}
fun emit(r:ValidationReport,fast:Boolean) {
 check(fast==(r.isValid()&&r.isComplete()))
 val issues=r.issues.joinToString(",","[","]") { "{\"code\":"+q(it.code)+",\"rule\":"+q(it.rule)+",\"path\":"+path(it.path)+"}" }
 val deferred=r.deferredChecks.joinToString(",","[","]") { "{\"rule\":"+q(it.rule)+",\"path\":"+path(it.path)+",\"reason_code\":"+q(it.reasonCode)+"}" }
 println("{\"issues\":$issues,\"deferred\":$deferred,\"valid\":${r.isValid()},\"complete\":${r.isComplete()},\"scope\":\"${r.scope}\"}")
}
fun main() {
 val bad=Content(ContentKind.text)
 val cycle=Tree(null,emptyList());cycle.children=listOf(cycle)
'''+ '\n'.join(calls)+'\n}'
    d=tmp_path/'generated';emit_direct(s,d,validation=True,mode='package')
    output=compile_program(tmp_path,source,tools,sources=[d/'api.kt'],dependencies=[foundation])
    assert [json.loads(line) for line in output.splitlines()]==expected


def test_external_effective_options_and_ordered_facts(tmp_path,tools,foundation,child_artifact):
    s=parent_schema()
    enum=s.enums['ChildKind']
    # Map declaration order is not a contract difference; normalized facts and
    # descriptor links accept an equivalent independently emitted enum.
    reordered=dataclasses.replace(s,enums={'ChildKind':dataclasses.replace(enum,members=dict(reversed(list(enum.members.items()))))})
    d=tmp_path/'ordered';api=emit_direct(reordered,d,validation=True,mode='package',external_types={'Child':'taut.Child','ChildKind':'taut.ChildKind'})
    program='''import taut.*
fun main(){check(Parent(Child(ChildKind.empty),emptyList(),emptyMap()).isValid());println("equivalent enum order PASS")}'''
    assert 'PASS' in compile_program(tmp_path/'order',program,tools,sources=[api],dependencies=[child_artifact,foundation])
    changed=dataclasses.replace(s,options={'max_depth':64})
    d=tmp_path/'bounds';api=emit_direct(changed,d,validation=True,mode='package',external_types={'Child':'taut.Child','ChildKind':'taut.ChildKind'})
    program='''import taut.*
import taut.validation.descriptors.*
fun main(){try{Parent(Child(ChildKind.empty),emptyList(),emptyMap()).validate();error("accepted")}
catch(e:ConfigurationError){check(e.message!!.contains("Child facts mismatch"));println("inherited codec options rejected PASS")}}'''
    assert 'PASS' in compile_program(tmp_path/'bounds-run',program,tools,sources=[api],dependencies=[child_artifact,foundation])


def test_independent_source_schemas_and_facade_share_one_actual_owner(tmp_path,tools):
    from taut.gen.scaffold import emit
    owner=tmp_path/'foundation';bindings={'kotlin':{'source_root':str(owner)}}
    child=tmp_path/'child';parent=tmp_path/'parent';diagnostic=tmp_path/'diagnostic'
    emit(child_schema(),child,langs=['kotlin'],services=[],runtime_mode='source',runtime_bindings=bindings,schema_identity='shared-source-child')
    child_api=child/'kotlin/api.kt';before=child_api.read_bytes()
    emit(parent_schema(),parent,langs=['kotlin'],services=[],runtime_mode='source',validation=True,runtime_bindings=bindings,
         kotlin_external_types={'Child':'taut.Child','ChildKind':'taut.ChildKind'},schema_identity='shared-source-parent')
    emit(schema(Diagnostic=Msg()),diagnostic,langs=['kotlin'],services=[],runtime_mode='source',validation=True,
         runtime_bindings=bindings,schema_identity='shared-source-diagnostic')
    assert child_api.read_bytes()==before and (owner/'validation.kt').exists()
    manifest=json.loads((owner/'.taut-kotlin-runtime.json').read_text())
    assert len(manifest['users'])==3
    facade=tmp_path/'facade.kt'
    facade.write_text('''package facade
typealias Report=taut.validation.ValidationReport
typealias Descriptor=taut.validation.descriptors.MessageDescriptor
fun identity(value:Report):Report=value
fun codec(value:taut.Cbor):taut.Cbor=value
''')
    program='''import taut.*
import taut.validation.*
fun main() {
 val parent=Parent(Child(ChildKind.text),emptyList(),emptyMap())
 val reports:List<ValidationReport> = listOf(parent.validate(),Diagnostic().validate())
 check(facade.identity(reports[0])===reports[0] && reports[1].isValid())
 val descriptor:facade.Descriptor=Parent.descriptor();check(descriptor===Parent.descriptor())
 val value:Cbor=parent.toCbor();check(facade.codec(value)===value)
 val aggregate:List<ValidationIssue>=reports.flatMap { it.issues }
 check(aggregate.single().code=="oneof.payload_missing")
 println("source/source/independent-reports/facade-identity/shared-codec PASS")
}'''.replace('List<ValidationIssue>=','List<ValidationIssue> =')
    sources=[*owner.glob('*.kt'),child_api,parent/'kotlin/api.kt',diagnostic/'kotlin/api.kt',facade]
    assert 'PASS' in compile_program(tmp_path,program,tools,sources=sources)


def test_mode_goldens_and_source_package_canonical_provenance(tmp_path):
    from taut.gen.scaffold import emit
    s=load_schema(EXAMPLE);goldens={}
    for validation in (False,True):
        for mode in ('source','package',None):
            d=tmp_path/(str(validation)+'-'+str(mode))
            emit(s,d,langs=['kotlin'],services=[],runtime_mode=mode,validation=validation,schema_identity='mode-golden')
            target=d/'kotlin';api=(target/'api.kt').read_text()
            goldens[validation,mode]=api
            assert api.count('fun descriptor(): taut.validation.descriptors.MessageDescriptor')==len(s.messages)
            assert api.count('fun validate(recursive: Boolean = true)')==(len(s.messages) if validation else 0)
            assert api.count('fun isValid(recursive: Boolean = true)')==(len(s.messages) if validation else 0)
            if mode=='source':
                manifest=json.loads((target/'.taut-kotlin-runtime.json').read_text())
                for name,resource in kotlin_runtime.FILES.items():
                    if name=='validation.kt' and not validation:
                        assert not (target/name).exists();continue
                    canonical=(RUNTIME/resource).read_bytes()
                    assert (target/name).read_bytes()==canonical
                    assert manifest['files'][name]==hashlib.sha256(canonical).hexdigest()
            else:
                assert {p.name for p in target.glob('*.kt')}=={'api.kt'}
        assert goldens[validation,'source']==goldens[validation,'package']==goldens[validation,None]
    # Every disabled-to-enabled source delta belongs to the optional wrappers,
    # their import or the explicit engine contract check. Mandatory facts match.
    stripped='\n'.join(line for line in goldens[True,'source'].splitlines()
                       if '_TautValidationEngine' not in line and 'ValidationEngine.contract' not in line)
    assert stripped+'\n'==goldens[False,'source']
