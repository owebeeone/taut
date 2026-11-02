# taut — Swift API

> Using taut-generated **Swift** code: native types, the deterministic-CBOR wire,
> forward-compatibility, and side-channel extensions. Authoring an IR is in
> [Reference.md](Reference.md); serving a service is in [Server.md](Server.md).

Generated Swift is plain types over a vendored, dependency-free CBOR runtime. Every
language reproduces the *same bytes* — the conformance corpus proves it.

## 1. Generate

```sh
tautc gen <ir> --lang swift --with-runtime -o <out>
```

Writes, into `<out>/swift/`:

| file | what |
| --- | --- |
| `api.swift` | native types, codecs, bounds, mandatory descriptors and optional validation methods |
| `cbor.swift` | the deterministic-CBOR runtime (`Cbor`, `encode`, `tryDecode`, `CborError`) |
| `ext.swift` | extension accessors (`extSet`/`extGet`/`extClear`) |
| `paths.swift` / `descriptors.swift` | immutable metadata, paths and typed adapters |
| `reports.swift` / `validation.swift` | shared reports/engine, only with `--with-validation` |
| `client.swift` / `server.swift` | typed stubs over a transport (see [Server.md](Server.md)) |

`--with-runtime` is the alias for `--runtime source`. Build the runtime sources
once as the shared `TautFoundation` module; generated APIs import that owner.
Without either runtime option, legacy supplied mode emits no runtime or import:
compile the canonical runtime once in the application module alongside schemas.
Explicit `module` bindings also support an imported supplied owner. Package mode
requires a real application-supplied module binding; it never installs a package.
See [the executable build examples](../dev-docs/examples/swift-oneof/README.md)
for complete module, link, package and flat supplied commands.

## 2. Native types

Enums are raw-`Int64`; the case names are a projection of the wire value:

```swift
public enum TaskState: Int64 { case `open` = 0; case doing = 1; case done = 2 }
// .rawValue gives the wire int; TaskState.fromCbor(c) maps back, and throws
// CborError.unknownEnum for any other value
```

Ordinary messages are structs with `toCbor` / `fromCbor`, and a decode from bytes,
`decode`, under the message's bounds:

```swift
public struct User { public var id: Int64; public var name: String }
// user.toCbor()                  -> Cbor.map([(1, ..), (2, ..)])
// try User.fromCbor(c)           -> c.tryGet(1).tryInt(), c.tryGet(2).tryText()
// User.maxDepth: Int = 32        -- User's effective max_depth
// User.maxEncodedLen: Int? = nil -- its effective max_encoded_len; nil for none
// try User.decode(bytes)         -> bytes -> User, under both bounds
```

The two constants are the schema's `max_depth` and `max_encoded_len` options as they
resolve for the message when the code is generated: the message's own, else the file's,
else the defaults, depth 32 and no length bound.

Field mapping: `INT → Int64`, `STR → String`, `BYTES → [UInt8]`, `BOOL → Bool`,
`FLOAT → Double`, `List(T) → [T]`, `Map(K,V) → [K: V]`. **Optional** fields are
`T?` (encoded as CBOR `null` when `nil`). **Transient** fields are in the struct
but never on the wire. A generated `public init(…)` keeps values constructible
cross-module.

Only direct recursive stored-message components become `final class`, because
Swift cannot store an optional self/mutually recursive struct inline. Ordinary
and collection-indirect recursive records retain value semantics. No message
base/protocol or per-field wrapper is introduced; required initializer arguments
remain required. Reference cycles are explicit validation issues.

## 3. Encode / decode

A message ↔ CBOR bytes goes through the generated `toCbor` plus the runtime `encode`,
and back through the generated `decode`:

```swift
import TautFoundation  // for explicitly shared module modes
let bytes: [UInt8] = encode(task.toCbor())   // serialize
let task = try Task.decode(bytes)            // deserialize, under Task's bounds
```

