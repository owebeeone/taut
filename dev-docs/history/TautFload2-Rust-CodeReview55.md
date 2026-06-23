# Taut Float Phase 2 Rust Code Review 55

## Findings

1. **[P2] Float coverage is untracked and can be lost from the landed change.**

   File/line: `src/tests/test_rust.py:1`

   The only new Rust float tests live in `src/tests/test_rust.py`, but `git status --short` reports it as `?? src/tests/test_rust.py`, while `git diff --name-only` only lists `src/taut/gen/runtime/cbor.rs` and `src/taut/gen/rust.py`. If the current tracked diff is landed as-is, Phase 2 loses its required Python-side Rust shape test and the rustc-backed `corpus/float_vectors.json` runtime parity test. Add this test file to the landed change, or move equivalent coverage into an already tracked test harness.

## Review Notes

No P0/P1 CBOR correctness or generator/runtime mismatch issues were found in the reviewed implementation.

The runtime float path in `src/taut/gen/runtime/cbor.rs:199` checks NaN before width selection, preserves `-0.0` via bit equality, tries half before single before double, and decodes major-7 float widths 25/26/27 without routing through `read_arg`. The hand-rolled half narrowing/re-widening matched the shared corpus and an additional exhaustive half-payload re-encode check.

The generator changes in `src/taut/gen/rust.py:33`, `src/taut/gen/rust.py:47`, `src/taut/gen/rust.py:65`, and `src/taut/gen/rust.py:93` cover the Rust `f64` type, by-value/by-reference float encoding, list/map float values, and `.float()` decoding. The sibling `trial/rs/src/generated.rs` regen gate still passes with the current generator.

## Residual Risks / Test Gaps

- The checked-out `trial/rs` tree contains `src/generated.rs` but no `Cargo.toml` or crate-level `vectors.rs`, so I could not run a Rust crate `corpus_byte_parity` test. The new `src/tests/test_rust.py:41` harness compiles `cbor.rs` directly with `rustc`, which covers the runtime bytes but not a consuming crate.
- The generator test in `src/tests/test_rust.py:24` is string-based; it does not compile a generated Rust module for a float-bearing schema. The current generated snippets look type-correct, and the full Python suite passes, but compiler-backed generated-schema coverage would reduce integration risk.

## Commands Inspected / Ran

- Read `dev-docs/TautFloatP2-Base.md` and `dev-docs/TautFloatP2-Rust.md`.
- Inspected `git status --short`, `git diff -- src/taut/gen/runtime/cbor.rs src/taut/gen/rust.py src/tests/test_rust.py`, and numbered source listings for the changed files.
- Ran `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m pytest src/tests/test_rust.py -q -p no:cacheprovider`; this failed because `/opt/homebrew/opt/python@3.14/bin/python3.14` has no `pytest` module.
- Ran `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src pytest src/tests/test_rust.py -q -p no:cacheprovider`: `2 passed`.
- Ran `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src pytest src/tests/test_regen.py::test_generated_rust_matches_committed -q -p no:cacheprovider`: `1 passed`.
- Ran `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src pytest src/tests -q -p no:cacheprovider`: `167 passed`.
- Ran an ad hoc `rustc --test` stdin harness against `src/taut/gen/runtime/cbor.rs` that exhaustively checked all half-float payloads for decode/re-encode behavior and checked f32 `-0.0`/NaN re-encoding: `2 passed`.
