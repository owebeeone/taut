# Taut Res+Ext Phase 2 Kotlin Prompt Review 55-2

## Findings

1. **[P1] The Kotlin corpus harness is still underspecified under the no-dependency constraint.**

   Phase 1 has landed the two JSON corpora, so the old "missing oracle" blocker is gone. The remaining problem is how Kotlin is supposed to consume them. The Kotlin brief asks to "Compile a harness over both corpora + a differential fuzz" and says "JDK stdlib only" (`dev-docs/TautResExtP2-Kotlin.md:20`-`dev-docs/TautResExtP2-Kotlin.md:23`), while the package remains stdlib-only (`pyproject.toml:21`). Kotlin/JDK stdlib has no JSON parser, and the existing Kotlin parity test avoids this by compiling hardcoded vector source from pytest (`src/tests/test_kotlin.py:107`-`src/tests/test_kotlin.py:125`). The prompt should explicitly require the pytest side to load `corpus/residual_vectors.json` and `corpus/ext_vectors.json`, emit a temporary Kotlin vector table/harness, compile `cbor.kt` + generated `api.kt` + `ext.kt`, and report the deterministic fuzz seed/mismatch count. Otherwise an agent can reasonably add a forbidden dependency, hand-roll a brittle JSON parser, or leave corpus changes disconnected from the compiled gate. **Prior blocker #3 remains unresolved.**

2. **[P1] `ext.kt` still needs an explicit top-level map check to avoid Kotlin/Python divergence.**

   The base brief says extension accessors operate on the top-level CBOR map and mirror `ext.py` (`dev-docs/TautResExtP2-Base.md:47`-`dev-docs/TautResExtP2-Base.md:64`). Python checks the band, decodes the host, then mutates/reads a dict; a scalar host fails instead of being rewritten (`src/taut/ext.py:19`-`src/taut/ext.py:46`). Kotlin's `Cbor.mapEntries` returns the backing `map` list for every `Cbor`, defaulting to empty for non-map kinds (`src/taut/gen/runtime/cbor.kt:7`-`src/taut/gen/runtime/cbor.kt:14`, `src/taut/gen/runtime/cbor.kt:41`). If the implementer follows "decode host, rebuild the pair list" literally (`dev-docs/TautResExtP2-Kotlin.md:14`-`dev-docs/TautResExtP2-Kotlin.md:18`), `extSet` and `extClear` can silently convert scalar bytes into a map. Require `require(decoded.kind == Cbor.MAP)` after the band check for `extSet`, `extGet`, and `extClear`, with a deterministic exception for non-map hosts. **Prior blocker #4 remains unresolved.**

3. **[P2] The available Kotlin toolchain will still be skipped unless the test prompt requires `kotlinc` discovery.**

   The prompt now names the Android Studio `kotlinc` and JBR paths (`dev-docs/TautResExtP2-Kotlin.md:20`-`dev-docs/TautResExtP2-Kotlin.md:21`), and those paths exist in this worktree environment. However, `src/tests/test_kotlin.py` still gates compiled Kotlin parity on `shutil.which("kotlinc")` (`src/tests/test_kotlin.py:107`-`src/tests/test_kotlin.py:110`), while `kotlinc` is not on `PATH`. A targeted run of `src/tests/test_resext_vectors.py` + `src/tests/test_kotlin.py` passes with one skip, and that skip is the Kotlin compile gate. The Phase 2 prompt should require a `_find_kotlinc` helper mirroring `_find_java`: check `KOTLINC`, then the Android Studio path, then `PATH`; run with the discovered JBR Java. **Prior blocker #5 remains unresolved, though the prompt now gives the right absolute paths.**

