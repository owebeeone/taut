# Taut ResExt Phase 2 JS Prompt Review 55-2

## Findings

### [P1] Differential fuzz remains underspecified as a reviewable deliverable

Phase 1 landed the fixed residual and extension corpora, so the core JS implementation can now be driven by parse-free vectors. The remaining weak point is the fuzz requirement: the base brief still requires "a differential fuzz vs the Python oracle" covering random schemas/values, injected unknown tags, extension messages, and band tags (`dev-docs/TautResExtP2-Base.md:81` through `dev-docs/TautResExtP2-Base.md:83`), and the JS brief repeats that as "a differential fuzz vs Python" with no dependencies (`dev-docs/TautResExtP2-Js.md:21`).

That instruction is implementable only as an ad hoc local choice. Phase 1 did not add a residual/ext fuzzer contract, a seed/count convention, a Python-oracle invocation protocol, or a mismatch-reporting format. The existing JS precedent is a fixed-vector Node harness over `float_vectors.json` (`src/tests/js_float_parity.js:31` through `src/tests/js_float_parity.js:58`), not a Python-differential fuzzer. A JS agent can still complete corpus parity, but reviewers will not have a stable way to tell whether the fuzz portion is sufficient.

Recommendation: either define the JS fuzz gate concretely in the prompt (fixed seed/count, temp codegen flow, Python oracle command/API, expected "0 mismatches" output), or explicitly mark fuzzing as manual/non-blocking beyond the committed corpora.

### [P2] `extGet` is now byte-unambiguous, but the API shape should be called out as intentionally generic

The prior review flagged a conflict between the base contract's `ext_get(host_bytes, tag) -> ExtMsg | null` wording and the JS prompt's `extGet(host, tag) -> the nested Cbor or null`. Phase 1 makes the vector contract concrete: `corpus/ext_vectors.json` expects raw nested extension-message hex for `get` rows (`corpus/ext_vectors.json:20` through `corpus/ext_vectors.json:35`), while the JS prompt says callers pass the returned `Cbor` to `ExtMsg.fromCbor` (`dev-docs/TautResExtP2-Js.md:17` through `dev-docs/TautResExtP2-Js.md:19`). That is implementable and byte-comparable.

The remaining risk is cross-language API consistency, not byte parity. The base brief still says extension accessors "mirror `ext.py` exactly" and describes `ext_get` as returning an extension value (`dev-docs/TautResExtP2-Base.md:47` through `dev-docs/TautResExtP2-Base.md:56`), while line 61 allows idiomatic per-language surfaces. The JS brief should explicitly say the JS surface is the generic-CBOR variant and that the harness should compare `encode(extGet(...))` to the vector `expect`, or decode it with `ExtMsg.fromCbor` only for typed assertions.

### [P2] Band-check ordering is only explicit in the base brief, not in the JS step

The base brief requires the extension tag band check first (`dev-docs/TautResExtP2-Base.md:47` through `dev-docs/TautResExtP2-Base.md:49`), matching Python's `_check(tag)` before decoding in all three accessors (`src/taut/ext.py:24` through `src/taut/ext.py:45`). The JS prompt mentions "Band-check `tag >= 2**20`" after describing decode/map surgery (`dev-docs/TautResExtP2-Js.md:15` through `dev-docs/TautResExtP2-Js.md:19`).

Because the prompt opens by telling the agent to read the base brief, this is not a blocker. It is still worth tightening: if the future fuzz gate includes invalid tags plus malformed host bytes, decoding before the band check can produce non-oracle errors.

### [P3] The `MAP` example still names an unexported runtime constant

The JS brief describes `CMap` as `{kind: MAP, map: [[key, Cbor], ...]}` (`dev-docs/TautResExtP2-Js.md:15`). In the current runtime, `MAP` is private to `cbor.js` and is not exported (`src/taut/gen/runtime/cbor.js:8`, `src/taut/gen/runtime/cbor.js:203`). This does not block implementation because `ext.js` can use `decode(...).map`, `cmapEntries(...)`, and `CMap(...)` without inspecting the constant. If top-level map validation is expected, the prompt should say to use the existing helpers or to export the constants.

