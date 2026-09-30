// Minimal deterministic CBOR - the Swift binding of the frozen wire substrate.
// Byte-for-byte identical to taut/src/taut/wire/cbor.py and the Rust/TS/C++
// runtimes: the same tiny subset (int, float, bytes, text, array, int-keyed map,
// bool, null) in core-deterministic encoding (definite length, shortest-form
// ints/floats, ascending map keys). Hand-rolled, no dependencies.
//
// Decode is fail-closed: every public decode entry point (`tryDecode`, the `try*`
// accessors and the generated `fromCbor` and `decode`) returns a value or throws
// `CborError`, and nothing else escapes or traps (TautCheckedDecode.md CD-E4).
//
// Decode is bounded (D26, TautCheckedDecode.md §3). An array or map has depth one more
// than the arrays and maps around it, and one deeper than the call's depth bound is
// `tooDeep(limit:)`, refused before its first item is read, so the recursion is never
// deeper than the bound; with a length bound, longer input is `tooLarge(len:limit:)`
// before a byte is read.

/// The depth bound a raw decode applies where its caller passes none (CD-B1).
public let defaultMaxDepth: Int = 32
/// No decode applies a deeper bound: a larger `maxDepth` applies this one (CD-B3).
public let maxDepthCeiling: Int = 128

public enum CborError: Error, Equatable, CustomStringConvertible {
    case truncated
    case trailingBytes
    case invalidUtf8
    case unsupportedInfo(UInt8)
    case unsupportedMajor(UInt8)
    case nonIntegerMapKey
    case intOverflow(String)
    /// The repeated key as text: an int in decimal, a str as itself, a bool as `true` or `false`.
    case duplicateMapKey(String)
    case missingKey(Int64)
    case wrongType(String)
    case unknownEnum(String, Int64)
    case nonCanonicalInt(UInt64)
    case negativeMapKey(Int64)
    /// An array or map deeper than the depth bound; `limit` is the bound applied.
    case tooDeep(limit: Int)
    /// Input of `len` bytes, longer than the length bound `limit`.
    case tooLarge(len: Int, limit: Int)

    public var parityTag: String {
        switch self {
        case .truncated: return "Truncated"
        case .trailingBytes: return "TrailingBytes"
        case .invalidUtf8: return "InvalidUtf8"
        case .unsupportedInfo: return "UnsupportedInfo"
        case .unsupportedMajor: return "UnsupportedMajor"
        case .nonIntegerMapKey: return "NonIntegerMapKey"
        case .intOverflow: return "IntOverflow"
        case .duplicateMapKey: return "DuplicateMapKey"
        case .missingKey: return "MissingKey"
        case .wrongType: return "WrongType"
        case .unknownEnum: return "UnknownEnum"
        case .nonCanonicalInt: return "NonCanonicalInt"
        case .negativeMapKey: return "NegativeMapKey"
        case .tooDeep: return "TooDeep"
        case .tooLarge: return "TooLarge"
        }
    }

    public var description: String {
        switch self {
        case .truncated:
            return "Truncated"
        case .trailingBytes:
            return "TrailingBytes"
        case .invalidUtf8:
            return "InvalidUtf8"
        case let .unsupportedInfo(info):
            return "UnsupportedInfo(info: \(info))"
        case let .unsupportedMajor(major):
            return "UnsupportedMajor(major: \(major))"
        case .nonIntegerMapKey:
            return "NonIntegerMapKey"
        case let .intOverflow(value):
            return "IntOverflow(value: \(value))"
        case let .duplicateMapKey(key):
            return "DuplicateMapKey(key: \(key))"
        case let .missingKey(key):
            return "MissingKey(key: \(key))"
        case let .wrongType(expected):
            return "WrongType(expected: \(expected))"
        case let .unknownEnum(name, value):
            return "UnknownEnum(enum: \(name), value: \(value))"
        case let .nonCanonicalInt(value):
            return "NonCanonicalInt(value: \(value))"
        case let .negativeMapKey(key):
            return "NegativeMapKey(key: \(key))"
        case let .tooDeep(limit):
            return "TooDeep(limit: \(limit))"
        case let .tooLarge(len, limit):
            return "TooLarge(len: \(len), limit: \(limit))"
        }
    }
}

public indirect enum Cbor {
    case int(Int64)
    case float(Double)
    case bytes([UInt8])
    case text(String)
    case array([Cbor])
    case map([(Int64, Cbor)])
    case bool(Bool)
    case null
}

