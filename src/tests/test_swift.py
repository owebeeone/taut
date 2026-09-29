"""Swift generator: native structs + enums + CBOR codec, forward-compat residual,
Swift-keyword escaping and `optional=MISSING_OK`. When swiftc is available, the
vendored runtime is also checked against the byte-exact float corpus, and the
shared parity corpus is replayed through the gate's runner (`tautc parity -t swift`).

Checked decode (TautCheckedDecode.md, D26): no field named like a parameter, local or
runtime helper of the generated code breaks it, a repeated map key is reported as text
(question 9), and every public decode entry point, the extension helpers included,
returns or throws `CborError` (CD-E4, question 5)."""

import json
import os
import random
import re
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path

from taut import ext
from taut.corpus.build import IR_PATH
from taut.corpus import parity, parity_swift
from taut.corpus import resext_build as rb
from taut.gen import scaffold, swift
from taut.ir.dsl import (
    BOOL, BYTES, FLOAT, INT, MISSING_OK, STR, Enum, F, List, Map, Msg, Ref, schema as mk,
)
from taut.ir.load import load_schema
from taut.ir.shapes import BAND_START
from taut.wire import cbor, codec

import pytest

GRIPLAB = load_schema(IR_PATH)
RAZEL = load_schema(IR_PATH.parent / "razel.taut.py")
RESEXT = load_schema(rb.IR_PATH)
ROOT = Path(__file__).resolve().parents[2]
FLOAT_VECTORS = ROOT / "corpus" / "float_vectors.json"
RESIDUAL_VECTORS = ROOT / "corpus" / "residual_vectors.json"
EXT_VECTORS = ROOT / "corpus" / "ext_vectors.json"
SWIFT_CBOR = ROOT / "src/taut/gen/runtime/cbor.swift"
SWIFT_EXT = ROOT / "src/taut/gen/runtime/ext.swift"
RESEXT_FUZZ_SEED = 0x55_0202
FAIL_CLOSED_SEED = 0xD2_5717
# `Late` reads an absent note as null (MISSING_OK); `Opt`, for contrast, requires the key.
MISSING_OK_SCHEMA = mk(
    Msg("Late", F("note", 1, STR, optional=MISSING_OK)),
    Msg("Opt", F("note", 1, STR, optional=True)),
)
# Fields named like what the generated Swift binds or calls, beyond the shared Names
# fixture: the decoders' parameter `c` and locals `v`, `raw` and `value`; the runtime's
# old free helper `decodeDictionary`, the members the code calls on a Cbor value and the
# runtime's free functions. Kind's members are named like the enum decoder's locals, and
# Level, which has no member 0, types a transient field, whose default applies on decode.
CLASH_SCHEMA = mk(
    Enum("Kind", raw=0, value=1, c=2),
    Enum("Level", high=2, low=1),
    Msg("Inner", F("v", 1, INT)),
    Msg("Clash",
        F("c", 1, INT),
        F("v", 2, INT, optional=True),
        F("raw", 3, Ref("Kind")),
        F("value", 4, STR, optional=MISSING_OK),
        F("decodeDictionary", 5, Map(STR, INT)),
        F("tryDictionary", 6, Map(BOOL, Ref("Kind"))),
        F("tryGet", 7, List(Ref("Inner"))),
        F("isNull", 8, Map(INT, Ref("Inner")), optional=True),
        F("mapEntries", 9, BOOL),
        F("encode", 10, BYTES),
        F("tryDecode", 11, FLOAT),
        F("tryArray", 12, List(List(STR))),
        F("level", 13, Ref("Level"), transient=True),
        next_id=14),
)
CLASH_VALUE = {
    "c": 1, "v": None, "raw": "value", "value": "x", "decodeDictionary": {"a": 1},
    "tryDictionary": {True: "c"}, "tryGet": [{"v": 5}], "isNull": {3: {"v": 4}},
    "mapEntries": True, "encode": b"\x01\x02", "tryDecode": 1.5, "tryArray": [["p"]],
}
# One map<K,V> per key kind, for question 9's payload.
KEYS_SCHEMA = mk(Msg("Keys",
                     F("by_text", 1, Map(STR, INT)),
                     F("by_flag", 2, Map(BOOL, INT)),
                     F("by_id", 3, Map(INT, INT))))


def _require_swiftc():
    swiftc = shutil.which("swiftc")
    if swiftc is None:
        pytest.skip("swiftc not found")
    return swiftc


def _compile_swift(tmp_path, sources, name):
    swiftc = _require_swiftc()
    exe = tmp_path / name
    compile_run = subprocess.run(
        [swiftc, *map(str, sources), "-o", str(exe)],
        text=True,
        capture_output=True,
    )
    assert compile_run.returncode == 0, compile_run.stderr
    return exe


def _write_resext_model(tmp_path):
    model = tmp_path / "ResExt.swift"
    model.write_text(swift.emit_types(RESEXT, forward_compat=True))
    return model


def _swift_string(value: str) -> str:
    return json.dumps(value)


