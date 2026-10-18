# Taut ResExt Phase 2 TypeScript Prompt Review 55-5

## Findings

No actionable TS prompt or plan issues remain after the TypeScript runtime-home migration.

The TS Phase 2 brief now correctly treats TypeScript as an in-repo runtime-resource target under
`src/taut/gen/runtime/typescript/`, not as a durable external or `trial` target. The old dispatch
blocker from Review55-4 is resolved: an implementation agent no longer needs a workspace-local
`trial/ts` checkout or approval to edit an external package.

Residual risks / test gaps are implementation work, not prompt blockers:

- `src/taut/gen/runtime/typescript/ext.ts` is intentionally absent until TS Phase 2 implements it.
  `_RUNTIMES["typescript"]` already contains the slot and `emit()` will vendor it once the file
  exists.
- Some historical discovery docs and legacy Rust/C++ generator code still mention old target-slice
  paths. Those are not in the TS ResExt prompt path and do not make `trial` a TS dependency.
- The TypeScript ResExt corpus harness still needs to be implemented in `src/tests/test_ts.py` during
  Phase 2; the current `test_ts.py` is only a runtime-resource smoke test.

## Prior Resolution Check

- **TS target location:** resolved. `TautResExtP2-Ts.md` names
  `src/taut/gen/runtime/typescript/` as the source of truth and no longer asks for
  `taut-dev-cross/trial/ts` or `/Users/owebeeone/limbo/glial-dev/trial/ts`.
- **Runtime vendoring:** resolved. `scaffold._RUNTIMES["typescript"]` includes `cbor.ts`,
  `codec.ts`, `schema.ts`, `taut_client.ts`, and the future `ext.ts`.
- **Package data:** resolved. `pyproject.toml` includes `typescript/*.ts` under
  `taut.gen.runtime`, so the nested runtime resources are package data.
- **Generated client dependency:** resolved. Generated TypeScript clients import the local
  `./taut_client.ts`, not a sibling workspace path.
- **Schema handoff:** resolved. The TS prompt requires exporting `resext.ir.json` into the temp
  generated TypeScript test directory and loading it with `loadSchema(json)`.
- **Structural extension bridge:** still correctly specified. The prompt requires
  `cborDecode(encodeRef(...))` before `extSet` and `decodeRef(..., cborEncode(got))` after
  `extGet`, and explicitly forbids raw byte-string storage.
- **FLOAT baseline confusion:** resolved by scope. The prompt no longer depends on an external dirty
  FLOAT package.

## Dispatch Verdict

Dispatch TypeScript Phase 2.

The prompt is now implementation-ready: the durable TS source home exists, generator/runtime
vendoring is wired, the expected test/harness shape is in-repo, and the old external-checkout
blocker is gone.

## Verification Notes

- Inspected `dev-docs/TautResExtP2-Ts.md`, `dev-docs/TautResExtP2-Base.md`,
  `dev-docs/TautResExtPlan.md`, `src/taut/gen/scaffold.py`, `pyproject.toml`,
  `src/taut/gen/runtime/typescript/*`, `src/tests/test_cli.py`, `src/tests/test_ts.py`, and
  `src/tests/test_resext_vectors.py`.
- Searched active docs/prompts for stale TypeScript external-target language. Remaining `trial`
  mentions are historical discovery material or legacy Rust/C++ target-slice code, not TS ResExt
  dispatch instructions.
- Fixed one stale shared test assertion during review:
  `test_committed_resext_ir_json_loads_and_is_current` now compares the committed JSON object to
  `schema_json(S)` directly because `schema_json` returns a dict.
- Ran
  `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m pytest -q -p no:cacheprovider src/tests/test_cli.py src/tests/test_ts.py src/tests/test_resext_vectors.py`:
  20 passed.
- Ran generated TypeScript example:
  `node --experimental-strip-types example.ts` in `docs/examples/tasks/generated/typescript`:
  `typescript: Task round-tripped in 72 bytes (ok)`.
- Ran full suite:
  `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m pytest -q -p no:cacheprovider src/tests`:
  189 passed, 1 skipped.
