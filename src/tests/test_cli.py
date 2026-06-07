"""The `tautc` codegen CLI: generate native types + codec (and client/server)
from an IR, the way a build script would."""

from taut import cli
from taut.corpus.build import IR_PATH


def test_gen_all_languages(tmp_path):
    rc = cli.main(["gen", str(IR_PATH), "-o", str(tmp_path)])
    assert rc == 0
    # api (types + codec) per language
    assert "class PeerPresence:" in (tmp_path / "python" / "api.py").read_text()
    assert "pub struct PeerPresence" in (tmp_path / "rust" / "api.rs").read_text()
    assert "struct PeerPresence" in (tmp_path / "cpp" / "api.hpp").read_text()
    assert "export interface PeerPresence" in (tmp_path / "typescript" / "api.ts").read_text()
    # both services in the IR get client/server (suffixed, since >1 service)
    assert (tmp_path / "python" / "client_GripLab.py").exists()
    assert (tmp_path / "rust" / "server_Collab.rs").exists()


def test_gen_api_only_subset(tmp_path):
    rc = cli.main(["gen", str(IR_PATH), "-o", str(tmp_path), "--lang", "rust", "--api-only"])
    assert rc == 0
    assert (tmp_path / "rust" / "api.rs").exists()
    # api-only: no client/server, no other languages
    assert not list(tmp_path.glob("rust/client*"))
    assert not (tmp_path / "python").exists()
    assert not (tmp_path / "cpp").exists()


def test_gen_single_service_unsuffixed(tmp_path):
    rc = cli.main(["gen", str(IR_PATH), "-o", str(tmp_path), "-l", "python", "-s", "GripLab"])
    assert rc == 0
    # exactly one service => plain client.py / server.py (no suffix)
    assert (tmp_path / "python" / "client.py").exists()
    assert (tmp_path / "python" / "server.py").exists()


def test_unknown_lang_errors(tmp_path):
    import pytest

    with pytest.raises(ValueError):
        cli.main(["gen", str(IR_PATH), "-o", str(tmp_path), "--lang", "cobol"])