4. **[P2] The scaffold/runtime blocker is resolved, but Phase 2 should add the Kotlin vendoring assertion once `ext.kt` exists.**

   The old ownership blocker is fixed: `_RUNTIMES["kotlin"]` now includes both `cbor.kt` and `ext.kt` (`src/taut/gen/scaffold.py:32`-`src/taut/gen/scaffold.py:39`), and `emit(..., runtime=True)` skips missing extension files until Phase 2 drops them in (`src/taut/gen/scaffold.py:600`-`src/taut/gen/scaffold.py:607`). `pyproject.toml` already includes `*.kt` package data (`pyproject.toml:38`-`pyproject.toml:40`). But the current Phase 1 test only proves the slot is registered and missing extension files are tolerated (`src/tests/test_resext_vectors.py:69`-`src/tests/test_resext_vectors.py:84`). The Kotlin Phase 2 prompt should require a test that, after creating `src/taut/gen/runtime/ext.kt`, `scaffold.emit(..., langs=["kotlin"], runtime=True, forward_compat=True)` writes both `cbor.kt` and `ext.kt`. It should also add the Kotlin-specific D14 fail/succeed assertion for extension schemas, since current D14 coverage only exercises Rust (`src/tests/test_forward_compat.py:77`-`src/tests/test_forward_compat.py:81`). **Prior blocker #2 is resolved; prior blocker #6 remains unresolved as test coverage.**

5. **[P2] The prompt still over-broadly names `cbor.kt` and `kotlin.py` as owned despite the residual path appearing ready.**

   Kotlin residual support is already generated as `wireResidual`, re-emitted through `toCbor`, captured through `fromCbor`, and sorted by the runtime map encoder (`src/taut/gen/kotlin.py:110`-`src/taut/gen/kotlin.py:140`, `src/taut/gen/runtime/cbor.kt:151`-`src/taut/gen/runtime/cbor.kt:154`). The residual corpus now specifically covers clean, interleaved, band-tag, and combined cases (`corpus/residual_vectors.json:1`-`corpus/residual_vectors.json:22`). Since the base brief says not to touch the proven encode byte path (`dev-docs/TautResExtP2-Base.md:68`-`dev-docs/TautResExtP2-Base.md:74`), narrow the Kotlin brief to "verify residual first; edit `cbor.kt`/`kotlin.py` only for a demonstrated corpus failure." This reduces regression risk in the FLOAT-proven CBOR runtime. **Prior blocker #7 remains as a scope-control risk, not an implementation blocker.**

## Prior Blockers

- **#1 Shared Phase 1 artifacts absent — resolved.** `ir/resext.taut.py` exists (`ir/resext.taut.py:16`-`ir/resext.taut.py:25`); `corpus/residual_vectors.json` has 4 rows and `corpus/ext_vectors.json` has 5 rows; `src/taut/corpus/resext_build.py` generates both; `run_tests.py` runs the generator (`run_tests.py:18`-`run_tests.py:21`); and `src/tests/test_resext_vectors.py` locks committed corpora to generated output. `src/taut/corpus/kit.py` is still Rust-only (`src/taut/corpus/kit.py:89`-`src/taut/corpus/kit.py:93`), but the plan now explicitly defers per-language harness emission as optional and makes the corpora the contract (`dev-docs/TautResExtPlan.md:51`-`dev-docs/TautResExtPlan.md:55`).
- **#2 Scaffold ownership/runtime slot — resolved.** Kotlin has an `ext.kt` runtime slot and Phase 2 can add the file without editing `scaffold.py`.
- **#3 Harness/no-dependency ambiguity — unresolved.**
- **#4 Non-map host behavior — unresolved.**
- **#5 Kotlin toolchain discovery — unresolved, partially mitigated by the prompt's absolute paths.**
- **#6 Kotlin D14 gate coverage — unresolved.**
- **#7 Broad runtime/generator ownership — unresolved as a regression-risk note.**

## Assessment

No P0 blocker remains. Phase 1 has resolved the previous shared-surface blockers, and the Kotlin Phase 2 work is now implementable by an experienced maintainer. I would still tighten the prompt before dispatch because the harness and non-map semantics are underspecified enough to produce non-parity implementations or skipped verification.

## Verification Notes

- Inspected `TautResExtPlan.md`, `TautResExtP2-Base.md`, `TautResExtP2-Kotlin.md`, the prior review, the Phase 1 fixture/corpora/generator tests, scaffold runtime vending, Kotlin generator/runtime/tests, Python `ext.py`, `run_tests.py`, `pyproject.toml`, and `corpus/kit.py`.
- Ran `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m pytest -p no:cacheprovider src/tests/test_resext_vectors.py src/tests/test_kotlin.py -q`: **11 passed, 1 skipped**. The skip is the existing `kotlinc`-on-`PATH` gate; the Android Studio `kotlinc` and JBR Java paths named by the prompt do exist.
- Did not run the full test suite and did not implement code changes.
