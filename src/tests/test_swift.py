"""Swift generator: native structs + enums + CBOR codec, forward-compat residual,
Swift-keyword escaping and `optional=MISSING_OK`. When swiftc is available, the
vendored runtime is also checked against the byte-exact float corpus, and the
shared parity corpus is replayed through the gate's runner (`tautc parity -t swift`).

Checked decode (TautCheckedDecode.md, D26): no field named like a parameter, local or
runtime helper of the generated code breaks it, a repeated map key is reported as text
(question 9), and every public decode entry point, the extension helpers included,
returns or throws `CborError` (CD-E4, question 5).

Bounds (D26 §3, step D1): the raw decode counts depth and takes the caller's `maxDepth`,
capped at the ceiling, and `maxEncodedLen`, and agrees with Python's `cbor.loads`, the
reference, case by case; an argument out of range traps (TautOptions.md OPT-P3). Each
message carries its effective bounds as constants and a typed `decode` from bytes that
applies them (CD-B3, OPT-L6); the extension helpers read a host at the ceiling with no
length bound (G3); input nested 100,000 deep is `tooDeep`, never a crash."""

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
from taut.ir import options
from taut.ir.dsl import (
    BOOL, BYTES, FLOAT, INT, MISSING_OK, STR, Enum, F, List, Map, Msg, Ref, option, schema as mk,
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
# runtime's free functions; each message's own bounds and typed decode (a static member
# beside an instance field of the same name). Kind's members are named like the enum
# decoder's locals, and Level, which has no member 0, types a transient field, whose
# default applies on decode.
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
        F("maxDepth", 14, INT),
        F("maxEncodedLen", 15, INT, optional=True),
        F("decode", 16, STR),
        F("defaultMaxDepth", 17, INT),
        F("maxDepthCeiling", 18, INT),
        next_id=19),
)
CLASH_VALUE = {
    "c": 1, "v": None, "raw": "value", "value": "x", "decodeDictionary": {"a": 1},
    "tryDictionary": {True: "c"}, "tryGet": [{"v": 5}], "isNull": {3: {"v": 4}},
    "mapEntries": True, "encode": b"\x01\x02", "tryDecode": 1.5, "tryArray": [["p"]],
    "maxDepth": 7, "maxEncodedLen": None, "decode": "d", "defaultMaxDepth": 8,
    "maxDepthCeiling": 9,
}
# A file that declares both bounds, a message that overrides one and one that inherits both
# (test_bounds.py's FILED, without its enum): the constants are each message's effective values.
FILED = mk(
    option.max_depth(3), option.max_encoded_len(16),
    Msg("Tree", F("kids", 1, List(Ref("Tree"))), option.max_depth(64), next_id=2),
    Msg("Plain", F("v", 1, List(INT)), next_id=2),
)
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

        func expand(_ segments: [(String, Int)]) -> [UInt8] {
            var out: [UInt8] = []
            for (unit, count) in segments {
                let piece = bytes(fromHex: unit)
                for _ in 0..<count {
                    out.append(contentsOf: piece)
                }
            }
            return out
        }
        """)


Segments = list[tuple[str, int]]


def _nest(opener: str, count: int, leaf: str) -> Segments:
    """`count` openers around a leaf, as `(hex, count)` segments that `expand` rebuilds, so
    that input 100,000 deep stays a short line of Swift."""
    return [(opener, count), (leaf, 1)]


def _swift_segments(segments: Segments) -> str:
    return "[" + ", ".join(f'("{unit}", {count})' for unit, count in segments) + "]"


def _expanded(segments: Segments) -> bytes:
    return b"".join(bytes.fromhex(unit) * count for unit, count in segments)


def _swift_error(exc: cbor.DecodeError) -> str:
    """A DecodeError as the Swift runtime describes its CborError: `Tag(field: value, ...)`."""
    if not exc.payload:
        return exc.tag
    return exc.tag + "(" + ", ".join(f"{name}: {value}" for name, value in exc.payload.items()) + ")"


def _reference(data: bytes, decode, encode) -> str:
    """Python's outcome, as the harnesses print theirs: `ok same` when the value re-encodes to
    the input (D2's law), `ok <hex>` otherwise, or `err <description>`."""
    try:
        again = encode(decode(data))
    except cbor.DecodeError as exc:
        return "err " + _swift_error(exc)
    return "ok same" if again == data else f"ok {again.hex()}"


_SWIFT_OUTCOME = textwrap.dedent("""
    func outcome(_ data: [UInt8], _ work: () throws -> [UInt8]) -> String {
        do {
            let again = try work()
            return again == data ? "ok same" : "ok \\(hex(again))"
        } catch let error as CborError {
            return "err \\(error)"
        } catch {
            return "untyped \\(type(of: error)) \\(error)"
        }
    }
    """)


def _first_difference(got: list[str], want: list[str]) -> str:
    """Where two outcome listings part, each line cut short (some are 200 KB of hex)."""
    for index, (left, right) in enumerate(zip(got, want)):
        if left != right:
            return f"line {index}: got {left[:200]!r}, want {right[:200]!r}"
    return f"{len(got)} lines, want {len(want)}"


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
        bound = (re.findall(r"static func \w+\(_ (\w+): (?:Cbor|\[UInt8\])\)", s)
                 + re.findall(r"\blet (\w+) = ", s))
        assert {"wire_c", "wire_v", "wire_raw", "wire_value", "wire_bytes"} <= set(bound)
        assert [name for name in bound if not name.startswith("wire_")] == []
        # a call, not the declaration of a message's own `decode`
        assert re.findall(r"(?<![\w.])(?<!func )(?:encode|decode|tryDecode|decodeDictionary)\(", s) == []
        assert "try wire_c.tryGet(14).tryDictionary(key: { try $0.tryText() }, " in s
        # the runtime's raw decode and the message's own members, qualified: no field hides them
        # (a name before `:` is a declaration or an argument label, not a reference)
        assert "Cbor.tryDecode(wire_bytes, maxDepth: Self.maxDepth, maxEncodedLen: Self.maxEncodedLen)" in s
        assert re.findall(r"(?<![\w.])(?<!func )(?:maxDepth|maxEncodedLen|fromCbor|defaultMaxDepth"
                          r"|maxDepthCeiling)\b(?!:)", s) == []


def _struct(source: str, name: str) -> str:
    """The generated struct `name`, up to the next top-level declaration."""
    start = source.index(f"public struct {name} {{")
    end = source.find("\npublic ", start)
    return source[start:] if end < 0 else source[start:end]


def test_each_message_carries_its_effective_bounds_and_a_typed_decode():
    """CD-B3, OPT-L6: each message has its effective `max_depth` and `max_encoded_len`, as
    `taut.ir.options.effective` resolves them when the code is generated, as the static
    constants `maxDepth` and `maxEncodedLen` (nil: no length bound), and a throwing `decode`
    from bytes that applies both through the runtime's raw decode, then `fromCbor`."""
    declared = {("fixture", "Tree64"): (64, None), ("fixture", "Tree128"): (128, None),
                ("fixture", "Flat2"): (2, None), ("fixture", "Sized8"): (32, 8),
                ("fixture", "Holds64"): (32, None), ("fixture", "HoldsSized8"): (32, None),
                ("fixture", "IntBox"): (32, None), ("filed", "Tree"): (64, 16),
                ("filed", "Plain"): (3, 16)}
    seen = {}
    for label, schema in (("fixture", parity.parity_schema()), ("filed", FILED)):
        for forward_compat in (False, True):
            source = swift.emit_types(schema, forward_compat=forward_compat)
            for name in schema.messages:
                depth = options.effective(schema, "max_depth", message=name)
                length = options.effective(schema, "max_encoded_len", message=name)
                seen[(label, name)] = (depth, length)
                struct = _struct(source, name)
                assert f"\n    public static let maxDepth: Int = {depth}\n" in struct, name
                assert (f"\n    public static let maxEncodedLen: Int? = "
                        f"{'nil' if length is None else length}\n") in struct, name
                assert (f"\n    public static func decode(_ wire_bytes: [UInt8]) throws -> {name} {{\n"
                        "        return try Self.fromCbor(Cbor.tryDecode(wire_bytes, maxDepth: Self.maxDepth, "
                        "maxEncodedLen: Self.maxEncodedLen))\n    }\n") in struct, name
    assert {key: seen[key] for key in declared} == declared
    # the generated targets add both per message (TautV010Plan.md §0); an enum has neither
    enum = swift.emit_types(parity.parity_schema())
    enum = enum[enum.index("public enum Mode"):enum.index("public struct")]
    assert "maxDepth" not in enum and "func decode(" not in enum


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


def test_the_runner_speaks_the_bounds_protocol():
    """The runner's side of C3's protocol (parity.py's docstring): the #constants line from the
    runtime's own constants; every decode row, bounds rows included, as segments the runner
    expands and checks against `len`, so a 100,000-deep row stays a short line; and every
    message's typed decode and constants, through which each from_cbor row decodes and
    reports the bounds it resolved (the gate judges the rest: test_swift_parity_gate_is_green)."""
    source = parity_swift._source()
    assert '"#constants\\tdefault_max_depth=\\(defaultMaxDepth);max_depth_ceiling=\\(maxDepthCeiling)"' in source
    assert len(source) < 100_000
    for row in parity.decode_rows():
        assert f'name: "{row["name"]}"' in source, row["name"]
    for name in parity.fixture_dispatch().messages:
        assert f"try {name}.decode(data)" in source and f"{name}.maxEncodedLen" in source, name


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
                          tryDecode: 1.5, tryArray: [["p"]], maxDepth: 7, maxEncodedLen: nil,
                          decode: "d", defaultMaxDepth: 8, maxDepthCeiling: 9)
        print(hex(encode(built.toCbor())))
        let typed = try Clash.decode(bytes(fromHex: "{wire}"))
        print(hex(encode(typed.toCbor())))
        print(Clash.maxDepth, Clash.maxEncodedLen == nil, typed.maxDepth, typed.decode)
        """))
    exe = _compile_swift(tmp_path, [generated / "cbor.swift", generated / "api.swift", harness],
                         "swift-clash")
    run = subprocess.run([str(exe)], text=True, capture_output=True)
    assert run.returncode == 0, run.stderr + run.stdout
    assert run.stdout.splitlines() == [wire, "true", wire, wire, "32 true 7 d"]


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
    """Every parity row's bytes (a bounds row's where it is short), the heads that claim the
    largest lengths and counts, and fixed-seed mutations of each: a byte changed, the tail
    cut, a byte inserted or a run of bytes repeated (which repeats keys and entries)."""
    rng = random.Random(FAIL_CLOSED_SEED)
    seeds = [bytes.fromhex(row["bytes"]) for row in parity.malformed_rows()]
    seeds += [bytes.fromhex(row["cbor"]) for row in parity.int_rows() if "cbor" in row]
    seeds += [parity.row_bytes(row) for row in parity.bounds_rows() if row["len"] <= 200]
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
    the raw decode (a free function and a member of Cbor), each accessor, each fixture
    message's typed decode from bytes and fromCbor (and the decoded message's re-encoding),
    each enum's fromCbor and the three ext helpers. A trap fails the run; any other error
    is counted as escaped. (Deep nesting, which would exhaust the stack without the depth
    bound, is `test_swift_deep_input_is_too_deep_not_a_crash`.)"""
    _require_swiftc()
    generated = _emit_swift(parity.parity_schema(), tmp_path / "gen", forward_compat)
    dispatch = parity.fixture_dispatch()
    from_bytes = [f'    observe("{name}.decode", wire) {{ _ = encode(try {name}.decode(data).toCbor()) }}'
                  for name in dispatch.messages]
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
        """) + "\n".join(from_bytes) + textwrap.dedent("""
            observe("Cbor.tryDecode", wire) { _ = try Cbor.tryDecode(data, maxDepth: 1, maxEncodedLen: 64) }
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


