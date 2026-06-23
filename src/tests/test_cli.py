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
    cli.main(["gen", str(IR_PATH), "-o", str(tmp_path), "--lang", "typescript,rust,cpp", "--api-only"])
    assert not (tmp_path / "typescript" / "cbor.ts").exists()
    assert not (tmp_path / "rust" / "cbor.rs").exists()
    assert not (tmp_path / "cpp" / "taut" / "cbor.hpp").exists()


def test_with_runtime_emits_self_contained_compiled_targets(tmp_path):
    cli.main(["gen", str(IR_PATH), "-o", str(tmp_path), "--lang", "typescript,rust,cpp",
              "-s", "GripLab", "--with-runtime"])
    ts_cbor = tmp_path / "typescript" / "cbor.ts"
    ts_codec = tmp_path / "typescript" / "codec.ts"
    ts_schema = tmp_path / "typescript" / "schema.ts"
    ts_client = tmp_path / "typescript" / "taut_client.ts"
    cbor_rs = tmp_path / "rust" / "cbor.rs"
    cbor_hpp = tmp_path / "cpp" / "taut" / "cbor.hpp"
    assert ts_cbor.exists() and ts_codec.exists() and ts_schema.exists() and ts_client.exists()
    assert cbor_rs.exists() and cbor_hpp.exists()
    # the emitted runtime must satisfy what the generated code imports
    assert "export class CborFloat" in ts_cbor.read_text()
    assert 'from "./taut_client.ts"' in (tmp_path / "typescript" / "client.ts").read_text()
    assert "pub enum Cbor" in cbor_rs.read_text()
    assert "use crate::cbor::Cbor;" in (tmp_path / "rust" / "api.rs").read_text()
    assert "namespace taut" in cbor_hpp.read_text()
    assert '#include "taut/cbor.hpp"' in (tmp_path / "cpp" / "api.hpp").read_text()


def test_with_runtime_skips_languages_without_one(tmp_path):
    # Python uses the in-package Python runtime directly; nothing to emit, no error.
    cli.main(["gen", str(IR_PATH), "-o", str(tmp_path), "--lang", "python", "--with-runtime"])
    assert (tmp_path / "python" / "api.py").exists()
    assert not list((tmp_path / "python").glob("cbor*"))


def test_corpus_emits_golden_and_rust_harness(tmp_path):
    rc = cli.main(["corpus", str(IR_PATH), "-o", str(tmp_path), "--lang", "rust"])
    assert rc == 0
    assert (tmp_path / "golden.json").exists()
    assert "corpus_byte_parity" in (tmp_path / "rust" / "vectors.rs").read_text()


def test_generated_rust_files_have_single_terminal_newline(tmp_path):
    cli.main(["gen", str(IR_PATH), "-o", str(tmp_path / "gen"), "--lang", "rust", "--api-only"])
    cli.main(["corpus", str(IR_PATH), "-o", str(tmp_path / "corpus"), "--lang", "rust"])

    for path in [
        tmp_path / "gen" / "rust" / "api.rs",
        tmp_path / "corpus" / "rust" / "vectors.rs",
    ]:
        text = path.read_text()
        assert text.endswith("\n")
        assert not text.endswith("\n\n")


def test_corpus_check_passes_then_detects_drift(tmp_path):
    cli.main(["corpus", str(IR_PATH), "-o", str(tmp_path)])
    # fresh output is up to date
    assert cli.main(["corpus", str(IR_PATH), "-o", str(tmp_path), "--check"]) == 0
    # tamper -> drift gate fails (exit 2)
    (tmp_path / "golden.json").write_text("{}\n")
    assert cli.main(["corpus", str(IR_PATH), "-o", str(tmp_path), "--check"]) == 2


def test_json_cbor_roundtrip_via_files(tmp_path):
    from taut.ir.load import load_schema
    from taut.wire import codec
    razel = str(IR_PATH.parent / "razel.taut.py")
    s = load_schema(IR_PATH.parent / "razel.taut.py")
    cbor = tmp_path / "v.cbor"
    cbor.write_bytes(codec.encode(s, "BuildResult",
                                  {"target": "//x", "status": "built", "recomputes": 7,
                                   "outputs": [{"path": "o", "digest": b"\xde\xad"}], "message": None}))
    js = tmp_path / "v.json"
    out_cbor = tmp_path / "v2.cbor"
    # CBOR -> JSON
    assert cli.main(["json", razel, "-m", "BuildResult", "-i", str(cbor), "-o", str(js)]) == 0
    text = js.read_text()
    assert '"recomputes": "7"' in text or '"recomputes":"7"' in text   # int64 -> string
    # JSON -> CBOR, byte-identical to the original
    assert cli.main(["json", razel, "-m", "BuildResult", "--from-json", "-i", str(js), "-o", str(out_cbor)]) == 0
    assert out_cbor.read_bytes() == cbor.read_bytes()