public extension Cbor {
    func tryGet(_ key: Int64) throws -> Cbor {
        guard case let .map(m) = self else {
            throw CborError.wrongType("map")
        }
        for (k, v) in m where k == key {
            return v
        }
        throw CborError.missingKey(key)
    }

    /// Like `tryGet`, but an absent key is nil (a MISSING_OK field); a non-map still fails.
    func tryGetOpt(_ key: Int64) throws -> Cbor? {
        guard case let .map(m) = self else {
            throw CborError.wrongType("map")
        }
        for (k, v) in m where k == key {
            return v
        }
        return nil
    }

    func tryInt() throws -> Int64 {
        guard case let .int(n) = self else {
            throw CborError.wrongType("int")
        }
        return n
    }

    func tryFloat() throws -> Double {
        guard case let .float(x) = self else {
            throw CborError.wrongType("float")
        }
        return x
    }

    func tryText() throws -> String {
        guard case let .text(s) = self else {
            throw CborError.wrongType("text")
        }
        return s
    }

    func tryBytes() throws -> [UInt8] {
        guard case let .bytes(b) = self else {
            throw CborError.wrongType("bytes")
        }
        return b
    }

    func tryBool() throws -> Bool {
        guard case let .bool(b) = self else {
            throw CborError.wrongType("bool")
        }
        return b
    }

    func tryArray() throws -> [Cbor] {
        guard case let .array(a) = self else {
            throw CborError.wrongType("array")
        }
        return a
    }

    /// A `map<K,V>` field: an array of `{1: key, 2: value}` entries. Each entry must hold
    /// keys 1 and 2 before either is decoded, and a repeated key is `duplicateMapKey` with
    /// the key as text. A member, not a free function, so that no field of a generated
    /// message, whatever its name, can hide it from that message's `fromCbor`.
    func tryDictionary<K: Hashable, V>(
        key decodeKey: (Cbor) throws -> K,
        value decodeValue: (Cbor) throws -> V
    ) throws -> [K: V] {
        var out: [K: V] = [:]
        for entry in try tryArray() {
            let rawKey = try entry.tryGet(1)
            let rawValue = try entry.tryGet(2)
            let keyValue = try decodeKey(rawKey)
            if out[keyValue] != nil {
                // K is Int64, String or Bool: decimal, the text itself, `true` or `false`.
                throw CborError.duplicateMapKey(String(describing: keyValue))
            }
            out[keyValue] = try decodeValue(rawValue)
        }
        return out
    }

    var isNull: Bool { if case .null = self { return true }; return false }

    /// All (key, value) pairs of a map (empty if not a map) - for forward-compat residual.
    var mapEntries: [(Int64, Cbor)] { if case let .map(m) = self { return m }; return [] }
}

private func head(_ out: inout [UInt8], _ major: UInt8, _ n: UInt64) {
    let mt = major << 5
    if n < 24 { out.append(mt | UInt8(n)) }
    else if n < 0x100 { out.append(mt | 24); out.append(UInt8(n)) }
    else if n < 0x1_0000 { out.append(mt | 25); out.append(UInt8(n >> 8)); out.append(UInt8(n & 0xff)) }
    else if n < 0x1_0000_0000 { out.append(mt | 26); for i in stride(from: 24, through: 0, by: -8) { out.append(UInt8((n >> UInt64(i)) & 0xff)) } }
    else { out.append(mt | 27); for i in stride(from: 56, through: 0, by: -8) { out.append(UInt8((n >> UInt64(i)) & 0xff)) } }
}

private func append16(_ out: inout [UInt8], _ bits: UInt16) {
    out.append(UInt8((bits >> 8) & 0xff))
    out.append(UInt8(bits & 0xff))
}

private func append32(_ out: inout [UInt8], _ bits: UInt32) {
    for i in stride(from: 24, through: 0, by: -8) {
        out.append(UInt8((bits >> UInt32(i)) & 0xff))
    }
}

private func append64(_ out: inout [UInt8], _ bits: UInt64) {
    for i in stride(from: 56, through: 0, by: -8) {
        out.append(UInt8((bits >> UInt64(i)) & 0xff))
    }
}

private func encFloat(_ v: Double, _ out: inout [UInt8]) {
    if v.isNaN {
        out.append(0xf9)
        append16(&out, 0x7e00)
        return
    }

    // Requires native Swift Float16; older targets need a hand-rolled half narrower.
    let h = Float16(v)
    if Double(h) == v {
        out.append(0xf9)
        append16(&out, h.bitPattern)
        return
    }

    let f = Float(v)
    if Double(f) == v {
        out.append(0xfa)
        append32(&out, f.bitPattern)
        return
    }

    out.append(0xfb)
    append64(&out, v.bitPattern)
}

