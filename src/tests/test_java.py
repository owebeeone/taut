"""Java generator/runtime coverage."""

import json
import os
import random
import shutil
import subprocess
import textwrap
from pathlib import Path

import pytest

from taut import cli, ext
from taut.corpus import resext_build as rb
from taut.corpus.build import IR_PATH
from taut.gen import java
from taut.ir.dsl import FLOAT, INT, F, List as TList, Map, Msg, schema as mk
from taut.ir.load import load_schema
from taut.ir.shapes import BAND_START
from taut.wire import cbor, codec

RAZEL = load_schema(IR_PATH.parent / "razel.taut.py")
RESEXT = load_schema(rb.IR_PATH)
ROOT = Path(__file__).resolve().parents[2]
EXT_JAVA = ROOT / "src" / "taut" / "gen" / "runtime" / "Ext.java"
PARITY_IR = ROOT / "ir" / "parity_int.taut.py"
PARITY_INT = ROOT / "corpus" / "parity" / "int.vectors.json"
PARITY_MALFORMED = ROOT / "corpus" / "parity" / "malformed.vectors.json"
FUZZ_SEED = 55004
FUZZ_ITERS = 1000
FLOATY = mk(Msg("Floaty",
                F("x", 1, FLOAT),
                F("maybe", 2, FLOAT, optional=True),
                F("xs", 3, TList(FLOAT)),
                F("by_id", 4, Map(INT, FLOAT))))


def _tool_pair_candidates():
    def pair(home: Path):
        return home / "bin" / "javac", home / "bin" / "java"

    if os.environ.get("JAVA_HOME"):
        yield pair(Path(os.environ["JAVA_HOME"]))
    yield pair(Path("/Applications/Android Studio.app/Contents/jbr/Contents/Home"))
    javac = shutil.which("javac")
    java_bin = shutil.which("java")
    if javac and java_bin:
        yield Path(javac), Path(java_bin)


def _find_java_tools() -> tuple[str, str]:
    attempted = []
    for javac, java_bin in _tool_pair_candidates():
        if not javac.is_file() or not java_bin.is_file():
            attempted.append(f"{javac} / {java_bin} (missing)")
            continue
        try:
            subprocess.run([str(javac), "-version"], check=True, capture_output=True, text=True)
            subprocess.run([str(java_bin), "-version"], check=True, capture_output=True, text=True)
        except (OSError, subprocess.CalledProcessError) as exc:
            attempted.append(f"{javac} / {java_bin} ({exc})")
            continue
        return str(javac), str(java_bin)
    pytest.skip("Java toolchain unavailable: " + "; ".join(attempted))


def _hex_rows(path: Path, rows: list[list[str]]) -> None:
    path.write_text("\n".join("\t".join(row) for row in rows) + "\n")


def _rand_text(rng: random.Random) -> str:
    alphabet = "abcdefghijklmnopqrstuvwxyz0123456789"
    return "".join(rng.choice(alphabet) for _ in range(rng.randint(0, 8)))


def _rand_cbor_value(rng: random.Random, depth: int = 0):
    choices = ["int", "str", "bytes", "bool", "null"]
    if depth == 0:
        choices.append("arr")
    kind = rng.choice(choices)
    if kind == "int":
        return rng.randint(-1000, 1000)
    if kind == "str":
        return _rand_text(rng)
    if kind == "bytes":
        return bytes(rng.randrange(256) for _ in range(rng.randint(0, 5)))
    if kind == "bool":
        return bool(rng.randrange(2))
    if kind == "arr":
        return [_rand_cbor_value(rng, depth + 1) for _ in range(rng.randint(0, 3))]
    return None


