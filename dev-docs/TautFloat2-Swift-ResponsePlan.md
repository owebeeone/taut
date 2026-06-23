# Taut Float Phase 2 Swift Response Plan

Source reviews:
- `dev-docs/TautFload2-Swift-CodeReview48.md`
- `dev-docs/TautFload2-Swift-CodeReview55.md`

## Summary

Both reviews approve the Swift float implementation. No CBOR parity, generator, or value-model
defects were found. CR48 adds broad differential fuzzing, double-rounding witness coverage, and an
out-of-band generated-model compile/roundtrip.

The remaining work is to promote the generated-model compile/roundtrip proof into an in-repo
follow-up test, plus a small portability comment for native `Float16`.

## Required Actions

1. Add an in-repo generated Swift model compile/roundtrip test.
   - Reason: both reviews identify this as the only real coverage gap. CR48 proved it out of
     band; the plan should make it a follow-up gate rather than leave it as optional cleanup.
   - Scope: generated model with scalar `FLOAT`, optional `FLOAT`, `List(FLOAT)`, `Map(INT,
     FLOAT)`, and a transient/default float if convenient.
   - Expected behavior: compile with `swiftc`, encode/decode/encode byte-stable, and preserve
     `-0.0` bits through at least one generated field.
   - This is still Phase 3.2-adjacent rather than a runtime blocker; do not alter the proven
     runtime float narrowing/encode path to add this test.

2. Add a short portability comment for native `Float16`.
   - Suggested location: near `encFloat` or the first `Float16` use in
     `src/taut/gen/runtime/cbor.swift`.
   - Message: this runtime requires native `Float16`; older Swift targets without it need a
     hand-rolled half narrower.
   - Reason: CR48 and CR55 both note the dependency is sanctioned by the brief but should be
     visible to future porters.

## Optional Cleanup

- Leave malformed/truncated float payload checks out of scope; the decoder follows the existing
  minimal trusted-input style.
- No action needed on map count style; it is pre-existing and not float-related.

## Verification Plan

- `PYTHONPATH=src python3 -m pytest src/tests/test_swift.py -q` with a Python that has pytest.
- `PYTHONPATH=src python3 -m pytest src/tests -q`.
- Confirm `swiftc` is present and that the corpus harness in `test_swift.py` runs rather than
  skips on the landing machine.

## Landing Checklist

- Confirm no untracked Swift test files are required; current Swift edits are in tracked files
  plus review docs.
- If adding the portability comment, keep it short and do not change runtime behavior.
- Commit `TautFload2-Swift-CodeReview48.md`, `TautFload2-Swift-CodeReview55.md`, and this
  response plan alongside the code as Phase 2 review artifacts.
