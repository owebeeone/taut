# Taut Res+Ext Parity — Phase 2: Kotlin

Read [TautResExtP2-Base.md](TautResExtP2-Base.md) first; reuse
[history/TautFloatP2-Kotlin.md](history/TautFloatP2-Kotlin.md) for the class-`Cbor` idiom.

**Files you own:** `src/taut/gen/runtime/cbor.kt` (residual accessor present; map is `List<Pair<Long,Cbor>>`) ·
`src/taut/gen/kotlin.py` (emits the `wireResidual` field) · **NEW** `src/taut/gen/runtime/ext.kt` ·
`src/tests/test_kotlin.py` + a Kotlin harness.

**Residual (verify+fix).** Generate the fixture `--forward-compat`, run `residual_vectors.json`
decode→re-encode, byte-diff. Confirm known + residual emit in one ascending order (`encode` sorts
`map` by key) for an interleaved unknown tag + a band-tag unknown.

**Extensions (implement) — `ext.kt`.** Over `Cbor(map: List<Pair<Long, Cbor>>)`:
`extSet(host: ByteArray, tag: Long, value: Cbor): ByteArray` → `decode` host, rebuild the pair list
without `tag`, add `Pair(tag, value)`, `encode(Cbor.map(...))` (sorts). `extGet(host, tag): Cbor?`
(null if absent). `extClear(host, tag): ByteArray`. Band-check `tag >= 1L shl 20`. `value` is
`ExtMsg.toCbor()`; `extGet` returns the nested `Cbor` for `ExtMsg.fromCbor`.

**Verify:** `kotlinc` is at `/Applications/Android Studio.app/Contents/plugins/Kotlin/kotlinc/bin/kotlinc`.
`test_kotlin.py` gates compiled parity on `shutil.which("kotlinc")`, so **prepend that bin dir to `PATH`**
(and set `JAVA_HOME="/Applications/Android Studio.app/Contents/jbr/Contents/Home"`, since PATH `java` may be
a broken shim) — else the harness silently skips. Run the jar with `$JAVA_HOME/bin/java`. JDK stdlib only.