# --- bounds (D26 §3): the raw decode, the typed decode, the extension helpers -----------------

BIG_BYTES = cbor.dumps(b"x" * 100_000)            # a byte string of 100,005 bytes in all
BIG_SEGMENTS = [(BIG_BYTES[:5].hex(), 1), ("78", 100_000)]


def _raw_cases() -> list[tuple[Segments, int | None, int | None]]:
    """test_cbor.py's cases for the bounds, as (input, maxDepth, maxEncodedLen), None where
    the call leaves the argument to its default: 32 and no length bound."""
    cases: list[tuple[Segments, int | None, int | None]] = []
    for opener, leaf in (("81", "80"), ("a100", "a0"), ("81", "a0"), ("a100", "80")):
        cases += [(_nest(opener, 31, leaf), None, None), (_nest(opener, 32, "00"), None, None),
                  (_nest(opener, 32, leaf), None, None)]        # 32 containers, a scalar, the 33rd
    cases += [(_nest("81a100", 16, leaf), None, None) for leaf in ("00", "80", "a0")]
    for wire in ("00", "6161", "80", "a0", "8100", "a10000", "820102",      # depth 1 at bound 1
                 "8180", "81a0", "a10080", "a100a0", "820180"):             # depth 2
        cases.append(([(wire, 1)], 1, None))
    cases += [([("a18000", 1)], 1, None), ([("a18000", 1)], 2, None)]      # a key is an item
    for depth in (1, 2, 5, 31, 33, 64, 127, 128):                           # as given
        cases += [(_nest("81", depth - 1, "80"), depth, None), (_nest("81", depth, "80"), depth, None)]
    for depth in (129, 1000, 2**31, 2**63 - 1):                             # above the ceiling
        cases += [(_nest("81", 127, "80"), depth, None), (_nest("81", 128, "80"), depth, None)]
    # once the head is complete, items missing or not; a torn head, and its own faults, first
    for leaf in ("", "9bffffffffffffffff", "bbffffffffffffffff", "98", "9900", "9a000000", "9b00",
                 "b8", "bb00000000000000", "9800", "9c", "bf"):
        cases.append((_nest("81", 32, leaf), None, None))
    cases += [(_nest("81", 33, ""), None, None), (_nest("a100", 32, "a1"), None, None)]
    for opener, leaf in (("81", "80"), ("a100", "a0"), ("81a100", "80")):   # 100,000 deep
        cases += [(_nest(opener, 100_000, leaf), depth, None) for depth in (None, 128, 10**9)]
    # the length bound: at it and beyond it, before any byte is read, and zero
    cases += [([("83010203", 1)], None, length) for length in (4, 2**40, 3)]
    cases += [(BIG_SEGMENTS, None, length) for length in (None, len(BIG_BYTES), len(BIG_BYTES) - 1)]
    cases += [([("c0c0c0c0", 1)], None, 3), (_nest("81", 40, "80"), None, 10), ([("0000", 1)], None, 1),
              ([("", 1)], None, 0), ([("00", 1)], None, 0)]
    # both: the length first, then the depth, and within both
    cases += [(_nest("81", 40, "80"), 64, 10), (_nest("81", 40, "80"), 8, 41), (_nest("81", 3, "80"), 4, 4)]
    return cases


