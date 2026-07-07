// Minimal deterministic CBOR — the Java binding of the frozen wire substrate.
// Same tiny subset (int, float, bytes, text, array, int-keyed map, bool, null),
// core-deterministic (definite length, shortest-form ints, ascending map keys).
// Hand-rolled, JDK only.
package taut;

import java.math.BigInteger;
import java.nio.ByteBuffer;
import java.nio.charset.CharacterCodingException;
import java.nio.charset.CodingErrorAction;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

public final class Cbor {
    public static final int INT = 0, BYTES = 1, TEXT = 2, ARR = 3, MAP = 4, BOOL = 5, NULL = 6, FLOAT = 7;
    public final int kind;
    public final long i;
    public final double d;
    public final String s;
    public final byte[] b;
    public final List<Cbor> arr;
    public final List<KV> map;

    public enum DecodeTag {
        Truncated,
        TrailingBytes,
        InvalidUtf8,
        UnsupportedInfo,
        UnsupportedMajor,
        NonIntegerMapKey,
        IntOverflow,
        DuplicateMapKey,
        MissingKey,
        WrongType,
        UnknownEnum
    }

    public static final class DecodeError extends RuntimeException {
        public final DecodeTag tag;
        public final Long key;
        public final String expected;
        public final String enumName;
        public final String value;
        public final Integer info;
        public final Integer major;

        private DecodeError(
                DecodeTag tag,
                String message,
                Long key,
                String expected,
                String enumName,
                String value,
                Integer info,
                Integer major) {
            super(message);
            this.tag = tag;
            this.key = key;
            this.expected = expected;
            this.enumName = enumName;
            this.value = value;
            this.info = info;
            this.major = major;
        }

        public static DecodeError truncated() {
            return new DecodeError(DecodeTag.Truncated, "truncated CBOR input", null, null, null, null, null, null);
        }

        public static DecodeError trailingBytes() {
            return new DecodeError(
                    DecodeTag.TrailingBytes,
                    "trailing bytes after top-level CBOR item",
                    null,
                    null,
                    null,
                    null,
                    null,
                    null);
        }

        public static DecodeError invalidUtf8() {
            return new DecodeError(DecodeTag.InvalidUtf8, "invalid UTF-8 in CBOR text", null, null, null, null, null, null);
        }

        public static DecodeError unsupportedInfo(int info) {
            return new DecodeError(
                    DecodeTag.UnsupportedInfo,
                    "unsupported CBOR additional-info " + info,
                    null,
                    null,
                    null,
                    null,
                    info,
                    null);
        }

        public static DecodeError unsupportedMajor(int major) {
            return new DecodeError(
                    DecodeTag.UnsupportedMajor,
                    "unsupported CBOR major type " + major,
                    null,
                    null,
                    null,
                    null,
                    null,
                    major);
        }

        public static DecodeError nonIntegerMapKey() {
            return new DecodeError(DecodeTag.NonIntegerMapKey, "non-integer CBOR map key", null, null, null, null, null, null);
        }

        public static DecodeError intOverflow(String value) {
            return new DecodeError(
                    DecodeTag.IntOverflow,
                    "integer outside i64 subset: " + value,
                    null,
                    null,
                    null,
                    value,
                    null,
                    null);
        }

        public static DecodeError duplicateMapKey(long key) {
            return new DecodeError(
                    DecodeTag.DuplicateMapKey,
                    "duplicate CBOR map key " + key,
                    key,
                    null,
                    null,
                    null,
                    null,
                    null);
        }

        public static DecodeError missingKey(long key) {
            return new DecodeError(
                    DecodeTag.MissingKey,
                    "missing CBOR map key " + key,
                    key,
                    null,
                    null,
                    null,
                    null,
                    null);
        }

        public static DecodeError wrongType(String expected) {
            return new DecodeError(
                    DecodeTag.WrongType,
                    "expected CBOR " + expected,
                    null,
                    expected,
                    null,
                    null,
                    null,
                    null);
        }

        public static DecodeError unknownEnum(String enumName, long value) {
            return new DecodeError(
                    DecodeTag.UnknownEnum,
                    "unknown " + enumName + " wire value " + value,
                    null,
                    null,
                    enumName,
                    Long.toString(value),
                    null,
                    null);
        }
    }

