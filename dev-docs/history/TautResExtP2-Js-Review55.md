# Taut ResExt Phase 2 JS Prompt Review 55

## Findings

### [P0] Phase 2 JS is blocked on missing Phase 1 artifacts

`dev-docs/TautResExtP2-Js.md:11` tells the JS agent to run `residual_vectors.json`, and `dev-docs/TautResExtP2-Js.md:21` requires a harness over both corpora. The shared brief defines those files as `corpus/residual_vectors.json` and `corpus/ext_vectors.json` (`dev-docs/TautResExtP2-Base.md:15` through `dev-docs/TautResExtP2-Base.md:22`), while the plan assigns emitting them, wiring regen, adding shared harness support, and committing fixture schemas to Phase 1 (`dev-docs/TautResExtPlan.md:51` through `dev-docs/TautResExtPlan.md:62`).

Those prerequisites are not present in the current repo. `corpus/` currently contains only float/glade/griplab artifacts, `run_tests.py:17` through `run_tests.py:23` regenerates no residual/ext corpora, and `src/taut/corpus/kit.py:89` through `src/taut/corpus/kit.py:92` still exposes only a Rust parity harness. A JS implementer following the prompt cannot know the fixture schema, expected byte rows, or authoritative set/get/clear cases. Creating them in the JS phase would also violate the "touch only your files" rule in `dev-docs/TautResExtP2-Base.md:63` through `dev-docs/TautResExtP2-Base.md:68`.

The prompt should either state that it is not executable until Phase 1 lands, or include/point to the committed Phase 1 artifacts and exact JS harness entrypoint.

### [P0] `ext.js` cannot be integrated under the stated file ownership

The JS prompt assigns a new `src/taut/gen/runtime/ext.js` file (`dev-docs/TautResExtP2-Js.md:6` through `dev-docs/TautResExtP2-Js.md:9`), and the base brief says Phase 2 agents should only touch their runtime, generator, new `ext.<lang>`, and tests (`dev-docs/TautResExtP2-Base.md:63` through `dev-docs/TautResExtP2-Base.md:68`). But the current scaffold can vend only one runtime resource per language: `_RUNTIMES` maps JS to just `("cbor.js", "cbor.js")` at `src/taut/gen/scaffold.py:30` through `src/taut/gen/scaffold.py:38`, and `emit()` writes a single runtime file at `src/taut/gen/scaffold.py:594` through `src/taut/gen/scaffold.py:599`.

The plan explicitly expects Phase 1 to add a vendored `ext.<lang>` runtime slot to `_RUNTIMES`/scaffold before Phase 2 (`dev-docs/TautResExtPlan.md:59` through `dev-docs/TautResExtPlan.md:62`). Since that slot is absent, adding `src/taut/gen/runtime/ext.js` alone leaves `tautc gen --with-runtime -l js` unable to emit it. Fixing that requires editing `src/taut/gen/scaffold.py`, which the JS prompt does not own.

The prompt should make the scaffold-slot prerequisite explicit, or expand JS ownership to include the scaffold change. As written, it asks for a new runtime module without a way to distribute it.

### [P1] `extGet` return semantics conflict with the shared/Python contract

The base contract says `ext_get(host_bytes, tag) -> ExtMsg | null` and decodes the nested map via the extension type's `from_cbor` (`dev-docs/TautResExtP2-Base.md:50` through `dev-docs/TautResExtP2-Base.md:51`). The Python oracle does that concretely: `ext_get()` calls `codec.decode_struct(...)` and returns a native dict or `None` at `src/taut/ext.py:32` through `src/taut/ext.py:38`.

The JS prompt instead specifies `extGet(host, tag) -> the nested Cbor or null` and says the caller should pass that to `ExtMsg.fromCbor` (`dev-docs/TautResExtP2-Js.md:15` through `dev-docs/TautResExtP2-Js.md:19`). That may be an intentional compiled-target idiom, but it no longer "mirrors `ext.py`" at the API level and makes `ext_vectors.json` ambiguous: get rows could assert decoded extension values, nested CBOR hex, or both.