def _loads(depth: int | None, length: int | None):
    limits = {name: value for name, value in (("max_depth", depth), ("max_encoded_len", length))
              if value is not None}
    return lambda data: cbor.loads(data, **limits)


def test_swift_raw_decode_bounds_match_the_reference(tmp_path):
    """CD-B1-B5, CD-E5, question 1: the raw decode, `tryDecode` and the `Cbor.tryDecode`
    member generated code calls, counts depth (a top-level container has depth 1, one at
    maxDepth + 1 is tooDeep once its head is complete), takes maxDepth (32 by default, above
    128 the ceiling) and maxEncodedLen (none by default, checked before any byte), and agrees
    with Python's `cbor.loads` on every case; the runtime's two constants are taut's."""
    _require_swiftc()
    cases = _raw_cases()
    table = ",\n".join(
        f"    Case(input: {_swift_segments(segments)}, maxDepth: {'nil' if depth is None else depth}, "
        f"maxEncodedLen: {'nil' if length is None else length})" for segments, depth, length in cases)
    harness = tmp_path / "main.swift"
    harness.write_text(_swift_support() + _SWIFT_OUTCOME + textwrap.dedent("""
        struct Case {
            let input: [(String, Int)]
            let maxDepth: Int?
            let maxEncodedLen: Int?
        }

        /// The free function, each argument given or left to its default.
        func viaFunction(_ data: [UInt8], _ c: Case) throws -> Cbor {
            switch (c.maxDepth, c.maxEncodedLen) {
            case (nil, nil):
                return try tryDecode(data)
            case let (depth?, nil):
                return try tryDecode(data, maxDepth: depth)
            case let (nil, length?):
                return try tryDecode(data, maxEncodedLen: length)
            case let (depth?, length?):
                return try tryDecode(data, maxDepth: depth, maxEncodedLen: length)
            }
        }

        /// The member of Cbor that generated code calls, the same way.
        func viaMember(_ data: [UInt8], _ c: Case) throws -> Cbor {
            switch (c.maxDepth, c.maxEncodedLen) {
            case (nil, nil):
                return try Cbor.tryDecode(data)
            case let (depth?, nil):
                return try Cbor.tryDecode(data, maxDepth: depth)
            case let (nil, length?):
                return try Cbor.tryDecode(data, maxEncodedLen: length)
            case let (depth?, length?):
                return try Cbor.tryDecode(data, maxDepth: depth, maxEncodedLen: length)
            }
        }

        print("constants \\(defaultMaxDepth) \\(maxDepthCeiling)")
        """) + "let cases: [Case] = [\n" + table + "\n]\n" + textwrap.dedent("""
        for c in cases {
            let data = expand(c.input)
            print(outcome(data) { encode(try viaFunction(data, c)) })
            print(outcome(data) { encode(try viaMember(data, c)) })
        }
        """))
    exe = _compile_swift(tmp_path, [SWIFT_CBOR, harness], "swift-raw-bounds")
    run = subprocess.run([str(exe)], text=True, capture_output=True)
    assert run.returncode == 0, run.stderr[-1500:]
    want = [f"constants {cbor.DEFAULT_MAX_DEPTH} {cbor.MAX_DEPTH_CEILING}"]
    for segments, depth, length in cases:
        want += [_reference(_expanded(segments), _loads(depth, length), cbor.dumps)] * 2
    got = run.stdout.splitlines()
    assert got == want, _first_difference(got, want)
    assert (cbor.DEFAULT_MAX_DEPTH, cbor.MAX_DEPTH_CEILING) == (options.DEFAULT_MAX_DEPTH,
                                                                options.MAX_DEPTH_CEILING)


