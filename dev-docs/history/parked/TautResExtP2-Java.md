# Taut Res+Ext Parity — Phase 2: Java

Read [TautResExtP2-Base.md](TautResExtP2-Base.md) first; reuse
[history/TautFloatP2-Java.md](history/TautFloatP2-Java.md) for the class-`Cbor` (+ `KV`) idiom.

**Files you own:** **NEW** `src/taut/gen/runtime/Ext.java` · `src/tests/test_java.py`.
Generate the Java parity/API harnesses as temporary sources from pytest; do not add checked-in Java
harness files. `src/taut/gen/runtime/Cbor.java` and `src/taut/gen/java.py` are verify-first only:
residual support appears present (`wireResidual`, `List<KV>`, sorted map encode), so edit them only
if `residual_vectors.json` demonstrates a real Java divergence.

**Do not change:** `ir/*`, the corpora/generators, Python `ext.py`, `gen/scaffold.py`, another
language, package dependencies, or proven FLOAT/CBOR encode paths unless tied to a failing ResExt
vector.

**Residual (verify+fix).** Generate the fixture `--forward-compat`, run `residual_vectors.json`
decode→re-encode, byte-diff. Confirm known + residual emit in one ascending order (`enc`'s `MAP`
arm sorts `List<KV>` by `k`) for an interleaved unknown tag + a band-tag unknown.

**Extensions (implement) — `Ext.java`** (in `package taut` — it uses `Cbor` + the package-private `KV`).
Pin the public runtime API exactly:

```java
package taut;

public final class Ext {
    private Ext() {}
    public static byte[] extSet(byte[] host, long tag, Cbor value) { ... }
    public static Cbor extGet(byte[] host, long tag) { ... }
    public static byte[] extClear(byte[] host, long tag) { ... }
}
```

Over `Cbor` (`List<KV> map`):
`static byte[] extSet(byte[] host, long tag, Cbor value)` → `Cbor.decode(host)`, rebuild
`List<KV>` without `tag`, add `new KV(tag, value)`, `Cbor.encode(Cbor.map(list))` (sorts).
`static Cbor extGet(byte[] host, long tag)` (null if absent). `static byte[] extClear(byte[] host, long tag)`.
Band-check `tag >= (1L << 20)` before host decode; throw `IllegalArgumentException` for below-band
tags and for decoded hosts whose root `kind != Cbor.MAP`. Inspect `decoded.kind` directly; do not
use `mapEntries()` as a scalar-to-empty-map fallback. `value` is `Decision.toCbor()`; `extGet`
returns the nested `Cbor` for `Decision.fromCbor`.

**Tests/gates to add:** residual byte parity over all four residual rows; extension byte parity over
all five ext rows through generated `Decision.toCbor()` / `Decision.fromCbor`; below-band tag before
host decode; scalar/non-map host rejection; a valid above-band host assertion; and a public API
compile/reflection/source assertion proving callers outside `package taut` can access
`taut.Ext.extSet`, `taut.Ext.extGet`, and `taut.Ext.extClear`. The ResExt harness that calls generated
`Host`/`Decision` may declare `package taut`, matching `src/tests/java/FloatParity.java`, but the
public `Ext` accessibility check must be separate.

**Verify:** use a working JDK — try PATH `javac`/`java` first (a real JDK 17+ is fine); if those are a
broken asdf shim ("Unable to locate a Java Runtime"), use Android Studio's JBR:
`JAVA_HOME="/Applications/Android Studio.app/Contents/jbr/Contents/Home"`, then `"$JAVA_HOME/bin/javac"` /
`"$JAVA_HOME/bin/java"`. Required evidence:
`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m pytest -q -p no:cacheprovider src/tests/test_resext_vectors.py src/tests/test_forward_compat.py src/tests/test_java.py`.
Report the JDK used, corpus parity result, invalid-case result, public API check, fuzz seed, and
mismatch count. JDK stdlib only.
