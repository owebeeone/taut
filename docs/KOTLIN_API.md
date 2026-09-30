# taut — Kotlin API

> Using taut-generated **Kotlin** code: native types, the deterministic-CBOR wire,
> forward-compatibility, and side-channel extensions. Authoring an IR is in
> [Reference.md](Reference.md); serving a service is in [Server.md](Server.md).

Generated Kotlin is plain `data class`es over a vendored, dependency-free CBOR runtime.
Every language reproduces the *same bytes* — the conformance corpus proves it.

## 1. Generate

```sh
tautc gen <ir> --lang kotlin --with-runtime -o <out>
```

Writes, into `<out>/kotlin/`:

| file | what |
| --- | --- |
| `api.kt` | native types (`enum class`/`data class`) + `toCbor`/`fromCbor`, and per message its bounds and `decode` |
| `cbor.kt` | the deterministic-CBOR runtime (`Cbor`, `encode`, `decode`, `DecodeError`) |
| `ext.kt` | extension accessors (`extSet`/`extGet`/`extClear`) |
| `client.kt` / `server.kt` | typed stubs over a transport (see [Server.md](Server.md)) |

Every file is `package taut`, so generated code resolves `Cbor` / `extSet` with no
imports — drop them in the same package. JDK stdlib only; no third-party deps.

## 2. Native types

Enums carry an integer wire value; the names are a projection:

```kotlin
enum class TaskState(val wire: Long) { open(0), doing(1), done(2);
    companion object { fun fromWire(v: Long): TaskState }  // DecodeError.UnknownEnum otherwise
}
```

Messages are `data class`es (mutable `var`, default `equals`/`copy`) with
`toCbor` / `fromCbor`, and a decode from bytes, `decode`, under the message's bounds:

```kotlin
data class User(var id: Long, var name: String) {
    fun toCbor(): Cbor                          // Cbor.map([(1, ..), (2, ..)])
    companion object {
        const val MAX_DEPTH: Int = 32           // User's effective max_depth
        val MAX_ENCODED_LEN: Int? = null        // its effective max_encoded_len; null for none
        fun decode(bytes: ByteArray): User      // bytes -> User, under both bounds
        fun fromCbor(c: Cbor): User             // c.get(1).intVal, c.get(2).textVal
    }
}
```

The two constants are the schema's `max_depth` and `max_encoded_len` options as they
resolve for the message when the code is generated: the message's own, else the file's,
else the defaults, depth 32 and no length bound.

Field mapping: `INT → Long`, `STR → String`, `BYTES → ByteArray`, `BOOL → Boolean`,
`FLOAT → Double`, `List(T) → List<T>`, `Map(K,V) → Map<K,V>`. **Optional** fields
are nullable `T?` (encoded as CBOR `null` when `null`). **Transient** fields are in
the class but never on the wire.

## 3. Encode / decode

A message ↔ CBOR bytes goes through the generated `toCbor` plus the runtime `encode`,
and back through the generated `decode`:

```kotlin
val bytes: ByteArray = encode(task.toCbor())   // serialize
val task = Task.decode(bytes)                  // deserialize, under Task's bounds
```

`Task.decode` is the runtime's `decode` under `Task.MAX_DEPTH` and `Task.MAX_ENCODED_LEN`,
then `Task.fromCbor`. The call's root decides its bounds: a message nested inside a
`Task` does not change them. The two steps can also be taken by hand,
`Task.fromCbor(decode(bytes))`, but `decode` without bounds applies only the defaults
(depth 32, no length bound), not the schema's.

Every decode entry point returns a value or throws `DecodeError`, nothing else, and no
input exhausts the stack.

## 4. The `Cbor` runtime (`cbor.kt`)

A tiny frozen subset of RFC 8949 in core deterministic encoding (definite lengths,
shortest-form ints, ascending map keys, shortest-form floats). Hand-rolled, zero deps.

```kotlin
class Cbor(val kind: Int, val i: Long, val s: String, val b: ByteArray,
           val arr: List<Cbor>, val map: List<Pair<Long, Cbor>>, val f: Double) {
    companion object {
        const val INT = 0; const val BYTES = 1; const val TEXT = 2; const val ARR = 3
        const val MAP = 4; const val BOOL = 5; const val NULL = 6; const val FLOAT = 7
        fun int(n: Long): Cbor;   fun text(s: String): Cbor;  fun bytes(b: ByteArray): Cbor
        fun bool(x: Boolean): Cbor; fun float(x: Double): Cbor
        fun arr(a: List<Cbor>): Cbor; fun map(m: List<Pair<Long, Cbor>>): Cbor; val nul: Cbor
    }
}

const val DEFAULT_MAX_DEPTH: Int = 32   // the depth bound where none is given
const val MAX_DEPTH_CEILING: Int = 128  // no decode applies a deeper bound

fun encode(c: Cbor): ByteArray
fun decode(data: ByteArray, maxDepth: Int = DEFAULT_MAX_DEPTH, maxEncodedLen: Int? = null): Cbor
```

