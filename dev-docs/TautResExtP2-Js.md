# Taut Res+Ext Parity — Phase 2: JavaScript

Read [TautResExtP2-Base.md](TautResExtP2-Base.md) first; reuse
[history/TautFloatP2-Js.md](history/TautFloatP2-Js.md) for the tagged-object `Cbor` idiom.

**Files you own:** `src/taut/gen/runtime/cbor.js` (residual accessor present; map is an array of
`[key, Cbor]`) · `src/taut/gen/js.py` (emits the `wireResidual` field) · **NEW**
`src/taut/gen/runtime/ext.js` · `src/tests/test_js.py` + a JS harness (note: `src/tests/js_float_parity.js`
already exists as a pattern).

**Residual (verify+fix).** Generate the fixture `--forward-compat`, run `residual_vectors.json`
decode→re-encode, byte-diff. Verify the emit interleaves known + residual in one ascending order
(`enc`'s `MAP` arm sorts) for an interleaved unknown tag + a band-tag unknown.

**Extensions (implement) — `ext.js`.** Use the exported `CMap([[key, Cbor], …])` constructor — the
`MAP` kind constant is **private** to `cbor.js`, so don't reference it:
`extSet(host, tag, value)` → `decode` host, rebuild `map` without `tag`, push `[tag, value]`,
`encode(CMap(map))` (sorts). `extGet(host, tag)` → the nested `Cbor` or `null`. `extClear(host, tag)`.
Band-check FIRST: `Number.isSafeInteger(tag) && tag >= 2**20` (reject non-integers / unsafe ints so band
tags round-trip like Python ints). **Export `extSet/extGet/extClear` in `module.exports`.** `value` is
`ExtMsg.toCbor(...)`; `extGet` returns the nested `Cbor` for `ExtMsg.fromCbor`.

**Verify:** node available — a harness over both corpora + a differential fuzz vs Python. No deps.