def test_swift_raw_decode_argument_out_of_range_traps(tmp_path):
    """OPT-P3: a maxDepth below 1 or a negative maxEncodedLen is the caller's error, not the
    input's (Python's ValueError): it traps, before any byte is read, and names the argument,
    through either entry point. In range, the input decides."""
    _require_swiftc()
    harness = tmp_path / "main.swift"
    harness.write_text(_swift_support() + textwrap.dedent("""
        let arguments = CommandLine.arguments
        let depth = Int(arguments[2])!
        let length: Int? = arguments[3] == "none" ? nil : Int(arguments[3])!
        let data = bytes(fromHex: arguments[4])
        do {
            let value: Cbor
            if arguments[1] == "member" {
                value = try Cbor.tryDecode(data, maxDepth: depth, maxEncodedLen: length)
            } else {
                value = try tryDecode(data, maxDepth: depth, maxEncodedLen: length)
            }
            print("ok \\(hex(encode(value)))")
        } catch {
            print("err \\(error)")
        }
        """))
    exe = _compile_swift(tmp_path, [SWIFT_CBOR, harness], "swift-raw-arguments")
    int_min = str(-(2**63))
    for entry in ("function", "member"):
        for depth, length, wire, named in [
            ("0", "none", "", "maxDepth"), ("-1", "none", "00", "maxDepth"),
            (int_min, "none", "c0c0c0c0", "maxDepth"), ("0", "-1", "00", "maxDepth"),
            ("32", "-1", "", "maxEncodedLen"), ("32", int_min, "c0c0c0c0", "maxEncodedLen"),
        ]:
            run = subprocess.run([str(exe), entry, depth, length, wire], text=True, capture_output=True)
            assert run.returncode != 0 and run.stdout == "", (entry, depth, length, run.stdout)
            assert named in run.stderr, (entry, depth, length, run.stderr)
        for depth, length, wire, want in [("1", "0", "", "err Truncated"), ("1", "none", "00", "ok 00"),
                                          ("1", "0", "00", "err TooLarge(len: 1, limit: 0)")]:
            run = subprocess.run([str(exe), entry, depth, length, wire], text=True, capture_output=True)
            assert (run.returncode, run.stdout.strip()) == (0, want), (entry, depth, length, run.stderr)


