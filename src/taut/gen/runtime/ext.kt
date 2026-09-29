// Extension accessors for Kotlin. Operates on top-level CBOR maps and stores
// extension messages as nested Cbor values, not pre-serialized bytes.
//
// They fail closed (TautCheckedDecode.md CD-E4): for any host bytes each returns or throws
// DecodeError, nothing else, and a host that is not a map is WrongType("map"). A tag below
// the band is the caller's error, IllegalArgumentException, found before the host is read.
package taut

private const val BAND_START: Long = 1L shl 20

private fun checkExtTag(tag: Long) {
    require(tag >= BAND_START) { "extension tag $tag is below the band (< $BAND_START)" }
}

// The host's top-level map. Not knowing the host's root, the helpers leave its own bounds to
// its reader (TautOptions.md G3).
// TODO(D1): read the host at the depth ceiling (128) with no length bound, the only bounds
// every valid host meets, once D1 gives decode its depth parameter. Until then this decode
// bounds no depth.
private fun hostMap(host: ByteArray): Cbor {
    val c = decode(host)
    if (c.kind != Cbor.MAP) {
        throw DecodeError.WrongType("map")
    }
    return c
}

fun extSet(host: ByteArray, tag: Long, value: Cbor): ByteArray {
    checkExtTag(tag)
    val entries = hostMap(host).mapEntries.filter { it.first != tag } + Pair(tag, value)
    return encode(Cbor.map(entries))
}

fun extGet(host: ByteArray, tag: Long): Cbor? {
    checkExtTag(tag)
    for (entry in hostMap(host).mapEntries) {
        if (entry.first == tag) {
            return entry.second
        }
    }
    return null
}

fun extClear(host: ByteArray, tag: Long): ByteArray {
    checkExtTag(tag)
    val entries = hostMap(host).mapEntries.filter { it.first != tag }
    return encode(Cbor.map(entries))
}
