"""Native Go execution, Python-normalized semantics, module identity and ownership."""
import dataclasses
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import types
import zipfile
import pytest
from taut.gen.scaffold import emit, emit_all, python_api
from taut.gen.go import emit_types
from taut.gen.go_metadata import fingerprint
from taut.gen.go_runtime import (OWNER, CAPABILITIES, FILES, ENGINE, canonical_sources,
    build_foundation, verify_artifact, canonical_path, binding, _go_env)
from taut.ir.dsl import STR, INT, BOOL, Enum, F, Msg, Ref, OneOf, Case, List, Map, schema
from taut.ir.load import load_schema, schema_from_json
from taut.ir.export import schema_json

ROOT=Path(__file__).resolve().parents[2]
EXAMPLE=ROOT/'dev-docs/examples/go-oneof'
SCHEMA=load_schema(EXAMPLE/'content.taut.py')


def go_run(root, *, ok=True, command=None):
    result=subprocess.run(['go',*(command or ['run','./app'])],cwd=root,env=_go_env(),capture_output=True,text=True,encoding='utf-8')
    if ok: assert result.returncode==0,result.stdout+result.stderr
    return result


def module(root, extra=''):
    root.mkdir(parents=True,exist_ok=True)
    (root/'go.mod').write_text('module example.local/app\n\ngo 1.20\n'+extra)


def app(root,code,imports=''):
    (root/'app').mkdir(exist_ok=True)
    (root/'app/main.go').write_text('package main\n'+imports+'\nfunc main(){'+code+'}\n',encoding='utf-8')


def python_rows():
    m=types.ModuleType('_go_oneof_reference'); sys.modules[m.__name__]=m
    exec(python_api(SCHEMA,validation=True),m.__dict__)
    rows=[]
    def row(name,v,recursive=True):
        report=v.validate(recursive=recursive)
        assert v.is_valid(recursive=recursive)==(report.is_valid() and report.is_complete())
        def path(p): return '/'.join('f='+s.field_name if s.kind=='field' else 'i='+str(s.index) if s.kind=='index' else 'k='+s.key_type+','+s.key_cbor_base64 for s in p)
        r=[name,report.scope,str(report.is_valid()).lower(),str(report.is_complete()).lower()]
        r+=['I:'+i.code+':'+i.rule+':'+path(i.path) for i in report.issues]
        r+=['D:'+d.reason_code+':'+d.rule+':'+path(d.path) for d in report.deferred_checks]
        rows.append('\t'.join(r))
    def content(kind): return m.Content(kind=kind)
    c=content(m.ContentKind.text); row('missing',c); c.text=''; row('empty',c); c.number=0; row('extra',c); row('roundtrip',c)
    c.kind=m.ContentKind.number; c.text=None; row('zero',c)
    c.kind=m.ContentKind.flag; c.number=None; c.flag=False; row('false',c)
    c.flag=None; c.kind=m.ContentKind.items; c.items=[]; row('empty-list',c)
    c.items=None; c.kind=m.ContentKind.empty; row('payload-free',c)
    c.kind=None; c.child=content(m.ContentKind.text); row('bad-tag-child',c)
    c.kind=m.ContentKind.empty; row('nonselected-child',c)
    c.kind=m.ContentKind.child; c.child=c; row('cycle',c)
    bad=content(m.ContentKind.text)
    w=m.Wrapper(bad,[bad,bad],{'z':bad,'':bad,'aa':bad},{-1:bad,24:bad,0:bad},{True:bad,False:bad})
    row('wrapper',w); row('local',w,False)
    v=m.Virtual(child=bad); row('virtual-child',v); bad.text=''; row('virtual-repaired',v); row('virtual-local',v,False)
    row('independent',m.Multi(left=None,right=m.ContentKind.number)); row('plain',m.Plain(0,None,None))
    return rows


@pytest.fixture(scope='module')
def package(tmp_path_factory):
    root=tmp_path_factory.mktemp('go-foundation')
    owner=build_foundation(root/'built','foundation.local/runtime')
    archive=root/'foundation.zip'
    with zipfile.ZipFile(archive,'w') as z:
        for path in owner.iterdir(): z.write(path,path.name)
    with zipfile.ZipFile(archive) as z: z.extractall(root/'extracted')
    return root/'extracted'


@pytest.mark.parametrize('mode',['source','package',None])
def test_python_normalized_conformance(tmp_path,package,mode):
    module(tmp_path,'require foundation.local/runtime v0.0.0\nreplace foundation.local/runtime => '+package.as_posix()+'\n' if mode!='source' else '')
    config=None if mode=='source' else {'go':{'import_path':'foundation.local/runtime','artifact':str(package)}}
    emit(SCHEMA,tmp_path,langs=['go'],services=[],runtime_mode=mode,validation=True,runtime_bindings=config)
    (tmp_path/'app').mkdir()
    code=(EXAMPLE/'conformance.go').read_text().replace('@API@','example.local/app/go')
    if mode=='source': code=code.replace('\n\tr "@RUNTIME@"','').replace('r.','a.')
    else: code=code.replace('@RUNTIME@','foundation.local/runtime')
    (tmp_path/'app/main.go').write_text(code)
    result=go_run(tmp_path)
    assert result.stdout.splitlines()==python_rows()
    if mode=='source':
        for name,data in canonical_sources().items(): assert (tmp_path/'go'/name).read_bytes()==data
    else: assert not (tmp_path/'go/cbor.go').exists()


