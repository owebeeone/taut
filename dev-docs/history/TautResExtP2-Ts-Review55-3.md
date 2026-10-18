# Taut ResExt Phase 2 TypeScript Prompt Review - Third Pass

## Findings

### P0 - The TS task is still not dispatchable because the required `trial/ts` worktree is absent

References:
- `dev-docs/TautResExtPlan.md:3`
- `dev-docs/TautResExtPlan.md:68`
- `dev-docs/TautResExtPlan.md:69`
- `dev-docs/TautResExtP2-Ts.md:1`
- `dev-docs/TautResExtP2-Ts.md:3`
- `dev-docs/TautResExtP2-Ts.md:8`
- `dev-docs/TautResExtP2-Ts.md:11`
- `dev-docs/history/TautFloatP2-Ts.md:3`
- `dev-docs/history/TautFloatP2-Ts.md:8`

The prompt now explicitly calls out the missing TS checkout as a blocker, which is an improvement
over the first pass. The underlying prerequisite is still not satisfied. In this workspace,
`/Users/owebeeone/limbo/taut-dev-cross/trial` contains only `cpp/generated/*` and
`rs/src/generated.rs`; `/Users/owebeeone/limbo/taut-dev-cross/ts` contains no TS package files; and
the only TypeScript under `taut-ts` is generated example output under
`docs/examples/tasks/generated/typescript`.

There is still a cross-doc orchestration conflict: the plan says Phase 2 is ready for fan-out while
the TS prompt says the TS task must not be dispatched until a separate `trial` checkout is provided.
That means the current prompt is honest about the blocker, but the overall Phase 2 state is not
implementable for TS as written from this checkout.

Prior status: unresolved. The ambiguity is reduced, but the dispatch blocker remains. The prompt
should either name the exact clean `trial` checkout to use, or make creation/provisioning of
`taut-dev-cross/trial/ts` a prerequisite before this Phase 2 task can be assigned.

### P1 - The typed extension path is still ambiguous enough to store the extension as bytes

References:
- `dev-docs/TautResExtP2-Base.md:60`
- `dev-docs/TautResExtP2-Base.md:66`
- `dev-docs/TautResExtP2-Base.md:74`
- `dev-docs/TautResExtP2-Base.md:83`
- `dev-docs/TautResExtP2-Ts.md:27`
- `dev-docs/TautResExtP2-Ts.md:35`
- `/Users/owebeeone/limbo/glial-dev/trial/ts/src/cbor.ts:15`
- `/Users/owebeeone/limbo/glial-dev/trial/ts/src/cbor.ts:23`
- `/Users/owebeeone/limbo/glial-dev/trial/ts/src/codec.ts:14`
- `/Users/owebeeone/limbo/glial-dev/trial/ts/src/codec.ts:44`
- `/Users/owebeeone/limbo/glial-dev/trial/ts/src/codec.ts:91`
- `/Users/owebeeone/limbo/glial-dev/trial/ts/src/codec.ts:97`
- `src/taut/ext.py:24`
- `src/taut/ext.py:38`

The prompt now acknowledges that `toWire`/`fromWire` are private and offers two routes: export them,
or use the existing `encodeRef`/`decodeRef`. The export route is viable. The `encodeRef` route is
not sufficient as written, because `encodeRef` returns a `Uint8Array`, and `Uint8Array` is itself a
valid `CborValue` byte string in the TS runtime. Passing that directly to `extSet` would store a CBOR
bytes value at the band tag, not the nested CBOR map required by the base and Python `ext.py`.

The corpus should catch that for the set rows, but the prompt still leaves a high-risk trap in the
core extension instruction. It should spell out the structural bridge if it keeps the raw helper
surface, for example: build the `Decision` value with `cbor.decode(encodeRef(schema, {k: "msg",
name: "Decision"}, decision))`, pass that nested `Map` to `extSet`, and reconstruct on `extGet` with
`decodeRef(schema, {k: "msg", name: "Decision"}, cbor.encode(got))`. Alternatively, export stable
structural helpers such as `toCbor`/`fromCbor` and require the ResExt tests to use those.

Prior status: partially resolved, not fully resolved. The prompt identifies the private-helper
problem, but the raw-vs-typed API remains ambiguous enough to produce the exact pre-serialized-bytes
regression the base forbids.

### P1 - The schema fixture handoff still lacks a concrete TS-consumable artifact or command

References:
- `dev-docs/TautResExtP2-Base.md:19`
- `dev-docs/TautResExtP2-Base.md:25`
- `dev-docs/TautResExtP2-Ts.md:19`
- `dev-docs/TautResExtP2-Ts.md:34`
- `src/taut/corpus/resext_build.py:22`
- `src/taut/corpus/resext_build.py:25`
- `src/taut/corpus/resext_build.py:89`
- `src/taut/corpus/resext_build.py:91`
- `src/taut/cli.py:110`
- `src/taut/cli.py:140`
- `src/taut/ir/export.py:42`
- `src/taut/ir/export.py:79`
- `/Users/owebeeone/limbo/glial-dev/trial/ts/src/schema.ts:107`
- `/Users/owebeeone/limbo/glial-dev/trial/ts/src/schema.ts:109`

