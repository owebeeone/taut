# Taut Res+Ext Phase 2 Kotlin Prompt Review 55-3

## Findings

1. **[P2] The Kotlin compiled parity gate is still skip-prone because toolchain discovery is left to shell setup.**

   The Kotlin brief now names the Android Studio `kotlinc` and JBR paths, but it still tells the implementer to prepend `kotlinc` to `PATH` because `test_kotlin.py` uses `shutil.which("kotlinc")`; otherwise the harness "silently skips" (`dev-docs/TautResExtP2-Kotlin.md:20`-`dev-docs/TautResExtP2-Kotlin.md:23`). The current test does exactly that (`src/tests/test_kotlin.py:107`-`src/tests/test_kotlin.py:110`). In this checkout the absolute `kotlinc` and JBR Java paths exist, yet the default focused test run reports `11 passed, 1 skipped`; with the documented `PATH`/`JAVA_HOME`, the existing Kotlin compile harness passes. That means a Phase 2 implementation can look green for a reviewer or CI job while never running the compiled residual/ext corpus harness, even though the local toolchain is available. Make the prompt require a checked-in `_find_kotlinc` helper mirroring `_find_java`: try `KOTLINC`, then the Android Studio path, then `PATH`, and skip/report only if all candidates fail. **Prior issue #5 is only partially resolved.**

2. **[P2] Kotlin-specific D14 and runtime-vendoring assertions are still not explicit enough.**

   The old scaffold ownership blocker is fixed: `_RUNTIMES["kotlin"]` contains `("ext.kt", "ext.kt")` (`src/taut/gen/scaffold.py:32`-`src/taut/gen/scaffold.py:39`), and `emit(..., runtime=True)` vendors runtime resources that exist while tolerating Phase-2-missing ext files (`src/taut/gen/scaffold.py:600`-`src/taut/gen/scaffold.py:607`). The remaining test gap is Kotlin-specific. Current shared tests prove the slot mechanism generically and only emit Rust at runtime (`src/tests/test_resext_vectors.py:71`-`src/tests/test_resext_vectors.py:89`), while the extension/forward-compat failure test is Rust-only (`src/tests/test_forward_compat.py:77`-`src/tests/test_forward_compat.py:81`). The Kotlin prompt owns `src/tests/test_kotlin.py` (`dev-docs/TautResExtP2-Kotlin.md:6`-`dev-docs/TautResExtP2-Kotlin.md:8`) but does not say to assert that, once `src/taut/gen/runtime/ext.kt` exists, `scaffold.emit(..., langs=["kotlin"], runtime=True, forward_compat=True)` writes both `cbor.kt` and `ext.kt`, or that Kotlin generation fails without `forward_compat` for an extension schema and succeeds with it. The base brief says the invariant must remain intact (`dev-docs/TautResExtP2-Base.md:47`-`dev-docs/TautResExtP2-Base.md:50`, `dev-docs/TautResExtP2-Base.md:117`-`dev-docs/TautResExtP2-Base.md:120`), but the Kotlin dispatch should make the expected assertions concrete. **Prior issue #2 is resolved; prior issue #6 remains unresolved as coverage.**

3. **[P3] The Kotlin-specific ownership list still invites unnecessary residual/runtime edits.**

   Kotlin residual support appears ready: generated `toCbor()` appends `wireResidual`, `fromCbor()` captures unknown entries, and the runtime map encoder sorts all entries by key (`src/taut/gen/kotlin.py:110`-`src/taut/gen/kotlin.py:140`, `src/taut/gen/runtime/cbor.kt:151`-`src/taut/gen/runtime/cbor.kt:154`). The residual corpus now covers clean, interleaved, band-tag, and combined rows (`corpus/residual_vectors.json:1`-`corpus/residual_vectors.json:22`). The base workflow says to verify residual first and fix only a real divergence (`dev-docs/TautResExtP2-Base.md:95`-`dev-docs/TautResExtP2-Base.md:99`), and it warns not to touch the proven encode byte path (`dev-docs/TautResExtP2-Base.md:87`-`dev-docs/TautResExtP2-Base.md:93`). The Kotlin brief still lists `cbor.kt` and `kotlin.py` as owned without the same "edit only on demonstrated corpus failure" qualifier (`dev-docs/TautResExtP2-Kotlin.md:6`-`dev-docs/TautResExtP2-Kotlin.md:8`). This is not an implementation blocker, but narrowing the wording would reduce avoidable FLOAT/CBOR regression risk. **Prior issue #7 remains as a scope-control risk.**

## Proposed Resolutions

1. **Make Kotlin toolchain discovery non-skip by default**
   - **Resolution:** Update the Kotlin prompt to require a checked-in `_find_kotlinc` helper in `src/tests/test_kotlin.py`, mirroring the existing Java discovery style: try `KOTLINC`, then the Android Studio Kotlin path, then `PATH`. Skip only after all candidates fail, and include the searched paths in the skip message.
   - **Verification:** Run the focused Kotlin compile harness without manually editing `PATH`; in this checkout it should find the Android Studio Kotlin compiler and run instead of reporting a skip.

