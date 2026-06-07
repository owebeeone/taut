"""DoD gate: regeneration reproduces the committed tree. The authored IR is the
only source; every generated artifact must byte-match fresh generator output, so
hand-edits to generated files (or drift between repos) fail CI."""

import json

import pytest

from taut.corpus.build import GOLDEN_PATH, IR_JSON_PATH, IR_PATH, generate_golden, reference_values
from taut.gen import cpp as cpp_gen
from taut.gen import rust as rust_gen
from taut.ir.export import schema_json
from taut.ir.load import load_schema


def test_ir_json_matches_committed():
    schema = load_schema(IR_PATH)
    expected = json.dumps(schema_json(schema), indent=2) + "\n"
    assert IR_JSON_PATH.read_text() == expected, "taut/corpus/griplab.ir.json is stale — re-run build"


def test_golden_matches_committed():
    schema = load_schema(IR_PATH)
    expected = json.dumps(generate_golden(schema), indent=2, sort_keys=True) + "\n"
    assert GOLDEN_PATH.read_text() == expected, "griplab.golden.json is stale — re-run build"


def test_generated_rust_matches_committed():
    if not rust_gen.OUT_PATH.exists():
        pytest.skip("trial/rs not a sibling checkout")
    schema = load_schema(IR_PATH)
    golden = json.loads(GOLDEN_PATH.read_text())
    assert rust_gen.OUT_PATH.read_text() == rust_gen._emit(schema, golden), "generated.rs is stale"


def test_generated_cpp_matches_committed():
    if not cpp_gen.CORPUS_PATH.exists():
        pytest.skip("trial/cpp not a sibling checkout")
    schema = load_schema(IR_PATH)
    refs = reference_values()
    assert cpp_gen.TYPES_PATH.read_text() == cpp_gen._emit_types(schema), "types.hpp is stale"
    assert cpp_gen.CORPUS_PATH.read_text() == cpp_gen._emit_corpus(schema, refs), "corpus.hpp is stale"
