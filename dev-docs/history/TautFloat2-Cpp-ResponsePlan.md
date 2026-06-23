# Taut Float Phase 2 C++ Response Plan

Source reviews:
- `dev-docs/TautFload2-Cpp-CodeReview48.md`
- `dev-docs/TautFload2-Cpp-CodeReview55.md`

## Summary

Both reviews approve the C++ float implementation. No runtime CBOR parity bugs were found in
`Buf::float_`, major-7 decode, NaN canonicalization, signed-zero preservation, or residual
re-emission. CR48 substantially strengthens the evidence with corpus parity, constexpr static
asserts, and broad differential fuzz.

The open work is test packaging plus a decision about how to represent generated native
`std::map` fields in compile-time tests.

## Required Actions

1. Include the C++ test file in the landed change.
   - File: `src/tests/test_cpp.py`
   - Reason: both reviews flag it as untracked. If it is omitted, Phase 2 loses the C++20
     static-assert corpus gate.

2. Clarify the `Map(INT, FLOAT)` test coverage.
   - The current test string-checks `std::map<long long, double>` and `b.float_(v)`, but does
     not compile that generated map path under C++20.
   - Treat this as a pre-existing `std::map` plus `constexpr` standard-library limitation, not
     a float runtime defect.
   - Adjust `test_cpp.py` so scalar/list float compile coverage is explicit, and map coverage is
     either:
     - documented as string-shape-only, or
     - compiled behind a probe that first proves the generated `std::map` constexpr function
       definition works under the available C++23 compiler and standard library.

3. Preserve the C++20 runtime requirement.
   - Keep the main float static-assert harness at `-std=c++20`; it validates the actual Phase 2
     runtime requirement.
   - Any constexpr-map check should be optional and gated by a compile probe, not by the
     language mode alone.

## Optional Cleanup

- Leave `Buf` bounds checking and the `narrow_half` fast-overflow reject unchanged for Phase 2.
  Both reviews classify these as pre-existing or explanatory nits, not defects.
- Add a short comment if desired that the `65504..65520` half-overflow region intentionally falls
  through unless the original value is exactly representable.

## Verification Plan

- `PYTHONPATH=src python3 -m pytest src/tests/test_cpp.py -q` with a Python that has pytest.
- `PYTHONPATH=src python3 -m pytest src/tests -q`.
- Confirm the generated scalar/list float C++20 static-assert harness compiles.
- If adding the optional map test, first compile a small generated-map probe under `-std=c++23`;
  run the generated map compile only when that probe passes. Keep C++20 as the main runtime
  static-assert target.

## Landing Checklist

- `git status --short` shows `src/tests/test_cpp.py` as tracked/staged.
- Commit `dev-docs/TautFload2-Cpp-CodeReview48.md`,
  `dev-docs/TautFload2-Cpp-CodeReview55.md`, and this response plan alongside the code as
  Phase 2 review artifacts.
