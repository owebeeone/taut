"""Swift runner for the parity gate, modelled on `parity_rust.py`.

The gate finds it by module name (`parity._RUNNERS`) and calls `run()`:

  1. find swiftc (`toolchains.find_swiftc`); a missing one is the only skip;
  2. generate the fixture's Swift with its vendored runtime (`parity.generate`);
     a refusal is RED;
  3. write `main.swift`, whose row tables come from `parity.int_rows()` and
     `parity.malformed_rows()` and whose dispatch comes from
     `parity.fixture_dispatch()`, never from hard-coded message names;
  4. build it with swiftc (`parity.build`); a failure is RED;
  5. run it (`parity.run_runner`), which parses and judges its report.

The runner prints `name<TAB>outcome<TAB>detail` per row. It checks int rows
itself; for a malformed row it only reports what happened (`ok` with the hex of the
re-encoding; `err` with the tag and payload; `untyped` for any other thrown error)
and the gate judges it.
Swift cannot catch a trap, so the runner flushes each line: a trap leaves the rows
before it reported and fails the target through the runner's exit status.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from . import parity, toolchains

TARGET = "swift"

_MAIN = r'''
import Foundation

struct IntRow {
    let name: String
    let cbor: String
    let n: String
    let byId: [(String, String)]
}

struct EncFail {
    let name: String
    let ints: [String]
}

struct Mal {
    let name: String
    let stage: String
    let schema: String
    let bytes: String
}

enum RunnerError: Error, CustomStringConvertible {
    case badRow(String)
    case noEntryPoint(String)

    var description: String {
        switch self {
        case let .badRow(why):
            return "bad row: \(why)"
        case let .noEntryPoint(why):
            return why
        }
    }
}

let roundTrip: [IntRow] = [
@ROUND_TRIP@
]
let encodeFail: [EncFail] = [
@ENCODE_FAIL@
]
let malformed: [Mal] = [
@MALFORMED@
]

func nibble(_ c: UInt8) -> UInt8? {
    switch c {
    case UInt8(ascii: "0")...UInt8(ascii: "9"):
        return c - UInt8(ascii: "0")
    case UInt8(ascii: "a")...UInt8(ascii: "f"):
        return c - UInt8(ascii: "a") + 10
    case UInt8(ascii: "A")...UInt8(ascii: "F"):
        return c - UInt8(ascii: "A") + 10
    default:
        return nil
    }
}

func unhex(_ s: String) throws -> [UInt8] {
    let digits = Array(s.utf8)
    guard digits.count % 2 == 0 else {
        throw RunnerError.badRow("odd-length hex \(s)")
    }
    var out: [UInt8] = []
    out.reserveCapacity(digits.count / 2)
    var i = 0
    while i < digits.count {
        guard let hi = nibble(digits[i]), let lo = nibble(digits[i + 1]) else {
            throw RunnerError.badRow("bad hex \(s)")
        }
        out.append(hi << 4 | lo)
        i += 2
    }
    return out
}

func hexOf(_ bytes: [UInt8]) -> String {
    let digits = Array("0123456789abcdef".utf8)
    var out: [UInt8] = []
    out.reserveCapacity(bytes.count * 2)
    for b in bytes {
        out.append(digits[Int(b >> 4)])
        out.append(digits[Int(b & 0x0f)])
    }
    return String(decoding: out, as: UTF8.self)
}

func emit(_ name: String, _ outcome: String, _ detail: String) {
    var clean = String.UnicodeScalarView()
    for scalar in detail.unicodeScalars {
        if scalar == "\t" || scalar == "\n" || scalar == "\r" {
            clean.append(" ")
        } else {
            clean.append(scalar)
        }
    }
    print("\(name)\t\(outcome)\t\(String(clean))")
    fflush(stdout)
}

/// A from_cbor row's typed entry point, by message name (from the fixture schema):
/// the decoded value's own encoding.
func fromCbor(_ message: String, _ c: Cbor) throws -> [UInt8] {
    switch message {
@FROM_CBOR@
    default:
        throw RunnerError.noEntryPoint("no from_cbor entry point for \(message)")
    }
}

/// A from_wire row's typed entry point, by enum name (from the fixture schema).
func fromWire(_ name: String, _ c: Cbor) throws {
    switch name {
@FROM_WIRE@
    default:
        throw RunnerError.noEntryPoint("no from_wire entry point for \(name)")
    }
}

/// A decoded row's re-encoding: the tree for raw_decode, the typed value for
/// from_cbor, and nothing for from_wire (an enum row never accepts).
func decodeRow(_ row: Mal) throws -> [UInt8] {
    let c = try tryDecode(try unhex(row.bytes))
    switch row.stage {
    case "raw_decode":
        return encode(c)
    case "from_cbor":
        return try fromCbor(row.schema, c)
    case "from_wire":
        try fromWire(row.schema, c)
        return []
    default:
        throw RunnerError.badRow("unknown stage \(row.stage)")
    }
}

/// An `err` detail: the runtime's tag, then `;field=value` for each payload field it
/// carries. Exhaustive on purpose: a new case fails the build until it is reported here.
func describe(_ e: CborError) -> String {
    let payload: String
    switch e {
    case .truncated, .trailingBytes, .invalidUtf8, .nonIntegerMapKey:
        payload = ""
    case let .unsupportedInfo(info):
        payload = ";info=\(info)"
    case let .unsupportedMajor(major):
        payload = ";major=\(major)"
    case let .intOverflow(value):
        payload = ";value=\(value)"
    case let .nonCanonicalInt(value):
        payload = ";value=\(value)"
    case let .negativeMapKey(key):
        payload = ";key=\(key)"
    case let .duplicateMapKey(key):
        payload = ";key=\(key)"
    case let .missingKey(key):
        payload = ";key=\(key)"
    case let .wrongType(expected):
        payload = ";expected=\(expected)"
    case let .unknownEnum(name, value):
        payload = ";enum=\(name);value=\(value)"
    }
    return e.parityTag + payload
}

func i64(_ s: String) throws -> Int64 {
    guard let v = Int64(s) else {
        throw RunnerError.badRow("\(s) does not fit Int64")
    }
    return v
}

for row in roundTrip {
    do {
        let n = try i64(row.n)
        var byId: [Int64: Int64] = [:]
        for (k, v) in row.byId {
            byId[try i64(k)] = try i64(v)
        }
        let built = IntBox(n: n, by_id: byId)
        let enc = hexOf(encode(built.toCbor()))
        if enc != row.cbor {
            emit(row.name, "fail", "encode \(enc) != \(row.cbor)")
            continue
        }
        let d = try IntBox.fromCbor(try tryDecode(try unhex(row.cbor)))
        let re = hexOf(encode(d.toCbor()))
        if d.n == n && d.by_id == byId && re == row.cbor {
            emit(row.name, "pass", "")
        } else {
            emit(row.name, "fail", "reencode \(re)")
        }
    } catch {
        emit(row.name, "fail", "\(type(of: error)): \(error)")
    }
}

for row in encodeFail {
    // Int64 is the encode-side subset guard: an out-of-subset value is
    // unrepresentable, so the type system satisfies the row.
    if row.ints.contains(where: { Int64($0) == nil }) {
        emit(row.name, "type-satisfied", "unrepresentable in Int64")
    } else {
        emit(row.name, "fail", "value fits Int64 but expected out-of-subset")
    }
}

for row in malformed {
    do {
        let again = try decodeRow(row)
        emit(row.name, "ok", hexOf(again))
    } catch let e as CborError {
        emit(row.name, "err", describe(e))
    } catch {
        emit(row.name, "untyped", "\(type(of: error)): \(error)")
    }
}
'''


def _sw(value: str) -> str:
    """A Swift string literal: quotes and backslashes escaped, anything outside
    printable ASCII as a `\\u{...}` escape."""
    out = []
    for ch in value:
        if ch in ('"', "\\"):
            out.append("\\" + ch)
        elif " " <= ch <= "~":
            out.append(ch)
        else:
            out.append(f"\\u{{{ord(ch):x}}}")
    return '"' + "".join(out) + '"'


def _tables() -> tuple[str, str, str]:
    round_trip, encode_fail, malformed = [], [], []
    for row in parity.int_rows():
        value = row["value"]
        if row["kind"] == "round_trip":
            pairs = ", ".join(f"({_sw(str(k))}, {_sw(str(v))})" for k, v in value["by_id"])
            round_trip.append(f"    IntRow(name: {_sw(row['name'])}, cbor: {_sw(row['cbor'])}, "
                              f"n: {_sw(str(value['n']))}, byId: [{pairs}]),")
        else:
            ints = [str(value["n"]), *(str(item) for pair in value["by_id"] for item in pair)]
            encode_fail.append(f"    EncFail(name: {_sw(row['name'])}, "
                               f"ints: [{', '.join(_sw(item) for item in ints)}]),")
    for row in parity.malformed_rows():
        malformed.append(f"    Mal(name: {_sw(row['name'])}, stage: {_sw(row['stage'])}, "
                         f"schema: {_sw(row.get('schema', ''))}, bytes: {_sw(row['bytes'])}),")
    return "\n".join(round_trip), "\n".join(encode_fail), "\n".join(malformed)


def _dispatch() -> tuple[str, str]:
    """The `switch` arms for every message (`from_cbor`) and enum (`from_wire`) in the fixture."""
    dispatch = parity.fixture_dispatch()
    from_cbor = [f"    case {_sw(name)}:\n        return encode(try {name}.fromCbor(c).toCbor())"
                 for name in dispatch.messages]
    from_wire = [f"    case {_sw(name)}:\n        _ = try {name}.fromCbor(c)"
                 for name in dispatch.enums]
    return "\n".join(from_cbor), "\n".join(from_wire)


def _source() -> str:
    round_trip, encode_fail, malformed = _tables()
    from_cbor, from_wire = _dispatch()
    return (_MAIN
            .replace("@ROUND_TRIP@", round_trip)
            .replace("@ENCODE_FAIL@", encode_fail)
            .replace("@MALFORMED@", malformed)
            .replace("@FROM_CBOR@", from_cbor)
            .replace("@FROM_WIRE@", from_wire))


def run() -> parity.TargetReport:
    swiftc = toolchains.find_swiftc()
    if swiftc is None:
        return parity.skipped(TARGET, "swiftc not found")
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        failed = parity.generate(TARGET, work, runtime=True)
        if failed is not None:
            return failed
        main = work / "main.swift"
        main.write_text(_source())
        sources = [str(path) for path in sorted((work / TARGET).glob("*.swift"))]
        binary = work / "parity_runner"
        failed = parity.build(TARGET, [swiftc, *sources, str(main), "-o", str(binary)], cwd=work)
        if failed is not None:
            return failed
        return parity.run_runner(TARGET, [str(binary)], cwd=work)
