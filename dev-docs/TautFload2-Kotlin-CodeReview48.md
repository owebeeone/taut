# Taut Float — Phase 2 Kotlin — Independent Code Review (CR48)

**Verdict: APPROVE.** The Kotlin float arm is byte-identical to the Python oracle across
**77,558 distinct doubles** (77,364 + 194 adversarial) with **0 mismatches**, all 22 corpus
rows pass (encode + decode→re-encode + decode→bits), decode is width-lenient, the codegen
output compiles and round-trips a float-bearing message (−0.0 bit-preserved), only the three
owned files are touched, and no new dependencies are introduced. I found no blockers and no
majors. Two minor/nit observations only.

This review was done independently: I re-derived the narrowing math, compiled and ran the
runtime against the oracle, and cross-checked CR55 line by line against the code.

---

## 1. What I verified and HOW

Toolchain used (the PATH `java` is broken, so JAVA_HOME is pinned):

```
KOTLINC="/Applications/Android Studio.app/Contents/plugins/Kotlin/kotlinc/bin/kotlinc"
JAVA="/Applications/Android Studio.app/Contents/jbr/Contents/Home/bin/java"
JAVA_HOME="/Applications/Android Studio.app/Contents/jbr/Contents/Home"
```

The runtime is a vendored snippet, so I compiled `src/taut/gen/runtime/cbor.kt` together with
small `/tmp` harnesses (`-include-runtime -d <jar>`) and ran them on the JBR JVM.

### (a) Corpus parity — PASS (22/22)

Compiled the author's own harness `src/tests/kotlin_float_parity.kt` with the runtime and ran it:

```
$KOTLINC src/taut/gen/runtime/cbor.kt src/tests/kotlin_float_parity.kt -include-runtime -d corpus.jar
$JAVA -jar corpus.jar        # exit 0, no output
```

Exit 0 with no output means every `check()` passed: for all 22 rows
`encode(double(f64)) == cbor`, `encode(decode(cbor)) == cbor` (re-encode idempotent), and
`doubleToLongBits(decode(cbor)) == f64` for the non-NaN rows. **corpus_parity_pass = true.**

### (b) Differential fuzz — PASS (0 mismatches / 77,364 doubles)

A `/tmp` harness reads f64 bit-patterns (16 hex chars per line), encodes each as
`Cbor.float(longBitsToDouble(bits))`, and prints the CBOR hex plus a decode→re-encode
idempotence marker. The oracle stream was produced with
`cd taut-kotlin && PYTHONPATH=src python3` calling `taut.wire.cbor.dumps(x).hex()` on the
**same** bit-patterns.

Generated set (`/tmp/ktreview/gen.py`, seed 20260623), de-duplicated to **77,364** doubles:
- **all 65,536 exact half bit-patterns** widened to double (the entire half lattice),
- **all 1,023 half subnormal fractions** (±),
- structured edges: ±0, ±Inf, 8 NaN payloads, 65504/65505 and the 65520 overflow boundary,
  2^-14 / 2^-15 / 2^-24 / 2^-25 / 2^-149 / 2^-1074, max-single and just-over-max-single,
  huge magnitudes (1e39, 1e300, DBL_MAX), 0.1/0.2/0.3/1.1/π/e, 2^24 and 2^24+1, plain
  integers −300..300, powers of two 2^−30..2^30, near-miss not-half values,
- 5,000 full-range random 64-bit patterns + 5,000 random-magnitude finite doubles,
- 2,000 random halves each nudged ±1 double-ulp.

```
PYTHONPATH=src python3 /tmp/ktreview/gen.py        # -> 77364 unique doubles
$JAVA -jar kt.jar /tmp/ktreview/bits.txt > kt_out.txt
diff <(cat oracle.txt) <(awk '{print $1}' kt_out.txt)
#   encode mismatch count: 0
#   re-encode idempotence failures: 0
```

**Result: 77,364 doubles, 0 mismatches, 0 idempotence failures.**

### (c) Adversarial double-rounding set — PASS (0 mismatches / 194 doubles)

A second set (`/tmp/ktreview/gen2.py`) targets the double-rounding trap directly: half-ulp
midpoints across exponents 2^−14..2^15, each ±1 double-ulp; the 65504→65520 half-overflow
threshold; and the 2^−24/2^−25 subnormal tie. **0 mismatches.**