`Task.decode` is the runtime's `Cbor.tryDecode` under `Task.maxDepth` and
`Task.maxEncodedLen`, then `Task.fromCbor`. The call's root decides its bounds: a message
nested inside a `Task` does not change them. The two steps can also be taken by hand,
`try tryDecode(bytes)` then `try Task.fromCbor(c)`, but `tryDecode` without bounds applies
only the defaults (depth 32, no length bound), not the schema's.

Every decode entry point returns a value or throws `CborError`; nothing traps, and no
input exhausts the stack.

## 4. The `Cbor` runtime (`cbor.swift`)

A tiny frozen subset of RFC 8949 in core deterministic encoding (definite lengths,
shortest-form ints, ascending map keys, shortest-form floats). Hand-rolled, zero deps.

```swift
public indirect enum Cbor {
    case int(Int64); case float(Double); case bytes([UInt8]); case text(String)
    case array([Cbor]); case map([(Int64, Cbor)]); case bool(Bool); case null
}

public let defaultMaxDepth: Int = 32    // the depth bound where none is given
public let maxDepthCeiling: Int = 128   // no decode applies a deeper bound

public func encode(_ v: Cbor) -> [UInt8]
public func tryDecode(_ data: [UInt8], maxDepth: Int = defaultMaxDepth,
                      maxEncodedLen: Int? = nil) throws -> Cbor   // also Cbor.tryDecode
```

Decode is bounded. An array or map has depth one more than the arrays and maps around
it, so a top-level one has depth 1; at a bound of 32, 32 nested containers decode and
the 33rd is `tooDeep(limit: 32)`, refused once its head is read, before any of its items.
A `maxDepth` above `maxDepthCeiling` applies the ceiling, and `limit` names the bound
applied; with a `maxEncodedLen`, longer input is `tooLarge(len:limit:)` before a byte is
read. A `maxDepth` below 1 or a negative `maxEncodedLen` is the caller's error, not the
input's, and traps.

Accessors, each throwing `CborError`: `.tryInt()`, `.tryFloat()`, `.tryText()`,
`.tryBytes()`, `.tryBool()`, `.tryArray()` (`wrongType` otherwise), `.tryGet(tag)` (map
value by tag, `missingKey` if absent), `.tryGetOpt(tag)` (nil if absent) and
`.tryDictionary(key:value:)` (a `Map(K,V)` field). `.isNull` and `.mapEntries` (empty
if not a map) do not throw. Float narrowing uses native `Float16`.

`CborError` is `Equatable`, one case per tag: `truncated`, `trailingBytes`, `invalidUtf8`,
`unsupportedInfo(UInt8)`, `unsupportedMajor(UInt8)`, `nonCanonicalInt(UInt64)`,
`intOverflow(String)`, `nonIntegerMapKey`, `negativeMapKey(Int64)`,
`duplicateMapKey(String)`, `missingKey(Int64)`, `wrongType(String)`,
`unknownEnum(String, Int64)`, `tooDeep(limit:)` and `tooLarge(len:limit:)`.
`.parityTag` is the tag every taut language reports (`"TooDeep"`, ...).
`duplicateMapKey` holds the key as text: an int in decimal, a str as itself, a bool as
`true` or `false`. The full table is in [CodecContract.md](CodecContract.md).

## 5. Forward-compatibility (unknown-field preservation)

Generate with `--forward-compat` and each message gains
`public var wire_residual: [(Int64, Cbor)]`. On `fromCbor`, tags the message doesn't
name are captured there; on `toCbor`, they're appended and `encode` sorts every key
ascending — so a node that *decodes → edits → re-encodes* a newer message never
drops fields it doesn't understand. (Swift's `encode` sorts keys, so the residual
just rides along — no explicit merge.) A message with no unknowns is byte-identical
with or without the flag. Without it, `fromCbor` accepts unknown fields and drops
them; the parity gate runs both builds (`swift` and `swift/fc`).

