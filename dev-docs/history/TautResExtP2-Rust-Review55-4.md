# Taut Res+Ext Phase 2 Rust Prompt Review 55-4

## Findings

No actionable blocker, major, or minor prompt issues remain in this pass.

The designer folded the Review55-3 proposed resolution into the Rust prompt: the stale "cargo is available" verification wording is gone, and the prompt now names the authoritative in-repo pytest-generated temporary `rustc --test` harness pattern (`dev-docs/TautResExtP2-Rust.md:50`-`dev-docs/TautResExtP2-Rust.md:52`). That matches the existing Rust test precedent in `src/tests/test_rust.py`, where pytest writes a temporary Rust test source, vendors `cbor.rs` via `#[path = ...]`, compiles with `rustc --test`, and runs the resulting binary (`src/tests/test_rust.py:41`-`src/tests/test_rust.py:102`).

The prompt is now implementation-ready for the Rust Phase 2 agent. It constrains owned files, preserves the verify-first posture for `cbor.rs` and `rust.py`, pins Rust extension API/error semantics, requires typed `Decision::to_cbor()` / `Decision::from_cbor()` exercise, covers below-band and non-map invalid cases, and names the fixed-seed differential fuzz evidence required by the base brief.

Residual risk / test gaps, not prompt blockers:

- `src/taut/gen/runtime/ext.rs` does not exist yet, so `tautc gen --with-runtime` currently vendors only `api.rs` and `cbor.rs` for Rust. This is expected Phase 2 implementation work, not a prompt issue.
- Rust residual byte parity is still unproven until the Phase 2 harness lands. The current generator/runtime shape looks aligned: forward-compatible `to_cbor()` appends known fields plus `wire_residual` into one `Cbor::Map`, and `Cbor::Map` encoding sorts keys before writing.
- The deterministic fuzz loop is specified but not implemented yet. The prompt correctly treats it as supporting evidence while the checked-in corpus parity remains the hard gate.

## Proposed Resolutions

No further prompt/doc changes are required before dispatch.

Implementation guidance for the Phase 2 Rust agent remains:

- Add `src/taut/gen/runtime/ext.rs` with `ext_set`, `ext_get`, and `ext_clear` over the existing `Cbor` enum.
- Extend `src/tests/test_rust.py` using the existing pytest/temp-`rustc --test` pattern.
- Generate `ir/resext.taut.py` with `--forward-compat`, run all residual and extension corpus rows byte-for-byte, assert below-band panic and non-map rejection, and report the fixed fuzz seed plus mismatch count.

## Prior Resolution Check

- **Review55-3 minor, stale Cargo wording: resolved.** The Rust prompt no longer tells the implementer to use Cargo as the verification path. It explicitly says the authoritative path is the pytest-generated temporary `rustc --test` harness and not an in-tree Cargo crate (`dev-docs/TautResExtP2-Rust.md:50`-`dev-docs/TautResExtP2-Rust.md:52`).

- **Review55 blocker 1, missing Phase 1 oracle artifacts: still resolved.** `ir/resext.taut.py`, `corpus/residual_vectors.json`, and `corpus/ext_vectors.json` are present. The residual corpus includes clean, interleaved unknown, band-tag residual, and interleaved+band rows; the extension corpus includes attach, replace, get, absent, and clear rows.

- **Review55 blocker 2, missing `ext.<lang>` scaffold slot: still resolved.** `scaffold._RUNTIMES["rust"]` includes `("ext.rs", "ext.rs")`; `emit()` skips missing runtime resources until Phase 2 adds them, then vendors them automatically (`src/taut/gen/scaffold.py:32`-`src/taut/gen/scaffold.py:39`, `src/taut/gen/scaffold.py:600`-`src/taut/gen/scaffold.py:607`).

- **Review55 major 3 / Review55-2 major 2, unavailable Cargo/prior-art harness shape: resolved.** The Rust prompt treats razel-wire only as conceptual prior art and points to the real in-repo pytest/temp-`rustc --test` harness pattern (`dev-docs/TautResExtP2-Rust.md:15`-`dev-docs/TautResExtP2-Rust.md:21`, `dev-docs/TautResExtP2-Rust.md:50`-`dev-docs/TautResExtP2-Rust.md:53`).

- **Review55 major 4, ambiguous forward-compatible fixture generation path: still resolved.** The base brief names `ir/resext.taut.py` and `tautc gen` from that schema, and the Rust prompt requires `tautc gen --forward-compat` while preserving `forward_compat=False` defaults (`dev-docs/TautResExtP2-Base.md:19`-`dev-docs/TautResExtP2-Base.md:27`, `dev-docs/TautResExtP2-Rust.md:28`-`dev-docs/TautResExtP2-Rust.md:35`).

- **Review55 major 5 / Review55-2 major 3, Rust extension API/error semantics: still resolved.** The Rust prompt pins `ext_set(host: &[u8], tag: i64, value: Cbor) -> Vec<u8>`, `ext_get(...) -> Option<Cbor>`, `ext_clear(...) -> Vec<u8>`, first-step band check, panic-on-misuse, below-band `#[should_panic]`, non-map rejection, and typed `Decision` round-trip exercise (`dev-docs/TautResExtP2-Rust.md:37`-`dev-docs/TautResExtP2-Rust.md:48`).

- **Review55-2 blocker 1, stale scaffold test rejecting `ext.rs`: still resolved.** `src/tests/test_resext_vectors.py` checks the runtime slot and vendors existing registered runtimes; it no longer asserts Rust `ext.rs` is absent (`src/tests/test_resext_vectors.py:69`-`src/tests/test_resext_vectors.py:89`).

- **Review55-2 minor 4, direct Rust generator trap: still resolved.** The prompt directs fixture generation through `tautc gen --forward-compat` and explicitly forbids changing `forward_compat=False` defaults unless a real ResExt vector failure requires it (`dev-docs/TautResExtP2-Rust.md:33`-`dev-docs/TautResExtP2-Rust.md:35`).

## Dispatch Verdict

Dispatch Rust Phase 2.

The prompt is ready for implementation as written. Remaining work is runtime/test implementation, not further prompt design.

## Verification Notes

Commands run from `/Users/owebeeone/limbo/taut-dev-cross/taut-rust`:

- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m pytest -q -p no:cacheprovider src/tests/test_resext_vectors.py src/tests/test_forward_compat.py src/tests/test_rust.py` -> 19 passed.
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m pytest -q -p no:cacheprovider src/tests` -> 187 passed, 1 skipped.
- Temp generation smoke: `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m taut.cli gen ir/resext.taut.py --out <tmp> --lang rust --api-only --with-runtime --forward-compat` -> exit 0, generated `rust/api.rs` and `rust/cbor.rs`; `Host` and `Decision` both carried `wire_residual`. `ext.rs` was not vendored because it has not been implemented yet, as expected.
