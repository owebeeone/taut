"""Kotlin generator: mutable `data class`es + `enum class`es + CBOR codec, with
forward-compat residual. (kotlinc compile/run parity verified out-of-band.)"""

from taut.corpus.build import IR_PATH
from taut.gen import kotlin
from taut.ir.load import load_schema

RAZEL = load_schema(IR_PATH.parent / "razel.taut.py")


def test_emits_data_classes_enums_and_codec():
    s = kotlin.emit_types(RAZEL)
    assert "package taut" in s
    assert "data class BuildResult(" in s
    assert "enum class BuildStatus(val wire: Long) {" in s
    assert "fun toCbor(): Cbor" in s
    assert "fun fromCbor(c: Cbor): BuildResult" in s


def test_mutable_var_and_nullable_optional():
    s = kotlin.emit_types(RAZEL)
    assert "var recomputes: Long" in s          # mutable var (per the v0.3 decision)
    assert "var message: String? = null" in s   # optional -> nullable


def test_forward_compat_adds_residual():
    s = kotlin.emit_types(RAZEL, forward_compat=True)
    assert "var wireResidual: List<Pair<Long, Cbor>>" in s
    assert "+ wireResidual" in s                            # re-emitted (encode sorts)
    assert "wireResidual" not in kotlin.emit_types(RAZEL)   # off by default
