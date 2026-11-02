"""Each generator emits map<K,V>: a native map type + codec. Compile/run parity
is verified out-of-band per language; this is the codegen-shape contract."""

import os
import re
import subprocess

from taut.gen import scaffold
from taut.ir.dsl import BOOL, INT, STR, F, Map, Msg, schema as mk

S = mk(Msg("Cfg", F("labels", 1, Map(STR, INT))))
PLAIN = mk(Msg("Plain", F("x", 1, INT)))
OPTIONAL_SCALARS = mk(
    Msg("Opt", F("count", 1, INT, optional=True), F("ready", 2, STR, optional=True))
)
OPTIONAL_BOOL = mk(Msg("Flag", F("enabled", 1, BOOL, optional=True)))


def test_each_generator_emits_a_native_map_type():
    assert "BTreeMap<String, i64>" in scaffold.rust_api(S)
    assert "std::map<std::string_view, long long>" in scaffold.cpp_api(S)
    assert "[String: Int64]" in scaffold.swift_api(S)
    assert "map[string]int64" in scaffold.go_api(S)
    assert "Map<String, Long>" in scaffold.kotlin_api(S)
    assert "java.util.Map<String, Long>" in scaffold.java_api(S)
    assert "dict[str, int]" in scaffold.python_api(S)
    assert "Map<string, bigint>" in scaffold.ts_api(S)
    assert "new Map(" in scaffold.js_api(S)


def test_go_imports_sort_only_for_maps(tmp_path):
    def imports(source):
        # Covers both single and grouped imports, retaining the actual binding.
        return {path: alias or path.rsplit('/',1)[-1] for alias,path in
                re.findall(r'^\s*(?:import\s+)?(?:([A-Za-z_]\w*)\s+)?"([^"]+)"\s*$',source,re.M)}
    mapped,plain=scaffold.go_api(S),scaffold.go_api(PLAIN)
    binding=imports(mapped)['sort']
    assert binding+'.Slice(' in mapped
    assert 'sort' not in imports(plain) and binding+'.Slice(' not in plain
    # Check actual dependency use: a missing or unused sorting import must fail
    # native compilation, and map encoding/decoding must retain both entries.
    for name,model,body in (
        ('mapped',S,'v:=a.Cfg{Labels:map[string]int64{"z":2,"a":1}};got,err:=a.TryCfgFromBytes(a.Encode(v.ToCbor()));if err!=nil||len(got.Labels)!=2||got.Labels["a"]!=1||got.Labels["z"]!=2{panic("map roundtrip")}'),
        ('plain',PLAIN,'v:=a.Plain{X:0};got,err:=a.TryPlainFromBytes(a.Encode(v.ToCbor()));if err!=nil||got.X!=0{panic("plain roundtrip")}'),
    ):
        root=tmp_path/name
        scaffold.emit(model,root,langs=['go'],services=[],runtime=True)
        (root/'go.mod').write_text('module mapgen.local/probe\n\ngo 1.20\n')
        (root/'app').mkdir()
        (root/'app/main.go').write_text('package main\nimport a "mapgen.local/probe/go"\nfunc main(){'+body+'}\n')
        env=dict(os.environ,GO111MODULE='on',GOWORK='off',GOPROXY='off',GOSUMDB='off',GOTOOLCHAIN='local')
        result=subprocess.run(['go','run','./app'],cwd=root,env=env,capture_output=True,text=True)
        assert result.returncode==0,result.stdout+result.stderr


def test_cpp_includes_map_header_only_when_needed():
    assert "#include <map>" in scaffold.cpp_api(S)
    assert "#include <map>" not in scaffold.cpp_api(PLAIN)


def test_rust_optional_scalar_fields_encode_values_not_references():
    api = scaffold.rust_api(OPTIONAL_SCALARS) + scaffold.rust_api(OPTIONAL_BOOL)
    assert "Some(v) => Cbor::Int(*v)" in api
    assert "Some(v) => Cbor::Bool(*v)" in api
