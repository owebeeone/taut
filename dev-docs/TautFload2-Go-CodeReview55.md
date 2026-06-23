# Taut Float Phase 2 Go Code Review 55

## Findings

No correctness issues found in the uncommitted Go float implementation.

I did not find a CBOR parity bug, generator/runtime mismatch, missing Phase 2 surface, or Phase 2 brief violation in the reviewed changes. The runtime adds the required `KFloat` value model and separate `F float64` field (`src/taut/gen/runtime/cbor.go:23`, `src/taut/gen/runtime/cbor.go:40`), encodes NaN before width selection (`src/taut/gen/runtime/cbor.go:139`), preserves signed zero via bit-equality checks for half/single exactness (`src/taut/gen/runtime/cbor.go:144`, `src/taut/gen/runtime/cbor.go:149`), and decodes all three CBOR float widths (`src/taut/gen/runtime/cbor.go:320`, `src/taut/gen/runtime/cbor.go:323`, `src/taut/gen/runtime/cbor.go:329`). The Go generator maps `float` to `float64`, `CFloat(...)`, and `.Float()` as required (`src/taut/gen/go.py:19`, `src/taut/gen/go.py:40`, `src/taut/gen/go.py:53`), with Python shape coverage for scalar/list/map/optional float fields (`src/tests/test_go.py:40`).

## Residual Risks / Test Gaps

- The Go parity harness is present (`src/taut/gen/runtime/cbor_float_test.go:62`) and passes, but it is not runnable from the repo root with the default module-mode command `go test ./src/taut/gen/runtime` because this checkout has no root `go.mod`. It passes with `GO111MODULE=off go test ./src/taut/gen/runtime`. This is a test-invocation/documentation risk rather than a float implementation defect.
- The Python generator test is string-shape coverage, not a compiled generated-message roundtrip. It verifies the expected float type and codec calls (`src/tests/test_go.py:42` through `src/tests/test_go.py:50`), but no Go compiler check currently exercises a generated float-bearing message with the vendored runtime.
- The hand-rolled double-to-half path is high-risk by nature. The committed corpus exercises key boundaries and near misses, and the harness covers all 22 rows, but there is no exhaustive half-space or randomized cross-check against the Python oracle in this change.

## Commands Inspected / Ran

- Inspected briefs: `dev-docs/TautFloatP2-Base.md`, `dev-docs/TautFloatP2-Go.md`.
- Inspected diff/status: `git status --short`, `git diff --stat`, `git diff -- src/taut/gen/go.py src/taut/gen/runtime/cbor.go src/tests/test_go.py`.
- Inspected untracked harness: `nl -ba src/taut/gen/runtime/cbor_float_test.go`.
- `go test ./src/taut/gen/runtime` -> failed before tests: no main module/root `go.mod`.
- `GO111MODULE=off go test ./src/taut/gen/runtime` -> passed.
- `PYTHONPATH=src python3 -m pytest src/tests/test_go.py src/tests/test_float_vectors.py -q` -> failed because Homebrew Python 3.14 has no `pytest`.
- `PYTHONPATH=src python -m pytest src/tests/test_go.py src/tests/test_float_vectors.py -q` -> passed, 7 tests.
- `PYTHONPATH=src python -m pytest src/tests -q` -> passed, 166 tests.