The taut-side Phase 1 artifacts are present now: `ir/resext.taut.py`,
`corpus/residual_vectors.json`, `corpus/ext_vectors.json`, the generator, and the lockstep tests.
That resolves the original missing-corpus blocker. The remaining TS handoff is still incomplete.

The TS package cannot load `ir/resext.taut.py` directly; it needs neutral IR JSON for
`loadSchema(json)`. The prompt says to export `ir/resext.taut.py` to IR JSON, but there is no
checked-in `corpus/resext.ir.json`, `resext_build.py` writes only the two vector files, and the CLI
has `gen`, `corpus`, and `json` subcommands but no direct `export` subcommand. The export helper
exists as `taut.ir.export.export_to`, but the prompt does not give a command or target filename.

Prior status: partially resolved. The prompt now names the fixture and says the schema must come
across, but it should pin an exact artifact such as `trial/ts/test/resext.ir.json` plus the command
that produces it, or Phase 1 should commit `corpus/resext.ir.json` alongside the vector corpora.

### P2 - Verification and fuzz instructions are still not reproducible for the TS package

References:
- `dev-docs/TautResExtP2-Base.md:100`
- `dev-docs/TautResExtP2-Base.md:114`
- `dev-docs/TautResExtP2-Ts.md:37`
- `dev-docs/TautResExtP2-Ts.md:38`
- `/Users/owebeeone/limbo/glial-dev/trial/ts/package.json:7`
- `/Users/owebeeone/limbo/glial-dev/trial/ts/package.json:8`
- `/Users/owebeeone/limbo/glial-dev/trial/ts/test/interop.test.ts:26`
- `/Users/owebeeone/limbo/glial-dev/trial/ts/test/interop.test.ts:30`

The base brief now does a better job separating fixed corpus parity from deterministic supporting
fuzz. The TS prompt still only says to run the `trial/ts` tests plus differential fuzz. In the real
historical TS package, `npm test` runs all `test/*.test.ts` and still fails because the Python
interop server hook in `test/interop.test.ts` does not start. A focused local test can pass, but the
prompt does not identify the required ResExt-only command or say whether full `npm test` is expected
after the existing interop prerequisite is fixed.

The fuzz path is also not pinned for the cross-repo interpreter package. The prompt does not say
where the TS fuzz harness should live, how it should locate the taut Python reference from the
separate checkout, or what exact command is the required Phase 2 evidence. The `npx tsx` fallback is
also still awkward next to "No package deps"; the package already has a no-dependency Node runner.

Prior status: partially resolved. The base brief improved the fuzz contract, but the TS-specific
verification command remains too vague for a reliable implementation handoff.

### P2 - The only verified fallback `trial` package is still dirty in ResExt-owned files

References:
- `dev-docs/TautResExtP2-Ts.md:16`
- `dev-docs/TautResExtP2-Ts.md:17`
- `dev-docs/history/TautFload2-Ts-CodeReview55.md:29`
- `/Users/owebeeone/limbo/glial-dev/trial/ts/src/cbor.ts:7`
- `/Users/owebeeone/limbo/glial-dev/trial/ts/src/codec.ts:8`
- `/Users/owebeeone/limbo/glial-dev/trial/ts/src/schema.ts:5`

If the owner decides that `/Users/owebeeone/limbo/glial-dev/trial/ts` is the intended missing
`trial` checkout, it is not a clean baseline. Its parent repo reports modified `ts/src/cbor.ts` and
`ts/src/codec.ts`, staged `ts/src/schema.ts`, and added FLOAT fixture/test files. Those overlap the
ResExt-owned files and the schema/test surface the new task would use.

Prior status: unresolved. Before dispatching ResExt against that package, land or explicitly
baseline the FLOAT work so the ResExt changes do not depend on or overwrite unrelated dirty state.

## Proposed Resolutions

1. **Provision the TS target before dispatch**
   - **Resolution:** Resolve the plan/prompt conflict by either creating or naming a clean `taut-dev-cross/trial/ts` checkout before assigning TS Phase 2. If the intended target is `/Users/owebeeone/limbo/glial-dev/trial/ts`, state that explicitly in the prompt and treat its current dirty FLOAT state as an input that must be landed or baselined first.
   - **Verification:** The TS prompt should name one absolute or repo-relative package path that contains `package.json`, `src/cbor.ts`, `src/codec.ts`, and `src/schema.ts`, and `git status --short` for that package's parent repo should be recorded before implementation starts.

