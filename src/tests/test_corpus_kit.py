"""The conformance kit: derive a golden corpus from any IR with auto-synthesized
coverage values, and emit a per-language parity harness. Generalizes the GripLab
corpus discipline so consumers don't hand-roll reference values + vectors."""

import shutil
import subprocess
import textwrap

import pytest

from taut import cli
from taut.corpus import kit, synth
from taut.corpus.build import IR_PATH
from taut.ir.load import load_schema
from taut.wire import codec

RAZEL = load_schema(IR_PATH.parent / "razel.taut.py")
GRIPLAB = load_schema(IR_PATH)


def test_synth_is_deterministic():
    assert synth.synth_values(RAZEL) == synth.synth_values(RAZEL)


def test_synth_covers_every_message_and_encodes():
    values = synth.synth_values(RAZEL)
    assert set(values) == set(RAZEL.messages)            # one vector per message
    for name, (msg, val) in values.items():
        # synthesized values are valid: they encode and round-trip through the codec
        assert codec.decode(RAZEL, msg, codec.encode(RAZEL, msg, val)) == val


def test_synth_exercises_the_type_space():
    # BuildResult has an enum, an i64, a list-of-message, and an optional — the value
    # should populate each (coverage, not just shape).
    _, val = synth.synth_values(RAZEL)["BuildResult"]
    assert isinstance(val["recomputes"], int)
    assert val["status"] in RAZEL.enums["BuildStatus"].members
    assert isinstance(val["outputs"], list) and val["outputs"]
    assert isinstance(val["outputs"][0]["digest"], (bytes, bytearray))


def test_build_corpus_matches_canonical_codec():
    values = synth.synth_values(RAZEL)
    corpus = kit.build_corpus(RAZEL, values)
    for name, entry in corpus.items():
        msg, val = values[name]
        assert entry["message"] == msg
        assert bytes.fromhex(entry["cbor"]) == codec.encode(RAZEL, msg, val)


def test_rust_harness_is_self_contained_and_covers_messages():
    corpus = kit.build_corpus(RAZEL, synth.synth_values(RAZEL))
    rs = kit.rust_vectors(RAZEL, corpus)
    assert "pub static VECTORS" in rs
    assert "fn corpus_byte_parity" in rs
    # a reencode arm for each message, using crate-root re-exported types and
    # unwrapping the fallible decode (golden vectors must decode)
    for m in RAZEL.messages:
        assert f'"{m}" => crate::{m}::from_cbor(c).expect("corpus decode: {m}").to_cbor(),' in rs


def test_golden_json_is_stable():
    corpus = kit.build_corpus(GRIPLAB, synth.synth_values(GRIPLAB))
    assert kit.golden_json(corpus) == kit.golden_json(corpus)


def test_generated_rust_corpus_compiles_and_passes_if_rustc(tmp_path):
    """The emitted vectors.rs must compile and run against the same `tautc gen`
    rust output an embedder vendors (api + runtime + crate-root re-exports) —
    the exact `gen` + `corpus` pipeline downstream regen scripts drive."""
    rustc = shutil.which("rustc")
    if rustc is None:
        pytest.skip("rustc not available")

    ir = (IR_PATH.parent / "razel.taut.py").as_posix()
    gen_dir = tmp_path / "gen"
    corpus_dir = tmp_path / "corpus"
    assert cli.main(["gen", ir, "-o", str(gen_dir), "-l", "rust",
                     "--api-only", "--with-runtime"]) == 0
    assert cli.main(["corpus", ir, "-o", str(corpus_dir), "-l", "rust"]) == 0

    # The crate shape vectors.rs documents: generated types plus
    # `Cbor`/`encode`/`decode` re-exported at the crate root.
    lib_rs = tmp_path / "lib.rs"
    lib_rs.write_text(textwrap.dedent(f"""
        // The vendored runtime imports through `alloc::` paths; a std embedder
        // links `alloc` explicitly.
        extern crate alloc;

        #[path = "{(gen_dir / 'rust' / 'cbor.rs').as_posix()}"]
        pub mod cbor;
        #[path = "{(gen_dir / 'rust' / 'api.rs').as_posix()}"]
        mod api;
        pub use api::*;
        pub use cbor::{{Cbor, decode, encode}};
        #[path = "{(corpus_dir / 'rust' / 'vectors.rs').as_posix()}"]
        mod vectors;
    """))
    bin_path = tmp_path / "corpus_parity"
    subprocess.run(
        [rustc, "--edition", "2021", "--test", str(lib_rs), "-o", str(bin_path)],
        check=True,
    )
    subprocess.run([str(bin_path)], check=True)