def _swift_support() -> str:
    return textwrap.dedent("""
        func bytes(fromHex hex: String) -> [UInt8] {
            precondition(hex.count % 2 == 0)
            var bytes: [UInt8] = []
            var idx = hex.startIndex
            while idx < hex.endIndex {
                let next = hex.index(idx, offsetBy: 2)
                bytes.append(UInt8(String(hex[idx..<next]), radix: 16)!)
                idx = next
            }
            return bytes
        }

        func hex(_ bytes: [UInt8]) -> String {
            let digits = Array("0123456789abcdef".utf8)
            var out: [UInt8] = []
            out.reserveCapacity(bytes.count * 2)
            for b in bytes {
                out.append(digits[Int(b >> 4)])
                out.append(digits[Int(b & 0x0f)])
            }
            return String(decoding: out, as: UTF8.self)
        }

        func fields(_ blob: String) -> [[Substring]] {
            return blob.split(separator: "\\n").map {
                $0.split(separator: "|", omittingEmptySubsequences: false)
            }
        }
        """)


def _random_text(rng: random.Random) -> str:
    alphabet = "abcXYZ09"
    return "".join(rng.choice(alphabet) for _ in range(rng.randrange(0, 8)))


def _random_cbor_value(rng: random.Random, depth: int = 0):
    choices = ["int", "text", "bytes", "bool", "null"]
    if depth < 2:
        choices.append("array")
    kind = rng.choice(choices)
    if kind == "int":
        return rng.randrange(-2000, 2001)
    if kind == "text":
        return _random_text(rng)
    if kind == "bytes":
        return bytes(rng.randrange(0, 256) for _ in range(rng.randrange(0, 8)))
    if kind == "bool":
        return bool(rng.randrange(0, 2))
    if kind == "null":
        return None
    return [_random_cbor_value(rng, depth + 1) for _ in range(rng.randrange(0, 4))]


def _random_host_map(rng: random.Random) -> dict[int, object]:
    band_tag = BAND_START + rng.randrange(1, 1 << 10)
    host: dict[int, object] = {
        1: rng.randrange(0, 1_000_000),
        2: _random_text(rng),
        3: _random_cbor_value(rng),          # interleaved residual between known tags
        5: rng.randrange(-1000, 1000),
        band_tag: _random_cbor_value(rng),   # band residual
    }
    target_size = rng.randrange(6, 10)
    while len(host) < target_size:
        tag = rng.randrange(0, 1 << 21)
        if tag not in (1, 2, 5) and tag not in host:
            host[tag] = _random_cbor_value(rng)
    return host


def _random_decision(rng: random.Random) -> dict[str, object]:
    return {"backend": _random_text(rng), "hops": rng.randrange(-50, 500)}


def _resext_fuzz_rows(iterations: int = 1000):
    rng = random.Random(RESEXT_FUZZ_SEED)
    residual_rows: list[tuple[str, str]] = []
    ext_rows: list[tuple[str, int, str, str, str, str, str, str, str]] = []
    for i in range(iterations):
        host = _random_host_map(rng)
        residual_rows.append((f"fuzz-{i}", cbor.dumps(host).hex()))

        ext_host = cbor.dumps(_random_host_map(rng))
        tag = BAND_START + rng.randrange(1, 1 << 12)
        value = _random_decision(rng)
        value_hex = codec.encode(RESEXT, "Decision", value).hex()
        set_expect = ext.ext_set(RESEXT, ext_host, "Decision", tag, value).hex()
        get_expect = codec.encode(RESEXT, "Decision", ext.ext_get(RESEXT, bytes.fromhex(set_expect), "Decision", tag)).hex()
        clear_expect = ext.ext_clear(bytes.fromhex(set_expect), tag).hex()
        ext_rows.append((
            f"fuzz-{i}",
            tag,
            ext_host.hex(),
            value_hex,
            set_expect,
            set_expect,
            get_expect,
            set_expect,
            clear_expect,
        ))
    return residual_rows, ext_rows


def test_emits_structs_enums_and_codec():
    s = swift.emit_types(RAZEL)
    assert "public struct BuildResult {" in s
    assert "public enum BuildStatus: Int64 {" in s
    assert "public func toCbor() -> Cbor" in s
    assert "public static func fromCbor(_ wire_c: Cbor) throws -> BuildResult" in s
    assert "public static func fromCbor(_ wire_c: Cbor) throws -> BuildStatus" in s
    assert "public init(" in s  # constructible cross-module


def test_generated_bindings_take_the_reserved_wire_prefix():
    """No field can clash with what the generated code binds or calls. Its parameters and
    locals take taut's reserved `wire_` prefix, which no field may take (ir/validate.py);
    the runtime is reached through members of a Cbor value, never an unqualified free
    function, which a field of the same name would hide (the Names fixture)."""
    for forward_compat in (False, True):
        s = swift.emit_types(parity.parity_schema(), forward_compat=forward_compat)
        bound = re.findall(r"static func \w+\(_ (\w+): Cbor\)", s) + re.findall(r"\blet (\w+) = ", s)
        assert {"wire_c", "wire_v", "wire_raw", "wire_value"} <= set(bound)
        assert [name for name in bound if not name.startswith("wire_")] == []
        assert re.findall(r"(?<![\w.])(?:encode|decode|tryDecode|decodeDictionary)\(", s) == []
        assert "try wire_c.tryGet(14).tryDictionary(key: { try $0.tryText() }, " in s


