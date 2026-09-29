"""Java generator/runtime coverage."""

import json
import os
import random
import re
import shutil
import subprocess
import textwrap
from pathlib import Path

import pytest

from taut import cli, ext
from taut.corpus import parity, parity_java
from taut.corpus import resext_build as rb
from taut.corpus.build import IR_PATH
from taut.gen import java, scaffold
from taut.ir import options
from taut.ir.dsl import (
    BOOL, BYTES, FLOAT, INT, MISSING_OK, STR, Enum, F, List as TList, Map, Msg, Ref, option,
    schema as mk,
)
from taut.ir.load import load_schema
from taut.ir.shapes import BAND_START
from taut.wire import cbor, codec

RAZEL = load_schema(IR_PATH.parent / "razel.taut.py")
RESEXT = load_schema(rb.IR_PATH)
ROOT = Path(__file__).resolve().parents[2]
EXT_JAVA = ROOT / "src" / "taut" / "gen" / "runtime" / "Ext.java"
FUZZ_SEED = 55004
FUZZ_ITERS = 1000
FLOATY = mk(Msg("Floaty",
                F("x", 1, FLOAT),
                F("maybe", 2, FLOAT, optional=True),
                F("xs", 3, TList(FLOAT)),
                F("by_id", 4, Map(INT, FLOAT))))
# MISSING_OK reads an absent key as null; plain optional still requires the key.
MISSING_OK_SCHEMA = mk(Msg("Late", F("note", 1, STR, optional=MISSING_OK)),
                       Msg("Opt", F("note", 1, STR, optional=True)))
# Lists nest and a map may sit in a list, so one field's codec can hold a lambda in a
# lambda (the parity fixture's Shapes.grid is list<list<int>>); a map value may be a
# message. SHAPES_HARNESS decodes NESTED_VALUE's bytes and re-encodes them, and builds
# a Keyed whose maps get their keys in the order below.
SHAPES = mk(Msg("Leaf", F("n", 1, INT)),
            Msg("Nested",
                F("grid", 1, TList(TList(INT))),
                F("cube", 2, TList(TList(TList(STR)))),
                F("tallies", 3, TList(Map(STR, INT))),
                F("leaves", 4, TList(TList(Map(INT, Ref("Leaf"))))),
                F("maybe_grid", 5, TList(TList(INT)), optional=True)),
            Msg("Keyed",
                F("by_text", 1, Map(STR, INT)),
                F("by_int", 2, Map(INT, INT)),
                F("by_flag", 3, Map(BOOL, INT))))
NESTED_VALUE = {"grid": [[1, -2], [], [3]],
                "cube": [[["a"], []], [], [["b", "c"]]],
                "tallies": [{"b": 2, "a": 1}, {}],
                "leaves": [[{2: {"n": 2}, 1: {"n": 1}}], []],
                "maybe_grid": [[], [7]]}
# A map field's entries are sorted by key: an int or bool key by value, a str key by
# Unicode code point, which is the order of its UTF-8 bytes (Python's `sorted`). UTF-16
# code unit order (String.compareTo) puts a key above U+FFFF, whose surrogate pair
# starts d800-dbff, before one in U+E000..U+FFFF. Each key's value is its position here.
TEXT_KEYS = ["\U0010ffff", "\uffff", "a\U00010000", "\U0001f600", "", "\ue000", "ab",
             "\U00010000", "a", "\ud7ff", "a\uffff", "\u00e9"]
INT_KEYS = [10, -1, 0, -300, 7]
BOOL_KEYS = [True, False]
KEYED_VALUE = {"by_text": {k: i for i, k in enumerate(TEXT_KEYS)},
               "by_int": {k: i for i, k in enumerate(INT_KEYS)},
               "by_flag": {k: i for i, k in enumerate(BOOL_KEYS)}}
# SHAPES_HARNESS's arguments after the Nested bytes: the keys, comma-separated, a str
# key as the hex of its UTF-8.
KEY_ARGS = [",".join(k.encode().hex() for k in TEXT_KEYS),
            ",".join(str(k) for k in INT_KEYS),
            ",".join(str(k).lower() for k in BOOL_KEYS)]
# Java reads a name in an expression as a variable before a class and a class before a
# package, so a field hides whatever shares its name wherever its class's code calls
# through that name. Names (ir/parity_int.taut.py) holds the locals and parameters the nine
# generators declared; Clash's fields are also named like what the Java codec resolves:
# the runtime's and java.util's classes, the packages, the message's own type and its
# fields' types, the members it calls (the typed `decode` and its constant's type among
# them), and Java's contextual keywords, which can name a field. Lists nest and a map holds
# messages, so lambdas nest too.
CLASH = mk(Enum("Mode", ok=0, alt=1),
           Msg("Leaf", F("n", 1, INT)),
           Msg("Clash",
               F("m", 1, INT), F("c", 2, STR), F("v", 3, INT), F("f", 4, INT, optional=True),
               F("e", 5, TList(TList(INT))), F("e1", 6, INT), F("kv", 7, INT), F("w", 8, INT),
               F("Cbor", 9, INT), F("KV", 10, INT), F("ArrayList", 11, TList(STR)),
               F("Arrays", 12, Map(INT, INT)), F("TreeMap", 13, Map(BOOL, Ref("Mode"))),
               F("java", 14, Map(STR, Ref("Leaf"))), F("taut", 15, INT),
               F("Clash", 16, INT, optional=MISSING_OK), F("Mode", 17, Ref("Mode")),
               F("Leaf", 18, Ref("Leaf")), F("List", 19, TList(Ref("Leaf"))),
               F("Map", 20, Map(INT, Ref("Leaf")), optional=True), F("String", 21, STR),
               F("Long", 22, INT), F("Boolean", 23, BOOL), F("Double", 24, FLOAT),
               F("Object", 25, BYTES), F("toCbor", 26, INT), F("fromCbor", 27, INT),
               F("fromWire", 28, INT), F("wire", 29, INT), F("values", 30, INT),
               F("var", 31, INT), F("record", 32, INT), F("yield", 33, INT),
               F("decode", 34, INT), F("Integer", 35, INT)))
CLASH_VALUE = {"m": 1, "c": "c", "v": -3, "f": None, "e": [[1, 2], []], "e1": 6, "kv": 7, "w": 8,
               "Cbor": 9, "KV": 10, "ArrayList": ["a", "b"], "Arrays": {12: -12, -1: 1},
               "TreeMap": {True: "alt", False: "ok"}, "java": {"b": {"n": 2}, "a": {"n": 1}},
               "taut": 15, "Clash": None, "Mode": "alt", "Leaf": {"n": 18}, "List": [{"n": 19}],
               "Map": {20: {"n": 20}}, "String": "s", "Long": -22, "Boolean": True, "Double": 1.5,
               "Object": b"\x00\x01", "toCbor": 26, "fromCbor": 27, "fromWire": 28, "wire": 29,
               "values": 30, "var": 31, "record": 32, "yield": 33, "decode": 34, "Integer": 35}
