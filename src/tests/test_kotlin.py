"""Kotlin generator: mutable `data class`es + `enum class`es + CBOR codec, with
forward-compat residual. (kotlinc compile/run parity verified out-of-band.)"""

import os
import shutil
import subprocess
from pathlib import Path

import pytest

from taut.corpus.build import IR_PATH
from taut.gen import kotlin
from taut.ir.dsl import FLOAT, INT, F, List, Map, Msg, schema as mk
from taut.ir.load import load_schema

RAZEL = load_schema(IR_PATH.parent / "razel.taut.py")
ROOT = Path(__file__).resolve().parents[2]


def _java_candidates(kotlinc):
    seen = set()

    def add(path):
        if path is None:
            return
        p = Path(path)
        key = os.fspath(p)
        if key not in seen:
            seen.add(key)
            yield p

    java_home = os.environ.get("JAVA_HOME")
    if java_home:
        yield from add(Path(java_home) / "bin" / "java")

    for parent in Path(kotlinc).resolve().parents:
        for rel in (
            Path("jbr/Contents/Home/bin/java"),
            Path("jbr/bin/java"),
            Path("jdk/Contents/Home/bin/java"),
            Path("jdk/bin/java"),
        ):
            yield from add(parent / rel)

    yield from add(shutil.which("java"))


def _find_java(kotlinc):
    attempted = []
    for java in _java_candidates(kotlinc):
        if not java.is_file():
            attempted.append(f"{java} (missing)")
            continue
        try:
            subprocess.run(
                [str(java), "-version"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
            )
        except (OSError, subprocess.CalledProcessError) as exc:
            attempted.append(f"{java} ({exc})")
            continue
        return str(java)
    tried = "; ".join(attempted) if attempted else "no candidates"
    pytest.skip(f"no usable JVM found for Kotlin parity harness: {tried}")


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


def test_float_scalar_codegen_shape():
    s = kotlin.emit_types(mk(Msg("M",
                                 F("x", 1, FLOAT),
                                 F("maybe", 2, FLOAT, optional=True),
                                 F("xs", 3, List(FLOAT)),
                                 F("by_id", 4, Map(INT, FLOAT)))))
    assert "var x: Double," in s
    assert "var maybe: Double? = null," in s
    assert "1L to Cbor.float(x)" in s
    assert "2L to (maybe?.let { Cbor.float(it) } ?: Cbor.nul)" in s
    assert "x = c.get(1).floatVal" in s
    assert "maybe = c.get(2).let { if (it.isNull) null else it.floatVal }" in s
    assert "xs = c.get(3).arrVal.map { it.floatVal }" in s
    assert "it.get(1).intVal to it.get(2).floatVal" in s


def test_kotlin_float_parity_harness_if_kotlinc(tmp_path):
    kotlinc = shutil.which("kotlinc")
    if kotlinc is None:
        pytest.skip("kotlinc not installed")
    java = _find_java(kotlinc)
    jar = tmp_path / "kotlin-float-parity.jar"
    subprocess.run(
        [
            kotlinc,
            str(ROOT / "src/taut/gen/runtime/cbor.kt"),
            str(ROOT / "src/tests/kotlin_float_parity.kt"),
            "-include-runtime",
            "-d",
            str(jar),
        ],
        check=True,
        cwd=ROOT,
    )
    subprocess.run([java, "-jar", str(jar)], check=True, cwd=ROOT)