def _fuzz_rows() -> list[list[str]]:
    rng = random.Random(FUZZ_SEED)
    rows = []
    tag = BAND_START + 1
    for i in range(FUZZ_ITERS):
        host_map = {
            1: rng.randint(0, 10_000),
            2: _rand_text(rng),
            5: rng.randint(-1000, 1000),
            3: _rand_cbor_value(rng),                         # interleaved unknown
            BAND_START + 2 + rng.randrange(BAND_START - 2): _rand_cbor_value(rng),
        }
        for _ in range(2):
            unknown = rng.randrange(0, 1 << 21)
            if unknown not in (1, 2, 5, tag):
                host_map[unknown] = _rand_cbor_value(rng)
        if i % 7 == 0:
            host_map[tag] = codec.encode_struct(
                RESEXT, "Decision", {"backend": _rand_text(rng), "hops": rng.randint(0, 20)}
            )
        host = cbor.dumps(host_map)
        decision = {"backend": _rand_text(rng), "hops": rng.randint(0, 20)}
        value_hex = codec.encode(RESEXT, "Decision", decision).hex()
        set_bytes = ext.ext_set(RESEXT, host, "Decision", tag, decision)
        got = ext.ext_get(RESEXT, set_bytes, "Decision", tag)
        rows.append([
            host.hex(),
            value_hex,
            set_bytes.hex(),
            codec.encode(RESEXT, "Decision", got).hex(),
            ext.ext_clear(set_bytes, tag).hex(),
        ])
    return rows


def _write_resext_inputs(tmp_path: Path) -> tuple[Path, Path, Path]:
    residual = tmp_path / "residual.tsv"
    ext_vectors = tmp_path / "ext.tsv"
    fuzz = tmp_path / "fuzz.tsv"
    _hex_rows(residual, [[r["note"], r["wire"]] for r in json.loads(rb.RESIDUAL_PATH.read_text())])
    _hex_rows(ext_vectors, [[
        r["op"],
        r["note"],
        r["host"],
        str(r["tag"]),
        r.get("value", "-"),
        r["expect"],
    ] for r in json.loads(rb.EXT_PATH.read_text())])
    _hex_rows(fuzz, _fuzz_rows())
    return residual, ext_vectors, fuzz


def _write_parity_inputs(tmp_path: Path) -> tuple[Path, Path]:
    int_rows = tmp_path / "parity-int.tsv"
    malformed_rows = tmp_path / "parity-malformed.tsv"

    # Baseline smoke test: pin the reviewed set; `lead` rows belong to the
    # governed `tautc parity` gate (corpus/parity/gen_vectors.py).
    int_data = json.loads(PARITY_INT.read_text())
    rows = []
    for row in [r for r in int_data["vectors"] if not r.get("lead")]:
        value = row["value"]
        by_id = ";".join(f"{k}={v}" for k, v in value.get("by_id", [])) or "-"
        rows.append([
            row["kind"],
            row["name"],
            value["n"],
            by_id,
            row.get("cbor", "-"),
            row.get("expect", {}).get("tag", "-"),
        ])
    _hex_rows(int_rows, rows)

    malformed_data = json.loads(PARITY_MALFORMED.read_text())
    rows = []
    for row in [r for r in malformed_data["vectors"] if not r.get("lead")]:
        expect = row["expect"]
        rows.append([
            row["name"],
            row["stage"],
            row.get("schema", "-"),
            row["bytes"],
            expect["tag"],
            str(expect.get("key", "-")),
            str(expect.get("expected", "-")),
            str(expect.get("enum", "-")),
            str(expect.get("value", "-")),
            str(expect.get("info", "-")),
            str(expect.get("major", "-")),
        ])
    _hex_rows(malformed_rows, rows)
    return int_rows, malformed_rows


def _generate_resext_java(tmp_path: Path) -> Path:
    out = tmp_path / "generated"
    rc = cli.main([
        "gen",
        str(rb.IR_PATH),
        "-o",
        str(out),
        "-l",
        "java",
        "--api-only",
        "--with-runtime",
        "--forward-compat",
    ])
    assert rc == 0
    java_dir = out / "java"
    assert (java_dir / "api.java").is_file()
    assert (java_dir / "Cbor.java").is_file()
    assert (java_dir / "Ext.java").is_file()
    return java_dir


