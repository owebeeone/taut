# Taut ResExt Phase 2 TypeScript Prompt Review - Second Pass

## Findings

### P0 - The TS worktree named by the prompt still is not present in this checkout

References:
- `dev-docs/TautResExtP2-Ts.md:1`
- `dev-docs/TautResExtP2-Ts.md:3`
- `dev-docs/TautResExtP2-Ts.md:11`
- `dev-docs/TautResExtP2-Ts.md:14`
- `dev-docs/TautResExtPlan.md:68`
- `dev-docs/TautResExtPlan.md:69`
- `dev-docs/TautResExtPlan.md:90`
- `dev-docs/history/TautFloatP2-Ts.md:1`
- `dev-docs/history/TautFloatP2-Ts.md:3`

The prompt still directs the TS agent to `trial/ts/src/*`, but
`/Users/owebeeone/limbo/taut-dev-cross/trial` is not a TS package: it contains only
`cpp/generated/*` and `rs/src/generated.rs`. The sibling
`/Users/owebeeone/limbo/taut-dev-cross/ts` still contains only `test/` and no `src`,
`package.json`, or codec files. So an agent launched from the requested cross-worktree cannot
start the TypeScript implementation as written.

The historical FLOAT-style package still exists at
`/Users/owebeeone/limbo/glial-dev/trial/ts`, but that is a different checkout from the location
named by this task and it is dirty in files this prompt would own:
`ts/src/cbor.ts`, `ts/src/codec.ts`, staged `ts/src/schema.ts`, and added FLOAT fixtures/tests.
Using that package without an explicit handoff would mix ResExt work with unlanded FLOAT work.

This prior blocker remains unresolved and is still the main implementability blocker. The prompt
should name the exact intended `trial` checkout, or make creating/checking out
`taut-dev-cross/trial/ts` a Phase 2 prerequisite. It should also require a clean or explicitly
baselined TS tree before the ResExt edits begin.

### P1 - `ext.ts` still depends on private codec helpers and leaves the raw-vs-typed API ambiguous

References:
- `dev-docs/TautResExtP2-Ts.md:22`
- `dev-docs/TautResExtP2-Ts.md:23`
- `dev-docs/TautResExtP2-Ts.md:24`
- `dev-docs/TautResExtP2-Ts.md:25`
- `dev-docs/TautResExtP2-Ts.md:26`
- `dev-docs/TautResExtP2-Base.md:47`
- `dev-docs/TautResExtP2-Base.md:50`
- `dev-docs/TautResExtP2-Base.md:55`
- `/Users/owebeeone/limbo/glial-dev/trial/ts/src/codec.ts:14`
- `/Users/owebeeone/limbo/glial-dev/trial/ts/src/codec.ts:44`
- `/Users/owebeeone/limbo/glial-dev/trial/ts/src/codec.ts:83`
- `/Users/owebeeone/limbo/glial-dev/trial/ts/src/codec.ts:91`
- `src/taut/ext.py:24`
- `src/taut/ext.py:32`

The TS prompt says extension values are produced via `codec.toWire` and returned to
`fromWire`, but in the real TS package those helpers are file-local functions, not exported API.
The only exported codec functions are byte-oriented `encode`, `decode`, `encodeRef`, and
`decodeRef`. That means a new `ext.ts` cannot follow the prompt literally without either
duplicating codec internals or changing `codec.ts` in a way the prompt does not specify.

The surface also diverges from the base/Python contract. The base describes
`ext_get(host_bytes, tag) -> ExtMsg | null`, with nested-map conversion through the extension
message type. The TS brief instead proposes `extGet(host, tag): CborValue | null` and a generic
`extSet(..., value: CborValue)`. A raw-CBOR API may be acceptable for the interpreter package, but
the prompt must say how callers convert native `Decision` values to/from the nested
`Map<number, CborValue>` without pre-serializing bytes. Otherwise implementers can easily store
the extension as a byte string, which the base explicitly forbids.

This prior blocker remains unresolved. The prompt should either instruct the agent to export
stable structural helpers from `codec.ts` such as `toCbor`/`fromCbor` or
`encodeStruct`/`decodeStruct`, or define `ext.ts` as a schema-aware typed API mirroring
`src/taut/ext.py`.

