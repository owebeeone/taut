# Taut Res+Ext Phase 2 Java Prompt Review - Third Pass

## Findings

### P1 - The Java `Ext` surface still does not pin public access modifiers

The earlier malformed `extSet(Cbor host?/byte[] host, ...)` issue is resolved: the Java brief now
uses `static byte[] extSet(byte[] host, long tag, Cbor value)`, `static Cbor extGet(...)`, and
`static byte[] extClear(...)` (`dev-docs/TautResExtP2-Java.md:14`-`20`). It also explicitly puts
`Ext.java` in `package taut`, which fixes the package-side part of the second-pass concern.

What remains is the shipped Java API shape. The brief says only `static`, not `public static`, and
does not say `public final class Ext` (`dev-docs/TautResExtP2-Java.md:16`-`18`). If an implementer
copies that literally, Java's default package-private class/method visibility can pass a harness
that also declares `package taut`, but it does not expose the extension accessor API to normal
downstream Java callers. That is inconsistent with the deliverable of porting an active accessor
API to non-Python targets (`dev-docs/TautResExtPlan.md:30`-`32`) and with `Cbor.java` being a public
runtime class (`src/taut/gen/runtime/Cbor.java:12`).

The prompt should pin this exact shape:

```java
package taut;

public final class Ext {
    private Ext() {}
    public static byte[] extSet(byte[] host, long tag, Cbor value);
    public static Cbor extGet(byte[] host, long tag);
    public static byte[] extClear(byte[] host, long tag);
}
```

### P2 - Java-specific error semantics are still easy to get wrong from the short prompt

The base brief is clear that the extension band check must happen before decoding the host, that
below-band tags are hard errors, and that non-map hosts must not be silently coerced into maps
(`dev-docs/TautResExtP2-Base.md:52`-`70`). The Java brief compresses this to "Band-check
`tag >= (1L << 20)`" after the one-line `Cbor.decode(host)` algorithm and does not name the Java
exception type (`dev-docs/TautResExtP2-Java.md:16`-`20`).

That is implementable by a careful agent who follows the base brief, but it leaves a Java-specific
trap: `Cbor.mapEntries()` returns an empty list for non-map values (`src/taut/gen/runtime/Cbor.java:39`).
Using that helper inside `Ext.extSet` or `Ext.extClear` would turn a scalar host into a new map
instead of throwing, violating the base contract. The Java prompt should say to throw
`IllegalArgumentException` for `tag < (1L << 20)` before `Cbor.decode(host)`, and to reject
`decoded.kind != Cbor.MAP` rather than using `mapEntries()` as a fallback.

### P3 - Harness package access remains implicit

Generated Java messages are package-private, and their `toCbor()` / `fromCbor()` methods are also
package-private (`src/taut/gen/java.py:84`-`104`). `KV` is package-private too
(`src/taut/gen/runtime/Cbor.java:194`-`198`). The Java prompt now correctly says `Ext.java` belongs
in `package taut` (`dev-docs/TautResExtP2-Java.md:14`), but it still does not say the Java ResExt
harness must also declare `package taut` when it calls generated `Host` / `Decision` methods.

This is a small compile-time footgun, not a semantic blocker. The existing Java float harness uses
`package taut` (`src/tests/java/FloatParity.java:1`), so the ResExt harness should follow that
pattern.

## Proposed Resolutions

1. **Pin the public Java runtime API**
   - **Resolution:** Update the Java prompt to require `package taut; public final class Ext` with a private constructor and `public static` methods for `extSet`, `extGet`, and `extClear`. Package-private methods should be considered a failed implementation even if the in-package harness compiles.
   - **Verification:** Add a small compile check from outside `package taut`, or an equivalent reflection/source assertion, that proves downstream callers can access `taut.Ext.extSet`, `taut.Ext.extGet`, and `taut.Ext.extClear`.

2. **Make Java error semantics explicit**
   - **Resolution:** Require `IllegalArgumentException` for `tag < (1L << 20)` before decoding host bytes, and for decoded hosts whose root kind is not `Cbor.MAP`. The implementation must inspect `decoded.kind` directly and must not rely on `mapEntries()` as a scalar-to-empty-map fallback.
   - **Verification:** Add Java harness assertions for below-band tag, scalar/non-map host, and valid above-band host. The below-band test should prove host bytes are not decoded first.