def _generate_parity_java(tmp_path: Path) -> Path:
    out = tmp_path / "parity-generated"
    rc = cli.main([
        "gen",
        str(PARITY_IR),
        "-o",
        str(out),
        "-l",
        "java",
        "--api-only",
        "--with-runtime",
    ])
    assert rc == 0
    java_dir = out / "java"
    assert (java_dir / "api.java").is_file()
    assert (java_dir / "Cbor.java").is_file()
    return java_dir


PARITY_HARNESS = r"""
package taut;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.LinkedHashMap;
import java.util.Map;

public final class JavaParityCorpus {
    private static int roundTripRows = 0;
    private static int encodeFailRows = 0;
    private static int malformedRows = 0;

    public static void main(String[] args) throws Exception {
        runInt(Path.of(args[0]));
        runMalformed(Path.of(args[1]));
        System.out.println("ok round_trip=" + roundTripRows
                + " encode_fail=" + encodeFailRows
                + " malformed=" + malformedRows
                + " mismatches=0");
    }

    private static void runInt(Path path) throws Exception {
        for (String line : Files.readAllLines(path)) {
            if (line.isBlank()) continue;
            String[] row = line.split("\t", -1);
            String kind = row[0];
            String name = row[1];
            String n = row[2];
            if (kind.equals("round_trip")) {
                IntBox box = new IntBox();
                box.n = Long.parseLong(n);
                box.by_id = parseMap(row[3]);
                checkHex(Cbor.encode(box.toCbor()), row[4], "encode " + name);

                IntBox decoded = IntBox.fromCbor(Cbor.decode(fromHex(row[4])));
                check(decoded.n == box.n, "decode n " + name);
                check(decoded.by_id.equals(box.by_id), "decode map " + name);
                checkHex(Cbor.encode(decoded.toCbor()), row[4], "re-encode " + name);
                roundTripRows++;
            } else if (kind.equals("encode_fail")) {
                expectNumberFormat(() -> Long.parseLong(n), "encode_fail native guard " + name);
                encodeFailRows++;
            } else {
                throw new AssertionError("unknown int vector kind " + kind);
            }
        }
    }

    private static void runMalformed(Path path) throws Exception {
        for (String line : Files.readAllLines(path)) {
            if (line.isBlank()) continue;
            String[] row = line.split("\t", -1);
            String name = row[0];
            String stage = row[1];
            String schema = row[2];
            byte[] bytes = fromHex(row[3]);
            if (stage.equals("raw_decode")) {
                expectDecode(() -> Cbor.decode(bytes), row, name);
            } else if (stage.equals("from_cbor") && schema.equals("IntBox")) {
                Cbor c = Cbor.decode(bytes);
                expectDecode(() -> IntBox.fromCbor(c), row, name);
            } else if (stage.equals("from_wire") && schema.equals("Mode")) {
                long wire = Cbor.decode(bytes).asInt();
                expectDecode(() -> Mode.fromWire(wire), row, name);
            } else {
                throw new AssertionError("unsupported malformed vector " + name);
            }
            malformedRows++;
        }
    }

    private static Map<Long, Long> parseMap(String text) {
        Map<Long, Long> out = new LinkedHashMap<>();
        if (text.equals("-")) return out;
        for (String item : text.split(";")) {
            String[] pair = item.split("=", -1);
            out.put(Long.parseLong(pair[0]), Long.parseLong(pair[1]));
        }
        return out;
    }

    private static void expectDecode(CheckedRunnable fn, String[] row, String name) {
        try {
            fn.run();
        } catch (Cbor.DecodeError err) {
            checkError(err, row, name);
            return;
        }
        throw new AssertionError(name + " did not throw DecodeError");
    }

    private static void checkError(Cbor.DecodeError err, String[] row, String name) {
        String tag = row[4];
        check(err.tag.name().equals(tag), name + " tag " + err.tag + " expected " + tag);
        if (!row[5].equals("-")) check(err.key != null && err.key == Long.parseLong(row[5]), name + " key");
        if (!row[6].equals("-")) check(row[6].equals(err.expected), name + " expected type");
        if (!row[7].equals("-")) check(row[7].equals(err.enumName), name + " enum");
        if (!row[8].equals("-")) check(row[8].equals(err.value), name + " value");
        if (!row[9].equals("-")) check(err.info != null && err.info == Integer.parseInt(row[9]), name + " info");
        if (!row[10].equals("-")) check(err.major != null && err.major == Integer.parseInt(row[10]), name + " major");
    }

    private static void expectNumberFormat(CheckedRunnable fn, String label) {
        try {
            fn.run();
        } catch (NumberFormatException ok) {
            return;
        }
        throw new AssertionError(label + " did not reject out-of-long value");
    }

    private static void checkHex(byte[] got, String expect, String label) {
        check(toHex(got).equals(expect), label + " got " + toHex(got) + " expected " + expect);
    }

    private static void check(boolean ok, String msg) {
        if (!ok) throw new AssertionError(msg);
    }

    private static byte[] fromHex(String hex) {
        byte[] out = new byte[hex.length() / 2];
        for (int i = 0; i < out.length; i++) {
            out[i] = (byte) Integer.parseInt(hex.substring(i * 2, i * 2 + 2), 16);
        }
        return out;
    }

    private static String toHex(byte[] bytes) {
        StringBuilder out = new StringBuilder(bytes.length * 2);
        for (byte b : bytes) out.append(String.format("%02x", b & 0xff));
        return out.toString();
    }

    private interface CheckedRunnable {
        void run();
    }
}
"""


