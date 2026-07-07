// Minimal deterministic CBOR — the Kotlin binding of the frozen wire substrate.
// Same tiny subset (int, bytes, text, array, int-keyed map, bool, null, float)
// in core-deterministic encoding (definite length, shortest-form ints/floats,
// ascending map keys). Hand-rolled, stdlib only.
package taut

sealed class DecodeError(message: String) : RuntimeException(message) {
    class Truncated : DecodeError("truncated CBOR input")
    class TrailingBytes : DecodeError("trailing bytes after top-level CBOR item")
    class InvalidUtf8 : DecodeError("invalid UTF-8 in CBOR text string")
    class UnsupportedInfo(val info: Int) : DecodeError("unsupported additional-info $info")
    class UnsupportedMajor(val major: Int) : DecodeError("unsupported major type $major")
    class NonIntegerMapKey : DecodeError("non-integer map key")
    class IntOverflow(val value: String) : DecodeError("integer out of i64 range: $value")
    class DuplicateMapKey(val key: Long) : DecodeError("duplicate map key $key")
    class MissingKey(val key: Long) : DecodeError("missing map key $key")
    class WrongType(val expected: String) : DecodeError("expected CBOR $expected")
    class UnknownEnum(val enumName: String, val value: Long) :
        DecodeError("unknown $enumName wire value $value")
}