def test_transient_enum_default_is_a_member_not_a_force_unwrap():
    """A transient field's default applies on every decode, so it must not trap: an enum's
    member with wire value 0, else its first member (as Rust's `#[default]`), never a
    force-unwrapped `(rawValue: 0)!`, which traps for an enum without a 0."""
    zero = mk(Enum("Zero", one=1, zero=0),
              Msg("Z", F("n", 1, INT), F("zero", 2, Ref("Zero"), transient=True)))
    s, s0 = swift.emit_types(CLASH_SCHEMA), swift.emit_types(zero)
    assert "level: Level = .high" in s     # Level has no 0: its first member
    assert "zero: Zero = .zero" in s0      # the member with wire value 0, as before
    assert ")!" not in s + s0


def test_swift_keyword_field_is_backticked():
    s = swift.emit_types(RAZEL)  # razel's VersionInfo.protocol collides with a Swift keyword
    assert "public var `protocol`: Int64" in s
    assert "Cbor.int(`protocol`)" in s


def test_transient_field_kept_with_default():
    s = swift.emit_types(GRIPLAB)  # FileSnapshot.preview is transient (native-only)
    assert "preview: String =" in s  # defaulted in init so it's omittable / off-wire


def test_forward_compat_adds_residual():
    s = swift.emit_types(RAZEL, forward_compat=True)
    assert "public var wire_residual: [(Int64, Cbor)]" in s
    assert "+ wire_residual" in s                    # re-emitted in toCbor (encode sorts)
    assert "wire_residual" not in swift.emit_types(RAZEL)  # off by default


def test_swift_resext_cli_generates_forward_compat_runtime(tmp_path):
    out = tmp_path / "gen"
    env = {**os.environ, "PYTHONPATH": str(ROOT / "src")}
    run = subprocess.run(
        [
            sys.executable, "-m", "taut.cli", "gen", str(ROOT / "ir/resext.taut.py"),
            "-o", str(out), "-l", "swift", "--api-only", "--with-runtime", "--forward-compat",
        ],
        text=True,
        capture_output=True,
        env=env,
    )
    assert run.returncode == 0, run.stderr
    api = (out / "swift/api.swift").read_text()
    assert "public struct Host" in api
    assert "public struct Decision" in api
    assert "public var wire_residual: [(Int64, Cbor)]" in api
    assert "wire_residual" not in swift.emit_types(RESEXT)
    assert (out / "swift/cbor.swift").exists()
    assert "public func extSet" in (out / "swift/ext.swift").read_text()


def test_float_codegen_shape():
    s = swift.emit_types(mk(Msg(
        "FloatBox",
        F("x", 1, FLOAT),
        F("xs", 2, List(FLOAT)),
        F("by_id", 3, Map(INT, FLOAT)),
        F("maybe", 4, FLOAT, optional=True),
        F("scratch", 5, FLOAT, transient=True),
    )))
    assert "public var x: Double" in s
    assert "public var xs: [Double]" in s
    assert "public var by_id: [Int64: Double]" in s
    assert "public var maybe: Double?" in s
    assert "scratch: Double = 0.0" in s
    assert "(1, Cbor.float(x))" in s
    assert "Cbor.array(xs.map { Cbor.float($0) })" in s
    assert "(2, Cbor.float($0.value))" in s
    assert "maybe.map { Cbor.float($0) }" in s
    assert "x: try wire_c.tryGet(1).tryFloat()" in s
    assert "return try wire_v.tryFloat()" in s


def test_swift_parity_gate_is_green():
    # The shared corpus, lead rows included, through the gate's own Swift runner
    # (`tautc parity -t swift`), as swift and swift/fc: every row reported, judged on tag
    # and payload, each held to the gate's governance: GREEN, or RED and allowlisted.
    reports, violations = parity.governed_variants(parity_swift.run)
    for report in reports:
        if not report.available:
            pytest.skip(report.skip_reason)
    assert violations == [], "\n".join(violations)


def test_missing_ok_generates_for_swift(tmp_path):
    scaffold.emit(MISSING_OK_SCHEMA, tmp_path, langs=["swift"], services=[])
    api = (tmp_path / "swift" / "api.swift").read_text()
    late = api[api.index("public struct Late"):api.index("public struct Opt")]
    opt = api[api.index("public struct Opt"):]
    assert "try wire_c.tryGetOpt(1)" in late
    assert "tryGetOpt" not in opt
    assert "try wire_c.tryGet(1)" in opt
    # encode is unchanged: an unset note is still written, as null
    assert "(1, (note.map { Cbor.text($0) } ?? Cbor.null))" in late


def test_swift_missing_ok_reads_absent_as_null(tmp_path):
    _require_swiftc()
    scaffold.emit(MISSING_OK_SCHEMA, tmp_path / "gen", langs=["swift"], services=[], runtime=True)
    generated = tmp_path / "gen" / "swift"
    harness = tmp_path / "main.swift"
    harness.write_text(_swift_support() + textwrap.dedent("""
        func observe(_ work: () throws -> String?) -> String {
            do {
                return "ok " + ((try work()) ?? "null")
            } catch let error as CborError {
                return "err \\(error)"
            } catch {
                return "untyped \\(error)"
            }
        }

        func late(_ wire: String) -> String {
            return observe { try Late.fromCbor(tryDecode(bytes(fromHex: wire))).note }
        }

        func opt(_ wire: String) -> String {
            return observe { try Opt.fromCbor(tryDecode(bytes(fromHex: wire))).note }
        }

        for wire in ["a0", "a101f6", "a1016178", "a10101", "00"] {
            print("Late \\(wire) \\(late(wire))")
        }
        print("Late encode \\(hex(encode(Late(note: nil).toCbor())))")
        for wire in ["a0", "a101f6"] {
            print("Opt \\(wire) \\(opt(wire))")
        }
        """))
    exe = _compile_swift(tmp_path, [generated / "cbor.swift", generated / "api.swift", harness],
                         "swift-missing-ok")
    run = subprocess.run([str(exe)], text=True, capture_output=True)
    assert run.returncode == 0, run.stderr + run.stdout
    assert run.stdout.splitlines() == [
        "Late a0 ok null",                                  # absent key: null
        "Late a101f6 ok null",                              # present null: null
        "Late a1016178 ok x",
        "Late a10101 err WrongType(expected: text)",        # a wrong type still fails
        "Late 00 err WrongType(expected: map)",             # and so does a non-map
        "Late encode a101f6",                               # encode still writes the key
        "Opt a0 err MissingKey(key: 1)",                    # plain optional: absent is MissingKey
        "Opt a101f6 ok null",
    ]


