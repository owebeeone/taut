"""JS generator: ES classes + frozen enum objects + CBOR codec (CommonJS),
forward-compat residual."""

from pathlib import Path
import shutil
import subprocess

import pytest
from taut.corpus.build import IR_PATH
from taut.gen import js
from taut.ir.dsl import FLOAT, INT, F, List, Map, Msg, schema as mk
from taut.ir.load import load_schema

RAZEL = load_schema(IR_PATH.parent / "razel.taut.py")
FLOATY = mk(Msg("Floaty",
                F("x", 1, FLOAT),
                F("xs", 2, List(FLOAT)),
                F("by_id", 3, Map(INT, FLOAT))))


def test_emits_classes_enums_and_codec():
    s = js.emit_types(RAZEL)
    assert 'require("./cbor.js")' in s
    assert "class BuildResult {" in s
    assert "const BuildStatus = Object.freeze({" in s
    assert "toCbor() {" in s
    assert "static fromCbor(c) {" in s
    assert "module.exports = {" in s


def test_optional_is_nullable():
    assert "this.message != null ?" in js.emit_types(RAZEL)


def test_forward_compat_residual():
    s = js.emit_types(RAZEL, forward_compat=True)
    assert "this.wireResidual" in s
    assert "wireResidual" not in js.emit_types(RAZEL)  # off by default


def test_float_scalar_shape():
    s = js.emit_types(FLOATY)
    assert "CFloat" in s
    assert "[1, CFloat(this.x)]" in s
    assert "CArr(this.xs.map((e) => CFloat(e)))" in s
    assert "CMap([[1, CInt(k)], [2, CFloat(v)]])" in s
    assert "v.x = cget(c, 1).f;" in s
    assert "v.xs = cget(c, 2).arr.map((e) => e.f);" in s


def test_js_float_runtime_parity():
    node = shutil.which("node")
    if node is None:
        pytest.skip("node is not installed")

    script = Path(__file__).with_name("js_float_parity.js")
    subprocess.run([node, str(script)], check=True)