I then *proved this set has teeth*: a Python model comparing DIRECT double→half narrowing
(`struct >e`) vs the BUGGY double→float→half path found **34 entries in the 194 where the two
paths produce different half bits**. The Kotlin codec matched the oracle on all 34 — i.e. the
double-rounding code path is genuinely exercised, and the implementation takes the correct
(direct) branch. (For shortest-form *width selection*, double-rounding cannot flip half-exactness
— I confirmed this by a 20M-sample hunt that found 0 width-flip candidates — so the practical
risk was always the *bits when half IS exact*, which the exhaustive half-lattice sweep in (b)
covers completely.)

### (d) Decode width-leniency — PASS

A harness decoded `1.0` encoded three ways: `f93c00` (half), `fa3f800000` (single),
`fb3ff0000000000000` (double). All three widen to the exact double `3ff0000000000000`. `-0.0`
half (`f98000`) decodes to bits `8000000000000000`; single +Inf (`fa7f800000`) → `Infinity`;
a double-encoded NaN re-encodes to canonical `f97e00`.

### (e) Subnormal shift-guard boundary — PASS

Spot-checked the deepest `doubleToHalfBits` subnormal path (`roundShiftEven(mant, 28-e)` with
shift 52/53/54/55 and the `shift > 54 → 0` guard): 2^−1074, 2^−25·(1+2^−30), 2^−25, 2^−26,
2^−27, 2^−30, 2^−50. Kotlin matched the oracle byte-for-byte on every one (e.g. 2^−25 →
`fa33000000`, 2^−1074 → `fb0000000000000001`).

### (f) Codegen integration — PASS (compiled + ran)

The shape test only does string assertions, so I generated real Kotlin for a float-bearing
schema (`F("x",FLOAT)`, optional FLOAT, `List(FLOAT)`, `Map(INT,FLOAT)`, `forward_compat=True`),
compiled it with the runtime, and round-tripped an instance:

```
wire=a501f93e00 02fb3fb999999999999a 0384 f90000 f98000 f97bff fb400921f9f01b866e ...
ROUND-TRIP OK (incl -0.0 bit-preserved)
```

`x=1.5`→`f93e00`, `maybe=0.1`→`fb…`, list `[0.0,-0.0,65504.0,π]`→`f90000 f98000 f97bff fb…`,
the `Map<Long,Double>` sorts and round-trips, and `-0.0` survives by bit-pattern. The generated
`_enc`/`_dec`/`_kt_ty`/`_default` wiring is correct.

### (g) Scope, deps, suite

- `git status` / `git diff`: only `src/taut/gen/kotlin.py`, `src/taut/gen/runtime/cbor.kt`,
  `src/tests/test_kotlin.py` modified; `kotlin_float_parity.kt` + the two review files untracked.
  No `ir/*`, `wire/*.py`, `scaffold.py`, `corpus/*`, or other-language files touched. **In scope.**
- `cbor.kt` adds no imports — only `java.lang.*` / `java.lang.Math` (JDK stdlib). **No new deps.**
- `test_kotlin.py` imports `FLOAT` from `taut.ir.dsl` (a Phase-1 shared symbol, not author-added).
- `PYTHONPATH=src python3 -m pytest src/tests -q` → **166 passed, 1 skipped** (the skip is the
  `kotlinc`-gated parity test, which I ran manually in (a)).

---

## 2. D0 rule audit (against the code)

| Rule | Where | Verdict |
|---|---|---|
| **A** shortest-of-half/single/double by **bit** equality | `encFloat` cbor.kt:123–137 — `doubleToLongBits(...) == want` for half and single, else double | Correct. Uses `want = doubleToLongBits(v)`, so −0.0 ≠ +0.0 is enforced by bit compare. |
| **narrow16 direct, RNE** | `doubleToHalfBits` cbor.kt:78–101 — operates on the 53-bit double mantissa directly; `roundShiftEven` cbor.kt:68–76 is round-to-nearest-**even** | Correct, direct double→half. No double→float→half anywhere. |
| **B** NaN → `F9 7E00` FIRST | `encFloat` cbor.kt:124–126 — `if (v.isNaN())` before any width test | Correct; verified over 8 NaN payloads incl. signaling and negative. |
| **C** −0.0 → `F9 8000` | bit-compare in A + `doubleToHalfBits` cbor.kt:84 returns `sign` for exp==0 (zeros), with widen `longBitsToDouble(sign<<48)` preserving the sign bit | Correct; verified by bits and by a round-trip through a list field. |
| ±Inf → `F9 7C00`/`F9 FC00` | `doubleToHalfBits` cbor.kt:83 (`exp==0x7ff`, frac==0 → 0x7c00) | Correct. |
| **D** decode 25/26/27 → double | `dec` major 7 cbor.kt:198–214 | Correct; all three widen exactly to double. |

