# Taut ResExt Phase 2 JS Prompt Review 55-4

## Findings

No actionable findings remain. The designer-edited JS Phase 2 prompt is implementation-ready as
written.

The only issue left in Review55-3 was the generated-type wording around `ExtMsg.toCbor(...)`.
That has been corrected in the current JS brief: it now tells the implementer to construct or
decode a generated `Decision`, call the instance method `decision.toCbor()` for `extSet`, call
`Decision.fromCbor(got)` for `extGet`, and use
`Decision.fromCbor(decode(hexToBytes(valueHex))).toCbor()` for corpus set/replace rows
(`dev-docs/TautResExtP2-Js.md:27` through `dev-docs/TautResExtP2-Js.md:30`). That matches the
actual JS generator shape: `toCbor()` is emitted as an instance method and `fromCbor(c)` as a
static method (`src/taut/gen/js.py:61` through `src/taut/gen/js.py:76`).

## Proposed Resolutions

None. No prompt/doc edits are required before dispatching the JS implementation task.

Residual implementation risk is limited to normal Phase 2 execution risk: `ext.js` is still
unimplemented, and the temporary pytest-generated Node harness still needs to prove corpus parity,
invalid-case behavior, and the fixed-seed differential fuzz. Those are implementation/test gaps,
not prompt-readiness gaps.

## Prior Resolution Check

- **Review55-3 P3 generated-type wording: resolved.** The JS brief no longer implies a static
  `ExtMsg.toCbor(...)` API. It now uses the generated JS instance/static split exactly:
  `decision.toCbor()` and `Decision.fromCbor(...)`
  (`dev-docs/TautResExtP2-Js.md:27` through `dev-docs/TautResExtP2-Js.md:30`), matching
  `src/taut/gen/js.py:61` through `src/taut/gen/js.py:76`.
- **Typed extension path remains explicit.** The base brief requires the harness to exercise the
  generated extension type's `to_cbor`/`from_cbor` equivalent and compare `get` rows by re-encoding
  the returned value (`dev-docs/TautResExtP2-Base.md:74` through
  `dev-docs/TautResExtP2-Base.md:83`). The JS brief now gives the concrete `Decision` harness path,
  so a map-only byte-match helper would no longer satisfy the prompt.
- **Previously resolved Review55 items remain stable.** The JS brief still pins the generic-CBOR
  `extGet` surface (`dev-docs/TautResExtP2-Js.md:23` through
  `dev-docs/TautResExtP2-Js.md:24`), first-position band validation and non-map rejection
  (`dev-docs/TautResExtP2-Js.md:25` through `dev-docs/TautResExtP2-Js.md:26`), exported
  `extSet/extGet/extClear` (`dev-docs/TautResExtP2-Js.md:26` through
  `dev-docs/TautResExtP2-Js.md:27`), and use of exported `CMap(...)` instead of the private
  `MAP` constant (`dev-docs/TautResExtP2-Js.md:21` through `dev-docs/TautResExtP2-Js.md:24`).
- **Shared Phase 1 surface remains available.** The fixture schema, residual corpus, extension
  corpus, scaffold runtime slot, and lockstep corpus tests are still present:
  `ir/resext.taut.py:16` through `ir/resext.taut.py:25`,
  `corpus/residual_vectors.json:1` through `corpus/residual_vectors.json:22`,
  `corpus/ext_vectors.json:1` through `corpus/ext_vectors.json:43`,
  `src/taut/gen/scaffold.py:32` through `src/taut/gen/scaffold.py:40`, and
  `src/tests/test_resext_vectors.py:21` through `src/tests/test_resext_vectors.py:28`.

## Dispatch Verdict

Ready to dispatch to the JS implementation agent.

The prompt is scoped to JS-owned files only (`src/taut/gen/runtime/ext.js` and
`src/tests/test_js.py`), while treating `src/taut/gen/runtime/cbor.js` and `src/taut/gen/js.py` as
verify-first unless the residual corpus proves a real divergence
(`dev-docs/TautResExtP2-Js.md:6` through `dev-docs/TautResExtP2-Js.md:11`). It gives concrete
extension semantics, required invalid-case assertions, corpus gates, fuzz evidence, and the exact
pytest command to run (`dev-docs/TautResExtP2-Js.md:32` through
`dev-docs/TautResExtP2-Js.md:39`).

## Verification Notes

Inspected:

- `dev-docs/TautResExtPlan.md`
- `dev-docs/TautResExtP2-Base.md`
- `dev-docs/TautResExtP2-Js.md`
- `dev-docs/TautResExtP2-Js-Review55-3.md`
- `ir/resext.taut.py`
- `corpus/residual_vectors.json`
- `corpus/ext_vectors.json`
- `src/taut/gen/js.py`
- `src/taut/gen/runtime/cbor.js`
- `src/taut/ext.py`
- `src/taut/gen/scaffold.py`
- `src/tests/test_resext_vectors.py`
- `src/tests/test_js.py`
- `src/tests/js_float_parity.js`
- `run_tests.py`
- `pyproject.toml`

No implementation tests were run; this was a prompt/docs review only. I confirmed local Node
availability with `node --version` (`v22.19.0`).