## Prior Blockers

- **Resolved: missing Phase 1 artifacts.** `ir/resext.taut.py` now exists (`ir/resext.taut.py:16` through `ir/resext.taut.py:25`), `corpus/residual_vectors.json` has the four residual rows including interleaved and band-tag cases (`corpus/residual_vectors.json:1` through `corpus/residual_vectors.json:22`), and `corpus/ext_vectors.json` has the five set/get/clear rows (`corpus/ext_vectors.json:1` through `corpus/ext_vectors.json:43`). `run_tests.py` now regenerates the ResExt corpora (`run_tests.py:17` through `run_tests.py:24`), and `src/tests/test_resext_vectors.py` locks committed corpora to the generator (`src/tests/test_resext_vectors.py:21` through `src/tests/test_resext_vectors.py:28`).
- **Resolved: missing scaffold/runtime slot.** `_RUNTIMES` now contains `("ext.js", "ext.js")` for JS (`src/taut/gen/scaffold.py:32` through `src/taut/gen/scaffold.py:40`), and `emit()` skips missing `ext.<lang>` resources until Phase 2 drops them in (`src/taut/gen/scaffold.py:600` through `src/taut/gen/scaffold.py:607`). Adding `src/taut/gen/runtime/ext.js` is now within JS ownership and does not require editing `scaffold.py`.
- **Resolved enough: `extGet` vector ambiguity.** The committed `get` vector expects nested extension hex, so the JS prompt's generic `Cbor` return can be tested byte-exactly. The API wording should still be clarified as noted above.
- **Still unresolved: reproducible differential fuzz contract.** Phase 1 made corpus parity executable, but did not define the fuzz gate that both the base and JS prompts require.
- **Mostly unresolved but minor: band-check ordering.** The base brief is clear; the JS brief should restate the order to prevent accidental divergence.

## Implementability Assessment

The JS Phase 2 prompt is now implementable for the required residual verification and extension accessor work. There are no remaining P0 blockers from the prior review. A JS agent can generate the shared fixture with `--forward-compat`, use the existing generated `wireResidual` path (`src/taut/gen/js.py:57` through `src/taut/gen/js.py:88`), rely on `cbor.js` map-key sorting for canonical re-emit (`src/taut/gen/runtime/cbor.js:147` through `src/taut/gen/runtime/cbor.js:150`), add only `src/taut/gen/runtime/ext.js`, and add tests/harness code under `src/tests/test_js.py` plus a JS harness.

The prompt is not fully review-tight because the fuzz requirement remains open-ended. I would not block Phase 2 JS on that if corpus parity is the acceptance gate, but I would block claiming the fuzz part is satisfied without a concrete seed/count/protocol in the submitted change.

## Scope Inspected

- `dev-docs/TautResExtPlan.md`
- `dev-docs/TautResExtP2-Base.md`
- `dev-docs/TautResExtP2-Js.md`
- `dev-docs/TautResExtP2-Js-Review55.md`
- `dev-docs/history/TautFloatP2-Js.md`
- `ir/resext.taut.py`
- `corpus/residual_vectors.json`
- `corpus/ext_vectors.json`
- `src/taut/corpus/resext_build.py`
- `src/tests/test_resext_vectors.py`
- `src/taut/gen/scaffold.py`
- `src/taut/gen/js.py`
- `src/taut/gen/runtime/cbor.js`
- `src/taut/ext.py`
- `src/tests/test_js.py`
- `src/tests/js_float_parity.js`
- `run_tests.py`
- `pyproject.toml`

## Verification

No implementation tests were run; this was a prompt/plan review only. I did run repository inspection commands and `node --version` (`v22.19.0`) to confirm local JS tool availability.
