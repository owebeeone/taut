# Findings

## P2 - `TypeRef` still excludes `float`, leaving the TS schema boundary type-incomplete

References:
- `/Users/owebeeone/limbo/glial-dev/trial/ts/src/schema.ts:5`
- `/Users/owebeeone/limbo/glial-dev/trial/ts/src/codec.ts:16`
- `/Users/owebeeone/limbo/glial-dev/trial/ts/test/float.test.ts:22`

`codec.ts` now correctly looks for `t.scalar === "float"` and wraps values in `CborFloat`, but the exported `TypeRef` definition in `schema.ts` still narrows scalar kinds to `"int" | "str" | "bytes" | "bool"`. That means the new float branch is outside the package's declared TS schema surface: callers cannot construct a float `TypeRef` without a cast, and a real TypeScript checker would flag the comparison as a no-overlap branch. The new float test confirms this by casting its inline schema `as never`, which masks the gap rather than exercising the public type shape.

Runtime JSON-loaded schemas still work because `loadSchema` casts from `unknown`, and the CBOR bytes match the oracle in the commands below. The issue is at the TypeScript codec boundary: Phase 2 asks TS to support scalar kind `float`, but the public schema model still says that scalar cannot exist. If the corrected TS brief intentionally keeps `schema.ts` out of scope, this needs an explicit follow-up or exception; otherwise the TypeRef scalar union should include `"float"` and the test should not need the `as never` escape hatch.

## P3 - Width-lenient float decode is implemented but not directly tested with non-preferred widths

References:
- `/Users/owebeeone/limbo/glial-dev/trial/ts/src/cbor.ts:271`
- `/Users/owebeeone/limbo/glial-dev/trial/ts/test/float.test.ts:68`

The decoder has arms for half/single/double (`info` 25/26/27), but the new oracle test only decodes each value from its preferred shortest-form vector. That verifies corpus parity, but it does not directly pin the Phase 2 rule that decode accepts all three widths even when the encoder would choose a shorter one, for example `f93c00`, `fa3f800000`, and `fb3ff0000000000000` all decoding to the same logical float. This is a test gap, not an observed implementation bug.

## P3 - Schema-level tests cover only a top-level float field and int coercion

References:
- `/Users/owebeeone/limbo/glial-dev/trial/ts/test/float.test.ts:82`

The schema test proves a top-level float field unwraps to a native number and that `{ f: 1 }` encodes as a float, but it does not cover recursive scalar positions such as `list<float>` or `map<int, float>`, and it does not cover the brief's bool coercion case (`Number(true) -> 1.0`, `Number(false) -> 0.0`). The implementation appears to recurse through these paths correctly by inspection, but the Python reference has explicit coverage for list/map float values and bool-to-float coercion, so TS currently has a parity coverage gap.

# Repo State Notes

- `/Users/owebeeone/limbo/glial-dev/trial/ts/test/float.test.ts` and `/Users/owebeeone/limbo/glial-dev/trial/ts/test/float_vectors.json` are currently untracked (`git status --short`). They need to be included with the implementation for the copied oracle fixture and Phase 2 tests to land.
- No CBOR byte-parity bug was found in the changed float encoder/decoder. The implementation matched taut's `corpus/float_vectors.json`, and an extra Python-oracle probe over 2,012 raw f64 bit patterns reported zero mismatches.

# Commands Inspected Or Ran

- Read `/Users/owebeeone/limbo/taut-dev-cross/taut-ts/dev-docs/TautFloatP2-Base.md`.
- Read `/Users/owebeeone/limbo/taut-dev-cross/taut-ts/dev-docs/TautFloatP2-Ts.md`.
- Inspected `git -C /Users/owebeeone/limbo/glial-dev/trial status --short`.
- Inspected `git -C /Users/owebeeone/limbo/glial-dev/trial diff --stat`.
- Inspected `git -C /Users/owebeeone/limbo/glial-dev/trial diff -- ts/src/cbor.ts`.
- Inspected `git -C /Users/owebeeone/limbo/glial-dev/trial diff -- ts/src/codec.ts`.
- Read `/Users/owebeeone/limbo/glial-dev/trial/ts/test/float.test.ts`.
- Read `/Users/owebeeone/limbo/glial-dev/trial/ts/test/float_vectors.json`.
- Compared `/Users/owebeeone/limbo/taut-dev-cross/taut-ts/corpus/float_vectors.json` to `/Users/owebeeone/limbo/glial-dev/trial/ts/test/float_vectors.json`; no diff.
- Ran `npm test` in `/Users/owebeeone/limbo/glial-dev/trial/ts`: failed because `test/interop.test.ts` could not start the Python server (`server did not start`); float tests and other earlier tests passed before that hook failure.
- Ran `node --experimental-strip-types --test test/float.test.ts` in `/Users/owebeeone/limbo/glial-dev/trial/ts`: passed, 2/2.
- Ran `node --experimental-strip-types --test test/corpus.test.ts test/glade_corpus.test.ts test/forward_compat.test.ts test/float.test.ts test/interop_rust.test.ts` in `/Users/owebeeone/limbo/glial-dev/trial/ts`: passed, 13/13.
- Ran an additional `node --experimental-strip-types --input-type=module` probe that compared TS `CborFloat` encoding with taut Python `taut.wire.cbor.dumps` for 2,012 raw f64 bit patterns: passed, 0 mismatches.
- Ran `tsc --version`: `tsc` is not installed in this environment, so the `TypeRef` issue above is by source inspection rather than a local compiler run.
