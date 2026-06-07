"""Swift generator: native structs + enums + CBOR codec, forward-compat residual,
and Swift-keyword escaping. (Compile/run parity is verified out-of-band with
swiftc; this is the codegen-shape contract.)"""

from taut.corpus.build import IR_PATH
from taut.gen import swift
from taut.ir.load import load_schema

GRIPLAB = load_schema(IR_PATH)
RAZEL = load_schema(IR_PATH.parent / "razel.taut.py")


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
