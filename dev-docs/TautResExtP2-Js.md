# Taut Res+Ext Parity — Phase 2: JavaScript

Read [TautResExtP2-Base.md](TautResExtP2-Base.md) first; reuse
[history/TautFloatP2-Js.md](history/TautFloatP2-Js.md) for the tagged-object `Cbor` idiom.

**Files you own:** **NEW** `src/taut/gen/runtime/ext.js` · `src/tests/test_js.py`.
Generate the JS parity harness as temporary source from pytest; do not add a checked-in JS harness
file (note: `src/tests/js_float_parity.js` already exists as a pattern).
`src/taut/gen/runtime/cbor.js` and `src/taut/gen/js.py` are
verify-first only: residual support appears present (`wireResidual`, array-of-`[key, Cbor]`, sorted
map encode), so edit them only if `residual_vectors.json` demonstrates a real JS divergence.

**Do not change:** `ir/*`, the corpora/generators, Python `ext.py`, `gen/scaffold.py`, another
language, package dependencies, or proven FLOAT/CBOR encode paths unless tied to a failing ResExt
vector.

**Residual (verify+fix).** Generate the fixture `--forward-compat`, run `residual_vectors.json`
decode→re-encode, byte-diff. Verify the emit interleaves known + residual in one ascending order
(`enc`'s `MAP` arm sorts) for an interleaved unknown tag + a band-tag unknown.

**Extensions (implement) — `ext.js`.** Use the exported `CMap([[key, Cbor], …])` constructor — the
`MAP` kind constant is **private** to `cbor.js`, so don't reference it:
`extSet(host, tag, value)` → `decode` host, rebuild `map` without `tag`, push `[tag, value]`,
`encode(CMap(map))` (sorts). `extGet(host, tag)` → the nested `Cbor` or `null`. `extClear(host, tag)`.
Band-check FIRST: `Number.isSafeInteger(tag) && tag >= 2**20` (reject non-integers / unsafe ints so band
tags round-trip like Python ints). Reject non-map hosts; do not coerce them to empty maps. **Export
`extSet/extGet/extClear` in `module.exports`.** `value` is built through the generated `Decision`
path: construct or decode a `Decision`, call `decision.toCbor()` for `extSet`, and call
`Decision.fromCbor(got)` for `extGet`. For corpus set/replace rows, use
`Decision.fromCbor(decode(hexToBytes(valueHex))).toCbor()`; do not hand-build equivalent maps.

**Tests/gates to add:** residual byte parity over all four residual rows; extension byte parity over
all five ext rows, including re-encoding the returned `Cbor` for `get` rows before comparing to
`expect`; below-band tag before host decode; non-map host rejection; exported accessor assertions;
and the fixed-seed differential fuzz described by the base brief.

**Required evidence:** run
`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m pytest -q -p no:cacheprovider src/tests/test_resext_vectors.py src/tests/test_js.py`.
Report `node --version`, corpus parity result, invalid-case result, fuzz seed, and mismatch count.
No deps.
