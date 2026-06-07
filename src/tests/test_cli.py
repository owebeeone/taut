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


def test_runtime_off_by_default(tmp_path):
    cli.main(["gen", str(IR_PATH), "-o", str(tmp_path), "--lang", "rust,cpp", "--api-only"])
    assert not (tmp_path / "rust" / "cbor.rs").exists()
    assert not (tmp_path / "cpp" / "taut" / "cbor.hpp").exists()


def test_with_runtime_emits_self_contained_compiled_targets(tmp_path):
    cli.main(["gen", str(IR_PATH), "-o", str(tmp_path), "--lang", "rust,cpp",
              "--api-only", "--with-runtime"])
    cbor_rs = tmp_path / "rust" / "cbor.rs"
    cbor_hpp = tmp_path / "cpp" / "taut" / "cbor.hpp"
    assert cbor_rs.exists() and cbor_hpp.exists()
    # the emitted runtime must satisfy what the generated code imports
    assert "pub enum Cbor" in cbor_rs.read_text()
    assert "use crate::cbor::Cbor;" in (tmp_path / "rust" / "api.rs").read_text()
    assert "namespace taut" in cbor_hpp.read_text()
    assert '#include "taut/cbor.hpp"' in (tmp_path / "cpp" / "api.hpp").read_text()


def test_with_runtime_skips_languages_without_one(tmp_path):
    # Python/TS use the IR-driven runtime codec; nothing to emit, no error.
    cli.main(["gen", str(IR_PATH), "-o", str(tmp_path), "--lang", "python", "--with-runtime"])
    assert (tmp_path / "python" / "api.py").exists()
    assert not list((tmp_path / "python").glob("cbor*"))
