"""Kotlin generator: mutable `data class`es + `enum class`es + CBOR codec, with
forward-compat residual. (kotlinc compile/run parity verified out-of-band.)"""

import copy
import functools
import json
import os
import random
import re
import subprocess
from pathlib import Path

import pytest

from taut import ext
from taut.corpus.build import IR_PATH
from taut.corpus import parity, parity_kotlin, toolchains
from taut.corpus import resext_build as rb
from taut.gen import kotlin
from taut.gen import scaffold
from taut.ir import options
from taut.ir.dsl import (
    BOOL, BYTES, FLOAT, INT, MISSING_OK, STR, F, List, Map, Msg, Ref, extension, option, schema as mk,
)
from taut.ir.load import load_schema
from taut.ir.model import EnumRef, ListOf, MapOf, MsgRef, Scalar
from taut.ir.shapes import BAND_START
from taut.wire import cbor, codec

RAZEL = load_schema(IR_PATH.parent / "razel.taut.py")
RESEXT = load_schema(rb.IR_PATH)
ROOT = Path(__file__).resolve().parents[2]
RESEXT_TAG = BAND_START + 1
RESEXT_FUZZ_SEED = 0x5EED55_04
INT_MIN, INT_MAX = -(1 << 63), (1 << 63) - 1
INT32_MAX = (1 << 31) - 1   # Kotlin's Int.MAX_VALUE, the largest bound a Kotlin caller can pass
# The messages with no wire field, which forward-compat must still build: none at all, and
# only a transient one. The resext harness round-trips them from BARE_WIRES.
BARE = mk(Msg("Bare"), Msg("Cache", F("hits", 1, INT, transient=True)))
BARE_WIRES = ["a0", "a10100", "a2010002f6", "a11a0010000182f4f5", "01", "80"]
# The hosts the extension helpers read beyond the resext corpus: every kind of item that is
# not a map, malformed input, hosts at the depth ceiling and one beyond it, and (with
# BAD_HOST_SEED) random and mutated hosts. The harness also reads a host DEEP_HOST_ARRAYS deep.
BAD_HOST_SEED = 0xBAD_4057
DEEP_HOST_ARRAYS = 100_000
NON_MAP_HOSTS = ["01", "20", "40", "6161", "80", "8101", "f4", "f5", "f6", "f93c00", "fb3ff0000000000000"]
MALFORMED_HOSTS = ["", "ff", "a1", "a101", "a10100ff", "1c", "c0", "a2010001", "a1617800", "a120",
                   "a1190001", "a11a00100001", "a11a0010000161ff"]
BAD_HOST_DECISION = {"backend": "b7", "hops": 1}
# Maps a host may be: empty, without the extension, and holding at RESEXT_TAG a Decision that is
# incomplete, of the wrong type, or carrying a field its schema lacks.
ODD_HOSTS = [{}, {1: 1}, {RESEXT_TAG: {1: "b7"}}, {RESEXT_TAG: 5}, {RESEXT_TAG: {1: 5, 2: 1}},
             {2: "x", RESEXT_TAG: {1: "b7", 2: 1, 3: "x"}}]
# optional=MISSING_OK reads an absent key as null; optional=True still refuses it.
LATE = mk(
    Msg("Late", F("note", 1, STR, optional=MISSING_OK)),
    Msg("Opt", F("note", 1, STR, optional=True)),
)
# A map field's entries are sorted by key: an int or bool key by value, a str key by
# Unicode code point, which is the order of its UTF-8 bytes (Python's `sorted`). UTF-16
# code unit order (String.compareTo, toSortedMap()) puts a key above U+FFFF, whose
# surrogate pair starts d800-dbff, before one in U+E000..U+FFFF. _KEYED_HARNESS puts
# each key at its position here.
KEYED = mk(Msg("Keyed",
               F("by_text", 1, Map(STR, INT)),
               F("by_int", 2, Map(INT, INT)),
               F("by_flag", 3, Map(BOOL, INT))))
TEXT_KEYS = ["\U0010ffff", "\uffff", "a\U00010000", "\U0001f600", "", "\ue000", "ab",
             "\U00010000", "a", "\ud7ff", "a\uffff", "\u00e9"]
INT_KEYS = [10, -1, 0, -300, 7]
BOOL_KEYS = [True, False]
KEYED_VALUE = {"by_text": {k: i for i, k in enumerate(TEXT_KEYS)},
               "by_int": {k: i for i, k in enumerate(INT_KEYS)},
               "by_flag": {k: i for i, k in enumerate(BOOL_KEYS)}}
# _KEYED_HARNESS's arguments: the keys, comma-separated, a str key as the hex of its UTF-8.
KEY_ARGS = [",".join(k.encode().hex() for k in TEXT_KEYS),
            ",".join(str(k) for k in INT_KEYS),
            ",".join(str(k).lower() for k in BOOL_KEYS)]


def _find_kotlin_tools():
    """(kotlinc, java): the gate's finder, `toolchains.find_kotlin_tools`, which probes kotlinc
    under the java it finds for it, so Android Studio's bundle needs no JAVA_HOME."""
    tools = toolchains.find_kotlin_tools()
    if tools is None:
        pytest.skip("no kotlinc that runs: searched KOTLINC, Android Studio and PATH, each with "
                    "JAVA_HOME, a JDK beside it or PATH's java")
    return tools


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


def _python_ext(op, host):
    """What ext.py, the reference, makes of `op` at RESEXT_TAG on `host`: `ok <hex>` (for get,
    the extension's own encoding), `null` (get, none there) or `err <Tag;payload...>`."""
    try:
        if op == "set":
            return "ok " + ext.ext_set(RESEXT, host, "Decision", RESEXT_TAG, BAD_HOST_DECISION).hex()
        if op == "get":
            got = ext.ext_get(RESEXT, host, "Decision", RESEXT_TAG)
            return "null" if got is None else "ok " + codec.encode(RESEXT, "Decision", got).hex()
        return "ok " + ext.ext_clear(host, RESEXT_TAG).hex()
    except cbor.DecodeError as exc:
        return "err " + parity.format_error(exc.tag, exc.payload)


def _deep_host(arrays):
    """A host map whose unknown field 7 holds `arrays` nested arrays: 1 + `arrays` deep."""
    return bytes.fromhex("a107" + "81" * (arrays - 1) + "80")


