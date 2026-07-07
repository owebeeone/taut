# Fail-closed Rust codec (`--fail-closed`)

**Status:** implemented (opt-in). Default codegen is byte-for-byte unchanged.

> **Revised 2026-07-07 — the frozen wire int subset is `i64` (`[-2^63, 2^63-1]`).**
> The `i128` widening described below was dropped. The fail-closed path keeps the
> `i64` carrier (same as the default runtime) but rejects a CBOR integer *outside*
> the `i64` subset as a typed `DecodeError::IntOverflow` — never the default
> runtime's silent `n as i64` wrap, never a panic, never a wider (128-bit) carry.
> On decode this fires in `dec`'s major-0 / major-1 arms (`i64::try_from`); on
> encode the `i64` carrier *is* the guarantee — an out-of-subset value is
> unrepresentable, so `encode` stays infallible and byte-identical. If 128-bit is
> ever needed it will be added as a distinct type, not a widening of `int`. Every
> mention of an `i128` carrier / "full `[-2^64, 2^64-1]` range" below is
> superseded by this note.

## Why

taut's Rust codec was written for a *trusted* producer: `cbor::decode` panics on
malformed input (short reads, bad UTF-8, trailing bytes, out-of-subset major/
simple values), the generated `from_wire` panics on an unknown enum wire value,
and the generated `from_cbor` reads fields through the panicking `Cbor::get()` /
`Cbor::int()` accessors. On top of that, `Cbor::Int` is an `i64` and decode does
`Cbor::Int(n as i64)`, so a CBOR `u64` above `i64::MAX` (e.g. `u64::MAX` →
`1bffffffffffffffff`) **silently wraps** to a negative `i64`.

razel is about to drive an **untrusted socket boundary** with taut-generated
messages. A panic there is a remote crash; a silent u64 wrap is a correctness
hole. `taut-shape-tool`'s `framing.rs` already had to wrap decode in a
`catch_unwind` and range-check tags before calling `from_wire` — proof the
panics leak all the way up. The fix pushes fail-closed discipline **down into
decode itself** so the `catch_unwind` becomes unnecessary.

## The opt-in — mirrors `--forward-compat`

`from_cbor -> Result<_, DecodeError>` is an API change to generated code, so it
is strictly **opt-in**, exactly like `--forward-compat`:

- `tautc gen … -l rust --fail-closed` (CLI) / `scaffold.emit(…, fail_closed=True)`
  (API). Threaded as a `fail_closed: bool = False` kwarg through
  `emit → rust_api → _emit_enum / _emit_message / _decode_try`.
- **Off by default**: a consumer who regenerates *without* the flag gets today's
  output **byte-for-byte** (proven: pristine-HEAD default output ≡ new default
  output, and the byte-exact generator tests in `test_rust.py` still pass). So
  existing consumers (gwz) are unaffected by construction.
- Rust-only today. `emit()` raises if `--fail-closed` is combined with a non-rust
  target, so the flag never gives a false sense of hardening for a language whose
  codegen wasn't hardened.

## What the flag changes (all opt-in, all Rust)

1. **`from_cbor -> Result<Self, DecodeError>`** — every field decodes through the
   fallible `try_get(tag)?` + `try_int()?` / `try_text()?` / … accessors and
   `?`-propagates a typed error. Never panics on any byte input.
2. **`from_wire(v: i128) -> Result<Self, DecodeError>`** — an unknown wire value
   is `Err(DecodeError::UnknownEnum { … })`, not a panic.
3. **`int` fields keep the `i64` carrier** (per the 2026-07-07 note above): an
   out-of-`i64` CBOR integer is a typed `DecodeError::IntOverflow`, not the
   default runtime's silent `n as i64` wrap. `enum::wire()` returns `i64`, so
   `Cbor::Int(x.wire())` type-checks against the carrier.
4. With `--with-runtime`, the **hardened `cbor.rs`** is vendored (under the same
   output name, so `use crate::cbor` is unchanged): a typed `DecodeError`, a
   fallible `try_decode` + `try_*` accessors, and a bounds-checked `dec`/
   `read_arg` (`data.get(..)` / `checked_add`, `core::str::from_utf8`) — no raw
   indexing, no `unwrap`, no `assert`/`panic` on the decode path.

The **infallible** `decode`/`get`/`int`/… surface is retained on the hardened
runtime (so `ext.rs` and any code sharing the runtime still links); `int()` still
returns `i64` (truncating, as before) — new code wanting the full range uses
`try_int() -> Result<i128, _>`.

## Integer representation (SUPERSEDED — see the 2026-07-07 note; the carrier is `i64`)

The frozen CBOR subset represents integers in `[-2^64, 2^64-1]` (major-0 argument
up to `u64::MAX`; major-1 down to `-1 - (u64::MAX)` = `-2^64`). The **Python
reference** (`taut/src/taut/wire/cbor.py`) decodes these to Python's unbounded
`int` — so the parity target is "the integer value survives round-trip, no
truncation."

`i128` is the smallest single Rust carrier that holds that whole range, so:

- It matches the Python oracle **value-for-value** for every representable int.
- **Encode is byte-identical**: `enc` does `*n as u64` / `(-1 - *n) as u64`, which
  produces the same bytes for `i128` as for `i64` across the entire `i64` range
  (verified: 50k random values, default-runtime `encode` ≡ hardened-runtime
  `encode`), and now *correctly* emits `1bffffffffffffffff` for `u64::MAX` instead
  of wrapping.
