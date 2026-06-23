# Taut Float — Phase 2 Java — Independent Code Review (CR48)

**Reviewer:** independent second pass (skeptical, empirical). Companion to CR55.
**Date:** 2026-06-23

## Verdict

**Approve with nits.** The implementation is byte-exact against the Python oracle
across **579,698 doubles, 0 mismatches, 0 decode→re-encode round-trip failures**,
including the full 22-row corpus, every one of the 65,536 half bit patterns and their
±1-double-ULP neighbours, all subnormal/boundary cases the brief enumerates, and
non-canonical-width NaN/Inf decode paths. The hand-rolled `doubleToHalfBits` narrowing
is correct (direct double→half RNE — no double-rounding). The constructor ripple is
complete; no factory was missed; no new dependencies; only owned files changed. The
single substantive issue is a **packaging gap** (the Java parity harness is untracked),
already flagged by CR55 — confirmed, but **P2, not a code-correctness blocker**.

---

## What I verified, and how

Toolchain: PATH `java`/`javac` are broken, so I used Android Studio's JDK 21
(`JAVA_HOME="/Applications/Android Studio.app/Contents/jbr/Contents/Home"`). Oracle:
`cd taut-java && PYTHONPATH=src python3 -c "from taut.wire import cbor; ..."`.
All harnesses live in `/tmp/jfloat` (nothing written into the repo except this review).

### (a) Corpus parity — PASS (22/22)

Compiled the runtime + the author's harness and ran it over the contract file:

```
javac -d /tmp/jfloat/out Cbor.java FloatParity.java
java  -cp /tmp/jfloat/out taut.FloatParity corpus/float_vectors.json
  -> ok 22 float vectors
```

`FloatParity` asserts, per row: `encode(double(f64bits)) == cbor`, `decode(cbor).kind
== FLOAT`, `encode(decode(cbor)) == cbor`, and (non-NaN rows) `rawLongBits(decode) ==
f64`. All 22 pass.

### (b) Differential fuzz vs the Python oracle — PASS (0 mismatches / 579,698)

A `/tmp/jfloat/FloatHarness.java` reads f64-bit-hex on stdin, encodes via
`Cbor.encode(Cbor.float_(v))`, and emits CBOR hex (plus a `RTFAIL` marker if
`encode(decode(encode(v))) != encode(v)`). The oracle (`/tmp/jfloat/oracle.py`) emits
`cbor.dumps(v).hex()` for the same bit-patterns. Three independent datasets, diffed
column-for-column:

| Dataset | Doubles | Mismatches | RTFAIL |
|---|---:|---:|---:|
| Structured + random (`gen_doubles.py`, seed 0xC0FFEE): full 65,536 half-pattern widening, ±0, ±Inf, 7 NaN payloads, half/single/double subnormals, 65504/65505/65519/65520/65535, 2^-14/-24/-25/-26/-149/-1074, max-single, max-double, near-miss-not-half, plain ints incl. 2^53±1, huge magnitudes, half-tie & single-tie nudges, 10k random u64 + 5k log-uniform | 89,228 | **0** | 0 |
| Exhaustive half-exactness boundary: all 65,536 half values widened to double **plus each ±1 double-ULP neighbour** (the values that must *not* shrink to half) | 190,470 | **0** | 0 |
| Fresh-seed random (seed 999999): 200k random u64 + 100k log-uniform in half/single range | 300,000 | **0** | 0 |
| **Total** | **579,698** | **0** | **0** |

The middle dataset is the decisive one for the shortest-form decision: it brackets
every half value on both sides by one double-ULP, so any off-by-one in the
half-exactness round-trip test (`widen(narrow(v)) bit== v`) would surface. None did.

### (c) Double-rounding trap — analysed and empirically cleared

