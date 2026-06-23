"""Swift generator: native structs + enums + CBOR codec, forward-compat residual,
and Swift-keyword escaping. When swiftc is available, the vendored runtime is
also checked against the byte-exact float corpus."""

import json
import shutil
import subprocess
import textwrap
from pathlib import Path

from taut.corpus.build import IR_PATH
from taut.gen import swift
from taut.ir.dsl import FLOAT, INT, F, List, Map, Msg, schema as mk
from taut.ir.load import load_schema
from taut.wire import codec

import pytest

GRIPLAB = load_schema(IR_PATH)
RAZEL = load_schema(IR_PATH.parent / "razel.taut.py")
ROOT = Path(__file__).resolve().parents[2]
FLOAT_VECTORS = ROOT / "corpus" / "float_vectors.json"
SWIFT_CBOR = ROOT / "src/taut/gen/runtime/cbor.swift"


def test_emits_structs_enums_and_codec():
    s = swift.emit_types(RAZEL)
    assert "public struct BuildResult {" in s
    assert "public enum BuildStatus: Int64 {" in s
    assert "public func toCbor() -> Cbor" in s
    assert "public static func fromCbor(_ c: Cbor) -> BuildResult" in s
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
    assert "x: c.get(1).floatVal" in s
    assert "return v.isNull ? nil : v.floatVal" in s


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

        let decoded = FloatBox.fromCbor(decode(encoded))
        let reencoded = encode(decoded.toCbor())
        if reencoded != encoded {{
            fatalError("generated FloatBox reencode: \\(hex(reencoded)) != \\(hex(encoded))")
        }}

        let decodedFromExpected = FloatBox.fromCbor(decode(bytes(fromHex: expected)))
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
