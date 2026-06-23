package taut

data class FloatVector(val note: String, val f64: String, val cbor: String)

private val vectors = listOf(
    FloatVector("zero", "0000000000000000", "f90000"),
    FloatVector("neg-zero", "8000000000000000", "f98000"),
    FloatVector("one", "3ff0000000000000", "f93c00"),
    FloatVector("neg-one", "bff0000000000000", "f9bc00"),
    FloatVector("one-and-half", "3ff8000000000000", "f93e00"),
    FloatVector("half-min-subnormal", "3e70000000000000", "f90001"),
    FloatVector("half-min-normal", "3f10000000000000", "f90400"),
    FloatVector("half-max", "40effc0000000000", "f97bff"),
    FloatVector("near-miss-not-half-exact-single", "3ff0020000000000", "fa3f801000"),
    FloatVector("single-100000", "40f86a0000000000", "fa47c35000"),
    FloatVector("single-max", "47efffffe0000000", "fa7f7fffff"),
    FloatVector("single-min-subnormal", "36a0000000000000", "fa00000001"),
    FloatVector("double-tenth", "3fb999999999999a", "fb3fb999999999999a"),
    FloatVector("double-1.1", "3ff199999999999a", "fb3ff199999999999a"),
    FloatVector("double-pi", "400921fb54442d18", "fb400921fb54442d18"),
    FloatVector("double-min-subnormal", "0000000000000001", "fb0000000000000001"),
    FloatVector("double-max", "7fefffffffffffff", "fb7fefffffffffffff"),
    FloatVector("pos-inf", "7ff0000000000000", "f97c00"),
    FloatVector("neg-inf", "fff0000000000000", "f9fc00"),
    FloatVector("nan-quiet-canonical", "7ff8000000000000", "f97e00"),
    FloatVector("nan-signaling", "7ff0000000000001", "f97e00"),
    FloatVector("nan-neg-payload", "fff8000000000000", "f97e00"),
)

private val hexChars = "0123456789abcdef".toCharArray()

private fun parseBits(hex: String): Long = java.lang.Long.parseUnsignedLong(hex, 16)

private fun hexToBytes(hex: String): ByteArray {
    val out = ByteArray(hex.length / 2)
    for (i in out.indices) {
        val hi = Character.digit(hex[i * 2], 16)
        val lo = Character.digit(hex[i * 2 + 1], 16)
        out[i] = ((hi shl 4) or lo).toByte()
    }
    return out
}

private fun ByteArray.hex(): String {
    val out = StringBuilder(size * 2)
    for (byte in this) {
        val x = byte.toInt() and 0xff
        out.append(hexChars[x ushr 4])
        out.append(hexChars[x and 0x0f])
    }
    return out.toString()
}

fun main() {
    for (row in vectors) {
        val wantBits = parseBits(row.f64)
        val value = java.lang.Double.longBitsToDouble(wantBits)
        val encoded = encode(Cbor.float(value)).hex()
        check(encoded == row.cbor) { "${row.note}: encode $encoded != ${row.cbor}" }

        val decoded = decode(hexToBytes(row.cbor))
        val reencoded = encode(decoded).hex()
        check(reencoded == row.cbor) { "${row.note}: re-encode $reencoded != ${row.cbor}" }

        if (!row.note.startsWith("nan")) {
            val gotBits = java.lang.Double.doubleToLongBits(decoded.floatVal)
            check(gotBits == wantBits) {
                "${row.note}: decode bits ${java.lang.Long.toUnsignedString(gotBits, 16)} != ${row.f64}"
            }
        }
    }
}