I tried to construct a witness where double→half-direct and double→float→half disagree
on the **encode decision**. They cannot, by structure: a value is half-exact iff
`widen(narrow(v)) == v`; any such value is exactly a half value, which is also exactly a
`float`, so `(float)v` is lossless and the two paths coincide. I confirmed this
empirically — 5,000,000 random doubles in half's dynamic range produced **0**
exactness-decision disagreements between the direct and via-float paths. Crucially, this
codec is immune *by architecture* regardless: `encFloat` (Cbor.java:125–126) narrows
**directly** via `doubleToHalfBits`, then verifies with a full `halfToDouble` round-trip
bit-compare. It never narrows through `float` for the half path. The single (`FA`) path
at Cbor.java:131–132 uses a single `(float)v` round and re-verifies bit-equality — also
correct.

### (d) NaN / Inf / width-lenient decode — PASS

`encFloat` checks `Double.isNaN(v)` first (Cbor.java:119) and emits `f9 7e 00` before
any width test — every NaN payload canonicalises. Verified decode→re-encode of
non-canonical widths against the oracle (corpus only carries half-NaN):

```
fa7fc00000 (single qNaN)      -> f97e00    fa7f800001 (single sNaN) -> f97e00
fb7ff8000000000000 (dbl qNaN) -> f97e00    fb7ff0000000000001 (sNaN)-> f97e00
faff800000 (single -Inf)      -> f9fc00    fb7ff0...0 (dbl +Inf)    -> f97c00
fbc7efffffe0000000 (-maxsingle as dbl) -> faff7fffff (shrinks to FA)
```
Java and Python agree on all eight. The single-sNaN case proves the decode produces a
double that `Double.isNaN` catches (JVM `float`→`double` NaN handling is a non-issue
because re-canonicalisation happens on re-encode). −0.0 → `f98000` and +0.0 → `f90000`
are distinguished (bit-compare, not `==`) — confirmed in the corpus and the generated
round-trip below.

### (e) Constructor ripple — COMPLETE (the Java-specific risk)

The private constructor gained a positional `double d` (Cbor.java:22). All **8** call
sites pass 7 args with `d` in slot 3 — `0.0` for non-floats, `v` for `float_`:
`int_`, `float_`, `text`, `bytes`, `bool`, `arr`, `map`, and the `NUL` constant
(Cbor.java:25–32). None missed (and the harness compiles, which Java would reject on any
arity mismatch). Factory is named `float_` (Cbor.java:26), avoiding the `float` keyword,
matching `int_`.

### (f) Codegen + value-model integration — PASS

Generated a float-bearing message (scalar / optional / `List<float>` / `Map<int,float>`),
compiled it against the runtime, and exercised a full round-trip:

```
public double x;  public Double maybe;
public java.util.List<Double> xs;  public java.util.Map<Long, Double> by_id;
... Cbor.float_(x) ... e -> e.d ...
```
Round-trip output: `x=0.1 maybe=-0.0 negzero-preserved=true`,
`xs=[1.5, 100000.0, 65504.0]`, `by_id={7=3.141592653589793}`,
wire `a401fb…02f98000…` — note `maybe=-0.0` survives as `f98000`. `_java_ty`/`_enc`/`_dec`
(java.py:18–69) thread `float`→`double`/`Double`, `Cbor.float_`, and `.d` correctly,
including boxed list/map element types.

### (g) Scope / deps — CLEAN

`git diff --name-only` → exactly the 3 owned tracked files
(`src/taut/gen/java.py`, `src/taut/gen/runtime/Cbor.java`, `src/tests/test_java.py`).
`Cbor.java` imports only `java.*` (StandardCharsets, ArrayList, Arrays, List) — no new
deps. `java.py` imports only the existing `..ir.model`. Python suites green:
`pytest src/tests/test_java.py -q` → 4 passed; `pytest src/tests -q` → 166 passed.

---

## Findings by severity

### Blocker — none.

### Major — none.

### Minor

**M1 — Java parity harness is untracked (packaging gap).**
`src/tests/java/FloatParity.java` is `?? src/tests/java/` in `git status`. It is real,
correct, and passes, but a patch from the tracked diff (or `git add -u`) ships the
runtime without its byte-gate, leaving Phase 2's "compiled+run where possible" check
outside version control. This matches CR55's sole finding — I confirm it. Fix:
`git add src/tests/java/FloatParity.java` before the commit.

