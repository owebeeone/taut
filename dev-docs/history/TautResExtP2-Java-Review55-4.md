# Taut Res+Ext Phase 2 Java Prompt Review - Fourth Pass

## Findings

No actionable issues remain.

The designer-edited Java prompt has folded the Review55-3 proposed resolutions into the actual
brief. The public extension API is now pinned as `package taut; public final class Ext` with a
private constructor and `public static` `extSet` / `extGet` / `extClear` methods
(`dev-docs/TautResExtP2-Java.md:20`-`32`). Java-specific invalid-case behavior is now explicit:
below-band tags must throw `IllegalArgumentException` before host decode, non-map top-level hosts
must throw, and implementations must inspect `decoded.kind` rather than using `mapEntries()` as a
scalar-to-empty-map fallback (`dev-docs/TautResExtP2-Java.md:34`-`41`). The harness/package concern
is also addressed: the prompt permits the ResExt harness to declare `package taut` for generated
`Host` / `Decision` access while requiring a separate outside-package public API check
(`dev-docs/TautResExtP2-Java.md:43`-`49`).

The prompt is now implementation-ready for the Java Phase 2 agent.

## Proposed Resolutions

None. Keep the current Java prompt wording.

Residual risk/test gaps to carry into implementation:

- The actual `Ext.java` implementation still needs to prove below-band tags are rejected before
  host decode, because the corpus contains only valid above-band rows.
- The public API check should be a real outside-package compile/reflection/source assertion, not
  only an in-package harness compile.
- The deterministic fuzz evidence remains supporting evidence rather than a checked-in gate, per
  the base brief; the Java implementer still needs to report seed and mismatch count.

## Prior Resolution Check

- **Resolved:** Public `Ext` API. Review55-3 asked for `public final class Ext`, private
  constructor, and public static methods. The Java prompt now gives that exact class shape
  (`dev-docs/TautResExtP2-Java.md:20`-`32`).
- **Resolved:** `IllegalArgumentException` semantics. The Java prompt now requires band checking
  before decoding and `IllegalArgumentException` for both below-band tags and decoded non-map hosts
  (`dev-docs/TautResExtP2-Java.md:38`-`40`), matching the base brief's language-specific error
  requirement (`dev-docs/TautResExtP2-Base.md:52`-`70`).
- **Resolved:** Avoiding `mapEntries()` fallback. The Java prompt explicitly forbids using
  `mapEntries()` to turn scalar hosts into empty maps (`dev-docs/TautResExtP2-Java.md:39`-`40`).
  This matters because `Cbor.mapEntries()` returns `List.of()` for non-map values
  (`src/taut/gen/runtime/Cbor.java:34`-`40`).
- **Resolved:** Harness package placement. The prompt now states that the ResExt harness calling
  package-private generated `Host` / `Decision` APIs may declare `package taut`, matching the
  existing Java harness pattern, while keeping public `Ext` accessibility as a separate check
  (`dev-docs/TautResExtP2-Java.md:43`-`49`). This aligns with generated Java classes and
  `toCbor()` / `fromCbor()` methods being package-private (`src/taut/gen/java.py:84`-`118`).
- **Resolved:** Residual ownership. The Java prompt now scopes owned files to new `Ext.java` and
  `src/tests/test_java.py`, with `Cbor.java` and `java.py` verify-first and editable only for a real
  `residual_vectors.json` divergence (`dev-docs/TautResExtP2-Java.md:6`-`10`).
- **Still resolved from earlier passes:** Phase 1 artifacts and runtime slots are present. The base
  brief lists `ir/resext.taut.py`, both corpora, and the `ext.<lang>` runtime slot as landed
  (`dev-docs/TautResExtP2-Base.md:15`-`29`); `_RUNTIMES["java"]` includes `Ext.java`, and `emit()`
  skips missing runtime files until Phase 2 lands them (`src/taut/gen/scaffold.py:32`-`40`,
  `src/taut/gen/scaffold.py:600`-`607`).

## Dispatch Verdict

Dispatch Java Phase 2.

The brief is specific enough to prevent the known Java failure modes: package-private runtime API,
late band checking, scalar-host coercion through `mapEntries()`, and in-package-only API proof. The
remaining work is implementation and verification, not prompt repair.

## Verification Notes

- Read and compared:
  - `dev-docs/TautResExtPlan.md`
  - `dev-docs/TautResExtP2-Base.md`
  - `dev-docs/TautResExtP2-Java.md`
  - `dev-docs/TautResExtP2-Java-Review55-3.md`
  - `src/taut/gen/runtime/Cbor.java`
  - `src/taut/gen/java.py`
  - `src/taut/gen/scaffold.py`
  - `ir/resext.taut.py`
  - `corpus/residual_vectors.json`
  - `corpus/ext_vectors.json`
  - relevant ResExt / forward-compat / Java tests.
- Ran:
  - `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m pytest -q -p no:cacheprovider src/tests/test_resext_vectors.py src/tests/test_forward_compat.py src/tests/test_java.py`
  - Result: `21 passed in 0.04s`.
- Checked Java toolchain:
  - PATH `javac` / `java` are present.
  - `javac 21.0.10`; `openjdk version "21.0.10" 2026-01-20`.
- Generated `ir/resext.taut.py` to a temp directory with Java runtime and `--forward-compat`, then
  compiled emitted `api.java` + `Cbor.java` with PATH `javac`.
  - Result: generation and compile succeeded. `Ext.java` was not emitted because the Phase 2
    runtime file has not landed yet, which matches scaffold's skip-until-present behavior.
