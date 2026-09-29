"""Java runner for the parity gate (see `parity_rust.py` for the shape).

The generated classes in `api.java` are package-private in package `taut`, so the
runner is a class of that package too: javac compiles it with `api.java` and the
vendored `Cbor.java` and `Ext.java`, and a compile error is RED. The runner checks
the int rows itself and reports what each malformed row did; the gate judges it.
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

import java.util.LinkedHashMap;

public final class ParityRunner {
    private record IntRow(String name, String cbor, String n, String[] byId) {}
    private record EncFail(String name, String[] ints) {}
    private record Mal(String name, String stage, String schema, String bytes) {}

    // byId holds each by_id pair as two items, key then value.
    private static final IntRow[] ROUND_TRIP = {
@ROUND_TRIP@
    };
    // ints holds n and every by_id key and value.
    private static final EncFail[] ENCODE_FAIL = {
@ENCODE_FAIL@
    };
    private static final Mal[] MALFORMED = {
@MALFORMED@
    };

    private ParityRunner() {}

    public static void main(String[] args) {
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
        for (Mal row : MALFORMED) {
            try {
                decodeRow(row);
                emit(row.name(), "ok", "");
            } catch (Cbor.DecodeError e) {
                emit(row.name(), "err", describe(e));
            } catch (Throwable t) {
                emit(row.name(), "untyped", untyped(t));
            }
        }
        System.out.flush();
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
            decoded = IntBox.fromCbor(Cbor.decode(unhex(row.cbor())));
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

    private static void decodeRow(Mal row) {
        Cbor c = Cbor.decode(unhex(row.bytes()));
        switch (row.stage()) {
            case "raw_decode" -> {
            }
            case "from_cbor" -> fromCbor(row.schema(), c);
            case "from_wire" -> fromWire(row.schema(), c.asInt());
            default -> throw new IllegalStateException("unknown stage " + row.stage());
        }
    }

    // A from_cbor row's typed entry point, by message name (from the fixture schema).
    private static void fromCbor(String message, Cbor c) {
        switch (message) {
@FROM_CBOR@
            default -> throw new IllegalStateException("no from_cbor entry point for " + message);
        }
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

    private static void emit(String name, String outcome, String detail) {
        String clean = detail.replace('\t', ' ').replace('\n', ' ').replace('\r', ' ');
        System.out.println(name + "\t" + outcome + "\t" + clean);
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


def _tables() -> tuple[str, str, str]:
    round_trip, encode_fail, malformed = [], [], []
    for row in parity.int_rows():
        value = row["value"]
        by_id = [item for pair in value["by_id"] for item in pair]
        if row["kind"] == "round_trip":
            round_trip.append(f"        new IntRow({_java_str(row['name'])}, {_java_str(row['cbor'])}, "
                              f"{_java_str(value['n'])}, {_strings(by_id)}),")
        else:
            encode_fail.append(f"        new EncFail({_java_str(row['name'])}, "
                               f"{_strings([value['n'], *by_id])}),")
    for row in parity.malformed_rows():
        malformed.append(f"        new Mal({_java_str(row['name'])}, {_java_str(row['stage'])}, "
                         f"{_java_str(row.get('schema', ''))}, {_java_str(row['bytes'])}),")
    return "\n".join(round_trip), "\n".join(encode_fail), "\n".join(malformed)


def _dispatch() -> tuple[str, str]:
    """The `case` arms for every message (`from_cbor`) and enum (`from_wire`) in the fixture."""
    dispatch = parity.fixture_dispatch()
    from_cbor = [f"            case {_java_str(name)} -> {name}.fromCbor(c);" for name in dispatch.messages]
    from_wire = [f"            case {_java_str(name)} -> {name}.fromWire(v);" for name in dispatch.enums]
    return "\n".join(from_cbor), "\n".join(from_wire)


def _payload() -> str:
    """One `field(...)` per payload field, in report order. A field DecodeError lacks
    fails the build, so a new payload field cannot go unreported."""
    return "\n".join(f"        field(out, {_java_str(name)}, e.{_JAVA_FIELD.get(name, name)});"
                     for name in parity.PAYLOAD_FIELDS)


def _source() -> str:
    round_trip, encode_fail, malformed = _tables()
    from_cbor, from_wire = _dispatch()
    return (_RUNNER.lstrip("\n")
            .replace("@ROUND_TRIP@", round_trip)
            .replace("@ENCODE_FAIL@", encode_fail)
            .replace("@MALFORMED@", malformed)
            .replace("@FROM_CBOR@", from_cbor)
            .replace("@FROM_WIRE@", from_wire)
            .replace("@PAYLOAD@", _payload()))


def run() -> parity.TargetReport:
    tools = toolchains.find_java_tools()
    if tools is None:
        return parity.skipped(TARGET, "javac/java not found (JAVA_HOME, Android Studio's JBR, PATH)")
    javac, java = tools
    env = toolchains.java_env(java)
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        failed = parity.generate(TARGET, work, runtime=True)
        if failed is not None:
            return failed
        generated = work / TARGET
        runner = generated / f"{_CLASS}.java"
        runner.write_text(_source())
        sources = sorted(str(path) for path in generated.glob("*.java"))
        classes = work / "classes"
        classes.mkdir()
        failed = parity.build(TARGET, [javac, "-encoding", "UTF-8", "-d", str(classes), *sources],
                              cwd=work, env=env)
        if failed is not None:
            return failed
        return parity.run_runner(TARGET, [java, "-cp", str(classes), f"taut.{_CLASS}"], cwd=work, env=env)
