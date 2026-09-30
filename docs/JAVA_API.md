# taut — Java API

> Using taut-generated **Java** code: native types, the deterministic-CBOR wire,
> forward-compatibility, and side-channel extensions. Authoring an IR is in
> [Reference.md](Reference.md); serving a service is in [Server.md](Server.md).

Generated Java is plain classes over a vendored, dependency-free CBOR runtime. Every
language reproduces the *same bytes* — the conformance corpus proves it.

## 1. Generate

```sh
tautc gen <ir> --lang java --with-runtime -o <out>
```

Writes, into `<out>/java/`:

| file | what |
| --- | --- |
| `api.java` | native types (`enum`/`class`) + `toCbor`/`fromCbor`, and per message its bounds and `decode` |
| `Cbor.java` | the deterministic-CBOR runtime (`Cbor`, `encode`, `decode`, `Cbor.DecodeError`) |
| `Ext.java` | extension accessors (`extSet`/`extGet`/`extClear`) |
| `client.java` / `server.java` | typed stubs over a transport (see [Server.md](Server.md)) |

Everything is `package taut`: generated classes are package-private into a single
`api.java`, so they resolve `Cbor` / `KV` / `Ext` directly — drop the files into the
`taut` package and `javac` them together. No third-party jars.

## 2. Native types

Enums carry an integer wire value; the names are a projection:

```java
enum TaskState { OPEN(0), DOING(1), DONE(2);
    final long wire;                                   // OPEN=0, DOING=1, DONE=2
    static TaskState fromWire(long v);                 // UnknownEnum for any other value
}
```

Messages are classes (mutable public fields) with `toCbor` / `fromCbor`, and a decode
from bytes, `decode`, under the message's bounds:

```java
class User { public long id; public String name;
    static final int MAX_DEPTH = 32;                 // User's effective max_depth
    static final Integer MAX_ENCODED_LEN = null;     // its effective max_encoded_len; null for none
    Cbor toCbor();                   // Cbor.map([KV(1, ..), KV(2, ..)])
    static User fromCbor(Cbor c);    // c.get(1).asInt(), c.get(2).asText()
    static User decode(byte[] b);    // bytes -> User, under both bounds
}
```

The two constants are the schema's `max_depth` and `max_encoded_len` options as they
resolve for the message when the code is generated: the message's own, else the file's,
else the defaults, depth 32 and no length bound. The codec itself is a class beside the
message, `User$Codec`, which `toCbor`, `fromCbor` and `decode` call, so a field may take
any name, `m` or `java` included.

Field mapping: `INT → long`, `STR → String`, `BYTES → byte[]`, `BOOL → boolean`,
`FLOAT → double`, `List(T) → java.util.List<T>`, `Map(K,V) → java.util.Map<K,V>`.
**Optional** fields take the boxed/reference type (`Long`, `Double`, `String`, the
message class) and encode as CBOR `null` when `null`. **Transient** fields are in
the class but never on the wire (left at the Java default on decode).

## 3. Encode / decode

A message ↔ CBOR bytes goes through the generated `toCbor` plus the runtime `encode`
(`static` on `Cbor`), and back through the generated `decode`:

```java
byte[] bytes = Cbor.encode(task.toCbor());   // serialize
Task task = Task.decode(bytes);              // deserialize, under Task's bounds
```

`Task.decode` is the runtime's `Cbor.decode` under `Task.MAX_DEPTH` and
`Task.MAX_ENCODED_LEN`, then `Task.fromCbor`. The call's root decides its bounds: a
message nested inside a `Task` does not change them. The two steps can also be taken by
hand, `Task.fromCbor(Cbor.decode(bytes))`, but `Cbor.decode(bytes)` applies only the
defaults (depth 32, no length bound), not the schema's.

Every decode entry point returns a value or throws `Cbor.DecodeError`, nothing else, and
no input exhausts the stack.

## 4. The `Cbor` runtime (`Cbor.java`)

A tiny frozen subset of RFC 8949 in core deterministic encoding (definite lengths,
shortest-form ints, ascending map keys, shortest-form floats). Hand-rolled, JDK only.

```java
public final class Cbor {
    public static final int INT=0, BYTES=1, TEXT=2, ARR=3, MAP=4, BOOL=5, NULL=6, FLOAT=7;
    public static final int DEFAULT_MAX_DEPTH = 32;     // the depth bound where none is given
    public static final int MAX_DEPTH_CEILING = 128;    // no decode applies a deeper bound
    public final int kind;                              // one of the above
    public final long i; public final double d;         // typed payload, by kind
    public final String s; public final byte[] b;
    public final List<Cbor> arr; public final List<KV> map;

    public static Cbor int_(long n);   public static Cbor float_(double v);
    public static Cbor text(String s); public static Cbor bytes(byte[] b);
    public static Cbor bool(boolean x);
    public static Cbor arr(List<Cbor> a);  public static Cbor map(List<KV> m);
    public static final Cbor NUL;

    public static byte[] encode(Cbor c);
    public static Cbor decode(byte[] data);                                  // the defaults
    public static Cbor decode(byte[] data, int maxDepth, Integer maxEncodedLen);
}
```