# Messages named like java.util's classes, which an import of one would clash with, and a
# field named `java`, the package the codec spells them with. Between them they hold each
# shape whose code names a java.util class: a list, lists in a list, and a map with each
# kind of key.
UTIL_NAMES = mk(Msg("ArrayList", F("n", 1, INT)),
                Msg("Arrays", F("items", 1, TList(Ref("ArrayList")))),
                Msg("TreeMap", F("by_id", 1, Map(INT, Ref("Arrays")))),
                Msg("List", F("tally", 1, Map(STR, INT)), F("flags", 2, Map(BOOL, INT))),
                Msg("Map", F("java", 1, TList(TList(INT))), F("list", 2, Ref("List")),
                    F("tree", 3, Ref("TreeMap"), optional=True)))
UTIL_NAMES_VALUE = {"java": [[1, 2], []],
                    "list": {"tally": {"b": 2, "a": 1}, "flags": {True: 1, False: 0}},
                    "tree": {"by_id": {2: {"items": [{"n": 1}]}, 1: {"items": []}}}}
# Question 9: a DecodeError's key is text. Each KEY_ROWS row is a label and its bytes; a
# `typed` row decodes a Keys, whose map fields hold an int, a str and a bool key.
KEYS = mk(Msg("Keys", F("by_int", 1, Map(INT, INT)), F("by_text", 2, Map(STR, INT)),
              F("by_flag", 3, Map(BOOL, INT))))
# The bounds (D26, TautCheckedDecode.md §3; D27, TautOptions.md OPT-D3, OPT-D4). FILED declares
# both at file level, and its Tree overrides the depth (test_bounds.py's). Each message's
# (MAX_DEPTH, MAX_ENCODED_LEN) is its effective values, None for no length bound; the parity
# fixture declares no file-level bound, so its other messages resolve to (32, None).
FILED = mk(option.max_depth(3), option.max_encoded_len(16),
           Msg("Tree", F("kids", 1, TList(Ref("Tree"))), option.max_depth(64), next_id=2),
           Msg("Plain", F("v", 1, TList(INT)), next_id=2))
FILED_BOUNDS = {"Tree": (64, 16), "Plain": (3, 16)}
FIXTURE_BOUNDS = {"Tree64": (64, None), "Tree128": (128, None), "Flat2": (2, None),
                  "Sized8": (32, 8), "Holds64": (32, None), "HoldsSized8": (32, None),
                  "IntBox": (32, None), "Empty": (32, None)}


def _twice(key) -> list[dict]:
    """A map<K,V> field's entries holding `key` twice."""
    return [{1: key, 2: 0}, {1: key, 2: 1}]


KEY_ROWS = {
    "raw-duplicate": "a205000501",
    "raw-negative": "a12000",
    "typed-missing": cbor.dumps({1: [], 2: []}).hex(),
    "typed-int": cbor.dumps({1: _twice(-(1 << 63)), 2: [], 3: []}).hex(),
    "typed-text": cbor.dumps({1: [], 2: _twice("\u00e9 k"), 3: []}).hex(),
    "typed-false": cbor.dumps({1: [], 2: [], 3: _twice(False)}).hex(),
    "typed-true": cbor.dumps({1: [], 2: [], 3: _twice(True)}).hex(),
}
# The fail-closed fuzz (CD-E4): mutants of the parity rows' bytes and random bytes. A
# replaced byte is often one that starts an item of another type.
FAIL_CLOSED_SEED = 26030
FAIL_CLOSED_MUTANTS = 3000
FAIL_CLOSED_RANDOM = 600
ITEM_STARTS = [0x00, 0x17, 0x18, 0x1b, 0x20, 0x3b, 0x40, 0x5b, 0x60, 0x61, 0x7b, 0x80, 0x81, 0x9b,
               0xa0, 0xa1, 0xbb, 0xc0, 0xf4, 0xf5, 0xf6, 0xf7, 0xf9, 0xfa, 0xfb, 0xff]


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


def _nest(opener: str, count: int, leaf: str) -> bytes:
    """`count` copies of the hex `opener`, then the hex `leaf`, as bytes."""
    return bytes.fromhex(opener * count + leaf)


# Input nested far beyond every bound (CD-B1): 100,000 arrays, maps, the two alternating, trees
# as the fixture's Tree64 nests them, and arrays whose items never come.
DEEP_INPUTS = [_nest(opener, 100_000, leaf) for opener, leaf in (
    ("81", "80"), ("a100", "a0"), ("81a100", "80"), ("a10181", "a10180"), ("81", ""))]


def _fail_closed_inputs() -> list[bytes]:
    """The parity rows' bytes, seeded mutants of them, random bytes, the bounds rows' bytes
    and DEEP_INPUTS: depth is bounded (D1), so no input is deeper than a Java stack holds."""
    rng = random.Random(FAIL_CLOSED_SEED)
    seeds = [bytes.fromhex(r["bytes"]) for r in parity.malformed_rows()]
    seeds += [bytes.fromhex(r["cbor"]) for r in parity.int_rows() if r["kind"] == "round_trip"]
    inputs = [*seeds, *(parity.row_bytes(r) for r in parity.bounds_rows()), *DEEP_INPUTS]
    for _ in range(FAIL_CLOSED_MUTANTS):
        data = bytearray(rng.choice(seeds))
        for _ in range(rng.randint(1, 4)):
            at = rng.randrange(len(data) + 1)
            op = rng.choices(["set", "flip", "insert", "cut"], weights=[4, 3, 2, 1])[0]
            if op == "set" and at < len(data):
                data[at] = rng.choice(ITEM_STARTS) if rng.randrange(2) else rng.randrange(256)
            elif op == "flip" and at < len(data):
                data[at] ^= 1 << rng.randrange(8)
            elif op == "insert":
                data.insert(at, rng.choice(ITEM_STARTS))
            else:
                del data[at:]
        inputs.append(bytes(data))
    for _ in range(FAIL_CLOSED_RANDOM):
        inputs.append(bytes(rng.randrange(256) for _ in range(rng.randrange(33))))
    return inputs