@functools.cache
def _bad_host_rows(count=60, seed=BAD_HOST_SEED):
    """(op, host hex, what ext.py makes of it) for each op on NON_MAP_HOSTS, MALFORMED_HOSTS,
    ODD_HOSTS, a host at the depth ceiling (128 deep) and one beyond it, `count` random byte
    strings and `count` mutations of strapped hosts."""
    rng = random.Random(seed)
    hosts = [bytes.fromhex(h) for h in NON_MAP_HOSTS + MALFORMED_HOSTS] + [cbor.dumps(h) for h in ODD_HOSTS]
    hosts += [_deep_host(127), _deep_host(128)]  # read at the ceiling (TautOptions.md G3)
    hosts += [bytes(rng.randrange(256) for _ in range(rng.randrange(1, 12))) for _ in range(count)]
    strapped = [bytes.fromhex(row[2]) for row in _resext_fuzz_rows(count=8, seed=seed)]
    for i in range(count):
        mutate = _mutate_tree if i % 2 else _mutate_bytes
        hosts.append(mutate(rng.choice(strapped), rng))
    return tuple((op, host.hex(), _python_ext(op, host)) for host in hosts for op in ("set", "get", "clear"))


def _bare_rows():
    """(message, wire, what codec.py makes of it: `ok <re-encoding>` or `err ...`) for BARE."""
    rows = []
    for message in BARE.messages:
        for wire in BARE_WIRES:
            try:
                again = codec.encode(BARE, message, codec.decode(BARE, message, bytes.fromhex(wire)))
                rows.append((message, wire, "ok " + again.hex()))
            except cbor.DecodeError as exc:
                rows.append((message, wire, "err " + parity.format_error(exc.tag, exc.payload)))
    return rows


def _kotlin_resext_harness_source(residual_rows, ext_rows, fuzz_rows, bad_host_rows, bare_rows,
                                  deep_host_expect):
    deep_host_src = ",\n".join(f"    {_kt_string(op)} to {_kt_string(want)}" for op, want in deep_host_expect.items())
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
    bare_src = ",\n".join(f"    BareRow({', '.join(_kt_string(v) for v in row)})" for row in bare_rows)
    fuzz_src = _fuzz_table_source(fuzz_rows)
    bad_host_src = _fuzz_table_source(bad_host_rows)
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
data class BadHostRow(val op: String, val host: String, val expect: String)
data class BareRow(val message: String, val wire: String, val expect: String)

private val residualRows = listOf(
{residual_src}
)

private val extRows = listOf(
{ext_src}
)

private val bareRows = listOf(
{bare_src}
)

private val fuzzRowsText = {fuzz_src}

private val badHostRowsText = {bad_host_src}

// What ext.py, the reference, makes of each op on a host DEEP_HOST_ARRAYS deep.
private val deepHostExpect = listOf(
{deep_host_src}
)

private val hexChars = "0123456789abcdef".toCharArray()
private const val EXT_TAG: Long = {RESEXT_TAG}L
private const val BAND: Long = {BAND_START}L
private const val FUZZ_SEED: Long = {RESEXT_FUZZ_SEED}L
private val BAD_HOST_DECISION = Decision({_kt_string(BAD_HOST_DECISION["backend"])}, {BAD_HOST_DECISION["hops"]}L)

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
    if (got == want) {{
        return 0
    }}
    println(label + ": got " + got + " want " + want)
    return 1
}}

private fun parsedFuzzRows(): List<FuzzRow> =
    fuzzRowsText.lineSequence().filter {{ it.isNotBlank() }}.map {{
        val parts = it.split('\\t')
        FuzzRow(parts[0], parts[1], parts[2], parts[3])
    }}.toList()

private fun parsedBadHostRows(): List<BadHostRow> =
    badHostRowsText.lineSequence().filter {{ it.isNotBlank() }}.map {{
        val parts = it.split('\\t')
        BadHostRow(parts[0], parts[1], parts[2])
    }}.toList()

// A DecodeError as the parity gate's `err` detail: its tag, then each payload field it carries.
private fun describe(e: DecodeError): String = when (e) {{
    is DecodeError.UnsupportedInfo -> "UnsupportedInfo;info=" + e.info
    is DecodeError.UnsupportedMajor -> "UnsupportedMajor;major=" + e.major
    is DecodeError.IntOverflow -> "IntOverflow;value=" + e.value
    is DecodeError.DuplicateMapKey -> "DuplicateMapKey;key=" + e.key
    is DecodeError.MissingKey -> "MissingKey;key=" + e.key
    is DecodeError.WrongType -> "WrongType;expected=" + e.expected
    is DecodeError.UnknownEnum -> "UnknownEnum;enum=" + e.enumName + ";value=" + e.value
    is DecodeError.NonCanonicalInt -> "NonCanonicalInt;value=" + e.value
    is DecodeError.NegativeMapKey -> "NegativeMapKey;key=" + e.key
    is DecodeError.TooDeep -> "TooDeep;limit=" + e.limit
    is DecodeError.TooLarge -> "TooLarge;len=" + e.len + ";limit=" + e.limit
    else -> e.javaClass.simpleName
}}

// A host map whose unknown field 7 holds `arrays` nested arrays: 1 + `arrays` deep.
private fun deepHost(arrays: Int): ByteArray {{
    val out = ByteArray(arrays + 2) {{ 0x81.toByte() }}
    out[0] = 0xa1.toByte()
    out[1] = 0x07
    out[arrays + 1] = 0x80.toByte()
    return out
}}

// The raw decode's bounds are its caller's arguments (TautOptions.md OPT-P3): a depth below 1 or
// a negative length is the caller's error, IllegalArgumentException, found before any byte is
// read and never a DecodeError.
private val badBounds: List<Pair<String, (ByteArray) -> Cbor>> = listOf(
    "maxDepth=0" to {{ data: ByteArray -> decode(data, maxDepth = 0) }},
    "maxDepth=-1" to {{ data: ByteArray -> decode(data, maxDepth = -1) }},
    "maxDepth=Int.MIN_VALUE" to {{ data: ByteArray -> decode(data, maxDepth = Int.MIN_VALUE) }},
    "maxEncodedLen=-1" to {{ data: ByteArray -> decode(data, maxEncodedLen = -1) }},
    "maxEncodedLen=Int.MIN_VALUE" to {{ data: ByteArray -> decode(data, maxEncodedLen = Int.MIN_VALUE) }},
)

private fun refusesArgument(data: ByteArray, read: (ByteArray) -> Cbor): Boolean {{
    try {{
        read(data)
    }} catch (e: IllegalArgumentException) {{
        return true
    }} catch (e: DecodeError) {{
        return false
    }}
    return false
}}

