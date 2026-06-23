# Taut Float Phase 2 Go Response Plan

Source reviews:
- `dev-docs/TautFload2-Go-CodeReview48.md`
- `dev-docs/TautFload2-Go-CodeReview55.md`

## Summary

Both reviews approve the Go float implementation. No runtime, value-model, generator, or CBOR
parity defects were found. CR48 closes the main CR55 confidence gaps with extensive differential
fuzz and an out-of-band compiled generated-message roundtrip.

The remaining work is making sure the harness lands and deciding how much of the out-of-band
verification should become an in-repo gate.

## Required Actions

1. Include the Go parity harness in the landed change.
   - File: `src/taut/gen/runtime/cbor_float_test.go`
   - Reason: it is the Go runtime byte-parity gate over `corpus/float_vectors.json`.

2. Document or encode the correct Go test invocation.
   - Root `go test ./src/taut/gen/runtime` fails because this repo has no root `go.mod`.
   - The working invocation is `GO111MODULE=off go test ./src/taut/gen/runtime`.
   - Add a Python-side gated test in `src/tests/test_go.py` that runs this exact command when
     `go` is present and skips cleanly otherwise.
   - Do not settle for documentation-only; otherwise the byte-parity harness exists but never
     becomes an in-repo gate.

## Optional Cleanup

- Add a short comment in `float64ToHalfBits` explaining that NaN is pre-filtered by `floatBytes`.
  CR48 notes the internal NaN branch is harmless but slightly surprising.
- Leave `roundShiftEven`'s defensive `shift == 0` guard as-is unless touching the helper for a
  comment; it is dead from current call sites but not incorrect.
- Consider promoting CR48's generated `FloatMsg` compile/roundtrip into a future test if Go
  generated-code integration becomes a gate.

## Verification Plan

- `GO111MODULE=off go test ./src/taut/gen/runtime`.
- `PYTHONPATH=src python3 -m pytest src/tests/test_go.py src/tests/test_float_vectors.py -q`
  with a Python that has pytest.
- `PYTHONPATH=src python3 -m pytest src/tests -q`.

## Landing Checklist

- `git status --short` shows `src/taut/gen/runtime/cbor_float_test.go` as tracked/staged.
- Do not add external dependencies or module files just for this harness.
- Commit `TautFload2-Go-CodeReview48.md`, `TautFload2-Go-CodeReview55.md`, and this response
  plan alongside the code as Phase 2 review artifacts.
