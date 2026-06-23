# Taut ResExt Phase 2 TypeScript Prompt Review

## Findings

### P0 - The prompt's `trial/ts` location is not valid in this cross-worktree checkout

References:
- `dev-docs/TautResExtP2-Ts.md:1`
- `dev-docs/TautResExtP2-Ts.md:3`
- `dev-docs/TautResExtP2-Ts.md:11`
- `dev-docs/TautResExtPlan.md:65`
- `dev-docs/TautResExtPlan.md:86`

The TypeScript prompt says Phase 2 runs in `trial/ts/src/*`, with owned files under `trial/ts`. In the requested workspace, `/Users/owebeeone/limbo/taut-dev-cross/trial` exists, but it is not a git repository and contains only `cpp/generated/*` and `rs/src/generated.rs`; there is no `trial/ts`. The sibling `/Users/owebeeone/limbo/taut-dev-cross/ts` also is not a package: it contains only an empty `test/` directory and no `src/cbor.ts`, `src/codec.ts`, or `package.json`.

There is a historical TS trial package at `/Users/owebeeone/limbo/glial-dev/trial/ts`, matching the FLOAT review history, but that is a different checkout from the one named by this task. It is also dirty: `git -C /Users/owebeeone/limbo/glial-dev/trial status --short` reports modified `ts/src/cbor.ts`, `ts/src/codec.ts`, staged `ts/src/schema.ts`, and added FLOAT test fixtures. As written, an implementation agent could either fail immediately in the requested cross-worktree or edit a separate dirty checkout and mix ResExt work with unfinished FLOAT-era changes.

The prompt should name the exact intended trial checkout or require the TS trial repo/worktree to be prepared before Phase 2 starts. It should also require a clean or explicitly baselined TS tree, because this task owns files that are already modified in the historical checkout.

### P0 - Required Phase 1 oracle corpora are not present, so the prompt is not executable now

References:
- `dev-docs/TautResExtPlan.md:51`
- `dev-docs/TautResExtPlan.md:55`
- `dev-docs/TautResExtPlan.md:59`
- `dev-docs/TautResExtP2-Base.md:15`
- `dev-docs/TautResExtP2-Base.md:19`
- `dev-docs/TautResExtP2-Ts.md:14`
- `run_tests.py:17`
- `src/taut/corpus/kit.py:89`

The base brief and TS prompt both make `corpus/residual_vectors.json` and `corpus/ext_vectors.json` the byte oracle. Those files do not exist in `/Users/owebeeone/limbo/taut-dev-cross/taut-ts/corpus`; only the existing float/glade/griplab corpus files are present. `run_tests.py` regenerates the existing corpus, float, glade, and CRDT artifacts, but has no residual/ext corpus build step. The conformance kit currently exposes only the existing Rust harness entry, not the residual/ext Phase 1 harness surface.

That means the TS prompt cannot be implemented or verified as written from this repo state. The task should be gated on Phase 1 landing the two corpus JSON files, their regen step, and whatever fixture IR/schema artifacts the TS tests are expected to load.

### P1 - The extension instructions depend on private TS codec helpers and conflict with the base surface

References:
- `dev-docs/TautResExtP2-Ts.md:22`
- `dev-docs/TautResExtP2-Ts.md:25`
- `dev-docs/TautResExtP2-Ts.md:26`
- `dev-docs/TautResExtP2-Base.md:45`
- `dev-docs/TautResExtP2-Base.md:50`
- `/Users/owebeeone/limbo/glial-dev/trial/ts/src/codec.ts:14`
- `/Users/owebeeone/limbo/glial-dev/trial/ts/src/codec.ts:44`
- `/Users/owebeeone/limbo/glial-dev/trial/ts/src/codec.ts:83`

The TS prompt says the extension value is produced via `codec.toWire` and `extGet` returns it for `fromWire`. In the real TS package, `toWire` and `fromWire` are file-local functions, not exported API. The only exported helpers are byte-oriented `encode`, `decode`, `encodeRef`, and `decodeRef`, so there is no public equivalent of Python's `codec.encode_struct` / `decode_struct` for producing or consuming the nested `Map<number, CborValue>` required by `ext_set`.

The base brief specifies `ext_get(host_bytes, tag) -> ExtMsg | null`, decoded through the extension type, while the TS prompt specifies `extGet(host, tag): CborValue | null`. A generic raw-CBOR TS surface may be acceptable, but the prompt does not say how callers should convert native extension values to nested CBOR maps without pre-serializing bytes, which the base explicitly forbids.

The TS brief should either instruct the agent to export stable structural helpers from `codec.ts` (for example `toCbor` / `fromCbor` or `encodeStruct` / `decodeStruct`) or define `ext.ts` as a typed/schema-aware API matching Python. Without that, implementers are likely to use private helpers, duplicate codec logic, or accidentally store serialized bytes as the extension value.

### P1 - The prompt omits the TS fixture schema/harness needed to consume the corpora

References:
- `dev-docs/TautResExtPlan.md:45`
- `dev-docs/TautResExtPlan.md:59`
- `dev-docs/TautResExtP2-Base.md:19`
- `dev-docs/TautResExtP2-Base.md:21`
- `dev-docs/TautResExtP2-Ts.md:14`
- `dev-docs/TautResExtP2-Ts.md:17`
- `/Users/owebeeone/limbo/glial-dev/trial/ts/test/forward_compat.test.ts:9`
- `/Users/owebeeone/limbo/glial-dev/trial/ts/test/forward_compat.test.ts:12`