// What an extension helper makes of `op` at `tag` on `host`: a value or a DecodeError (CD-E4).
// Anything else escaping is `untyped`, which no row expects.
private fun extOutcome(op: String, host: ByteArray, tag: Long): String {{
    try {{
        return when (op) {{
            "set" -> {{
                "ok " + extSet(host, tag, BAD_HOST_DECISION.toCbor()).hex()
            }}
            "get" -> {{
                val got = extGet(host, tag)
                if (got == null) {{
                    "null"
                }} else {{
                    "ok " + encode(Decision.fromCbor(got).toCbor()).hex()
                }}
            }}
            else -> {{
                "ok " + extClear(host, tag).hex()
            }}
        }}
    }} catch (e: DecodeError) {{
        return "err " + describe(e)
    }} catch (e: Throwable) {{
        return "untyped " + e.javaClass.name + ": " + e.message
    }}
}}

// A tag below the band is the caller's error, IllegalArgumentException, found before the host
// is read: this host is not even CBOR.
private fun refusesBelowBand(op: String, tag: Long): Boolean {{
    val host = hexToBytes("ff")
    try {{
        when (op) {{
            "set" -> {{
                extSet(host, tag, BAD_HOST_DECISION.toCbor())
            }}
            "get" -> {{
                extGet(host, tag)
            }}
            else -> {{
                extClear(host, tag)
            }}
        }}
    }} catch (e: IllegalArgumentException) {{
        return e.message.orEmpty().contains("below the band")
    }} catch (e: DecodeError) {{
        return false
    }}
    return false
}}

