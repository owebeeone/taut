# Taut Float Phase 2 Rust Response Plan

Source reviews:
- `dev-docs/TautFload2-Rust-CodeReview48.md`
- `dev-docs/TautFload2-Rust-CodeReview55.md`

## Summary

Both reviews approve the Rust float implementation. No runtime, narrowing, decode, or generator
correctness issues were found. CR48 extends CR55 with broader encode fuzzing, exhaustive half
decode checks, and an out-of-band generated-struct compile/roundtrip.

The only required fix is packaging the Rust test file.

## Required Actions

1. Include the Rust test file in the landed change.
   - File: `src/tests/test_rust.py`
   - Reason: both reviews flag it as untracked. Without it, Phase 2 loses the Python shape test
     and the `rustc --test` corpus parity harness.

## Optional Cleanup

- Decoder truncation currently panics on malformed float payload lengths, matching the minimal
  style of the existing decoder. Do not change this for Phase 2 unless doing a broader decoder
  hardening pass.
- Leave arithmetic half widening as-is; CR48 proves it is exact for all half payloads.
- Avoid reflow-only churn in any follow-up edits unless the file is already being touched for a
  substantive reason.
- Consider promoting CR48's generated float-bearing Rust struct compile/roundtrip into a future
  test if generated-code compile coverage becomes part of the gate.

## Verification Plan

- `PYTHONPATH=src python3 -m pytest src/tests/test_rust.py src/tests/test_regen.py -q` with a
  Python that has pytest.
- `PYTHONPATH=src python3 -m pytest src/tests -q`.
- Confirm `src/tests/test_rust.py` invokes `rustc --test` when `rustc` is present and skips
  cleanly otherwise.

## Landing Checklist

- `git status --short` shows `src/tests/test_rust.py` as tracked/staged.
- Confirm no new dependency such as the `half` crate appears anywhere in the runtime.
- Commit `TautFload2-Rust-CodeReview48.md`, `TautFload2-Rust-CodeReview55.md`, and this
  response plan alongside the code as Phase 2 review artifacts.
