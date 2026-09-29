"""Kotlin runner for the parity gate (see `parity_rust.py` for the shape).

kotlinc is slow, so the gate compiles once: the generated `api.kt`, the vendored
runtime (`cbor.kt`, `ext.kt`) and the runner go into one jar, which java runs. Both
tools come from `toolchains.find_kotlin_tools` (on a Mac, Android Studio's). A
decoded malformed row reports the hex of its re-encoding: `encode` of the tree for
a raw row, of the typed value's `toCbor()` for a from_cbor row.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from . import parity, toolchains

TARGET = "kotlin"

_MAIN = r'''
package taut

private class IntRow(val name: String, val cbor: String, val n: String, val byId: List<Pair<String, String>>)
private class EncFail(val name: String, val value: String)
private class Mal(val name: String, val stage: String, val schema: String, val bytes: String)

private val ROUND_TRIP: List<IntRow> = listOf(
@ROUND_TRIP@
)
private val ENCODE_FAIL: List<EncFail> = listOf(
@ENCODE_FAIL@
)
private val MALFORMED: List<Mal> = listOf(
@MALFORMED@
)

private fun unhex(s: String): ByteArray {
    val out = ByteArray(s.length / 2)
    for (i in out.indices) {
        out[i] = s.substring(2 * i, 2 * i + 2).toInt(16).toByte()
    }
    return out
}

private fun hexOf(b: ByteArray): String {
    val out = StringBuilder(b.size * 2)
    for (x in b) {
        out.append(String.format("%02x", x.toInt() and 0xff))
    }
    return out.toString()
}

private fun emit(name: String, outcome: String, detail: String) {
    val flat = detail.replace('\t', ' ').replace('\n', ' ').replace('\r', ' ')
    println("$name\t$outcome\t$flat")
}

/** A from_cbor row's typed entry point, by message name (from the fixture schema): the decoded value's own encoding. */
private fun fromCbor(message: String, c: Cbor): ByteArray {
    return when (message) {
@FROM_CBOR@
        else -> {
            throw IllegalStateException("no from_cbor entry point for $message")
        }
    }
}

/** A from_wire row's typed entry point, by enum name (from the fixture schema). */
private fun fromWire(name: String, v: Long) {
    when (name) {
@FROM_WIRE@
        else -> {
            throw IllegalStateException("no from_wire entry point for $name")
        }
    }
}

/** A decoded row's re-encoding: the tree for raw_decode, the typed value for from_cbor, and nothing for from_wire. */
private fun decodeRow(row: Mal): ByteArray {
    val c = decode(unhex(row.bytes))
    return when (row.stage) {
        "raw_decode" -> {
            encode(c)
        }
        "from_cbor" -> {
            fromCbor(row.schema, c)
        }
        "from_wire" -> {
            fromWire(row.schema, c.intVal)
            ByteArray(0)
        }
        else -> {
            throw IllegalStateException("unknown stage ${row.stage}")
        }
    }
}

/**
 * An `err` detail: the tag, then `;field=value` for each payload field it carries.
 * Exhaustive on purpose: a new DecodeError variant fails the build until it is reported here.
 */
private fun describe(e: DecodeError): String = when (e) {
    is DecodeError.Truncated -> "Truncated"
    is DecodeError.TrailingBytes -> "TrailingBytes"
    is DecodeError.InvalidUtf8 -> "InvalidUtf8"
    is DecodeError.UnsupportedInfo -> "UnsupportedInfo;info=${e.info}"
    is DecodeError.UnsupportedMajor -> "UnsupportedMajor;major=${e.major}"
    is DecodeError.NonIntegerMapKey -> "NonIntegerMapKey"
    is DecodeError.IntOverflow -> "IntOverflow;value=${e.value}"
    is DecodeError.DuplicateMapKey -> "DuplicateMapKey;key=${e.key}"
    is DecodeError.MissingKey -> "MissingKey;key=${e.key}"
    is DecodeError.WrongType -> "WrongType;expected=${e.expected}"
    is DecodeError.UnknownEnum -> "UnknownEnum;enum=${e.enumName};value=${e.value}"
    is DecodeError.NonCanonicalInt -> "NonCanonicalInt;value=${e.value}"
    is DecodeError.NegativeMapKey -> "NegativeMapKey;key=${e.key}"
}

/** An int row's round trip: null when it holds, else what differed. */
private fun roundTrip(row: IntRow): String? {
    val byId = LinkedHashMap<Long, Long>()
    for ((k, v) in row.byId) {
        byId[k.toLong()] = v.toLong()
    }
    val built = IntBox(n = row.n.toLong(), by_id = byId)
    val enc = hexOf(encode(built.toCbor()))
    if (enc != row.cbor) {
        return "encode $enc != ${row.cbor}"
    }
    val decoded = IntBox.fromCbor(decode(unhex(row.cbor)))
    val re = hexOf(encode(decoded.toCbor()))
    if (decoded.n != row.n.toLong() || decoded.by_id != byId || re != row.cbor) {
        return "decoded n=${decoded.n} by_id=${decoded.by_id}, reencode $re"
    }
    return null
}

fun main() {
    for (row in ROUND_TRIP) {
        try {
            val failure = roundTrip(row)
            if (failure == null) {
                emit(row.name, "pass", "")
            } else {
                emit(row.name, "fail", failure)
            }
        } catch (e: Throwable) {
            emit(row.name, "fail", "threw ${e.javaClass.name}: ${e.message}")
        }
    }
    for (row in ENCODE_FAIL) {
        // Long is the encode-side subset guard: an out-of-subset value is
        // unrepresentable, so this is satisfied by the type system.
        if (row.value.toLongOrNull() == null) {
            emit(row.name, "type-satisfied", "unrepresentable in Long")
        } else {
            emit(row.name, "fail", "value fits Long but expected out-of-subset")
        }
    }
    for (row in MALFORMED) {
        try {
            val again = decodeRow(row)
            emit(row.name, "ok", hexOf(again))
        } catch (e: DecodeError) {
            emit(row.name, "err", describe(e))
        } catch (e: Throwable) {
            emit(row.name, "untyped", "${e.javaClass.name}: ${e.message}")
        }
    }
}
'''


def _kt(value: str) -> str:
    """A Kotlin string literal: `\\`, `"` and `$` (a template) escaped, and anything
    outside printable ASCII as UTF-16 `\\uXXXX` units."""
    out = []
    for ch in str(value):
        if ch in '\\"$':
            out.append("\\" + ch)
        elif " " <= ch <= "~":
            out.append(ch)
        else:
            units = ch.encode("utf-16-be")
            out.extend(f"\\u{units[i]:02x}{units[i + 1]:02x}" for i in range(0, len(units), 2))
    return '"' + "".join(out) + '"'


def _tables() -> tuple[str, str, str]:
    round_trip, encode_fail, malformed = [], [], []
    for row in parity.int_rows():
        if row["kind"] == "round_trip":
            pairs = ", ".join(f"Pair({_kt(k)}, {_kt(v)})" for k, v in row["value"]["by_id"])
            round_trip.append(f"    IntRow({_kt(row['name'])}, {_kt(row['cbor'])}, "
                              f"{_kt(row['value']['n'])}, listOf({pairs})),")
        else:
            encode_fail.append(f"    EncFail({_kt(row['name'])}, {_kt(row['value']['n'])}),")
    for row in parity.malformed_rows():
        malformed.append(f"    Mal({_kt(row['name'])}, {_kt(row['stage'])}, "
                         f"{_kt(row.get('schema', ''))}, {_kt(row['bytes'])}),")
    return "\n".join(round_trip), "\n".join(encode_fail), "\n".join(malformed)


def _dispatch() -> tuple[str, str]:
    """The `when` arms for every message (`from_cbor`) and enum (`from_wire`) in the fixture."""
    dispatch = parity.fixture_dispatch()
    from_cbor = [f"        {_kt(name)} -> {{\n            encode({name}.fromCbor(c).toCbor())\n        }}"
                 for name in dispatch.messages]
    from_wire = [f"        {_kt(name)} -> {{\n            {name}.fromWire(v)\n        }}"
                 for name in dispatch.enums]
    return "\n".join(from_cbor), "\n".join(from_wire)


def _source() -> str:
    round_trip, encode_fail, malformed = _tables()
    from_cbor, from_wire = _dispatch()
    return (_MAIN
            .replace("@ROUND_TRIP@", round_trip)
            .replace("@ENCODE_FAIL@", encode_fail)
            .replace("@MALFORMED@", malformed)
            .replace("@FROM_CBOR@", from_cbor)
            .replace("@FROM_WIRE@", from_wire))


def run() -> parity.TargetReport:
    tools = toolchains.find_kotlin_tools()
    if tools is None:
        return parity.skipped(TARGET, "kotlinc (and a java to run it) not found")
    kotlinc, java = tools
    env = toolchains.java_env(java)
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        failed = parity.generate(TARGET, work, runtime=True)
        if failed is not None:
            return failed
        runner = work / "ParityRunner.kt"
        runner.write_text(_source())
        sources = [str(p) for p in sorted((work / TARGET).glob("*.kt"))]
        jar = work / "parity_runner.jar"
        failed = parity.build(TARGET, [kotlinc, *sources, str(runner), "-include-runtime", "-d", str(jar)],
                              cwd=work, env=env)
        if failed is not None:
            return failed
        return parity.run_runner(TARGET, [java, "-jar", str(jar)], cwd=work, env=env)
