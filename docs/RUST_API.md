# taut — Rust API

> Using taut-generated **Rust** code: native types, the deterministic-CBOR wire,
> forward-compatibility, and side-channel extensions. Authoring an IR is in
> [Reference.md](Reference.md); serving a service is in [Server.md](Server.md).

Generated Rust is plain types over a vendored, dependency-free CBOR runtime. Every
language reproduces the *same bytes* — the conformance corpus proves it.

## 1. Generate

```sh
tautc gen <ir> --lang rust --with-runtime -o <out>
```

Writes, into `<out>/rust/`:

| file | what |
| --- | --- |
| `api.rs` | native types (`enum`/`struct`) + `to_cbor`/`from_cbor`, and per message its bounds and `decode` |
| `cbor.rs` | the deterministic-CBOR runtime (`Cbor`, `encode`, `try_decode`, `try_decode_with`, `DecodeError`) |
| `ext.rs` | extension accessors (`ext_set`/`ext_get`/`ext_clear`) |
| `client.rs` / `server.rs` | typed stubs over a transport (see [Server.md](Server.md)) |

Generated code names the runtime `crate::cbor`, so declare `mod cbor;` at the crate root
beside `mod api;`, and `extern crate alloc;`: the runtime uses `core` and `alloc` only, so
it also builds in a `no_std` crate. No third-party crates.

## 2. Native types

Enums carry an integer wire value; the names are a projection:

```rust
pub enum TaskState { Open, Doing, Done }
impl TaskState {
    pub fn wire(self) -> i64;                               // Open=0, Doing=1, Done=2
    pub fn from_wire(v: i64) -> Result<Self, DecodeError>;  // UnknownEnum for any other value
}
```

Messages are structs with `to_cbor` / `from_cbor`, and a decode from bytes, `decode`,
under the message's bounds:

```rust
pub struct User { pub id: i64, pub name: String }
impl User {
    pub const MAX_DEPTH: usize = 32;                   // User's effective max_depth
    pub const MAX_ENCODED_LEN: Option<usize> = None;   // its effective max_encoded_len
    pub fn to_cbor(&self) -> Cbor;                             // Cbor::Map(vec![(1, ..), (2, ..)])
    pub fn from_cbor(c: &Cbor) -> Result<Self, DecodeError>;   // c.try_get(1)?.try_int()?, ...
    pub fn decode(bytes: &[u8]) -> Result<Self, DecodeError>;  // bytes -> User, under both bounds
}
```

The two constants are the schema's `max_depth` and `max_encoded_len` options as they
resolve for the message when the code is generated: the message's own, else the file's,
else the defaults, depth 32 and no length bound. `api.rs` also has the file's pair as
module-level `MAX_DEPTH` and `MAX_ENCODED_LEN`, for a decode rooted at a type that is not
a message, such as a method's `list<T>` output.

Field mapping: `INT → i64`, `STR → String`, `BYTES → Vec<u8>`, `BOOL → bool`,
`FLOAT → f64`, `List(T) → Vec<T>`, `Map(K,V) → BTreeMap<K,V>`. **Optional** fields
are `Option<T>` (encoded as CBOR `null` when `None`). **Transient** fields are in
the struct but never on the wire.

## 3. Encode / decode

A message ↔ CBOR bytes goes through the generated `to_cbor` plus the runtime `encode`,
and back through the generated `decode`:

```rust
use crate::cbor::encode;

let bytes: Vec<u8> = encode(&task.to_cbor());   // serialize
let task = Task::decode(&bytes)?;               // deserialize, under Task's bounds
```

`Task::decode` is the runtime's `try_decode_with` under `Task::MAX_DEPTH` and
`Task::MAX_ENCODED_LEN`, then `Task::from_cbor`. The call's root decides its bounds: a
message nested inside a `Task` does not change them. The two steps can also be taken by
hand, `try_decode(&bytes)?` then `Task::from_cbor(&c)`, but `try_decode` applies only
the defaults (depth 32, no length bound), not the schema's.

Every decode entry point returns `Result<_, DecodeError>`; none panics, and no input
exhausts the stack.

## 4. The `Cbor` runtime (`cbor.rs`)

A tiny frozen subset of RFC 8949 in core deterministic encoding (definite lengths,
shortest-form ints, ascending map keys, shortest-form floats). Hand-rolled, zero deps.

```rust
pub enum Cbor { Int(i64), Float(f64), Bytes(Vec<u8>), Text(String), Array(Vec<Cbor>),
                Map(Vec<(i64, Cbor)>), Bool(bool), Null }

pub const DEFAULT_MAX_DEPTH: usize = 32;   // the depth bound where none is given
pub const MAX_DEPTH_CEILING: usize = 128;  // no decode applies a deeper bound

pub fn encode(v: &Cbor) -> Vec<u8>;
pub fn try_decode(data: &[u8]) -> Result<Cbor, DecodeError>;   // DEFAULT_MAX_DEPTH, no length bound
pub fn try_decode_max(data: &[u8], max_encoded_len: usize) -> Result<Cbor, DecodeError>;
pub fn try_decode_with(data: &[u8], max_depth: usize, max_encoded_len: Option<usize>)
    -> Result<Cbor, DecodeError>;
```