def _run_harness(work: Path, schema, harness: str, source: str, args: list[str], *,
                 forward_compat: bool = False) -> str:
    """`schema`'s Java code, its runtime and the class `harness` (`source`) built by one
    javac and run with `args`: what the harness prints, read as UTF-8."""
    javac, java_bin = _find_java_tools()
    scaffold.emit(schema, work, langs=["java"], services=[], runtime=True,
                  forward_compat=forward_compat)
    java_dir = work / "java"
    (java_dir / f"{harness}.java").write_text(textwrap.dedent(source).strip() + "\n")
    classes = work / "classes"
    classes.mkdir()
    sources = sorted(str(path) for path in java_dir.glob("*.java"))
    build = subprocess.run([javac, "-encoding", "UTF-8", "-d", str(classes), *sources],
                           cwd=work, capture_output=True, text=True)
    assert build.returncode == 0, build.stdout + build.stderr
    run = subprocess.run([java_bin, "-Dstdout.encoding=UTF-8", "-cp", str(classes),
                          f"taut.{harness}", *args], cwd=work, capture_output=True, encoding="utf-8")
    assert run.returncode == 0, run.stdout + run.stderr
    return run.stdout


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

        // A host that is not a map is WrongType{map}, and a malformed one its own tag
        // (CD-E4); the band is checked first, as a caller error, whatever the host.
        byte[] scalar = new byte[] {1};
        expectDecodeError(() -> Ext.extSet(scalar, TAG, Cbor.NUL), "set scalar host", "WrongType;expected=map");
        expectDecodeError(() -> Ext.extGet(scalar, TAG), "get scalar host", "WrongType;expected=map");
        expectDecodeError(() -> Ext.extClear(scalar, TAG), "clear scalar host", "WrongType;expected=map");
        byte[] list = fromHex("80");
        expectDecodeError(() -> Ext.extGet(list, TAG), "get array host", "WrongType;expected=map");
        byte[] torn = fromHex("a101");
        expectDecodeError(() -> Ext.extSet(torn, TAG, Cbor.NUL), "set torn host", "Truncated");
        expectDecodeError(() -> Ext.extGet(torn, TAG), "get torn host", "Truncated");
        expectDecodeError(() -> Ext.extClear(torn, TAG), "clear torn host", "Truncated");
        expectIllegalArgument(() -> Ext.extGet(scalar, 5L), "get below band, scalar host");

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

    // `fn` throws DecodeError whose tag, and `expected` when it has one, read `want`.
    private static void expectDecodeError(CheckedRunnable fn, String label, String want) {
        try {
            fn.run();
        } catch (Cbor.DecodeError e) {
            String got = e.tag.name() + (e.expected == null ? "" : ";expected=" + e.expected);
            check(got.equals(want), label + " threw " + got + ", expected " + want);
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


MISSING_OK_HARNESS = r"""
package taut;

import java.util.function.Supplier;

public final class MissingOkHarness {
    public static void main(String[] args) {
        decode("late-absent", () -> Late.fromCbor(Cbor.decode(unhex("a0"))).note);
        decode("late-null", () -> Late.fromCbor(Cbor.decode(unhex("a101f6"))).note);
        decode("late-text", () -> Late.fromCbor(Cbor.decode(unhex("a1016178"))).note);
        decode("late-wrong-type", () -> Late.fromCbor(Cbor.decode(unhex("a10101"))).note);
        decode("late-not-map", () -> Late.fromCbor(Cbor.decode(unhex("00"))).note);
        decode("opt-absent", () -> Opt.fromCbor(Cbor.decode(unhex("a0"))).note);
        decode("opt-null", () -> Opt.fromCbor(Cbor.decode(unhex("a101f6"))).note);
        System.out.println("late-unset-encode\t" + hex(Cbor.encode(new Late().toCbor())));
    }

    private static void decode(String name, Supplier<String> note) {
        String result;
        try {
            String value = note.get();
            result = value == null ? "null" : "text:" + value;
        } catch (Cbor.DecodeError e) {
            result = e.tag.name();
            if (e.key != null) {
                result += ";key=" + e.key;
            }
            if (e.expected != null) {
                result += ";expected=" + e.expected;
            }
        }
        System.out.println(name + "\t" + result);
    }

    private static byte[] unhex(String text) {
        byte[] out = new byte[text.length() / 2];
        for (int i = 0; i < out.length; i++) {
            out[i] = (byte) Integer.parseInt(text.substring(2 * i, 2 * i + 2), 16);
        }
        return out;
    }

    private static String hex(byte[] bytes) {
        StringBuilder out = new StringBuilder();
        for (byte b : bytes) {
            out.append(String.format("%02x", b & 0xff));
        }
        return out.toString();
    }
}
"""


SHAPES_HARNESS = r"""
package taut;

import java.nio.charset.StandardCharsets;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.function.Function;

public final class ShapesHarness {
    // args[0]: the hex of a Nested value's bytes, decoded and then re-encoded.
    // args[1], args[2] and args[3]: Keyed's str, int and bool keys (KEY_ARGS).
    public static void main(String[] args) {
        Nested nested = Nested.fromCbor(Cbor.decode(unhex(args[0])));
        System.out.println("nested\t" + hex(Cbor.encode(nested.toCbor())));
        Keyed keyed = new Keyed();
        keyed.by_text = positions(args[1], key -> new String(unhex(key), StandardCharsets.UTF_8));
        keyed.by_int = positions(args[2], Long::parseLong);
        keyed.by_flag = positions(args[3], Boolean::parseBoolean);
        System.out.println("keyed\t" + hex(Cbor.encode(keyed.toCbor())));
    }

    // The comma-separated `keys`, read by `parse`, each mapped to its position.
    private static <K> Map<K, Long> positions(String keys, Function<String, K> parse) {
        Map<K, Long> out = new LinkedHashMap<>();
        for (String key : keys.split(",", -1)) {
            out.put(parse.apply(key), (long) out.size());
        }
        return out;
    }

    private static byte[] unhex(String text) {
        byte[] out = new byte[text.length() / 2];
        for (int i = 0; i < out.length; i++) {
            out[i] = (byte) Integer.parseInt(text.substring(2 * i, 2 * i + 2), 16);
        }
        return out;
    }

    private static String hex(byte[] bytes) {
        StringBuilder out = new StringBuilder();
        for (byte b : bytes) {
            out.append(String.format("%02x", b & 0xff));
        }
        return out.toString();
    }
}
"""


ROUND_TRIP_HARNESS = r"""
package taut;

public final class RoundTripHarness {
    // args[0]: the hex of a @MESSAGE@ value's bytes, decoded by its typed decode and then
    // re-encoded.
    public static void main(String[] args) {
        @MESSAGE@ value = @MESSAGE@.decode(unhex(args[0]));
        System.out.println(hex(Cbor.encode(value.toCbor())));
    }

    private static byte[] unhex(String text) {
        byte[] out = new byte[text.length() / 2];
        for (int i = 0; i < out.length; i++) {
            out[i] = (byte) Integer.parseInt(text.substring(2 * i, 2 * i + 2), 16);
        }
        return out;
    }

    private static String hex(byte[] bytes) {
        StringBuilder out = new StringBuilder();
        for (byte b : bytes) {
            out.append(String.format("%02x", b & 0xff));
        }
        return out.toString();
    }
}
"""


KEY_TEXT_HARNESS = r"""
package taut;

public final class KeyTextHarness {
    // args: a label, then the hex of its bytes, for each row; a `typed` row decodes a Keys.
    public static void main(String[] args) {
        for (int i = 0; i < args.length; i += 2) {
            String outcome;
            try {
                Cbor tree = Cbor.decode(unhex(args[i + 1]));
                if (args[i].startsWith("typed")) {
                    Keys.fromCbor(tree);
                }
                outcome = "ok";
            } catch (Cbor.DecodeError e) {
                String key = e.key;
                outcome = e.tag.name() + ";key=" + key;
            }
            System.out.println(args[i] + "\t" + outcome);
        }
    }

    private static byte[] unhex(String text) {
        byte[] out = new byte[text.length() / 2];
        for (int i = 0; i < out.length; i++) {
            out[i] = (byte) Integer.parseInt(text.substring(2 * i, 2 * i + 2), 16);
        }
        return out;
    }
}
"""


FAIL_CLOSED_HARNESS = r"""
package taut;

import java.nio.file.Files;
import java.nio.file.Path;

public final class FailClosedHarness {
    private static final long TAG = 1048577L;
    private static int escapes = 0;

    private interface Entry {
        void run(byte[] data);
    }

    // args[0]: a file of inputs, the hex of one on each line, each fed to every entry point.
    public static void main(String[] args) throws Exception {
        int inputs = 0;
        for (String line : Files.readAllLines(Path.of(args[0]))) {
            byte[] data = unhex(line);
            check("decode", line, data, d -> Cbor.decode(d));
            check("decodeAtCeiling", line, data, d -> Cbor.decode(d, Cbor.MAX_DEPTH_CEILING, null));
@ENTRIES@
            check("extGet", line, data, d -> Ext.extGet(d, TAG));
            check("extSet", line, data, d -> Ext.extSet(d, TAG, Cbor.NUL));
            check("extClear", line, data, d -> Ext.extClear(d, TAG));
            inputs++;
        }
        System.out.println("inputs=" + inputs + " escapes=" + escapes);
    }

    // Prints anything but DecodeError that escapes `entry` on `input`.
    private static void check(String entry, String input, byte[] data, Entry fn) {
        try {
            fn.run(data);
        } catch (Cbor.DecodeError expected) {
            return;
        } catch (Throwable t) {
            escapes++;
            System.out.println(entry + "\t" + input + "\t" + t);
        }
    }

    private static byte[] unhex(String text) {
        byte[] out = new byte[text.length() / 2];
        for (int i = 0; i < out.length; i++) {
            out[i] = (byte) Integer.parseInt(text.substring(2 * i, 2 * i + 2), 16);
        }
        return out;
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


# The bounds harnesses' shared helpers: a DecodeError as `parity.format_error` writes one
# (Java names `enum` `enumName`), and hex both ways. Each harness reports an outcome as `ok:`
# and the hex of an encoding, or that text.
BOUNDS_HELPERS = r"""
    // A DecodeError as the gate writes one: its tag, then `;field=value` for each payload
    // field it carries.
    private static String describe(Cbor.DecodeError e) {
        StringBuilder out = new StringBuilder(e.tag.name());
        field(out, "info", e.info);
        field(out, "major", e.major);
        field(out, "key", e.key);
        field(out, "expected", e.expected);
        field(out, "enum", e.enumName);
        field(out, "value", e.value);
        field(out, "len", e.len);
        field(out, "limit", e.limit);
        return out.toString();
    }

    private static void field(StringBuilder out, String name, Object value) {
        if (value != null) {
            out.append(';').append(name).append('=').append(value);
        }
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
"""


RAW_BOUNDS_HARNESS = r"""
package taut;

import java.nio.file.Files;
import java.nio.file.Path;

public final class RawBoundsHarness {
    // args[0]: a file of calls, `label<TAB>hex<TAB>maxDepth<TAB>maxEncodedLen` on each line,
    // `-` for a bound the call leaves out. First the runtime's two depth numbers.
    public static void main(String[] args) throws Exception {
        System.out.println("constants\t" + Cbor.DEFAULT_MAX_DEPTH + ";" + Cbor.MAX_DEPTH_CEILING);
        for (String line : Files.readAllLines(Path.of(args[0]))) {
            String[] call = line.split("\t", -1);
            byte[] data = unhex(call[1]);
            Integer maxDepth = call[2].equals("-") ? null : Integer.valueOf(call[2]);
            Integer maxEncodedLen = call[3].equals("-") ? null : Integer.valueOf(call[3]);
            String outcome;
            try {
                outcome = "ok:" + hex(Cbor.encode(decode(data, maxDepth, maxEncodedLen)));
            } catch (Cbor.DecodeError e) {
                outcome = describe(e);
            } catch (IllegalArgumentException e) {
                outcome = "IllegalArgumentException";
            } catch (Throwable t) {
                outcome = "untyped:" + t;
            }
            System.out.println(call[0] + "\t" + outcome);
        }
    }

    // The default overload for a call that passes no bound, else the raw decode with the
    // default depth where the call passes none.
    private static Cbor decode(byte[] data, Integer maxDepth, Integer maxEncodedLen) {
        if (maxDepth == null && maxEncodedLen == null) {
            return Cbor.decode(data);
        }
        return Cbor.decode(data, maxDepth == null ? Cbor.DEFAULT_MAX_DEPTH : maxDepth, maxEncodedLen);
    }
@HELPERS@
}
"""


TYPED_BOUNDS_HARNESS = r"""
package taut;

import java.nio.file.Files;
import java.nio.file.Path;

public final class TypedBoundsHarness {
    private static final String[] MESSAGES = {@MESSAGES@};

    // args[0]: a file of inputs, `label<TAB>hex` on each line, each decoded through every
    // message's typed decode. Then each message's two constants.
    public static void main(String[] args) throws Exception {
        for (String line : Files.readAllLines(Path.of(args[0]))) {
            String[] input = line.split("\t", -1);
            byte[] data = unhex(input[1]);
            for (String message : MESSAGES) {
                String outcome;
                try {
                    outcome = "ok:" + hex(decode(message, data));
                } catch (Cbor.DecodeError e) {
                    outcome = describe(e);
                } catch (Throwable t) {
                    outcome = "untyped:" + t;
                }
                System.out.println(input[0] + " " + message + "\t" + outcome);
            }
        }
@CONSTANTS@
    }

    // The message's typed decode, then the encoding of the value it decoded.
    private static byte[] decode(String message, byte[] data) {
        switch (message) {
@DISPATCH@
            default -> throw new IllegalStateException("no message " + message);
        }
    }
@HELPERS@
}
"""


EXT_BOUNDS_HARNESS = r"""
package taut;

import java.nio.file.Files;
import java.nio.file.Path;

public final class ExtBoundsHarness {
    private static final long TAG = 1048577L;

    private interface Helper {
        String run(byte[] host);
    }

    // args[0]: a file of hosts, `label<TAB>hex` on each line, each given to the three helpers.
    public static void main(String[] args) throws Exception {
        for (String line : Files.readAllLines(Path.of(args[0]))) {
            String[] row = line.split("\t", -1);
            byte[] host = unhex(row[1]);
            report(row[0] + " get", host, h -> {
                Cbor got = Ext.extGet(h, TAG);
                return got == null ? "null" : hex(Cbor.encode(got));
            });
            report(row[0] + " set", host, h -> hex(Ext.extSet(h, TAG, Cbor.NUL)));
            report(row[0] + " clear", host, h -> hex(Ext.extClear(h, TAG)));
        }
    }

    private static void report(String label, byte[] host, Helper helper) {
        String outcome;
        try {
            outcome = "ok:" + helper.run(host);
        } catch (Cbor.DecodeError e) {
            outcome = describe(e);
        } catch (Throwable t) {
            outcome = "untyped:" + t;
        }
        System.out.println(label + "\t" + outcome);
    }
@HELPERS@
}
"""


def test_emits_classes_enums_and_codec():
    s = java.emit_types(RAZEL)
    assert "package taut;" in s
    assert "class BuildResult {" in s
    assert "enum BuildStatus {" in s
    assert "BUILT(1)" in s
    # The class's toCbor and fromCbor call its codec, a class of its own beside it.
    assert "Cbor toCbor() { return BuildResult$Codec.toCbor(this); }" in s
    assert "static BuildResult fromCbor(Cbor $c) { return BuildResult$Codec.fromCbor($c); }" in s
    assert "static BuildResult decode(byte[] $bytes) { return BuildResult$Codec.decode($bytes); }" in s
    assert "final class BuildResult$Codec {" in s
    assert "static Cbor toCbor(BuildResult $self) {" in s
    assert "static BuildResult fromCbor(Cbor $c) {" in s
    assert "static BuildResult decode(byte[] $bytes) {" in s


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
    assert "$m.add(new KV(1, Cbor.float_($self.x)));" in s
    assert "$m.add(new KV(2, $self.maybe != null ? Cbor.float_($self.maybe) : Cbor.NUL));" in s
    assert "Cbor.arr($self.xs.stream().map($e -> Cbor.float_($e)).toList())" in s
    assert "new KV(2, Cbor.float_($e.getValue()))" in s
    assert "$v.x = $c.get(1).asFloat();" in s
    assert "$v.maybe = $f.isNull() ? null : $f.asFloat();" in s
    assert "$c.get(3).asArray().stream().map($e -> $e.asFloat()).toList()" in s
    assert "$e -> $e.get(2).asFloat()" in s


# What generated Java declares: a method's parameter, a local, a loop variable and a
# lambda's parameter. A class's constants, `static final`, are its members, not locals.
_DECLARED = re.compile(r"\([\w\[\]]+ (?P<param>[\w$]+)\)"
                       r"|(?<!static final )\b\w+ (?P<local>[\w$]+) = "
                       r"|for \(\w+ (?P<item>[\w$]+) :"
                       r"|(?P<lambda>[\w$]+) ->")


def _class_body(source: str, header: str) -> list[str]:
    """The lines of the class that `header` opens in generated `source`, braces left out."""
    return source.split(f"\n{header} {{\n", 1)[1].split("\n}\n", 1)[0].splitlines()


def _bounds_lines(schema, name: str) -> list[str]:
    """Message `name`'s two constants: its effective max_depth and max_encoded_len (OPT-D3)."""
    depth = options.effective(schema, "max_depth", message=name)
    length = options.effective(schema, "max_encoded_len", message=name)
    return [f"    static final int MAX_DEPTH = {depth};",
            f"    static final Integer MAX_ENCODED_LEN = {'null' if length is None else length};"]


@pytest.mark.parametrize("forward_compat", [False, True], ids=["plain", "fc"])
def test_java_declares_only_dollar_names_and_message_classes_only_delegate(forward_compat):
    """The naming scheme, in the source. Each parameter, local, loop variable and lambda
    parameter the generator declares starts with `$`, which no taut field name (a Python
    identifier) holds. Nothing is imported, so no message name clashes with an import. A
    message's class holds only its fields, whose types name classes where no field can
    hide them, its two bounds, whose values are literals, and a toCbor, fromCbor and decode
    that call its codec, `<Message>$Codec`, a name no field holds; the codec, where no field
    is in scope, spells java.util's classes in full."""
    for schema in (RAZEL, FLOATY, SHAPES, CLASH, UTIL_NAMES, FILED, parity.parity_schema()):
        source = java.emit_types(schema, forward_compat)
        declared = [name for match in _DECLARED.finditer(source)
                    for name in match.groups() if name is not None]
        assert declared and all(name.startswith("$") for name in declared), declared
        assert "$bytes" in declared
        assert not re.search(r"^import ", source, re.MULTILINE)
        for name in schema.messages:
            body = _class_body(source, f"class {name}")
            fields = [line for line in body if line.startswith("    public ") and line.endswith(";")]
            assert body[len(fields):] == [
                *_bounds_lines(schema, name),
                f"    Cbor toCbor() {{ return {name}$Codec.toCbor(this); }}",
                f"    static {name} fromCbor(Cbor $c) {{ return {name}$Codec.fromCbor($c); }}",
                f"    static {name} decode(byte[] $bytes) {{ return {name}$Codec.decode($bytes); }}",
            ], name


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


def test_java_passes_the_shared_parity_gate():
    """Every row of the shared corpus through the gate's Java runner (`tautc parity -t
    java`), as java and java/fc, each held to the gate's governance: GREEN, or RED and
    allowlisted. A run's int rows round-trip or are satisfied by `long`."""
    reports, violations = parity.governed_variants(parity_java.run)
    for report in reports:
        if not report.available:
            pytest.skip(report.skip_reason)
    assert violations == [], "\n".join(violations)
    for report in reports:
        if not report.fault:
            satisfied = {r.name for r in report.results if r.status == parity.TYPE_SATISFIED}
            assert satisfied == {r.name for r in report.results if r.kind == "encode_fail"}, report.target


@pytest.mark.parametrize("forward_compat", [False, True], ids=["plain", "fc"])
def test_java_compiles_fields_named_like_what_its_code_names(tmp_path, forward_compat):
    """A field hides what shares its name in its class's code (TautV010Plan.md §0: a field
    `m` hid toCbor's local `m`, and a field `java` the package in `java.util.List.of`).
    So the codec's locals and parameters start with `$`, and it is a class of its own beside
    the message, `<Message>$Codec`, where none of the message's fields is in scope to hide
    `Cbor`, a message's or enum's class, or the package `java`. Clash, whose fields are named
    like all these, compiles in the plain and the forward-compat build and round-trips."""
    wire = codec.encode(CLASH, "Clash", CLASH_VALUE)
    source = ROUND_TRIP_HARNESS.replace("@MESSAGE@", "Clash")
    out = _run_harness(tmp_path, CLASH, "RoundTripHarness", source, [wire.hex()],
                       forward_compat=forward_compat)
    assert out.strip() == wire.hex()


@pytest.mark.parametrize("forward_compat", [False, True], ids=["plain", "fc"])
def test_java_compiles_messages_named_like_java_util_classes(tmp_path, forward_compat):
    """An import of a java.util class clashes with a message of its name, so the generated
    code imports none: the codec spells java.util's classes in full, where no field of the
    message is in scope to hide the package, and the message class names them only in
    types, where no field can. Messages named ArrayList, Arrays, TreeMap, List and Map, one
    holding a field named `java`, compile in both builds and round-trip."""
    wire = codec.encode(UTIL_NAMES, "Map", UTIL_NAMES_VALUE)
    source = ROUND_TRIP_HARNESS.replace("@MESSAGE@", "Map")
    out = _run_harness(tmp_path, UTIL_NAMES, "RoundTripHarness", source, [wire.hex()],
                       forward_compat=forward_compat)
    assert out.strip() == wire.hex()


def test_java_decode_error_key_is_text(tmp_path):
    """Question 9: a DecodeError's key is text, an int in decimal, a str as itself and a
    bool as `true` or `false`, for a raw map's key and each map<K,V> key kind alike."""
    args = [item for label, data in KEY_ROWS.items() for item in (label, data)]
    out = _run_harness(tmp_path, KEYS, "KeyTextHarness", KEY_TEXT_HARNESS, args)
    assert dict(line.split("\t") for line in out.splitlines()) == {
        "raw-duplicate": "DuplicateMapKey;key=5",
        "raw-negative": "NegativeMapKey;key=-1",
        "typed-missing": "MissingKey;key=3",
        "typed-int": "DuplicateMapKey;key=-9223372036854775808",
        "typed-text": "DuplicateMapKey;key=\u00e9 k",
        "typed-false": "DuplicateMapKey;key=false",
        "typed-true": "DuplicateMapKey;key=true",
    }


def test_java_decode_entry_points_throw_nothing_but_decode_error(tmp_path):
    """CD-E4 and question 5: for any bytes, each public decode entry point returns or
    throws DecodeError. The entry points are the raw decode, at the default depth and at
    the ceiling, each message's typed decode and its fromCbor, and each enum's fromWire in
    the parity fixture's forward-compat build (the plain build's decode and the
    unknown-field loop), and the three extension helpers above the band. The inputs include
    100,000-deep ones, which are TooDeep, never a StackOverflowError (D1)."""
    schema = parity.parity_schema()
    entries = [f'            check("{m}", line, data, d -> {m}.fromCbor(Cbor.decode(d)));'
               for m in schema.messages]
    entries += [f'            check("{m}.decode", line, data, d -> {m}.decode(d));'
                for m in schema.messages]
    entries += [f'            check("{e}", line, data, d -> {e}.fromWire(Cbor.decode(d).asInt()));'
                for e in schema.enums]
    inputs = _fail_closed_inputs()
    path = tmp_path / "inputs.txt"
    path.write_text("".join(data.hex() + "\n" for data in inputs))
    source = FAIL_CLOSED_HARNESS.replace("@ENTRIES@", "\n".join(entries))
    out = _run_harness(tmp_path, schema, "FailClosedHarness", source, [str(path)],
                       forward_compat=True)
    assert out.strip() == f"inputs={len(inputs)} escapes=0"


def test_java_missing_ok_reads_an_absent_key_as_null(tmp_path):
    javac, java_bin = _find_java_tools()
    scaffold.emit(MISSING_OK_SCHEMA, tmp_path, langs=["java"], services=[], runtime=True)
    java_dir = tmp_path / "java"
    harness = java_dir / "MissingOkHarness.java"
    harness.write_text(textwrap.dedent(MISSING_OK_HARNESS).strip() + "\n")
    classes = tmp_path / "classes"
    classes.mkdir()
    subprocess.run([javac, "-d", str(classes), str(java_dir / "Cbor.java"), str(java_dir / "api.java"),
                    str(harness)], check=True, cwd=ROOT, capture_output=True, text=True)
    run = subprocess.run([java_bin, "-cp", str(classes), "taut.MissingOkHarness"],
                         check=True, cwd=ROOT, capture_output=True, text=True)
    assert dict(line.split("\t") for line in run.stdout.splitlines()) == {
        "late-absent": "null",                           # absent key: null, not MissingKey
        "late-null": "null",
        "late-text": "text:x",
        "late-wrong-type": "WrongType;expected=text",    # a present value is still checked
        "late-not-map": "WrongType;expected=map",        # and the message is still a map
        "opt-absent": "MissingKey;key=1",                # plain optional requires the key
        "opt-null": "null",
        "late-unset-encode": "a101f6",                   # encode still writes the key, as null
    }


@pytest.fixture(scope="module")
def java_shapes(tmp_path_factory):
    """SHAPES' generated code and SHAPES_HARNESS, built by one javac and run once: the
    lines the harness prints, by label."""
    javac, java_bin = _find_java_tools()
    work = tmp_path_factory.mktemp("java-shapes")
    scaffold.emit(SHAPES, work, langs=["java"], services=[], runtime=True)
    java_dir = work / "java"
    harness = java_dir / "ShapesHarness.java"
    harness.write_text(textwrap.dedent(SHAPES_HARNESS).strip() + "\n")
    classes = work / "classes"
    classes.mkdir()
    build = subprocess.run([javac, "-encoding", "UTF-8", "-d", str(classes), str(java_dir / "Cbor.java"),
                            str(java_dir / "api.java"), str(harness)],
                           cwd=work, capture_output=True, text=True)
    assert build.returncode == 0, build.stdout + build.stderr
    run = subprocess.run([java_bin, "-cp", str(classes), "taut.ShapesHarness",
                          codec.encode(SHAPES, "Nested", NESTED_VALUE).hex(), *KEY_ARGS],
                         cwd=work, capture_output=True, text=True)
    assert run.returncode == 0, run.stdout + run.stderr
    return dict(line.split("\t", 1) for line in run.stdout.splitlines())


def test_java_nested_lists_round_trip(java_shapes):
    """A lambda inside a lambda binds its own name, so list<list<int>>, a list three
    deep, a map in a list and a message-valued map in a list of lists all compile and
    decode and re-encode to the same bytes."""
    assert java_shapes["nested"] == codec.encode(SHAPES, "Nested", NESTED_VALUE).hex()


def test_java_sorts_str_map_keys_by_code_point(java_shapes):
    """Map entries put in any order encode sorted by key as Python sorts them: a str key
    by code point, so U+FFFF before U+10000 and "a\\uffff" before "a\\U00010000", and an
    int or bool key by value, as before."""
    assert java_shapes["keyed"] == codec.encode(SHAPES, "Keyed", KEYED_VALUE).hex()


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


# --- bounds (D26: TautCheckedDecode.md §3, CD-E4; D27: TautOptions.md OPT-D4, OPT-L6, G3) -------

def test_java_gives_each_message_its_effective_bounds_and_a_typed_decode():
    """CD-B3, OPT-L6: each message's class holds MAX_DEPTH and MAX_ENCODED_LEN, its effective
    max_depth and max_encoded_len as `options.effective` resolves them when the code is
    generated (null for no length bound), and a static decode from bytes, which its codec runs:
    the raw decode under both constants, then fromCbor. A message inherits the file's values
    unless it declares its own, and embedding a message that declares one changes nothing."""
    for schema, expected in ((FILED, FILED_BOUNDS), (parity.parity_schema(), FIXTURE_BOUNDS)):
        source = java.emit_types(schema)
        for name, (depth, length) in expected.items():
            body = _class_body(source, f"class {name}")
            assert f"    static final int MAX_DEPTH = {depth};" in body, name
            assert f"    static final Integer MAX_ENCODED_LEN = {'null' if length is None else length};" in body, name
        for name in schema.messages:
            codec_body = _class_body(source, f"final class {name}$Codec")
            at = codec_body.index(f"    static {name} decode(byte[] $bytes) {{")
            assert codec_body[at + 1:at + 3] == [
                f"        return fromCbor(Cbor.decode($bytes, {name}.MAX_DEPTH, {name}.MAX_ENCODED_LEN));",
                "    }"], name


def _raw_bound_calls() -> list[tuple[str, bytes, int | None, int | None]]:
    """Raw decode calls, `(label, bytes, max_depth, max_encoded_len)` with None for a bound the
    call leaves out: test_cbor.py's cases for Python's `loads`, each bound a Java int."""
    calls: list[tuple[str, bytes, int | None, int | None]] = []

    def call(label: str, data: bytes, max_depth: int | None = None,
             max_encoded_len: int | None = None) -> None:
        calls.append((f"{len(calls)} {label}", data, max_depth, max_encoded_len))

    for opener, leaf in (("81", "80"), ("a100", "a0"), ("81", "a0"), ("a100", "80")):
        call(f"32 {opener} then {leaf}", _nest(opener, 31, leaf))
        call(f"32 {opener} then a scalar", _nest(opener, 32, "00"))
        call(f"33 {opener} then {leaf}", _nest(opener, 32, leaf))
    for leaf in ("00", "80", "a0"):
        call(f"32 alternating then {leaf}", _nest("81a100", 16, leaf))
    for hexed in ("00", "6161", "80", "a0", "8100", "a10000", "820102",
                  "8180", "81a0", "a10080", "a100a0", "820180"):
        call(f"depth 1, {hexed}", bytes.fromhex(hexed), 1)
    call("a key at depth 1", bytes.fromhex("a18000"), 1)
    call("a key at depth 2", bytes.fromhex("a18000"), 2)
    for depth in (1, 2, 5, 31, 32, 33, 64, 127, 128, 129, 1000, 2**31 - 1):
        call(f"depth {depth}, at the bound", _nest("81", min(depth, 128) - 1, "80"), depth)
        call(f"depth {depth}, beyond it", _nest("81", min(depth, 128), "80"), depth)
    call("33rd head, its items missing", _nest("81", 33, ""))
    call("33rd map head, its items missing", _nest("a100", 32, "a1"))
    for head in ("9bffffffffffffffff", "bbffffffffffffffff", "98", "9900", "9a000000", "9b00",
                 "b8", "bb00000000000000", "9800", "9c", "bf"):
        call(f"33rd head {head}", _nest("81", 32, head))
    for index, data in enumerate(DEEP_INPUTS):
        for depth in (None, 128, 10**9):
            call(f"deep input {index}, depth {depth}", data, depth)
    four = bytes.fromhex("83010203")
    for length in (4, 2**31 - 1, 3):
        call(f"4 bytes, length {length}", four, None, length)
    big = cbor.dumps(b"x" * 100_000)
    call("100,003 bytes, no bound", big)
    call("100,003 bytes, a null length bound", big, 32, None)
    call("100,003 bytes, a byte over", big, None, len(big) - 1)
    call("length before a byte", bytes.fromhex("c0c0c0c0"), None, 3)
    call("length before depth", _nest("81", 40, "80"), None, 10)
    call("length before trailing bytes", bytes.fromhex("0000"), None, 1)
    call("length 0, empty", b"", None, 0)
    call("length 0, a byte", b"\x00", None, 0)
    for data in (b"", b"\x00", bytes.fromhex("c0c0c0c0")):
        for depth, length in ((0, None), (-1, None), (-(2**31), None), (None, -1),
                              (None, -(2**31)), (0, 3)):
            call(f"caller error {depth}, {length}", data, depth, length)
    return calls


def _python_raw(data: bytes, max_depth: int | None, max_encoded_len: int | None) -> str:
    """What Python's `loads`, the reference, does with a raw call, as RAW_BOUNDS_HARNESS
    reports it; Python's caller error, ValueError, is Java's IllegalArgumentException."""
    limits = {name: value for name, value in (("max_depth", max_depth),
                                              ("max_encoded_len", max_encoded_len))
              if value is not None}
    try:
        return "ok:" + cbor.dumps(cbor.loads(data, **limits)).hex()
    except cbor.DecodeError as exc:
        return parity.format_error(exc.tag, exc.payload)
    except ValueError:
        return "IllegalArgumentException"


def _arg(value: int | None) -> str:
    return "-" if value is None else str(value)


def test_java_raw_decode_applies_the_bounds_as_python_does(tmp_path):
    """CD-B1-B5 and question 1, call by call against Python's `loads`. The runtime's
    DEFAULT_MAX_DEPTH and MAX_DEPTH_CEILING are 32 and 128. Cbor.decode(data) applies 32;
    Cbor.decode(data, maxDepth, maxEncodedLen) applies maxDepth, the ceiling above it, and a
    length bound unless maxEncodedLen is null, before any byte is read. A top-level container
    has depth 1, and a container a level too deep is TooDeep once its head is complete, so
    100,000-deep input is TooDeep, never a StackOverflowError. A depth below 1 or a negative
    length is the caller's error, IllegalArgumentException, where Python raises ValueError."""
    calls = _raw_bound_calls()
    path = tmp_path / "calls.tsv"
    path.write_text("".join(f"{label}\t{data.hex()}\t{_arg(depth)}\t{_arg(length)}\n"
                            for label, data, depth, length in calls))
    source = RAW_BOUNDS_HARNESS.replace("@HELPERS@", BOUNDS_HELPERS)
    out = _run_harness(tmp_path, KEYS, "RawBoundsHarness", source, [str(path)])
    seen = dict(line.split("\t", 1) for line in out.splitlines())
    assert seen.pop("constants") == f"{options.DEFAULT_MAX_DEPTH};{options.MAX_DEPTH_CEILING}"
    assert seen == {label: _python_raw(data, depth, length) for label, data, depth, length in calls}


# Inputs for every message's typed decode: DEEP_INPUTS, and inputs at FILED's and the fixture's
# declared bounds and one beyond them.
TYPED_INPUTS = {
    **{f"deep input {index}": data for index, data in enumerate(DEEP_INPUTS)},
    "a tree 4 deep": bytes.fromhex("a10181a10180"),
    "a list 4 deep": bytes.fromhex("a10181818100"),
    "a list 2 deep": bytes.fromhex("a1018100"),
    "a list 3 deep": bytes.fromhex("a1018180"),
    "16 bytes": bytes.fromhex("a1018d" + "00" * 13),
    "17 bytes": bytes.fromhex("a1018e" + "00" * 14),
    "8 bytes": bytes.fromhex("a101450102030405"),
    "9 bytes": bytes.fromhex("a10146010203040506"),
}


def _python_typed(schema, message: str, data: bytes) -> str:
    """What Python's typed decode, `codec.decode`, does with `data` rooted at `message`, as
    TYPED_BOUNDS_HARNESS reports it."""
    try:
        return "ok:" + codec.encode(schema, message, codec.decode(schema, message, data)).hex()
    except cbor.DecodeError as exc:
        return parity.format_error(exc.tag, exc.payload)


@pytest.mark.parametrize("which", ["filed", "fixture"])
def test_java_typed_decode_applies_its_messages_bounds_as_python_does(tmp_path, which):
    """CD-B3, OPT-D4 and OPT-L6, against Python's `codec.decode`: each message's decode from
    bytes applies its own MAX_DEPTH and MAX_ENCODED_LEN, whatever a message it embeds declares,
    so far too deep input is TooDeep at the message's bound, or TooLarge first where a length
    bound applies, never a StackOverflowError. Each message's constants are its effective
    values. Built with forward-compat, so a decoded unknown field re-encodes as in Python."""
    schema, expected = (FILED, FILED_BOUNDS) if which == "filed" else (parity.parity_schema(), FIXTURE_BOUNDS)
    messages = list(schema.messages)
    path = tmp_path / "inputs.tsv"
    path.write_text("".join(f"{label}\t{data.hex()}\n" for label, data in TYPED_INPUTS.items()))
    dispatch = [f'            case "{m}" -> {{\n'
                f"                return Cbor.encode({m}.decode(data).toCbor());\n"
                "            }" for m in messages]
    constants = [f'        System.out.println("bounds {m}\\t" + {m}.MAX_DEPTH + ";" + {m}.MAX_ENCODED_LEN);'
                 for m in messages]
    source = (TYPED_BOUNDS_HARNESS.replace("@MESSAGES@", ", ".join(f'"{m}"' for m in messages))
              .replace("@DISPATCH@", "\n".join(dispatch)).replace("@CONSTANTS@", "\n".join(constants))
              .replace("@HELPERS@", BOUNDS_HELPERS))
    out = _run_harness(tmp_path, schema, "TypedBoundsHarness", source, [str(path)],
                       forward_compat=True)
    seen = dict(line.split("\t", 1) for line in out.splitlines())
    resolved = {m: seen.pop(f"bounds {m}") for m in messages}
    def text(depth, length) -> str:
        return f"{depth};{'null' if length is None else length}"

    assert resolved == {m: text(options.effective(schema, "max_depth", message=m),
                                options.effective(schema, "max_encoded_len", message=m))
                        for m in messages}
    assert {m: resolved[m] for m in expected} == {m: text(*bounds) for m, bounds in expected.items()}
    assert seen == {f"{label} {m}": _python_typed(schema, m, data)
                    for label, data in TYPED_INPUTS.items() for m in messages}


def test_java_extension_helpers_read_a_host_at_the_ceiling_with_no_length_bound(tmp_path):
    """TautOptions.md G3 and CD-E4: a helper cannot name its host's root, so it reads the host
    at the depth ceiling, 128, with no length bound, the only bounds every valid host meets,
    whatever the schema declares (FILED: depth 3, 16 bytes). A deeper host is TooDeep{128},
    however deep."""
    def host(arrays: int) -> bytes:  # a host map whose field 7 holds `arrays` nested arrays
        return bytes.fromhex("a107" + "81" * (arrays - 1) + "80")

    hosts = {"at the ceiling": host(127), "one beyond": host(128), "far beyond": host(100_000),
             "long": cbor.dumps({1: 1, 7: b"x" * 100_000})}
    path = tmp_path / "hosts.tsv"
    path.write_text("".join(f"{label}\t{data.hex()}\n" for label, data in hosts.items()))
    source = EXT_BOUNDS_HARNESS.replace("@HELPERS@", BOUNDS_HELPERS)
    out = _run_harness(tmp_path, FILED, "ExtBoundsHarness", source, [str(path)])
    expected = {}
    for label, data in hosts.items():
        if label.endswith("beyond"):
            expected.update({f"{label} {op}": "TooDeep;limit=128" for op in ("get", "set", "clear")})
            continue
        tree = cbor.loads(data, max_depth=128)
        expected[f"{label} get"] = "ok:null"
        expected[f"{label} set"] = "ok:" + cbor.dumps({**tree, BAND_START + 1: None}).hex()
        expected[f"{label} clear"] = "ok:" + data.hex()
    assert dict(line.split("\t", 1) for line in out.splitlines()) == expected
