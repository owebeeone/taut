// Forward-compatible extension accessors for Java targets.
// Operates schema-free on the host's top-level CBOR map.
package taut;

import java.util.ArrayList;
import java.util.List;

public final class Ext {
    private static final long BAND_START = 1L << 20;

    private Ext() {}

    public static byte[] extSet(byte[] host, long tag, Cbor value) {
        checkTag(tag);
        Cbor root = decodeHostMap(host);
        List<KV> entries = withoutTag(root.map, tag);
        entries.add(new KV(tag, value));
        return Cbor.encode(Cbor.map(entries));
    }

    public static Cbor extGet(byte[] host, long tag) {
        checkTag(tag);
        Cbor root = decodeHostMap(host);
        for (KV kv : root.map) {
            if (kv.k == tag) return kv.v;
        }
        return null;
    }

    public static byte[] extClear(byte[] host, long tag) {
        checkTag(tag);
        Cbor root = decodeHostMap(host);
        return Cbor.encode(Cbor.map(withoutTag(root.map, tag)));
    }

    private static void checkTag(long tag) {
        if (tag < BAND_START) {
            throw new IllegalArgumentException("extension tag below band: " + tag);
        }
    }

    private static Cbor decodeHostMap(byte[] host) {
        Cbor root = Cbor.decode(host);
        if (root.kind != Cbor.MAP) {
            throw new IllegalArgumentException("host root is not a CBOR map");
        }
        return root;
    }

    private static List<KV> withoutTag(List<KV> entries, long tag) {
        List<KV> out = new ArrayList<>();
        for (KV kv : entries) {
            if (kv.k != tag) out.add(kv);
        }
        return out;
    }
}