def _emit_swift(schema, out, forward_compat=False):
    """The schema's Swift with its vendored runtime: out/swift/{api,cbor,ext}.swift."""
    scaffold.emit(schema, out, langs=["swift"], services=[], runtime=True,
                  forward_compat=forward_compat)
    return out / "swift"


@pytest.mark.parametrize("forward_compat", [False, True], ids=["plain", "fc"])
def test_swift_fields_named_like_generated_code_compile(tmp_path, forward_compat):
    """A field named like a generated parameter or local, a runtime helper, a member the
    code calls on a Cbor value or a runtime free function compiles, decodes and re-encodes;
    a transient field of an enum without a 0 takes its default without trapping."""
    _require_swiftc()
    generated = _emit_swift(CLASH_SCHEMA, tmp_path / "gen", forward_compat)
    wire = codec.encode(CLASH_SCHEMA, "Clash", CLASH_VALUE).hex()
    harness = tmp_path / "main.swift"
    harness.write_text(_swift_support() + textwrap.dedent(f"""
        let decoded = try Clash.fromCbor(tryDecode(bytes(fromHex: "{wire}")))
        print(hex(encode(decoded.toCbor())))
        print(decoded.level == .high)
        let built = Clash(c: 1, v: nil, raw: .value, value: "x", decodeDictionary: ["a": 1],
                          tryDictionary: [true: .c], tryGet: [Inner(v: 5)],
                          isNull: [3: Inner(v: 4)], mapEntries: true, encode: [1, 2],
                          tryDecode: 1.5, tryArray: [["p"]])
        print(hex(encode(built.toCbor())))
        """))
    exe = _compile_swift(tmp_path, [generated / "cbor.swift", generated / "api.swift", harness],
                         "swift-clash")
    run = subprocess.run([str(exe)], text=True, capture_output=True)
    assert run.returncode == 0, run.stderr + run.stdout
    assert run.stdout.splitlines() == [wire, "true", wire]


def _keys_wire(text=(), flag=(), ids=()) -> str:
    """A Keys whose three maps hold these keys, in order, each entry its own value."""
    def entries(keys):
        return [{1: key, 2: n} for n, key in enumerate(keys)]
    return cbor.dumps({1: entries(text), 2: entries(flag), 3: entries(ids)}).hex()


def test_swift_duplicate_map_key_is_reported_as_text(tmp_path):
    """Question 9: DuplicateMapKey's key is a String, the key as text: an int in decimal, a
    str as itself, a bool as `true` or `false`, for a raw map and each map<K,V> key kind."""
    _require_swiftc()
    generated = _emit_swift(KEYS_SCHEMA, tmp_path / "gen")
    rows = [
        ("raw", "a201000101"),
        ("text", _keys_wire(text=["a", "a"])),
        ("text-non-ascii", _keys_wire(text=["\u00e9", "\u00e9"])),
        ("true", _keys_wire(flag=[True, True])),
        ("false", _keys_wire(flag=[False, False])),
        ("int", _keys_wire(ids=[5, 5])),
        ("negative", _keys_wire(ids=[-5, -5])),
    ]
    table = ",\n".join(f"    ({_swift_string(name)}, {_swift_string(wire)})" for name, wire in rows)
    harness = tmp_path / "main.swift"
    harness.write_text(_swift_support() + "let rows: [(String, String)] = [\n" + table + "\n]\n"
                       + textwrap.dedent("""
        for (name, wire) in rows {
            do {
                let c = try tryDecode(bytes(fromHex: wire))
                if name != "raw" {
                    _ = try Keys.fromCbor(c)
                }
                print("\\(name) ok")
            } catch CborError.duplicateMapKey(let key) {
                let text: String = key
                print("\\(name) \\(text)")
            } catch {
                print("\\(name) other \\(error)")
            }
        }
        """))
    exe = _compile_swift(tmp_path, [generated / "cbor.swift", generated / "api.swift", harness],
                         "swift-duplicate-key")
    run = subprocess.run([str(exe)], text=True, capture_output=True, encoding="utf-8")
    assert run.returncode == 0, run.stderr + run.stdout
    assert run.stdout.splitlines() == [
        "raw 1", "text a", "text-non-ascii \u00e9", "true true", "false false", "int 5",
        "negative -5",
    ]