@pytest.mark.parametrize('validation',[False,True])
def test_mandatory_metadata_owned_snapshots_engine_free(tmp_path,validation):
    emit(SCHEMA,tmp_path,langs=['go'],services=[],runtime=True,validation=validation)
    module(tmp_path)
    app(tmp_path,'''
      d:=a.DescribeContent(); var v *a.Content; if v.Descriptor()!=d || len(d.Fields())!=6 || len(d.Oneofs())!=1 {panic("mandatory metadata")}
      if n,ok:=d.NextID(); !ok || n!=9 {panic("next id")}; if d.ReservedNumbers()[0]!=7 || d.ReservedNames()[0]!="retired" {panic("reservations")}
      d.Fields()[0]=nil; d.Oneofs()[0].Members()["empty"]="text"; d.ReservedNumbers()[0]=99; d.EffectiveOptions()["max_depth"]=int64(0)
      d.Fields()[0].Options()["x"]=true; d.Constraints()[0].Parameters()["controlling_field"]="wrong"
      a.DescribeSchema().Messages()["Content"]=nil; a.DescribeContentKind().Members()["text"]=99
      if d.Fields()[0]==nil || d.Oneofs()[0].Members()["empty"]!="" || d.EffectiveOptions()["max_depth"]!=int64(32) || d.Constraints()[0].Parameters()["controlling_field"]!="kind" {panic("snapshot")}
      vf:=a.DescribeVirtual().Fields()[0]; if !vf.Virtual() || vf.Access()!="" || vf.Type().Enum()!=a.DescribeContentKind() {panic("virtual fact")}
      if d.Fields()[3].Type().Message()!=d || a.DescribeSchema().IRVersion()!=3 {panic("recursive publication")}
      c:=a.Content{Kind:a.ContentKindEmpty}; binding:=a.TautBindingContent(); if binding.Read(&c,"kind")!=a.ContentKindEmpty || binding.Present(&c,"text") {panic("typed primitive/presence adapter")}
    ''','import a "example.local/app/go"')
    go_run(tmp_path)
    assert (tmp_path/'go/validation.go').exists()==validation
    text=(tmp_path/'go/api.go').read_text()
    assert (' Validate() ' in text)==validation


def ext(name,path):
    return {'type':name,'import_path':path,'owner':OWNER,'descriptor_contract':1,'codec_contract':1,'capabilities':sorted(CAPABILITIES)}


@pytest.mark.parametrize('mode',['source','package',None])
@pytest.mark.parametrize('child_validation',[False,True])
def test_independent_disabled_child_actual_nominal_owner(tmp_path,package,mode,child_validation):
    k=Enum('ChildKind',text=0,empty=1)
    child=schema(k,Child=Msg(kind=F(1,OneOf(k)),text=F(2,STR,Case(kind=k.text))))
    # Build the composed schema through the real native IR reader; no child regeneration.
    d=schema_json(child); d['messages'].append({'name':'Parent','options':{},'effective':d['effective'],'reserved_tags':[],'reserved_names':[],'next_id':None,'fields':[{'name':'child','tag':1,'options':{},'type':{'k':'msg','name':'Child'},'optional':False,'transient':False,'merge':None}]})
    parent=schema_from_json(d)
    module(tmp_path,'require foundation.local/runtime v0.0.0\nreplace foundation.local/runtime => '+package.as_posix()+'\n' if mode!='source' else '')
    owner=tmp_path/'foundation' if mode=='source' else package
    runtime_path='example.local/app/foundation' if mode=='source' else 'foundation.local/runtime'
    config={'go':{'import_path':runtime_path,**({'source_root':str(owner)} if mode=='source' else {'artifact':str(owner)})}}
    emit(child,tmp_path/'child',langs=['go'],services=[],runtime_mode=mode,validation=child_validation,runtime_bindings=config)
    go_run(tmp_path,command=['test','./child/go'])
    before=(tmp_path/'child/go/api.go').read_bytes()
    external={n:ext(n,'example.local/app/child/go') for n in ('Child','ChildKind')}
    emit(parent,tmp_path/'parent',langs=['go'],services=[],runtime_mode=mode,validation=True,runtime_bindings=config,go_external_types=external)
    assert (tmp_path/'child/go/api.go').read_bytes()==before
    app(tmp_path,'''
      c:=child.Child{Kind:child.ChildKindText}; p:=parent.Parent{Child:c}
      var report rt.ValidationReport=p.Validate(); if report.IsValid() || p.IsValid() || len(report.Issues())!=1 {panic("child metadata traversal")}
      if !p.IsValidWithOptions(parent.ValidationOptions{}) || parent.DescribeChild()!=child.DescribeChild() {panic("local/nominal child identity")}
      var codec rt.Cbor=p.Child.ToCbor(); _=codec; var x parent.Child=c; _=x
    ''','import (child "example.local/app/child/go"; parent "example.local/app/parent/go"; rt '+json.dumps(runtime_path)+')')
    go_run(tmp_path)


