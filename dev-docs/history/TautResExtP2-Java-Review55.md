# Taut Res+Ext Phase 2 Java Prompt Review

## Findings

### P0 - Phase 1 artifacts required by the Java prompt are not present

The Java brief is not implementable as written in this checkout because it assumes the Phase 1 shared surface has already landed. The base brief declares `corpus/residual_vectors.json` and `corpus/ext_vectors.json` as the parse-free oracle files (`dev-docs/TautResExtP2-Base.md:19`-`22`), and the Java prompt instructs the agent to run those corpora (`dev-docs/TautResExtP2-Java.md:10`, `dev-docs/TautResExtP2-Java.md:23`). The plan says Phase 1.2 should emit and commit both files and wire their regen gates (`dev-docs/TautResExtPlan.md:55`-`58`), and Phase 1.3 should commit the fixture schema(s) as IR (`dev-docs/TautResExtPlan.md:59`-`61`).

Current repo state does not match that premise: `corpus/` contains only float/glade/griplab artifacts, `run_tests.py` regenerates only the existing corpus/float/glade/CRDT artifacts (`run_tests.py:17`-`23`), and `src/taut/corpus/kit.py` still exposes only a Rust harness (`src/taut/corpus/kit.py:89`-`93`). A Java Phase 2 agent would have to invent or add shared corpora/generators/schema files, but the base brief explicitly forbids editing corpus generators, `ir/*`, and shared scaffold files (`dev-docs/TautResExtP2-Base.md:63`-`68`). That is a scope contradiction and should be resolved before starting Java implementation.

### P0 - `Ext.java` cannot be distributed by `--with-runtime` without an out-of-scope scaffold change

The Java prompt asks the agent to add `src/taut/gen/runtime/Ext.java` while listing only Java runtime/generator/tests as owned files (`dev-docs/TautResExtP2-Java.md:6`-`8`). The plan says Phase 1.3 should add the vendored `ext.<lang>` runtime slot to `_RUNTIMES`/scaffold so Phase 2 agents only drop in their language module (`dev-docs/TautResExtPlan.md:59`-`61`), but that scaffold change is not present. `_RUNTIMES` currently has only `"java": ("Cbor.java", "Cbor.java")` (`src/taut/gen/scaffold.py:30`-`38`), and `scaffold.emit(..., runtime=True)` emits exactly that configured runtime file (`src/taut/gen/scaffold.py:594`-`599`).

As written, adding `Ext.java` would allow ad hoc tests to compile it directly, but generated Java outputs using `--with-runtime` would still omit the extension accessor module. Fixing that requires either a Phase 1 scaffold update or adding `src/taut/gen/scaffold.py` to the Java agent's allowed files. Otherwise the extension deliverable is not actually shipped through the repo's generator path.

### P1 - The Java `extSet` signature is ambiguous enough to split implementations

The base contract says `ext_set(host_bytes, tag, ext_value) -> bytes` operates on host wire bytes (`dev-docs/TautResExtP2-Base.md:42`-`52`). The Java brief instead sketches ``static byte[] extSet(Cbor host?/byte[] host, long tag, Cbor value)`` (`dev-docs/TautResExtP2-Java.md:14`-`16`), then uses `Cbor.decode(host)` as if `host` is bytes. That leaves the implementer to choose between a `byte[]` API, a `Cbor` API, overloads, or a malformed hybrid.

For byte-exact cross-language parity, the prompt should specify the exact Java surface, for example `public static byte[] extSet(byte[] host, long tag, Cbor value)`, `public static Cbor extGet(byte[] host, long tag)`, and `public static byte[] extClear(byte[] host, long tag)`. It should also name the below-band failure mode, likely `IllegalArgumentException`, and say what happens when `host` is not a top-level map. Without that, tests and downstream users may bind to different APIs even if the bytes happen to match locally.

### P1 - JDK-stdlib-only corpus harness is under-specified for the expected JSON corpora

The prompt requires a Java harness over both corpora plus differential fuzz while also requiring JDK stdlib only (`dev-docs/TautResExtP2-Java.md:21`-`24`). The only existing Java harness pattern is `FloatParity.java`, which uses a regex tailored to the simple float vector rows (`src/tests/java/FloatParity.java:9`-`15`). The planned residual/ext corpora are not present, their JSON shape is not available to inspect, and the conformance kit does not emit a Java harness (`src/taut/corpus/kit.py:89`-`93`).