Decode is bounded. An array or map has depth one more than the arrays and maps around
it, so a top-level one has depth 1; at a bound of 32, 32 nested containers decode and
the 33rd is `DecodeError.TooDeep` with `limit` 32, refused once its head is read, before
any of its items. A `maxDepth` above `MAX_DEPTH_CEILING` applies the ceiling, and
`limit` names the bound applied; with a `maxEncodedLen`, longer input is
`DecodeError.TooLarge` (`len`, `limit`) before a byte is read. A `maxDepth` below 1 or a
negative `maxEncodedLen` is the caller's error, `IllegalArgumentException`, not a
`DecodeError`.

Build with the companion factories; read with the typed accessors, each throwing
`DecodeError.WrongType` on the wrong kind: `.intVal`, `.textVal`, `.bytesVal`,
`.boolVal`, `.floatVal`, `.arrVal`, `.mapEntries`; `.get(key)` (map value by tag,
`MissingKey` if absent), `.getOrNull(key)` (null if absent); and `.isNull`.

`DecodeError` is a sealed `RuntimeException`, one subclass per tag: `Truncated`,
`TrailingBytes`, `InvalidUtf8`, `UnsupportedInfo(info)`, `UnsupportedMajor(major)`,
`NonCanonicalInt(value)`, `IntOverflow(value)`, `NonIntegerMapKey`, `NegativeMapKey(key)`,
`DuplicateMapKey(key)`, `MissingKey(key)`, `WrongType(expected)`,
`UnknownEnum(enumName, value)`, `TooDeep(limit)` and `TooLarge(len, limit)`.
`DuplicateMapKey.key` is the repeated key, a `Long`, `String` or `Boolean`, whose text is
the payload: an int in decimal, a str as itself, a bool as `true` or `false`. The full
table is in [CodecContract.md](CodecContract.md).

## 5. Forward-compatibility (unknown-field preservation)

Generate with `--forward-compat` and each `data class` gains
`var wireResidual: List<Pair<Long, Cbor>>`. On `fromCbor`, tags the class doesn't name
are captured there; on `toCbor`, they're appended (`Cbor.map(known + wireResidual)`)
and `encode` sorts every map key — so the residual just **rides along in ascending-tag
order**, and a node that *decodes → edits → re-encodes* a newer message never drops
fields it doesn't understand. A message with no unknowns is byte-identical with or
without the flag. Without it, `fromCbor` accepts unknown fields and drops them; the
parity gate runs both builds (`kotlin` and `kotlin/fc`).

A schema that declares an extension **requires** `--forward-compat` (build error
otherwise — extensions ride the residual space).

## 6. Extensions (side-channels) — `ext.kt`

Attach / read / clear a declared extension on *any* host message's wire bytes,
knowing only the extension's schema (never the host's). Tags live in the band ≥ `1L shl 20`:

```kotlin
fun extSet(host: ByteArray, tag: Long, value: Cbor): ByteArray  // attach / replace
fun extGet(host: ByteArray, tag: Long): Cbor?                   // null if absent
fun extClear(host: ByteArray, tag: Long): ByteArray            // strip
```

`value` is the generated extension message's `toCbor()`; decode `extGet`'s result
with `ExtMsg.fromCbor()`:

```kotlin
val raw = extSet(host, 0x100001, decision.toCbor())
val decision = extGet(raw, 0x100001)?.let { Decision.fromCbor(it) }
val stripped = extClear(raw, 0x100001)
```

They fail closed: for any host bytes each returns or throws `DecodeError`, and a host
that is not a map is `DecodeError.WrongType("map")`. Not knowing the host's schema, they
read a host at the depth ceiling, 128, with no length bound, the only bounds every valid
host meets; the host's own reader applies the host's. A below-band `tag` is the caller's
error, `IllegalArgumentException` (`require`), thrown before the host is read. The host
app decodes its own message obliviously — the extension rides in `wireResidual` and
survives.

## 7. Consuming the runtime

`cbor.kt` / `ext.kt` are vendored, dependency-free source — drop them into the module
under `package taut`; `api.kt` shares the package, so `Cbor` resolves with no import.
The JDK stdlib is the only toolchain. The bytes match every other taut target.

## 8. Changed in v0.10.0

Nothing is removed. What changes:
- `decode` takes `maxDepth` and `maxEncodedLen`, by default 32 and none. Input nested
  deeper than its bound, into which v0.9 recursed without limit, is `TooDeep`.
- `DecodeError` gains `TooDeep`, `TooLarge`, `NonCanonicalInt` and `NegativeMapKey`, so an
  exhaustive `when` needs four more branches; `DuplicateMapKey.key` is `Any`, not `Long`.
- `extSet`, `extGet` and `extClear` throw `DecodeError.WrongType("map")` for a host that
  is not a map, where v0.9 threw `IllegalArgumentException`.
- New: each message's `MAX_DEPTH`, `MAX_ENCODED_LEN` and `decode`; `DEFAULT_MAX_DEPTH`,
  `MAX_DEPTH_CEILING`, `getOrNull` and `mapFieldVal`.
