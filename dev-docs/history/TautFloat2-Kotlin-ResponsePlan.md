# Taut Float Phase 2 Kotlin Response Plan

Source reviews:
- `dev-docs/TautFload2-Kotlin-CodeReview48.md`
- `dev-docs/TautFload2-Kotlin-CodeReview55.md`

## Summary

Both reviews approve the Kotlin float implementation. CR55 could not run `kotlinc` locally, but
CR48 did compile and run the Kotlin runtime, the corpus harness, fuzz probes, and generated-code
roundtrips. No runtime, generator, or CBOR parity defects remain.

The one concrete improvement is making the in-repo parity test more reliable when `kotlinc` is
available but `java` on `PATH` is broken.

## Required Actions

1. Include the Kotlin parity harness in the landed change.
   - File: `src/tests/kotlin_float_parity.kt`
   - Reason: it is the compiled Kotlin corpus gate when `kotlinc` is available.

2. Harden `test_kotlin.py`'s JVM selection.
   - Current concern from CR48: the test may find `kotlinc` but then run a broken `java` from
     `PATH`.
   - Preferred behavior:
     - use `JAVA_HOME/bin/java` when `JAVA_HOME` is set;
     - otherwise try to infer the JBR/JDK adjacent to the discovered `kotlinc`;
     - otherwise fall back to `java` on `PATH`;
     - skip with a clear message if no usable JVM is found.

## Optional Cleanup

- Add a comment in `doubleToHalfBits` explaining that double subnormals flush to half zero only
  as a candidate, and the exactness check rejects the width when the original value is not zero.
- No action needed for CR55's old "kotlinc missing" gap; CR48 closed it out of band.

## Verification Plan

- `PYTHONPATH=src python3 -m pytest src/tests/test_kotlin.py -q` with a Python that has pytest.
- `PYTHONPATH=src python3 -m pytest src/tests -q`.
- When Kotlin is available, confirm the test compiles `src/taut/gen/runtime/cbor.kt` plus
  `src/tests/kotlin_float_parity.kt` and runs the jar with the selected JVM.

## Landing Checklist

- `git status --short` shows `src/tests/kotlin_float_parity.kt` as tracked/staged.
- If JVM-selection logic changes, verify it still skips cleanly on machines without Kotlin.
- Commit `TautFload2-Kotlin-CodeReview48.md`, `TautFload2-Kotlin-CodeReview55.md`, and this
  response plan alongside the code as Phase 2 review artifacts.