Decode is bounded. An array or map has depth one more than the arrays and maps around
it, so a top-level one has depth 1; at a bound of 32, 32 nested containers decode and
the 33rd is `TooDeep` with `limit` 32, refused once its head is read, before any of its
items. A `maxDepth` above `MAX_DEPTH_CEILING` applies the ceiling, and `limit` names the
bound applied; with a non-null `maxEncodedLen`, longer input is `TooLarge` (`len`,
`limit`) before a byte is read. A `maxDepth` below 1 or a negative `maxEncodedLen` is the
caller's error, `IllegalArgumentException`, not a `DecodeError`.

Typed accessors, each throwing `Cbor.DecodeError` (`WrongType`) on the wrong kind:
`.asInt()`, `.asFloat()`, `.asText()`, `.asBytes()`, `.asBool()`, `.asArray()`,
`.mapEntries()`; `.get(tag)` (map value by tag, `MissingKey` if absent), `.getOpt(tag)`
(null if absent); and `.isNull()`. A map is a `List<KV>` where `KV { long k; Cbor v; }`
is package-private — which is why `Ext` and consumers live in `package taut`.

`Cbor.DecodeError` is a `RuntimeException` whose `tag` is a `Cbor.DecodeTag`:
`Truncated`, `TrailingBytes`, `InvalidUtf8`, `UnsupportedInfo`, `UnsupportedMajor`,
`NonCanonicalInt`, `IntOverflow`, `NonIntegerMapKey`, `NegativeMapKey`,
`DuplicateMapKey`, `MissingKey`, `WrongType`, `UnknownEnum`, `TooDeep` or `TooLarge`.
The payload is in the fields that tag names: `info`, `major`, `key`, `expected`,
`enumName`, `value`, `len` and `limit`. `key` is the key as text: an int in decimal, a
str as itself, a bool as `true` or `false`. The full table is in
[CodecContract.md](CodecContract.md).

## 5. Forward-compatibility (unknown-field preservation)

Generate with `--forward-compat` and each class gains
`public java.util.List<KV> wireResidual`. On `fromCbor`, tags the class doesn't name
are captured there; on `toCbor`, they're added back and **merged with the known fields
in one ascending-tag order** (`Cbor.encode` sorts map keys) — so a node that
*decodes → edits → re-encodes* a newer message never drops fields it doesn't
understand. A message with no unknowns is byte-identical with or without the flag.
Without it, `fromCbor` accepts unknown fields and drops them; the parity gate runs both
builds (`java` and `java/fc`).

A schema that declares an extension **requires** `--forward-compat` (build error
otherwise — extensions ride the residual space).

## 6. Extensions (side-channels) — `Ext.java`

Attach / read / clear a declared extension on *any* host message's wire bytes,
knowing only the extension's schema (never the host's). Tags live in the band ≥ `2^20`:

```java
public static byte[] extSet(byte[] host, long tag, Cbor value);  // attach / replace
public static Cbor   extGet(byte[] host, long tag);              // null if absent
public static byte[] extClear(byte[] host, long tag);            // strip
```

`value` is the generated extension message's `toCbor()`; decode `extGet`'s result
with `ExtMsg.fromCbor()`:

```java
byte[] raw = Ext.extSet(host, 0x100001, decision.toCbor());
Cbor c = Ext.extGet(raw, 0x100001);
Decision decision = c == null ? null : Decision.fromCbor(c);
raw = Ext.extClear(raw, 0x100001);
```

They fail closed: for any host bytes each returns or throws `Cbor.DecodeError`, and a
host that is not a map is `WrongType` (`map`). Not knowing the host's schema, they read a
host at the depth ceiling, 128, with no length bound, the only bounds every valid host
meets; the host's own reader applies the host's. A below-band `tag` is the caller's
error, `IllegalArgumentException`, thrown before the host is read. The host app decodes
its own message obliviously — the extension rides in `wireResidual` and survives.

## 7. Consuming the runtime

`Cbor.java` / `Ext.java` are vendored, dependency-free source — drop them into the
`taut` package next to `api.java` and `javac` the lot. The JDK is the only toolchain.
The bytes match every other taut target.

## 8. Changed in v0.10.0

Nothing is removed. What changes:
- `Cbor.decode(data)` applies depth 32, and `Cbor.decode(data, maxDepth, maxEncodedLen)`
  takes the caller's bounds. Input nested deeper than its bound, into which v0.9 recursed
  without limit, is `TooDeep`.
- `DecodeTag` gains `NonCanonicalInt`, `NegativeMapKey`, `TooDeep` and `TooLarge`, so an
  exhaustive `switch` needs four more cases; `DecodeError.key` is a `String`, not a
  `Long`, and `len` and `limit` are new.
- `Ext.extSet`, `extGet` and `extClear` throw `Cbor.DecodeError` for a host that is not a
  map, where v0.9 threw `IllegalArgumentException`.
- New: each message's `MAX_DEPTH`, `MAX_ENCODED_LEN` and `decode`, and its codec class
  `<Message>$Codec`; `DEFAULT_MAX_DEPTH`, `MAX_DEPTH_CEILING`, `getOpt` and `decodeMap`.
