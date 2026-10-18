# Taut Res+Ext Phase 2 Kotlin Prompt Review 55-4

## Findings

No actionable prompt issues remain.

The designer-edited Kotlin brief folds in the Review55-3 resolutions and is implementation-ready when read with the base brief. It now limits ownership to `src/taut/gen/runtime/ext.kt` and `src/tests/test_kotlin.py`, explicitly marks `src/taut/gen/runtime/cbor.kt` and `src/taut/gen/kotlin.py` as verify-first only, and says to edit them only on a demonstrated `residual_vectors.json` divergence (`dev-docs/TautResExtP2-Kotlin.md:6`-`dev-docs/TautResExtP2-Kotlin.md:10`). That matches the current Kotlin residual shape: generated `toCbor()` appends `wireResidual`, `fromCbor()` captures unknown map entries, and the Kotlin CBOR map encoder sorts all map entries by key (`src/taut/gen/kotlin.py:110`-`src/taut/gen/kotlin.py:140`, `src/taut/gen/runtime/cbor.kt:151`-`src/taut/gen/runtime/cbor.kt:154`).

The prompt also now prevents the prior skip-prone Kotlin gate from being copied forward. It requires a checked-in `_find_kotlinc` helper that tries `KOTLINC`, the Android Studio compiler path, and then `PATH`, skipping only after all candidates fail and reporting searched paths (`dev-docs/TautResExtP2-Kotlin.md:34`-`dev-docs/TautResExtP2-Kotlin.md:39`). This is the right instruction because the current pre-Phase-2 `src/tests/test_kotlin.py` still uses only `shutil.which("kotlinc")` and skips if the compiler is not already on `PATH` (`src/tests/test_kotlin.py:107`-`src/tests/test_kotlin.py:110`), even though the Android Studio compiler exists in this checkout.

The Kotlin-specific D14/runtime-vendoring coverage is now explicit. The brief requires a Kotlin-named extension-schema gate for fail-without/succeed-with `forward_compat=True`, plus a runtime-vendoring assertion that `scaffold.emit(..., langs=["kotlin"], runtime=True, forward_compat=True)` writes both `cbor.kt` and `ext.kt` after `src/taut/gen/runtime/ext.kt` exists (`dev-docs/TautResExtP2-Kotlin.md:27`-`dev-docs/TautResExtP2-Kotlin.md:32`). The scaffold side supports that requirement: Kotlin has an `ext.kt` runtime slot and `emit()` vendors runtime resources that exist (`src/taut/gen/scaffold.py:32`-`src/taut/gen/scaffold.py:38`, `src/taut/gen/scaffold.py:600`-`src/taut/gen/scaffold.py:607`).

## Proposed Resolutions

None. No prompt edits are required before dispatch.

Residual risks to carry into implementation review:

- The generated Kotlin parity harness still has to prove the typed extension path, not just generic map surgery: `Decision.toCbor()` for `extSet`, `Decision.fromCbor()` after `extGet`, and byte comparison against all corpus rows.
- `src/taut/gen/runtime/ext.kt` does not exist yet, so the Kotlin runtime-vendoring assertion can only become active after the Phase 2 implementation adds that file.
- The current checked-in Kotlin compile test still skips without a `PATH` compiler; this is expected pre-implementation state and is addressed by the prompt, but reviewers should confirm the new `_find_kotlinc` helper actually lands.

## Prior Resolution Check

- **Review55-3 #1, non-skip `kotlinc` discovery: resolved in prompt.** The brief now forbids manual `PATH` reliance and specifies the compiler discovery order and skip-message requirement (`dev-docs/TautResExtP2-Kotlin.md:34`-`dev-docs/TautResExtP2-Kotlin.md:39`).
- **Review55-3 #2, Kotlin D14/runtime-vendoring checks: resolved in prompt.** The brief now asks for Kotlin-specific forward-compat fail/succeed coverage and an `emit(..., langs=["kotlin"], runtime=True, forward_compat=True)` assertion for both runtime files (`dev-docs/TautResExtP2-Kotlin.md:27`-`dev-docs/TautResExtP2-Kotlin.md:32`).
- **Review55-3 #3, narrow residual/runtime ownership wording: resolved in prompt.** The brief now states that `cbor.kt` and `kotlin.py` are verify-first only and should be edited only after a real corpus divergence (`dev-docs/TautResExtP2-Kotlin.md:6`-`dev-docs/TautResExtP2-Kotlin.md:10`).
- **Base-brief dependencies remain satisfied.** The shared fixture and corpora exist, cover clean/interleaved/band residual cases plus five extension operations, and the Python tests lock committed corpora to the generator (`ir/resext.taut.py`, `corpus/residual_vectors.json`, `corpus/ext_vectors.json`, `src/tests/test_resext_vectors.py`).

## Dispatch Verdict

Dispatchable. The Kotlin Phase 2 prompt is now precise enough for an implementation agent: residual work is verify-first, extension work is scoped to a new `ext.kt` plus tests, Kotlin-specific gate coverage is concrete, and compiler discovery is no longer allowed to false-skip merely because the shell lacks manual `PATH` setup.

## Verification Notes

- Read `dev-docs/TautResExtPlan.md`, `dev-docs/TautResExtP2-Base.md`, `dev-docs/TautResExtP2-Kotlin.md`, and `dev-docs/TautResExtP2-Kotlin-Review55-3.md`.
- Inspected relevant fixture/corpus/gate/runtime files: `ir/resext.taut.py`, `corpus/residual_vectors.json`, `corpus/ext_vectors.json`, `src/tests/test_resext_vectors.py`, `src/tests/test_forward_compat.py`, `src/tests/test_kotlin.py`, `src/taut/gen/kotlin.py`, `src/taut/gen/runtime/cbor.kt`, and `src/taut/gen/scaffold.py`.
- Confirmed `/Applications/Android Studio.app/Contents/plugins/Kotlin/kotlinc/bin/kotlinc` is present and reports `kotlinc-jvm 2.2.20`; the matching JBR Java reports OpenJDK `21.0.10`.
- Ran `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m pytest -q -p no:cacheprovider src/tests/test_resext_vectors.py src/tests/test_forward_compat.py src/tests/test_kotlin.py`: **21 passed, 1 skipped**. The skip is the current pre-implementation `shutil.which("kotlinc")` behavior, not a remaining prompt issue.
- Did not implement runtime code, commit, push, or edit any file other than this review document.
