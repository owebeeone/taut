# taut — Rust API

> Using taut-generated **Rust** code: native types, the deterministic-CBOR wire,
> forward-compatibility, and side-channel extensions. Authoring an IR is in
> [Reference.md](Reference.md); serving a service is in [Server.md](Server.md).

Generated Rust is plain types over a vendored, dependency-free CBOR runtime. Every
language reproduces the *same bytes* — the conformance corpus proves it.

## 1. Generate

```sh
tautc gen --lang rust --with-runtime -o <out>
```

Writes, into `<out>/rust/`:

| file | what |
| --- | --- |
| `api.rs` | native types (`enum`/`struct`) + `to_cbor`/`from_cbor` |
| `cbor.rs` | the deterministic-CBOR runtime (`Cbor`, `encode`, `decode`) |
| `ext.rs` | extension accessors (`ext_set`/`ext_get`/`ext_clear`) |
| `client.rs` / `server.rs` | typed stubs over a transport (see [Server.md](Server.md)) |

Re-export at the crate root so generated code resolves `crate::cbor` / `crate::ext`:
`pub use generated::*; pub use cbor::*;`. No third-party crates.

## 2. Native types

Enums carry an integer wire value; the names are a projection:

```rust
pub enum TaskState { Open, Doing, Done }
impl TaskState {
    pub fn wire(self) -> i64;          // Open=0, Doing=1, Done=2
    pub fn from_wire(v: i64) -> Self;  // panics on an unknown value
}
```

Messages are structs with `to_cbor` / `from_cbor`:

```rust
pub struct User { pub id: i64, pub name: String }
impl User {
    pub fn to_cbor(&self) -> Cbor;        // Cbor::Map([(1, ..), (2, ..)])
    pub fn from_cbor(c: &Cbor) -> Self;   // c.get(1).int(), c.get(2).text()
}
```

Field mapping: `INT → i64`, `STR → String`, `BYTES → Vec<u8>`, `BOOL → bool`,
`FLOAT → f64`, `List(T) → Vec<T>`, `Map(K,V) → BTreeMap<K,V>`. **Optional** fields
are `Option<T>` (encoded as CBOR `null` when `None`). **Transient** fields are in
the struct but never on the wire.

## 3. Encode / decode

A message ↔ CBOR bytes goes through the generated `to_cbor`/`from_cbor` plus the
runtime `encode`/`decode`:

```rust
use crate::cbor::{encode, decode};

let bytes: Vec<u8> = encode(&task.to_cbor());   // serialize
let task = Task::from_cbor(&decode(&bytes));     // deserialize
```

## 4. The `Cbor` runtime (`cbor.rs`)

A tiny frozen subset of RFC 8949 in core deterministic encoding (definite lengths,
shortest-form ints, ascending map keys, shortest-form floats). Hand-rolled, zero deps.

```rust
pub enum Cbor { Int(i64), Bytes(Vec<u8>), Text(String), Array(Vec<Cbor>),
                Map(Vec<(i64, Cbor)>), Bool(bool), Null, Float(f64) }

pub fn encode(v: &Cbor) -> Vec<u8>;
pub fn decode(data: &[u8]) -> Cbor;
```

Accessors (panic on the wrong shape): `.int()`, `.text()`, `.bytes()`,
`.boolean()`, `.float()`, `.array()`, `.get(tag)` (map value by tag),
`.map_entries()`, `.is_null()`.

## 5. Forward-compatibility (unknown-field preservation)

Generate with `--forward-compat` and each struct gains
`pub wire_residual: Vec<(i64, Cbor)>`. On `from_cbor`, tags the struct doesn't name
are captured there; on `to_cbor`, they're re-emitted **merged with the known fields
in one ascending-tag order** — so a node that *decodes → edits → re-encodes* a newer
message never drops fields it doesn't understand. A message with no unknowns is
byte-identical with or without the flag.

A schema that declares an extension **requires** `--forward-compat` (build error
otherwise — extensions ride the residual space).

## 6. Extensions (side-channels) — `ext.rs`

Attach / read / clear a declared extension on *any* host message's wire bytes,
knowing only the extension's schema (never the host's). Tags live in the band ≥ `2^20`:

```rust
pub fn ext_set(host: &[u8], tag: i64, value: Cbor) -> Vec<u8>;  // attach / replace
pub fn ext_get(host: &[u8], tag: i64) -> Option<Cbor>;          // None if absent
pub fn ext_clear(host: &[u8], tag: i64) -> Vec<u8>;             // strip
```

`value` is the generated extension message's `to_cbor()`; decode `ext_get`'s result
with `ExtMsg::from_cbor()`:

```rust
let raw = ext_set(&host, 0x100001, decision.to_cbor());
let decision = ext_get(&raw, 0x100001).map(|c| Decision::from_cbor(&c));
let raw = ext_clear(&raw, 0x100001);
```

A below-band `tag` panics; a non-map host panics. The host app decodes its own
message obliviously — the extension rides in `wire_residual` and survives.

## 7. Consuming the runtime

`cbor.rs` / `ext.rs` are vendored, dependency-free source — drop them into the crate
and re-export; `api.rs` does `use crate::cbor::Cbor`. `cargo build` is the only
toolchain. The bytes match every other taut target.
