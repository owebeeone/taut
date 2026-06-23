"""Java generator: plain classes + enums (with wire value) + CBOR codec, mutable
fields, forward-compat residual. Float parity uses $JAVA_HOME/bin/javac and
$JAVA_HOME/bin/java out of band; on this machine use Android Studio's JBR because
PATH java/javac shims may be broken."""

from taut.corpus.build import IR_PATH
from taut.gen import java
from taut.ir.dsl import FLOAT, INT, F, List as TList, Map, Msg, schema as mk
from taut.ir.load import load_schema

RAZEL = load_schema(IR_PATH.parent / "razel.taut.py")
FLOATY = mk(Msg("Floaty",
                F("x", 1, FLOAT),
                F("maybe", 2, FLOAT, optional=True),
                F("xs", 3, TList(FLOAT)),
                F("by_id", 4, Map(INT, FLOAT))))


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


def test_float_scalar_codegen_shape():
    s = java.emit_types(FLOATY)
    assert "public double x;" in s
    assert "public Double maybe;" in s
    assert "public java.util.List<Double> xs;" in s
    assert "public java.util.Map<Long, Double> by_id;" in s
    assert "m.add(new KV(1, Cbor.float_(x)));" in s
    assert "m.add(new KV(2, maybe != null ? Cbor.float_(maybe) : Cbor.NUL));" in s
    assert "Cbor.arr(xs.stream().map(e -> Cbor.float_(e)).toList())" in s
    assert "new KV(2, Cbor.float_(e.getValue()))" in s
    assert "v.x = c.get(1).d;" in s
    assert "v.maybe = f.isNull() ? null : f.d;" in s
    assert "c.get(3).arr.stream().map(e -> e.d).toList()" in s
    assert "e -> e.get(2).d" in s


def test_forward_compat_residual():
    s = java.emit_types(RAZEL, forward_compat=True)
    assert "public java.util.List<KV> wireResidual" in s
    assert "wireResidual" not in java.emit_types(RAZEL)  # off by default
