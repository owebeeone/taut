"""TypeScript runtime-resource smoke tests."""

import shutil
import subprocess

import pytest

from taut import cli
from taut.corpus.build import IR_PATH


def test_typescript_runtime_emits_and_runs_if_node(tmp_path):
    node = shutil.which("node")
    if not node:
        pytest.skip("node not available")

    assert cli.main([
        "gen",
        str(IR_PATH),
        "-o",
        str(tmp_path),
        "--lang",
        "typescript",
        "--api-only",
        "--with-runtime",
    ]) == 0

    ts_dir = tmp_path / "typescript"
    smoke = ts_dir / "runtime_smoke.test.ts"
    smoke.write_text(
        """
import test from "node:test";
import assert from "node:assert/strict";
import { CborFloat, decode, encode } from "./cbor.ts";

test("vendored TypeScript runtime encodes deterministic CBOR", () => {
  const input = new Map([[3, new CborFloat(1.5)], [1, "ok"]]);
  const encoded = encode(input);
  assert.equal(Buffer.from(encoded).toString("hex"), "a201626f6b03f93e00");

  const decoded = decode(encoded);
  assert.ok(decoded instanceof Map);
  assert.equal(decoded.get(1), "ok");
  assert.ok(decoded.get(3) instanceof CborFloat);
  assert.equal(decoded.get(3).value, 1.5);
});
""".lstrip()
    )

    subprocess.run(
        [node, "--experimental-strip-types", "--test", str(smoke.name)],
        cwd=ts_dir,
        check=True,
        text=True,
        capture_output=True,
    )