def test_swift_runtime_has_no_trapping_decode_path():
    """Question 5: no decode path traps. The accessors that trapped on the wrong shape
    (`get`, `intVal`, ...) and `decode` are gone with the `force` that called `fatalError`,
    and the free `decodeDictionary`, which a field could hide, is a member of Cbor."""
    runtime = SWIFT_CBOR.read_text()
    for gone in ("fatalError", "preconditionFailure", "try!", "func force", "func get(",
                 "public func decode(", "intVal", "floatVal", "textVal", "bytesVal", "boolVal",
                 "arrayVal", "func decodeDictionary"):
        assert gone not in runtime, gone
    assert "func tryDictionary<" in runtime
    extension = SWIFT_EXT.read_text()
    for gone in ("fatalError", "preconditionFailure", "try!", "decode(host)"):
        assert gone not in extension, gone


def _fail_closed_inputs() -> list[str]:
    """Every parity row's bytes, the heads that claim the largest lengths and counts, and
    fixed-seed mutations of each: a byte changed, the tail cut, a byte inserted or a run
    of bytes repeated (which repeats keys and entries)."""
    rng = random.Random(FAIL_CLOSED_SEED)
    seeds = [bytes.fromhex(row["bytes"]) for row in parity.malformed_rows()]
    seeds += [bytes.fromhex(row["cbor"]) for row in parity.int_rows() if "cbor" in row]
    seeds += [bytes.fromhex(head) for head in (
        "", "ff", "1bffffffffffffffff", "3bffffffffffffffff", "5bffffffffffffffff",
        "7bffffffffffffffff", "9bffffffffffffffff", "bbffffffffffffffff", "c0", "f8", "fc",
        "5a7fffffff", "9a7fffffff00")]
    inputs: set[bytes] = set()
    for data in seeds:
        inputs.add(data)
        for _ in range(20):
            mutant = bytearray(data)
            op = rng.randrange(4)
            if op == 0 and mutant:
                mutant[rng.randrange(len(mutant))] = rng.randrange(256)
            elif op == 1 and mutant:
                del mutant[rng.randrange(len(mutant)):]
            elif op == 2 or not mutant:
                mutant.insert(rng.randrange(len(mutant) + 1), rng.randrange(256))
            else:
                start = rng.randrange(len(mutant))
                end = rng.randrange(start, len(mutant)) + 1
                mutant[end:end] = mutant[start:end]
            inputs.add(bytes(mutant))
    return sorted(data.hex() for data in inputs)


@pytest.mark.parametrize("forward_compat", [False, True], ids=["plain", "fc"])
def test_swift_decode_entry_points_fail_closed_on_mutated_input(tmp_path, forward_compat):
    """CD-E4: on each input, every public decode entry point returns or throws CborError:
    the raw decode, each accessor, each fixture message's and enum's fromCbor (and the
    decoded message's re-encoding) and the three ext helpers. A trap fails the run; any
    other error is counted as escaped. (Nesting deep enough to exhaust the stack is D1's
    depth bound.)"""
    _require_swiftc()
    generated = _emit_swift(parity.parity_schema(), tmp_path / "gen", forward_compat)
    dispatch = parity.fixture_dispatch()
    typed = [f'    observe("{name}", wire) {{ _ = encode(try {name}.fromCbor(c).toCbor()) }}'
             for name in dispatch.messages]
    typed += [f'    observe("{name}", wire) {{ _ = try {name}.fromCbor(c) }}' for name in dispatch.enums]
    inputs = _fail_closed_inputs()
    harness = tmp_path / "main.swift"
    harness.write_text("import Foundation\n" + _swift_support() + "let inputs: [String] = [\n"
                       + ",\n".join(f'    "{wire}"' for wire in inputs) + "\n]\n"
                       + textwrap.dedent("""
        var escaped = 0

        func observe(_ what: String, _ wire: String, _ work: () throws -> Void) {
            do {
                try work()
            } catch is CborError {
            } catch {
                escaped += 1
                print("escaped \\(what) \\(wire): \\(type(of: error)) \\(error)")
            }
        }

        let band: Int64 = 1 << 20
        for wire in inputs {
            fputs("input \\(wire)\\n", stderr)
            let data = bytes(fromHex: wire)
            observe("extGet", wire) { _ = try extGet(data, tag: band) }
            observe("extSet", wire) { _ = try extSet(data, tag: band, value: .null) }
            observe("extClear", wire) { _ = try extClear(data, tag: band) }
            var decoded: Cbor? = nil
            observe("tryDecode", wire) { decoded = try tryDecode(data) }
            guard let c = decoded else {
                continue
            }
            observe("tryGet", wire) { _ = try c.tryGet(1) }
            observe("tryGetOpt", wire) { _ = try c.tryGetOpt(1) }
            observe("tryInt", wire) { _ = try c.tryInt() }
            observe("tryFloat", wire) { _ = try c.tryFloat() }
            observe("tryText", wire) { _ = try c.tryText() }
            observe("tryBytes", wire) { _ = try c.tryBytes() }
            observe("tryBool", wire) { _ = try c.tryBool() }
            observe("tryArray", wire) { _ = try c.tryArray() }
            observe("tryDictionary", wire) {
                _ = try c.tryDictionary(key: { try $0.tryText() }, value: { try $0.tryInt() })
            }
        """) + "\n".join(typed) + "\n}\n"
                       + 'print("fail-closed inputs=\\(inputs.count) escaped=\\(escaped)")\n')
    exe = _compile_swift(tmp_path, [generated / "cbor.swift", generated / "ext.swift",
                                    generated / "api.swift", harness], "swift-fail-closed")
    run = subprocess.run([str(exe)], text=True, capture_output=True)
    assert run.returncode == 0, run.stderr[-1500:] + run.stdout[-1500:]
    assert run.stdout.splitlines()[-1] == f"fail-closed inputs={len(inputs)} escaped=0", run.stdout