**M2 — `test_java.py` only asserts generated-code *strings*, never compiles them.**
`test_java.py:2` even says "javac compile/run parity verified out-of-band." The shape
test (test_java.py `test_float_scalar_codegen_shape`) string-matches the emitted Java; it
would not catch a generated snippet that compiles-but-is-wrong, nor a runtime/codegen
drift. I separately compiled + round-tripped the generated float API (§f) and it is
correct, but there is no committed `javac` gate. This is an accepted Phase-2 limitation
(the brief defers the cross-language byte gate to Phase 3.2), so it is a *note*, not a
defect in this change. No action required for this PR.

### Nits

**N1 — `roundRight(sig, 28 - e)` shift range.** For the subnormal arm, `e` ranges
`[-25, -15]` (guarded by `e < -25 → 0` above and `e >= -14` below), so the shift is
`[43, 53]`. `roundRight` computes `1L << (shift-1)` up to `1L << 52` and masks with
`(1L << shift) - 1` up to `(1L << 53) - 1` — all within `long`, no overflow. The
`sig`-only operand (≤ 2^53) is never shifted left, so no UB. Correct, but a one-line
comment stating the proven shift bounds would help the next reader. Empirically cleared
by the subnormal sweep (§b/§d).

**N2 — `doubleToHalfBits` uses `doubleToRawLongBits` (raw) while `encFloat` compares with
`doubleToLongBits` (canonicalising).** This is fine and intentional: NaN is filtered out
before `doubleToHalfBits` is ever called, so the raw/canonical distinction only matters
for NaN and is moot here. Worth a comment so a future edit doesn't move the NaN guard.

**N3 — `List<Byte>` autoboxing in `enc`.** Every output byte boxes into a `Byte` object;
fine for a frozen-tiny-subset codec, but it's the obvious perf wart if these messages
ever get large. Pre-existing, out of scope for the float change.

---

## Independent take on CodeReview55

**Agree** with CR55's one substantive finding (untracked harness, their `[P2]`) — I
reproduced it via `git status --short` (`?? src/tests/java/`) and `git diff --name-only`
(three files). My M1 is the same issue, same fix.

**Agree** with CR55's core correctness conclusion ("no confirmed runtime/generator
bugs") — but CR55 reached it largely by *inspection plus the 22-row harness*. I consider
that **insufficient on its own** for the highest-risk component (the hand-rolled
narrowing): 22 rows cannot exercise the half-exactness boundary densely. My differential
fuzz (579,698 doubles, including the exhaustive ±1-ULP half boundary and tie nudges)
**raises the confidence** from "looks right + 22 vectors" to "byte-identical to the
oracle across the boundary-dense space." CR55's verdict is correct; its *evidence* was
thinner than the risk warranted.

**Agree** with CR55's residual-risk notes (no committed `javac` gate for generated code;
non-preferred NaN widths not in the corpus). I closed the latter empirically (§d) — Java
matches the oracle on single/double NaN decode→canonicalise. CR55 did not actually run
those cases; it noted the gap. I verified there is no bug behind it.

**Nothing in CR55 is overstated.** It did not over-claim correctness — if anything it was
conservatively scoped (it explicitly labelled byte parity "out-of-band"). The one thing
it *missed*: it never empirically stressed the narrowing beyond 22 rows, so a
double-rounding or boundary bug *could* have slipped past its method. There wasn't one,
but the method wouldn't have caught one.

---

## What I could not verify

- **CI cross-language gate (Phase 3.2):** not in this repo state; the in-repo gate for
  the 6 out-of-band languages doesn't exist yet by design. Not this PR's responsibility.
- **`equals`/`hashCode` semantics for the new `d` field:** the value model uses default
  identity `equals` (per java.py's header note), so the new field doesn't participate;
  nothing to verify for this change, but worth knowing two `Cbor.float_` instances are
  never value-equal.
- I did not run the author's harness through the *broken* PATH `java` — I used the
  Android Studio JDK 21 as instructed; results are JDK-21-specific (IEEE-754 ops are
  spec-mandated, so portability across JDKs is not a real risk here).
