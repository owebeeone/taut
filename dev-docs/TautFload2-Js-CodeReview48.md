# Taut Float Phase 2 — JavaScript — Independent Code Review (CR48)

**Verdict: APPROVE.** The JS float arm is byte-identical to the Python oracle across
**306,587 encode** comparisons and **89,588 decode** comparisons with **0 mismatches**.
All D0 rules are implemented correctly, including the two correctness traps
(double-rounding and NaN canonicalization). Scope is clean: only the three owned files
changed, no new dependencies. No blockers, no majors. A handful of minor/nit observations
below, none requiring a change to land.

Reviewer stance: independent, skeptical. I re-derived every claim against the code and the
Python reference myself, and proved byte-exactness empirically rather than by inspection
alone.

---

## 1. What I verified, and how

### Toolchain (it ran — nothing hand-waved)
- `node v22.19.0`, `python3 3.10.15` (with `pytest 9.0.2`), in the worktree.
- Full Python suite: `PYTHONPATH=src python3 -m pytest src/tests -q` → **166 passed**.
- JS shape test: `PYTHONPATH=src python3 -m pytest src/tests/test_js.py -q` → **4 passed**.
- Author's parity harness: `node src/tests/js_float_parity.js` → `js float parity: 22 vectors ok`.

### (a) Corpus parity — PASS (22/22)
The author's harness `src/tests/js_float_parity.js` drives all three contract checks from
`corpus/float_vectors.json` (encode == cbor; `encode(decode(cbor)) == cbor`; `f64_bits(decode) == f64`
for non-NaN rows) plus an explicit width-lenient decode triple (`f93e00`/`fa3fc00000`/`fb3ff8000000000000`
all decode to `1.5` and re-encode to `f93e00`). Re-run here, green. I independently re-derived
every row's expected bytes from the Python oracle in the fuzz below, so the corpus is not
self-referential in my verification.

### (b) Differential fuzz vs the Python oracle — the decisive check
Oracle bytes were produced by the **Python reference** (`from taut.wire import cbor;
cbor.dumps(x).hex()`), not by the corpus, so this is a true independent diff of the
hand-rolled `narrow16` against `struct.pack(">e"/">f"/">d")`.

Harnesses (in `/tmp/floatfuzz`, nothing written into the repo):
- `gen_oracle.py` — builds a structured + random double set, dedups by exact 64-bit pattern,
  writes `doubles.txt` (f64 bit-hex) and `oracle.txt` (Python CBOR hex).
- `js_encode.js` — `require`s the runtime **under review**, encodes each double via
  `encode(CFloat(v))`, writes `js.txt`; also self-checks `decode(encode(v))` bit-idempotence.
- `targeted_py.py` / inline node — exhaustive half-tie midpoints + the overflow-to-inf band.
- `decode_oracle.py` / `decode_js.js` — decode-arm parity (info 25/26/27) in both codecs.

**Encode results (JS bytes vs Python oracle bytes, line-aligned):**

| Pass | What it covers | Doubles | Mismatches |
|---|---|---|---|
| Broad | ±0, ±Inf, 12 NaN payloads, all 65,536 half patterns, 4k random singles, integers −2050..2050, every 2^k & ±2^k & 2^k+1, half/single subnormals, max-half/single/double, near-miss ±1-ULP perturbations of halves and singles, ~10k uniform-random 64-bit patterns, 4k log-uniform random doubles | **87,557** | **0** |
| Targeted | every exact midpoint between adjacent halves ±1 ULP (RNE tie-to-even stress) + the 65504→65536 overflow band at fine granularity | **219,030** | **0** |
| **Total encode** | | **306,587** | **0** |

`decode(encode(v))` bit-idempotence self-check over the 87,557 set: **0 round-trip failures**
(`/tmp/floatfuzz/js_rt.json`).

**Decode results (JS-decoded f64 bits vs Python-decoded f64 bits):**

| What it covers | CBOR strings | Mismatches |
|---|---|---|
| All 65,536 half patterns (info 25) + every distinct FA/FB encoding from the encode oracle + hand-picked single/double NaN/Inf payloads | **89,588** | **0** |

This decode sweep independently proves `halfToNumber` matches `struct.unpack(">e")` for **every**
half bit pattern (subnormals included), and that single/double NaN payloads canonicalize on
re-encode (compared as `"NAN" == "NAN"`).

Exact commands (reproducible):
```
PYTHONPATH=src python3 /tmp/floatfuzz/gen_oracle.py          # -> 87557 unique doubles
node /tmp/floatfuzz/js_encode.js                              # -> 0 roundtrip fails
paste -d' ' /tmp/floatfuzz/doubles.txt /tmp/floatfuzz/oracle.txt /tmp/floatfuzz/js.txt \
  | awk '$2!=$3{n++} END{print "mismatches:", n+0}'           # -> 0
PYTHONPATH=src python3 /tmp/floatfuzz/targeted_py.py          # -> 219030 doubles, diff -> 0
PYTHONPATH=src python3 /tmp/floatfuzz/decode_oracle.py
node /tmp/floatfuzz/decode_js.js
paste -d' ' .../dec_cbor.txt .../dec_py.txt .../dec_js.txt \
  | awk '$2!=$3{n++} END{print "decode mismatches:", n+0}'    # -> 0
```

