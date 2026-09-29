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
import java.util.Comparator;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.SortedMap;
import java.util.TreeMap;
import java.util.function.Function;

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
        UnknownEnum,
        NonCanonicalInt,
        NegativeMapKey
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

        // `value` is the raw unsigned argument, which a shorter form could have held.
        public static DecodeError nonCanonicalInt(long value) {
            String text = Long.toUnsignedString(value);
            return new DecodeError(
                    DecodeTag.NonCanonicalInt,
                    "non-canonical CBOR argument " + text,
                    null,
                    null,
                    null,
                    text,
                    null,
                    null);
        }

        public static DecodeError negativeMapKey(long key) {
            return new DecodeError(
                    DecodeTag.NegativeMapKey,
                    "negative CBOR map key " + key,
                    key,
                    null,
                    null,
                    null,
                    null,
                    null);
        }

        // A repeated `map<K,V>` key. An integer key is the payload `key`; the payload has
        // no field for a text or bool key, so only the message names one.
        static DecodeError duplicateEntryKey(Object key) {
            if (key instanceof Long n) {
                return duplicateMapKey(n);
            }
            return new DecodeError(
                    DecodeTag.DuplicateMapKey,
                    "duplicate map key " + key,
                    null,
                    null,
                    null,
                    null,
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
    // The value for `key`, or null when the map lacks it: an `optional=MISSING_OK` field.
    public Cbor getOpt(long key) {
        if (kind != MAP) {
            throw DecodeError.wrongType("map");
        }
        for (KV kv : map) {
            if (kv.k == key) {
                return kv.v;
            }
        }
        return null;
    }
    // A `map<K,V>` field: an array of entry maps {1: key, 2: value}. Each entry must
    // hold keys 1 and 2 before either is decoded; `key` and `value` decode an entry's
    // two items, and a repeated key is DuplicateMapKey.
    public static <K, V> Map<K, V> decodeMap(Cbor c, Function<Cbor, K> key, Function<Cbor, V> value) {
        Map<K, V> out = new LinkedHashMap<>();
        for (Cbor entry : c.asArray()) {
            entry.get(1);
            entry.get(2);
            K k = key.apply(entry);
            if (out.containsKey(k)) {
                throw DecodeError.duplicateEntryKey(k);
            }
            out.put(k, value.apply(entry));
        }
        return out;
    }
    // The order of a map<str,V> field's keys: by Unicode code point, which is the order of
    // their UTF-8 bytes. String.compareTo, and so a TreeMap's natural order, compares UTF-16
    // code units, which puts U+10000 (d800 dc00) before U+FFFF.
    public static final Comparator<String> CODE_POINT_ORDER = Cbor::compareCodePoints;
    private static int compareCodePoints(String a, String b) {
        int n = Math.min(a.length(), b.length());
        int i = 0;
        while (i < n) {
            int x = a.codePointAt(i);
            int y = b.codePointAt(i);
            if (x != y) {
                return Integer.compare(x, y);
            }
            i += Character.charCount(x);
        }
        return Integer.compare(a.length(), b.length());
    }
    // A map<str,V> field's entries in the order it encodes them (CODE_POINT_ORDER).
    public static <V> SortedMap<String, V> sortedByCodePoint(Map<String, V> m) {
        SortedMap<String, V> out = new TreeMap<>(CODE_POINT_ORDER);
        out.putAll(m);
        return out;
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
    // The argument's raw bits: `info` itself, or the 1, 2, 4 or 8 bytes after the head.
    private static long readRaw(byte[] d, int[] off, int info) {
        if (info < 24) {
            return info;
        }
        int width;
        if (info == 24) {
            width = 1;
        } else if (info == 25) {
            width = 2;
        } else if (info == 26) {
            width = 4;
        } else if (info == 27) {
            width = 8;
        } else {
            throw DecodeError.unsupportedInfo(info);
        }
        require(d, off[0], width);
        long v = 0;
        for (int j = 0; j < width; j++) {
            v = (v << 8) | u(d, off[0] + j);
        }
        off[0] += width;
        return v;
    }
    // An int, length or count argument. Strict-canonical (D2): an argument that a
    // shorter form could hold is one the canonical encoder never writes. Floats are
    // exempt and use readRaw.
    private static long readArg(byte[] d, int[] off, int info) {
        long v = readRaw(d, off, info);
        boolean fitsShorter = switch (info) {
            case 24 -> v < 24;
            case 25 -> v <= 0xFFL;
            case 26 -> v <= 0xFFFFL;
            case 27 -> Long.compareUnsigned(v, 0xFFFFFFFFL) <= 0;
            default -> false;
        };
        if (fitsShorter) {
            throw DecodeError.nonCanonicalInt(v);
        }
        return v;
    }
    // A byte or text length: beyond the remaining bytes is Truncated, whatever its size.
    private static int readLength(byte[] d, int[] off, int info) {
        long n = readArg(d, off, info);
        if (Long.compareUnsigned(n, d.length - off[0]) > 0) {
            throw DecodeError.truncated();
        }
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
    // One item, left to right: its head, then its body; the first failing check wins.
    private static Cbor dec(byte[] d, int[] off) {
        int initial = u(d, off[0]);
        off[0]++;
        int major = initial >> 5, info = initial & 0x1f;
        switch (major) {
            case 0 -> {
                long n = readArg(d, off, info);
                if (n < 0) {
                    throw DecodeError.intOverflow(Long.toUnsignedString(n));
                }
                return int_(n);
            }
            case 1 -> {
                long n = readArg(d, off, info);
                if (n < 0) {
                    throw DecodeError.intOverflow("-" + unsignedStringPlusOne(n));
                }
                return int_(-1 - n);
            }
            case 2 -> {
                int n = readLength(d, off, info);
                byte[] bb = new byte[n];
                System.arraycopy(d, off[0], bb, 0, n);
                off[0] += n;
                return bytes(bb);
            }
            case 3 -> {
                int n = readLength(d, off, info);
                String s = decodeUtf8(d, off[0], n);
                off[0] += n;
                return text(s);
            }
            case 4 -> {
                // Items are read in order. Each takes at least one byte, so a count
                // beyond the input ends in the error of the first item that fails.
                long n = readArg(d, off, info);
                List<Cbor> a = new ArrayList<>();
                for (long j = 0; Long.compareUnsigned(j, n) < 0; j++) {
                    a.add(dec(d, off));
                }
                return arr(a);
            }
            case 5 -> {
                long n = readArg(d, off, info);
                List<KV> m = new ArrayList<>();
                Set<Long> seen = new HashSet<>();
                for (long j = 0; Long.compareUnsigned(j, n) < 0; j++) {
                    // The key first: its item, then NonIntegerMapKey, NegativeMapKey and
                    // DuplicateMapKey, and only then the value.
                    Cbor k = dec(d, off);
                    if (k.kind != INT) {
                        throw DecodeError.nonIntegerMapKey();
                    }
                    if (k.i < 0) {
                        throw DecodeError.negativeMapKey(k.i);
                    }
                    if (!seen.add(k.i)) {
                        throw DecodeError.duplicateMapKey(k.i);
                    }
                    Cbor v = dec(d, off);
                    m.add(new KV(k.i, v));
                }
                return map(m);
            }
            case 7 -> {
                if (info == 20) {
                    return bool(false);
                }
                if (info == 21) {
                    return bool(true);
                }
                if (info == 22) {
                    return NUL;
                }
                if (info == 25) {
                    return float_(halfToDouble((int) readRaw(d, off, info)));
                }
                if (info == 26) {
                    return float_((double) Float.intBitsToFloat((int) readRaw(d, off, info)));
                }
                if (info == 27) {
                    return float_(Double.longBitsToDouble(readRaw(d, off, info)));
                }
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