3. **State harness package placement**
   - **Resolution:** Require the generated ResExt Java harness to declare `package taut`, matching the existing float parity harness, so it can call package-private generated `Host`/`Decision` methods while still separately checking that `Ext` itself is public.
   - **Verification:** The temporary Java harness should compile in `package taut` and exercise generated `Decision.toCbor()` / `Decision.fromCbor()` for extension rows.

## Prior Issue Status

- **Resolved:** Prior P0 "Phase 1 artifacts required by the Java prompt are not present." The plan
  now marks Phase 1 landed with `ir/resext.taut.py`, both corpora, regen gates, and ext runtime
  slots (`dev-docs/TautResExtPlan.md:51`-`55`). The base brief lists the same shared surface as
  present (`dev-docs/TautResExtP2-Base.md:18`-`29`). `run_tests.py` regenerates ResExt corpora
  (`run_tests.py:17`-`24`), and the committed JSON files contain the expected 4 residual and 5 ext
  hex rows.
- **Resolved:** Prior P0 "`Ext.java` cannot be distributed by `--with-runtime` without scaffold."
  `_RUNTIMES["java"]` now includes `("Ext.java", "Ext.java")`, and `emit()` vendors existing runtime
  resources while skipping missing Phase 2 files (`src/taut/gen/scaffold.py:32`-`39`,
  `src/taut/gen/scaffold.py:600`-`607`). Package data already includes `*.java`
  (`pyproject.toml:38`-`40`).
- **Mostly resolved:** Prior P1 "Java `extSet` signature is ambiguous." The host type is now
  unambiguously `byte[]`, `value` is a nested `Cbor`, and `extGet` returns `Cbor` for generated
  `Decision.fromCbor`. The remaining gap is public class/method visibility and exact exception
  semantics.
- **Resolved:** Prior P1 "JDK-stdlib-only corpus harness is under-specified." The corpora are simple
  parse-free hex JSON rows generated by `src/taut/corpus/resext_build.py`, and the base brief now
  states that pytest owns JSON/fuzz I/O while the compiled harness only receives generated vector
  tables and reports pass/fail (`dev-docs/TautResExtP2-Base.md:100`-`113`).
- **Resolved:** Prior P2 "toolchain instruction appears stale." The Java brief now says to try PATH
  `javac`/`java` first and use Android Studio's JBR only if PATH is a broken shim
  (`dev-docs/TautResExtP2-Java.md:22`-`25`).
- **Mostly resolved:** Prior P2 "residual ownership invites unnecessary edits." The Java prompt
  still lists `Cbor.java` and `java.py` as owned files, but it now frames residual work as
  "verify+fix" (`dev-docs/TautResExtP2-Java.md:10`-`12`), and the base workflow says residual is
  done if the corpus is green and to fix only a real divergence (`dev-docs/TautResExtP2-Base.md:95`-`99`).
- **Partially resolved:** Prior P2 "package/access assumptions should be explicit." `package taut`
  is explicit for `Ext.java`; harness package placement and public `Ext` visibility are still
  implicit.

## Current Implementability Summary

There are no remaining Phase 1 or repository-state blockers. The Java Phase 2 task is now
implementable by a careful agent who reads the base brief and supplies the obvious Java API details:
`Ext` as a public runtime class, public static methods, `IllegalArgumentException` for invalid
extension operations, and a `package taut` harness.

I would still tighten the Java prompt before isolated fan-out because the remaining gaps are exactly
where an implementation can pass local byte corpora while shipping a package-private API or missing
Java-only error semantics. No additional shared scaffold, corpus, or generator prerequisite appears
necessary.

## Verification Performed

- `PYTHONPATH=src python -m pytest src/tests/test_resext_vectors.py src/tests/test_java.py src/tests/test_forward_compat.py -q`
  - Result: `21 passed in 0.06s`.
- `python run_tests.py`
  - Result: `187 passed, 1 skipped in 3.74s`.
- Generated `ir/resext.taut.py` to a temporary directory with
  `PYTHONPATH=src python -m taut.cli gen ir/resext.taut.py --lang java --api-only --with-runtime --forward-compat -o <tmp>`
  and compiled the emitted Java files with `javac`.
  - Result: generated `api.java` and `Cbor.java` compiled successfully. `Ext.java` was not emitted
    because the Phase 2 file does not exist yet, matching the scaffold's skip-until-present behavior.