RESEXT_HARNESS = r"""
package taut;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Arrays;
import java.util.List;

public final class ResExtParity {
    private static final long TAG = 1048577L;
    private static int residualRows = 0;
    private static int extRows = 0;
    private static int fuzzRows = 0;

    public static void main(String[] args) throws Exception {
        runResidual(Path.of(args[0]));
        runExt(Path.of(args[1]));
        runFuzz(Path.of(args[2]));
        runInvalidCases();
        System.out.println("ok residual=" + residualRows + " ext=" + extRows
                + " fuzz=" + fuzzRows + " seed=" + args[3] + " mismatches=0");
    }

    private static void runResidual(Path path) throws Exception {
        for (String line : Files.readAllLines(path)) {
            if (line.isBlank()) continue;
            String[] row = line.split("\t", -1);
            String note = row[0];
            byte[] wire = fromHex(row[1]);
            Host host = Host.fromCbor(Cbor.decode(wire));
            byte[] got = Cbor.encode(host.toCbor());
            check(Arrays.equals(got, wire), "residual " + note + " got " + toHex(got));
            residualRows++;
        }
    }

    private static void runExt(Path path) throws Exception {
        for (String line : Files.readAllLines(path)) {
            if (line.isBlank()) continue;
            String[] row = line.split("\t", -1);
            String op = row[0];
            String note = row[1];
            byte[] host = fromHex(row[2]);
            long tag = Long.parseLong(row[3]);
            String value = row[4];
            String expect = row[5];
            if (op.equals("set")) {
                Decision decision = Decision.fromCbor(Cbor.decode(fromHex(value)));
                byte[] got = Ext.extSet(host, tag, decision.toCbor());
                checkHex(got, expect, "ext set " + note);
                Decision round = Decision.fromCbor(Ext.extGet(got, tag));
                checkHex(Cbor.encode(round.toCbor()), value, "ext set/get typed " + note);
            } else if (op.equals("get")) {
                Cbor got = Ext.extGet(host, tag);
                if (expect.equals("null")) {
                    check(got == null, "ext get absent " + note);
                } else {
                    Decision decision = Decision.fromCbor(got);
                    checkHex(Cbor.encode(decision.toCbor()), expect, "ext get " + note);
                }
            } else if (op.equals("clear")) {
                checkHex(Ext.extClear(host, tag), expect, "ext clear " + note);
            } else {
                throw new AssertionError("unknown op " + op);
            }
            extRows++;
        }
    }

    private static void runFuzz(Path path) throws Exception {
        for (String line : Files.readAllLines(path)) {
            if (line.isBlank()) continue;
            String[] row = line.split("\t", -1);
            byte[] hostBytes = fromHex(row[0]);
            String valueHex = row[1];
            Host host = Host.fromCbor(Cbor.decode(hostBytes));
            checkHex(Cbor.encode(host.toCbor()), row[0], "fuzz residual " + fuzzRows);

            Decision decision = Decision.fromCbor(Cbor.decode(fromHex(valueHex)));
            byte[] set = Ext.extSet(hostBytes, TAG, decision.toCbor());
            checkHex(set, row[2], "fuzz set " + fuzzRows);

            Decision got = Decision.fromCbor(Ext.extGet(set, TAG));
            checkHex(Cbor.encode(got.toCbor()), row[3], "fuzz get " + fuzzRows);
            checkHex(Ext.extClear(set, TAG), row[4], "fuzz clear " + fuzzRows);
            fuzzRows++;
        }
    }

    private static void runInvalidCases() {
        expectIllegalArgument(() -> Ext.extSet(new byte[0], 5L, Cbor.NUL), "set below band");
        expectIllegalArgument(() -> Ext.extGet(new byte[0], 5L), "get below band");
        expectIllegalArgument(() -> Ext.extClear(new byte[0], 5L), "clear below band");

        byte[] scalar = new byte[] {1};
        expectIllegalArgument(() -> Ext.extSet(scalar, TAG, Cbor.NUL), "set scalar host");
        expectIllegalArgument(() -> Ext.extGet(scalar, TAG), "get scalar host");
        expectIllegalArgument(() -> Ext.extClear(scalar, TAG), "clear scalar host");

        byte[] set = Ext.extSet(fromHex("a0"), TAG, Cbor.NUL);
        checkHex(set, "a11a00100001f6", "valid above-band set");
        check(Ext.extGet(set, TAG) != null, "valid above-band get");
        checkHex(Ext.extClear(set, TAG), "a0", "valid above-band clear");
    }

    private static void expectIllegalArgument(CheckedRunnable fn, String label) {
        try {
            fn.run();
        } catch (IllegalArgumentException ok) {
            return;
        } catch (Exception exc) {
            throw new AssertionError(label + " threw wrong exception " + exc);
        }
        throw new AssertionError(label + " did not throw");
    }

    private static void checkHex(byte[] got, String expect, String label) {
        check(toHex(got).equals(expect), label + " got " + toHex(got) + " expected " + expect);
    }

    private static void check(boolean ok, String msg) {
        if (!ok) throw new AssertionError(msg);
    }

    private static byte[] fromHex(String hex) {
        byte[] out = new byte[hex.length() / 2];
        for (int i = 0; i < out.length; i++) {
            out[i] = (byte) Integer.parseInt(hex.substring(i * 2, i * 2 + 2), 16);
        }
        return out;
    }

    private static String toHex(byte[] bytes) {
        StringBuilder out = new StringBuilder(bytes.length * 2);
        for (byte b : bytes) out.append(String.format("%02x", b & 0xff));
        return out.toString();
    }

    private interface CheckedRunnable {
        void run() throws Exception;
    }
}
"""


