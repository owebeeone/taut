// Minimal deterministic CBOR — the Kotlin binding of the frozen wire substrate.
// Same tiny subset (int, bytes, text, array, int-keyed map, bool, null) in
// core-deterministic encoding (definite length, shortest-form ints, ascending
// map keys). Hand-rolled, stdlib only.
package taut

class Cbor(
    val kind: Int,
    val i: Long = 0,
    val s: String = "",
    val b: ByteArray = ByteArray(0),
    val arr: List<Cbor> = emptyList(),
    val map: List<Pair<Long, Cbor>> = emptyList(),
) {
    companion object {
        const val INT = 0; const val BYTES = 1; const val TEXT = 2
        const val ARR = 3; const val MAP = 4; const val BOOL = 5; const val NULL = 6
        fun int(n: Long) = Cbor(INT, i = n)
        fun text(s: String) = Cbor(TEXT, s = s)
        fun bytes(b: ByteArray) = Cbor(BYTES, b = b)
        fun bool(x: Boolean) = Cbor(BOOL, i = if (x) 1 else 0)
        fun arr(a: List<Cbor>) = Cbor(ARR, arr = a)
        fun map(m: List<Pair<Long, Cbor>>) = Cbor(MAP, map = m)
        val nul = Cbor(NULL)
    }

    fun get(key: Long): Cbor {
        for (kv in map) if (kv.first == key) return kv.second
        throw RuntimeException("no map key $key")
    }
    val intVal: Long get() = i
    val textVal: String get() = s
    val bytesVal: ByteArray get() = b
    val boolVal: Boolean get() = i != 0L
    val arrVal: List<Cbor> get() = arr
    val isNull: Boolean get() = kind == NULL
    val mapEntries: List<Pair<Long, Cbor>> get() = map  // forward-compat residual
}

private fun head(out: MutableList<Byte>, major: Int, n: Long) {
    val mt = major shl 5
    when {
        n < 24 -> out.add((mt or n.toInt()).toByte())
        n < 0x100 -> { out.add((mt or 24).toByte()); out.add(n.toByte()) }
        n < 0x10000 -> { out.add((mt or 25).toByte()); out.add((n shr 8).toByte()); out.add(n.toByte()) }
        n < 0x100000000 -> { out.add((mt or 26).toByte()); for (sh in intArrayOf(24, 16, 8, 0)) out.add((n shr sh).toByte()) }
        else -> { out.add((mt or 27).toByte()); for (sh in intArrayOf(56, 48, 40, 32, 24, 16, 8, 0)) out.add((n shr sh).toByte()) }
    }
}

fun encode(c: Cbor): ByteArray {
    val out = ArrayList<Byte>()
    enc(c, out)
    return out.toByteArray()
}

private fun enc(c: Cbor, out: MutableList<Byte>) {
    when (c.kind) {
        Cbor.INT -> if (c.i >= 0) head(out, 0, c.i) else head(out, 1, -1 - c.i)
        Cbor.BYTES -> { head(out, 2, c.b.size.toLong()); for (x in c.b) out.add(x) }
        Cbor.TEXT -> { val bb = c.s.toByteArray(Charsets.UTF_8); head(out, 3, bb.size.toLong()); for (x in bb) out.add(x) }
        Cbor.ARR -> { head(out, 4, c.arr.size.toLong()); for (x in c.arr) enc(x, out) }
        Cbor.MAP -> {
            val m = c.map.sortedBy { it.first }  // deterministic: ascending keys
            head(out, 5, m.size.toLong())
            for (kv in m) { head(out, 0, kv.first); enc(kv.second, out) }
        }
        Cbor.BOOL -> out.add((if (c.i != 0L) 0xf5 else 0xf4).toByte())
        Cbor.NULL -> out.add(0xf6.toByte())
    }
}

private fun u(data: ByteArray, i: Int): Int = data[i].toInt() and 0xFF

fun decode(data: ByteArray): Cbor {
    val (v, off) = dec(data, 0)
    if (off != data.size) throw RuntimeException("trailing bytes after top-level CBOR item")
    return v
}

private fun readArg(data: ByteArray, off: Int, info: Int): Pair<Long, Int> = when {
    info < 24 -> Pair(info.toLong(), off)
    info == 24 -> Pair(u(data, off).toLong(), off + 1)
    info == 25 -> Pair((u(data, off).toLong() shl 8) or u(data, off + 1).toLong(), off + 2)
    info == 26 -> { var v = 0L; for (j in 0 until 4) v = (v shl 8) or u(data, off + j).toLong(); Pair(v, off + 4) }
    else -> { var v = 0L; for (j in 0 until 8) v = (v shl 8) or u(data, off + j).toLong(); Pair(v, off + 8) }
}

private fun dec(data: ByteArray, off0: Int): Pair<Cbor, Int> {
    val initial = u(data, off0)
    val major = initial shr 5
    val info = initial and 0x1f
    val off = off0 + 1
    when (major) {
        0 -> { val (n, o) = readArg(data, off, info); return Pair(Cbor.int(n), o) }
        1 -> { val (n, o) = readArg(data, off, info); return Pair(Cbor.int(-1 - n), o) }
        2 -> { val (n, o) = readArg(data, off, info); val k = n.toInt(); return Pair(Cbor.bytes(data.copyOfRange(o, o + k)), o + k) }
        3 -> { val (n, o) = readArg(data, off, info); val k = n.toInt(); return Pair(Cbor.text(String(data, o, k, Charsets.UTF_8)), o + k) }
        4 -> {
            val (n, o0) = readArg(data, off, info); var o = o0; val a = ArrayList<Cbor>()
            for (j in 0 until n.toInt()) { val (v, o2) = dec(data, o); a.add(v); o = o2 }
            return Pair(Cbor.arr(a), o)
        }
        5 -> {
            val (n, o0) = readArg(data, off, info); var o = o0; val m = ArrayList<Pair<Long, Cbor>>()
            for (j in 0 until n.toInt()) { val (kc, o2) = dec(data, o); val (vc, o3) = dec(data, o2); m.add(Pair(kc.i, vc)); o = o3 }
            return Pair(Cbor.map(m), o)
        }
        7 -> return when (info) {
            20 -> Pair(Cbor.bool(false), off)
            21 -> Pair(Cbor.bool(true), off)
            22 -> Pair(Cbor.nul, off)
            else -> throw RuntimeException("unsupported simple value $info")
        }
    }
    throw RuntimeException("unsupported major type $major")
}
