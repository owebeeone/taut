# Taut Res+Ext Parity — Phase 2: Rust

Read [TautResExtP2-Base.md](TautResExtP2-Base.md) first; reuse
[history/TautFloatP2-Rust.md](history/TautFloatP2-Rust.md) for the `Cbor` enum idiom.

**Files you own:** **NEW** `src/taut/gen/runtime/ext.rs` · `src/tests/test_rust.py`.
`src/taut/gen/runtime/cbor.rs` and `src/taut/gen/rust.py` are verify-first only: residual support
appears present (`wire_residual: Vec<(i64, Cbor)>` and sorted map encode), so edit them only if
`residual_vectors.json` demonstrates a real Rust divergence.

**Do not change:** `ir/*`, the corpora/generators, Python `ext.py`, `gen/scaffold.py`, another
language, package dependencies, `forward_compat=False` defaults, or proven FLOAT/CBOR encode paths
unless tied to a failing ResExt vector.

**Prior art — `razel/crates/razel-wire` (verified 2026-06-23).** razel ships a proven taut Rust
wire crate: `cbor.rs` (runtime, incl. the `map_entries` residual primitive), `vectors.rs` (golden
corpus from taut's Python codec), and a `corpus_byte_parity` test that decode→re-encodes every
vector to identical bytes in `cargo test`. That crate is **not in this checkout** (no `Cargo.toml`/`vectors.rs`/`razel-wire` here) — treat it as
*conceptual* prior art. Your actual harness is the in-repo `src/tests/test_rust.py` pattern: a pytest
that writes a temp `.rs`, `#[path=…] mod cbor;` the vendored runtime, and builds+runs with `rustc --test`
(skip if `rustc` absent). It proves only *codec* parity today — two real gaps remain, so Rust is NOT done:
- **Residual is UNPROVEN in Rust.** Both razel-wire and `gwz-core` generate with **forward-compat
  OFF** (no `wire_residual` in either `generated.rs`) and neither has an unknown-tag round-trip
  test. Your residual step is the **first** byte-proof of preservation, not a re-confirmation —
  turn the flag on for the fixture and actually gate it.
- **Extensions don't exist in Rust anywhere** (gwz / razel / taut). `ext.rs` is fully net-new.

**Residual (verify — first real byte-proof; see Prior art).** The generated struct carries `wire_residual: Vec<(i64, Cbor)>` and
`to_cbor`/`from_cbor` capture+re-emit. Generate the fixture `--forward-compat`, run
`residual_vectors.json` decode→re-encode, byte-diff. The one thing to verify hard: known fields
and residual pairs emit in a **single ascending tag order** (an unknown tag between two known
tags must interleave). If `to_cbor` builds a `Vec<(i64,Cbor)>` and hands it to `Cbor::Map` whose
`encode` sorts, you're fine — confirm it, don't assume. Turn forward-compat on **only** via
`tautc gen --forward-compat` for the fixture — do NOT change the `forward_compat=False` default in
`rust.py::_emit`/`_emit_message`, or `test_regen`/`test_forward_compat` move.

**Extensions (implement) — `ext.rs`.** Mirror `ext.py` over the `Cbor` enum:
`ext_set(host: &[u8], tag: i64, value: Cbor) -> Vec<u8>` → `decode` host to `Cbor::Map(v)`, drop any
existing `tag`, push `(tag, value)`, `encode(&Cbor::Map(v))` (sorts). `ext_get(host, tag) -> Option<Cbor>`
(None if absent). `ext_clear(host, tag) -> Vec<u8>`. Band-check FIRST: `tag >= 1<<20`, else **`panic!`** — match cbor.rs's
panic-on-misuse idiom (do NOT add a `Result` surface). Add a `#[should_panic]` test for a below-band tag.
Reject non-map hosts; do not coerce them to empty maps. `value` is the caller's
`Decision::to_cbor()`; `ext_get` returns the nested `Cbor` for `Decision::from_cbor`.

**Tests/gates to add:** residual byte parity over all four residual rows; extension byte parity over
all five ext rows through generated `Decision::to_cbor()` / `Decision::from_cbor()`; below-band
`#[should_panic]`; non-map host rejection; the D14 flag/gate checks already in
`test_forward_compat.py`; and the fixed-seed differential fuzz described by the base brief.

**Verify:** the authoritative in-repo path is the existing pytest-generated temporary
`rustc --test` harness pattern, not an in-tree Cargo crate. Required evidence:
`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m pytest -q -p no:cacheprovider src/tests/test_resext_vectors.py src/tests/test_forward_compat.py src/tests/test_rust.py`.
Report `rustc --version`, corpus parity result, invalid-case result, fuzz seed, and mismatch count.
No new deps (no `half`, nothing). Keep `test_regen`/`test_forward_compat` green.