PUBLIC_ACCESS = r"""
package publiccheck;

import taut.Cbor;
import taut.Ext;

public final class PublicExtAccess {
    public static void main(String[] args) {
        byte[] host = new byte[] {(byte) 0xa0};
        byte[] set = Ext.extSet(host, 1048577L, Cbor.NUL);
        Cbor got = Ext.extGet(set, 1048577L);
        if (got == null) throw new AssertionError("public extGet returned null");
        byte[] cleared = Ext.extClear(set, 1048577L);
        if (cleared.length != 1 || (cleared[0] & 0xff) != 0xa0) {
            throw new AssertionError("public extClear mismatch");
        }
    }
}
"""


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
    assert "v.x = c.get(1).asFloat();" in s
    assert "v.maybe = f.isNull() ? null : f.asFloat();" in s
    assert "c.get(3).asArray().stream().map(e -> e.asFloat()).toList()" in s
    assert "e -> e.get(2).asFloat()" in s


def test_forward_compat_residual():
    s = java.emit_types(RAZEL, forward_compat=True)
    assert "public java.util.List<KV> wireResidual" in s
    assert "wireResidual" not in java.emit_types(RAZEL)  # off by default


def test_ext_runtime_public_api_source_shape():
    src = EXT_JAVA.read_text()
    assert "package taut;" in src
    assert "public final class Ext" in src
    assert "private Ext() {}" in src
    assert "public static byte[] extSet(byte[] host, long tag, Cbor value)" in src
    assert "public static Cbor extGet(byte[] host, long tag)" in src
    assert "public static byte[] extClear(byte[] host, long tag)" in src
    assert src.index("checkTag(tag);") < src.index("decodeHostMap(host);")
    assert "root.kind != Cbor.MAP" in src


