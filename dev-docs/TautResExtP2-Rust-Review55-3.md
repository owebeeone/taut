# Taut Res+Ext Phase 2 Rust Prompt Review 55-3

## Findings

No blocker or major findings remain in this pass. The Rust Phase 2 prompt is implementable as written, with one wording cleanup recommended before fan-out.

1. **[Minor] The last Rust verification sentence still says "cargo is available" even though the operative harness path is the pytest/temp-`rustc --test` pattern.** The prompt now correctly says `razel-wire` is conceptual only and that the actual in-repo harness is `src/tests/test_rust.py`-style pytest that writes a temporary `.rs` and builds it with `rustc --test` (`dev-docs/TautResExtP2-Rust.md:10`-`dev-docs/TautResExtP2-Rust.md:16`). The base brief also says the pytest side owns corpus/fuzz I/O and emits a temp harness source (`dev-docs/TautResExtP2-Base.md:108`-`dev-docs/TautResExtP2-Base.md:112`). But the Rust brief ends with "cargo is available -- build a harness..." (`dev-docs/TautResExtP2-Rust.md:39`-`dev-docs/TautResExtP2-Rust.md:40`). This checkout still has no `Cargo.toml`; `rustc` and `cargo` are installed, but the repo precedent is not an in-tree Cargo crate. This is not blocking because the earlier prompt text is specific enough, but line 39 should say the pytest/temp-`rustc --test` harness is authoritative, or explicitly limit Cargo to an optional temporary harness if used.

## Proposed Resolutions

1. **Clean up the Rust harness wording**
   - **Resolution:** Change the last Rust prompt sentence so the authoritative verification path is the existing pytest-generated temporary `rustc --test` harness. If Cargo is mentioned, limit it to an optional temporary helper, not the in-repo contract.
   - **Verification:** The Rust Phase 2 test addition should live in the existing Python test pattern, generate the fixture with `--forward-compat`, compile a temporary Rust test harness with `rustc --test`, run residual and extension corpora, assert below-band `panic!`, and run the deterministic fuzz loop.

## Prior Issue Status

- **Review55 blocker 1, missing Phase 1 oracle artifacts: resolved.** `ir/resext.taut.py`, `corpus/residual_vectors.json`, and `corpus/ext_vectors.json` are present. The residual corpus has the clean, interleaved, band-tag, and interleaved+band rows; the extension corpus has set, replace, get, absent, and clear rows. `run_tests.py` regenerates `taut.corpus.resext_build`, and `src/tests/test_resext_vectors.py` locksteps the committed corpora against the generator.

- **Review55 blocker 2, missing `ext.<lang>` scaffold slot: resolved.** `_RUNTIMES` now includes Rust `("ext.rs", "ext.rs")`, and `emit()` vendors runtime resources that exist while skipping Phase-2 files not yet landed. `pyproject.toml` already includes `*.rs` runtime package data, so adding `src/taut/gen/runtime/ext.rs` should be picked up without another packaging edit.

- **Review55 major 3, unavailable Cargo/prior-art harness shape: resolved with the minor wording caveat above.** The current prompt explicitly says `razel-wire` is not in this checkout and names the existing pytest/temp-`rustc --test` pattern as the actual harness shape. The remaining "cargo is available" wording is only a cleanup item.

- **Review55 major 4, ambiguous forward-compatible fixture generation path: resolved.** The base brief names `ir/resext.taut.py` and the Rust prompt says to use `tautc gen --forward-compat` for the fixture while preserving the default-off generator behavior. A smoke run of `PYTHONPATH=src python -m taut.cli gen ir/resext.taut.py --out <tmp> --lang rust --api-only --with-runtime --forward-compat` generated forward-compatible `api.rs` plus `cbor.rs`; `Host` and `Decision` both carried `wire_residual`.

- **Review55 major 5, Rust extension API/error semantics: resolved.** The Rust prompt now pins `ext_set(host: &[u8], tag: i64, value: Cbor) -> Vec<u8>`, `ext_get(...) -> Option<Cbor>`, and `ext_clear(...) -> Vec<u8>`, requires a first-step band check, and explicitly chooses `panic!` rather than `Result`. It also requires a `#[should_panic]` below-band test and tells the harness to exercise `Decision::to_cbor()`/`Decision::from_cbor()`.

- **Review55-2 blocker 1, stale scaffold test that rejected `ext.rs`: resolved.** `src/tests/test_resext_vectors.py` now checks that every language has an extension runtime slot and that `emit()` vendors registered runtime resources that exist. It no longer asserts Rust `ext.rs` is absent, so adding the requested file should not flip the shared Phase 1 test.

- **Review55-2 major 2, harness/fuzz direction: resolved except for the minor Cargo wording.** The base brief now gives a concrete no-new-deps differential fuzz shape: fixed seed, at least 1000 iterations, Python oracle, pytest-generated compiled harness, and clear skip/report behavior if the toolchain is absent.

- **Review55-2 major 3, API/error semantics: resolved.** See Review55 major 5 above.

- **Review55-2 minor 4, direct Rust generator trap: resolved.** The prompt continues to steer the agent through `tautc gen --forward-compat` and warns not to change the `forward_compat=False` defaults in `rust.py::_emit` / `_emit_message`.

## Assessment

The Rust Phase 2 prompt is now implementable. The shared prerequisites have landed, scaffold/package wiring no longer blocks `ext.rs`, the fixture generation path is clear, and the public Rust extension surface is pinned tightly enough to avoid the prior panic-vs-`Result` drift.

Residual parity looks likely to pass unchanged: forward-compatible `to_cbor()` appends known fields and residual pairs into one `Cbor::Map`, and Rust CBOR map encoding sorts all keys before writing. Extension work is genuinely net-new but scoped: implement `src/taut/gen/runtime/ext.rs`, then add Rust tests that generate the fixture, compile a temp harness against `api.rs`/`cbor.rs`/`ext.rs`, run both corpora, assert below-band panic behavior, and run the fixed-seed differential loop.

Verification run for this review:

- `PYTHONPATH=src python -m pytest src/tests/test_resext_vectors.py src/tests/test_forward_compat.py src/tests/test_rust.py -q` -> 19 passed.
- `PYTHONPATH=src python -m pytest src/tests -q` -> 187 passed, 1 skipped.
