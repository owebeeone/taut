# Taut ResExt Phase 2 JS Prompt Review 55-3

## Findings

No P0/P1/P2 findings. The JS Phase 2 prompt is now implementable as written, with one
low-severity wording issue below.

### [P3] `ExtMsg.toCbor(...)` wording does not match the generated JS method shape

The JS prompt now correctly requires the typed extension path, but the final sentence says
`value` is `ExtMsg.toCbor(...)` (`dev-docs/TautResExtP2-Js.md:20` through
`dev-docs/TautResExtP2-Js.md:21`). Generated JS types expose `toCbor()` as an instance method
and `fromCbor()` as a static method (`src/taut/gen/js.py:61` through `src/taut/gen/js.py:76`).
So the harness should use a shape like `new Decision(...).toCbor()`, or, for corpus rows,
`Decision.fromCbor(decode(valueHex)).toCbor()`.

This is not a blocker: the base brief now explicitly requires the harness to exercise generated
`to_cbor`/`from_cbor` and compare `get` rows by re-encoding the returned value
(`dev-docs/TautResExtP2-Base.md:74` through `dev-docs/TautResExtP2-Base.md:83`). Tightening the
JS line would prevent a literal static-method implementation attempt.

## Proposed Resolutions

1. **Fix the generated-type wording**
   - **Resolution:** Change the JS prompt's `ExtMsg.toCbor(...)` phrase to the generated instance/static shape: construct or decode a `Decision`, call `decision.toCbor()` for `extSet`, and call `Decision.fromCbor(got)` for `extGet`.
   - **Verification:** The JS ResExt harness should include the corpus path `Decision.fromCbor(decode(valueHex)).toCbor()` for set/replace rows and should re-encode the returned `Cbor` for get rows before comparing to `expect`.

No other JS prompt change is required before implementation.

## Prior Issues

- **Resolved: missing Phase 1 artifacts.** The current tree has `ir/resext.taut.py`
  (`ir/resext.taut.py:16` through `ir/resext.taut.py:25`), the four residual vectors
  (`corpus/residual_vectors.json:1` through `corpus/residual_vectors.json:22`), and the five
  extension vectors (`corpus/ext_vectors.json:1` through `corpus/ext_vectors.json:43`).
  `run_tests.py` regenerates the ResExt corpora (`run_tests.py:17` through `run_tests.py:24`),
  and `src/tests/test_resext_vectors.py` locks the committed corpora to the generator
  (`src/tests/test_resext_vectors.py:21` through `src/tests/test_resext_vectors.py:28`).
- **Resolved: missing scaffold/runtime slot.** JS now has `("ext.js", "ext.js")` in
  `_RUNTIMES` (`src/taut/gen/scaffold.py:32` through `src/taut/gen/scaffold.py:40`), and
  `emit()` vendors runtime resources that exist while skipping Phase-2 files that have not
  landed yet (`src/taut/gen/scaffold.py:600` through `src/taut/gen/scaffold.py:607`). The
  package-data glob already includes `*.js` runtime resources (`pyproject.toml:38` through
  `pyproject.toml:40`).
- **Resolved: `extGet` return ambiguity.** The base brief now allows idiomatic per-language
  typed or generic surfaces while requiring byte parity and generated-type exercise
  (`dev-docs/TautResExtP2-Base.md:74` through `dev-docs/TautResExtP2-Base.md:83`). The JS
  prompt explicitly specifies the generic-CBOR surface: `extGet(host, tag)` returns the nested
  `Cbor` or `null` for `ExtMsg.fromCbor` (`dev-docs/TautResExtP2-Js.md:17` through
  `dev-docs/TautResExtP2-Js.md:21`).
- **Resolved: differential fuzz contract.** The base brief now makes corpus parity the hard
  checked-in gate and defines fuzzing as supporting evidence with a deterministic fixed seed,
  at least 1000 iterations, mismatch reporting, Python-oracle ownership, and toolchain-absent
  handling (`dev-docs/TautResExtP2-Base.md:100` through `dev-docs/TautResExtP2-Base.md:113`).
  The JS brief can stay short because it tells the agent to read the base first
  (`dev-docs/TautResExtP2-Js.md:3` through `dev-docs/TautResExtP2-Js.md:4`).
- **Resolved: band-check ordering.** The JS brief now says `Band-check FIRST` and pins
  `Number.isSafeInteger(tag) && tag >= 2**20` (`dev-docs/TautResExtP2-Js.md:17` through
  `dev-docs/TautResExtP2-Js.md:21`), matching the base requirement and Python's `_check` before
  decoding (`src/taut/ext.py:24` through `src/taut/ext.py:45`).
- **Resolved: unexported `MAP` constant.** The JS prompt now explicitly says to use exported
  `CMap(...)` and not reference private `MAP` (`dev-docs/TautResExtP2-Js.md:15` through
  `dev-docs/TautResExtP2-Js.md:18`). The runtime exports `CMap`, `encode`, and `decode`, while
  keeping `MAP` private (`src/taut/gen/runtime/cbor.js:8` through
  `src/taut/gen/runtime/cbor.js:16`, `src/taut/gen/runtime/cbor.js:203`).

## Implementability Assessment

The JS Phase 2 prompt is ready for implementation. Residual verification has a committed
fixture and corpus, generated JS already emits `wireResidual` only under `forward_compat`
(`src/taut/gen/js.py:57` through `src/taut/gen/js.py:88`), and `cbor.js` sorts map keys on
encode (`src/taut/gen/runtime/cbor.js:147` through `src/taut/gen/runtime/cbor.js:150`), which
is the required interleave behavior.

The extension work is now within JS ownership: add `src/taut/gen/runtime/ext.js`, use the
exported `CMap`/`decode`/`encode` surface (`src/taut/gen/runtime/cbor.js:16`,
`src/taut/gen/runtime/cbor.js:176` through `src/taut/gen/runtime/cbor.js:180`,
`src/taut/gen/runtime/cbor.js:203`), and add JS tests/harness code under `src/tests/test_js.py`
plus a JS harness following the existing Node precedent (`src/tests/js_float_parity.js:31`
through `src/tests/js_float_parity.js:58`). No scaffold or corpus-generator edits are required.

## Scope Inspected

- `dev-docs/TautResExtPlan.md`
- `dev-docs/TautResExtP2-Base.md`
- `dev-docs/TautResExtP2-Js.md`
- `dev-docs/TautResExtP2-Js-Review55.md`
- `dev-docs/TautResExtP2-Js-Review55-2.md`
- `dev-docs/history/TautFloatP2-Js.md`
- `ir/resext.taut.py`
- `corpus/residual_vectors.json`
- `corpus/ext_vectors.json`
- `src/taut/corpus/resext_build.py`
- `src/tests/test_resext_vectors.py`
- `src/taut/gen/scaffold.py`
- `src/taut/gen/js.py`
- `src/taut/gen/runtime/cbor.js`
- `src/taut/gen/runtime/__init__.py`
- `src/taut/ext.py`
- `src/tests/test_js.py`
- `src/tests/js_float_parity.js`
- `src/tests/test_forward_compat.py`
- `src/taut/cli.py`
- `run_tests.py`
- `pyproject.toml`

## Verification

No implementation tests were run; this was a prompt/state review only. I inspected the current
repository state and confirmed local Node availability with `node --version` (`v22.19.0`).
