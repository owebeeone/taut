# taut — Swift API

> Using taut-generated **Swift** code: native types, the deterministic-CBOR wire,
> forward-compatibility, and side-channel extensions. Authoring an IR is in
> [Reference.md](Reference.md); serving a service is in [Server.md](Server.md).

Generated Swift is plain types over a vendored, dependency-free CBOR runtime. Every
language reproduces the *same bytes* — the conformance corpus proves it.

## 1. Generate

```sh
tautc gen --lang swift --with-runtime -o <out>
```

Writes, into `<out>/swift/`:

| file | what |
| --- | --- |
| `api.swift` | native types (`enum`/`struct`) + `toCbor`/`fromCbor` |
| `cbor.swift` | the deterministic-CBOR runtime (`Cbor`, `encode`, `decode`) |
| `ext.swift` | extension accessors (`extSet`/`extGet`/`extClear`) |
| `client.swift` / `server.swift` | typed stubs over a transport (see [Server.md](Server.md)) |

All files live in one module — `api.swift` refers to `Cbor` directly (no imports).
Compile the lot with `swiftc *.swift`; no third-party packages.

## 2. Native types

Enums are raw-`Int64`; the case names are a projection of the wire value:

```swift
public enum TaskState: Int64 { case `open` = 0; case doing = 1; case done = 2 }
// .rawValue gives the wire int; TaskState(rawValue: v)! maps back (traps on unknown)
```

Messages are structs with `toCbor` / `fromCbor`:

```swift
public struct User { public var id: Int64; public var name: String }
// user.toCbor()         -> Cbor.map([(1, ..), (2, ..)])
// User.fromCbor(c)      -> c.get(1).intVal, c.get(2).textVal
```

Field mapping: `INT → Int64`, `STR → String`, `BYTES → [UInt8]`, `BOOL → Bool`,
`FLOAT → Double`, `List(T) → [T]`, `Map(K,V) → [K: V]`. **Optional** fields are
`T?` (encoded as CBOR `null` when `nil`). **Transient** fields are in the struct
but never on the wire. A generated `public init(…)` keeps values constructible
cross-module.

## 3. Encode / decode

A message ↔ CBOR bytes goes through the generated `toCbor`/`fromCbor` plus the
runtime `encode`/`decode`:

```swift
let bytes: [UInt8] = encode(task.toCbor())   // serialize
let task = Task.fromCbor(decode(bytes))       // deserialize
```

## 4. The `Cbor` runtime (`cbor.swift`)

A tiny frozen subset of RFC 8949 in core deterministic encoding (definite lengths,
shortest-form ints, ascending map keys, shortest-form floats). Hand-rolled, zero deps.

```swift
public indirect enum Cbor {
    case int(Int64); case float(Double); case bytes([UInt8]); case text(String)
    case array([Cbor]); case map([(Int64, Cbor)]); case bool(Bool); case null
}

public func encode(_ v: Cbor) -> [UInt8]
public func decode(_ data: [UInt8]) -> Cbor
```

Accessors (trap on the wrong shape): `.intVal`, `.textVal`, `.bytesVal`,
`.boolVal`, `.floatVal`, `.arrayVal`, `.get(tag)` (map value by tag),
`.mapEntries`, `.isNull`. Float narrowing uses native `Float16`.

## 5. Forward-compatibility (unknown-field preservation)

Generate with `--forward-compat` and each struct gains
`public var wire_residual: [(Int64, Cbor)]`. On `fromCbor`, tags the struct doesn't
name are captured there; on `toCbor`, they're appended and `encode` sorts every key
ascending — so a node that *decodes → edits → re-encodes* a newer message never
drops fields it doesn't understand. (Swift's `encode` sorts keys, so the residual
just rides along — no explicit merge.) A message with no unknowns is byte-identical
with or without the flag.

A schema that declares an extension **requires** `--forward-compat` (extensions ride
the residual space).

## 6. Extensions (side-channels) — `ext.swift`

Attach / read / clear a declared extension on *any* host message's wire bytes,
knowing only the extension's schema (never the host's). Tags live in the band ≥ `1 << 20`:

```swift
public func extSet(_ host: [UInt8], tag: Int64, value: Cbor) -> [UInt8]  // attach / replace
public func extGet(_ host: [UInt8], tag: Int64) -> Cbor?                 // nil if absent
public func extClear(_ host: [UInt8], tag: Int64) -> [UInt8]            // strip
```

`value` is the generated extension message's `toCbor()`; decode `extGet`'s result
with `ExtMsg.fromCbor()`:

```swift
let raw = extSet(host, tag: 0x100001, value: decision.toCbor())
let decision = extGet(raw, tag: 0x100001).map { Decision.fromCbor($0) }
let raw2 = extClear(raw, tag: 0x100001)
```

A below-band `tag` traps; a non-map host traps. The host app decodes its own
message obliviously — the extension rides in `wire_residual` and survives.

## 7. Consuming the runtime

`cbor.swift` / `ext.swift` are vendored, dependency-free source — drop them into the
module alongside `api.swift`, which refers to `Cbor` directly. `swiftc *.swift` is
the only toolchain. The bytes match every other taut target.
