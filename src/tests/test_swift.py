"""Swift generator: native structs + enums + CBOR codec, forward-compat residual,
and Swift-keyword escaping. When swiftc is available, the vendored runtime is
also checked against the byte-exact float corpus."""

import json
import os
import random
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path

from taut import ext
from taut.corpus.build import IR_PATH
from taut.corpus import resext_build as rb
from taut.gen import swift
from taut.ir.dsl import FLOAT, INT, F, List, Map, Msg, schema as mk
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
PARITY_IR = ROOT / "ir" / "parity_int.taut.py"
PARITY_INT_VECTORS = ROOT / "corpus" / "parity" / "int.vectors.json"
PARITY_MALFORMED_VECTORS = ROOT / "corpus" / "parity" / "malformed.vectors.json"
SWIFT_CBOR = ROOT / "src/taut/gen/runtime/cbor.swift"
SWIFT_EXT = ROOT / "src/taut/gen/runtime/ext.swift"
RESEXT_FUZZ_SEED = 0x55_0202


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


def _swift_i64(value: str) -> str:
    if value == "-9223372036854775808":
        return "Int64.min"
    if value == "9223372036854775807":
        return "Int64.max"
    return value


def _swift_intbox(value: dict[str, object]) -> str:
    entries = value["by_id"]
    if entries:
        by_id = "[" + ", ".join(
            f"{_swift_i64(str(k))}: {_swift_i64(str(v))}"
            for k, v in entries
        ) + "]"
    else:
        by_id = "[:]"
    return f"IntBox(n: {_swift_i64(str(value['n']))}, by_id: {by_id})"


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
    assert "public static func fromCbor(_ c: Cbor) throws -> BuildResult" in s
    assert "public static func fromCbor(_ c: Cbor) throws -> BuildStatus" in s
    assert "public init(" in s  # constructible cross-module


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
    assert "x: try c.tryGet(1).tryFloat()" in s
    assert "return try v.tryFloat()" in s