This is likely implementable if Phase 1 emits a Java-friendly vector source, or if the corpora are intentionally constrained to simple hex fields that can be parsed safely without a JSON library. The prompt does not say that. A Java agent may end up writing a brittle regex parser for a more complex JSON shape or expanding scope into shared corpus/harness generation.

### P2 - The Java toolchain instruction appears stale on this checkout

The Java brief says PATH `java`/`javac` are broken and mandates Android Studio's JDK (`dev-docs/TautResExtP2-Java.md:21`-`23`). In this environment, `/usr/bin/java` and `/usr/bin/javac` both resolve and report OpenJDK `21.0.10`, matching the Android Studio JBR version. The Android Studio path also exists, so the instruction is not fatal, but it should be softened to "if PATH shims are broken" or expressed as a fallback. Otherwise the prompt encodes machine-local state that is already stale.

### P2 - The prompt lists `java.py` as owned, but residual code likely only needs verification

The existing Java generator already emits `wireResidual`, appends it to the generated map, and relies on sorted CBOR map encoding (`src/taut/gen/java.py:88`-`100`, `src/taut/gen/java.py:113`-`115`). The runtime `MAP` encoder sorts `List<KV>` by key before emission (`src/taut/gen/runtime/Cbor.java:147`-`151`), and `mapEntries()` exposes residual capture (`src/taut/gen/runtime/Cbor.java:34`-`39`). I generated Java with `--forward-compat --with-runtime` for the existing Razel IR in `/tmp` and it compiled successfully with `javac`.

This means the residual half is probably a verification task once the corpora exist. The prompt should emphasize not touching `src/taut/gen/java.py` or `Cbor.java` unless the byte corpus exposes an actual divergence. That would reduce regression risk in the FLOAT-proven encode path, which the base brief explicitly warns not to disturb (`dev-docs/TautResExtP2-Base.md:68`).

### P2 - Package/access assumptions should be made explicit for `Ext.java`

`Cbor` is public, but `KV` is package-private in the same source file (`src/taut/gen/runtime/Cbor.java:194`-`198`), and generated message classes plus `toCbor`/`fromCbor` are also package-private (`src/taut/gen/java.py:84`-`91`, `src/taut/gen/java.py:103`-`117`). `Ext.java` will therefore need to be emitted in `package taut;` and compiled alongside generated `api.java`/`Cbor.java`. That is probably intended, but the Java prompt should say it directly so an implementer does not create a different package or public-facing helper that cannot access `KV`.

## Current Implementability Summary

The low-level Java runtime shape is suitable for residual and extension work: top-level maps are `List<KV>`, `Cbor.encode` sorts keys, `Cbor.decode` yields a `Cbor` tree, and generated forward-compatible messages already carry and re-emit residuals. The extension accessor itself is small and straightforward once the API is made exact.

The prompt is not ready as an isolated Phase 2 task because required Phase 1 artifacts are missing and the new runtime file is not wired into scaffold output. Starting from this prompt would either force the Java agent to edit forbidden shared files or produce an `Ext.java` that passes local ad hoc tests but is not included in generated Java runtimes.

## Open Questions

- Should Phase 1 land `residual_vectors.json`, `ext_vectors.json`, fixture IR, and `_RUNTIMES` ext wiring before the Java agent starts, or should the Java prompt explicitly expand ownership to those shared files?
- Should Java expose only the generic `Cbor` accessor API, or should it also provide typed helpers around generated `ExtMsg.toCbor()` / `ExtMsg.fromCbor()`?
- What exact JSON shape should the JDK-only Java harness parse, and should Phase 1 generate a Java vector source to avoid hand-rolled JSON parsing?

## Residual Risks / Test Gaps

- No in-repo Java residual byte-parity test exists yet; `src/tests/test_java.py` currently checks generator shape only.
- No Java extension accessor exists yet, and no generated-runtime test proves it is emitted by `--with-runtime`.
- Differential fuzz requirements are stated at a high level, but seed, iteration count, fixture schema, and mismatch reporting format are not specified.
