// Extension accessors for Kotlin. Operates on top-level CBOR maps and stores
// extension messages as nested Cbor values, not pre-serialized bytes.
package taut

private const val BAND_START: Long = 1L shl 20

private fun checkExtTag(tag: Long) {
    require(tag >= BAND_START) { "extension tag $tag is below the band (< $BAND_START)" }
}

private fun hostMap(host: ByteArray): Cbor {
    val c = decode(host)
    require(c.kind == Cbor.MAP) { "extension host must decode to a top-level CBOR map" }
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
        if (entry.first == tag) return entry.second
    }
    return null
}

fun extClear(host: ByteArray, tag: Long): ByteArray {
    checkExtTag(tag)
    val entries = hostMap(host).mapEntries.filter { it.first != tag }
    return encode(Cbor.map(entries))
}
