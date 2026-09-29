"""Java runner for the parity gate (see `parity_rust.py` for the shape).

The generated classes in `api.java` are package-private in package `taut`, so the
runner is a class of that package too: javac compiles it with `api.java` and the
vendored `Cbor.java` and `Ext.java`, and a compile error is RED. The runner checks
the int rows itself and reports what each malformed or bounds row did, a decoded one
with the hex of its re-encoding (`Cbor.encode` of the tree for a raw row, of the typed
value's `toCbor()` for a from_cbor row); the gate judges it.

It speaks the bounds protocol (`parity.py`'s docstring): a `#constants` line from
`Cbor.DEFAULT_MAX_DEPTH` and `Cbor.MAX_DEPTH_CEILING`; a raw row's call passes its
`limits` to `Cbor.decode(data, maxDepth, maxEncodedLen)`; a from_cbor row decodes
through its message's typed `decode(byte[])`, and its line's fourth column is the
bounds that decode applies, the message's MAX_DEPTH and MAX_ENCODED_LEN. A row's bytes
are embedded as segments, which the runner expands and checks against the row's `len`.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from . import parity, toolchains

TARGET = "java"
_CLASS = "ParityRunner"
# A payload field whose DecodeError field has another name (Java reserves `enum`).
_JAVA_FIELD = {"enum": "enumName"}

_RUNNER = r'''
package taut;

import java.io.ByteArrayOutputStream;
import java.util.LinkedHashMap;

public final class ParityRunner {
    private record IntRow(String name, String cbor, String n, String[] byId) {}
    private record EncFail(String name, String[] ints) {}
    // A run of a row's bytes: `hex` repeated `count` times.
    private record Seg(String hex, int count) {}
    // A malformed or bounds row: its bytes as segments, which the runner expands (a
    // 100,000-deep row is beyond a Java string literal), and its `len`, the expanded length,
    // null where the row gives none. A raw row's call passes `maxDepth` and `maxEncodedLen`,
    // its `limits`, each null where it passes none.
    private record DecodeRow(String name, String stage, String schema, Seg[] bytes, Integer len,
                             Integer maxDepth, Integer maxEncodedLen) {}

    // byId holds each by_id pair as two items, key then value.
    private static final IntRow[] ROUND_TRIP = {
@ROUND_TRIP@
    };
    // ints holds n and every by_id key and value.
    private static final EncFail[] ENCODE_FAIL = {
@ENCODE_FAIL@
    };
    private static final DecodeRow[] DECODE = {
@DECODE@
    };

    private ParityRunner() {}

    public static void main(String[] args) {
        emit("#constants", "default_max_depth=" + Cbor.DEFAULT_MAX_DEPTH
                + ";max_depth_ceiling=" + Cbor.MAX_DEPTH_CEILING);
        for (IntRow row : ROUND_TRIP) {
            try {
                roundTrip(row);
            } catch (Throwable t) {
                emit(row.name(), "fail", "raised " + untyped(t));
            }
        }
        for (EncFail row : ENCODE_FAIL) {
            encodeFail(row);
        }
        for (DecodeRow row : DECODE) {
            String[] seen = observe(row);
            if (row.stage().equals("from_cbor")) {
                emit(row.name(), seen[0], seen[1], resolved(row.schema()));
            } else {
                emit(row.name(), seen[0], seen[1]);
            }
        }
        System.out.flush();
    }

    // What decoding a row did, as an outcome and its detail: `ok` and the hex of its
    // re-encoding, `err` and its DecodeError, or `untyped` and anything else, an expansion
    // whose length is not the row's `len` among them.
    private static String[] observe(DecodeRow row) {
        byte[] data = expand(row.bytes());
        if (row.len() != null && data.length != row.len()) {
            return new String[] {"untyped", "bytes expand to " + data.length + " bytes, len is " + row.len()};
        }
        try {
            return new String[] {"ok", hex(decodeRow(row, data))};
        } catch (Cbor.DecodeError e) {
            return new String[] {"err", describe(e)};
        } catch (Throwable t) {
            return new String[] {"untyped", untyped(t)};
        }
    }

    private static byte[] expand(Seg[] segs) {
        ByteArrayOutputStream out = new ByteArrayOutputStream();
        for (Seg seg : segs) {
            byte[] run = unhex(seg.hex());
            for (int i = 0; i < seg.count(); i++) {
                out.write(run, 0, run.length);
            }
        }
        return out.toByteArray();
    }

    private static void roundTrip(IntRow row) {
        IntBox built = new IntBox();
        built.n = Long.parseLong(row.n());
        built.by_id = new LinkedHashMap<>();
        for (int i = 0; i < row.byId().length; i += 2) {
            built.by_id.put(Long.parseLong(row.byId()[i]), Long.parseLong(row.byId()[i + 1]));
        }
        String enc = hex(Cbor.encode(built.toCbor()));
        if (!enc.equals(row.cbor())) {
            emit(row.name(), "fail", "encode " + enc + " != " + row.cbor());
            return;
        }
        IntBox decoded;
        try {
            decoded = IntBox.decode(unhex(row.cbor()));
        } catch (Cbor.DecodeError e) {
            emit(row.name(), "fail", "decode " + describe(e));
            return;
        }
        String re = hex(Cbor.encode(decoded.toCbor()));
        if (decoded.n == built.n && decoded.by_id.equals(built.by_id) && re.equals(row.cbor())) {
            emit(row.name(), "pass", "");
        } else {
            emit(row.name(), "fail", "reencode " + re);
        }
    }

    private static void encodeFail(EncFail row) {
        for (String value : row.ints()) {
            try {
                Long.parseLong(value);
            } catch (NumberFormatException e) {
                // long is the encode-side subset guard: an out-of-subset value is
                // unrepresentable, so the type system satisfies this row.
                emit(row.name(), "type-satisfied", "unrepresentable in long");
                return;
            }
        }
        emit(row.name(), "fail", "value fits long but expected out-of-subset");
    }

    // A decoded row's re-encoding: the tree for raw_decode, the typed value for
    // from_cbor, and nothing for from_wire (an enum row never accepts).
    private static byte[] decodeRow(DecodeRow row, byte[] data) {
        switch (row.stage()) {
            case "raw_decode" -> {
                return Cbor.encode(raw(row, data));
            }
            case "from_cbor" -> {
                return typed(row.schema(), data);
            }
            case "from_wire" -> {
                fromWire(row.schema(), Cbor.decode(data).asInt());
                return new byte[0];
            }
            default -> throw new IllegalStateException("unknown stage " + row.stage());
        }
    }

    // A raw row's call: the default overload when it passes no limits, else the raw decode
    // with them, at the default depth where it passes none.
    private static Cbor raw(DecodeRow row, byte[] data) {
        if (row.maxDepth() == null && row.maxEncodedLen() == null) {
            return Cbor.decode(data);
        }
        int maxDepth = row.maxDepth() == null ? Cbor.DEFAULT_MAX_DEPTH : row.maxDepth();
        return Cbor.decode(data, maxDepth, row.maxEncodedLen());
    }

    // A from_cbor row's typed entry point, by message name (from the fixture schema): the
    // message's decode from bytes, under its bounds, and the decoded value's own encoding.
    private static byte[] typed(String message, byte[] data) {
        switch (message) {
@TYPED@
            default -> throw new IllegalStateException("no typed entry point for " + message);
        }
    }

    // A from_cbor row's fourth column, by message name: the bounds its typed entry point
    // applies, the message's generated constants.
    private static String resolved(String message) {
        switch (message) {
@RESOLVED@
            default -> throw new IllegalStateException("no typed entry point for " + message);
        }
    }

    private static String bounds(int maxDepth, Integer maxEncodedLen) {
        return "max_depth=" + maxDepth + ";max_encoded_len=" + (maxEncodedLen == null ? "" : maxEncodedLen);
    }

    // A from_wire row's typed entry point, by enum name (from the fixture schema).
    private static void fromWire(String name, long v) {
        switch (name) {
@FROM_WIRE@
            default -> throw new IllegalStateException("no from_wire entry point for " + name);
        }
    }

    // An `err` detail: the tag, then `;field=value` for each payload field it carries.
    private static String describe(Cbor.DecodeError e) {
        StringBuilder out = new StringBuilder(e.tag.name());
@PAYLOAD@
        return out.toString();
    }

    private static void field(StringBuilder out, String name, Object value) {
        if (value != null) {
            out.append(';').append(name).append('=').append(value);
        }
    }

    private static String untyped(Throwable t) {
        return t.getClass().getName() + ": " + t.getMessage();
    }

    // One report line: its columns, tab-separated, with any tab or line break inside a
    // column made a space.
    private static void emit(String... columns) {
        StringBuilder line = new StringBuilder();
        for (int i = 0; i < columns.length; i++) {
            if (i > 0) {
                line.append('\t');
            }
            line.append(columns[i].replace('\t', ' ').replace('\n', ' ').replace('\r', ' '));
        }
        System.out.println(line);
    }

    private static byte[] unhex(String text) {
        byte[] out = new byte[text.length() / 2];
        for (int i = 0; i < out.length; i++) {
            out[i] = (byte) Integer.parseInt(text.substring(2 * i, 2 * i + 2), 16);
        }
        return out;
    }

    private static String hex(byte[] bytes) {
        StringBuilder out = new StringBuilder(bytes.length * 2);
        for (byte b : bytes) {
            out.append(Character.forDigit((b >> 4) & 0xf, 16)).append(Character.forDigit(b & 0xf, 16));
        }
        return out.toString();
    }
}
'''


def _java_str(value: object) -> str:
    """A Java string literal. JSON's escapes are Java's, and JSON writes a quote, a
    backslash or a line break with a short escape, never the unicode escape that javac
    would translate before it reads the literal."""
    return json.dumps(str(value))


def _strings(values: list[object]) -> str:
    return "new String[] {" + ", ".join(_java_str(v) for v in values) + "}"


def _segments(row: dict) -> str:
    """A row's bytes as the runner embeds them, a `Seg` per segment (the bounds protocol,
    item 5): the runner expands them, so no literal holds a 100,000-deep row."""
    return "new Seg[] {" + ", ".join(f"new Seg({_java_str(hexed)}, {count})"
                                     for hexed, count in parity.segments(row)) + "}"


def _nullable(value: int | None) -> str:
    """An `Integer` argument: the int, or null for none."""
    return "null" if value is None else str(value)


def _tables() -> tuple[str, str, str]:
    round_trip, encode_fail, decode = [], [], []
    for row in parity.int_rows():
        value = row["value"]
        by_id = [item for pair in value["by_id"] for item in pair]
        if row["kind"] == "round_trip":
            round_trip.append(f"        new IntRow({_java_str(row['name'])}, {_java_str(row['cbor'])}, "
                              f"{_java_str(value['n'])}, {_strings(by_id)}),")
        else:
            encode_fail.append(f"        new EncFail({_java_str(row['name'])}, "
                               f"{_strings([value['n'], *by_id])}),")
    for row in parity.decode_rows():
        limits = row.get("limits", {})
        decode.append(f"        new DecodeRow({_java_str(row['name'])}, {_java_str(row['stage'])}, "
                      f"{_java_str(row.get('schema', ''))}, {_segments(row)}, "
                      f"{_nullable(row.get('len'))}, {_nullable(limits.get('max_depth'))}, "
                      f"{_nullable(limits.get('max_encoded_len'))}),")
    return "\n".join(round_trip), "\n".join(encode_fail), "\n".join(decode)


def _dispatch() -> tuple[str, str, str]:
    """The `case` arms for every message and enum in the fixture: each message's typed entry
    point, `decode` from bytes (from_cbor), and the bounds it applies, and each enum's
    `fromWire` (from_wire)."""
    dispatch = parity.fixture_dispatch()
    typed = [f"            case {_java_str(name)} -> {{\n"
             f"                return Cbor.encode({name}.decode(data).toCbor());\n"
             "            }" for name in dispatch.messages]
    resolved = [f"            case {_java_str(name)} -> {{\n"
                f"                return bounds({name}.MAX_DEPTH, {name}.MAX_ENCODED_LEN);\n"
                "            }" for name in dispatch.messages]
    from_wire = [f"            case {_java_str(name)} -> {name}.fromWire(v);" for name in dispatch.enums]
    return "\n".join(typed), "\n".join(resolved), "\n".join(from_wire)


def _payload() -> str:
    """One `field(...)` per payload field, in report order. A field DecodeError lacks
    fails the build, so a new payload field cannot go unreported."""
    return "\n".join(f"        field(out, {_java_str(name)}, e.{_JAVA_FIELD.get(name, name)});"
                     for name in parity.PAYLOAD_FIELDS)


def _source() -> str:
    round_trip, encode_fail, decode = _tables()
    typed, resolved, from_wire = _dispatch()
    return (_RUNNER.lstrip("\n")
            .replace("@ROUND_TRIP@", round_trip)
            .replace("@ENCODE_FAIL@", encode_fail)
            .replace("@DECODE@", decode)
            .replace("@TYPED@", typed)
            .replace("@RESOLVED@", resolved)
            .replace("@FROM_WIRE@", from_wire)
            .replace("@PAYLOAD@", _payload()))


def run(forward_compat: bool = False) -> parity.TargetReport:
    """The java gate, or with `forward_compat` its `java/fc` variant (`parity_rust.py`)."""
    name = parity.variant(TARGET, forward_compat)
    tools = toolchains.find_java_tools()
    if tools is None:
        return parity.skipped(name, "javac/java not found (JAVA_HOME, Android Studio's JBR, PATH)")
    javac, java = tools
    env = toolchains.java_env(java)
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        failed = parity.generate(name, work, runtime=True)
        if failed is not None:
            return failed
        generated = work / TARGET
        runner = generated / f"{_CLASS}.java"
        runner.write_text(_source())
        sources = sorted(str(path) for path in generated.glob("*.java"))
        classes = work / "classes"
        classes.mkdir()
        failed = parity.build(name, [javac, "-encoding", "UTF-8", "-d", str(classes), *sources],
                              cwd=work, env=env)
        if failed is not None:
            return failed
        return parity.run_runner(name, [java, "-cp", str(classes), f"taut.{_CLASS}"], cwd=work, env=env)