def test_swift_resext_corpus_vectors(tmp_path):
    residual_rows = json.loads(RESIDUAL_VECTORS.read_text())
    ext_rows = json.loads(EXT_VECTORS.read_text())
    residual_blob = "\n".join(f"{row['note']}|{row['wire']}" for row in residual_rows)
    ext_blob = "\n".join(
        "|".join([
            row["op"],
            row["note"],
            row["host"],
            str(row["tag"]),
            row.get("value", ""),
            row["expect"],
        ])
        for row in ext_rows
    )
    model = _write_resext_model(tmp_path)
    harness = tmp_path / "main.swift"
    harness.write_text(_swift_support() + textwrap.dedent(f"""
        let residualBlob = {_swift_string(residual_blob)}
        let extBlob = {_swift_string(ext_blob)}
        var mismatches = 0

        func check(_ condition: Bool, _ message: String) {{
            if !condition {{
                print(message)
                mismatches += 1
            }}
        }}

        for parts in fields(residualBlob) {{
            let note = String(parts[0])
            let wire = String(parts[1])
            let decoded = try! Host.fromCbor(tryDecode(bytes(fromHex: wire)))
            let got = hex(encode(decoded.toCbor()))
            check(got == wire, "residual \\(note): \\(got) != \\(wire)")
        }}

        for parts in fields(extBlob) {{
            let op = String(parts[0])
            let note = String(parts[1])
            let host = String(parts[2])
            let tag = Int64(parts[3])!
            let value = String(parts[4])
            let expect = String(parts[5])

            if op == "set" {{
                let decision = try! Decision.fromCbor(tryDecode(bytes(fromHex: value)))
                let got = hex(try extSet(bytes(fromHex: host), tag: tag, value: decision.toCbor()))
                check(got == expect, "ext set \\(note): \\(got) != \\(expect)")
            }} else if op == "get" {{
                let raw = try extGet(bytes(fromHex: host), tag: tag)
                let got = raw.map {{ hex(encode((try! Decision.fromCbor($0)).toCbor())) }} ?? "null"
                check(got == expect, "ext get \\(note): \\(got) != \\(expect)")
            }} else if op == "clear" {{
                let got = hex(try extClear(bytes(fromHex: host), tag: tag))
                check(got == expect, "ext clear \\(note): \\(got) != \\(expect)")
            }} else {{
                check(false, "unknown op \\(op)")
            }}
        }}

        if mismatches != 0 {{
            fatalError("swift resext corpus mismatches=\\(mismatches)")
        }}
        print("swift resext corpus mismatches=0")
        """))
    exe = _compile_swift(tmp_path, [SWIFT_CBOR, SWIFT_EXT, model, harness], "swift-resext-corpus")
    run = subprocess.run([str(exe)], text=True, capture_output=True)
    assert run.returncode == 0, run.stderr + run.stdout
    assert "swift resext corpus mismatches=0" in run.stdout


def test_swift_ext_helpers_fail_closed(tmp_path):
    """CD-E4: for any host bytes the ext helpers return or throw CborError. A host that is
    not a map is WrongType(map) and malformed host bytes are their decode error. A tag
    below the band is the caller's error, not the input's, and still traps."""
    model = _write_resext_model(tmp_path)
    harness = tmp_path / "main.swift"
    harness.write_text(_swift_support() + textwrap.dedent("""
        let mode = CommandLine.arguments[1]
        let tag: Int64 = 1 << 20
        let decision = Decision(backend: "b7", hops: 1)

        func observe(_ what: String, _ work: () throws -> [UInt8]?) {
            do {
                print("\\(what) ok \\((try work()).map(hex) ?? "null")")
            } catch let error as CborError {
                print("\\(what) err \\(error)")
            } catch {
                print("\\(what) untyped \\(error)")
            }
        }

        if mode == "below-set" {
            _ = try? extSet([], tag: 7, value: decision.toCbor())
            fatalError("a tag below the band did not trap")
        } else if mode == "below-get" {
            _ = try? extGet([], tag: 7)
            fatalError("a tag below the band did not trap")
        } else if mode == "below-clear" {
            _ = try? extClear([], tag: 7)
            fatalError("a tag below the band did not trap")
        }
        let hosts = [("map", "a0"), ("scalar", "01"), ("array", "80"), ("truncated", "a1"),
                     ("trailing", "a000"), ("empty", "")]
        for (name, host) in hosts {
            let data = bytes(fromHex: host)
            observe("set \\(name)") { try extSet(data, tag: tag, value: decision.toCbor()) }
            observe("get \\(name)") { try extGet(data, tag: tag).map { encode($0) } }
            observe("clear \\(name)") { try extClear(data, tag: tag) }
        }
        """))
    exe = _compile_swift(tmp_path, [SWIFT_CBOR, SWIFT_EXT, model, harness], "swift-ext-fail-closed")
    for mode in ["below-set", "below-get", "below-clear"]:
        run = subprocess.run([str(exe), mode], text=True, capture_output=True)
        assert run.returncode != 0, mode
        assert "below the band" in run.stderr + run.stdout, mode
    run = subprocess.run([str(exe), "hosts"], text=True, capture_output=True)
    assert run.returncode == 0, run.stderr + run.stdout
    decision = {"backend": "b7", "hops": 1}
    set_map = ext.ext_set(RESEXT, bytes.fromhex("a0"), "Decision", BAND_START, decision).hex()
    expected = [f"set map ok {set_map}", "get map ok null", "clear map ok a0"]
    for name, error in [("scalar", "WrongType(expected: map)"), ("array", "WrongType(expected: map)"),
                        ("truncated", "Truncated"), ("trailing", "TrailingBytes"),
                        ("empty", "Truncated")]:
        expected += [f"{op} {name} err {error}" for op in ("set", "get", "clear")]
    assert run.stdout.splitlines() == expected