Before implementation, the prompt should pin the JS API and vector format. If JS is meant to expose only generic CBOR, say the corpus harness must compare `ExtMsg.fromCbor(extGet(...))` against the Python oracle. If JS is meant to mirror Python more directly, add a typed wrapper shape or clarify how `ExtMsg` is supplied.

### [P1] Verification asks for differential fuzzing without a reproducible contract

`dev-docs/TautResExtP2-Base.md:76` through `dev-docs/TautResExtP2-Base.md:78` require differential fuzzing vs Python for random schemas/values, injected unknown tags, extension messages, and band tags. The JS brief repeats that at `dev-docs/TautResExtP2-Js.md:21`, but the repo currently has no residual/ext fuzzer, no fixture schema, no JS harness generator, and no seed/count/mismatch reporting convention. The existing JS precedent is a fixed-vector float harness (`src/tests/js_float_parity.js:31` through `src/tests/js_float_parity.js:58`), not a Python-differential schema/value fuzzer.

This is implementable as an ad hoc local script, but not as a stable reviewable gate. The prompt should define whether fuzzing is checked in or manual, the required seed/count, how the JS harness invokes the Python oracle with no third-party deps, and which cases are covered by the corpora versus random fuzz.

### [P2] Band-check error ordering is underspecified

The base brief says to band-check first (`dev-docs/TautResExtP2-Base.md:43` through `dev-docs/TautResExtP2-Base.md:45`), and Python checks the tag before decoding host bytes in all three accessors (`src/taut/ext.py:24` through `src/taut/ext.py:46`). The JS prompt only says "Band-check `tag >= 2**20`" after describing decode/map surgery (`dev-docs/TautResExtP2-Js.md:15` through `dev-docs/TautResExtP2-Js.md:19`).

If invalid-tag cases enter `ext_vectors.json` or the fuzzer, decoding before checking can produce different failures for malformed host bytes and below-band tags. The prompt should state that `extSet`, `extGet`, and `extClear` reject below-band tags before decoding, matching `ext.py`.

## Non-Blocking Notes

- The existing JS residual shape looks plausible once the missing corpus exists. Generated messages add `wireResidual` only when `forward_compat=True` (`src/taut/gen/js.py:57` through `src/taut/gen/js.py:88`), and `cbor.js` sorts map keys during encode (`src/taut/gen/runtime/cbor.js:147` through `src/taut/gen/runtime/cbor.js:150`), so interleaved residual tags should re-emit in canonical order if the corpus confirms it.
- The prompt references `{kind: MAP, map: ...}` (`dev-docs/TautResExtP2-Js.md:15`), but `MAP` is not exported from `cbor.js` (`src/taut/gen/runtime/cbor.js:8`, `src/taut/gen/runtime/cbor.js:203`). `ext.js` can avoid that by using `decode(...).map`/`CMap(...)`, but if top-level map validation is desired the prompt should say whether to export kind constants or use an existing helper.
- Node is available locally (`v22.19.0`), so the JS runtime gate itself is not blocked by tool availability.

## Scope Inspected

- `dev-docs/TautResExtPlan.md`
- `dev-docs/TautResExtP2-Base.md`
- `dev-docs/TautResExtP2-Js.md`
- `dev-docs/history/TautFloatP2-Js.md`
- `src/taut/gen/runtime/cbor.js`
- `src/taut/gen/js.py`
- `src/taut/gen/scaffold.py`
- `src/taut/ext.py`
- `src/taut/wire/codec.py`
- `src/taut/wire/cbor.py`
- `src/taut/corpus/kit.py`
- `src/tests/test_js.py`
- `src/tests/js_float_parity.js`
- `src/tests/test_forward_compat.py`
- `run_tests.py`
- Current `corpus/` and `src/taut/gen/runtime/` contents

## Verification

No implementation tests were run; this was a prompt/plan review only. I did run repository inspection commands and `node --version` to confirm local JS tool availability.