The residual corpus is described as parse-free raw CBOR hex, but TS `codec.decode(schema, message, data)` needs a `SchemaIndex` and a message name. The prompt tells the TS agent only to copy two JSON vector files into `trial/ts/test/`; it does not identify the fixture IR/schema JSON, message names, extension message name, or test harness shape. Existing TS residual coverage hand-constructs the schema inline in the test file, so there is no established package-level convention to infer this from.

Phase 1 in the plan says fixture schemas should be committed as IR and the kit should emit per-language harnesses, but the TS prompt should still point to the exact artifact names and expected vector row schema. Otherwise an implementation can pass local hand-written tests while missing the real oracle shape, or it can spend time reverse-engineering Phase 1 assumptions that are not in the prompt.

### P2 - The verification command is too broad for the current TS package and the fuzz requirement is underspecified

References:
- `dev-docs/TautResExtP2-Ts.md:29`
- `dev-docs/TautResExtP2-Ts.md:30`
- `dev-docs/TautResExtP2-Base.md:76`
- `dev-docs/TautResExtP2-Base.md:79`
- `/Users/owebeeone/limbo/glial-dev/trial/ts/package.json:7`
- `/Users/owebeeone/limbo/glial-dev/trial/ts/package.json:8`

The TS prompt says to run the `trial/ts` tests plus differential fuzz over both corpora vs the Python reference. In the real TS package, `npm test` currently runs all `test/*.test.ts` and fails in `test/interop.test.ts` because the Python server does not start. The existing focused residual command passes, but the prompt does not distinguish local corpus tests from interop tests that need external server prerequisites.

The fuzz requirement also lacks enough implementation detail for a Phase 2 agent: it does not say how the TS repo should locate the taut Python reference from a separate checkout, how to generate random schemas/values for TS without new dependencies, what mismatch-count output is expected, or whether fuzz is a required gate or best-effort when the fixed corpora pass. The `npx tsx` fallback is also in tension with the "No package deps" rule; the package already has a no-dependency Node runner in `package.json`.

The prompt should name exact required commands, separate optional/interoperability tests from required corpus tests, and define the Python oracle invocation for the cross-repo fuzz.

### P2 - The dirty historical TS checkout creates file-ownership and regression risk

References:
- `dev-docs/TautResExtP2-Ts.md:11`
- `dev-docs/history/TautFload2-Ts-CodeReview55.md:31`
- `/Users/owebeeone/limbo/glial-dev/trial/ts/src/cbor.ts:7`
- `/Users/owebeeone/limbo/glial-dev/trial/ts/src/codec.ts:8`
- `/Users/owebeeone/limbo/glial-dev/trial/ts/src/schema.ts:5`

The real TS package currently has uncommitted FLOAT work in the same owned files named by the ResExt prompt. That matters because ResExt would likely touch `codec.ts` to expose structural helpers and may touch tests/fixtures. If the FLOAT changes are not already landed or intentionally included in the baseline, a ResExt implementation could overwrite, stage, or accidentally rely on unrelated work.

Before using `/Users/owebeeone/limbo/glial-dev/trial/ts` for this prompt, land or reset the FLOAT baseline explicitly. If the intended implementation path is a fresh `taut-dev-cross/trial/ts` worktree, the prompt should make that setup a prerequisite.

### P3 - Tag validation should specify integer and safe-range behavior for TS

References:
- `dev-docs/TautResExtP2-Ts.md:23`
- `dev-docs/TautResExtP2-Ts.md:25`
- `dev-docs/TautResExtP2-Base.md:44`
- `/Users/owebeeone/limbo/glial-dev/trial/ts/src/cbor.ts:149`
- `/Users/owebeeone/limbo/glial-dev/trial/ts/src/cbor.ts:220`

The prompt says to band-check `tag >= 2 ** 20`, but TS represents tags as `number`. The CBOR runtime can encode/decode 64-bit additional-info values through `BigInt`, but it converts them to/from `number`, so tags above `Number.MAX_SAFE_INTEGER` are not safe. The prompt should require `Number.isSafeInteger(tag)`, `tag >= 2 ** 20`, and probably `tag >= 0`; otherwise TS can silently lose parity for large extension tags that Python handles exactly.

This is not a blocker if the Phase 1 fixture tags stay near `BAND_START`, but it is a cross-language consistency risk worth pinning in the prompt.

## Verification Notes

- Read `dev-docs/TautResExtPlan.md`, `dev-docs/TautResExtP2-Ts.md`, `dev-docs/TautResExtP2-Base.md`, and the FLOAT TS precedent.
- Inspected the TypeScript-related generated files in `taut-ts/docs/examples/tasks/generated/typescript`; they are generated examples, not the owned TS package.
- Verified `/Users/owebeeone/limbo/taut-dev-cross/trial` has no `ts/` package and `/Users/owebeeone/limbo/taut-dev-cross/ts` has no TS source/package files.
- Verified `/Users/owebeeone/limbo/glial-dev/trial/ts` exists and contains the real historical TS package, but its repo has uncommitted/staged FLOAT-related changes.
- Ran `node --experimental-strip-types --test test/forward_compat.test.ts` in `/Users/owebeeone/limbo/glial-dev/trial/ts`: passed, 1/1.
- Ran `npm test` in `/Users/owebeeone/limbo/glial-dev/trial/ts`: failed, 15 passed and 5 failed because `test/interop.test.ts` could not start the Python server.