public func encode(_ v: Cbor) -> [UInt8] {
    var out = [UInt8]()
    enc(v, &out)
    return out
}

private func enc(_ v: Cbor, _ out: inout [UInt8]) {
    switch v {
    case let .int(n):
        if n >= 0 { head(&out, 0, UInt64(n)) } else { head(&out, 1, UInt64(-1 - n)) }
    case let .float(x): encFloat(x, &out)
    case let .bytes(b): head(&out, 2, UInt64(b.count)); out.append(contentsOf: b)
    case let .text(s): let b = Array(s.utf8); head(&out, 3, UInt64(b.count)); out.append(contentsOf: b)
    case let .array(a): head(&out, 4, UInt64(a.count)); for x in a { enc(x, &out) }
    case let .map(m):
        let entries = m.sorted { $0.0 < $1.0 }   // deterministic: ascending keys
        head(&out, 5, UInt64(m.count))
        for (k, val) in entries {
            precondition(k >= 0, "negative raw map key \(k)")
            head(&out, 0, UInt64(k))
            enc(val, &out)
        }
    case let .bool(b): out.append(b ? 0xf5 : 0xf4)
    case .null: out.append(0xf6)
    }
}

public extension Cbor {
    /// Decode one item that fills `data`, or throw `CborError` (CD-E5). `maxDepth` bounds
    /// nesting: a top-level array or map has depth 1, and one at depth `maxDepth` + 1 is
    /// `tooDeep` once its head is read. A value above `maxDepthCeiling` applies the ceiling,
    /// and `limit` names the bound applied. `maxEncodedLen`, when given, bounds the input's
    /// length, checked before any byte is read. A `maxDepth` below 1 or a negative
    /// `maxEncodedLen` is the caller's error, not the input's, and traps.
    /// A member, so that generated code reaches it whatever its fields are named.
    static func tryDecode(
        _ data: [UInt8], maxDepth: Int = defaultMaxDepth, maxEncodedLen: Int? = nil
    ) throws -> Cbor {
        precondition(maxDepth >= 1, "maxDepth must be at least 1, not \(maxDepth)")
        let limit = Swift.min(maxDepth, maxDepthCeiling)
        if let bound = maxEncodedLen {
            precondition(bound >= 0, "maxEncodedLen must not be negative, not \(bound)")
            guard data.count <= bound else {
                throw CborError.tooLarge(len: data.count, limit: bound)
            }
        }
        let (v, off) = try dec(data, 0, 0, limit)
        guard off == data.count else {
            throw CborError.trailingBytes
        }
        return v
    }
}

/// The raw decode, `Cbor.tryDecode`, as a free function.
public func tryDecode(
    _ data: [UInt8], maxDepth: Int = defaultMaxDepth, maxEncodedLen: Int? = nil
) throws -> Cbor {
    return try Cbor.tryDecode(data, maxDepth: maxDepth, maxEncodedLen: maxEncodedLen)
}

private func requireBytes(_ data: [UInt8], _ off: Int, _ count: Int) throws {
    guard off >= 0 && off <= data.count && count <= data.count - off else {
        throw CborError.truncated
    }
}

private func readArg(_ data: [UInt8], _ off: Int, _ info: UInt8) throws -> (UInt64, Int) {
    if info < 24 {
        return (UInt64(info), off)
    }
    let width: Int
    let shorterMax: UInt64   // the largest argument a shorter form holds
    switch info {
    case 24:
        width = 1
        shorterMax = 23
    case 25:
        width = 2
        shorterMax = 0xff
    case 26:
        width = 4
        shorterMax = 0xffff
    case 27:
        width = 8
        shorterMax = 0xffff_ffff
    default:
        throw CborError.unsupportedInfo(info)
    }
    try requireBytes(data, off, width)
    var v: UInt64 = 0
    for j in 0..<width {
        v = (v << 8) | UInt64(data[off + j])
    }
    // Strict-canonical (D2): an argument that fits a shorter form is non-minimal,
    // which the canonical encoder never writes. Lengths and counts included;
    // floats are read in `dec` and exempt.
    guard v > shorterMax else {
        throw CborError.nonCanonicalInt(v)
    }
    return (v, off + width)
}

private func checkedCount(_ data: [UInt8], _ off: Int, _ n: UInt64) throws -> Int {
    guard n <= UInt64(Int.max) else {
        throw CborError.truncated
    }
    let k = Int(n)
    try requireBytes(data, off, k)
    return k
}