def test_swift_resext_fixed_seed_fuzz(tmp_path):
    residual_rows, ext_rows = _resext_fuzz_rows()
    residual_blob = "\n".join(f"{note}|{wire}" for note, wire in residual_rows)
    ext_blob = "\n".join(
        "|".join(map(str, row))
        for row in ext_rows
    )
    model = _write_resext_model(tmp_path)
    harness = tmp_path / "main.swift"
    harness.write_text(_swift_support() + textwrap.dedent(f"""
        let seed = {RESEXT_FUZZ_SEED}
        let residualBlob = {_swift_string(residual_blob)}
        let extBlob = {_swift_string(ext_blob)}
        var mismatches = 0

        func check(_ condition: Bool, _ message: String) {{
            if !condition {{
                print(message)
                mismatches += 1
            }}
        }}

        for parts in fields(residualBlob) {{
            let note = String(parts[0])
            let wire = String(parts[1])
            let decoded = try! Host.fromCbor(tryDecode(bytes(fromHex: wire)))
            let got = hex(encode(decoded.toCbor()))
            check(got == wire, "seed=\\(seed) residual \\(note): input=\\(wire) got=\\(got)")
        }}

        for parts in fields(extBlob) {{
            let note = String(parts[0])
            let tag = Int64(parts[1])!
            let host = String(parts[2])
            let value = String(parts[3])
            let setExpect = String(parts[4])
            let getHost = String(parts[5])
            let getExpect = String(parts[6])
            let clearHost = String(parts[7])
            let clearExpect = String(parts[8])

            let decision = try! Decision.fromCbor(tryDecode(bytes(fromHex: value)))
            let setGot = hex(try extSet(bytes(fromHex: host), tag: tag, value: decision.toCbor()))
            check(setGot == setExpect, "seed=\\(seed) ext set \\(note): host=\\(host) got=\\(setGot) expect=\\(setExpect)")

            let raw = try extGet(bytes(fromHex: getHost), tag: tag)
            let getGot = raw.map {{ hex(encode((try! Decision.fromCbor($0)).toCbor())) }} ?? "null"
            check(getGot == getExpect, "seed=\\(seed) ext get \\(note): host=\\(getHost) got=\\(getGot) expect=\\(getExpect)")

            let clearGot = hex(try extClear(bytes(fromHex: clearHost), tag: tag))
            check(clearGot == clearExpect, "seed=\\(seed) ext clear \\(note): host=\\(clearHost) got=\\(clearGot) expect=\\(clearExpect)")
        }}

        if mismatches != 0 {{
            fatalError("swift resext fuzz seed=\\(seed) mismatches=\\(mismatches)")
        }}
        print("swift resext fuzz seed=\\(seed) iterations=\\(fields(residualBlob).count) mismatches=0")
        """))
    exe = _compile_swift(tmp_path, [SWIFT_CBOR, SWIFT_EXT, model, harness], "swift-resext-fuzz")
    run = subprocess.run([str(exe)], text=True, capture_output=True)
    assert run.returncode == 0, run.stderr + run.stdout
    assert f"swift resext fuzz seed={RESEXT_FUZZ_SEED} iterations=1000 mismatches=0" in run.stdout


def test_swift_runtime_float_vectors(tmp_path):
    swiftc = shutil.which("swiftc")
    if swiftc is None:
        pytest.skip("swiftc not found")

    rows = json.loads(FLOAT_VECTORS.read_text())
    vector_rows = ",\n".join(
        f'    ("{row["note"]}", "{row["f64"]}", "{row["cbor"]}")'
        for row in rows
    )
    harness = tmp_path / "main.swift"
    harness.write_text(textwrap.dedent(f"""
        let vectors: [(String, String, String)] = [
        {vector_rows}
        ]

        func bytes(fromHex hex: String) -> [UInt8] {{
            precondition(hex.count % 2 == 0)
            var bytes: [UInt8] = []
            var idx = hex.startIndex
            while idx < hex.endIndex {{
                let next = hex.index(idx, offsetBy: 2)
                bytes.append(UInt8(String(hex[idx..<next]), radix: 16)!)
                idx = next
            }}
            return bytes
        }}

        func hex(_ bytes: [UInt8]) -> String {{
            let digits = Array("0123456789abcdef".utf8)
            var out: [UInt8] = []
            out.reserveCapacity(bytes.count * 2)
            for b in bytes {{
                out.append(digits[Int(b >> 4)])
                out.append(digits[Int(b & 0x0f)])
            }}
            return String(decoding: out, as: UTF8.self)
        }}

        for (note, f64, expected) in vectors {{
            let bits = UInt64(f64, radix: 16)!
            let value = Double(bitPattern: bits)
            let encoded = hex(encode(.float(value)))
            if encoded != expected {{
                fatalError("encode \\(note): \\(encoded) != \\(expected)")
            }}

            let decoded = try tryDecode(bytes(fromHex: expected))
            let reencoded = hex(encode(decoded))
            if reencoded != expected {{
                fatalError("reencode \\(note): \\(reencoded) != \\(expected)")
            }}

            if !note.hasPrefix("nan") {{
                let decodedBits = try decoded.tryFloat().bitPattern
                if decodedBits != bits {{
                    fatalError("decode bits \\(note): \\(String(decodedBits, radix: 16)) != \\(f64)")
                }}
            }}
        }}
        """))
    exe = tmp_path / "swift-float-harness"
    compile_run = subprocess.run(
        [swiftc, str(SWIFT_CBOR), str(harness), "-o", str(exe)],
        text=True,
        capture_output=True,
    )
    assert compile_run.returncode == 0, compile_run.stderr

    run = subprocess.run([str(exe)], text=True, capture_output=True)
    assert run.returncode == 0, run.stderr


