"""Kotlin runner for the parity gate (see `parity_rust.py` for the shape).

kotlinc is slow, so the gate compiles once: the generated `api.kt`, the vendored
runtime (`cbor.kt`, `ext.kt`) and the runner go into one jar, which java runs. Both
tools come from `toolchains.find_kotlin_tools` (on a Mac, Android Studio's). A
decoded malformed or bounds row reports the hex of its re-encoding: `encode` of the
tree for a raw row, of the typed value's `toCbor()` for a from_cbor row. The report
is UTF-8, so a payload's text (a str map key's, question 9) arrives as itself on any
platform.

It speaks the bounds protocol (`parity.py`'s docstring, C3): it prints `#constants`
from the runtime's own `DEFAULT_MAX_DEPTH` and `MAX_DEPTH_CEILING`; a raw row's call
passes the row's `limits`; a from_cbor row decodes from bytes through its message's
typed `decode`, which applies the message's generated `MAX_DEPTH` and
`MAX_ENCODED_LEN`, and its line adds them as a fourth column; and the table holds
each row's bytes as segments, which the runner expands and checks against `len`.
"""

from __future__ import annotations

import tempfile
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from . import parity, toolchains

TARGET = "kotlin"
# Kotlin's Int.MAX_VALUE. A row's bound above it is passed as it, which bounds the same: no
# ByteArray is longer, and a depth above the ceiling applies the ceiling.
_INT_MAX = 2**31 - 1