def test_swift_typed_decode_applies_its_roots_bounds(tmp_path):
    """CD-B3, OPT-D4: a message's `decode` applies its own effective bounds to the whole call,
    whatever the messages nested inside declare, as Python's `codec.decode` does: the fixture's
    declared, inherited and default bounds, and a file's bounds (FILED) where a message declares
    none. 100,000-deep input is tooDeep at the root's bound."""
    _require_swiftc()
    fixture = parity.parity_schema()
    cases = [
        (fixture, "Tree64", [("a10181", 100_000), ("a10180", 1)]),
        (fixture, "Tree128", [("a10181", 100_000), ("a10180", 1)]),
        (fixture, "Holds64", [("a10181", 100_000), ("a10180", 1)]),
        (fixture, "IntBox", [("81", 100_000), ("80", 1)]),
        (fixture, "Tree64", [("a10181", 63), ("a10180", 1)]),             # 128 deep, over 64
        (fixture, "Holds64", [("a101", 1), ("a10181", 15), ("a10180", 1)]),  # 33 deep, over 32
        (fixture, "Flat2", [("a1018100", 1)]), (fixture, "Flat2", [("a1018180", 1)]),
        (fixture, "Sized8", [("a101450102030405", 1)]), (fixture, "Sized8", [("a10146010203040506", 1)]),
        (fixture, "HoldsSized8", [("a101a1014a00010203040506070809", 1)]),
        (FILED, "Tree", [("a10181a10180", 1)]), (FILED, "Plain", [("a10181818100", 1)]),
        (FILED, "Plain", [("a1018d", 1), ("00", 13)]), (FILED, "Plain", [("a1018e", 1), ("00", 14)]),
        (FILED, "Tree", [("a1018e", 1), ("00", 14)]),
    ]
    generated = _emit_swift(fixture, tmp_path / "gen")
    filed = tmp_path / "filed.swift"
    filed.write_text(swift.emit_types(FILED))
    names = [*fixture.messages, *FILED.messages]
    arms = "\n".join(f'    case "{name}":\n        return encode(try {name}.decode(data).toCbor())'
                     for name in names)
    constants = "\n".join(f'print("{name} \\({name}.maxDepth) \\({name}.maxEncodedLen.map {{ String($0) }} '
                          f'?? "nil")")' for name in names)
    table = ",\n".join(f'    ("{message}", {_swift_segments(segments)})' for _, message, segments in cases)
    harness = tmp_path / "main.swift"
    harness.write_text(_swift_support() + _SWIFT_OUTCOME
                       + "func typed(_ message: String, _ data: [UInt8]) throws -> [UInt8] {\n"
                       + "    switch message {\n" + arms + "\n    default:\n"
                       + '        fatalError("no message \\(message)")\n    }\n}\n' + constants + "\n"
                       + "let cases: [(String, [(String, Int)])] = [\n" + table + "\n]\n"
                       + textwrap.dedent("""
        for (message, input) in cases {
            let data = expand(input)
            print(outcome(data) { try typed(message, data) })
        }
        """))
    exe = _compile_swift(tmp_path, [generated / "cbor.swift", generated / "api.swift", filed, harness],
                         "swift-typed-bounds")
    run = subprocess.run([str(exe)], text=True, capture_output=True)
    assert run.returncode == 0, run.stderr[-1500:]
    want = []
    for schema in (fixture, FILED):
        for name in schema.messages:
            length = options.effective(schema, "max_encoded_len", message=name)
            want.append(f"{name} {options.effective(schema, 'max_depth', message=name)} "
                        f"{'nil' if length is None else length}")
    for schema, message, segments in cases:
        want.append(_reference(_expanded(segments),
                               lambda data, s=schema, m=message: codec.decode(s, m, data),
                               lambda value, s=schema, m=message: codec.encode(s, m, value)))
    got = run.stdout.splitlines()
    assert got == want, _first_difference(got, want)
    assert "err TooDeep(limit: 64)" in got and "err TooLarge(len: 17, limit: 16)" in got


