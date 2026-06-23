# taut — Kotlin API

> Using taut-generated **Kotlin** code: native types, the deterministic-CBOR wire,
> forward-compatibility, and side-channel extensions. Authoring an IR is in
> [Reference.md](Reference.md); serving a service is in [Server.md](Server.md).

Generated Kotlin is plain `data class`es over a vendored, dependency-free CBOR runtime.
Every language reproduces the *same bytes* — the conformance corpus proves it.

## 1. Generate

```sh
tautc gen --lang kotlin --with-runtime -o <out>
```

Writes, into `<out>/kotlin/`:

| file | what |
| --- | --- |
| `api.kt` | native types (`enum class`/`data class`) + `toCbor`/`fromCbor` |
| `cbor.kt` | the deterministic-CBOR runtime (`Cbor`, `encode`, `decode`) |
| `ext.kt` | extension accessors (`extSet`/`extGet`/`extClear`) |
| `client.kt` / `server.kt` | typed stubs over a transport (see [Server.md](Server.md)) |

Every file is `package taut`, so generated code resolves `Cbor` / `extSet` with no
imports — drop them in the same package. JDK stdlib only; no third-party deps.

## 2. Native types

Enums carry an integer wire value; the names are a projection:

```kotlin
enum class TaskState(val wire: Long) { open(0), doing(1), done(2);
    companion object { fun fromWire(v: Long): TaskState }  // throws on an unknown value
}
```

Messages are `data class`es (mutable `var`, default `equals`/`copy`) with
`toCbor` / `fromCbor`:

```kotlin
data class User(var id: Long, var name: String) {
    fun toCbor(): Cbor                              // Cbor.map([(1, ..), (2, ..)])
    companion object { fun fromCbor(c: Cbor): User } // c.get(1).intVal, c.get(2).textVal
}
```

Field mapping: `INT → Long`, `STR → String`, `BYTES → ByteArray`, `BOOL → Boolean`,
`FLOAT → Double`, `List(T) → List<T>`, `Map(K,V) → Map<K,V>`. **Optional** fields
are nullable `T?` (encoded as CBOR `null` when `null`). **Transient** fields are in
the class but never on the wire.

## 3. Encode / decode

A message ↔ CBOR bytes goes through the generated `toCbor`/`fromCbor` plus the
runtime `encode`/`decode`:

```kotlin
val bytes: ByteArray = encode(task.toCbor())   // serialize
val task = Task.fromCbor(decode(bytes))        // deserialize
```

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

fun encode(c: Cbor): ByteArray
fun decode(data: ByteArray): Cbor
```

Build with the companion factories; read with the typed accessors:
`.intVal`, `.textVal`, `.bytesVal`, `.boolVal`, `.floatVal`, `.arrVal`,
`.get(key)` (map value by tag), `.mapEntries`, `.isNull`.

## 5. Forward-compatibility (unknown-field preservation)

Generate with `--forward-compat` and each `data class` gains
`var wireResidual: List<Pair<Long, Cbor>>`. On `fromCbor`, tags the class doesn't name
are captured there; on `toCbor`, they're appended (`Cbor.map(known + wireResidual)`)
and `encode` sorts every map key — so the residual just **rides along in ascending-tag
order**, and a node that *decodes → edits → re-encodes* a newer message never drops
fields it doesn't understand. A message with no unknowns is byte-identical with or
without the flag.

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

A below-band `tag` throws (`require`); a non-map host throws. The host app decodes its
own message obliviously — the extension rides in `wireResidual` and survives.

## 7. Consuming the runtime

`cbor.kt` / `ext.kt` are vendored, dependency-free source — drop them into the module
under `package taut`; `api.kt` shares the package, so `Cbor` resolves with no import.
The JDK stdlib is the only toolchain. The bytes match every other taut target.
