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

// The host's top-level map. Not knowing the host's root, the helpers read it at the depth
// ceiling with no length bound, the only bounds every valid host meets, and leave the host's
// own bounds to its reader (TautOptions.md G3).
private fun hostMap(host: ByteArray): Cbor {
    val c = decode(host, maxDepth = MAX_DEPTH_CEILING)
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