@pytest.mark.parametrize('case',['Descriptor','descriptor','validate','validate_with_options','is_valid'])
def test_names_fail_before_writes(tmp_path,case):
    s=schema(Thing=Msg(**{case:F(1,INT)}))
    with pytest.raises(ValueError,match='Go'): emit(s,tmp_path,langs=['go'],services=[],runtime=True,validation=True)
    assert not list(tmp_path.rglob('*'))


@pytest.mark.parametrize('bad',['type','Kind','Cbor','DescribeThing','ValidationOptions'])
def test_native_type_symbols_rejected_before_writes(tmp_path,bad):
    s=schema(**{bad:Msg(value=F(1,INT)),'Thing':Msg(value=F(1,INT))})
    with pytest.raises(ValueError): emit(s,tmp_path,langs=['go'],services=[],runtime=True)
    assert not list(tmp_path.rglob('*'))


def test_validation_name_allowed_disabled_and_metadata_member_names(tmp_path):
    # EnumMemberRef/IR keeps the user's parallel authoring patch out of this lane.
    d=schema_json(schema(Enum('Choice',ok=0),Thing=Msg(validate=F(1,INT),tag=F(2,Ref('Choice')))))
    d['enums'][0]['members']={'name':0,'metadata':1}; d['enums'][0]['member_options']={'name':{},'metadata':{}}
    s=schema_from_json(d)
    emit(s,tmp_path,langs=['go'],services=[],runtime=True)
    module(tmp_path); app(tmp_path,'v:=a.Thing{Validate:0,Tag:a.ChoiceMetadata}; if v.Descriptor().Fields()[0].Name()!="validate" {panic("native naming")}; _=v.ToCbor()','import a "example.local/app/go"')
    go_run(tmp_path)


def tree(root): return {str(p.relative_to(root)):p.read_bytes() for p in root.rglob('*') if p.is_file()}


@pytest.mark.parametrize('tamper',['api','runtime','handwritten','mode','caps','namespace'])
def test_prewrite_refusal_preserves_tree(tmp_path,tamper):
    target=tmp_path/'out'
    if tamper in ('api','runtime'):
        emit(SCHEMA,target,langs=['go'],services=[],runtime=True,validation=True)
        p=target/'go'/('api.go' if tamper=='api' else 'descriptors.go'); p.write_text(p.read_text()+'// edited\n')
    elif tamper=='handwritten':
        (target/'go').mkdir(parents=True); (target/'go/cbor.go').write_text('// mine')
    before=tree(tmp_path)
    kwargs={}
    if tamper=='mode': kwargs['runtime_mode']='package'
    if tamper=='caps': kwargs['runtime_bindings']={'go':{'capabilities':[]}}
    if tamper=='namespace': kwargs['runtime_bindings']={'go':{'source_root':str(tmp_path/'bad.')}}
    with pytest.raises(ValueError): emit(SCHEMA,target,langs=['go'],services=[],runtime=True,validation=True,**kwargs)
    assert tree(tmp_path)==before


def test_canonical_fingerprints_normalize_order_and_include_effective_codec():
    d=schema_json(SCHEMA); a=fingerprint(d['messages'][0]); reverse=json.loads(json.dumps(d['messages'][0])); reverse['fields'].reverse()
    assert fingerprint(reverse)==a
    reverse['effective']['max_depth']=12
    assert fingerprint(reverse)!=a


@pytest.mark.parametrize('case',['missing','wrong_owner','descriptor','codec','capabilities','old_checker','engine'])
def test_actual_stale_artifact_is_rejected(tmp_path,package,case):
    root=tmp_path/'stale'; shutil.copytree(package,root)
    p=root/'descriptors.go'; s=p.read_text()
    if case=='missing': p.unlink()
    elif case=='wrong_owner': p.write_text(s.replace('"taut.go.foundation"','"foreign"'))
    elif case=='descriptor': p.write_text(s.replace('const DescriptorContract = 1','const DescriptorContract = 99'))
    elif case=='codec': p.write_text(s.replace('const CodecContract = 1','const CodecContract = 99'))
    elif case=='capabilities': p.write_text(s.replace('c != "oneof.v1"','c != "missing.rule"'))
    elif case=='old_checker': p.write_text(s.replace(') ContractGuard {',') {',1).replace('return ContractGuard{FoundationOwner}','return',1))
    elif case=='engine': (root/'validation.go').unlink()
    with pytest.raises(ValueError,match='actual artifact'): verify_artifact(root,'foundation.local/runtime',validation=True)


