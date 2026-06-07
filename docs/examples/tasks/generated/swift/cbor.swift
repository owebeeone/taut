// Minimal deterministic CBOR — the Swift binding of the frozen wire substrate.
// Byte-for-byte identical to taut/src/taut/wire/cbor.py and the Rust/TS/C++
// runtimes: the same tiny subset (int, bytes, text, array, int-keyed map, bool,
// null) in core-deterministic encoding (definite length, shortest-form ints,
// ascending map keys). Hand-rolled, no dependencies.

public indirect enum Cbor {
    case int(Int64)
    case bytes([UInt8])
    case text(String)
    case array([Cbor])
    case map([(Int64, Cbor)])
    case bool(Bool)
    case null
}

public extension Cbor {
    func get(_ key: Int64) -> Cbor {
        if case let .map(m) = self { for (k, v) in m where k == key { return v } }
        fatalError("no map key \(key)")
    }
    var intVal: Int64 { if case let .int(n) = self { return n }; fatalError("not an int") }
    var textVal: String { if case let .text(s) = self { return s }; fatalError("not text") }
    var bytesVal: [UInt8] { if case let .bytes(b) = self { return b }; fatalError("not bytes") }
    var boolVal: Bool { if case let .bool(b) = self { return b }; fatalError("not a bool") }
    var arrayVal: [Cbor] { if case let .array(a) = self { return a }; fatalError("not an array") }
    var isNull: Bool { if case .null = self { return true }; return false }
    /// All (key, value) pairs of a map (empty if not a map) — for forward-compat residual.
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

public func encode(_ v: Cbor) -> [UInt8] {
    var out = [UInt8]()
    enc(v, &out)
    return out
}

private func enc(_ v: Cbor, _ out: inout [UInt8]) {
    switch v {
    case let .int(n):
        if n >= 0 { head(&out, 0, UInt64(n)) } else { head(&out, 1, UInt64(-1 - n)) }
    case let .bytes(b): head(&out, 2, UInt64(b.count)); out.append(contentsOf: b)
    case let .text(s): let b = Array(s.utf8); head(&out, 3, UInt64(b.count)); out.append(contentsOf: b)
    case let .array(a): head(&out, 4, UInt64(a.count)); for x in a { enc(x, &out) }
    case let .map(m):
        let entries = m.sorted { $0.0 < $1.0 }   // deterministic: ascending keys
        head(&out, 5, UInt64(m.count))
        for (k, val) in entries { head(&out, 0, UInt64(k)); enc(val, &out) }
    case let .bool(b): out.append(b ? 0xf5 : 0xf4)
    case .null: out.append(0xf6)
    }
}

public func decode(_ data: [UInt8]) -> Cbor {
    let (v, off) = dec(data, 0)
    precondition(off == data.count, "trailing bytes after top-level CBOR item")
    return v
}

private func readArg(_ data: [UInt8], _ off: Int, _ info: UInt8) -> (UInt64, Int) {
    if info < 24 { return (UInt64(info), off) }
    if info == 24 { return (UInt64(data[off]), off + 1) }
    if info == 25 { return ((UInt64(data[off]) << 8) | UInt64(data[off + 1]), off + 2) }
    if info == 26 { var v: UInt64 = 0; for j in 0..<4 { v = (v << 8) | UInt64(data[off + j]) }; return (v, off + 4) }
    var v: UInt64 = 0; for j in 0..<8 { v = (v << 8) | UInt64(data[off + j]) }; return (v, off + 8)
}

private func dec(_ data: [UInt8], _ off0: Int) -> (Cbor, Int) {
    let initial = data[off0]
    let major = initial >> 5
    let info = initial & 0x1f
    let off = off0 + 1
    switch major {
    case 0: let (n, o) = readArg(data, off, info); return (.int(Int64(bitPattern: n)), o)
    case 1: let (n, o) = readArg(data, off, info); return (.int(-1 - Int64(bitPattern: n)), o)
    case 2: let (n, o) = readArg(data, off, info); let k = Int(n); return (.bytes(Array(data[o..<o + k])), o + k)
    case 3: let (n, o) = readArg(data, off, info); let k = Int(n); return (.text(String(decoding: data[o..<o + k], as: UTF8.self)), o + k)
    case 4:
        let (n, o0) = readArg(data, off, info); var o = o0; var a = [Cbor]()
        for _ in 0..<n { let (v, o2) = dec(data, o); a.append(v); o = o2 }
        return (.array(a), o)
    case 5:
        let (n, o0) = readArg(data, off, info); var o = o0; var m = [(Int64, Cbor)]()
        for _ in 0..<n { let (k, o2) = dec(data, o); let (v, o3) = dec(data, o2); m.append((k.intVal, v)); o = o3 }
        return (.map(m), o)
    case 7:
        switch info {
        case 20: return (.bool(false), off)
        case 21: return (.bool(true), off)
        case 22: return (.null, off)
        default: fatalError("unsupported simple value \(info)")
        }
    default: fatalError("unsupported major type \(major)")
    }
}
