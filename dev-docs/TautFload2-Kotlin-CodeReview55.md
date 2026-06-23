# Taut Float Phase 2 Kotlin Code Review 55

## Findings

No correctness findings found in the uncommitted Kotlin float implementation.

I did not find CBOR parity bugs, generator/runtime mismatches, or Phase 2 scope violations in the reviewed diff. The runtime value model adds the required separate `Double` slot and float factory/accessor at `src/taut/gen/runtime/cbor.kt:14`, `src/taut/gen/runtime/cbor.kt:19`, `src/taut/gen/runtime/cbor.kt:24`, and `src/taut/gen/runtime/cbor.kt:39`. Encoding routes `Cbor.FLOAT` through shortest-form float encoding at `src/taut/gen/runtime/cbor.kt:158`, with NaN canonicalized before width tests at `src/taut/gen/runtime/cbor.kt:123`-`src/taut/gen/runtime/cbor.kt:126`, direct double-to-half narrowing at `src/taut/gen/runtime/cbor.kt:78`-`src/taut/gen/runtime/cbor.kt:100`, and bit-exact half/single checks at `src/taut/gen/runtime/cbor.kt:127`-`src/taut/gen/runtime/cbor.kt:134`. Decode accepts CBOR float widths 25/26/27 at `src/taut/gen/runtime/cbor.kt:202`-`src/taut/gen/runtime/cbor.kt:211`. The generator maps `float` to `Double`, `0.0`, `Cbor.float(...)`, and `.floatVal` at `src/taut/gen/kotlin.py:29`-`src/taut/gen/kotlin.py:77`.

## Residual Risks / Test Gaps

- Kotlin compile/runtime parity was not executed in this environment because `kotlinc` is not on `PATH`. The Python test that would compile and run `src/tests/kotlin_float_parity.kt` is present at `src/tests/test_kotlin.py:57`-`src/tests/test_kotlin.py:74`, but it skipped locally.
- The generated Kotlin float shape is covered by string assertions at `src/tests/test_kotlin.py:41`-`src/tests/test_kotlin.py:54`; without `kotlinc`, I could not compile a generated Kotlin schema containing float fields.
- The parity harness mirrors all 22 current `corpus/float_vectors.json` rows in `src/tests/kotlin_float_parity.kt:5`-`src/tests/kotlin_float_parity.kt:28`. That is adequate for the locked Phase 2 corpus, but it will not automatically track future corpus edits.

## Commands Inspected Or Run

- Read briefs: `sed -n '1,240p' dev-docs/TautFloatP2-Base.md`; `sed -n '1,260p' dev-docs/TautFloatP2-Kotlin.md`.
- Inspected diff/status: `git status --short`; `git diff --stat`; `git diff -- src/taut/gen/runtime/cbor.kt`; `git diff -- src/taut/gen/kotlin.py src/tests/test_kotlin.py src/tests/kotlin_float_parity.kt`; numbered `nl -ba` reads of changed files.
- Hygiene: `git diff --check` passed.
- Attempted brief command with module form: `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m pytest -p no:cacheprovider src/tests/test_kotlin.py -q` failed because this `python3` does not have `pytest` installed.
- Kotlin-specific Python tests: `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src pytest -p no:cacheprovider src/tests/test_kotlin.py -q` -> `4 passed, 1 skipped`; skipped item was the `kotlinc` parity harness.
- Full Python suite: `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src pytest -p no:cacheprovider src/tests -q` -> `166 passed, 1 skipped`.
- Python oracle sanity check: `PYTHONPATH=src python3` against `corpus/float_vectors.json` and `taut.wire.cbor.dumps` checked all 22 rows.
- Algorithm sanity check: a Python translation of the Kotlin half/single selection logic matched the Python oracle over 200,013 float samples. This is not a substitute for compiling the Kotlin runtime.