def test_reports_are_general_owned_snapshots_and_bad_rules_are_configuration(tmp_path):
    emit(SCHEMA,tmp_path,langs=['go'],services=[],runtime=True,validation=True); module(tmp_path)
    app(tmp_path,'''
      path:=[]r.PathSegment{r.FieldPath("custom")}; issue:=r.NewValidationIssue("business.future","business.rule",path,"custom"); path[0]=r.FieldPath("changed")
      issues:=[]r.ValidationIssue{issue}; report:=r.NewValidationReport(issues,nil,""); issues[0]=r.NewValidationIssue("other","r",nil,"")
      report.Issues()[0]=r.ValidationIssue{}; report.Issues()[0].Path()[0]=r.FieldPath("again")
      n,_:=report.Issues()[0].Path()[0].FieldName(); if n!="custom" || report.Scope()!="recursive" || report.IsValid() || !report.IsComplete() {panic("owned general report")}
      for _,bad:=range []map[string]any{{},{"controlling_field":int64(1)},{"controlling_field":"kind","extra":true}} {
        func(){defer func(){if recover()==nil {panic("malformed rule accepted")}}(); r.NewConstraintDescriptor("taut.oneof.v1",bad)}()
      }
    ''','import r "example.local/app/go"')
    go_run(tmp_path)


def test_sealed_descriptor_and_binding_cannot_be_overwritten(tmp_path):
    emit(SCHEMA,tmp_path,langs=['go'],services=[],runtime=True); module(tmp_path)
    for code in ('*a.DescribeContent() = a.MessageDescriptor{}', '*a.TautBindingContent() = a.MessageBinding{}'):
        app(tmp_path,code,'import a "example.local/app/go"')
        result=go_run(tmp_path,ok=False)
        assert result.returncode and ('invalid' in result.stderr or 'cannot' in result.stderr)


def test_descriptor_inputs_and_lazy_links_are_owned_snapshots(tmp_path):
    emit(SCHEMA,tmp_path,langs=['go'],services=[],runtime=True); module(tmp_path)
    app(tmp_path,'''
      options:=map[string]any{"nested":[]any{map[string]any{"x":int64(1)}}}
      first:=r.NewMessageDescriptor("Link","a.Link",nil,nil,nil,nil,nil,nil,options,nil,"a")
      second:=r.NewMessageDescriptor("Link","b.Link",nil,nil,nil,nil,nil,nil,nil,nil,"b")
      selected:=first; typ:=r.MessageType("Link",func()r.MessageDescriptor{return selected})
      if typ.Message()!=first {panic("link")}; selected=second
      options["nested"].([]any)[0].(map[string]any)["x"]=int64(99)
      first.Options()["nested"].([]any)[0].(map[string]any)["x"]=int64(200)
      if typ.Message()!=first || first.Options()["nested"].([]any)[0].(map[string]any)["x"]!=int64(1) {panic("published snapshot")}
    ''','import r "example.local/app/go"')
    go_run(tmp_path)


def test_fast_does_not_construct_report_or_diagnostics(tmp_path):
    emit(SCHEMA,tmp_path,langs=['go'],services=[],runtime=True,validation=True); module(tmp_path)
    p=tmp_path/'go/reports.go'; text=p.read_text()
    for name in ('NewValidationIssue','NewDeferredCheck','NewValidationReport'):
        start=text.index('func '+name+'('); body=text.index('{',start)
        text=text[:body+1]+' panic("fast path constructed diagnostics"); '+text[body+1:]
    p.write_text(text)
    app(tmp_path,'''
      v:=a.Content{Kind:a.ContentKindText}; if v.IsValid(){panic("missing")}; s:=""; v.Text=&s; if !v.IsValid(){panic("present")}
      virtual:=a.Virtual{}; if virtual.IsValid(){panic("virtual")}; var nilValue *a.Content; if nilValue.IsValid(){panic("nil")}
    ''','import a "example.local/app/go"')
    go_run(tmp_path)


@pytest.mark.parametrize('transition',['disable','package','owner_move','remap','unavailable','obstruction'])
def test_shared_owner_transitions_and_old_owner_refusal(tmp_path,package,transition):
    root=tmp_path/'owner'; config={'go':{'import_path':'example.local/app/owner','source_root':str(root)}}
    one=tmp_path/'one'; two=tmp_path/'two'
    emit(SCHEMA,one,langs=['go'],services=[],runtime_mode='source',validation=True,runtime_bindings=config)
    emit(SCHEMA,two,langs=['go'],services=[],runtime_mode='source',validation=False,runtime_bindings=config)
    if transition=='disable':
        emit(SCHEMA,one,langs=['go'],services=[],runtime_mode='source',validation=False,runtime_bindings=config)
        assert not (root/ENGINE).exists() and not (root/'reports.go').exists()
        assert (root/'descriptors.go').exists() and ' Validate() ' not in (one/'go/api.go').read_text()
    elif transition=='package':
        emit(SCHEMA,one,langs=['go'],services=[],runtime_mode='package',validation=True,runtime_bindings={'go':{'import_path':'foundation.local/runtime','artifact':str(package)}})
        assert (root/'descriptors.go').exists() and not (root/ENGINE).exists()
        assert json.loads((root/'.taut-go-runtime.json').read_text())['users'].keys()=={str((two/'go/.taut-go-outputs.json').resolve()).lower() if os.name=='nt' else str((two/'go/.taut-go-outputs.json').resolve())}
    elif transition=='owner_move':
        new=tmp_path/'new'; config={'go':{'import_path':'example.local/app/new','source_root':str(new)}}
        emit(SCHEMA,one,langs=['go'],services=[],runtime_mode='source',validation=True,runtime_bindings=config)
        assert (new/ENGINE).exists() and (root/'descriptors.go').exists() and not (root/ENGINE).exists()
    else:
        if transition=='remap': config={'go':{'import_path':'other.local/owner','source_root':str(root)}}
        if transition=='unavailable': (root/'.taut-go-runtime.json').unlink()
        if transition=='obstruction': (tmp_path/'blocked').write_text('handwritten'); config={'go':{'import_path':'app.local/new','source_root':str(tmp_path/'blocked'/'owner')}}
        before=tree(tmp_path)
        with pytest.raises(ValueError): emit(SCHEMA,one,langs=['go'],services=[],runtime_mode='source',validation=True,runtime_bindings=config)
        assert tree(tmp_path)==before