A schema that declares an extension **requires** `--forward-compat` (extensions ride
the residual space).

## 6. Extensions (side-channels) — `ext.swift`

Attach / read / clear a declared extension on *any* host message's wire bytes,
knowing only the extension's schema (never the host's). Tags live in the band ≥ `1 << 20`:

```swift
public func extSet(_ host: [UInt8], tag: Int64, value: Cbor) throws -> [UInt8]  // attach / replace
public func extGet(_ host: [UInt8], tag: Int64) throws -> Cbor?                 // nil if absent
public func extClear(_ host: [UInt8], tag: Int64) throws -> [UInt8]            // strip
```

`value` is the generated extension message's `toCbor()`; decode `extGet`'s result
with `ExtMsg.fromCbor()`:

```swift
let raw = try extSet(host, tag: 0x100001, value: decision.toCbor())
let decision = try extGet(raw, tag: 0x100001).map { try Decision.fromCbor($0) }
let raw2 = try extClear(raw, tag: 0x100001)
```

They fail closed: for any host bytes each returns or throws `CborError`, and a host that
is not a map is `wrongType("map")`. Not knowing the host's schema, they read a host at
the depth ceiling, 128, with no length bound, the only bounds every valid host meets; the
host's own reader applies the host's. A below-band `tag` is the caller's error and traps
before the host is read. The host app decodes its own message obliviously — the
extension rides in `wire_residual` and survives.

## 7. Consuming the runtime

One canonical source closure supplies codecs, descriptors and optional validation.
It can be compiled once in the default supplied application module, or once in an
explicitly shared imported module for source/package/supplied bindings. Every
schema must use that same actual owner for codec, descriptor and report types.
Applications need Swift and its standard libraries; no Taut compiler or schema
loader participates in their build/runtime. Package selection performs no install,
discovery or fallback. Native types from separately generated disabled children
are reused through explicit external mappings and mandatory typed metadata.

When several `api.swift` files share one application module, give the build inputs
distinct basenames using byte-identical copies; Swift rejects duplicate basenames.
The [Swift example](../dev-docs/examples/swift-oneof/README.md) includes those exact
commands, output ownership rules and independently compiled child bindings.

Every message publishes `static let descriptor` and `static var schemaDescriptor`
with complete immutable fields/types/enums/options/reservations/constraints.
`--with-validation` adds `validate(recursive: Bool = true) -> ValidationReport`
and `isValid(recursive: Bool = true) -> Bool` to every message. Both call one shared
engine. Reports own their paths and collections; `isValid` and `isComplete` are
computed properties. Virtual selection contributes a deferred check, making a
report incomplete and the Boolean false. Local scope checks only the root;
recursive scope traverses every populated owned child. Drafts remain mutable and
serialize populated payloads without implicit validation or repair.

## 8. Changed in v0.10.0

- `decode(_:)` and the accessors that trapped through `fatalError` (`get`, `intVal`,
  `floatVal`, `textVal`, `bytesVal`, `boolVal`, `arrayVal`) are gone: use `tryDecode` or
  a message's `decode`, and the `try*` accessors. The free `decodeDictionary` is now the
  member `tryDictionary`.
- `extSet`, `extGet` and `extClear` throw `CborError`; a host that is not a map trapped
  and is `wrongType("map")`.
- `CborError` gains `tooDeep`, `tooLarge`, `nonCanonicalInt` and `negativeMapKey`, so an
  exhaustive `switch` needs four more cases; `duplicateMapKey` holds a `String`, not an
  `Int64`.
- New: each message's `maxDepth`, `maxEncodedLen` and `decode(_:)`; `tryDecode`'s
  `maxDepth:` and `maxEncodedLen:`, `Cbor.tryDecode`, `defaultMaxDepth`,
  `maxDepthCeiling` and `tryGetOpt`.