// A message with no wire field, generated with forward-compat: its re-encoding, or the error.
private fun bareOutcome(message: String, wire: ByteArray): String {{
    try {{
        val c = decode(wire)
        return when (message) {{
            "Bare" -> {{
                "ok " + encode(Bare.fromCbor(c).toCbor()).hex()
            }}
            else -> {{
                "ok " + encode(Cache.fromCbor(c).toCbor()).hex()
            }}
        }}
    }} catch (e: DecodeError) {{
        return "err " + describe(e)
    }}
}}

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
    for (op in listOf("set", "get", "clear")) {{
        for (tag in longArrayOf(0L, BAND - 1L, -1L, Long.MIN_VALUE)) {{
            if (refusesBelowBand(op, tag)) {{
                invalidCases += 1
            }} else {{
                println("ext " + op + ": below-band tag " + tag + " was not refused")
                corpusMismatches += 1
            }}
        }}
    }}
    val atBand = extOutcome("clear", hexToBytes("a0"), BAND)
    corpusMismatches += mismatch("ext clear at the band's first tag", atBand, "ok a0")

    var badHostMismatches = 0
    val badHostRows = parsedBadHostRows()
    for (row in badHostRows) {{
        val got = extOutcome(row.op, hexToBytes(row.host), EXT_TAG)
        badHostMismatches += mismatch("bad host " + row.op + " " + row.host, got, row.expect)
    }}

    // A host is read at the depth ceiling with no length bound (TautOptions.md G3): one
    // {DEEP_HOST_ARRAYS} arrays deep is what ext.py says, TooDeep{{128}}, not a StackOverflowError,
    // and one of 100,000 bytes is read whole.
    var boundMismatches = 0
    val deep = deepHost({DEEP_HOST_ARRAYS})
    for ((op, want) in deepHostExpect) {{
        boundMismatches += mismatch("deep host " + op, extOutcome(op, deep, EXT_TAG), want)
    }}
    val big = encode(Cbor.map(listOf(1L to Cbor.int(1L), 7L to Cbor.bytes(ByteArray(100_000) {{ 0x78.toByte() }}))))
    boundMismatches += mismatch("big host get", extOutcome("get", big, EXT_TAG), "null")
    val bigStrapped = extSet(big, EXT_TAG, BAD_HOST_DECISION.toCbor())
    boundMismatches += mismatch("big host strapped get", extOutcome("get", bigStrapped, EXT_TAG),
        "ok " + encode(BAD_HOST_DECISION.toCbor()).hex())
    boundMismatches += mismatch("big host clear", extClear(bigStrapped, EXT_TAG).hex(), big.hex())

    var argumentCases = 0
    for (hex in listOf("", "00", "c0c0c0c0")) {{
        for ((label, read) in badBounds) {{
            if (refusesArgument(hexToBytes(hex), read)) {{
                argumentCases += 1
            }} else {{
                println("decode " + label + " of '" + hex + "' was not refused as the caller's error")
                corpusMismatches += 1
            }}
        }}
    }}

    var bareMismatches = 0
    for (row in bareRows) {{
        val got = bareOutcome(row.message, hexToBytes(row.wire))
        bareMismatches += mismatch("bare " + row.message + " " + row.wire, got, row.expect)
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
        " argument_cases=" + argumentCases +
        " bad_host_rows=" + badHostRows.size +
        " bad_host_mismatches=" + badHostMismatches +
        " bound_mismatches=" + boundMismatches +
        " bare_mismatches=" + bareMismatches +
        " fuzz_seed=" + FUZZ_SEED +
        " fuzz_rows=" + fuzzRows.size +
        " fuzz_mismatches=" + fuzzMismatches)
    check(corpusMismatches == 0) {{ "corpus mismatches=" + corpusMismatches }}
    check(invalidCases == 12) {{ "invalid cases=" + invalidCases }}
    check(argumentCases == 15) {{ "argument cases=" + argumentCases }}
    check(badHostMismatches == 0) {{ "bad host mismatches=" + badHostMismatches }}
    check(boundMismatches == 0) {{ "bound mismatches=" + boundMismatches }}
    check(bareMismatches == 0) {{ "bare mismatches=" + bareMismatches }}
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


def test_forward_compat_types_its_lists_so_a_message_without_wire_fields_builds():
    """kotlinc cannot infer T for an empty `listOf()` that nothing types, which a message with
    no wire field (BARE: none at all, or only a transient one) emitted under forward-compat, in
    toCbor's known entries and fromCbor's known tags. Both lists name their type; the
    resext harness compiles BARE so, and the gate's kotlin/fc variant the fixture's Empty."""
    fc = kotlin.emit_types(mk(Msg("Bare"), Msg("Cache", F("hits", 1, INT, transient=True)),
                              Msg("One", F("n", 1, INT))), forward_compat=True)
    assert fc.count("return Cbor.map(listOf<Pair<Long, Cbor>>() + wireResidual)") == 2
    assert fc.count("wireResidual = c.mapEntries.filter { it.first !in listOf<Long>() },") == 2
    assert "return Cbor.map(listOf<Pair<Long, Cbor>>(1L to Cbor.int(n)) + wireResidual)" in fc
    assert "wireResidual = c.mapEntries.filter { it.first !in listOf<Long>(1L) }," in fc
    assert "listOf()" not in fc
    plain = kotlin.emit_types(BARE)                  # Cbor.map's parameter types the list
    assert plain.count("return Cbor.map(listOf())") == 2 and "listOf<" not in plain


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


# --- the bounds (D26, TautCheckedDecode.md §3; D27, TautOptions.md OPT-D3, OPT-L6) ------------

# A file that declares both bounds; messages that override its depth, inherit both, override its
# length at the ceiling on declared values, and have no field.
FILED = mk(
    option.max_depth(3), option.max_encoded_len(16),
    Msg("Tree", F("kids", 1, List(Ref("Tree"))), option.max_depth(64)),
    Msg("Plain", F("v", 1, List(INT))),
    Msg("Blob", F("b", 1, BYTES), option.max_encoded_len(INT32_MAX)),
    Msg("Nothing"),
)


def _companion(source, message):
    """The lines inside `message`'s companion object in generated `source`."""
    lines = source.splitlines()
    start = next(i for i, line in enumerate(lines) if re.fullmatch(rf"(data )?class {message}\(", line))
    opening = lines.index("    companion object {", start)
    return lines[opening + 1:lines.index("    }", opening)]


def test_each_message_carries_its_bounds_and_a_decode_from_bytes():
    """CD-B3, OPT-L6: a message's companion holds MAX_DEPTH and MAX_ENCODED_LEN, the effective
    values `options.effective` resolves when the code is generated (the message's, else the
    file's, else 32 and none), and `decode(bytes)`, the typed entry point, which takes no bound
    and passes both to the raw decode. `fromCbor` reads a tree its caller decoded (G1)."""
    fixture = parity.parity_schema()
    spot = [
        (FILED, {"Tree": (64, 16), "Plain": (3, 16), "Blob": (3, INT32_MAX), "Nothing": (3, 16)}),
        (fixture, {"IntBox": (32, None), "Tree64": (64, None), "Tree128": (128, None), "Flat2": (2, None),
                   "Sized8": (32, 8), "Holds64": (32, None), "HoldsSized8": (32, None)}),
    ]
    for schema_, want in spot:
        resolved = {name: (options.effective(schema_, "max_depth", message=name),
                           options.effective(schema_, "max_encoded_len", message=name))
                    for name in schema_.messages}
        assert {name: resolved[name] for name in want} == want
        for forward_compat in (False, True):
            source = kotlin.emit_types(schema_, forward_compat=forward_compat)
            for name, (depth, length) in resolved.items():
                assert _companion(source, name)[:3] == [
                    f"        const val MAX_DEPTH: Int = {depth}",
                    f"        val MAX_ENCODED_LEN: Int? = {'null' if length is None else length}",
                    f"        fun decode(bytes: ByteArray): {name} = "
                    "fromCbor(taut.decode(bytes, MAX_DEPTH, MAX_ENCODED_LEN))",
                ], (name, forward_compat)


def test_the_runtime_exports_the_depth_numbers_and_a_bounded_raw_decode():
    """CD-B3: the vendored cbor.kt holds taut's two depth numbers as compile-time constants, and
    its raw decode takes an optional depth, 32 unless passed, and an optional length. The gate
    compares the numbers its runner prints from them (#constants) with the corpus header."""
    lines = (ROOT / "src/taut/gen/runtime/cbor.kt").read_text().splitlines()
    assert f"const val DEFAULT_MAX_DEPTH: Int = {options.DEFAULT_MAX_DEPTH}" in lines
    assert f"const val MAX_DEPTH_CEILING: Int = {options.MAX_DEPTH_CEILING}" in lines
    assert ("fun decode(data: ByteArray, maxDepth: Int = DEFAULT_MAX_DEPTH, maxEncodedLen: Int? = null)"
            ": Cbor {") in lines


def test_kotlin_float_parity_harness_if_kotlinc(tmp_path):
    kotlinc, java = _find_kotlin_tools()
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


@pytest.mark.gate
def test_kotlin_passes_the_parity_gate():
    """The shared corpus, lead rows included, through `tautc parity`'s Kotlin runner
    (`taut.corpus.parity_kotlin`: one kotlinc build each), as kotlin and kotlin/fc, each held
    to the gate's governance: GREEN, or RED and allowlisted. A missing toolchain skips."""
    reports, violations = parity.governed_variants(parity_kotlin.run)
    for report in reports:
        if not report.available:
            pytest.skip(report.skip_reason)
    assert violations == [], "\n".join(violations)
    encode_fail = {r["name"] for r in parity.int_rows() if r["kind"] == "encode_fail"}
    for report in reports:
        if not report.fault:  # only an encode-fail row is satisfied by the type system (Long)
            assert {r.name for r in report.results if r.status == parity.TYPE_SATISFIED} == encode_fail


def test_kotlin_resext_corpus_and_fuzz_harness_if_kotlinc(tmp_path):
    """The runtime's extension helpers and residual against ext.py, the reference, in one kotlinc
    build that also holds the runtime's caller errors: a below-band tag (invalid_cases) and an
    out-of-range bound passed to the raw decode (argument_cases, TautOptions.md OPT-P3). A host
    is read at the depth ceiling with no length bound (bound_mismatches, G3)."""
    kotlinc, java = _find_kotlin_tools()
    api = tmp_path / "api.kt"
    bare = tmp_path / "bare.kt"
    harness = tmp_path / "resext_harness.kt"
    jar = tmp_path / "kotlin-resext-parity.jar"

    residual_rows = json.loads(rb.RESIDUAL_PATH.read_text())
    ext_rows = json.loads(rb.EXT_PATH.read_text())
    fuzz_rows = _resext_fuzz_rows()
    bad_host_rows = _bad_host_rows()
    deep_host = _deep_host(DEEP_HOST_ARRAYS)
    deep_host_expect = {op: _python_ext(op, deep_host) for op in ("set", "get", "clear")}
    api.write_text(kotlin.emit_types(RESEXT, forward_compat=True))
    bare.write_text(kotlin.emit_types(BARE, forward_compat=True))
    harness.write_text(_kotlin_resext_harness_source(residual_rows, ext_rows, fuzz_rows, bad_host_rows,
                                                     _bare_rows(), deep_host_expect))

    subprocess.run(
        [
            kotlinc,
            str(ROOT / "src/taut/gen/runtime/cbor.kt"),
            str(ROOT / "src/taut/gen/runtime/ext.kt"),
            str(api),
            str(bare),
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
    assert "invalid_cases=12" in result.stdout      # each op refuses four below-band tags
    assert "argument_cases=15" in result.stdout     # five bad bounds, on three inputs each
    assert f"bad_host_rows={len(bad_host_rows)} bad_host_mismatches=0" in result.stdout
    assert "bound_mismatches=0" in result.stdout
    assert "bare_mismatches=0" in result.stdout
    assert f"fuzz_seed={RESEXT_FUZZ_SEED}" in result.stdout
    assert "fuzz_rows=1000" in result.stdout
    assert "fuzz_mismatches=0" in result.stdout


def test_the_bad_hosts_state_what_ext_py_the_reference_does():
    """CD-E4 in the reference: a host that is not a map is WrongType{map} for every op, a
    malformed one its DecodeError, one deeper than the ceiling TooDeep{128} (G3), and the rows
    the Kotlin harness replays hold every outcome."""
    rows = _bad_host_rows()
    by_host = {}
    for op, host, outcome in rows:
        by_host.setdefault(host, {})[op] = outcome
    for host in NON_MAP_HOSTS:
        assert by_host[host] == dict.fromkeys(("set", "get", "clear"), "err WrongType;expected=map")
    assert {host: by_host[host]["get"] for host in MALFORMED_HOSTS} == {
        "": "err Truncated",
        "ff": "err UnsupportedInfo;info=31",
        "a1": "err Truncated",
        "a101": "err Truncated",
        "a10100ff": "err TrailingBytes",
        "1c": "err UnsupportedInfo;info=28",
        "c0": "err UnsupportedMajor;major=6",
        "a2010001": "err DuplicateMapKey;key=1",
        "a1617800": "err NonIntegerMapKey",
        "a120": "err NegativeMapKey;key=-1",
        "a1190001": "err NonCanonicalInt;value=1",
        "a11a00100001": "err Truncated",
        "a11a0010000161ff": "err InvalidUtf8",
    }
    assert [by_host[cbor.dumps(h).hex()]["get"] for h in ODD_HOSTS] == [
        "null", "null", "err MissingKey;key=2", "err WrongType;expected=map", "err WrongType;expected=text",
        "ok a3016262370201036178"]
    at_ceiling = _deep_host(127).hex()                            # 128 deep: read
    assert by_host[at_ceiling]["get"] == "null" and by_host[at_ceiling]["clear"] == "ok " + at_ceiling
    assert by_host[at_ceiling]["set"].startswith("ok a2")         # the host's field 7 and the extension
    too_deep = dict.fromkeys(("set", "get", "clear"), "err TooDeep;limit=128")
    assert by_host[_deep_host(128).hex()] == too_deep
    assert {op: _python_ext(op, _deep_host(DEEP_HOST_ARRAYS)) for op in too_deep} == too_deep
    kinds = {outcome.split(";")[0] if outcome.startswith("err ") else outcome.split(" ")[0]
             for _, _, outcome in rows}
    assert {"ok", "null", "err WrongType", "err MissingKey", "err Truncated", "err InvalidUtf8",
            "err TooDeep"} <= kinds


def test_a_message_without_wire_fields_still_requires_a_map():
    s = kotlin.emit_types(mk(Msg("Empty"), Msg("Cache", F("hits", 1, INT, transient=True))))
    assert s.count('throw DecodeError.WrongType("map")') == 2


def test_kotlin_generates_missing_ok(tmp_path):
    scaffold.emit(LATE, tmp_path, langs=["kotlin"], services=[])
    s = (tmp_path / "kotlin" / "api.kt").read_text()
    assert "note = c.getOrNull(1)?.let { if (it.isNull) { null } else { it.textVal } }," in s
    assert "note = c.get(1).let { if (it.isNull) null else it.textVal }," in s
    assert s.count("1L to (note?.let { Cbor.text(it) } ?: Cbor.nul)") == 2  # encode unchanged


_LATE_HARNESS = r'''
package taut

private fun unhex(s: String): ByteArray {
    val out = ByteArray(s.length / 2)
    for (i in out.indices) {
        out[i] = s.substring(2 * i, 2 * i + 2).toInt(16).toByte()
    }
    return out
}

private fun hexOf(b: ByteArray): String {
    val out = StringBuilder()
    for (x in b) {
        out.append(String.format("%02x", x.toInt() and 0xff))
    }
    return out.toString()
}

private fun observe(label: String, read: () -> String?) {
    val seen = try {
        "ok " + (read() ?: "null")
    } catch (e: DecodeError.WrongType) {
        "WrongType{" + e.expected + "}"
    } catch (e: DecodeError.MissingKey) {
        "MissingKey{" + e.key + "}"
    } catch (e: DecodeError) {
        e.javaClass.simpleName
    }
    println(label + "\t" + seen)
}

fun main() {
    for (hex in listOf("a0", "a101f6", "a10101", "00")) {
        observe("Late " + hex) { Late.fromCbor(decode(unhex(hex))).note }
    }
    observe("Opt a0") { Opt.fromCbor(decode(unhex("a0"))).note }
    println("Late encode\t" + hexOf(encode(Late().toCbor())))
}
'''


def test_kotlin_missing_ok_decode_if_kotlinc(tmp_path):
    kotlinc, java = _find_kotlin_tools()
    scaffold.emit(LATE, tmp_path, langs=["kotlin"], services=[], runtime=True)
    harness = tmp_path / "late_harness.kt"
    harness.write_text(_LATE_HARNESS)
    jar = tmp_path / "kotlin-missing-ok.jar"
    sources = sorted(str(p) for p in (tmp_path / "kotlin").glob("*.kt"))
    subprocess.run(
        [kotlinc, *sources, str(harness), "-include-runtime", "-d", str(jar)],
        check=True,
        cwd=tmp_path,
        env=_java_env(java),
    )
    result = subprocess.run(
        [java, "-jar", str(jar)],
        check=False,
        cwd=tmp_path,
        env=_java_env(java),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    observed = dict(line.split("\t", 1) for line in result.stdout.splitlines())
    assert observed == {
        "Late a0": "ok null",              # absent reads as null (M16)
        "Late a101f6": "ok null",          # present null is null
        "Late a10101": "WrongType{text}",  # a present value keeps its type (M17)
        "Late 00": "WrongType{map}",       # the message is still a map
        "Opt a0": "MissingKey{1}",         # optional=True: absent is still MissingKey
        "Late encode": "a101f6",           # encode unchanged: unset is written as null
    }


_KEYED_HARNESS = r'''
package taut

private fun unhex(s: String): ByteArray {
    val out = ByteArray(s.length / 2)
    for (i in out.indices) {
        out[i] = s.substring(2 * i, 2 * i + 2).toInt(16).toByte()
    }
    return out
}

private fun hexOf(b: ByteArray): String {
    val out = StringBuilder()
    for (x in b) {
        out.append(String.format("%02x", x.toInt() and 0xff))
    }
    return out.toString()
}

// The comma-separated `keys`, read by `parse`, each mapped to its position.
private fun <K> positions(keys: String, parse: (String) -> K): Map<K, Long> {
    val out = LinkedHashMap<K, Long>()
    for (key in keys.split(",")) {
        out[parse(key)] = out.size.toLong()
    }
    return out
}

// args: Keyed's str, int and bool keys (KEY_ARGS).
fun main(args: Array<String>) {
    val keyed = Keyed(
        by_text = positions(args[0]) { String(unhex(it), Charsets.UTF_8) },
        by_int = positions(args[1]) { it.toLong() },
        by_flag = positions(args[2]) { it == "true" },
    )
    println(hexOf(encode(keyed.toCbor())))
}
'''


def test_kotlin_sorts_str_map_keys_by_code_point_if_kotlinc(tmp_path):
    """Map entries put in any order encode sorted by key as Python sorts them: a str key
    by code point, so U+FFFF before U+10000 and "a\\uffff" before "a\\U00010000", and an
    int or bool key by value, as before. One kotlinc build."""
    kotlinc, java = _find_kotlin_tools()
    scaffold.emit(KEYED, tmp_path, langs=["kotlin"], services=[], runtime=True)
    harness = tmp_path / "keyed_harness.kt"
    harness.write_text(_KEYED_HARNESS)
    jar = tmp_path / "kotlin-keyed.jar"
    sources = sorted(str(p) for p in (tmp_path / "kotlin").glob("*.kt"))
    subprocess.run(
        [kotlinc, *sources, str(harness), "-include-runtime", "-d", str(jar)],
        check=True,
        cwd=tmp_path,
        env=_java_env(java),
    )
    result = subprocess.run(
        [java, "-jar", str(jar), *KEY_ARGS],
        check=False,
        cwd=tmp_path,
        env=_java_env(java),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.strip() == codec.encode(KEYED, "Keyed", KEYED_VALUE).hex()


# --- beyond the corpus: question 9's key text and fail-closed decode (CD-E4) ---------------

# Question 9 (TautCheckedDecode.md §8): a repeated key's payload is the key as text, an int in
# decimal, a str as itself and a bool as `true` or `false`. A raw map's keys, (key, text), and
# a repeated key in each map<K,V> field of the fixture, (message, field tag, key, text).
Q9_RAW = [(0, "0"), (23, "23"), (24, "24"), (1 << 53, "9007199254740992"), (INT_MAX, str(INT_MAX))]
Q9_FIELDS = [
    ("IntBox", 2, -1, "-1"),                        # map<int, int>
    ("IntBox", 2, INT_MIN, str(INT_MIN)),
    ("Names", 27, INT_MAX, str(INT_MAX)),
    ("Shapes", 16, -300, "-300"),                   # map<int, EnumBox>
    ("Shapes", 14, "", ""),                         # map<str, int>
    ("Shapes", 14, "a b", "a b"),
    ("Shapes", 14, "naïve", "naïve"),
    ("Shapes", 14, "\U0001f600", "\U0001f600"),
    ("Shapes", 18, "true", "true"),                 # an optional map<str, int>
    ("Names", 9, "5", "5"),
    ("Shapes", 15, False, "false"),                 # map<bool, Mode>
    ("Shapes", 15, True, "true"),
]
# Raw inputs at CD-E5's edges; Python, the reference, states what each is.
RAW_EDGES = [
    "", "17", "1817", "1818", "1900ff", "190100", "1a0000ffff", "1a00010000", "1b00000000ffffffff",
    "1b0000000100000000", "3817", "5800", "780161", "9800", "b800", "a1180000", "7b0000000000000001",
    "1900", "7b0020000000000000", "5b7fffffffffffffff", "7b8000000000000000", "9b7fffffffffffffff",
    "bb8000000000000000", "fa3f800000", "fb3ff0000000000000", "fa7fc00001", "f97c01", "f98000", "f93c",
    "f7", "f800", "e0", "ff", "9f", "3c", "d8", "df", "c1", "a1f500", "a2000000", "a2010002",
    "a20100010002", "a13b7fffffffffffffff00", "a11b7fffffffffffffff00", "a11b800000000000000000",
    "3bffffffffffffffff", "8261ff00", "63eda080", "62c328", "61c0", "64f4908080", "62c3a9",
    "64f0908080", "63efbfbf", "82a0a0", "00ff",
]
# An enum's wire value that is not a member, or not an int.
ENUM_EDGES = ["02", "20", "1b7fffffffffffffff", "3b7fffffffffffffff", "6161", "f5", "f6", "80", "a0",
              "fa3f800000", "1817"]
# The bounds a raw call passes (TautCheckedDecode.md CD-B3, CD-B5): depth arguments, each applied
# as given up to the ceiling and as the ceiling above it, up to Int's largest, which a Kotlin
# caller can pass; and (hex, limits) at the edges: a map key is an item of its map, and a length
# bound, at, below and far above the input's length, is checked first.
DEPTH_ARGUMENTS = [1, 2, 5, 31, 33, 64, 127, 128, 129, 1000, INT32_MAX]
LIMIT_EDGES = [
    ("a18000", {"max_depth": 1}), ("a18000", {"max_depth": 2}),
    ("83010203", {"max_encoded_len": 4}), ("83010203", {"max_encoded_len": 3}),
    ("83010203", {"max_encoded_len": INT32_MAX}), ("00", {"max_encoded_len": 0}),
    ("0000", {"max_encoded_len": 1}),
    ("81" * 40 + "80", {"max_depth": 64, "max_encoded_len": 10}),
    ("81" * 40 + "80", {"max_depth": 40, "max_encoded_len": 41}),
    ("81" * 40 + "80", {"max_depth": 41, "max_encoded_len": 41}),
]
# A typed decode of 100,000-deep input under its root's own depth bound (B9 and B10 are raw):
# (message, the opener repeated, the bound).
DEEP_ROOTS = [("Tree64", "a10181", 64), ("Tree128", "a10181", 128), ("Holds64", "a10181", 32),
              ("IntBox", "81", 32)]
BEYOND_SEED = 0xB3_70_4D
_SAMPLES = {
    "int": [0, 1, -1, 23, 24, -25, 256, 1 << 40, INT_MIN, INT_MAX],
    "str": ["", "a", "b", "naïve", "\uffff", "\U00010000"],
    "bytes": [b"", b"\x00", b"\xff\x00"],
    "bool": [False, True],
    "float": [0.0, -0.0, 1.5, 0.1, -2.25, 1e300, float("inf"), float("nan")],
}
# What a tree mutation puts in a node's place: each CBOR kind, and maps shaped like a message,
# a map<K,V> entry or two entries with one key.
_REPLACEMENTS = [0, 7, -1, "x", b"", True, None, 1.5, [], {}, [0], ["x"], [{}], [[None]], [{1: 0}],
                 {1: 0}, {1: "x", 2: 0}, [{1: 0, 2: 0}, {1: 0, 2: 1}]]


# A recursive message (Tree64, Tree128) nests through a list of itself. A list inside this many
# messages is left empty, so a random tree is at most 8 containers deep, inside every bound in
# the fixture that it can meet; no other fixture message nests a list that deep.
_NATIVE_NESTING = 4


def _native(schema, t, rng, nesting=0):
    """A random native value of type `t`, as `taut.wire.codec` takes one, inside `nesting`
    messages."""
    if isinstance(t, Scalar):
        return rng.choice(_SAMPLES[t.kind])
    if isinstance(t, EnumRef):
        return rng.choice(list(schema.enums[t.name].members))
    if isinstance(t, MsgRef):
        return {f.name: None if f.optional and rng.randrange(3) == 0 else _native(schema, f.type, rng, nesting + 1)
                for f in schema.messages[t.name].wire_fields()}
    if isinstance(t, ListOf):
        count = rng.randrange(3) if nesting < _NATIVE_NESTING else 0
        return [_native(schema, t.elem, rng, nesting) for _ in range(count)]
    assert isinstance(t, MapOf)
    return {_native(schema, t.key, rng, nesting): _native(schema, t.value, rng, nesting)
            for _ in range(rng.randrange(3))}


def _nodes(node, parent=None, key=None):
    """`(parent, key, node)` for every node of a decoded CBOR tree; the root's parent is None."""
    yield parent, key, node
    children = enumerate(node) if isinstance(node, list) else node.items() if isinstance(node, dict) else ()
    for child_key, child in list(children):
        yield from _nodes(child, node, child_key)


def _mutate_tree(data, rng):
    """`data` with one node of its tree replaced, or a key dropped from or added to a map, or an
    item repeated in or swapped within an array: canonical CBOR a schema may refuse."""
    # The fixture's recursive messages (Tree64, Tree128) may nest past the raw default, so the
    # tree is read at the ceiling; each row is still judged under its root's own bounds.
    tree = cbor.loads(data, max_depth=cbor.MAX_DEPTH_CEILING)
    parent, key, node = rng.choice(list(_nodes(tree)))
    move = rng.randrange(5)
    if move == 1 and isinstance(node, dict) and node:
        del node[rng.choice(list(node))]
    elif move == 2 and isinstance(node, dict):
        node[rng.choice([0, 3, 99, BAND_START, INT_MAX])] = copy.deepcopy(rng.choice(_REPLACEMENTS))
    elif move == 3 and isinstance(node, list) and node:
        node.insert(rng.randrange(len(node) + 1), copy.deepcopy(rng.choice(node)))
    elif move == 4 and isinstance(node, list) and len(node) > 1:
        i, j = rng.sample(range(len(node)), 2)
        node[i], node[j] = node[j], node[i]
    elif parent is None:
        tree = copy.deepcopy(rng.choice(_REPLACEMENTS))
    else:
        parent[key] = copy.deepcopy(rng.choice(_REPLACEMENTS))
    return cbor.dumps(tree)


def _mutate_bytes(data, rng):
    """`data` truncated, or with one byte changed, inserted, deleted or appended."""
    out = bytearray(data)
    move = rng.randrange(5)
    if move == 0:
        return bytes(out[:rng.randrange(len(out))])
    at = rng.randrange(len(out))
    if move == 1:
        out[at] = rng.randrange(256)
    elif move == 2:
        out.insert(at, rng.randrange(256))
    elif move == 3:
        del out[at]
    else:
        out.append(rng.randrange(256))
    return bytes(out)


def _drop_unknown(schema, t, value):
    """A decoded `value` without the unknown fields, at any depth, that a codec generated
    without forward-compat drops."""
    if isinstance(t, MsgRef):
        return {f.name: None if value[f.name] is None else _drop_unknown(schema, f.type, value[f.name])
                for f in schema.messages[t.name].wire_fields()}
    if isinstance(t, ListOf):
        return [_drop_unknown(schema, t.elem, v) for v in value]
    if isinstance(t, MapOf):
        return {k: _drop_unknown(schema, t.value, v) for k, v in value.items()}
    return value


def _beyond_row(fixture, name, stage, schema_name, data, **fields):
    """A malformed row expecting what Python, the reference, observes (`expect_dropping` when a
    codec that drops unknown fields re-encodes it otherwise), a bound's tag included; None for an
    accepted enum, which the gate never expects. `data` is the row's bytes, or its segments
    (CD-C2), which then carry their expanded `len`; `fields` adds a raw row's `limits`."""
    segmented = isinstance(data, list)
    row = {"name": name, "stage": stage, "schema": schema_name, "bytes": data if segmented else data.hex(),
           **fields}
    if segmented:
        row["len"] = len(parity.row_bytes(row))
    outcome, detail = parity._observe_python(fixture, row)
    assert outcome in (parity.OK, parity.ERR), (name, detail)
    if outcome == parity.ERR:
        tag, payload = parity.parse_error(detail)
        return {**row, "expect": {"tag": tag, **payload}}
    if stage == "from_wire":
        return None
    row["expect"] = {"accept": True, "reencode": detail}
    if stage == "from_cbor":
        kept = codec.decode(fixture, schema_name, parity.row_bytes(row))
        dropped = codec.encode(fixture, schema_name, _drop_unknown(fixture, MsgRef(schema_name), kept)).hex()
        if dropped != detail:
            row["expect_dropping"] = {"accept": True, "reencode": dropped}
    return row


def _with_repeated_key(fixture, message, tag, key, rng):
    """A `message` whose map field `tag` holds two entries with the key `key`."""
    field = next(f for f in fixture.messages[message].wire_fields() if f.tag == tag)
    value = _native(fixture, MsgRef(message), rng)
    value[field.name] = {key: _native(fixture, field.type.value, rng)}
    tree = cbor.loads(codec.encode(fixture, message, value))
    tree[tag].append(dict(tree[tag][0]))
    return cbor.dumps(tree)


@functools.cache
def _beyond_rows(per_message=36, randoms=60, seed=BEYOND_SEED):
    """Malformed rows beyond the shared corpus, for the gate's own runner and judge: question 9's
    repeated keys, CD-E5's raw edges, random bytes, the bounds a raw call passes, `per_message`
    random encodings of each fixture message (a third as they are, a third with a byte mutated,
    a third with a node), typed decodes of 100,000-deep input and bad enum values. The bounds
    fixture's random values are inside its bounds (`_native`); a mutation may cross one, and
    its row expects the bound's tag."""
    fixture = parity.parity_schema()
    rng = random.Random(seed)
    rows = []
    for i, (key, text) in enumerate(Q9_RAW):
        data = b"\xa2" + cbor.dumps(key) + cbor.dumps(0) + cbor.dumps(key) + cbor.dumps(1)
        rows.append({"name": f"beyond-q9-raw-{i}", "stage": "raw_decode", "schema": "", "bytes": data.hex(),
                     "expect": {"tag": "DuplicateMapKey", "key": text}})
    for i, (message, tag, key, text) in enumerate(Q9_FIELDS):
        data = _with_repeated_key(fixture, message, tag, key, rng)
        rows.append({"name": f"beyond-q9-{message}-{i}", "stage": "from_cbor", "schema": message,
                     "bytes": data.hex(), "expect": {"tag": "DuplicateMapKey", "key": text}})
    randoms_ = [bytes(rng.randrange(256) for _ in range(rng.randrange(1, 10))) for _ in range(randoms)]
    for i, data in enumerate([bytes.fromhex(h) for h in RAW_EDGES] + randoms_):
        rows.append(_beyond_row(fixture, f"beyond-raw-{i}", "raw_decode", "", data))
    for depth in DEPTH_ARGUMENTS:  # at the bound applied, and one beyond it
        applied = min(depth, cbor.MAX_DEPTH_CEILING)
        for beyond in (0, 1):
            data = bytes.fromhex("81" * (applied - 1 + beyond) + "80")
            rows.append(_beyond_row(fixture, f"beyond-depth-{depth}-{beyond}", "raw_decode", "", data,
                                    limits={"max_depth": depth}))
    for i, (hexed, limits) in enumerate(LIMIT_EDGES):
        rows.append(_beyond_row(fixture, f"beyond-limits-{i}", "raw_decode", "", bytes.fromhex(hexed),
                                limits=limits))
    for message in fixture.messages:
        for i in range(per_message):
            data = codec.encode(fixture, message, _native(fixture, MsgRef(message), rng))
            if i % 3:
                data = (_mutate_tree if i % 3 == 1 else _mutate_bytes)(data, rng)
            rows.append(_beyond_row(fixture, f"beyond-{message}-{i}", "from_cbor", message, data))
    for message, opener, _ in DEEP_ROOTS:
        rows.append(_beyond_row(fixture, f"beyond-deep-{message}", "from_cbor", message,
                                [{"repeat": opener, "count": 100_000}, "80"]))
    for enum in fixture.enums:
        for i, data in enumerate(bytes.fromhex(h) for h in ENUM_EDGES):
            rows.append(_beyond_row(fixture, f"beyond-{enum}-{i}", "from_wire", enum, data))
    return tuple(row for row in rows if row is not None)


def test_the_rows_beyond_the_corpus_state_what_python_the_reference_does():
    fixture = parity.parity_schema()
    rows = _beyond_rows()
    assert len({row["name"] for row in rows}) == len(rows)
    for row in rows:  # python keeps unknown fields: judged by `expect`
        assert parity.judge("python", row, *parity._observe_python(fixture, row)) == (parity.PASS, ""), row
    q9 = [row["expect"]["key"] for row in rows if row["name"].startswith("beyond-q9-")]
    assert q9 == [text for _, text in Q9_RAW] + [text for *_, text in Q9_FIELDS]
    # a mix: every fixture message accepted and refused at the schema stage, rows that a codec
    # dropping unknown fields re-encodes otherwise, and each decode tag
    typed = [row for row in rows if row["stage"] == "from_cbor"]
    assert {row["schema"] for row in typed if row["expect"].get("accept")} == set(fixture.messages)
    assert any("expect_dropping" in row for row in typed)
    tags = {row["expect"].get("tag") for row in rows}
    assert {"Truncated", "TrailingBytes", "InvalidUtf8", "UnsupportedInfo", "UnsupportedMajor",
            "NonIntegerMapKey", "NegativeMapKey", "DuplicateMapKey", "NonCanonicalInt", "IntOverflow",
            "WrongType", "MissingKey", "UnknownEnum", "TooDeep", "TooLarge"} <= tags
    refused = {row["schema"] for row in typed if row["expect"].get("tag") in ("WrongType", "MissingKey")}
    assert refused == set(fixture.messages)
    # the bounds: each depth argument applied as given up to the ceiling, the ceiling above it,
    # and a typed decode of deep input refused at its root's own bound
    applied = [(row["limits"]["max_depth"], row["expect"].get("tag", "accept"), row["expect"].get("limit"))
               for row in rows if row["name"].startswith("beyond-depth-")]
    assert applied == [(depth, tag, limit) for depth in DEPTH_ARGUMENTS
                       for tag, limit in (("accept", None), ("TooDeep", str(min(depth, 128))))]
    deep = {row["schema"]: row["expect"] for row in rows if row["name"].startswith("beyond-deep-")}
    assert deep == {message: {"tag": "TooDeep", "limit": str(bound)} for message, _, bound in DEEP_ROOTS}


def test_kotlin_matches_python_beyond_the_corpus(monkeypatch):
    """Every public decode entry point (raw `decode` with a raw row's limits, each fixture
    message's typed `decode` from bytes and the enum's `fromWire`) returns a value or throws
    DecodeError, with Python's tag and payload, on the rows beyond the corpus, question 9's
    repeated keys and the bounds among them: through the gate's own Kotlin runner and judge, as
    kotlin and as kotlin/fc. A runner reports anything else escaping as `untyped`, which fails
    its row. The JVM's own stdout here is ASCII, as on a host whose locale is: the runner still
    reports a str key such as `naïve` as itself."""
    allowlisted = parity.allowlisted_targets()
    if {"kotlin", "kotlin/fc"} & allowlisted:
        pytest.skip("kotlin is allowlisted (corpus/parity/allowlist.json): its runner is not held "
                    "to the rows")
    rows = list(_beyond_rows())
    monkeypatch.setattr(parity, "malformed_rows", lambda: rows)
    tool_options = os.environ.get("JAVA_TOOL_OPTIONS", "")
    monkeypatch.setenv("JAVA_TOOL_OPTIONS", f"{tool_options} -Dstdout.encoding=US-ASCII".strip())
    for forward_compat in (False, True):
        report = parity_kotlin.run(forward_compat=forward_compat)
        if not report.available:
            pytest.skip(report.skip_reason)
        assert not report.fault, report.fault
        assert [(r.name, r.detail) for r in report.failures] == [], report.target
        assert {r.name for r in report.results if r.kind == "malformed"} == {row["name"] for row in rows}
