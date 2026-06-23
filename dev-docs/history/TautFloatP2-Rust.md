# Taut Float — Phase 2: Rust

Read [TautFloatP2-Base.md](TautFloatP2-Base.md) first.

**Files you own:** `src/taut/gen/runtime/cbor.rs` · `src/taut/gen/rust.py` · the Rust
conformance harness (kit `vectors.rs` / the crate's `corpus_byte_parity` test).

**Value model — enum.** `pub enum Cbor { Int(i64), … }` → add `Float(f64)`, plus an
accessor `pub fn float(&self) -> f64 { if let Cbor::Float(x) = self { *x } else { panic!("not a float") } }`.

**Runtime (`cbor.rs`):**
- `enc`: add `Cbor::Float(x) => { … }` — shortest-form per the base algorithm. Bits via
  `f64::to_bits().to_be_bytes()`, `f32::to_bits()`, etc.
- `dec` major 7: add `25 => half→f64`, `26 => f32→f64`, `27 => f64`, reading the raw
  2/4/8 payload bytes (NOT via `read_arg`).
- **Narrowing:** Rust stable has no `f16` and **no deps are allowed** (the `half` crate is
  out). Hand-roll `narrow16` (double→half, round-to-nearest-even, subnormals + overflow→single).
  Single: `let f = *x as f32; if f as f64 == *x { … }`.

**Codegen (`rust.py`):** add `"float"` to `_rust_type` (→ `"f64"`), `_encode`
(→ `Cbor::Float({expr})`), `_encode_ref`, and `_decode` (→ `{expr}.float()`). Verify line
numbers — they drift.

**Verify:** if `cargo` is present, add float rows to the parity harness and run
`corpus_byte_parity`; else mirror `wire/cbor.py` exactly and hand-check each corpus row.
Keep `test_regen.py` green (it byte-checks `generated.rs` against the generator).
