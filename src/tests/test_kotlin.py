"""Kotlin generator: mutable `data class`es + `enum class`es + CBOR codec, with
forward-compat residual. (kotlinc compile/run parity verified out-of-band.)"""

import json
import os
import random
import shutil
import subprocess
from pathlib import Path

import pytest

from taut import ext
from taut.corpus.build import IR_PATH
from taut.corpus import resext_build as rb
from taut.gen import kotlin
from taut.gen import scaffold
from taut.ir.dsl import FLOAT, INT, STR, F, List, Map, Msg, extension, schema as mk
from taut.ir.load import load_schema
from taut.ir.shapes import BAND_START
from taut.wire import cbor, codec

RAZEL = load_schema(IR_PATH.parent / "razel.taut.py")
RESEXT = load_schema(rb.IR_PATH)
ROOT = Path(__file__).resolve().parents[2]
ANDROID_STUDIO_KOTLINC = Path(
    "/Applications/Android Studio.app/Contents/plugins/Kotlin/kotlinc/bin/kotlinc"
)
RESEXT_TAG = BAND_START + 1
RESEXT_FUZZ_SEED = 0x5EED55_04


def _kotlinc_candidates():
    seen = set()

    def add(path):
        if not path:
            return
        p = Path(path)
        if p.is_dir():
            p = p / "bin" / "kotlinc"
        key = os.fspath(p)
        if key not in seen:
            seen.add(key)
            yield p

    yield from add(os.environ.get("KOTLINC"))
    yield from add(ANDROID_STUDIO_KOTLINC)
    yield from add(shutil.which("kotlinc"))