### P1 - The TS schema/harness handoff is still incomplete across repos

References:
- `dev-docs/TautResExtP2-Base.md:19`
- `dev-docs/TautResExtP2-Base.md:20`
- `dev-docs/TautResExtP2-Base.md:21`
- `dev-docs/TautResExtP2-Base.md:23`
- `dev-docs/TautResExtP2-Ts.md:14`
- `dev-docs/TautResExtP2-Ts.md:17`
- `ir/resext.taut.py:16`
- `ir/resext.taut.py:21`
- `src/taut/corpus/resext_build.py:23`
- `src/taut/corpus/resext_build.py:69`
- `/Users/owebeeone/limbo/glial-dev/trial/ts/src/schema.ts:66`
- `/Users/owebeeone/limbo/glial-dev/trial/ts/src/schema.ts:107`
- `/Users/owebeeone/limbo/glial-dev/trial/ts/test/forward_compat.test.ts:9`
- `/Users/owebeeone/limbo/glial-dev/trial/ts/test/forward_compat.test.ts:12`

Phase 1 now provides the fixture IR and both vector corpora, and the base brief names
`ir/resext.taut.py`. That resolves the old taut-side missing-prerequisite problem. The TS prompt,
however, still tells the agent only to copy `residual_vectors.json` and `ext_vectors.json` into
`trial/ts/test/`.

The existing TS codec needs a `SchemaIndex` plus message names to decode and re-encode residual
vectors. It cannot consume `ir/resext.taut.py` directly; it expects JSON shaped like the existing
IR export contract. The current TS residual test hand-constructs a small schema inline, so there
is no package convention that would let an implementation agent infer the ResExt fixture setup
without reverse-engineering the Python IR and corpus builder.

This prior blocker is partially resolved, not fully resolved. The prompt should specify the exact
schema artifact to copy or generate for TS, for example an exported `resext.ir.json`, or it should
include the inline `Host`/`Decision` test schema expected by the corpus tests.

### P2 - The verification instructions are still not reproducible as written

References:
- `dev-docs/TautResExtP2-Ts.md:29`
- `dev-docs/TautResExtP2-Ts.md:30`
- `dev-docs/TautResExtP2-Base.md:81`
- `dev-docs/TautResExtP2-Base.md:82`
- `dev-docs/TautResExtP2-Base.md:83`
- `/Users/owebeeone/limbo/glial-dev/trial/ts/package.json:7`
- `/Users/owebeeone/limbo/glial-dev/trial/ts/package.json:8`
- `/Users/owebeeone/limbo/glial-dev/trial/ts/test/interop.test.ts:15`
- `/Users/owebeeone/limbo/glial-dev/trial/ts/test/interop.test.ts:16`
- `/Users/owebeeone/limbo/glial-dev/trial/ts/test/interop.test.ts:26`
- `/Users/owebeeone/limbo/glial-dev/trial/ts/test/interop.test.ts:30`

The prompt says to run the `trial/ts` tests plus differential fuzz. In the real historical TS
package, the package-level `npm test` command runs every `test/*.test.ts`; five Python interop
tests currently fail because the Python server does not start. Focused local tests can pass, but
the prompt does not identify the required ResExt-only command or separate corpus parity from
interop tests with external server prerequisites.

The fuzz requirement is also still underspecified for a cross-repo TS package. It does not say how
the TS tests should locate the taut Python reference, how random schemas/values are generated
without adding dependencies, what output/mismatch count is required, or whether fuzz is a hard gate
after the fixed corpora pass. The `npx tsx` suggestion is also awkward next to "No package deps";
the package already uses Node's `--experimental-strip-types` runner.

This prior blocker remains unresolved at P2 severity. The prompt should name exact required
commands, expected fixture paths, and whether full `npm test` is required or whether a focused
ResExt test file is the Phase 2 gate.

### P3 - Tag validation should pin TS integer and safe-range behavior