    private Cbor(int kind, long i, double d, String s, byte[] b, List<Cbor> arr, List<KV> map) {
        this.kind = kind; this.i = i; this.d = d; this.s = s; this.b = b; this.arr = arr; this.map = map;
    }
    public static Cbor int_(long n) { return new Cbor(INT, n, 0.0, null, null, null, null); }
    public static Cbor float_(double v) { return new Cbor(FLOAT, 0, v, null, null, null, null); }
    public static Cbor text(String s) { return new Cbor(TEXT, 0, 0.0, s, null, null, null); }
    public static Cbor bytes(byte[] b) { return new Cbor(BYTES, 0, 0.0, null, b, null, null); }
    public static Cbor bool(boolean x) { return new Cbor(BOOL, x ? 1 : 0, 0.0, null, null, null, null); }
    public static Cbor arr(List<Cbor> a) { return new Cbor(ARR, 0, 0.0, null, null, a, null); }
    public static Cbor map(List<KV> m) { return new Cbor(MAP, 0, 0.0, null, null, null, m); }
    public static final Cbor NUL = new Cbor(NULL, 0, 0.0, null, null, null, null);

    public Cbor get(long key) {
        if (kind != MAP) throw DecodeError.wrongType("map");
        for (KV kv : map) if (kv.k == key) return kv.v;
        throw DecodeError.missingKey(key);
    }
    public boolean isNull() { return kind == NULL; }
    public long asInt() { if (kind == INT) return i; throw DecodeError.wrongType("int"); }
    public double asFloat() { if (kind == FLOAT) return d; throw DecodeError.wrongType("float"); }
    public String asText() { if (kind == TEXT) return s; throw DecodeError.wrongType("text"); }
    public byte[] asBytes() { if (kind == BYTES) return b; throw DecodeError.wrongType("bytes"); }
    public boolean asBool() { if (kind == BOOL) return i != 0; throw DecodeError.wrongType("bool"); }
    public List<Cbor> asArray() { if (kind == ARR) return arr; throw DecodeError.wrongType("array"); }
    public List<KV> mapEntries() { if (kind == MAP) return map; throw DecodeError.wrongType("map"); }