def test_generated_swift_float_model_roundtrips(tmp_path):
    swiftc = shutil.which("swiftc")
    if swiftc is None:
        pytest.skip("swiftc not found")

    schema = mk(Msg(
        "FloatBox",
        F("x", 1, FLOAT),
        F("maybe", 2, FLOAT, optional=True),
        F("xs", 3, List(FLOAT)),
        F("by_id", 4, Map(INT, FLOAT)),
        F("scratch", 5, FLOAT, transient=True),
    ))
    value = {
        "x": -0.0,
        "maybe": 0.1,
        "xs": [1.5, -0.0, 65504.0, 100000.0],
        "by_id": {7: -1.0, 2: 3.141592653589793},
        "scratch": 99.0,
    }
    expected_hex = codec.encode(schema, "FloatBox", value).hex()

    model = tmp_path / "FloatBox.swift"
    model.write_text(swift.emit_types(schema))
    harness = tmp_path / "main.swift"
    harness.write_text(textwrap.dedent(f"""
        func bytes(fromHex hex: String) -> [UInt8] {{
            precondition(hex.count % 2 == 0)
            var bytes: [UInt8] = []
            var idx = hex.startIndex
            while idx < hex.endIndex {{
                let next = hex.index(idx, offsetBy: 2)
                bytes.append(UInt8(String(hex[idx..<next]), radix: 16)!)
                idx = next
            }}
            return bytes
        }}

        func hex(_ bytes: [UInt8]) -> String {{
            let digits = Array("0123456789abcdef".utf8)
            var out: [UInt8] = []
            out.reserveCapacity(bytes.count * 2)
            for b in bytes {{
                out.append(digits[Int(b >> 4)])
                out.append(digits[Int(b & 0x0f)])
            }}
            return String(decoding: out, as: UTF8.self)
        }}

        let expected = "{expected_hex}"
        let box = FloatBox(
            x: -0.0,
            maybe: 0.1,
            xs: [1.5, -0.0, 65504.0, 100000.0],
            by_id: [7: -1.0, 2: 3.141592653589793],
            scratch: 99.0
        )

        let encoded = encode(box.toCbor())
        if hex(encoded) != expected {{
            fatalError("generated FloatBox encode: \\(hex(encoded)) != \\(expected)")
        }}

        let decoded = try! FloatBox.fromCbor(tryDecode(encoded))
        let reencoded = encode(decoded.toCbor())
        if reencoded != encoded {{
            fatalError("generated FloatBox reencode: \\(hex(reencoded)) != \\(hex(encoded))")
        }}

        let decodedFromExpected = try! FloatBox.fromCbor(tryDecode(bytes(fromHex: expected)))
        let reencodedExpected = hex(encode(decodedFromExpected.toCbor()))
        if reencodedExpected != expected {{
            fatalError("generated FloatBox expected reencode: \\(reencodedExpected) != \\(expected)")
        }}

        if decoded.x.bitPattern != 0x8000000000000000 {{
            fatalError("generated scalar float lost -0.0 bits")
        }}
        if decoded.xs.count != 4 || decoded.xs[1].bitPattern != 0x8000000000000000 {{
            fatalError("generated list float lost -0.0 bits")
        }}
        guard let maybe = decoded.maybe else {{
            fatalError("generated optional float decoded nil")
        }}
        if maybe != 0.1 {{
            fatalError("generated optional float decoded \\(maybe)")
        }}
        if decoded.by_id[7] != -1.0 || decoded.by_id[2] != 3.141592653589793 {{
            fatalError("generated map float decoded \\(decoded.by_id)")
        }}
        if decoded.scratch != 0.0 {{
            fatalError("generated transient float default decoded \\(decoded.scratch)")
        }}
        """))
    exe = tmp_path / "swift-generated-float-harness"
    compile_run = subprocess.run(
        [swiftc, str(SWIFT_CBOR), str(model), str(harness), "-o", str(exe)],
        text=True,
        capture_output=True,
    )
    assert compile_run.returncode == 0, compile_run.stderr

    run = subprocess.run([str(exe)], text=True, capture_output=True)
    assert run.returncode == 0, run.stderr