References:
- `dev-docs/TautResExtP2-Ts.md:25`
- `dev-docs/TautResExtP2-Base.md:49`
- `/Users/owebeeone/limbo/glial-dev/trial/ts/src/cbor.ts:149`
- `/Users/owebeeone/limbo/glial-dev/trial/ts/src/cbor.ts:171`
- `/Users/owebeeone/limbo/glial-dev/trial/ts/src/cbor.ts:193`
- `/Users/owebeeone/limbo/glial-dev/trial/ts/src/cbor.ts:211`
- `/Users/owebeeone/limbo/glial-dev/trial/ts/src/cbor.ts:220`

The TS brief says only to band-check `tag >= 2 ** 20`. Since TS tags are `number`, the prompt
should also require `Number.isSafeInteger(tag)`, `tag >= 0`, and preferably rejection of
non-integers. The CBOR runtime encodes/decodes 64-bit additional-info values through `BigInt` but
converts them to `number`, so values above `Number.MAX_SAFE_INTEGER` can silently lose parity with
Python.

This is not a blocker for the current Phase 1 fixtures because they use `1048577`, but it is a
cross-language consistency risk.

## Prior Blocker Status

- Resolved: the prior P0 "required Phase 1 oracle corpora are not present" blocker is fixed in
  `taut-ts`. `corpus/residual_vectors.json`, `corpus/ext_vectors.json`,
  `ir/resext.taut.py`, and `src/taut/corpus/resext_build.py` are tracked. `run_tests.py` now
  regenerates ResExt vectors, and `src/tests/test_resext_vectors.py` locks committed JSON to the
  generator and Python oracle.
- Resolved: the fork-gate pieces described by Phase 1 are present on the taut side. The scaffold
  has `ext.<lang>` runtime slots for compiled targets and tolerates missing `ext` files until
  Phase 2 drops them in. This does not solve TS because TS is cross-repo and interpreter-style.
- Partially resolved: the previous fixture-schema/harness blocker is improved because the base
  brief now names `ir/resext.taut.py` and the corpora include message names. It is still incomplete
  for TS because the prompt does not say how the separate TS package obtains a `SchemaIndex`.
- Unresolved: the TS repo location blocker remains. `taut-dev-cross/trial/ts` still does not
  exist, and the only verified real TS package is the dirty historical checkout under
  `/Users/owebeeone/limbo/glial-dev/trial/ts`.
- Unresolved: the `codec.toWire`/`fromWire` API blocker remains; those helpers are still private
  in the real TS package.
- Unresolved: the verification/fuzz instructions remain too vague for a reliable Phase 2 agent.
- Unresolved but lower severity: TS tag validation still needs safe-integer guidance.

## Assessment

Phase 1 has resolved the taut-side shared-oracle blocker. The current TS Phase 2 prompt is still
not implementable as written because the named TS repo is absent from this checkout and the
fallback historical TS package is dirty. Even after the repo setup is fixed, the prompt needs
specific TS guidance for structural codec helpers, schema fixture transfer, and exact verification
commands to avoid wrong extension encoding or unverifiable work.

## Verification Notes

- Read `dev-docs/TautResExtPlan.md`, `dev-docs/TautResExtP2-Ts.md`,
  `dev-docs/TautResExtP2-Base.md`, and the prior review
  `dev-docs/TautResExtP2-Ts-Review55.md`.
- Inspected `corpus/residual_vectors.json`, `corpus/ext_vectors.json`, `ir/resext.taut.py`,
  `run_tests.py`, `src/taut/corpus/resext_build.py`, `src/tests/test_resext_vectors.py`,
  `src/taut/gen/scaffold.py`, and the Python `src/taut/ext.py` oracle.
- Verified `/Users/owebeeone/limbo/taut-dev-cross/trial` has no `ts` package and
  `/Users/owebeeone/limbo/taut-dev-cross/ts` has no TS source/package files.
- Verified `/Users/owebeeone/limbo/glial-dev/trial/ts` exists and contains the historical TS
  package, but its parent repo has uncommitted/staged FLOAT-related changes.
- Ran `PYTHONPATH=src pytest src/tests/test_resext_vectors.py -q` in `taut-ts`: 7 passed.
- Ran `node --experimental-strip-types --test test/forward_compat.test.ts` in the historical
  `trial/ts`: 1 passed.
- Ran `npm test` in the historical `trial/ts`: 15 passed and 5 failed, all in
  `test/interop.test.ts` because the Python server did not start.
