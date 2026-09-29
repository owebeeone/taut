// Extension accessors for taut's residual extension band.
//
// These operate on the host's top-level CBOR map without knowing the host
// schema. The caller passes the generated extension message's toCbor() value.
//
// They fail closed (TautCheckedDecode.md CD-E4): for any host bytes each returns
// or throws `CborError`, nothing else. A host that is not a map is
// `wrongType("map")`. Not knowing the host's root, they read it at the depth
// ceiling with no length bound, the only bounds every valid host meets, and leave
// the host's own bounds to its reader (TautOptions.md G3). A tag below the band is
// the caller's error, not the input's, and traps.

private let extensionBandStart: Int64 = 1 << 20

private func checkExtensionTag(_ tag: Int64) {
    precondition(tag >= extensionBandStart, "extension tag \(tag) is below the band (< \(extensionBandStart))")
}

/// The host's top-level map, read at the depth ceiling with no length bound; a host that
/// is not a map is `wrongType("map")`.
private func hostMap(_ host: [UInt8]) throws -> [(Int64, Cbor)] {
    guard case let .map(entries) = try tryDecode(host, maxDepth: maxDepthCeiling) else {
        throw CborError.wrongType("map")
    }
    return entries
}

public func extSet(_ host: [UInt8], tag: Int64, value: Cbor) throws -> [UInt8] {
    checkExtensionTag(tag)
    var entries = try hostMap(host).filter { $0.0 != tag }
    entries.append((tag, value))
    return encode(.map(entries))
}

public func extGet(_ host: [UInt8], tag: Int64) throws -> Cbor? {
    checkExtensionTag(tag)
    for (key, value) in try hostMap(host) where key == tag {
        return value
    }
    return nil
}

public func extClear(_ host: [UInt8], tag: Int64) throws -> [UInt8] {
    checkExtensionTag(tag)
    return encode(.map(try hostMap(host).filter { $0.0 != tag }))
}
