import json

import pytest

from taut.cli import main
from taut.corpus import parity


def test_parity_artifacts_validate():
    lines = parity.validate_all()
    assert "int vectors: 10" in lines
    assert "malformed vectors: 12" in lines
    assert any(line.startswith("rust: gated") for line in lines)


def test_parity_cli_target(capsys):
    assert main(["parity", "--target", "rust"]) == 0
    out = capsys.readouterr().out
    assert "int vectors: 10" in out
    assert "malformed vectors: 12" in out
    assert "rust: gated" in out


def test_parity_allowlist_accepts_explicit_exception(tmp_path):
    data = json.loads(parity.ALLOWLIST.read_text())
    data["targets"].append(
        {
            "target": "rust",
            "phase": "test",
            "owner": "test",
            "reason": "temporary test exception",
        }
    )
    path = tmp_path / "allowlist.json"
    path.write_text(json.dumps(data))

    statuses = parity.target_statuses(path)
    rust = next(status for status in statuses if status.target == "rust")
    assert rust.status == "allowlisted"
    assert rust.reason == "temporary test exception"


def test_parity_encode_fail_accepts_out_of_range_map_value(tmp_path):
    data = {
        "version": 1,
        "contract": "taut-codec-parity/i64/v0",
        "schema_path": "ir/parity_int.taut.py",
        "vectors": [
            {
                "name": "map-value-overflow",
                "kind": "encode_fail",
                "message": "IntBox",
                "value": {"n": "0", "by_id": [["1", "9223372036854775808"]]},
                "expect": {"tag": "IntOutOfSubset"},
            }
        ],
    }
    path = tmp_path / "int.vectors.json"
    path.write_text(json.dumps(data))
    assert parity.validate_int_vectors(path) == 1


def test_parity_rejects_duplicate_allowlist_target(tmp_path):
    data = json.loads(parity.ALLOWLIST.read_text())
    row = {
        "target": "rust",
        "phase": "test",
        "owner": "test",
        "reason": "temporary test exception",
    }
    data["targets"].extend([row, dict(row)])
    path = tmp_path / "allowlist.json"
    path.write_text(json.dumps(data))

    with pytest.raises(parity.ParityValidationError, match="duplicate target rust"):
        parity.target_statuses(path)
