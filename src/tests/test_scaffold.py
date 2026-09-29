"""The scaffold generators emit per-language API types + client/server stubs."""

import pytest

from taut.corpus.build import IR_PATH
from taut.gen import scaffold
from taut.ir.dsl import INT, Enum, F, List, Msg, Ref, option, schema
from taut.ir.load import load_schema
from taut.ir.model import Schema
from taut.ir.options import OPTIONS, OptionDef

S = load_schema(IR_PATH)


def test_api_types_emitted_per_language():
    assert "class PeerPresence:" in scaffold.python_api(S)
    assert "export interface PeerPresence" in scaffold.ts_api(S)
    assert "pub struct PeerPresence" in scaffold.rust_api(S)
    assert "struct PeerPresence" in scaffold.cpp_api(S)


def test_client_and_server_cover_methods():
    svc = S.services["GripLab"]
    client = scaffold.python_client(S, svc)
    server = scaffold.python_server(S, svc)
    assert "class GripLabClient" in client
    assert "async def cmd_run(self, argv" in client          # cmd.run -> cmd_run
    assert "def presence_subscribe(self)" in client          # streaming method
    assert "class GripLabHandlers(Protocol)" in server
    assert '"cmd.run": handlers.cmd_run' in server
    assert "transport.register_method(m, bind[m.name])" in server


def test_emit_all_writes_the_tree(tmp_path):
    written = scaffold.emit_all(S, "GripLab", tmp_path)
    rel = {p.relative_to(tmp_path).as_posix() for p in written}
    assert "python/api.py" in rel and "rust/client.rs" in rel and "cpp/server.hpp" in rel
    assert "python/__init__.py" in rel


# --- the generator refusal (TautOptions.md OPT-F2) ------------------------------------------

def test_every_target_implements_both_wire_options():
    assert set(scaffold._IMPLEMENTED_OPTIONS) == set(scaffold._LANGS)
    wire = {name for name, defn in OPTIONS.items() if defn.klass == "wire"}
    assert wire == {"max_depth", "max_encoded_len"}
    for lang, implemented in scaffold._IMPLEMENTED_OPTIONS.items():
        assert implemented == wire, lang


def _tree():
    return schema(Msg("Tree", option.max_depth(64), F("children", 1, List(Ref("Tree")))))


def test_emit_refuses_a_target_lacking_a_declared_option_before_writing(tmp_path, monkeypatch):
    monkeypatch.setitem(scaffold._IMPLEMENTED_OPTIONS, "go", frozenset({"max_encoded_len"}))
    with pytest.raises(ValueError, match="go lacks max_depth"):
        scaffold.emit(_tree(), tmp_path, langs=["rust", "go"], services=[])
    assert list(tmp_path.iterdir()) == []   # nothing written, not even rust's
    written = scaffold.emit(_tree(), tmp_path, langs=["rust"], services=[])   # rust has it
    assert [p.relative_to(tmp_path).as_posix() for p in written] == ["rust/api.rs"]


@pytest.mark.parametrize("declared", [
    schema(option.max_depth(16), Msg("M", F("x", 1, INT))),
    schema(Msg("M", option.max_depth(16), F("x", 1, INT))),
    schema(Msg("M", F("x", 1, INT, option.max_depth(16)))),
    schema(Enum("E", option.max_depth(16), a=0), Msg("M", F("x", 1, INT))),
], ids=["file", "message", "field", "enum"])
def test_a_declaration_at_any_level_is_refused(tmp_path, monkeypatch, declared):
    monkeypatch.setitem(scaffold._IMPLEMENTED_OPTIONS, "go", frozenset())
    with pytest.raises(ValueError, match="go lacks max_depth"):
        scaffold.emit(declared, tmp_path, langs=["go"], services=[])
    assert list(tmp_path.iterdir()) == []


def test_declared_means_declared_not_default(tmp_path, monkeypatch):
    monkeypatch.setitem(scaffold._IMPLEMENTED_OPTIONS, "go", frozenset())
    plain = schema(Msg("M", F("x", 1, INT)))   # max_depth resolves to 32, but none is declared
    written = scaffold.emit(plain, tmp_path, langs=["go"], services=[])
    assert [p.relative_to(tmp_path).as_posix() for p in written] == ["go/api.go"]


def test_only_an_option_that_binds_the_target_is_refused(tmp_path, monkeypatch):
    # none of these classes has an option yet (OPT-D2, question 7): registered for the test
    for defn in (
        OptionDef("doc", str, frozenset({"message"}), default="", klass="metadata", inherits=()),
        OptionDef("rust_only", bool, frozenset({"message"}), default=False, klass="codegen",
                  inherits=("message",), targets=frozenset({"rust"})),
        OptionDef("merge_like", str, frozenset({"message"}), default="lww", klass="semantic",
                  inherits=("message",)),
    ):
        monkeypatch.setitem(OPTIONS, defn.name, defn)
    ignored = schema(Msg("M", option.doc("text"), option.rust_only(True), F("x", 1, INT)))
    assert scaffold.emit(ignored, tmp_path / "go", langs=["go"], services=[])
    with pytest.raises(ValueError, match="rust lacks rust_only"):
        scaffold.emit(ignored, tmp_path / "rust", langs=["rust"], services=[])
    semantic = schema(Msg("M", option.merge_like("counter"), F("x", 1, INT)))
    with pytest.raises(ValueError, match="go lacks merge_like"):
        scaffold.emit(semantic, tmp_path / "semantic", langs=["go"], services=[])


def test_an_unregistered_option_is_refused_for_every_target(tmp_path):
    unknown = Schema(enums={}, messages={}, options={"nope": 1})
    with pytest.raises(ValueError, match="python lacks nope"):
        scaffold.emit(unknown, tmp_path, langs=["python"], services=[])