_MAIN = r'''
package taut

private class IntRow(val name: String, val cbor: String, val n: String, val byId: List<Pair<String, String>>)
private class EncFail(val name: String, val value: String)
// A malformed or bounds row. Its bytes are segments, each `hex` or `hex*count`, joined by `,`
// (a 100,000-deep row is 200 KB expanded, beyond a JVM string constant); `len` is their
// expanded length where the row states one. A raw row's `limits` are `maxDepth` and
// `maxEncodedLen`, null where its call passes none.
private class DecodeRow(
    val name: String,
    val stage: String,
    val schema: String,
    val segments: String,
    val len: Int?,
    val maxDepth: Int?,
    val maxEncodedLen: Int?,
)

private val ROUND_TRIP: List<IntRow> = listOf(
@ROUND_TRIP@
)
private val ENCODE_FAIL: List<EncFail> = listOf(
@ENCODE_FAIL@
)
private val DECODE_ROWS: List<DecodeRow> = listOf(
@DECODE_ROWS@
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

// A report line: its columns joined by tabs, with tabs and line breaks inside a column as spaces.
private fun emit(vararg columns: String) {
    println(columns.joinToString("\t") { it.replace('\t', ' ').replace('\n', ' ').replace('\r', ' ') })
}

// A row's input: its segments expanded. An expansion whose length is not the row's `len` is not
// the row's input; IllegalStateException reports it as untyped.
private fun expand(row: DecodeRow): ByteArray {
    val out = java.io.ByteArrayOutputStream()
    for (segment in row.segments.split(",")) {
        val bytes = unhex(segment.substringBefore("*"))
        val count = if (segment.contains("*")) {
            segment.substringAfter("*").toInt()
        } else {
            1
        }
        for (i in 0 until count) {
            out.write(bytes)
        }
    }
    val data = out.toByteArray()
    check(row.len == null || data.size == row.len) { "bytes expand to ${data.size} bytes, len is ${row.len}" }
    return data
}

// A bounds column: the bounds a typed entry point applies, the length empty for none.
private fun bounds(maxDepth: Int, maxEncodedLen: Int?): String =
    "max_depth=$maxDepth;max_encoded_len=${maxEncodedLen ?: ""}"

/** A from_cbor row's typed entry point, by message name (from the fixture schema): the value it decodes from bytes, under the message's own bounds, encoded again. */
private fun fromBytes(message: String, data: ByteArray): ByteArray {
    return when (message) {
@FROM_BYTES@
        else -> {
            throw IllegalStateException("no from_cbor entry point for $message")
        }
    }
}

/** The bounds a message's typed entry point applies: its generated MAX_DEPTH and MAX_ENCODED_LEN. */
private fun resolved(message: String): String {
    return when (message) {
@RESOLVED@
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

/** A decoded row's re-encoding: the tree for raw_decode, whose call passes the row's limits; the typed value for from_cbor; nothing for from_wire. */
private fun decodeRow(row: DecodeRow, data: ByteArray): ByteArray {
    return when (row.stage) {
        "raw_decode" -> {
            encode(decode(data, row.maxDepth ?: DEFAULT_MAX_DEPTH, row.maxEncodedLen))
        }
        "from_cbor" -> {
            fromBytes(row.schema, data)
        }
        "from_wire" -> {
            fromWire(row.schema, decode(data).intVal)
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
    is DecodeError.TooDeep -> "TooDeep;limit=${e.limit}"
    is DecodeError.TooLarge -> "TooLarge;len=${e.len};limit=${e.limit}"
}

/** An int row's round trip, through IntBox's typed entry point: null when it holds, else what differed. */
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
    val decoded = IntBox.decode(unhex(row.cbor))
    val re = hexOf(encode(decoded.toCbor()))
    if (decoded.n != row.n.toLong() || decoded.by_id != byId || re != row.cbor) {
        return "decoded n=${decoded.n} by_id=${decoded.by_id}, reencode $re"
    }
    return null
}

fun main() {
    // A payload is compared as text, a str map key's among them: report in UTF-8, whatever
    // the platform's default.
    System.setOut(java.io.PrintStream(java.io.FileOutputStream(java.io.FileDescriptor.out), true, "UTF-8"))
    // The runtime's own depth numbers, which the gate compares with the bounds header.
    emit("#constants", "default_max_depth=$DEFAULT_MAX_DEPTH;max_depth_ceiling=$MAX_DEPTH_CEILING")
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
    for (row in DECODE_ROWS) {
        // A from_cbor row's line adds the bounds its typed entry point applies.
        val applied: Array<String> = if (row.stage == "from_cbor") {
            arrayOf(resolved(row.schema))
        } else {
            arrayOf<String>()
        }
        try {
            val again = decodeRow(row, expand(row))
            emit(row.name, "ok", hexOf(again), *applied)
        } catch (e: DecodeError) {
            emit(row.name, "err", describe(e), *applied)
        } catch (e: Throwable) {
            emit(row.name, "untyped", "${e.javaClass.name}: ${e.message}", *applied)
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


def _kt_int(value: int | None) -> str:
    """A Kotlin `Int?` argument: null for none, and a value above Int's range as Int's largest."""
    return "null" if value is None else str(min(value, _INT_MAX))


def _segments(row: Mapping[str, Any]) -> str:
    """A row's bytes as the runner's table holds them (the bounds protocol, item 5): each
    segment `hex` or `hex*count`, joined by `,`, for the runner to expand."""
    return ",".join(hexed if count == 1 else f"{hexed}*{count}" for hexed, count in parity.segments(row))


def _tables() -> tuple[str, str, str]:
    round_trip, encode_fail, decode_rows = [], [], []
    for row in parity.int_rows():
        if row["kind"] == "round_trip":
            pairs = ", ".join(f"Pair({_kt(k)}, {_kt(v)})" for k, v in row["value"]["by_id"])
            round_trip.append(f"    IntRow({_kt(row['name'])}, {_kt(row['cbor'])}, "
                              f"{_kt(row['value']['n'])}, listOf({pairs})),")
        else:
            encode_fail.append(f"    EncFail({_kt(row['name'])}, {_kt(row['value']['n'])}),")
    for row in parity.decode_rows():
        limits = row.get("limits", {})
        decode_rows.append(f"    DecodeRow({_kt(row['name'])}, {_kt(row['stage'])}, "
                           f"{_kt(row.get('schema', ''))}, {_kt(_segments(row))}, {_kt_int(row.get('len'))}, "
                           f"{_kt_int(limits.get('max_depth'))}, {_kt_int(limits.get('max_encoded_len'))}),")
    return "\n".join(round_trip), "\n".join(encode_fail), "\n".join(decode_rows)


def _dispatch() -> tuple[str, str, str]:
    """The `when` arms for every message (`from_cbor`: its typed decode and its bounds) and
    enum (`from_wire`) in the fixture."""
    dispatch = parity.fixture_dispatch()
    from_bytes = [f"        {_kt(name)} -> {{\n            encode({name}.decode(data).toCbor())\n        }}"
                  for name in dispatch.messages]
    resolved = [f"        {_kt(name)} -> {{\n            bounds({name}.MAX_DEPTH, {name}.MAX_ENCODED_LEN)\n        }}"
                for name in dispatch.messages]
    from_wire = [f"        {_kt(name)} -> {{\n            {name}.fromWire(v)\n        }}"
                 for name in dispatch.enums]
    return "\n".join(from_bytes), "\n".join(resolved), "\n".join(from_wire)


def _source() -> str:
    round_trip, encode_fail, decode_rows = _tables()
    from_bytes, resolved, from_wire = _dispatch()
    return (_MAIN
            .replace("@ROUND_TRIP@", round_trip)
            .replace("@ENCODE_FAIL@", encode_fail)
            .replace("@DECODE_ROWS@", decode_rows)
            .replace("@FROM_BYTES@", from_bytes)
            .replace("@RESOLVED@", resolved)
            .replace("@FROM_WIRE@", from_wire))


def run(forward_compat: bool = False) -> parity.TargetReport:
    """The kotlin gate, or with `forward_compat` its `kotlin/fc` variant (`parity_rust.py`)."""
    name = parity.variant(TARGET, forward_compat)
    tools = toolchains.find_kotlin_tools()
    if tools is None:
        return parity.skipped(name, "kotlinc (and a java to run it) not found")
    kotlinc, java = tools
    env = toolchains.java_env(java)
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        failed = parity.generate(name, work, runtime=True)
        if failed is not None:
            return failed
        runner = work / "ParityRunner.kt"
        runner.write_text(_source())
        sources = [str(p) for p in sorted((work / TARGET).glob("*.kt"))]
        jar = work / "parity_runner.jar"
        failed = parity.build(name, [kotlinc, *sources, str(runner), "-include-runtime", "-d", str(jar)],
                              cwd=work, env=env)
        if failed is not None:
            return failed
        return parity.run_runner(name, [java, "-jar", str(jar)], cwd=work, env=env)