def test_source_package_consumer_preserves_shared_engine(tmp_path):
    config={'go':{'import_path':'example.local/app/owner','source_root':str(tmp_path/'owner')}}
    for name,mode in [('publisher','source'),('consumer','package')]:
        emit(SCHEMA,tmp_path/name,langs=['go'],services=[],runtime_mode=mode,validation=True,runtime_bindings=config)
    emit(SCHEMA,tmp_path/'publisher',langs=['go'],services=[],runtime_mode='source',validation=False,runtime_bindings=config)
    assert (tmp_path/'owner/validation.go').exists()
    module(tmp_path)
    app(tmp_path,'v:=a.Content{Kind:a.ContentKindEmpty}; if !v.IsValid(){panic("shared engine")}', 'import a "example.local/app/consumer/go"')
    go_run(tmp_path)


def test_package_engine_free_and_compatible_unequal_build(tmp_path):
    owner=build_foundation(tmp_path/'owner','foundation.local/minimal',validation=False)
    assert not (owner/'reports.go').exists() and not (owner/ENGINE).exists()
    p=owner/'descriptors.go'; p.write_text(p.read_text().replace('go-oneof-reference.1','another.compatible.patch.99'))
    receipt=owner/'.taut-go-foundation.json'; data=json.loads(receipt.read_text()); data['files']['descriptors.go']=__import__('hashlib').sha256(p.read_bytes()).hexdigest(); receipt.write_text(json.dumps(data))
    verify_artifact(owner,'foundation.local/minimal',execute=True)
    before=tree(tmp_path)
    with pytest.raises(ValueError,match='actual artifact'):
        emit(SCHEMA,tmp_path/'enabled',langs=['go'],services=[],runtime_mode='package',validation=True,runtime_bindings={'go':{'import_path':'foundation.local/minimal','artifact':str(owner)}})
    assert tree(tmp_path)==before


@pytest.mark.parametrize('case',['unknown_control','ordinary_control','wrong_enum','duplicate','multiple_controls','exhaustive','empty','optional_tag'])
def test_native_schema_rule_errors_prewrite(tmp_path,case):
    k=Enum('Choice',a=0,b=1); other=Enum('Other',a=0)
    s=schema(k,other,M=Msg(tag=F(1,OneOf(k)),a=F(2,STR,Case(tag=k.a)),b=F(3,STR,Case(tag=k.b))))
    d=schema_json(s); fields=d['messages'][0]['fields']
    if case=='unknown_control': fields[1]['cases'][0]['controlling_field']='unknown'
    elif case=='ordinary_control': fields[0].pop('oneof')
    elif case=='wrong_enum': fields[1]['cases'][0]['enum']='Other'
    elif case=='duplicate': fields[2]['cases'][0]['member']='a'
    elif case=='multiple_controls':
        tag=json.loads(json.dumps(fields[0]));tag.update(name='other',tag=4);fields.append(tag); fields[1]['cases'].append({'controlling_field':'other','enum':'Choice','member':'a'})
    elif case=='exhaustive': fields[0]['oneof']['exhaustive']=True;fields.pop()
    elif case=='empty': d['enums'][0]['members']={}; d['enums'][0]['member_options']={}
    elif case=='optional_tag': fields[0]['optional']=True
    with pytest.raises(ValueError):
        emit(schema_from_json(d),tmp_path,langs=['go'],services=[],runtime=True)
    assert tree(tmp_path)=={}


@pytest.mark.parametrize('virtual',[False,True])
@pytest.mark.parametrize('exhaustive',[False,True])
def test_all_oneof_modes_and_multiple_members_one_payload(tmp_path,virtual,exhaustive):
    k=Enum('Choice',a=0,b=1)
    s=schema(k,M=Msg(tag=F(1,OneOf(k,virtual=virtual,exhaustive=exhaustive)),value=F(2,STR,Case(tag=k.a),Case(tag=k.b))))
    emit(s,tmp_path,langs=['go'],services=[],runtime=True,validation=True); module(tmp_path)
    tag='' if virtual else 'Tag:a.ChoiceB,'
    app(tmp_path,f'v:=a.M{{{tag}}}; s:="";v.Value=&s; r:=v.Validate(); if r.IsValid()!=true || r.IsComplete()!={str(not virtual).lower()} || v.IsValid()!={str(not virtual).lower()}{{panic("mode")}}','import a "example.local/app/go"')
    go_run(tmp_path)


