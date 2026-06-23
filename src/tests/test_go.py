"""Go generator: native structs + typed-const enums + CBOR codec, forward-compat
residual, PascalCase exported fields. (go-build parity verified out-of-band.)"""

import os
from pathlib import Path
import shutil
import subprocess

import pytest

from taut.corpus.build import IR_PATH
from taut.gen import go
from taut.ir.dsl import FLOAT, INT, F, List, Map, Msg, schema as mk
from taut.ir.load import load_schema

ROOT = Path(__file__).resolve().parents[2]
RAZEL = load_schema(IR_PATH.parent / "razel.taut.py")
FLOAT_SCHEMA = mk(Msg("FloatMsg",
                      F("x", 1, FLOAT),
                      F("xs", 2, List(FLOAT)),
                      F("by_id", 3, Map(INT, FLOAT)),
                      F("maybe", 4, FLOAT, optional=True)))


def test_emits_structs_enums_and_codec():
    s = go.emit_types(RAZEL)
    assert "package taut" in s
    assert "type BuildResult struct {" in s
    assert "type BuildStatus int64" in s
    assert "BuildStatusBuilt BuildStatus = 1" in s
    assert "func (x BuildResult) ToCbor() Cbor {" in s
    assert "func BuildResultFromCbor(c Cbor) BuildResult {" in s


def test_fields_pascalcased_and_optional_is_pointer():
    s = go.emit_types(RAZEL)
    assert "Recomputes int64" in s   # recomputes -> Recomputes (exported)
    assert "Message *string" in s    # optional -> nil-able pointer


def test_forward_compat_adds_residual():
    s = go.emit_types(RAZEL, forward_compat=True)
    assert "WireResidual []KV" in s
    assert "append(m, x.WireResidual...)" in s          # re-emitted (Encode sorts)
    assert "WireResidual" not in go.emit_types(RAZEL)   # off by default


def test_float_scalar_codegen():
    s = go.emit_types(FLOAT_SCHEMA)
    assert "X float64" in s
    assert "Xs []float64" in s
    assert "ById map[int64]float64" in s
    assert "Maybe *float64" in s
    assert "CFloat(x.X)" in s
    assert "a = append(a, CFloat(e))" in s
    assert "V: CFloat(x.ById[k])" in s
    assert "v.X = c.Get(1).Float()" in s
    assert "t := fv.Float(); v.Maybe = &t" in s


def test_go_runtime_float_harness():
    if shutil.which("go") is None:
        pytest.skip("go not installed")

    env = os.environ.copy()
    env["GO111MODULE"] = "off"
    result = subprocess.run(
        ["go", "test", "./src/taut/gen/runtime"],
        cwd=ROOT,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    assert result.returncode == 0, result.stdout