def test_java_i64_fail_closed_shared_parity_corpus(tmp_path):
    javac, java_bin = _find_java_tools()
    java_dir = _generate_parity_java(tmp_path)
    int_rows, malformed_rows = _write_parity_inputs(tmp_path)

    harness = java_dir / "JavaParityCorpus.java"
    harness.write_text(textwrap.dedent(PARITY_HARNESS).strip() + "\n")

    classes = tmp_path / "classes"
    classes.mkdir()
    subprocess.run([
        javac,
        "-d",
        str(classes),
        str(java_dir / "Cbor.java"),
        str(java_dir / "api.java"),
        str(harness),
    ], check=True, cwd=ROOT, capture_output=True, text=True)

    parity = subprocess.run([
        java_bin,
        "-cp",
        str(classes),
        "taut.JavaParityCorpus",
        str(int_rows),
        str(malformed_rows),
    ], check=True, cwd=ROOT, capture_output=True, text=True)
    assert "round_trip=7" in parity.stdout
    assert "encode_fail=3" in parity.stdout
    assert "malformed=12" in parity.stdout
    assert "mismatches=0" in parity.stdout


def test_java_resext_runtime_parity_invalid_cases_public_access_and_fuzz(tmp_path):
    javac, java_bin = _find_java_tools()
    java_dir = _generate_resext_java(tmp_path)
    residual, ext_vectors, fuzz = _write_resext_inputs(tmp_path)

    harness = java_dir / "ResExtParity.java"
    harness.write_text(textwrap.dedent(RESEXT_HARNESS).strip() + "\n")
    public_dir = tmp_path / "publiccheck"
    public_dir.mkdir()
    public_access = public_dir / "PublicExtAccess.java"
    public_access.write_text(textwrap.dedent(PUBLIC_ACCESS).strip() + "\n")

    classes = tmp_path / "classes"
    classes.mkdir()
    subprocess.run([
        javac,
        "-d",
        str(classes),
        str(java_dir / "Cbor.java"),
        str(java_dir / "Ext.java"),
        str(java_dir / "api.java"),
        str(harness),
    ], check=True, cwd=ROOT, capture_output=True, text=True)

    parity = subprocess.run([
        java_bin,
        "-cp",
        str(classes),
        "taut.ResExtParity",
        str(residual),
        str(ext_vectors),
        str(fuzz),
        str(FUZZ_SEED),
    ], check=True, cwd=ROOT, capture_output=True, text=True)
    assert "residual=4" in parity.stdout
    assert "ext=5" in parity.stdout
    assert f"fuzz={FUZZ_ITERS}" in parity.stdout
    assert f"seed={FUZZ_SEED}" in parity.stdout
    assert "mismatches=0" in parity.stdout

    subprocess.run([
        javac,
        "-cp",
        str(classes),
        "-d",
        str(classes),
        str(public_access),
    ], check=True, cwd=ROOT, capture_output=True, text=True)
    public_run = subprocess.run([
        java_bin,
        "-cp",
        str(classes),
        "publiccheck.PublicExtAccess",
    ], check=True, cwd=ROOT, capture_output=True, text=True)
    assert public_run.returncode == 0