2. **Add Kotlin-specific D14/runtime-vendoring checks**
   - **Resolution:** Require Kotlin Phase 2 to add target-named assertions that extension schemas fail without `forward_compat=True`, succeed with it, and that `scaffold.emit(..., langs=["kotlin"], runtime=True, forward_compat=True)` vendors both `cbor.kt` and `ext.kt` after `src/taut/gen/runtime/ext.kt` exists.
   - **Verification:** The Kotlin test suite should have a Kotlin-named forward-compat gate and a Kotlin runtime vendoring assertion, not only the shared Rust-backed checks.

3. **Narrow residual/runtime ownership wording**
   - **Resolution:** Change the Kotlin prompt from broad ownership of `kotlin.py`/`cbor.kt` to verify-first ownership: do not edit generator or proven CBOR encode paths unless the residual corpus demonstrates a real Kotlin divergence. Expected Phase 2 implementation should primarily add `ext.kt` and tests.
   - **Verification:** Review diff should show no Kotlin generator/runtime CBOR churn unless tied to a failing residual vector.

## Prior Issues

- **#1 Shared Phase 1 artifacts absent — resolved.** `ir/resext.taut.py` exists and defines the shared `Host`/`Decision` fixture plus band extension (`ir/resext.taut.py:16`-`ir/resext.taut.py:24`). Both corpora exist with the expected 4 residual and 5 extension vectors (`corpus/residual_vectors.json:1`-`corpus/residual_vectors.json:22`, `corpus/ext_vectors.json:1`-`corpus/ext_vectors.json:43`). `src/taut/corpus/resext_build.py` generates them, `run_tests.py` runs that generator, and `src/tests/test_resext_vectors.py` locks committed output to generated output.
- **#2 Scaffold ownership/runtime slot — resolved.** Kotlin has an `ext.kt` runtime slot, so Phase 2 can add the Kotlin runtime module without editing `scaffold.py`.
- **#3 Harness/no-dependency ambiguity — resolved in the base brief.** The base now explicitly says compiled stdlib-only targets do not parse JSON; pytest must load JSON/generate fuzz rows, emit a temporary Kotlin vector table/harness, then compile and run it (`dev-docs/TautResExtP2-Base.md:108`-`dev-docs/TautResExtP2-Base.md:112`).
- **#4 Non-map host behavior — resolved in the base brief.** The base now requires a top-level map check and says not to coerce scalar/array hosts into maps (`dev-docs/TautResExtP2-Base.md:68`-`dev-docs/TautResExtP2-Base.md:70`).
- **#5 Kotlin toolchain discovery — partially unresolved.** The prompt gives the right absolute paths and they work, but the checked-in test pattern still false-skips unless `PATH` is manually prepared.
- **#6 Kotlin D14 gate coverage — unresolved as test coverage.** The invariant is in the base brief, but the Kotlin prompt should ask for a Kotlin-specific fail/succeed assertion and ext runtime vendoring assertion.
- **#7 Broad runtime/generator ownership — unresolved as a low-severity scope risk.** Residual should be verify-first; runtime/generator edits should be limited to demonstrated corpus failures.

## Assessment

No P0/P1 blocker remains. The Kotlin Phase 2 prompt is implementable as written when read with the strengthened base brief: shared corpora are present, the fixture is present, scaffold/runtime vending is ready for `ext.kt`, no new dependency is needed, non-map semantics are specified, and the residual path appears byte-parity-ready.

I would still tighten the Kotlin-specific brief before dispatch so the compiled parity harness cannot silently skip in this environment and so Kotlin-specific D14/runtime-vendoring coverage is explicit. Those are testability and regression-risk issues, not blockers to implementation.

## Verification Notes

- Inspected `TautResExtPlan.md`, `TautResExtP2-Base.md`, `TautResExtP2-Kotlin.md`, both prior reviews, the resext fixture/corpora/generator/tests, scaffold runtime vending, Kotlin generator/runtime/tests, Python `ext.py`, `run_tests.py`, and package metadata.
- Ran `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m pytest -p no:cacheprovider src/tests/test_resext_vectors.py src/tests/test_kotlin.py -q`: **11 passed, 1 skipped**. The skip is the default `kotlinc` discovery gate.
- Ran `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src JAVA_HOME="/Applications/Android Studio.app/Contents/jbr/Contents/Home" PATH="/Applications/Android Studio.app/Contents/plugins/Kotlin/kotlinc/bin:$PATH" python -m pytest -p no:cacheprovider src/tests/test_kotlin.py::test_kotlin_float_parity_harness_if_kotlinc -q`: **1 passed**.
- Did not implement code, did not edit any file other than this review document, and did not commit or push.