### D0 rule-by-rule audit (code, not just bytes)

| Rule | Site | Verdict |
|---|---|---|
| **NaN → F9 7E00, checked FIRST** | `cbor.js:120` `if (Number.isNaN(v))` is the first statement in `encFloat`, before any width test. `Number.isNaN` is bit-pattern-agnostic, so all 12 fuzzed NaN payloads (quiet/signaling, both signs) → `f97e00`. | OK |
| **Shortest-form A**, bit-equal compare | `encFloat:124-131`: half if `Object.is(halfToNumber(h), v)`, else single if `Object.is(Math.fround(v), v)`, else double. `Object.is` gives bit equality so `−0 ≠ +0`. | OK |
| **narrow16 direct double→half, RNE** | `doubleToHalfBits:66` reads f64 parts via `DataView` and rounds in **one** step (`roundScaled`/`roundShiftRight` implement round-half-to-even on the BigInt mantissa). No `Math.fround` is on the half path — double-rounding trap avoided. | OK |
| **−0.0 → F9 8000** | `doubleToHalfBits:70` returns `sign` (`0x8000`) for zero with sign bit set; `halfToNumber(0x8000) = -0`; `Object.is(-0,-0)` ⇒ stays half. Fuzzed: `f98000`. | OK |
| **±Inf → F9 7C00 / FC00** | `doubleToHalfBits:69` maps `exp==0x7ff & frac==0` → `0x7c00`/`0xfc00`. | OK |
| **Decode 25/26/27 widening** | `dec:196-198` adds half/single/double arms producing `CFloat(...)`; half via `halfToNumber`, single/double via `DataView.getFloat32/64`. Proven exact over 89,588 strings. | OK |
| **Coerce at scalar boundary (E)** | `encFloat:119` `const v = Number(value)` coerces an int-valued field (e.g. `CFloat(0)` from an `int` payload) to double → `f90000`. Mirrors Python `float(value)`. | OK |

### JS-specific items the brief flagged
- **Tagged object `{kind: FLOAT, f}`** — `FLOAT = 7` and `CFloat = (x) => ({ kind: FLOAT, f: x })`
  added (`cbor.js:8,11`); `enc` handles `case FLOAT` (`:143`), `dec` constructs `CFloat(...)`.
- **`CFloat` in `module.exports`** — present (`cbor.js:203`). The generated-types import line in
  `js.py:98` also adds `CFloat` to its destructured `require(...)`. Both verified.
- **narrow16 hand-rolled** — yes, BigInt-mantissa RNE; no native f16, no new dep.
- **Codegen** — `js.py:_enc` emits `CFloat({expr})` (`:17`), `_dec` emits `{expr}.f` (`:34`).
  Shape test `test_js.py:test_float_scalar_shape` asserts scalar/list/map encode+decode forms.

### Scope / dependencies
`git status` shows only `src/taut/gen/js.py`, `src/taut/gen/runtime/cbor.js`, `src/tests/test_js.py`
modified, plus the untracked harness `src/tests/js_float_parity.js` and the two review docs.
No `ir/*`, `wire/cbor.py`, `corpus/*`, or `scaffold.py` touched. No `package.json`; the runtime
has no external `require`. **Clean.**

---

## 2. Findings by severity

### Blocker — none.
### Major — none.

### Minor

- **M1 — `roundScaled` left-shift path is reachable but inert (dead-ish, slightly misleading).**
  `roundScaled(m, scale)` (`cbor.js:52`) returns `m << BigInt(scale)` when `scale >= 0`. On the
  normal path `sig = roundScaled(m, e - exp + 10)`; for a normalized double, `e - exp + 10 =
  (p.exp-1023-52) - (p.exp-1023) + 10 = -42`, always negative, so the left-shift branch is never
  taken from the normal path. On the subnormal path `roundScaled(m, e + 24)` with `e = -1074`
  is also always a right-shift. The `scale >= 0` arm is effectively unreachable for the inputs
  that occur. It's harmless and arguably defensive, but a reader auditing `narrow16` has to prove
  it can't fire. Optional: drop it, or add a one-line comment that scale is always negative here.
  *Not a defect — no behavior depends on it.*

- **M2 — `halfToNumber` uses float arithmetic, not bit reconstruction.**
  `cbor.js:91` computes `sign * (1 + frac/1024) * Math.pow(2, exp-15)` (and `sign*frac*2^-24` for
  subnormals). This is mathematically exact for all half values (every half is exactly
  representable in double, and these products are exact), and the 65,536-pattern decode sweep
  confirms bit-equality with `struct.unpack(">e")`. So this is correct — flagged only because it
  *looks* like it could carry rounding error and a future maintainer might "fix" it. A comment
  noting "all half values are exact in double; products below are exact" would preempt that.

### Nit