def _find_kotlinc():
    attempted = []
    for kotlinc in _kotlinc_candidates():
        if not kotlinc.is_file():
            attempted.append(f"{kotlinc} (missing)")
            continue
        try:
            subprocess.run(
                [str(kotlinc), "-version"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
            )
        except (OSError, subprocess.CalledProcessError) as exc:
            attempted.append(f"{kotlinc} ({exc})")
            continue
        return str(kotlinc)
    tried = "; ".join(attempted) if attempted else "no candidates"
    pytest.skip(f"no usable kotlinc found; searched KOTLINC, Android Studio, PATH: {tried}")


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


def _java_env(java):
    env = os.environ.copy()
    java_path = Path(java).resolve()
    if java_path.name == "java" and java_path.parent.name == "bin":
        java_home = java_path.parent.parent
        env["JAVA_HOME"] = os.fspath(java_home)
        env["PATH"] = os.fspath(java_path.parent) + os.pathsep + env.get("PATH", "")
    return env


def _kt_string(s):
    return json.dumps(s)


def _kt_nullable_string(s):
    return "null" if s is None else _kt_string(s)


def _random_cbor_value(rng, depth=0):
    choices = ["int", "text", "bytes", "bool", "null"]
    if depth < 2:
        choices.append("array")
    kind = rng.choice(choices)
    if kind == "int":
        return rng.randint(-100_000, 100_000)
    if kind == "text":
        return f"s{rng.randrange(100_000)}"
    if kind == "bytes":
        return bytes(rng.randrange(256) for _ in range(rng.randrange(0, 5)))
    if kind == "bool":
        return bool(rng.randrange(2))
    if kind == "null":
        return None
    return [_random_cbor_value(rng, depth + 1) for _ in range(rng.randrange(0, 4))]


def _resext_fuzz_rows(count=1000, seed=RESEXT_FUZZ_SEED):
    rng = random.Random(seed)
    rows = []
    for i in range(count):
        host_map = {
            1: rng.randint(0, 10_000),
            2: f"n{rng.randrange(100_000)}",
            5: rng.randint(-10_000, 10_000),
            3: _random_cbor_value(rng),  # interleaves between known tags 2 and 5
            BAND_START + 2 + rng.randrange(BAND_START - 2): _random_cbor_value(rng),
        }
        while len(host_map) < 7:
            tag = rng.randrange(0, 1 << 21)
            if tag in (1, 2, 5, RESEXT_TAG) or tag in host_map:
                continue
            host_map[tag] = _random_cbor_value(rng)
        host = cbor.dumps(host_map)
        decision = {"backend": f"b{rng.randrange(100_000)}", "hops": rng.randint(0, 64)}
        strapped = ext.ext_set(RESEXT, host, "Decision", RESEXT_TAG, decision)
        rows.append(
            (
                host.hex(),
                codec.encode(RESEXT, "Decision", decision).hex(),
                strapped.hex(),
                ext.ext_clear(strapped, RESEXT_TAG).hex(),
            )
        )
    return rows


def _fuzz_table_source(rows):
    chunks = []
    cur = []
    size = 0
    for row in rows:
        line = "\t".join(row)
        if cur and size + len(line) + 1 > 50_000:
            chunks.append("\n".join(cur))
            cur = []
            size = 0
        cur.append(line)
        size += len(line) + 1
    if cur:
        chunks.append("\n".join(cur))
    return "listOf(\n" + ",\n".join(f'"""{chunk}"""' for chunk in chunks) + '\n).joinToString("\\n")'


def _kotlin_resext_harness_source(residual_rows, ext_rows, fuzz_rows):
    residual_src = ",\n".join(
        f"    ResidualRow({_kt_string(r['note'])}, {_kt_string(r['wire'])})"
        for r in residual_rows
    )
    ext_src = ",\n".join(
        "    ExtRow("
        f"{_kt_string(r['op'])}, {_kt_string(r['note'])}, {_kt_string(r['host'])}, "
        f"{r['tag']}L, {_kt_nullable_string(r.get('value'))}, {_kt_string(r['expect'])})"
        for r in ext_rows
    )
    fuzz_src = _fuzz_table_source(fuzz_rows)
    return f"""package taut

data class ResidualRow(val note: String, val wire: String)
data class ExtRow(
    val op: String,
    val note: String,
    val host: String,
    val tag: Long,
    val value: String?,
    val expect: String,
)
data class FuzzRow(val host: String, val value: String, val setExpect: String, val clearExpect: String)

private val residualRows = listOf(
{residual_src}
)

private val extRows = listOf(
{ext_src}
)

private val fuzzRowsText = {fuzz_src}

private val hexChars = "0123456789abcdef".toCharArray()
private const val EXT_TAG: Long = {RESEXT_TAG}L
private const val FUZZ_SEED: Long = {RESEXT_FUZZ_SEED}L

private fun hexToBytes(hex: String): ByteArray {{
    val out = ByteArray(hex.length / 2)
    for (i in out.indices) {{
        val hi = Character.digit(hex[i * 2], 16)
        val lo = Character.digit(hex[i * 2 + 1], 16)
        out[i] = ((hi shl 4) or lo).toByte()
    }}
    return out
}}

private fun ByteArray.hex(): String {{
    val out = StringBuilder(size * 2)
    for (byte in this) {{
        val x = byte.toInt() and 0xff
        out.append(hexChars[x ushr 4])
        out.append(hexChars[x and 0x0f])
    }}
    return out.toString()
}}

private fun mismatch(label: String, got: String, want: String): Int {{
    if (got == want) return 0
    println(label + ": got " + got + " want " + want)
    return 1
}}

private fun parsedFuzzRows(): List<FuzzRow> =
    fuzzRowsText.lineSequence().filter {{ it.isNotBlank() }}.map {{
        val parts = it.split('\\t')
        FuzzRow(parts[0], parts[1], parts[2], parts[3])
    }}.toList()

fun main() {{
    var corpusMismatches = 0
    for (row in residualRows) {{
        val decoded = Host.fromCbor(decode(hexToBytes(row.wire)))
        corpusMismatches += mismatch("residual " + row.note, encode(decoded.toCbor()).hex(), row.wire)
    }}

    for (row in extRows) {{
        val host = hexToBytes(row.host)
        when (row.op) {{
            "set" -> {{
                val decision = Decision.fromCbor(decode(hexToBytes(row.value!!)))
                corpusMismatches += mismatch("ext set " + row.note, extSet(host, row.tag, decision.toCbor()).hex(), row.expect)
            }}
            "get" -> {{
                val got = extGet(host, row.tag)
                if (row.expect == "null") {{
                    if (got != null) {{
                        println("ext get " + row.note + ": got value, expected null")
                        corpusMismatches += 1
                    }}
                }} else if (got == null) {{
                    println("ext get " + row.note + ": got null, expected value")
                    corpusMismatches += 1
                }} else {{
                    val decision = Decision.fromCbor(got)
                    corpusMismatches += mismatch("ext get " + row.note, encode(decision.toCbor()).hex(), row.expect)
                }}
            }}
            "clear" -> corpusMismatches += mismatch("ext clear " + row.note, extClear(host, row.tag).hex(), row.expect)
            else -> error("unknown ext op " + row.op)
        }}
    }}

    var invalidCases = 0
    try {{
        extGet(hexToBytes("ff"), 5L)
        println("below-band tag did not throw")
        corpusMismatches += 1
    }} catch (e: IllegalArgumentException) {{
        check(e.message!!.contains("below the band"))
        invalidCases += 1
    }}
    try {{
        val decision = Decision("b7", 1L)
        extSet(hexToBytes("01"), EXT_TAG, decision.toCbor())
        println("non-map host did not throw")
        corpusMismatches += 1
    }} catch (e: IllegalArgumentException) {{
        check(e.message!!.contains("top-level CBOR map"))
        invalidCases += 1
    }}

    var fuzzMismatches = 0
    val fuzzRows = parsedFuzzRows()
    for ((index, row) in fuzzRows.withIndex()) {{
        val host = hexToBytes(row.host)
        val decoded = Host.fromCbor(decode(host))
        fuzzMismatches += mismatch("fuzz residual " + index, encode(decoded.toCbor()).hex(), row.host)

        val decision = Decision.fromCbor(decode(hexToBytes(row.value)))
        val strapped = extSet(host, EXT_TAG, decision.toCbor())
        fuzzMismatches += mismatch("fuzz ext set " + index, strapped.hex(), row.setExpect)
        val got = extGet(strapped, EXT_TAG)
        if (got == null) {{
            println("fuzz ext get " + index + ": got null")
            fuzzMismatches += 1
        }} else {{
            val roundTrip = Decision.fromCbor(got)
            fuzzMismatches += mismatch("fuzz ext get " + index, encode(roundTrip.toCbor()).hex(), row.value)
        }}
        fuzzMismatches += mismatch("fuzz ext clear " + index, extClear(strapped, EXT_TAG).hex(), row.clearExpect)
    }}

    println("kotlin resext corpus_mismatches=" + corpusMismatches +
        " invalid_cases=" + invalidCases +
        " fuzz_seed=" + FUZZ_SEED +
        " fuzz_rows=" + fuzzRows.size +
        " fuzz_mismatches=" + fuzzMismatches)
    check(corpusMismatches == 0) {{ "corpus mismatches=" + corpusMismatches }}
    check(invalidCases == 2) {{ "invalid cases=" + invalidCases }}
    check(fuzzRows.size >= 1000) {{ "fuzz rows=" + fuzzRows.size }}
    check(fuzzMismatches == 0) {{ "fuzz mismatches=" + fuzzMismatches + " seed=" + FUZZ_SEED }}
}}
"""


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


def test_kotlin_extensions_require_forward_compat(tmp_path):
    s = mk(
        Msg("Host", F("id", 1, INT)),
        Msg("Decision", F("backend", 1, STR)),
        extension("Decision", tag=BAND_START + 1),
    )
    with pytest.raises(ValueError):
        scaffold.emit(s, tmp_path, langs=["kotlin"], services=[])
    scaffold.emit(s, tmp_path, langs=["kotlin"], services=[], forward_compat=True)


def test_kotlin_runtime_vendors_cbor_and_ext(tmp_path):
    written = scaffold.emit(
        RESEXT,
        tmp_path,
        langs=["kotlin"],
        services=[],
        runtime=True,
        forward_compat=True,
    )
    names = {p.name for p in written}
    assert "api.kt" in names
    assert "cbor.kt" in names
    assert "ext.kt" in names


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
    kotlinc = _find_kotlinc()
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
        env=_java_env(java),
    )
    subprocess.run([java, "-jar", str(jar)], check=True, cwd=ROOT, env=_java_env(java))


