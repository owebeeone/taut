"""Swift runner for the parity gate, modelled on `parity_rust.py`.

The gate finds it by module name (`parity._RUNNERS`) and calls `run()`, and
`run(forward_compat=True)` for the `swift/fc` variant:

  1. find swiftc (`toolchains.find_swiftc`); a missing one is the only skip;
  2. generate the fixture's Swift with its vendored runtime (`parity.generate`, with
     forward_compat for `swift/fc`); a refusal is RED;
  3. write `main.swift`, whose row tables come from `parity.int_rows()` and
     `parity.decode_rows()` (the malformed rows, then the bounds rows) and whose
     dispatch comes from `parity.fixture_dispatch()`, never from hard-coded message names;
  4. build it with swiftc (`parity.build`); a failure is RED;
  5. run it (`parity.run_runner`), which parses and judges its report.

The runner speaks the gate's protocol (`parity`'s docstring), C3's bounds included. It
prints `#constants<TAB>default_max_depth=<n>;max_depth_ceiling=<n>` once, from the
runtime's own `defaultMaxDepth` and `maxDepthCeiling`, then `name<TAB>outcome<TAB>detail`
per row. It checks int rows itself; for a decode row it only reports what happened (`ok`
with the hex of the re-encoding; `err` with the tag and payload; `untyped` for any other
thrown error) and the gate judges it:
  - a row's bytes are embedded as their segments (`parity.segments`), which the runner
    expands and checks against the row's `len`, a mismatch being `untyped`, so a
    100,000-deep row stays one short line;
  - a raw_decode row calls `tryDecode` with its `limits`, each one it lacks left at the
    runtime's default;
  - a from_cbor row decodes from bytes through its message's typed `decode`, which applies
    the message's bounds, and its line adds a fourth column, the bounds that entry point
    resolved, the message's `maxDepth` and `maxEncodedLen`;
  - a from_wire row names an enum, which the raw decode reads with its defaults before the
    enum's `fromCbor`.
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

/// A malformed or bounds row: its input as `(hex, count)` segments, the expanded length
/// where the row states one, and a raw row's limits (nil: left at the call's default).
struct DecodeRow {
    let name: String
    let stage: String
    let schema: String
    let segments: [(String, Int)]
    let len: Int?
    let maxDepth: Int?
    let maxEncodedLen: Int?
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
let decodeRows: [DecodeRow] = [
@DECODE_ROWS@
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

/// One report line: the columns joined by tabs, a tab or line break inside one a space.
func emit(_ columns: [String]) {
    var cleaned: [String] = []
    for column in columns {
        var clean = String.UnicodeScalarView()
        for scalar in column.unicodeScalars {
            if scalar == "\t" || scalar == "\n" || scalar == "\r" {
                clean.append(" ")
            } else {
                clean.append(scalar)
            }
        }
        cleaned.append(String(clean))
    }
    print(cleaned.joined(separator: "\t"))
    fflush(stdout)
}

/// A row's input: its segments expanded, and checked against its `len` where it has one.
func expand(_ row: DecodeRow) throws -> [UInt8] {
    var out: [UInt8] = []
    for (hex, count) in row.segments {
        let unit = try unhex(hex)
        for _ in 0..<count {
            out.append(contentsOf: unit)
        }
    }
    if let want = row.len {
        guard out.count == want else {
            throw RunnerError.badRow("bytes expand to \(out.count) bytes, len is \(want)")
        }
    }
    return out
}

/// A from_cbor row's typed entry point, by message name (from the fixture schema): the
/// message's `decode` from bytes, which applies its bounds, and the value's own encoding.
func fromBytes(_ message: String, _ data: [UInt8]) throws -> [UInt8] {
    switch message {
@FROM_BYTES@
    default:
        throw RunnerError.noEntryPoint("no from_cbor entry point for \(message)")
    }
}

/// A bounds column: `max_depth=<n>;max_encoded_len=<n>`, the length empty for none.
func boundsColumn(_ maxDepth: Int, _ maxEncodedLen: Int?) -> String {
    return "max_depth=\(maxDepth);max_encoded_len=\(maxEncodedLen.map { String($0) } ?? "")"
}

/// The bounds a from_cbor row's typed entry point applies: its message's constants.
func resolved(_ message: String) -> String {
    switch message {
@RESOLVED@
    default:
        return "no bounds for \(message)"
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
func decodeRow(_ row: DecodeRow) throws -> [UInt8] {
    let data = try expand(row)
    switch row.stage {
    case "raw_decode":
        return encode(try tryDecode(data, maxDepth: row.maxDepth ?? defaultMaxDepth,
                                    maxEncodedLen: row.maxEncodedLen))
    case "from_cbor":
        return try fromBytes(row.schema, data)
    case "from_wire":
        try fromWire(row.schema, try tryDecode(data))
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
    case let .tooDeep(limit):
        payload = ";limit=\(limit)"
    case let .tooLarge(len, limit):
        payload = ";len=\(len);limit=\(limit)"
    }
    return e.parityTag + payload
}

func i64(_ s: String) throws -> Int64 {
    guard let v = Int64(s) else {
        throw RunnerError.badRow("\(s) does not fit Int64")
    }
    return v
}

print("#constants\tdefault_max_depth=\(defaultMaxDepth);max_depth_ceiling=\(maxDepthCeiling)")
fflush(stdout)

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
            emit([row.name, "fail", "encode \(enc) != \(row.cbor)"])
            continue
        }
        let d = try IntBox.decode(try unhex(row.cbor))
        let re = hexOf(encode(d.toCbor()))
        if d.n == n && d.by_id == byId && re == row.cbor {
            emit([row.name, "pass", ""])
        } else {
            emit([row.name, "fail", "reencode \(re)"])
        }
    } catch {
        emit([row.name, "fail", "\(type(of: error)): \(error)"])
    }
}

for row in encodeFail {
    // Int64 is the encode-side subset guard: an out-of-subset value is
    // unrepresentable, so the type system satisfies the row.
    if row.ints.contains(where: { Int64($0) == nil }) {
        emit([row.name, "type-satisfied", "unrepresentable in Int64"])
    } else {
        emit([row.name, "fail", "value fits Int64 but expected out-of-subset"])
    }
}

for row in decodeRows {
    var columns: [String]
    do {
        columns = [row.name, "ok", hexOf(try decodeRow(row))]
    } catch let e as CborError {
        columns = [row.name, "err", describe(e)]
    } catch {
        columns = [row.name, "untyped", "\(type(of: error)): \(error)"]
    }
    if row.stage == "from_cbor" {
        columns.append(resolved(row.schema))
    }
    emit(columns)
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


def _optional(value: int | None) -> str:
    """A Swift `Int?` literal."""
    return "nil" if value is None else str(value)


def _tables() -> tuple[str, str, str]:
    round_trip, encode_fail, decode_rows = [], [], []
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
    for row in parity.decode_rows():
        limits = row.get("limits", {})
        segments = ", ".join(f"({_sw(hexed)}, {count})" for hexed, count in parity.segments(row))
        decode_rows.append(
            f"    DecodeRow(name: {_sw(row['name'])}, stage: {_sw(row['stage'])}, "
            f"schema: {_sw(row.get('schema', ''))}, segments: [{segments}], "
            f"len: {_optional(row.get('len'))}, maxDepth: {_optional(limits.get('max_depth'))}, "
            f"maxEncodedLen: {_optional(limits.get('max_encoded_len'))}),")
    return "\n".join(round_trip), "\n".join(encode_fail), "\n".join(decode_rows)


def _dispatch() -> tuple[str, str, str]:
    """The `switch` arms for every message (its typed `decode` and the bounds it applies,
    for `from_cbor`) and enum (`from_wire`) in the fixture."""
    dispatch = parity.fixture_dispatch()
    from_bytes = [f"    case {_sw(name)}:\n        return encode(try {name}.decode(data).toCbor())"
                  for name in dispatch.messages]
    resolved = [f"    case {_sw(name)}:\n        return boundsColumn({name}.maxDepth, {name}.maxEncodedLen)"
                for name in dispatch.messages]
    from_wire = [f"    case {_sw(name)}:\n        _ = try {name}.fromCbor(c)"
                 for name in dispatch.enums]
    return "\n".join(from_bytes), "\n".join(resolved), "\n".join(from_wire)


def _source() -> str:
    round_trip, encode_fail, decode_rows = _tables()
    from_bytes, resolved, from_wire = _dispatch()
    return (_MAIN
            .replace("@ROUND_TRIP@", round_trip)
            .replace("@ENCODE_FAIL@", encode_fail)
            .replace("@DECODE_ROWS@", decode_rows)
            .replace("@FROM_BYTES@", from_bytes)
            .replace("@RESOLVED@", resolved)
            .replace("@FROM_WIRE@", from_wire))


def run(forward_compat: bool = False) -> parity.TargetReport:
    """The swift gate, or with `forward_compat` its `swift/fc` variant."""
    name = parity.variant(TARGET, forward_compat)
    swiftc = toolchains.find_swiftc()
    if swiftc is None:
        return parity.skipped(name, "swiftc not found")
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        failed = parity.generate(name, work, runtime=True)
        if failed is not None:
            return failed
        main = work / "main.swift"
        main.write_text(_source())
        sources = [str(path) for path in sorted((work / TARGET).glob("*.swift"))]
        binary = work / "parity_runner"
        failed = parity.build(name, [swiftc, *sources, str(main), "-o", str(binary)], cwd=work)
        if failed is not None:
            return failed
        return parity.run_runner(name, [str(binary)], cwd=work)
