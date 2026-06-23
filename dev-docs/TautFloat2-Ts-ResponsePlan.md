# Taut Float Phase 2 TypeScript Response Plan

Source reviews:
- `dev-docs/TautFload2-Ts-CodeReview48.md`
- `dev-docs/TautFload2-Ts-CodeReview55.md`

Implementation repo:
- `/Users/owebeeone/limbo/glial-dev/trial`

## Summary

Both reviews approve the TypeScript runtime float codec. No CBOR byte-parity defect was found in
`ts/src/cbor.ts` or the scalar coercion behavior in `ts/src/codec.ts`. CR48 adds strong
differential fuzzing and confirms recursive codec paths behave correctly at runtime.

There is one real follow-up: the public TypeScript schema model still excludes scalar `"float"`.

## Required Actions

1. Update the TypeScript schema type surface.
   - File: `/Users/owebeeone/limbo/glial-dev/trial/ts/src/schema.ts`
   - Change `TypeRef` scalar union from `"int" | "str" | "bytes" | "bool"` to
     `"int" | "str" | "bytes" | "bool" | "float"`.
   - Reason: without this, `codec.ts`'s `t.scalar === "float"` branch is outside the declared
     type model, and callers cannot construct a float `TypeRef` without a cast.

2. Remove the float test's `as never` escape hatch.
   - File: `/Users/owebeeone/limbo/glial-dev/trial/ts/test/float.test.ts`
   - After `schema.ts` admits `"float"`, the inline float schema should type without a cast.
   - This must be verified with TypeScript type checking; `node --experimental-strip-types`
     strips types and will not prove the fix.

3. Include the copied oracle fixture and test in the landed change.
   - Files:
     - `/Users/owebeeone/limbo/glial-dev/trial/ts/test/float.test.ts`
     - `/Users/owebeeone/limbo/glial-dev/trial/ts/test/float_vectors.json`
   - Reason: both review passes note these are untracked in the implementation repo.

4. Add direct test coverage for the gaps CR55 identified.
   - Width-lenient decode: assert `f93c00`, `fa3f800000`, and `fb3ff0000000000000` all decode
     as `CborFloat(1.0)` and re-encode to the preferred half form.
   - Recursive scalar positions: cover `list<float>` and `map<int,float>`.
   - Bool coercion: cover `true -> 1.0` and `false -> 0.0` at a float scalar boundary.

## Optional Cleanup

- In `doubleToHalfBits`, the NaN subcase is dead because `pushShortestFloat` filters NaN first.
  A comment or simplification is optional; do not change behavior.
- No package dependency changes are needed. Continue using `node --experimental-strip-types` for
  runtime tests unless the project adopts a full TypeScript type-check gate.

## Verification Plan

- From `/Users/owebeeone/limbo/glial-dev/trial/ts`:
  - `node --experimental-strip-types --test test/float.test.ts`
  - `node --experimental-strip-types --test test/corpus.test.ts test/glade_corpus.test.ts test/forward_compat.test.ts test/float.test.ts test/interop_rust.test.ts`
- Run `npm test` if the Python server dependency is available; otherwise record any existing
  interop environment failure separately from float.
- If `tsc` is available, run a focused type-check or probe that constructs a float `TypeRef`
  without a cast.
- If `tsc` is not installed locally, use `npx -p typescript@5 tsc --noEmit --strict` on a focused
  probe that imports the real `ts/src/schema.ts` and constructs a `{ k: "scalar", scalar:
  "float" }` `TypeRef`. The probe must pass without `as never` or other escape hatches.

## Landing Checklist

- `git -C /Users/owebeeone/limbo/glial-dev/trial status --short` shows the float test and
  fixture as tracked/staged.
- Commit `TautFload2-Ts-CodeReview48.md`, `TautFload2-Ts-CodeReview55.md`, and this response
  plan in `taut-ts` alongside the code/review set as Phase 2 review artifacts.
