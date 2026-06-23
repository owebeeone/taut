# taut — Java API

> Using taut-generated **Java** code: native types, the deterministic-CBOR wire,
> forward-compatibility, and side-channel extensions. Authoring an IR is in
> [Reference.md](Reference.md); serving a service is in [Server.md](Server.md).

Generated Java is plain classes over a vendored, dependency-free CBOR runtime. Every
language reproduces the *same bytes* — the conformance corpus proves it.

## 1. Generate

```sh
tautc gen --lang java --with-runtime -o <out>
```

Writes, into `<out>/java/`:

| file | what |
| --- | --- |
| `api.java` | native types (`enum`/`class`) + `toCbor`/`fromCbor` |
| `Cbor.java` | the deterministic-CBOR runtime (`Cbor`, `encode`, `decode`) |
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
    static TaskState fromWire(long v);                 // throws on an unknown value
}
```

Messages are classes (mutable public fields) with `toCbor` / `fromCbor`:

```java
class User { public long id; public String name;
    Cbor toCbor();                  // Cbor.map([KV(1, ..), KV(2, ..)])
    static User fromCbor(Cbor c);   // c.get(1).i, c.get(2).s
}
```

Field mapping: `INT → long`, `STR → String`, `BYTES → byte[]`, `BOOL → boolean`,
`FLOAT → double`, `List(T) → java.util.List<T>`, `Map(K,V) → java.util.Map<K,V>`.
**Optional** fields take the boxed/reference type (`Long`, `Double`, `String`, the
message class) and encode as CBOR `null` when `null`. **Transient** fields are in
the class but never on the wire (left at the Java default on decode).

## 3. Encode / decode

A message ↔ CBOR bytes goes through the generated `toCbor`/`fromCbor` plus the
runtime `encode`/`decode` (both `static` on `Cbor`):

```java
byte[] bytes = Cbor.encode(task.toCbor());      // serialize
Task task = Task.fromCbor(Cbor.decode(bytes));  // deserialize
```

## 4. The `Cbor` runtime (`Cbor.java`)

A tiny frozen subset of RFC 8949 in core deterministic encoding (definite lengths,
shortest-form ints, ascending map keys, shortest-form floats). Hand-rolled, JDK only.

```java
public final class Cbor {
    public static final int INT=0, BYTES=1, TEXT=2, ARR=3, MAP=4, BOOL=5, NULL=6, FLOAT=7;
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
    public static Cbor decode(byte[] data);
}
```

Read the payload directly off the public fields by `kind` (`.i`, `.s`, `.b`, `.d`,
`.arr`). Map helpers: `.get(tag)` (map value by tag, throws if absent),
`.mapEntries()` (entries, or empty), `.isNull()`. A map is a `List<KV>` where
`KV { long k; Cbor v; }` is package-private — which is why `Ext` and consumers live
in `package taut`.

## 5. Forward-compatibility (unknown-field preservation)

Generate with `--forward-compat` and each class gains
`public java.util.List<KV> wireResidual`. On `fromCbor`, tags the class doesn't name
are captured there; on `toCbor`, they're added back and **merged with the known fields
in one ascending-tag order** (`Cbor.encode` sorts map keys) — so a node that
*decodes → edits → re-encodes* a newer message never drops fields it doesn't
understand. A message with no unknowns is byte-identical with or without the flag.

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

A below-band `tag` throws `IllegalArgumentException`; a non-map host throws too. The
host app decodes its own message obliviously — the extension rides in `wireResidual`
and survives.

## 7. Consuming the runtime

`Cbor.java` / `Ext.java` are vendored, dependency-free source — drop them into the
`taut` package next to `api.java` and `javac` the lot. The JDK is the only toolchain.
The bytes match every other taut target.