- **N1 — `pushFloat32`/`pushFloat64` vs `head()` style.** Float push helpers write the major byte
  inline (`0xfa`/`0xfb`) rather than going through `head`. Correct (floats aren't head-encoded),
  just stylistically separate; fine.
- **N2 — `_view`/`_buf` is module-global shared scratch.** `f64Parts`, `pushFloat32/64`,
  `readFloat32/64` all reuse the single 8-byte `_view`. Single-threaded JS, no re-entrancy across
  a `setFloat*`→`getUint*` pair, so safe; worth a mental note only.
- **N3 — `js_float_parity.js` is not wired into the default CI gate** (`run_tests.py` runs pytest
  only). This is the same observation CR55 makes; it's a Phase-3.2 concern (the brief explicitly
  defers the cross-language byte gate), not a defect in this change. The Python shape test that
  *does* run in CI cannot catch a runtime byte regression. See §4.

### Things I specifically tried to break and could not
- False shrink to half via the overflow path: `65520` (which would RNE to Inf as a half) correctly
  stays single (`fa477ff000`) because `halfToNumber(0x7c00)=Inf ≠ 65520`. The `exp > 15`/`0x7c00`
  return never produces a false half because the round-trip check rejects it.
- Near-misses: `2^-25` (half-RNE would tie-to-even down to 0) correctly does **not** shrink — it
  emits single `fa33000000`, because `halfToNumber(0x0000)=0 ≠ 2^-25`. Subnormal-into-normal
  carry (`sub >= 1024 → 0x0400`) verified: `2^-14 → f90400`.
- All ±1-ULP perturbations of every half and of 2k singles: none wrongly shrank.

---

## 3. Independent take on CR55 (`TautFload2-Js-CodeReview55.md`)

**Agree with its bottom line (no correctness defects), but CR55 is thin and under-proves it.**

- **Agree:** its rule mapping (NaN-before-width at `:120`, `-0` via bit-sensitive equality, direct
  RNE half narrowing, `Math.fround` single, decode 25/26/27) is accurate against the code. Its line
  citations (`cbor.js:66/118/196`, `js.py:13/30/95`) check out.
- **Agree:** the residual-risk it raises — the Node harness isn't in the pytest CI gate and
  `test_js.py` is shape-only — is real and correctly characterized (my N3). It's a known
  Phase-3.2 gap, not a blocker.
- **Overstated / unverifiable as written:** CR55 reports "ad hoc … 20,027 f64 bit patterns" and
  full 65,536 half + 20,011 single decode sweeps, but notes these were *not checked in*. As a
  reader I can't reproduce them. CR55's confidence is therefore asserted, not demonstrated in the
  artifact. My review re-runs an equivalent (larger: 306,587 encode + 89,588 decode) diff with the
  exact commands so the evidence is reproducible. I reach the same conclusion **with** the receipts.
- **Missed:** CR55 does not mention the `roundScaled` always-negative-scale observation (M1) or the
  `halfToNumber`-uses-float-arithmetic-but-is-exact subtlety (M2). Neither is a bug, but both are
  exactly the kind of thing a `narrow16` audit should call out so a future maintainer doesn't
  "simplify" them into a regression. CR55 also didn't explicitly exercise the overflow-to-inf
  no-false-shrink case (`65520`) or the subnormal-into-normal carry boundary; I did.
- **Net:** CR55 is correct but a light pass. CR48 confirms its verdict and strengthens the evidence.

---

## 4. What I could not verify

- **Cross-language in-repo gate.** Per the plan, JS float runtime bytes are *not* gated by the
  default `pytest` run; the Node harness is a separate invocation, and the cross-language byte gate
  is explicitly Phase 3.2. I verified byte-exactness out-of-band (as the base brief permits for
  shape-test-only backends), but I cannot assert that an unrelated future change to `cbor.js`
  would be caught by CI as it stands. Recommend Phase 3.2 wire `js_float_parity.js` (or its
  successor) into `run_tests.py`. This is a process gap, not a defect in this change.
- **Non-finite single/double decode → JSON layer.** Out of scope here (this review is the CBOR
  binary codec); `jsoncodec.py` is a Python-only/Phase-1 concern and untouched.
- Everything else in the brief was runnable and was run.

---

## Appendix — file:line index
- Runtime: `src/taut/gen/runtime/cbor.js` — `FLOAT/CFloat` `:8,11`; `doubleToHalfBits` `:66`;
  `halfToNumber` `:91`; `encFloat` `:118`; `case FLOAT` enc `:143`; decode arms `:196-198`;
  exports `:203`.
- Codegen: `src/taut/gen/js.py` — `_enc` float `:17`; `_dec` float `:34`; `CFloat` import `:98`.
- Shape test: `src/tests/test_js.py:36` `test_float_scalar_shape`.
- Author harness: `src/tests/js_float_parity.js`.
- My harnesses (not in repo): `/tmp/floatfuzz/{gen_oracle.py, js_encode.js, targeted_py.py,
  decode_oracle.py, decode_js.js}`.