The single (`FA`) path uses `v.toFloat()` (cbor.kt:132), which is a single *direct* narrow — no
double-rounding there either, and the exactness gate is again a `doubleToLongBits` compare.

The normal-path carry is handled: `roundShiftEven(mant, 42)` then `if (q == 0x800) { e+=1; q=0x400 }`
(cbor.kt:93–97), so a mantissa that rounds up across the 11-bit boundary correctly bumps the
exponent; `halfExp >= 31 → 0x7c00` (cbor.kt:99) routes the half-overflow to Inf, which the
exactness check then rejects unless the input truly is Inf. Verified at the 65504/65520 boundary.

---

## 3. Independent take on CR55

**Agree with CR55's bottom line (no correctness findings), and I went further — I actually
compiled and ran the runtime, which CR55 could not.** Specifics:

- **Agree:** CR55's line-cited audit of the value model (new `Double f` slot, `FLOAT=7`,
  `float()`/`floatVal`), NaN-before-width, direct narrowing, bit-exact gates, and decode arm is
  accurate. I re-checked each cited line and confirm them.
- **Agree, and now closed:** CR55 listed "Kotlin compile/runtime parity not executed — `kotlinc`
  not on PATH" as a residual risk and explicitly flagged its 200,013-sample Python re-model as
  "not a substitute for compiling the Kotlin runtime." That was the right caveat. **I closed that
  gap**: the real Kotlin runtime compiles and byte-matches the oracle over 77,558 doubles
  including the full half lattice and the double-rounding adversaries. CR55's central residual
  risk is now discharged, not merely argued.
- **Slightly overstated, harmless:** CR55 says the harness "will not automatically track future
  corpus edits." True but immaterial under Phase 2 — the corpus is locked at 22 rows, and Phase
  3.2 owns the cross-language gate. Not a finding.
- **Nothing missed of substance.** CR55 did not separately verify decode width-leniency or
  compile the *generated* codegen output (only string asserts); I did both and they pass, so
  CR55's conclusion holds under stronger evidence.

No disagreement on any correctness claim.

---

## 4. Findings by severity

**Blockers:** none.
**Majors:** none.

**Minor:**

- **`test_kotlin.py:74` runs `java` from PATH, not JBR.** The parity test invokes
  `subprocess.run(["java", "-jar", str(jar)], ...)`. In this environment the PATH `java` is
  broken, so even if `kotlinc` were found, the run step would fail rather than verify. The test
  is gated on `shutil.which("kotlinc")` and skips cleanly today, so it is not breaking the suite —
  but as written it is not a reliable in-repo gate. *Fix:* resolve the JDK from the kotlinc
  install (or `JAVA_HOME`) and use that `java`, mirroring how the harness must actually be run.
  (Out-of-band CI may differ; flagging because the test's value is to *run*, and right now it
  can find a compiler it cannot pair with a JVM.)

**Nit:**

- **`doubleToHalfBits` cbor.kt:84 flushes all double subnormals to half ±0** (`if (exp == 0)
  return sign`). This is *correct* only because the bit-exactness gate at cbor.kt:129 then
  rejects the result (a tiny subnormal ≠ 0), pushing it to single/double. It is load-bearing
  behavior that reads as a shortcut; a one-line comment ("subnormal/zero doubles flush to half
  ±0; the exactness check downgrades the width") would prevent a future edit from mistaking it
  for a bug. No behavior change. (Verified: 2^−1074 → `fb…0001`, never a spurious half-zero.)

---

## 5. What I could not verify

Nothing material was unrunnable. The toolchain was available; I compiled and ran every check
(corpus, 77k+ fuzz, adversarial double-rounding, subnormal shift-guard, decode-leniency, and the
generated-codegen round-trip). The only thing I deliberately did **not** do is modify the
implementation. The `test_kotlin.py:74` PATH-`java` issue (Minor above) is the one spot where the
*repo's own* test could not self-verify in this environment; I verified the same behavior
manually with the JBR JVM instead.
