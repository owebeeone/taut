# Taut Res+Ext Parity — Phase 2: Java

Read [TautResExtP2-Base.md](TautResExtP2-Base.md) first; reuse
[history/TautFloatP2-Java.md](history/TautFloatP2-Java.md) for the class-`Cbor` (+ `KV`) idiom.

**Files you own:** `src/taut/gen/runtime/Cbor.java` (residual accessor present; map is `List<KV>`) ·
`src/taut/gen/java.py` (emits the `wireResidual` field) · **NEW** `src/taut/gen/runtime/Ext.java` ·
`src/tests/test_java.py` + `src/tests/java/` harness.

**Residual (verify+fix).** Generate the fixture `--forward-compat`, run `residual_vectors.json`
decode→re-encode, byte-diff. Confirm known + residual emit in one ascending order (`enc`'s `MAP`
arm sorts `List<KV>` by `k`) for an interleaved unknown tag + a band-tag unknown.

**Extensions (implement) — `Ext.java`** (in `package taut` — it uses `Cbor` + the package-private `KV`).
Over `Cbor` (`List<KV> map`):
`static byte[] extSet(byte[] host, long tag, Cbor value)` → `Cbor.decode(host)`, rebuild
`List<KV>` without `tag`, add `new KV(tag, value)`, `Cbor.encode(Cbor.map(list))` (sorts).
`static Cbor extGet(byte[] host, long tag)` (null if absent). `static byte[] extClear(byte[] host, long tag)`.
Band-check `tag >= (1L << 20)`. `value` is `ExtMsg.toCbor()`; `extGet` returns the nested `Cbor` for
`ExtMsg.fromCbor`.

**Verify:** use a working JDK — try PATH `javac`/`java` first (a real JDK 17+ is fine); if those are a
broken asdf shim ("Unable to locate a Java Runtime"), use Android Studio's JBR:
`JAVA_HOME="/Applications/Android Studio.app/Contents/jbr/Contents/Home"`, then `"$JAVA_HOME/bin/javac"` /
`"$JAVA_HOME/bin/java"`. Build a harness over both corpora + a differential fuzz. JDK stdlib only.
