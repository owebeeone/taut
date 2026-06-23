# Taut Res+Ext Parity — Phase 2: Kotlin

Read [TautResExtP2-Base.md](TautResExtP2-Base.md) first; reuse
[history/TautFloatP2-Kotlin.md](history/TautFloatP2-Kotlin.md) for the class-`Cbor` idiom.

**Files you own:** **NEW** `src/taut/gen/runtime/ext.kt` · `src/tests/test_kotlin.py`.
Generate the Kotlin parity harness as temporary source from pytest; do not add a checked-in harness
file. `src/taut/gen/runtime/cbor.kt` and `src/taut/gen/kotlin.py` are verify-first only: residual
support appears present (`wireResidual`, `List<Pair<Long,Cbor>>`, sorted map encode), so edit them
only if `residual_vectors.json` demonstrates a real Kotlin divergence.

**Do not change:** `ir/*`, the corpora/generators, Python `ext.py`, `gen/scaffold.py`, another
language, package dependencies, or proven FLOAT/CBOR encode paths unless tied to a failing ResExt
vector.

**Residual (verify+fix).** Generate the fixture `--forward-compat`, run `residual_vectors.json`
decode→re-encode, byte-diff. Confirm known + residual emit in one ascending order (`encode` sorts
`map` by key) for an interleaved unknown tag + a band-tag unknown.

**Extensions (implement) — `ext.kt`.** Over `Cbor(map: List<Pair<Long, Cbor>>)`:
`extSet(host: ByteArray, tag: Long, value: Cbor): ByteArray` → `decode` host, rebuild the pair list
without `tag`, add `Pair(tag, value)`, `encode(Cbor.map(...))` (sorts). `extGet(host, tag): Cbor?`
(null if absent). `extClear(host, tag): ByteArray`. Band-check `tag >= 1L shl 20` before host decode.
Reject non-map hosts; do not coerce them to empty maps. `value` is `Decision.toCbor()`; `extGet`
returns the nested `Cbor` for `Decision.fromCbor`.

**Tests/gates to add:** residual byte parity over all four residual rows; extension byte parity over
all five ext rows through generated `Decision.toCbor()` / `Decision.fromCbor`; below-band tag before
host decode; non-map host rejection; a Kotlin-named D14 gate proving extension schemas fail without
`forward_compat=True` and succeed with it; and a Kotlin runtime-vendoring assertion that
`scaffold.emit(..., langs=["kotlin"], runtime=True, forward_compat=True)` writes both `cbor.kt` and
`ext.kt` after `src/taut/gen/runtime/ext.kt` exists.

**Verify:** do not rely on manual `PATH` setup. Add a checked-in `_find_kotlinc` helper in
`src/tests/test_kotlin.py` mirroring `_find_java`: try `KOTLINC`, then
`/Applications/Android Studio.app/Contents/plugins/Kotlin/kotlinc/bin/kotlinc`, then `PATH`; skip
only after all candidates fail and include searched paths in the skip message. Use the matching JBR
Java when PATH `java` is a broken shim. Required evidence:
`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m pytest -q -p no:cacheprovider src/tests/test_resext_vectors.py src/tests/test_forward_compat.py src/tests/test_kotlin.py`.
Report the discovered `kotlinc`/`java`, corpus parity result, invalid-case result, fuzz seed, and
mismatch count. JDK stdlib only.
