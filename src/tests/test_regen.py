"""DoD gate: regeneration reproduces the committed in-repo corpus artifacts."""

import json

from taut.corpus.build import GOLDEN_PATH, IR_JSON_PATH, IR_PATH, generate_golden
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