private func negativeOverflowValue(_ n: UInt64) -> String {
    if n == UInt64.max {
        return "-18446744073709551616"
    }
    return "-\(n + 1)"
}

private func decodeUtf8(_ bytes: ArraySlice<UInt8>) throws -> String {
    var decoder = Unicode.UTF8()
    var iterator = bytes.makeIterator()
    var scalars = String.UnicodeScalarView()

    while true {
        switch decoder.decode(&iterator) {
        case let .scalarValue(scalar):
            scalars.append(scalar)
        case .emptyInput:
            return String(scalars)
        case .error:
            throw CborError.invalidUtf8
        }
    }
}

/// A container whose head is read, inside `depth` others: refuse it before its first item
/// if it would sit deeper than `limit` (CD-B2), which bounds `dec`'s recursion.
private func enter(_ depth: Int, _ limit: Int) throws {
    guard depth < limit else {
        throw CborError.tooDeep(limit: limit)
    }
}

/// The item at `off0`, inside `depth` arrays and maps, under depth bound `limit`.
private func dec(_ data: [UInt8], _ off0: Int, _ depth: Int, _ limit: Int) throws -> (Cbor, Int) {
    try requireBytes(data, off0, 1)
    let initial = data[off0]
    let major = initial >> 5
    let info = initial & 0x1f
    let off = off0 + 1

    switch major {
    case 0:
        let (n, o) = try readArg(data, off, info)
        guard n <= UInt64(Int64.max) else {
            throw CborError.intOverflow(String(n))
        }
        return (.int(Int64(n)), o)
    case 1:
        let (n, o) = try readArg(data, off, info)
        guard n <= UInt64(Int64.max) else {
            throw CborError.intOverflow(negativeOverflowValue(n))
        }
        return (.int(-1 - Int64(n)), o)
    case 2:
        let (n, o) = try readArg(data, off, info)
        let k = try checkedCount(data, o, n)
        return (.bytes(Array(data[o..<o + k])), o + k)
    case 3:
        let (n, o) = try readArg(data, off, info)
        let k = try checkedCount(data, o, n)
        return (.text(try decodeUtf8(data[o..<o + k])), o + k)
    case 4:
        // No up-front count check: items are read in order, so the first bad item
        // is reported, and each consumes a byte, so a huge count ends at Truncated.
        // The depth is checked once the head is complete, before the first item.
        let (n, o0) = try readArg(data, off, info)
        try enter(depth, limit)
        var o = o0
        var a = [Cbor]()
        for _ in 0..<n {
            let (v, o2) = try dec(data, o, depth + 1, limit)
            a.append(v)
            o = o2
        }
        return (.array(a), o)
    case 5:
        // As for arrays: entries are read in order, each key before its value.
        let (n, o0) = try readArg(data, off, info)
        try enter(depth, limit)
        var o = o0
        var m = [(Int64, Cbor)]()
        var seen = Set<Int64>()
        for _ in 0..<n {
            let (rawKey, o2) = try dec(data, o, depth + 1, limit)
            guard case let .int(key) = rawKey else {
                throw CborError.nonIntegerMapKey
            }
            guard key >= 0 else {
                throw CborError.negativeMapKey(key)
            }
            guard !seen.contains(key) else {
                throw CborError.duplicateMapKey(String(key))
            }
            seen.insert(key)
            let (v, o3) = try dec(data, o2, depth + 1, limit)
            m.append((key, v))
            o = o3
        }
        return (.map(m), o)
    case 7:
        switch info {
        case 20: return (.bool(false), off)
        case 21: return (.bool(true), off)
        case 22: return (.null, off)
        case 25:
            try requireBytes(data, off, 2)
            let bits = (UInt16(data[off]) << 8) | UInt16(data[off + 1])
            return (.float(Double(Float16(bitPattern: bits))), off + 2)
        case 26:
            try requireBytes(data, off, 4)
            var bits: UInt32 = 0
            for j in 0..<4 { bits = (bits << 8) | UInt32(data[off + j]) }
            return (.float(Double(Float(bitPattern: bits))), off + 4)
        case 27:
            try requireBytes(data, off, 8)
            var bits: UInt64 = 0
            for j in 0..<8 { bits = (bits << 8) | UInt64(data[off + j]) }
            return (.float(Double(bitPattern: bits)), off + 8)
        default:
            throw CborError.unsupportedInfo(info)
        }
    case 6:
        throw CborError.unsupportedMajor(major)
    default:
        throw CborError.unsupportedMajor(major)
    }
}
