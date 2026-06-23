# Taut ResExt Phase 2 TypeScript Prompt Review - Fourth Pass

## Findings

### P0 - TS dispatch is still blocked on the external checkout decision, but the prompt now states that blocker correctly

References:
- `dev-docs/TautResExtPlan.md:68`
- `dev-docs/TautResExtPlan.md:69`
- `dev-docs/TautResExtP2-Ts.md:1`
- `dev-docs/TautResExtP2-Ts.md:3`
- `dev-docs/TautResExtP2-Ts.md:8`
- `dev-docs/TautResExtP2-Ts.md:14`
- `/Users/owebeeone/limbo/glial-dev/trial/ts/package.json:1`
- `/Users/owebeeone/limbo/glial-dev/trial/ts/package.json:8`

The Review55-3 repo-location resolution has been folded into the prompt as an explicit pre-dispatch blocker. That is the right prompt shape: `/Users/owebeeone/limbo/taut-dev-cross/trial/ts` is still absent, `/Users/owebeeone/limbo/taut-dev-cross/trial` contains only `cpp` and `rs`, and `/Users/owebeeone/limbo/taut-dev-cross/ts` contains only an empty `test` directory. The only actual TS package I found remains `/Users/owebeeone/limbo/glial-dev/trial/ts`, with `package.json`, `src/cbor.ts`, `src/codec.ts`, and `src/schema.ts`.

This is no longer a prompt ambiguity, but it is still a dispatch blocker. A TypeScript implementer cannot start from the requested workspace-local checkout until the owner either provisions `/Users/owebeeone/limbo/taut-dev-cross/trial/ts` or explicitly accepts `/Users/owebeeone/limbo/glial-dev/trial/ts` as the target despite its dirty FLOAT baseline.

## Proposed Resolutions

1. **Resolve the TS checkout precondition before assignment**
   - **Resolution:** Either create/provide `/Users/owebeeone/limbo/taut-dev-cross/trial/ts`, or explicitly approve `/Users/owebeeone/limbo/glial-dev/trial/ts` as the ResExt target.
   - **Verification:** Before implementation starts, record `git -C /Users/owebeeone/limbo/glial-dev/trial status --short` if the historical package is used. The current baseline is:

```text
 M ts/src/cbor.ts
 M ts/src/codec.ts
M  ts/src/schema.ts
A  ts/test/float.test.ts
A  ts/test/float_vectors.json
```

No additional prompt edits are required for the Review55-3 issues I checked.

## Prior Resolution Check

- **Actual TS checkout path:** resolved in prompt wording, externally unresolved. The prompt now correctly says the expected workspace-local `trial/ts` package is absent and names the historical fallback path. This is implementation-ready only after owner approval/provisioning.
- **Schema JSON handoff:** resolved. `dev-docs/TautResExtP2-Ts.md:30` through `dev-docs/TautResExtP2-Ts.md:38` now gives a concrete copy/export workflow to `test/resext.ir.json` using `taut.ir.export.export_to`; `src/taut/ir/export.py:78` supports that command.
- **Structural CBOR bridge vs byte-string storage:** resolved. `dev-docs/TautResExtP2-Ts.md:51` through `dev-docs/TautResExtP2-Ts.md:69` now requires decoding `encodeRef(...)` bytes into a nested `CborValue` map before `extSet`, and re-encoding the returned structural value before `decodeRef`. It also requires a test that fails if a `Uint8Array` byte string is stored at the band tag.
- **Focused test/typecheck commands:** resolved. `dev-docs/TautResExtP2-Ts.md:76` through `dev-docs/TautResExtP2-Ts.md:81` now pins `node --experimental-strip-types --test test/resext.test.ts`, asks for any existing TypeScript check only if available, and separates known full `npm test` status from the Phase 2 gate.
- **FLOAT dirty-state baseline:** resolved in prompt wording. `dev-docs/TautResExtP2-Ts.md:8` through `dev-docs/TautResExtP2-Ts.md:14` and `dev-docs/TautResExtP2-Ts.md:25` through `dev-docs/TautResExtP2-Ts.md:28` explicitly warn not to overwrite or normalize dirty FLOAT work and require recording the pre-ResExt status.
- **Taut-side oracle artifacts:** still good. `ir/resext.taut.py`, `corpus/residual_vectors.json`, `corpus/ext_vectors.json`, and `src/tests/test_resext_vectors.py` are present. The fixture has `Host`, `Decision`, and extension tag `1048577`.

## Dispatch Verdict

**Conditional no-go for immediate TS dispatch.** The prompt itself is now implementation-ready after Review55-3, but the task must not be handed to a TypeScript implementer until the TS package target is confirmed. Once the owner approves the historical package or provisions the workspace-local package, this prompt is ready to run.

Residual risk/test gaps after that precondition:
- The deterministic TS fuzz remains a new test implementation responsibility, not pre-proven by this review.
- The historical TS package has no checked-in `tsconfig.json` or package typecheck script today, so the focused Node test is the only concrete TS gate unless the package gains one.
- Full `npm test` in the historical package still has unrelated Python interop-server failures; the prompt correctly keeps that out of the Phase 2 gate.

## Verification Notes

- Read `dev-docs/TautResExtPlan.md`, `dev-docs/TautResExtP2-Base.md`, `dev-docs/TautResExtP2-Ts.md`, and `dev-docs/TautResExtP2-Ts-Review55-3.md`.
- Inspected `ir/resext.taut.py`, `corpus/residual_vectors.json`, `corpus/ext_vectors.json`, `src/taut/corpus/resext_build.py`, `src/taut/ir/export.py`, and `src/tests/test_resext_vectors.py`.
- Inspected `/Users/owebeeone/limbo/glial-dev/trial/ts/package.json`, `src/cbor.ts`, `src/codec.ts`, and `src/schema.ts`.
- Verified `/Users/owebeeone/limbo/taut-dev-cross/trial/ts` is missing and `/Users/owebeeone/limbo/glial-dev/trial/ts` is the only found TS package relevant to this prompt.
- Ran `PYTHONPATH=src pytest src/tests/test_resext_vectors.py -q` in `taut-ts`: 7 passed.
- Ran `PYTHONPATH=src python - <<'PY' ... schema_json(load_schema("ir/resext.taut.py")) ... PY` in `taut-ts`: exported schema data contains messages `Host`, `Decision` and extension `Decision` at tag `1048577`.
- Ran `node --experimental-strip-types --test test/forward_compat.test.ts` in the historical TS package: 1 passed.
- Ran `npm test` in the historical TS package: 15 passed, 5 failed, all from `test/interop.test.ts` because the Python server did not start.