@pytest.mark.parametrize('mode',['source','package',None])
@pytest.mark.parametrize('validation',[False,True])
def test_cli_runtime_validation_independence(tmp_path,package,mode,validation):
    command=[sys.executable,'-m','taut.cli','gen',str(EXAMPLE/'content.taut.py'),'--lang','go','--api-only','--out',str(tmp_path/'output')]
    if mode: command+=['--runtime',mode]
    if validation: command+=['--with-validation']
    if mode!='source':
        p=tmp_path/'binding.json';p.write_text(json.dumps({'go':{'import_path':'foundation.local/runtime','artifact':str(package)}}));command+=['--runtime-bindings',str(p)]
    result=subprocess.run(command,capture_output=True,text=True)
    assert result.returncode==0,result.stdout+result.stderr
    text=(tmp_path/'output/go/api.go').read_text()
    assert (' Validate() ' in text)==validation
    assert (tmp_path/'output/go/cbor.go').exists()==(mode=='source')


def test_go_emission_and_canonical_closure_are_gofmt_clean_without_crlf(tmp_path):
    # This is an additional exact formatting check. The two historical Windows
    # write_text/CRLF tests remain unchanged and visible in test_go.py.
    from src.tests.test_go import _generated_go
    for name,text in {**_generated_go(),'oneof_on':emit_types(SCHEMA,validation=True),'oneof_off':emit_types(SCHEMA)}.items():
        result=subprocess.run(['gofmt'],input=text,capture_output=True,text=True)
        assert result.returncode==0 and result.stdout==text,(name,result.stderr)
    for name,data in canonical_sources().items():
        result=subprocess.run(['gofmt'],input=data,capture_output=True)
        assert result.returncode==0 and result.stdout==data,(name,result.stderr)


def test_generation_never_executes_target_and_actual_forged_stale_exports_fail(tmp_path,package,monkeypatch):
    root=tmp_path/'stale'; shutil.copytree(package,root)
    p=root/'descriptors.go'; p.write_text(p.read_text().replace('const DescriptorContract = 1','const DescriptorContract = 99'))
    receipt=root/'.taut-go-foundation.json'; data=json.loads(receipt.read_text()); data['files']['descriptors.go']=__import__('hashlib').sha256(p.read_bytes()).hexdigest(); receipt.write_text(json.dumps(data))
    config={'go':{'import_path':'foundation.local/runtime','artifact':str(root)}}
    # Coherent self-reported metadata is intentionally insufficient; the native
    # generated init guard checks the actual selected compiled exports.
    with monkeypatch.context() as context:
        context.setattr(subprocess,'run',lambda *a,**k: (_ for _ in ()).throw(AssertionError('target executed during generation')))
        emit(SCHEMA,tmp_path/'app-root',langs=['go'],services=[],runtime_mode='package',validation=True,runtime_bindings=config)
    target=tmp_path/'app-root'; module(target,'require foundation.local/runtime v0.0.0\nreplace foundation.local/runtime => '+root.as_posix()+'\n')
    app(target,'_ = a.DescribeContent()','import a "example.local/app/go"')
    result=go_run(target,ok=False)
    assert result.returncode and ('regenerate/rebind' in result.stderr or 'incompatible' in result.stderr)


def test_enum_metadata_names_are_real_oneof_choices_and_nonpython_fields(tmp_path):
    k=Enum('Choice',first=0,second=1)
    d=schema_json(schema(k,M=Msg(tag=F(1,OneOf(k)),value=F(2,STR,Case(tag=k.first),Case(tag=k.second)))))
    d['enums'][0]['members']={'name':0,'metadata':1}; d['enums'][0]['member_options']={'name':{},'metadata':{}}
    d['messages'][0]['fields'][1]['name']='__value'
    for c in d['messages'][0]['fields'][1]['cases']: c['member']={'first':'name','second':'metadata'}[c['member']]
    emit(schema_from_json(d),tmp_path,langs=['go'],services=[],runtime=True,validation=True); module(tmp_path)
    app(tmp_path,'s:=""; v:=a.M{Tag:a.ChoiceMetadata,Value:&s}; if !v.IsValid() || v.Descriptor().Fields()[1].Name()!="__value" {panic("native enum/field names")}', 'import a "example.local/app/go"')
    go_run(tmp_path)