Decode is bounded. An array or map has depth one more than the arrays and maps around
it, so a top-level one has depth 1; at a bound of 32, 32 nested containers decode and the
33rd is `TooDeep { limit: 32 }`, refused once its head is read, before any of its items.
`try_decode_with` takes the caller's bounds: a `max_depth` above `MAX_DEPTH_CEILING`
applies the ceiling, and `limit` names the bound applied; with `Some(max_encoded_len)`,
longer input is `TooLarge { len, limit }` before a byte is read. A `max_depth` of 0 is
the caller's error, not the input's: it panics before the input is read.

Accessors, each the value or a `DecodeError`: `.try_int()`, `.try_float()`,
`.try_text()`, `.try_bytes()`, `.try_bool()`, `.try_array()` (`WrongType` otherwise),
`.try_get(key)` (map value by key, `MissingKey` if absent) and `.try_get_opt(key)`
(`Ok(None)` if absent). Plain predicates: `.is_null()`, `.is_map()`, and
`.map_entries()` (empty if not a map).

`DecodeError` has one variant per tag: `Truncated`, `TrailingBytes`, `InvalidUtf8`,
`UnsupportedInfo(u8)`, `UnsupportedMajor(u8)`, `NonCanonicalInt(u64)`, `IntOverflow`,
`NonIntegerMapKey`, `NegativeMapKey(i64)`, `DuplicateMapKey(MapKey)`, `MissingKey(i64)`,
`WrongType { expected }`, `UnknownEnum { enum_name, value }`, `TooDeep { limit }` and
`TooLarge { len, limit }`. `e.tag()` is the variant's name, the tag every taut language
reports. A `MapKey` is the repeated key, an int, a str or a bool, and displays as text:
an int in decimal, a str as itself, a bool as `true` or `false`. The full table of tags,
payloads and the order of checks is in [CodecContract.md](CodecContract.md).

## 5. Forward-compatibility (unknown-field preservation)

Generate with `--forward-compat` and each struct gains
`pub wire_residual: Vec<(i64, Cbor)>`. On `from_cbor`, tags the struct doesn't name
are captured there; on `to_cbor`, they're re-emitted **merged with the known fields
in one ascending-tag order** — so a node that *decodes → edits → re-encodes* a newer
message never drops fields it doesn't understand. A message with no unknowns is
byte-identical with or without the flag. Without it, `from_cbor` accepts unknown
fields and drops them; the parity gate runs both builds (`rust` and `rust/fc`).

A schema that declares an extension **requires** `--forward-compat` (build error
otherwise — extensions ride the residual space).

## 6. Extensions (side-channels) — `ext.rs`

Attach / read / clear a declared extension on *any* host message's wire bytes,
knowing only the extension's schema (never the host's). Tags live in the band ≥ `2^20`:

```rust
pub fn ext_set(host: &[u8], tag: i64, value: Cbor) -> Result<Vec<u8>, DecodeError>;  // attach / replace
pub fn ext_get(host: &[u8], tag: i64) -> Result<Option<Cbor>, DecodeError>;          // Ok(None) if absent
pub fn ext_clear(host: &[u8], tag: i64) -> Result<Vec<u8>, DecodeError>;             // strip
```

`value` is the generated extension message's `to_cbor()`; decode `ext_get`'s result
with `ExtMsg::from_cbor()`:

```rust
let raw = ext_set(&host, 0x100001, decision.to_cbor())?;
let decision = ext_get(&raw, 0x100001)?.map(|c| Decision::from_cbor(&c)).transpose()?;
let raw = ext_clear(&raw, 0x100001)?;
```

They fail closed: host bytes that do not decode are the `DecodeError` decode reports,
and a host that is not a map is `WrongType { expected: "map" }`. Not knowing the host's
schema, they read a host at the depth ceiling, 128, with no length bound, the only bounds
every valid host meets; the host's own reader applies the host's. A below-band `tag` is
the caller's error: it panics before the host is read. The host app decodes its own
message obliviously — the extension rides in `wire_residual` and survives.

## 7. Consuming the runtime

`cbor.rs` / `ext.rs` are vendored, dependency-free source — drop them into the crate
as `mod cbor;` and `mod ext;`; `api.rs` does `use crate::cbor::{Cbor, DecodeError}`.
`cargo build` (edition 2021) is the only toolchain. The bytes match every other taut
target.

## 8. Changed in v0.10.0

- `--legacy-codec` (`fail_closed=False`) and its runtime are gone; `--fail-closed` is
  an accepted no-op.
- `cbor.rs` drops `decode()` and the accessors that panicked (`get`, `int`, `float`,
  `text`, `bytes`, `boolean`, `array`): use `try_decode` or a message's `decode`, and
  the `try_*` accessors.
- `ext_set`, `ext_get` and `ext_clear` return `Result`; a host that is not a map was a
  panic and is `WrongType`.
- `DecodeError` gains `TooDeep` and `TooLarge`, so an exhaustive `match` needs two more
  arms, and `tag()`. `DuplicateMapKey` carries a `MapKey`, not an `i64`, and a
  `map<K,V>` field refuses a repeated key.
- New: each message's `MAX_DEPTH`, `MAX_ENCODED_LEN` and `decode`; `try_decode_max`,
  `try_decode_with`, `DEFAULT_MAX_DEPTH`, `MAX_DEPTH_CEILING`, `try_get_opt` and
  `is_map`. Input nested deeper than its bound, into which v0.9 recursed without limit,
  is `TooDeep`.
