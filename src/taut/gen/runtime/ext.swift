// Extension accessors for taut's residual extension band.
//
// These operate on the host's top-level CBOR map without knowing the host
// schema. The caller passes the generated extension message's toCbor() value.

private let extensionBandStart: Int64 = 1 << 20

private func checkExtensionTag(_ tag: Int64) {
    precondition(tag >= extensionBandStart, "extension tag \(tag) is below the band (< \(extensionBandStart))")
}

private func hostMap(_ host: [UInt8]) -> [(Int64, Cbor)] {
    switch decode(host) {
    case let .map(entries):
        return entries
    default:
        preconditionFailure("extension host root is not a map")
    }
}

public func extSet(_ host: [UInt8], tag: Int64, value: Cbor) -> [UInt8] {
    checkExtensionTag(tag)
    var entries = hostMap(host).filter { $0.0 != tag }
    entries.append((tag, value))
    return encode(.map(entries))
}

public func extGet(_ host: [UInt8], tag: Int64) -> Cbor? {
    checkExtensionTag(tag)
    for (key, value) in hostMap(host) where key == tag {
        return value
    }
    return nil
}

public func extClear(_ host: [UInt8], tag: Int64) -> [UInt8] {
    checkExtensionTag(tag)
    return encode(.map(hostMap(host).filter { $0.0 != tag }))
}
