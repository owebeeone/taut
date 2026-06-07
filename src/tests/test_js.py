"""JS generator: ES classes + frozen enum objects + CBOR codec (CommonJS),
forward-compat residual. (node load/round-trip parity verified out-of-band.)"""

from taut.corpus.build import IR_PATH
from taut.gen import js
from taut.ir.load import load_schema

RAZEL = load_schema(IR_PATH.parent / "razel.taut.py")


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