def test_native_map_slice_cycles_and_shared_collections_are_path_local(tmp_path):
    k=Enum('Choice',text=0,empty=1)
    s=schema(k,Node=Msg(tag=F(1,OneOf(k)),text=F(2,STR,Case(tag=k.text)),
        children=F(3,List(Ref('Node'))),by_key=F(4,Map(STR,Ref('Node')))),
        Root=Msg(left=F(1,Ref('Node')),right=F(2,Ref('Node'))))
    emit(s,tmp_path,langs=['go'],services=[],runtime=True,validation=True); module(tmp_path)
    app(tmp_path,'''
      m:=map[string]a.Node{}; n:=a.Node{Tag:a.ChoiceEmpty,ByKey:m}; m["loop"]=n
      r:=n.Validate(); if r.IsValid() || n.IsValid() || len(r.Issues())!=1 || r.Issues()[0].Code()!="validation.ownership_cycle" || len(r.Issues()[0].Path())!=3 {panic("map value copy hid ownership cycle")}
      list:=make([]a.Node,1); list[0]=a.Node{Tag:a.ChoiceEmpty,Children:list}; n=a.Node{Tag:a.ChoiceEmpty,Children:list}
      r=n.Validate(); if r.IsValid() || n.IsValid() || len(r.Issues())!=1 || r.Issues()[0].Code()!="validation.ownership_cycle" {panic("slice cycle")}
      shared:=map[string]a.Node{"child":a.Node{Tag:a.ChoiceText}}
      owner:=a.Node{Tag:a.ChoiceEmpty,ByKey:shared}; root:=a.Root{Left:owner,Right:owner}
      r=root.Validate(); if len(r.Issues())!=2 || r.Issues()[0].Code()!="oneof.payload_missing" || r.Issues()[1].Code()!="oneof.payload_missing" {panic("global visited hid shared path")}
    ''','import a "example.local/app/go"')
    go_run(tmp_path)


@pytest.mark.parametrize('replacement',['old','facts','split_owner'])
def test_actual_independently_built_child_replacements_are_rejected(tmp_path,package,replacement):
    child=schema(Child=Msg(value=F(1,INT)))
    parent=schema(Child=Msg(value=F(1,INT)),Parent=Msg(child=F(1,Ref('Child'))))
    module(tmp_path,'require foundation.local/runtime v0.0.0\nreplace foundation.local/runtime => '+package.as_posix()+'\n')
    config={'go':{'import_path':'foundation.local/runtime','artifact':str(package)}}
    emit(child,tmp_path/'child',langs=['go'],services=[],runtime_mode='package',runtime_bindings=config)
    go_run(tmp_path,command=['test','./child/go'])
    original=(tmp_path/'child/go/api.go').read_bytes()
    if replacement=='old':
        p=tmp_path/'child/go/api.go'; s=p.read_text(); p.write_text(s[:s.index('func DescribeChild()')])
    elif replacement=='facts':
        p=tmp_path/'child/go/api.go'; s=p.read_text(); doc=schema_json(child); p.write_text(s.replace(fingerprint(doc['messages'][0]),'replaced-incompatible-facts'))
    else:
        # Equal source compiled as a second import path is a different nominal owner.
        config={'go':{'import_path':'example.local/app/split','source_root':str(tmp_path/'split')}}
        emit(schema(Seed=Msg(value=F(1,INT))),tmp_path/'seed',langs=['go'],services=[],runtime_mode='source',validation=True,runtime_bindings=config)
    emit(parent,tmp_path/'parent',langs=['go'],services=[],runtime_mode='source' if replacement=='split_owner' else 'package',validation=True,runtime_bindings=config,go_external_types={'Child':ext('Child','example.local/app/child/go')})
    assert (tmp_path/'child/go/api.go').read_bytes()==(original if replacement=='split_owner' else p.read_bytes())
    app(tmp_path,'_ = p.DescribeParent()','import p "example.local/app/parent/go"')
    result=go_run(tmp_path,ok=False)
    assert result.returncode,result.stdout
    assert any(word in result.stderr for word in ('DescribeChild','TautBindingChild','regenerate/rebind','cannot use','does not implement'))


@pytest.mark.parametrize('after',[1,3])
def test_output_fault_is_durable_fail_closed(tmp_path,monkeypatch,after):
    from taut.gen import python_runtime
    target=tmp_path/'output'; handwritten=tmp_path/'keep.txt'; handwritten.write_text('keep')
    original=python_runtime.os.replace if hasattr(python_runtime,'os') else os.replace
    calls=0
    def fail(source,destination):
        nonlocal calls
        calls+=1
        if calls>after: raise OSError('injected output interruption')
        return original(source,destination)
    with monkeypatch.context() as context:
        context.setattr(os,'replace',fail)
        with pytest.raises(OSError,match='injected'):
            emit(SCHEMA,target,langs=['go'],services=[],runtime=True,validation=True)
    before=tree(tmp_path)
    with pytest.raises(ValueError): emit(SCHEMA,target,langs=['go'],services=[],runtime=True,validation=True)
    assert tree(tmp_path)==before and handwritten.read_text()=='keep'


@pytest.mark.skipif(os.name!='nt',reason='Windows namespace spelling')
@pytest.mark.parametrize('suffix',['ambiguous.','ambiguous ','stream:data'])
def test_raw_windows_namespace_paths_refused_before_path_coercion(tmp_path,suffix):
    raw='\\\\?\\'+str(tmp_path/suffix)
    before=tree(tmp_path)
    with pytest.raises(ValueError,match='namespace'): canonical_path(raw)
    with pytest.raises(ValueError,match='namespace'):
        emit(SCHEMA,tmp_path/'out',langs=['go'],services=[],runtime=True,runtime_bindings={'go':{'source_root':raw,'import_path':'app.local/owner'}})
    assert tree(tmp_path)==before


