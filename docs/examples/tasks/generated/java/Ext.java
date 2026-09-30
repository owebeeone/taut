// Forward-compatible extension accessors for Java targets.
// Operates schema-free on the host's top-level CBOR map.
// Fail-closed (TautCheckedDecode.md CD-E4): for any host bytes each helper returns or
// throws Cbor.DecodeError, and a host that is not a map is WrongType{map}. A tag below
// the band is the caller's error, IllegalArgumentException, checked before the host. A
// host is read at the depth ceiling, with no length bound (TautOptions.md G3).
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
            if (kv.k == tag) {
                return kv.v;
            }
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

    // The host's top-level map, read at the depth ceiling with no length bound
    // (TautOptions.md G3): a helper cannot name the host's root, and these are the only
    // bounds every valid host meets. The host's own bounds are its reader's.
    private static Cbor decodeHostMap(byte[] host) {
        Cbor root = Cbor.decode(host, Cbor.MAX_DEPTH_CEILING, null);
        if (root.kind != Cbor.MAP) {
            throw Cbor.DecodeError.wrongType("map");
        }
        return root;
    }

    private static List<KV> withoutTag(List<KV> entries, long tag) {
        List<KV> out = new ArrayList<>();
        for (KV kv : entries) {
            if (kv.k != tag) {
                out.add(kv);
            }
        }
        return out;
    }
}
