# Taut Float Phase 2 Swift Code Review 55

## Findings

No correctness findings.

I did not identify any Phase 2 blocking issues in the uncommitted Swift float changes. The runtime adds `Cbor.float(Double)` and `floatVal` at `src/taut/gen/runtime/cbor.swift:7-24`, canonicalizes NaN before width selection at `src/taut/gen/runtime/cbor.swift:60-65`, tries half, single, then double in shortest-form order at `src/taut/gen/runtime/cbor.swift:67-82`, and decodes major-7 float widths 25/26/27 at `src/taut/gen/runtime/cbor.swift:145-155`. The generator maps `float` to `Double`, `0.0`, `Cbor.float(...)`, and `.floatVal` at `src/taut/gen/swift.py:26-80`. The added tests cover float codegen shape and a compiled runtime corpus harness at `src/tests/test_swift.py:52-144`.

## Residual Risks / Test Gaps

- The Swift corpus harness compiles the vendored runtime plus an ad hoc top-level program, but it does not compile a generated Swift model containing float fields. The shape test checks the emitted fragments, but an end-to-end generated-message compile would catch integration drift across optional fields, lists, maps, and initializers.
- Verification was performed on Apple Swift 6.3.1 for arm64 macOS. The implementation intentionally depends on native `Float16`, as allowed by the Swift brief; older or different Swift toolchains remain covered only by their own compile result.
- The runtime decoder keeps the existing minimal codec style and does not add malformed or truncated CBOR payload tests for the new float payload lengths. This is not a Phase 2 parity failure, but it remains outside the current coverage.

## Commands Inspected / Ran

- Read `dev-docs/TautFloatP2-Base.md` and `dev-docs/TautFloatP2-Swift.md`.
- Inspected `git diff -- src/taut/gen/runtime/cbor.swift src/taut/gen/swift.py src/tests/test_swift.py`.
- `git diff --check` passed.
- `which swiftc` -> `/usr/bin/swiftc`.
- `swiftc --version` -> Apple Swift 6.3.1, target `arm64-apple-macosx26.0`.
- `PYTHONPATH=src python3 -m pytest src/tests/test_swift.py -q` did not run tests because the active `python3` environment has no `pytest` module.
- `env PYTHONPATH=src uvx --from pytest pytest src/tests/test_swift.py -q` passed: 6 tests.
- `env PYTHONPATH=src uvx --from pytest pytest src/tests/test_float_vectors.py src/tests/test_float.py src/tests/test_cbor.py -q` passed: 24 tests.
- `env PYTHONPATH=src uvx --from pytest pytest src/tests -q` passed: 167 tests.
- A manual temporary Swift harness compiled `src/taut/gen/runtime/cbor.swift`, loaded all 22 rows from `corpus/float_vectors.json`, and verified encode, re-encode, and non-NaN decode bit parity. It passed all 22 rows.
