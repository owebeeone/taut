# Taut Float Phase 2 JavaScript Response Plan

Source reviews:
- `dev-docs/TautFload2-Js-CodeReview48.md`
- `dev-docs/TautFload2-Js-CodeReview55.md`

## Summary

Both reviews approve the JavaScript float implementation. No CBOR parity, generator, or value-model
defects were found. CR48 adds stronger fuzz/decode evidence and confirms the double-rounding and
NaN traps are handled correctly.

The main remaining issue is test integration: the runtime byte-parity harness exists but is a
standalone Node command.

## Required Actions

1. Include the Node parity harness in the landed change.
   - File: `src/tests/js_float_parity.js`
   - Reason: it is the JavaScript runtime byte-parity gate over the 22 corpus rows.

2. Wire the Node harness into the normal Python test flow, if feasible.
   - Add a `pytest` test in `src/tests/test_js.py` that runs `node src/tests/js_float_parity.js`
     when `node` is present.
   - If Node is absent, skip cleanly.
   - This closes CR55's CI gap: `pytest src/tests` currently proves generator shape but not JS
     runtime bytes.

## Optional Cleanup

- Add a comment near `roundScaled` that current half-narrowing call sites always right-shift.
- Add a comment near `halfToNumber` that all half values are exactly representable in double, so
  the arithmetic widening is bit-exact.
- Leave module-global `DataView` scratch storage as-is; both reviews consider it safe for this
  runtime.

## Verification Plan

- `node src/tests/js_float_parity.js`.
- `PYTHONPATH=src python3 -m pytest src/tests/test_js.py -q` with a Python that has pytest.
- `PYTHONPATH=src python3 -m pytest src/tests -q`.

## Landing Checklist

- `git status --short` shows `src/tests/js_float_parity.js` as tracked/staged.
- If a pytest wrapper is added, confirm it skips cleanly when Node is unavailable.
- Commit `TautFload2-Js-CodeReview48.md`, `TautFload2-Js-CodeReview55.md`, and this response
  plan alongside the code as Phase 2 review artifacts.
