"""The scaffold generators emit per-language API types + client/server stubs."""

from prism.corpus.build import IR_PATH
from prism.gen import scaffold
from prism.ir.load import load_schema

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
