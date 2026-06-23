# Taut Float Phase 2 Java Code Review 55

## Findings

### [P2] Java parity harness is not included in the tracked diff

- Reference: `src/tests/java/FloatParity.java:1`
- Phase 2 requires `src/tests/test_java.py` plus a Java parity harness. The harness file exists and passes locally, but `git diff --stat` / `git diff --name-only` only show the three tracked file changes, while `git status --short` reports `?? src/tests/java/`. A patch made from the current tracked diff, or a commit made with `git add -u`, would omit the Java corpus gate and leave the runtime parity check outside version control.
- Impact: the Java runtime can regress on the 22-row float corpus without an in-repo Java harness to rerun, which violates the Phase 2 definition of done even though the current local file passes.

No confirmed Java runtime or generator correctness bugs were found in the tracked implementation. The reviewed runtime preserves `-0.0`, canonicalizes NaNs before width selection, accepts CBOR float widths 25/26/27, uses a direct double-to-half narrowing path, and the generated float scalar/list/map shapes compile against the updated runtime.

## Residual Risks / Test Gaps

- `src/tests/java/FloatParity.java` exercises all 22 preferred corpus rows, but the corpus does not explicitly include non-preferred single/double NaN encodings decoded through the width-lenient path and re-encoded to canonical `F9 7E00`.
- The committed Python shape test is string-based. I separately compiled a generated float-bearing Java API against `Cbor.java`, but there is no committed automated `javac` gate for generated float API code.
- The default Homebrew `python3` on this machine does not have `pytest`; the Python checks were run with the asdf Python 3.10.15 environment.

## Commands Inspected / Run

- `sed -n '1,240p' dev-docs/TautFloatP2-Base.md`
- `sed -n '1,260p' dev-docs/TautFloatP2-Java.md`
- `git diff --stat && git diff --name-only`
- `git diff -- src/taut/gen/runtime/Cbor.java`
- `git diff -- src/taut/gen/java.py`
- `git diff -- src/tests/test_java.py`
- `find src/tests/java -maxdepth 3 -type f -print -exec sed -n '1,260p' {} \;`
- `git diff --check` -> passed
- `PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -p no:cacheprovider src/tests/test_java.py -q` -> failed because `/opt/homebrew/opt/python@3.14/bin/python3.14` has no `pytest`
- `PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 /Users/owebeeone/.asdf/shims/python -m pytest -p no:cacheprovider src/tests/test_java.py -q` -> `4 passed`
- `PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 /Users/owebeeone/.asdf/shims/python -m pytest -p no:cacheprovider src/tests -q` -> `166 passed`
- `tmpdir=$(mktemp -d /tmp/taut-java-float.XXXXXX); javac -d "$tmpdir" src/taut/gen/runtime/Cbor.java src/tests/java/FloatParity.java && java -cp "$tmpdir" taut.FloatParity corpus/float_vectors.json; rc=$?; rm -rf "$tmpdir"; exit $rc` -> `ok 22 float vectors`
- Temporary generated-float-API compile against `src/taut/gen/runtime/Cbor.java` in `/tmp` -> passed
