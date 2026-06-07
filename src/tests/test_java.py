"""Java generator: plain classes + enums (with wire value) + CBOR codec, mutable
fields, forward-compat residual. (javac compile/run parity verified out-of-band.)"""

from taut.corpus.build import IR_PATH
from taut.gen import java
from taut.ir.load import load_schema

RAZEL = load_schema(IR_PATH.parent / "razel.taut.py")


def test_emits_classes_enums_and_codec():
    s = java.emit_types(RAZEL)
    assert "package taut;" in s
    assert "class BuildResult {" in s
    assert "enum BuildStatus {" in s
    assert "BUILT(1)" in s
    assert "Cbor toCbor() {" in s
    assert "static BuildResult fromCbor(Cbor c) {" in s


def test_primitive_vs_optional_boxed():
    s = java.emit_types(RAZEL)
    assert "public long recomputes;" in s   # non-optional int -> primitive long
    assert "public String message;" in s    # optional str -> nullable reference


def test_forward_compat_residual():
    s = java.emit_types(RAZEL, forward_compat=True)
    assert "public java.util.List<KV> wireResidual" in s
    assert "wireResidual" not in java.emit_types(RAZEL)  # off by default