class Cbor(
    val kind: Int,
    val i: Long = 0,
    val s: String = "",
    val b: ByteArray = ByteArray(0),
    val arr: List<Cbor> = emptyList(),
    val map: List<Pair<Long, Cbor>> = emptyList(),
    val f: Double = 0.0,
) {
    companion object {
        const val INT = 0; const val BYTES = 1; const val TEXT = 2
        const val ARR = 3; const val MAP = 4; const val BOOL = 5; const val NULL = 6
        const val FLOAT = 7
        fun int(n: Long) = Cbor(INT, i = n)
        fun text(s: String) = Cbor(TEXT, s = s)
        fun bytes(b: ByteArray) = Cbor(BYTES, b = b)
        fun bool(x: Boolean) = Cbor(BOOL, i = if (x) 1 else 0)
        fun float(x: Double) = Cbor(FLOAT, f = x)
        fun arr(a: List<Cbor>) = Cbor(ARR, arr = a)
        fun map(m: List<Pair<Long, Cbor>>) = Cbor(MAP, map = m)
        val nul = Cbor(NULL)
    }

    fun get(key: Long): Cbor {
        if (kind != MAP) throw DecodeError.WrongType("map")
        for (kv in map) if (kv.first == key) return kv.second
        throw DecodeError.MissingKey(key)
    }
    val intVal: Long get() {
        if (kind != INT) throw DecodeError.WrongType("int")
        return i
    }
    val textVal: String get() {
        if (kind != TEXT) throw DecodeError.WrongType("text")
        return s
    }
    val bytesVal: ByteArray get() {
        if (kind != BYTES) throw DecodeError.WrongType("bytes")
        return b
    }
    val boolVal: Boolean get() {
        if (kind != BOOL) throw DecodeError.WrongType("bool")
        return i != 0L
    }
    val arrVal: List<Cbor> get() {
        if (kind != ARR) throw DecodeError.WrongType("array")
        return arr
    }
    val floatVal: Double get() {
        if (kind != FLOAT) throw DecodeError.WrongType("float")
        return f
    }
    val isNull: Boolean get() = kind == NULL
    val mapEntries: List<Pair<Long, Cbor>> get() {
        if (kind != MAP) throw DecodeError.WrongType("map")
        return map
    }  // forward-compat residual
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

private fun put16(out: MutableList<Byte>, bits: Int) {
    out.add(((bits ushr 8) and 0xff).toByte())
    out.add((bits and 0xff).toByte())
}

private fun put32(out: MutableList<Byte>, bits: Int) {
    for (sh in intArrayOf(24, 16, 8, 0)) out.add(((bits ushr sh) and 0xff).toByte())
}

private fun put64(out: MutableList<Byte>, bits: Long) {
    for (sh in intArrayOf(56, 48, 40, 32, 24, 16, 8, 0)) out.add(((bits ushr sh) and 0xff).toByte())
}

private fun roundShiftEven(n: Long, shift: Int): Long {
    if (shift <= 0) return n shl (-shift)
    if (shift > 54) return 0L
    val q = n ushr shift
    val remMask = (1L shl shift) - 1L
    val rem = n and remMask
    val half = 1L shl (shift - 1)
    return if (rem > half || (rem == half && (q and 1L) != 0L)) q + 1L else q
}

private fun doubleToHalfBits(v: Double): Int {
    val bits = java.lang.Double.doubleToLongBits(v)
    val sign = ((bits ushr 48) and 0x8000L).toInt()
    val exp = ((bits ushr 52) and 0x7ffL).toInt()
    val frac = bits and 0x000f_ffff_ffff_ffffL
    if (exp == 0x7ff) return sign or (if (frac == 0L) 0x7c00 else 0x7e00)
    if (exp == 0) return sign

    var e = exp - 1023
    val mant = frac or (1L shl 52)
    if (e < -14) {
        val q = roundShiftEven(mant, 28 - e).toInt()
        return sign or q
    }

    var q = roundShiftEven(mant, 42).toInt()
    if (q == 0x800) {
        e += 1
        q = 0x400
    }
    val halfExp = e + 15
    if (halfExp >= 31) return sign or 0x7c00
    return sign or (halfExp shl 10) or (q - 0x400)
}

private fun halfBitsToDouble(bits: Int): Double {
    val sign = bits and 0x8000
    val exp = (bits ushr 10) and 0x1f
    val frac = bits and 0x03ff
    val signFactor = if (sign == 0) 1.0 else -1.0
    return when (exp) {
        0 -> if (frac == 0) {
            java.lang.Double.longBitsToDouble(sign.toLong() shl 48)
        } else {
            signFactor * java.lang.Math.scalb(frac.toDouble(), -24)
        }
        31 -> if (frac == 0) {
            if (sign == 0) java.lang.Double.POSITIVE_INFINITY else java.lang.Double.NEGATIVE_INFINITY
        } else {
            java.lang.Double.NaN
        }
        else -> signFactor * java.lang.Math.scalb((0x400 + frac).toDouble(), exp - 25)
    }
}

private fun encFloat(v: Double, out: MutableList<Byte>) {
    if (v.isNaN()) {
        out.add(0xf9.toByte()); put16(out, 0x7e00); return
    }
    val want = java.lang.Double.doubleToLongBits(v)
    val h = doubleToHalfBits(v)
    if (java.lang.Double.doubleToLongBits(halfBitsToDouble(h)) == want) {
        out.add(0xf9.toByte()); put16(out, h); return
    }
    val f = v.toFloat()
    if (java.lang.Double.doubleToLongBits(f.toDouble()) == want) {
        out.add(0xfa.toByte()); put32(out, java.lang.Float.floatToIntBits(f)); return
    }
    out.add(0xfb.toByte()); put64(out, java.lang.Double.doubleToLongBits(v))
}

private fun encInt(n: Long, out: MutableList<Byte>) {
    if (n >= 0) head(out, 0, n) else head(out, 1, -1L - n)
}

fun encode(c: Cbor): ByteArray {
    val out = ArrayList<Byte>()
    enc(c, out)
    return out.toByteArray()
}

private fun enc(c: Cbor, out: MutableList<Byte>) {
    when (c.kind) {
        Cbor.INT -> encInt(c.i, out)
        Cbor.BYTES -> { head(out, 2, c.b.size.toLong()); for (x in c.b) out.add(x) }
        Cbor.TEXT -> { val bb = c.s.toByteArray(Charsets.UTF_8); head(out, 3, bb.size.toLong()); for (x in bb) out.add(x) }
        Cbor.ARR -> { head(out, 4, c.arr.size.toLong()); for (x in c.arr) enc(x, out) }
        Cbor.MAP -> {
            val m = c.map.sortedBy { it.first }  // deterministic: ascending keys
            head(out, 5, m.size.toLong())
            for (kv in m) { encInt(kv.first, out); enc(kv.second, out) }
        }
        Cbor.BOOL -> out.add((if (c.i != 0L) 0xf5 else 0xf4).toByte())
        Cbor.NULL -> out.add(0xf6.toByte())
        Cbor.FLOAT -> encFloat(c.f, out)
    }
}

private fun u(data: ByteArray, i: Int): Int = data[i].toInt() and 0xFF

private fun ensure(data: ByteArray, off: Int, n: Int) {
    if (off < 0 || n < 0 || off > data.size || data.size - off < n) throw DecodeError.Truncated()
}

fun decode(data: ByteArray): Cbor {
    val (v, off) = dec(data, 0)
    if (off != data.size) throw DecodeError.TrailingBytes()
    return v
}

private fun readArg(data: ByteArray, off: Int, info: Int): Pair<Long, Int> = when {
    info < 24 -> Pair(info.toLong(), off)
    info == 24 -> {
        ensure(data, off, 1)
        Pair(u(data, off).toLong(), off + 1)
    }
    info == 25 -> {
        ensure(data, off, 2)
        Pair((u(data, off).toLong() shl 8) or u(data, off + 1).toLong(), off + 2)
    }
    info == 26 -> {
        ensure(data, off, 4)
        var v = 0L
        for (j in 0 until 4) v = (v shl 8) or u(data, off + j).toLong()
        Pair(v, off + 4)
    }
    info == 27 -> {
        ensure(data, off, 8)
        var v = 0L
        for (j in 0 until 8) v = (v shl 8) or u(data, off + j).toLong()
        Pair(v, off + 8)
    }
    else -> throw DecodeError.UnsupportedInfo(info)
}

private fun unsignedString(bits: Long): String = java.lang.Long.toUnsignedString(bits)

private fun positiveInt(bits: Long): Long {
    if (bits < 0) throw DecodeError.IntOverflow(unsignedString(bits))
    return bits
}

private fun negativeInt(bits: Long): Long {
    if (bits < 0) {
        val unsigned = java.math.BigInteger(unsignedString(bits))
        throw DecodeError.IntOverflow(unsigned.add(java.math.BigInteger.ONE).negate().toString())
    }
    return -1L - bits
}

private fun sizeArg(bits: Long): Int {
    if (bits < 0 || bits > Int.MAX_VALUE.toLong()) throw DecodeError.IntOverflow(unsignedString(bits))
    return bits.toInt()
}

private fun utf8(data: ByteArray, off: Int, len: Int): String {
    val decoder = Charsets.UTF_8.newDecoder()
        .onMalformedInput(java.nio.charset.CodingErrorAction.REPORT)
        .onUnmappableCharacter(java.nio.charset.CodingErrorAction.REPORT)
    try {
        return decoder.decode(java.nio.ByteBuffer.wrap(data, off, len)).toString()
    } catch (e: java.nio.charset.CharacterCodingException) {
        throw DecodeError.InvalidUtf8()
    }
}

private fun dec(data: ByteArray, off0: Int): Pair<Cbor, Int> {
    ensure(data, off0, 1)
    val initial = u(data, off0)
    val major = initial shr 5
    val info = initial and 0x1f
    val off = off0 + 1
    when (major) {
        0 -> { val (n, o) = readArg(data, off, info); return Pair(Cbor.int(positiveInt(n)), o) }
        1 -> { val (n, o) = readArg(data, off, info); return Pair(Cbor.int(negativeInt(n)), o) }
        2 -> {
            val (n, o) = readArg(data, off, info)
            val k = sizeArg(n)
            ensure(data, o, k)
            return Pair(Cbor.bytes(data.copyOfRange(o, o + k)), o + k)
        }
        3 -> {
            val (n, o) = readArg(data, off, info)
            val k = sizeArg(n)
            ensure(data, o, k)
            return Pair(Cbor.text(utf8(data, o, k)), o + k)
        }
        4 -> {
            val (n, o0) = readArg(data, off, info); var o = o0; val a = ArrayList<Cbor>()
            for (j in 0 until sizeArg(n)) { val (v, o2) = dec(data, o); a.add(v); o = o2 }
            return Pair(Cbor.arr(a), o)
        }
        5 -> {
            val (n, o0) = readArg(data, off, info); var o = o0; val m = ArrayList<Pair<Long, Cbor>>()
            val seen = HashSet<Long>()
            for (j in 0 until sizeArg(n)) {
                val (kc, o2) = dec(data, o)
                if (kc.kind != Cbor.INT) throw DecodeError.NonIntegerMapKey()
                val key = kc.intVal
                if (!seen.add(key)) throw DecodeError.DuplicateMapKey(key)
                val (vc, o3) = dec(data, o2)
                m.add(Pair(key, vc))
                o = o3
            }
            return Pair(Cbor.map(m), o)
        }
        7 -> return when (info) {
            20 -> Pair(Cbor.bool(false), off)
            21 -> Pair(Cbor.bool(true), off)
            22 -> Pair(Cbor.nul, off)
            25 -> {
                ensure(data, off, 2)
                Pair(Cbor.float(halfBitsToDouble((u(data, off) shl 8) or u(data, off + 1))), off + 2)
            }
            26 -> {
                ensure(data, off, 4)
                var bits = 0
                for (j in 0 until 4) bits = (bits shl 8) or u(data, off + j)
                Pair(Cbor.float(java.lang.Float.intBitsToFloat(bits).toDouble()), off + 4)
            }
            27 -> {
                ensure(data, off, 8)
                var bits = 0L
                for (j in 0 until 8) bits = (bits shl 8) or u(data, off + j).toLong()
                Pair(Cbor.float(java.lang.Double.longBitsToDouble(bits)), off + 8)
            }
            else -> throw DecodeError.UnsupportedInfo(info)
        }
        6 -> throw DecodeError.UnsupportedMajor(major)
    }
    throw DecodeError.UnsupportedMajor(major)
}