def test_kotlin_resext_corpus_and_fuzz_harness_if_kotlinc(tmp_path):
    kotlinc = _find_kotlinc()
    java = _find_java(kotlinc)
    api = tmp_path / "api.kt"
    harness = tmp_path / "resext_harness.kt"
    jar = tmp_path / "kotlin-resext-parity.jar"

    residual_rows = json.loads(rb.RESIDUAL_PATH.read_text())
    ext_rows = json.loads(rb.EXT_PATH.read_text())
    fuzz_rows = _resext_fuzz_rows()
    api.write_text(kotlin.emit_types(RESEXT, forward_compat=True))
    harness.write_text(_kotlin_resext_harness_source(residual_rows, ext_rows, fuzz_rows))

    subprocess.run(
        [
            kotlinc,
            str(ROOT / "src/taut/gen/runtime/cbor.kt"),
            str(ROOT / "src/taut/gen/runtime/ext.kt"),
            str(api),
            str(harness),
            "-include-runtime",
            "-d",
            str(jar),
        ],
        check=True,
        cwd=ROOT,
        env=_java_env(java),
    )
    result = subprocess.run(
        [java, "-jar", str(jar)],
        check=False,
        cwd=ROOT,
        env=_java_env(java),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "corpus_mismatches=0" in result.stdout
    assert "invalid_cases=2" in result.stdout
    assert f"fuzz_seed={RESEXT_FUZZ_SEED}" in result.stdout
    assert "fuzz_rows=1000" in result.stdout
    assert "fuzz_mismatches=0" in result.stdout
