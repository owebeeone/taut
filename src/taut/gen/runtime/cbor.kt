// Minimal deterministic CBOR — the Kotlin binding of the frozen wire substrate.
// Same tiny subset (int, bytes, text, array, int-keyed map, bool, null, float)
// in core-deterministic encoding (definite length, shortest-form ints/floats,
// ascending map keys). Hand-rolled, stdlib only.
//
// Decode is bounded (D26, TautCheckedDecode.md §3). An array or map has depth one more than
// the arrays and maps around it, and one deeper than the call's depth bound is TooDeep(limit);
// with a length bound, longer input is TooLarge(len, limit) before a byte is read. For any
// input bytes `decode` returns a value or throws DecodeError, nothing else.
package taut

// The depth bound a raw decode applies where its caller passes none, and the deepest bound any
// decode applies (TautCheckedDecode.md CD-B1, CD-B3). The parity corpus pins both to taut's.
const val DEFAULT_MAX_DEPTH: Int = 32
const val MAX_DEPTH_CEILING: Int = 128

sealed class DecodeError(message: String) : RuntimeException(message) {
    class Truncated : DecodeError("truncated CBOR input")
    class TrailingBytes : DecodeError("trailing bytes after top-level CBOR item")
    class InvalidUtf8 : DecodeError("invalid UTF-8 in CBOR text string")
    class UnsupportedInfo(val info: Int) : DecodeError("unsupported additional-info $info")
    class UnsupportedMajor(val major: Int) : DecodeError("unsupported major type $major")
    class NonIntegerMapKey : DecodeError("non-integer map key")
    class IntOverflow(val value: String) : DecodeError("integer out of i64 range: $value")
    // The repeated key: a Long for a CBOR map key or an int-keyed map<K,V> field, and
    // the String or Boolean key of a text- or bool-keyed one. Its text is the key as
    // text (TautCheckedDecode.md §8 question 9): an int in decimal, a str as itself and
    // a bool as `true` or `false`.
    class DuplicateMapKey(val key: Any) : DecodeError("duplicate map key $key")
    class MissingKey(val key: Long) : DecodeError("missing map key $key")
    class WrongType(val expected: String) : DecodeError("expected CBOR $expected")
    class UnknownEnum(val enumName: String, val value: Long) :
        DecodeError("unknown $enumName wire value $value")
    // D2 strictness: a 1/2/4/8-byte argument that fits a shorter form (value is the
    // raw argument), and a map key below zero.
    class NonCanonicalInt(val value: Long) : DecodeError("non-canonical integer encoding of $value")
    class NegativeMapKey(val key: Long) : DecodeError("negative map key $key")
    // The bounds (CD-E1): an array or map deeper than the depth bound `limit`, the bound
    // applied; and input of `len` bytes, longer than the length bound `limit`.
    class TooDeep(val limit: Int) : DecodeError("an array or map deeper than $limit")
    class TooLarge(val len: Int, val limit: Int) : DecodeError("$len bytes of input, more than $limit")
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
        // The order of a map<str,V> field's keys: by Unicode code point, which is the order
        // of their UTF-8 bytes. String.compareTo, and so toSortedMap(), compares UTF-16 code
        // units, which puts U+10000 (d800 dc00) before U+FFFF.
        val codePointOrder: Comparator<String> = Comparator { a, b -> compareCodePoints(a, b) }
    }

    fun get(key: Long): Cbor {
        if (kind != MAP) throw DecodeError.WrongType("map")
        for (kv in map) if (kv.first == key) return kv.second
        throw DecodeError.MissingKey(key)
    }
    // An optional=MISSING_OK field: an absent key is null, but this must still be a map.
    fun getOrNull(key: Long): Cbor? {
        if (kind != MAP) {
            throw DecodeError.WrongType("map")
        }
        for (kv in map) {
            if (kv.first == key) {
                return kv.second
            }
        }
        return null
    }
    // A map<K,V> field: an array of {1: key, 2: value} entry maps, read in order (CD-E5).
    // Each entry must be a map holding key 1, then key 2, before `entry` decodes either,
    // and a repeated key is DuplicateMapKey before its value is decoded. The check reads
    // the raw key, before `entry`: K is an int, text or bool scalar, so a raw key equal to
    // an earlier one (which decoded) decodes to an equal key, and any other does not.
    fun <K, V> mapFieldVal(entry: (Cbor) -> Pair<K, V>): Map<K, V> {
        val out = LinkedHashMap<K, V>()
        val seen = HashSet<Any>()
        for (e in arrVal) {
            val key = e.get(1)
            e.get(2)
            val raw = scalarKey(key)
            if (raw != null && !seen.add(raw)) {
                throw DecodeError.DuplicateMapKey(raw)
            }
            val (k, v) = entry(e)
            out[k] = v
        }
        return out
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

private fun compareCodePoints(a: String, b: String): Int {
    val n = minOf(a.length, b.length)
    var i = 0
    while (i < n) {
        val x = a.codePointAt(i)
        val y = b.codePointAt(i)
        if (x != y) {
            return x.compareTo(y)
        }
        i += Character.charCount(x)
    }
    return a.length.compareTo(b.length)
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

// One item that fills `data`, or DecodeError at the first fault (CD-E5). `maxDepth` bounds
// nesting: a top-level array or map has depth 1, and one at depth maxDepth + 1 is TooDeep once
// its head is read. A value above MAX_DEPTH_CEILING applies the ceiling, and TooDeep.limit
// names the bound applied. `maxEncodedLen`, when given, bounds the input's length, checked
// before any byte is read. A depth below 1 or a negative length is the caller's error,
// IllegalArgumentException, not a DecodeError. A message's own `decode(bytes)` passes its
// bounds here; a raw caller passes the ones it means to apply.
fun decode(data: ByteArray, maxDepth: Int = DEFAULT_MAX_DEPTH, maxEncodedLen: Int? = null): Cbor {
    require(maxDepth >= 1) { "maxDepth must be at least 1, not $maxDepth" }
    if (maxEncodedLen != null) {
        require(maxEncodedLen >= 0) { "maxEncodedLen must not be negative, not $maxEncodedLen" }
        if (data.size > maxEncodedLen) {
            throw DecodeError.TooLarge(data.size, maxEncodedLen)
        }
    }
    val (v, off) = dec(data, 0, 0, minOf(maxDepth, MAX_DEPTH_CEILING))
    if (off != data.size) {
        throw DecodeError.TrailingBytes()
    }
    return v
}

// A container whose head is complete, inside `depth` others: refused before its first item
// when it would sit deeper than `limit` (CD-B2). Checked before `dec` recurses, it also bounds
// the recursion, so no input reaches the stack's limit.
private fun enter(depth: Int, limit: Int) {
    if (depth >= limit) {
        throw DecodeError.TooDeep(limit)
    }
}

// A head's argument, as the raw unsigned 64 bits. Info 28-31 is UnsupportedInfo, missing
// bytes are Truncated, and (D2) a 1/2/4/8-byte argument that fits a shorter form is
// NonCanonicalInt: the canonical encoder never writes one, whether it is an int, a
// length or a count. Floats do not come here.
private fun readArg(data: ByteArray, off: Int, info: Int): Pair<Long, Int> {
    if (info < 24) {
        return Pair(info.toLong(), off)
    }
    val width = when (info) {
        24 -> 1
        25 -> 2
        26 -> 4
        27 -> 8
        else -> throw DecodeError.UnsupportedInfo(info)
    }
    ensure(data, off, width)
    var v = 0L
    for (j in 0 until width) {
        v = (v shl 8) or u(data, off + j).toLong()
    }
    val shorterMax = when (width) {
        1 -> 23L
        2 -> 0xFFL
        4 -> 0xFFFFL
        else -> 0xFFFF_FFFFL
    }
    if (v >= 0 && v <= shorterMax) {
        throw DecodeError.NonCanonicalInt(v)
    }
    return Pair(v, off + width)
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

// A byte or text length (unsigned bits) beyond the bytes left after `off` is Truncated,
// whatever its size.
private fun lengthArg(data: ByteArray, off: Int, bits: Long): Int {
    if (bits < 0 || bits > (data.size - off).toLong()) {
        throw DecodeError.Truncated()
    }
    return bits.toInt()
}

// A map<K,V> entry's raw key as the value its decoded key would be, or null when it is
// not a key scalar (decoding it is then WrongType).
private fun scalarKey(c: Cbor): Any? = when (c.kind) {
    Cbor.INT -> c.i
    Cbor.TEXT -> c.s
    Cbor.BOOL -> c.i != 0L
    else -> null
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

// The item at `off0`, inside `depth` arrays and maps, under the depth bound `limit`.
private fun dec(data: ByteArray, off0: Int, depth: Int, limit: Int): Pair<Cbor, Int> {
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
            val k = lengthArg(data, o, n)
            return Pair(Cbor.bytes(data.copyOfRange(o, o + k)), o + k)
        }
        3 -> {
            val (n, o) = readArg(data, off, info)
            val k = lengthArg(data, o, n)
            return Pair(Cbor.text(utf8(data, o, k)), o + k)
        }
        // A count (unsigned) is not checked against the bytes left: items are read in
        // order, so the first fault is reported, and every item takes at least one byte.
        // Once the head is read, a container one level too deep is TooDeep (enter).
        4 -> {
            val (n, o0) = readArg(data, off, info)
            enter(depth, limit)
            var o = o0
            val a = ArrayList<Cbor>()
            var j = 0L
            while (java.lang.Long.compareUnsigned(j, n) < 0) {
                val (v, o2) = dec(data, o, depth + 1, limit)
                a.add(v)
                o = o2
                j += 1
            }
            return Pair(Cbor.arr(a), o)
        }
        5 -> {
            val (n, o0) = readArg(data, off, info)
            enter(depth, limit)
            var o = o0
            val m = ArrayList<Pair<Long, Cbor>>()
            val seen = HashSet<Long>()
            var j = 0L
            while (java.lang.Long.compareUnsigned(j, n) < 0) {
                // The key first: its item, then NonIntegerMapKey, NegativeMapKey and
                // DuplicateMapKey, and only then the value.
                val (kc, o2) = dec(data, o, depth + 1, limit)
                if (kc.kind != Cbor.INT) {
                    throw DecodeError.NonIntegerMapKey()
                }
                val key = kc.i
                if (key < 0) {
                    throw DecodeError.NegativeMapKey(key)
                }
                if (!seen.add(key)) {
                    throw DecodeError.DuplicateMapKey(key)
                }
                val (vc, o3) = dec(data, o2, depth + 1, limit)
                m.add(Pair(key, vc))
                o = o3
                j += 1
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
                for (j in 0 until 4) {
                    bits = (bits shl 8) or u(data, off + j)
                }
                Pair(Cbor.float(java.lang.Float.intBitsToFloat(bits).toDouble()), off + 4)
            }
            27 -> {
                ensure(data, off, 8)
                var bits = 0L
                for (j in 0 until 8) {
                    bits = (bits shl 8) or u(data, off + j).toLong()
                }
                Pair(Cbor.float(java.lang.Double.longBitsToDouble(bits)), off + 8)
            }
            else -> throw DecodeError.UnsupportedInfo(info)
        }
        6 -> throw DecodeError.UnsupportedMajor(major)
    }
    throw DecodeError.UnsupportedMajor(major)
}