def test_attributed_go_surface_goldens():
    k=Enum('Choice',text=0,number=1)
    s=schema(k,Content=Msg(kind=F(1,Ref('Choice')),text=F(2,STR,optional=True),number=F(3,INT,optional=True)))
    for enabled in (False,True):
        name='on.go' if enabled else 'off.go'
        assert emit_types(s,validation=enabled,identity='go-oneof-golden')==(EXAMPLE/'goldens'/name).read_text()
    old=(EXAMPLE/'goldens/legacy-api.go').read_text()
    body=old[old.index('type Choice'):]
    assert body in (EXAMPLE/'goldens/off.go').read_text()


def test_malformed_codec_facts_and_unpublished_links_fail_as_configuration(tmp_path):
    emit(SCHEMA,tmp_path,langs=['go'],services=[],runtime=True,validation=True); module(tmp_path)
    app(tmp_path,'''
      mustPanic:=func(f func()){func(){defer func(){if recover()==nil{panic("configuration accepted")}}(); f()}()}
      for _,effective:=range []map[string]any{{},{"max_depth":true,"max_encoded_len":nil},{"max_depth":int64(129),"max_encoded_len":nil},{"max_depth":int64(32),"max_encoded_len":nil,"future":int64(1)}}{
        mustPanic(func(){r.NewMessageDescriptor("M","M",nil,nil,nil,nil,nil,nil,nil,effective,"")})
      }
      d:=r.NewMessageDescriptor("M","M",nil,nil,nil,nil,nil,nil,nil,nil,"")
      type value struct{}; b:=r.NewMessageBinding[value](d,func(*value,int)bool{return false},func(*value,int)(int64,bool){return 0,false},func(*value,int)any{return nil},func(*value,int,r.Traversal,[]r.PathSegment)bool{return true})
      mustPanic(func(){r.ValidateRecord(&value{},b,false)})
      missing:=r.MessageType("Missing",func()r.MessageDescriptor{return nil}); field:=r.NewFieldDescriptor("child","Child",1,missing,"required",false,false,nil)
      parent:=r.NewMessageDescriptor("P","P",[]r.FieldDescriptor{field},nil,nil,nil,nil,nil,nil,nil,"")
      mustPanic(func(){r.NewSchemaDescriptor(3,"P",map[string]r.MessageDescriptor{"P":parent},nil,nil,nil)})
    ''','import r "example.local/app/go"')
    go_run(tmp_path)


@pytest.mark.parametrize('child_fc,parent_fc',[(False,False),(True,True),(False,True),(True,False)])
def test_actual_external_forward_compat_codec_facts(tmp_path,package,child_fc,parent_fc):
    child=schema(Child=Msg(value=F(1,INT)))
    parent=schema(Child=Msg(value=F(1,INT)),Parent=Msg(child=F(1,Ref('Child'))))
    module(tmp_path,'require foundation.local/runtime v0.0.0\nreplace foundation.local/runtime => '+package.as_posix()+'\n')
    config={'go':{'import_path':'foundation.local/runtime','artifact':str(package)}}
    emit(child,tmp_path/'child',langs=['go'],services=[],runtime_mode='package',forward_compat=child_fc,runtime_bindings=config)
    go_run(tmp_path,command=['test','./child/go'])
    before=tree(tmp_path/'child')
    emit(parent,tmp_path/'parent',langs=['go'],services=[],runtime_mode='package',forward_compat=parent_fc,validation=True,runtime_bindings=config,go_external_types={'Child':ext('Child','example.local/app/child/go')})
    assert tree(tmp_path/'child')==before
    app(tmp_path,'v:=p.Parent{Child:p.Child{Value:0}}; if !v.IsValid(){panic("unconstrained child")}','import p "example.local/app/parent/go"')
    result=go_run(tmp_path,ok=child_fc==parent_fc)
    if child_fc!=parent_fc:
        assert result.returncode and 'Go imported message facts mismatch; regenerate/rebind child' in result.stderr


def test_supplementary_unicode_native_names_and_original_report_paths(tmp_path):
    k=Enum('Choice',a=0)
    s=schema(k,**{'𐐀Record':Msg(tag=F(1,OneOf(k)),**{'𐐨value':F(2,STR,Case(tag=k.a))})})
    emit(s,tmp_path,langs=['go'],services=[],runtime=True,validation=True,schema_identity='schema😀')
    module(tmp_path)
    app(tmp_path,'v:=a.𐐀Record{Tag:a.ChoiceA}; r:=v.Validate(); name,_:=r.Issues()[0].Path()[0].FieldName(); if name!="𐐨value" || v.Descriptor().QualifiedName()!="schema😀.𐐀Record" {panic("Unicode facts")}; text:="";v.𐐀value=&text;if !v.IsValid(){panic("repair")}', 'import a "example.local/app/go"')
    go_run(tmp_path)