def test_swift_parity_corpus_vectors(tmp_path):
    int_vectors = json.loads(PARITY_INT_VECTORS.read_text())["vectors"]
    malformed_vectors = json.loads(PARITY_MALFORMED_VECTORS.read_text())["vectors"]
    round_trip_rows = [
        row for row in int_vectors
        if row["kind"] == "round_trip"
    ]
    encode_fail_count = sum(1 for row in int_vectors if row["kind"] == "encode_fail")
    round_trip_swift = ",\n".join(
        f"    ({_swift_string(row['name'])}, {_swift_string(row['cbor'])}, {{ {_swift_intbox(row['value'])} }})"
        for row in round_trip_rows
    )
    malformed_blob = "\n".join(
        "|".join([
            row["name"],
            row["stage"],
            row.get("schema", ""),
            row["bytes"],
            row["expect"]["tag"],
        ])
        for row in malformed_vectors
    )

    model = tmp_path / "Parity.swift"
    model.write_text(swift.emit_types(load_schema(PARITY_IR)))
    harness = tmp_path / "main.swift"
    harness.write_text(_swift_support() + textwrap.dedent(f"""
        let roundTripRows: [(String, String, () -> IntBox)] = [
        {round_trip_swift}
        ]
        let malformedBlob = {_swift_string(malformed_blob)}
        let encodeFailRows = {encode_fail_count}
        var mismatches = 0

        func check(_ condition: Bool, _ message: String) {{
            if !condition {{
                print(message)
                mismatches += 1
            }}
        }}

        func expectError(_ name: String, expectedTag: String, _ work: () throws -> Void) {{
            do {{
                try work()
                check(false, "\\(name): decoded successfully")
            }} catch let error as CborError {{
                check(error.parityTag == expectedTag, "\\(name): \\(error.parityTag) != \\(expectedTag) (\\(error))")
            }} catch {{
                check(false, "\\(name): non-CborError \\(error)")
            }}
        }}

        for (name, expected, makeValue) in roundTripRows {{
            let value = makeValue()
            let encoded = hex(encode(value.toCbor()))
            check(encoded == expected, "round trip encode \\(name): \\(encoded) != \\(expected)")

            do {{
                let decoded = try IntBox.fromCbor(tryDecode(bytes(fromHex: expected)))
                check(decoded.n == value.n, "round trip n \\(name): \\(decoded.n) != \\(value.n)")
                check(decoded.by_id == value.by_id, "round trip by_id \\(name): \\(decoded.by_id) != \\(value.by_id)")
                let reencoded = hex(encode(decoded.toCbor()))
                check(reencoded == expected, "round trip reencode \\(name): \\(reencoded) != \\(expected)")
            }} catch {{
                check(false, "round trip decode \\(name): \\(error)")
            }}
        }}

        for parts in fields(malformedBlob) {{
            let name = String(parts[0])
            let stage = String(parts[1])
            let schema = String(parts[2])
            let wire = String(parts[3])
            let expectedTag = String(parts[4])

            expectError(name, expectedTag: expectedTag) {{
                if stage == "raw_decode" {{
                    _ = try tryDecode(bytes(fromHex: wire))
                }} else if stage == "from_cbor" && schema == "IntBox" {{
                    _ = try IntBox.fromCbor(tryDecode(bytes(fromHex: wire)))
                }} else if stage == "from_wire" && schema == "Mode" {{
                    _ = try Mode.fromCbor(tryDecode(bytes(fromHex: wire)))
                }} else {{
                    throw CborError.wrongType("known parity stage")
                }}
            }}
        }}

        check(encodeFailRows == 3, "unexpected encode-fail count \\(encodeFailRows)")

        if mismatches != 0 {{
            fatalError("swift parity mismatches=\\(mismatches)")
        }}
        print("swift parity round_trip=\\(roundTripRows.count) malformed=\\(fields(malformedBlob).count) encode_fail_unrepresentable=\\(encodeFailRows) mismatches=0")
        """))
    exe = _compile_swift(tmp_path, [SWIFT_CBOR, model, harness], "swift-parity-corpus")
    run = subprocess.run([str(exe)], text=True, capture_output=True)
    assert run.returncode == 0, run.stderr + run.stdout
    assert "swift parity round_trip=7 malformed=12 encode_fail_unrepresentable=3 mismatches=0" in run.stdout


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
                let got = hex(extSet(bytes(fromHex: host), tag: tag, value: decision.toCbor()))
                check(got == expect, "ext set \\(note): \\(got) != \\(expect)")
            }} else if op == "get" {{
                let raw = extGet(bytes(fromHex: host), tag: tag)
                let got = raw.map {{ hex(encode((try! Decision.fromCbor($0)).toCbor())) }} ?? "null"
                check(got == expect, "ext get \\(note): \\(got) != \\(expect)")
            }} else if op == "clear" {{
                let got = hex(extClear(bytes(fromHex: host), tag: tag))
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


def test_swift_resext_invalid_cases_trap(tmp_path):
    model = _write_resext_model(tmp_path)
    harness = tmp_path / "main.swift"
    harness.write_text(_swift_support() + textwrap.dedent("""
        let mode = CommandLine.arguments[1]
        let tag: Int64 = 1 << 20
        let decision = Decision(backend: "b7", hops: 1)
        let scalarHost = bytes(fromHex: "01")

        if mode == "below-set" {
            _ = extSet([], tag: 7, value: decision.toCbor())
        } else if mode == "below-get" {
            _ = extGet([], tag: 7)
        } else if mode == "below-clear" {
            _ = extClear([], tag: 7)
        } else if mode == "nonmap-set" {
            _ = extSet(scalarHost, tag: tag, value: decision.toCbor())
        } else if mode == "nonmap-get" {
            _ = extGet(scalarHost, tag: tag)
        } else if mode == "nonmap-clear" {
            _ = extClear(scalarHost, tag: tag)
        } else {
            fatalError("unknown mode \\(mode)")
        }
        fatalError("invalid case did not trap")
        """))
    exe = _compile_swift(tmp_path, [SWIFT_CBOR, SWIFT_EXT, model, harness], "swift-resext-invalid")
    modes = ["below-set", "below-get", "below-clear", "nonmap-set", "nonmap-get", "nonmap-clear"]
    for mode in modes:
        run = subprocess.run([str(exe), mode], text=True, capture_output=True)
        assert run.returncode != 0, mode
        combined = run.stderr + run.stdout
        if mode.startswith("below-"):
            assert "below the band" in combined
        else:
            assert "not a map" in combined


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
            let setGot = hex(extSet(bytes(fromHex: host), tag: tag, value: decision.toCbor()))
            check(setGot == setExpect, "seed=\\(seed) ext set \\(note): host=\\(host) got=\\(setGot) expect=\\(setExpect)")

            let raw = extGet(bytes(fromHex: getHost), tag: tag)
            let getGot = raw.map {{ hex(encode((try! Decision.fromCbor($0)).toCbor())) }} ?? "null"
            check(getGot == getExpect, "seed=\\(seed) ext get \\(note): host=\\(getHost) got=\\(getGot) expect=\\(getExpect)")

            let clearGot = hex(extClear(bytes(fromHex: clearHost), tag: tag))
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

            let decoded = decode(bytes(fromHex: expected))
            let reencoded = hex(encode(decoded))
            if reencoded != expected {{
                fatalError("reencode \\(note): \\(reencoded) != \\(expected)")
            }}

            if !note.hasPrefix("nan") {{
                let decodedBits = decoded.floatVal.bitPattern
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