    public static byte[] encode(Cbor c) {
        List<Byte> out = new ArrayList<>();
        enc(c, out);
        byte[] r = new byte[out.size()];
        for (int i = 0; i < r.length; i++) r[i] = out.get(i);
        return r;
    }
    private static void head(List<Byte> out, int major, long n) {
        int mt = major << 5;
        if (n < 24) out.add((byte) (mt | n));
        else if (n < 0x100L) { out.add((byte) (mt | 24)); out.add((byte) n); }
        else if (n < 0x10000L) { out.add((byte) (mt | 25)); out.add((byte) (n >> 8)); out.add((byte) n); }
        else if (n < 0x100000000L) { out.add((byte) (mt | 26)); for (int sh = 24; sh >= 0; sh -= 8) out.add((byte) (n >> sh)); }
        else { out.add((byte) (mt | 27)); for (int sh = 56; sh >= 0; sh -= 8) out.add((byte) (n >> sh)); }
    }
    private static void emit16(List<Byte> out, int bits) {
        out.add((byte) (bits >> 8));
        out.add((byte) bits);
    }
    private static void emit32(List<Byte> out, int bits) {
        for (int sh = 24; sh >= 0; sh -= 8) out.add((byte) (bits >> sh));
    }
    private static void emit64(List<Byte> out, long bits) {
        for (int sh = 56; sh >= 0; sh -= 8) out.add((byte) (bits >> sh));
    }
    private static long roundRight(long n, int shift) {
        long q = n >>> shift;
        long rem = n & ((1L << shift) - 1);
        long half = 1L << (shift - 1);
        if (rem > half || (rem == half && (q & 1L) != 0)) q++;
        return q;
    }
    private static int doubleToHalfBits(double v) {
        long bits = Double.doubleToRawLongBits(v);
        int sign = (int) (bits >>> 63);
        int halfSign = sign << 15;
        long abs = bits & 0x7fffffffffffffffL;
        int exp = (int) ((abs >>> 52) & 0x7ff);
        long frac = abs & 0x000fffffffffffffL;
        if (exp == 0) return halfSign;
        if (exp == 0x7ff) return halfSign | (frac == 0 ? 0x7c00 : 0x7e00);

        int e = exp - 1023;
        long sig = (1L << 52) | frac;
        if (e > 15) return halfSign | 0x7c00;
        if (e >= -14) {
            long rounded = roundRight(sig, 42);
            int halfExp = e + 15;
            if (rounded == 0x800) {
                rounded = 0x400;
                halfExp++;
            }
            if (halfExp >= 31) return halfSign | 0x7c00;
            return halfSign | (halfExp << 10) | ((int) rounded & 0x3ff);
        }
        if (e < -25) return halfSign;
        long rounded = roundRight(sig, 28 - e);
        if (rounded == 0) return halfSign;
        if (rounded >= 0x400) return halfSign | 0x0400;
        return halfSign | (int) rounded;
    }
    private static double halfToDouble(int bits) {
        long sign = ((long) bits & 0x8000L) << 48;
        int exp = (bits >>> 10) & 0x1f;
        int frac = bits & 0x3ff;
        if (exp == 0) {
            if (frac == 0) return Double.longBitsToDouble(sign);
            double v = Math.scalb((double) frac, -24);
            return sign == 0 ? v : -v;
        }
        if (exp == 0x1f) {
            long payload = frac == 0 ? 0L : ((long) frac << 42);
            return Double.longBitsToDouble(sign | 0x7ff0000000000000L | payload);
        }
        long doubleExp = (long) (exp - 15 + 1023) << 52;
        return Double.longBitsToDouble(sign | doubleExp | ((long) frac << 42));
    }
    private static void encFloat(double v, List<Byte> out) {
        if (Double.isNaN(v)) {
            out.add((byte) 0xf9);
            out.add((byte) 0x7e);
            out.add((byte) 0x00);
            return;
        }
        int h = doubleToHalfBits(v);
        if (Double.doubleToLongBits(halfToDouble(h)) == Double.doubleToLongBits(v)) {
            out.add((byte) 0xf9);
            emit16(out, h);
            return;
        }
        float f = (float) v;
        if (Double.doubleToLongBits((double) f) == Double.doubleToLongBits(v)) {
            out.add((byte) 0xfa);
            emit32(out, Float.floatToIntBits(f));
            return;
        }
        out.add((byte) 0xfb);
        emit64(out, Double.doubleToLongBits(v));
    }
    private static void enc(Cbor c, List<Byte> out) {
        switch (c.kind) {
            case INT -> { if (c.i >= 0) head(out, 0, c.i); else head(out, 1, -1 - c.i); }
            case FLOAT -> encFloat(c.d, out);
            case BYTES -> { head(out, 2, c.b.length); for (byte x : c.b) out.add(x); }
            case TEXT -> { byte[] bb = c.s.getBytes(StandardCharsets.UTF_8); head(out, 3, bb.length); for (byte x : bb) out.add(x); }
            case ARR -> { head(out, 4, c.arr.size()); for (Cbor x : c.arr) enc(x, out); }
            case MAP -> {
                List<KV> m = new ArrayList<>(c.map);
                m.sort((a, b2) -> Long.compare(a.k, b2.k)); // ascending keys
                head(out, 5, m.size());
                for (KV kv : m) {
                    if (kv.k >= 0) head(out, 0, kv.k);
                    else head(out, 1, -1 - kv.k);
                    enc(kv.v, out);
                }
            }
            case BOOL -> out.add((byte) (c.i != 0 ? 0xf5 : 0xf4));
            case NULL -> out.add((byte) 0xf6);
            default -> throw new IllegalArgumentException("unknown CBOR kind " + c.kind);
        }
    }
    public static Cbor decode(byte[] data) {
        int[] off = {0};
        Cbor v = dec(data, off);
        if (off[0] != data.length) throw DecodeError.trailingBytes();
        return v;
    }
    private static int u(byte[] d, int i) {
        if (i < 0 || i >= d.length) throw DecodeError.truncated();
        return d[i] & 0xFF;
    }
    private static void require(byte[] d, int off, int len) {
        if (off < 0 || len < 0 || off > d.length || len > d.length - off) throw DecodeError.truncated();
    }
    private static long readArg(byte[] d, int[] off, int info) {
        if (info < 24) return info;
        if (info == 24) { require(d, off[0], 1); long v = u(d, off[0]); off[0] += 1; return v; }
        if (info == 25) { require(d, off[0], 2); long v = ((long) u(d, off[0]) << 8) | u(d, off[0] + 1); off[0] += 2; return v; }
        if (info == 26) {
            require(d, off[0], 4);
            long v = 0;
            for (int j = 0; j < 4; j++) v = (v << 8) | u(d, off[0] + j);
            off[0] += 4;
            return v;
        }
        if (info == 27) {
            require(d, off[0], 8);
            long v = 0;
            for (int j = 0; j < 8; j++) v = (v << 8) | u(d, off[0] + j);
            off[0] += 8;
            return v;
        }
        throw DecodeError.unsupportedInfo(info);
    }
    private static int readLength(byte[] d, int[] off, int info) {
        long n = readArg(d, off, info);
        if (Long.compareUnsigned(n, Integer.MAX_VALUE) > 0) throw DecodeError.truncated();
        return (int) n;
    }
    private static String unsignedStringPlusOne(long n) {
        return new BigInteger(Long.toUnsignedString(n)).add(BigInteger.ONE).toString();
    }
    private static String decodeUtf8(byte[] d, int off, int n) {
        try {
            return StandardCharsets.UTF_8
                    .newDecoder()
                    .onMalformedInput(CodingErrorAction.REPORT)
                    .onUnmappableCharacter(CodingErrorAction.REPORT)
                    .decode(ByteBuffer.wrap(d, off, n))
                    .toString();
        } catch (CharacterCodingException exc) {
            throw DecodeError.invalidUtf8();
        }
    }
    private static Cbor dec(byte[] d, int[] off) {
        int initial = u(d, off[0]); off[0]++;
        int major = initial >> 5, info = initial & 0x1f;
        switch (major) {
            case 0 -> {
                long n = readArg(d, off, info);
                if (n < 0) throw DecodeError.intOverflow(Long.toUnsignedString(n));
                return int_(n);
            }
            case 1 -> {
                long n = readArg(d, off, info);
                if (n < 0) throw DecodeError.intOverflow("-" + unsignedStringPlusOne(n));
                return int_(-1 - n);
            }
            case 2 -> {
                int n = readLength(d, off, info);
                require(d, off[0], n);
                byte[] bb = new byte[n];
                System.arraycopy(d, off[0], bb, 0, n);
                off[0] += n;
                return bytes(bb);
            }
            case 3 -> {
                int n = readLength(d, off, info);
                require(d, off[0], n);
                String s = decodeUtf8(d, off[0], n);
                off[0] += n;
                return text(s);
            }
            case 4 -> {
                int n = readLength(d, off, info);
                List<Cbor> a = new ArrayList<>();
                for (int j = 0; j < n; j++) a.add(dec(d, off));
                return arr(a);
            }
            case 5 -> {
                int n = readLength(d, off, info);
                List<KV> m = new ArrayList<>();
                Set<Long> seen = new HashSet<>();
                for (int j = 0; j < n; j++) {
                    Cbor k = dec(d, off);
                    if (k.kind != INT) throw DecodeError.nonIntegerMapKey();
                    if (!seen.add(k.i)) throw DecodeError.duplicateMapKey(k.i);
                    Cbor v = dec(d, off);
                    m.add(new KV(k.i, v));
                }
                return map(m);
            }
            case 7 -> {
                if (info == 20) return bool(false);
                if (info == 21) return bool(true);
                if (info == 22) return NUL;
                if (info == 25) return float_(halfToDouble((int) readArg(d, off, info)));
                if (info == 26) return float_((double) Float.intBitsToFloat((int) readArg(d, off, info)));
                if (info == 27) return float_(Double.longBitsToDouble(readArg(d, off, info)));
                throw DecodeError.unsupportedInfo(info);
            }
            default -> throw DecodeError.unsupportedMajor(major);
        }
    }
}

final class KV {
    public final long k;
    public final Cbor v;
    public KV(long k, Cbor v) { this.k = k; this.v = v; }
}
