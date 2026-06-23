# Taut Float Phase 2 Java Response Plan

Source reviews:
- `dev-docs/TautFload2-Java-CodeReview48.md`
- `dev-docs/TautFload2-Java-CodeReview55.md`

## Summary

Both reviews approve the Java float implementation. No constructor-ripple, runtime, generator, or
CBOR byte-parity bugs were found. CR48 independently stress-tested the narrowing and compiled a
generated float-bearing API out of band.

The one required fix is packaging the Java parity harness.

## Required Actions

1. Include the Java parity harness in the landed change.
   - File: `src/tests/java/FloatParity.java`
   - Reason: both reviews flag `src/tests/java/` as untracked. Without this file, the compiled
     22-vector Java runtime gate is not versioned.

2. Keep `test_java.py` focused, but make its limitation explicit.
   - Current committed coverage is shape-based; CR48 separately proved generated float API code
     compiles and round-trips.
   - Either leave this as an accepted Phase 2 limitation or add a `javac`-gated generated API
     compile smoke test in `src/tests/test_java.py`.

## Optional Cleanup

- Add a short comment documenting the safe shift bounds in `roundRight`.
- Add a short comment that `doubleToHalfBits` uses raw bits only after `encFloat` has filtered
  NaN.
- Leave `List<Byte>` boxing alone; it is pre-existing and out of scope.

## Verification Plan

- Compile and run the harness:
  `tmpdir=$(mktemp -d); "$JAVA_HOME/bin/javac" -d "$tmpdir" src/taut/gen/runtime/Cbor.java src/tests/java/FloatParity.java && "$JAVA_HOME/bin/java" -cp "$tmpdir" taut.FloatParity corpus/float_vectors.json`
  - On this machine CR48 used:
    `JAVA_HOME="/Applications/Android Studio.app/Contents/jbr/Contents/Home"`.
  - Do not assume bare `java`/`javac` on `PATH` are usable here; they may be broken shims.
- `PYTHONPATH=src python3 -m pytest src/tests/test_java.py -q` with a Python that has pytest.
- `PYTHONPATH=src python3 -m pytest src/tests -q`.

## Landing Checklist

- `git status --short` shows `src/tests/java/FloatParity.java` as tracked/staged.
- Confirm no constructor call sites were left with the old arity after any rebasing.
- Commit `TautFload2-Java-CodeReview48.md`, `TautFload2-Java-CodeReview55.md`, and this
  response plan alongside the code as Phase 2 review artifacts.