2. **Make the typed extension bridge structural**
   - **Resolution:** Remove the ambiguous "use `encodeRef` directly" wording, or spell out the structural round trip. For set rows, encode the generated `Decision`, immediately CBOR-decode those bytes into a nested `CborValue`, and pass that nested value to `extSet`. For get rows, encode the returned nested `CborValue` and feed those bytes through `decodeRef` for `Decision`. An acceptable alternative is to export stable `toCbor`/`fromCbor` helpers and require the tests to use them.
   - **Verification:** Add a test that fails if `extSet` stores the extension value as a CBOR byte string instead of as the nested Decision map. The committed `set`/`replace` rows in `corpus/ext_vectors.json` should be the primary gate.

3. **Commit or generate a TS-consumable schema artifact**
   - **Resolution:** Pin one schema handoff. Either commit a neutral fixture such as `corpus/resext.ir.json`, or add an exact command in the TS prompt that writes `trial/ts/test/resext.ir.json` using `taut.ir.export.export_to` from `ir/resext.taut.py`.
   - **Verification:** The focused TS ResExt test should load that JSON through `loadSchema(json)` and should not depend on importing `ir/resext.taut.py` directly.

4. **Define focused TS verification commands**
   - **Resolution:** Add a ResExt-only test command that does not rely on the currently failing package-wide Python interop server. Keep full `npm test` as optional follow-up until the existing interop startup issue is fixed.
   - **Verification:** Require a command equivalent to `node --experimental-strip-types --test <resext-test-file>` plus a type-checking command such as `npx tsc --noEmit` when the package has TypeScript checking available. Record the known status of full `npm test` separately.

5. **Baseline FLOAT dirty state before ResExt edits**
   - **Resolution:** If `/Users/owebeeone/limbo/glial-dev/trial/ts` is used, land, stash, or explicitly mark the FLOAT changes as the baseline before ResExt work touches `src/cbor.ts`, `src/codec.ts`, `src/schema.ts`, or tests.
   - **Verification:** Capture `git status --short` before and after ResExt so implementation review can distinguish ResExt changes from pre-existing FLOAT edits.

## Prior Issue Status

- Resolved: the prior P0 "required Phase 1 oracle corpora are not present" blocker is fixed on the
  taut side. The two corpora, fixture IR, generator, `run_tests.py` hook, scaffold ext slots, and
  `src/tests/test_resext_vectors.py` are present and tracked.
- Resolved: the TS safe-integer tag-validation concern is addressed in the current prompt with
  `Number.isSafeInteger(tag) && tag >= 2 ** 20`.
- Partially resolved: the TS repo-location problem is now explicitly documented as a blocker in the
  prompt, but the required checkout is still missing.
- Partially resolved: the schema/harness issue now points at `ir/resext.taut.py` and `loadSchema`,
  but it still lacks a concrete `resext.ir.json` artifact or export command.
- Partially resolved: the private `toWire`/`fromWire` issue is called out, but the `encodeRef` /
  `decodeRef` alternative is underspecified and can lead to byte-string extension storage.
- Unresolved: the verification/fuzz instructions still do not define a reproducible TS command set.
- Unresolved: the historical TS package remains dirty in files this task would own.
- New in this pass: the plan-level "Phase 2 ready" statement conflicts with the TS prompt's explicit
  "do not dispatch yet" blocker.

## Assessment

The taut-side Phase 1 state is now solid enough to serve as the oracle. The TypeScript Phase 2 prompt
is still not implementable as a dispatched task in this workspace because the required `trial/ts`
repo is absent. After that checkout is provided, the prompt still needs three concrete TS handoff
details: a schema JSON fixture path/command, an unambiguous structural typed-extension path, and a
focused verification command that does not rely on the currently failing package-wide interop tests.

## Verification Notes

- Read `dev-docs/TautResExtPlan.md`, `dev-docs/TautResExtP2-Ts.md`,
  `dev-docs/TautResExtP2-Base.md`, `dev-docs/TautResExtP2-Ts-Review55.md`, and
  `dev-docs/TautResExtP2-Ts-Review55-2.md`.
- Inspected `ir/resext.taut.py`, `corpus/residual_vectors.json`, `corpus/ext_vectors.json`,
  `src/taut/corpus/resext_build.py`, `src/tests/test_resext_vectors.py`, `run_tests.py`,
  `src/taut/ext.py`, `src/taut/cli.py`, `src/taut/ir/export.py`, and `src/taut/gen/scaffold.py`.
- Verified `/Users/owebeeone/limbo/taut-dev-cross/trial` has no `ts` package and
  `/Users/owebeeone/limbo/taut-dev-cross/ts` has no TS source/package files.
- Verified the only found historical TS package is `/Users/owebeeone/limbo/glial-dev/trial/ts`, and
  its parent repo has uncommitted/staged FLOAT-related changes.
- Ran `PYTHONPATH=src pytest src/tests/test_resext_vectors.py -q` in `taut-ts`: 7 passed.
- Ran `node --experimental-strip-types --test test/forward_compat.test.ts` in the historical
  `trial/ts`: 1 passed.
- Ran `npm test` in the historical `trial/ts`: 15 passed and 5 failed, all from
  `test/interop.test.ts` because the Python server did not start.