def test_swift_deep_input_is_too_deep_not_a_crash(tmp_path):
    """CD-E4, B9-B10: input nested 100,000 deep is tooDeep at the bound each entry point
    applies, with no stack overflow and no trap: the raw decode at 32, at the ceiling and
    capped there, each message's typed decode at its own bound, and the ext helpers at 128."""
    _require_swiftc()
    generated = _emit_swift(parity.parity_schema(), tmp_path / "gen", forward_compat=True)
    harness = tmp_path / "main.swift"
    harness.write_text(_swift_support() + textwrap.dedent("""
        func observe(_ what: String, _ work: () throws -> Void) {
            do {
                try work()
                print("\\(what) ok")
            } catch let error as CborError {
                print("\\(what) \\(error)")
            } catch {
                print("\\(what) untyped \\(error)")
            }
        }

        let tag: Int64 = 1 << 20
        for (name, opener, leaf) in [("arrays", "81", "80"), ("maps", "a100", "a0")] {
            let data = expand([(opener, 99_999), (leaf, 1)])
            observe("\\(name) tryDecode") { _ = try tryDecode(data) }
            observe("\\(name) ceiling") { _ = try Cbor.tryDecode(data, maxDepth: maxDepthCeiling) }
            observe("\\(name) capped") { _ = try tryDecode(data, maxDepth: Int.max) }
            observe("\\(name) IntBox") { _ = try IntBox.decode(data) }
            observe("\\(name) extGet") { _ = try extGet(data, tag: tag) }
            observe("\\(name) extSet") { _ = try extSet(data, tag: tag, value: .null) }
            observe("\\(name) extClear") { _ = try extClear(data, tag: tag) }
        }
        let trees = expand([("a10181", 99_999), ("a10180", 1)])
        observe("trees Tree64") { _ = try Tree64.decode(trees) }
        observe("trees Tree128") { _ = try Tree128.decode(trees) }
        observe("trees Holds64") { _ = try Holds64.decode(trees) }
        """))
    exe = _compile_swift(tmp_path, [generated / "cbor.swift", generated / "ext.swift",
                                    generated / "api.swift", harness], "swift-deep")
    run = subprocess.run([str(exe)], text=True, capture_output=True)
    assert run.returncode == 0, run.stderr[-1500:]
    want = []
    for name in ("arrays", "maps"):
        want += [f"{name} {entry} TooDeep(limit: {limit})" for entry, limit in (
            ("tryDecode", 32), ("ceiling", 128), ("capped", 128), ("IntBox", 32),
            ("extGet", 128), ("extSet", 128), ("extClear", 128))]
    want += ["trees Tree64 TooDeep(limit: 64)", "trees Tree128 TooDeep(limit: 128)",
             "trees Holds64 TooDeep(limit: 32)"]
    assert run.stdout.splitlines() == want


