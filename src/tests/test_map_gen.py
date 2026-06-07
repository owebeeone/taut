"""Each generator emits map<K,V>: a native map type + codec. Compile/run parity
is verified out-of-band per language; this is the codegen-shape contract."""

from taut.gen import scaffold
from taut.ir.dsl import INT, STR, F, Map, Msg, schema as mk

S = mk(Msg("Cfg", F("labels", 1, Map(STR, INT))))
PLAIN = mk(Msg("Plain", F("x", 1, INT)))


def test_each_generator_emits_a_native_map_type():
    assert "BTreeMap<String, i64>" in scaffold.rust_api(S)
    assert "std::map<std::string_view, long long>" in scaffold.cpp_api(S)
    assert "[String: Int64]" in scaffold.swift_api(S)
    assert "map[string]int64" in scaffold.go_api(S)
    assert "Map<String, Long>" in scaffold.kotlin_api(S)
    assert "java.util.Map<String, Long>" in scaffold.java_api(S)
    assert "dict[str, int]" in scaffold.python_api(S)
    assert "Record<string, number>" in scaffold.ts_api(S)
    assert "new Map(" in scaffold.js_api(S)


def test_go_imports_sort_only_for_maps():
    assert 'import "sort"' in scaffold.go_api(S)
    assert 'import "sort"' not in scaffold.go_api(PLAIN)


def test_cpp_includes_map_header_only_when_needed():
    assert "#include <map>" in scaffold.cpp_api(S)
    assert "#include <map>" not in scaffold.cpp_api(PLAIN)