- Cross-language byte-parity is therefore preserved (the golden corpus + the
  rs/ts/py interop matrix stay green).

Map **keys** stay `i64` (CBOR field tags are small; a key that doesn't fit `i64`
is rejected as `DecodeError::IntOverflow`, not silently wrapped) — this keeps
`ext.rs` and the `wire_residual: Vec<(i64, Cbor)>` field source-compatible.

Rejected alternatives: separate `U64`/`I64` `Cbor` arms (fractures `PartialEq`
and every `match`), and a divergent value model (would break cross-language
byte-parity). `i128` is a single carrier that is parity-exact and keeps `enc` one
arm.

## `DecodeError`

```
enum DecodeError {
    Truncated, TrailingBytes, InvalidUtf8,
    UnsupportedInfo(u8), UnsupportedMajor(u8),
    NonIntegerMapKey, IntOverflow,
    MissingKey(i64),
    WrongType { expected: &'static str },
    UnknownEnum { enum_name: &'static str, value: i64 },
}
```

Every variant is reachable only from *input* bytes; `Display` is implemented; it
is `no_std`-safe (`core::fmt`).

## Files

- `taut/src/taut/gen/rust.py` — `_emit_enum` / `_emit_message` /
  `_from_cbor_fail_closed` / `_decode_try` (+ `_decode_try_elem`) / `_rust_int_type`,
  all gated on `fail_closed`. The default path (`_from_cbor_default`, `_decode`)
  is untouched.
- `taut/src/taut/gen/scaffold.py` — `rust_api(fail_closed=…)`, `emit(fail_closed=…)`,
  runtime-resource swap (`cbor.rs → cbor_fail_closed.rs`), rust-only guard.
- `taut/src/taut/cli.py` — `--fail-closed`.
- `taut/src/taut/gen/runtime/cbor_fail_closed.rs` — the hardened runtime template
  (encode byte-identical to `cbor.rs`; adds `DecodeError` + fallible decode).
- `taut/src/tests/test_rust.py` — the fail-closed gates (shape + off-by-default +
  rustc-driven behavior: u64::MAX round-trip and every bad input → typed error).

## Reference adoption: `taut-shape-rs`

`taut-shape-rs` (the reference `log` node/client, the impl razel patterns on) is
migrated to the hardened mode as the worked example:

- `crates/taut-shape/src/cbor.rs` + `generated.rs` re-vendored from the
  `--fail-closed --with-runtime` output (same provenance headers, no_std prelude).
- `framing.rs`: the `catch_unwind` around decode is **gone** — `cbor::try_decode`
  returns `FrameError::MalformedBody(e)` directly; `wire_to_tag` is just
  `LogMsgType::from_wire(byte as i128).ok()` (the range-check-before-panic is no
  longer needed).
- `node.rs` / `client.rs`: `from_cbor(…)?`/`.ok()?`/`match` on the `Result`;
  int-field construction casts widened `as i64 → as i128` (lossless from the
  engine's u64/i64).
- Generated-code lints (`clippy::redundant_closure`, `clippy::needless_question_mark`)
  are `#[allow]`-ed at the `pub mod generated;` declaration in `lib.rs` (same
  convention already used for the default codec), so the vendored output stays
  byte-identical to tautc while `clippy -D warnings` passes. The generator also
  emits `|x| T::from_cbor(x)` (not `|x| Ok(T::from_cbor(x)?)`) for message list
  elements so the *generated* code is clippy-clean for every consumer.

All gates green: taut suite, golden corpus (`corpus/gen.py --check`, rs tool ≡
committed `log.v0.json`), the rs/ts/py interop matrix (36/36), taut-shape-rs
`cargo test --workspace` + `clippy -D warnings`, `no_std` core build.

## razel-facing surface

razel pins taut by release/rev (like gwz) and invokes:

```
tautc gen <razel.taut.py> -o <gen-dir> -l rust --api-only --with-runtime --fail-closed
```

which emits `api.rs` (fallible `from_cbor -> Result<_, DecodeError>`, `i128`
ints) + a hardened `cbor.rs` (fallible `try_decode`). razel decodes socket bytes
with `cbor::try_decode(bytes)?` then `Msg::from_cbor(&c)?` — a malformed or
hostile frame is a typed `DecodeError`, never a panic or a wrapped integer.

## gwz migration (if/when it adopts hardening)

gwz is unaffected today: it regenerates `gwz-core/src/protocol/generated.rs` +
`cbor.rs` **without** `--fail-closed`, so it gets today's bytes exactly. To
adopt the hardening later, gwz re-runs its regen with `--fail-closed`
(`--with-runtime` if it re-vendors `cbor.rs`), then updates its call sites: every
`Msg::from_cbor(&c)` becomes `Msg::from_cbor(&c)?` (its decode entry points
return `Result`), int fields it reads become `i128` (narrow with `as u64`/`as
u32` at the engine boundary, as taut-shape-rs does), and — if it runs
`clippy -D warnings` over the generated file — add the two `#[allow]`s to its
`generated` module declaration (or accept the generator's already-clean output).
It is a mechanical, compiler-driven migration (the build enumerates every site);
no wire-format change, so no corpus/interop rework.