def test_swift_ext_helpers_read_the_host_at_the_ceiling_with_no_length_bound(tmp_path):
    """TautOptions.md G3, CD-E4: not knowing the host's root (they take no schema), the
    helpers read a host at the depth ceiling with no length bound, the only bounds every
    valid host meets, as Python's do: a host 128 deep works, one 129 deep or far deeper is
    tooDeep(128), and a host of 100,000 bytes needs no length bound."""
    _require_swiftc()
    decision = {"backend": "b7", "hops": 1}
    hosts = [
        ("ceiling", [("a107", 1), ("81", 126), ("80", 1)]),       # a map around 127 arrays: 128
        ("beyond", [("a107", 1), ("81", 127), ("80", 1)]),        # 129
        ("deep", [("a107", 1), ("81", 99_999), ("80", 1)]),
        ("big", [(cbor.dumps({1: 1, 7: b""})[:-1].hex(), 1), *BIG_SEGMENTS]),
    ]
    model = _write_resext_model(tmp_path)
    table = ",\n".join(f'    ("{name}", {_swift_segments(segments)})' for name, segments in hosts)
    harness = tmp_path / "main.swift"
    harness.write_text(_swift_support() + textwrap.dedent("""
        let tag: Int64 = 1 << 20
        let decision = Decision(backend: "b7", hops: 1)

        func observe(_ what: String, _ work: () throws -> String) {
            do {
                print("\\(what) ok \\(try work())")
            } catch let error as CborError {
                print("\\(what) err \\(error)")
            } catch {
                print("\\(what) untyped \\(error)")
            }
        }

        """) + "let hosts: [(String, [(String, Int)])] = [\n" + table + "\n]\n" + textwrap.dedent("""
        for (name, segments) in hosts {
            let host = expand(segments)
            observe("set \\(name)") { hex(try extSet(host, tag: tag, value: decision.toCbor())) }
            observe("get \\(name)") { try extGet(host, tag: tag).map { hex(encode($0)) } ?? "null" }
            observe("clear \\(name)") { hex(try extClear(host, tag: tag)) }
            observe("strapped \\(name)") {
                let strapped = try extSet(host, tag: tag, value: decision.toCbor())
                return try extGet(strapped, tag: tag).map { hex(encode($0)) } ?? "null"
            }
        }
        """))
    exe = _compile_swift(tmp_path, [SWIFT_CBOR, SWIFT_EXT, model, harness], "swift-ext-bounds")
    run = subprocess.run([str(exe)], text=True, capture_output=True)
    assert run.returncode == 0, run.stderr[-1500:]

    def reference(call) -> str:
        try:
            return "ok " + call()
        except cbor.DecodeError as exc:
            return "err " + _swift_error(exc)

    def got_decision(host: bytes) -> str:
        value = ext.ext_get(RESEXT, host, "Decision", BAND_START)
        return "null" if value is None else codec.encode(RESEXT, "Decision", value).hex()

    want = []
    for name, segments in hosts:
        host = _expanded(segments)
        want += [
            f"set {name} " + reference(lambda: ext.ext_set(RESEXT, host, "Decision", BAND_START, decision).hex()),
            f"get {name} " + reference(lambda: got_decision(host)),
            f"clear {name} " + reference(lambda: ext.ext_clear(host, BAND_START).hex()),
            f"strapped {name} " + reference(lambda: got_decision(
                ext.ext_set(RESEXT, host, "Decision", BAND_START, decision))),
        ]
    got = run.stdout.splitlines()
    assert got == want, _first_difference(got, want)
    assert got[4:8] == [f"{op} beyond err TooDeep(limit: 128)" for op in ("set", "get", "clear", "strapped")]
    assert got[3] == "strapped ceiling ok " + codec.encode(RESEXT, "Decision", decision).hex()


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
