# Taut Float Phase 2 — Swift — Independent Code Review (CodeReview48)

**Verdict: APPROVE.** The Swift `float` arm is byte-identical to the Python oracle across
all 22 corpus rows (encode + re-encode + decode-bits) and an aggressive differential fuzz
of **35,302 doubles, 0 mismatches**, including 80 hand-constructed double-rounding
witnesses (0 mismatches). The implementation correctly avoids the double-rounding trap by
narrowing `Double → Float16` directly, canonicalises NaN before width selection, preserves
`-0.0`, and `Float16(v)` overflow saturates to ±Inf (no trap). Only the three owned files
changed; no new dependencies. Findings are one minor (portability) and two nits — no
blockers, no majors.

Independent senior reviewer. I did not trust the author's tests or the prior review — I
built my own harnesses in `/tmp/swift-float-review`, compiled with the in-repo `swiftc`, and
diffed against the Python reference myself. The only file I wrote in-repo is this review.

---

## 1. Scope / hygiene

`git -C taut-swift status` — exactly the three owned files modified, plus the two review
docs:

```
modified:   src/taut/gen/runtime/cbor.swift
modified:   src/taut/gen/swift.py
modified:   src/tests/test_swift.py
untracked:  dev-docs/TautFload2-Swift-CodeReview55.md, …-CodeReview48.md (this file)
```

No edits to `ir/*`, `wire/*`, `gen/scaffold.py`, `corpus/*`, or any other language's runtime.
`grep '^import' cbor.swift` → **none**: the runtime is pure language built-ins (native
`Float16`/`Float`, allowed by the brief), **no new dependencies**. Scope clean.

Toolchain: `/usr/bin/swiftc`, Apple Swift 6.3.1 (swiftlang-6.3.1.1.2),
target `arm64-apple-macosx26.0`. Native `Float16` present, compiles and runs.

---

## 2. D0 rule audit (read against `cbor.swift` + the Python oracle)

| Rule | Where | Verdict |
|---|---|---|
| **B — NaN → `F9 7E00`, FIRST** | `cbor.swift:61-65` — `if v.isNaN` is the first statement in `encFloat`, before any width test | OK, matches `cbor.py:54-55` |
| **A — shortest half/single/double, exact, bit-equal** | `cbor.swift:67-82`: half if `Double(Float16(v))==v`, else single if `Double(Float(v))==v`, else double | OK; order half→single→double; `==` on `Double` is bit-exact for finite values (NaN excluded), so `-0.0 ≠ +0.0` holds |
| **narrow16 = RNE AND direct double→half** | `cbor.swift:67` `let h = Float16(v)`, `v: Double` | OK — proven direct (§4.3). `Float16.init(_:Double)` rounds binary64→binary16 in one step |
| **C — −0.0 → `F9 8000`** | falls through to half: `Float16(-0.0)` is −0.0 half, `Double(==)` true, `bitPattern==0x8000` | OK (corpus `neg-zero` + e2e list-field check) |
| **±Inf → `F9 7C00`/`F9 FC00`** | half-exact: `Float16(±Inf)` is ±Inf half | OK (corpus `pos-inf`/`neg-inf` + fuzz) |
| **D — decode 25/26/27 widen to double** | `cbor.swift:145-155`: reads 2/4/8 BE bytes, `Double(Float16(bitPattern:))` / `Double(Float(bitPattern:))` / `Double(bitPattern:)` | OK, matches `cbor.py:179-184`; half/single→double widening is lossless |
| **E — coerce at scalar boundary** | N/A static target; field held as native `Double` (`_swift_ty:"Double"`) | OK, consistent with the brief |

**Overflow ("didn't overflow" clause).** `Float16(v)`/`Float(v)` do **not** trap — a too-large
finite double saturates to `±Inf`, so `Double(h) == v` is false and the code falls through.
The half/single branch is taken with an Inf result only when `v` is literally `±Inf`, the
correct half-exact answer. This is the Swift-idiomatic equivalent of Python's
`except OverflowError`. Verified empirically in §4.4.

**Codegen (`swift.py`).** `_swift_ty → "Double"` (`:28`), `_default → "0.0"` (`:45`),
`_encode → "Cbor.float(expr)"` (`:57`), `_decode → "expr.floatVal"` (`:80`) — all four dicts
updated consistently. Matches the Swift brief verbatim; optional/list/map/transient float
fields all generate and compile (§4.6).

---

## 3. Value-model integration

`enum Cbor` gains `case float(Double)` (`cbor.swift:9`) and `var floatVal: Double`
(`cbor.swift:24`) exactly as the brief prescribes; `enc`/`dec` switches add the float arm
(`:95`, `:145-155`). `floatVal` `fatalError`s on a non-float, mirroring the sibling
accessors — fine for generated code where the schema fixes the type. No reuse of the int slot.
Idiomatic and minimal.

---

## 4. Empirical verification (the core of the job)

All harnesses in `/tmp/swift-float-review/`. Swift multi-file compiles require the
top-level-code file to be named `main.swift` (else `error: statements are not allowed at the
top level`) — I hit and worked around this in every harness.

### 4.1 Corpus parity — 22 rows, 0 failures

`main.swift` (corpus harness) loads all 22 rows from `corpus/float_vectors.json`; per row:
`encode(double(f64)) == cbor`, `encode(decode(cbor)) == cbor` (re-encode parity, covers NaN),
and — non-`nan*` rows — `decode(cbor).bitPattern == f64`.

```
$ swiftc cbor.swift main.swift -o corpus-harness && ./corpus-harness
CORPUS: 22 rows, 0 failures
```

Green on every row, including `neg-zero` (`f98000`), all three NaN payloads → `f97e00`,
`half-max` (`f97bff`), single/double subnormals, and `near-miss-not-half-exact-single`
(`fa3f801000`).

### 4.2 Differential fuzz — 35,302 doubles, **0 mismatches** (the decisive check)

`gen_doubles.py` (seed 20260623) emitted 35,302 doubles as f64-bit-hex → `doubles.hex`:

- **Structured (~10k+):** all 4,101 integers in [−2050, 2050]; powers of two and ×1.5/×3
  over exponents −160..130; `k/16` and `k/1024` grids over [−4000, 4000]; `±0`, `±Inf`,
  `65504`, `65505`, `65519`, `65520`, `65535` (half-overflow boundary), `2^-14`, `2^-24`,
  `2^-25`, `2^-149`, `2^-1074` (min double subnormal), max-single & just-above, min-double
  normal, huge magnitudes (`1e308`, `±1.79e308`), `0.1`, `1.1`, π, e, near-miss
  `1+2^-24`; **8 distinct NaN bit patterns** (quiet, signaling, neg, all-ones payload, etc.).
- **Random (~14k):** 6,000 uniform-over-bit-space (full 64-bit), 4,000 uniform in ±70000 to
  stress narrow16, 2,000 in the half-subnormal region, 2,000 single-ish (±1e30).

Oracle bytes (batch, `taut-swift && PYTHONPATH=src python3`):
```
from taut.wire import cbor; cbor.dumps(Double(bits)).hex()    # one line per double  → oracle.hex (35302)
```
Swift bytes from `main.swift` (fuzz harness): reads the same `doubles.hex`, prints
`encode(.float(value)).hex()` per line → `swift.hex` (35302). Indexed diff in Python:

```
TOTAL doubles: 35302
MISMATCHES: 0
```

**0 mismatches across 35,302 doubles** — every Swift byte equals the Python oracle byte.

### 4.3 Double-rounding trap — directly proven AVOIDED

The headline risk. Two-pronged.

*Algebraic:* shortest-form emits half bits only inside the `Double(Float16(v)) == v`
exactness gate, and half-exactness is purely a property of v's bit pattern (half lattice ⊂
single lattice ⊂ double lattice). The rounding *path* therefore cannot change which width is
selected — it could only corrupt bytes if the codec emitted an *inexact* half, which this
code never does (`h.bitPattern` is written strictly inside the `== v` branch). I tried to
construct a double whose *half-exactness verdict flips* between the direct and via-single
paths and found **zero exist**, consistent with this.

*Empirical:* I constructed 80 genuine double-rounding witnesses in Python — doubles near
half midpoints where `double→half directly` ≠ `double→single→half` (verified the two paths
disagree, e.g. `f64=3e60000000000001`: direct half `0x0001`, via-single `0x0000`). Fed them
to Swift and diffed against the oracle:

```
DR WITNESSES: byte-identical across 80 double-rounding witnesses, 0 mismatches
```

`Float16(v)` tracks the direct path; the oracle (Python `struct '>e'`, also direct) matches
bit-for-bit. The runtime is on the correct path.

### 4.4 `Float16(v)` overflow — proven non-trapping

```
Float16(70000.0) = inf   isInfinite: true   Double(inf) == 70000.0 -> false
Float16(1e300)   = inf   isInfinite: true
v=65505.0  Float16=65504.0  exact=false
v=65519.0  Float16=65504.0  exact=false
v=65520.0  Float16=inf      exact=false      (round-to-even-up-to-inf boundary)
v=65535.0  Float16=inf      exact=false
```

Saturates to ±Inf (no trap), and `Double(inf) == finite v` is false, so over-range values
fall through to single/double. The 65505/65519/65520 boundaries behave exactly as the oracle
expects.

### 4.5 Half-lattice sweep — all 65,536 patterns round-trip

`Float16(Double(Float16(bitPattern: b))).bitPattern == b` for every non-NaN `b` in
`0...65535` → **0 failures**, proving `narrow16 ∘ widen16` is the identity on the half lattice
(no scanner/rounding artifact).

### 4.6 End-to-end generated-model compile + round-trip (closes the CR55 gap)

CR55 only string-inspected the generated code. I generated a real `FloatBox`
(scalar/list/map/optional/transient float fields, forward-compat on) and **compiled it with
the runtime**:

```
$ swiftc cbor.swift FloatBox.swift main.swift -o e2e-harness   # compiles clean
encoded FloatBox: a401f93e000284f90000f98000f97bfffb3fb999999999999a0382a2010302fb400921fb54442d11a2010702fa47c3500004f9bc00
E2E OK: generated message round-trips, -0.0 preserved
```

`toCbor`/`fromCbor` compile and round-trip idempotently; `-0.0` survives a list field
(`xs[1].sign == .minus && xs[1] == 0.0`); transient `scratch` stays off-wire and defaults to
`0.0`. Floats thread through every container (`1.5→f93e00`, `0.1→fb3fb9…`, `65504→f97bff`,
`100000→fa47c35000`, π-double, `-1.0→f9bc00`). No integration drift.

### 4.7 Author's own tests — green

```
$ PYTHONPATH=src python3 -m pytest src/tests/test_swift.py -q   ->  6 passed
$ PYTHONPATH=src python3 -m pytest src/tests -q                 ->  167 passed
```

`pytest` was importable directly here (unlike CR55's environment). The author's
`test_swift_runtime_float_vectors` compiles `cbor.swift` and runs the 22-row corpus inside
the normal suite when `swiftc` is present — a real compiled gate, good.

---

## 5. Findings by severity

### Blockers
None.

### Majors
None.

### Minors

- **M1 — unguarded `Float16` (portability, not parity).** `cbor.swift:67` and `:147` use
  `Float16` with no `#if`/`@available` fallback. On a Swift toolchain without native `Float16`
  the runtime fails to **compile**. This is explicitly sanctioned by the Swift brief ("Confirm
  `Float16` is available on the build platform") and compiles+runs here on 6.3.1, so it is not a
  Phase-2 parity defect. A one-line comment marking the `Float16` dependency would help a future
  port to a Float16-less toolchain (which would need to hand-roll narrow16 like the other
  languages). No fix required this phase. **Fix (optional):** add `// requires native Float16
  (Apple / recent Linux Swift); a Float16-less target must hand-roll narrow16` above `encFloat`.

### Nits

- **N1 — decoder has no payload bounds checks.** `cbor.swift:146-154` index `data[off]`,
  `data[off+j]` without verifying slice length; a truncated `f9`/`fa`/`fb` traps with an index
  out-of-range rather than a clean error. This mirrors the Python reference's trust-the-length
  style and the pre-existing int/bytes/text arms — consistent, out of scope for float parity.
  Flagging for completeness; a Phase-3 hardening note at most.
- **N2 — `head(&out, 5, UInt64(m.count))` vs iterating `entries`** (`cbor.swift:101-102`).
  `entries = m.sorted` has the same count, so correct; reading `entries.count` would be more
  obviously consistent. Pre-existing, untouched by this diff. No change needed.

---

## 6. Independent take on CodeReview55

**I agree with CR55's verdict (no correctness findings) and independently confirm it — but my
fuzz is far more decisive than CR55's evidence.** CR55 verified only the 22 corpus rows via a
manual harness; that alone does **not** exclude a double-rounding bug, because the corpus has
only a handful of half-relevant rows. The real proof is the 35,302-double differential fuzz
plus the 80 double-rounding witnesses (§4.2–4.3) and the full half-lattice sweep (§4.5), none
of which CR55 ran.

Point-by-point on CR55's residual risks:

- **"Harness does not compile a generated Swift model with float fields"** — **Agree, and I
  closed it.** §4.6 compiles and round-trips a real generated `FloatBox`
  (scalar/list/map/optional/transient), byte-matching the oracle. Genuine gap, now empirically
  covered (still not pinned by an in-repo test — see §7).
- **"Verified only on Apple Swift 6.3.1 / depends on native `Float16`"** — **Agree** (my M1).
  Same toolchain here. The `Float16` dependency is brief-sanctioned; older/Linux Swift is out of
  scope and would be caught by its own compile. Accurately stated, not overstated.
- **"No malformed/truncated payload tests"** — **Agree** (my N1). Correctly scoped by CR55 as
  out-of-phase.

**Nothing in CR55 is overstated or wrong.** What it *missed* is the strongest available
evidence: the direct-narrowing proof and a large differential fuzz. CR55 reads as a careful but
lighter pass — inspection-level confidence; this review supplies proof-level backing. Verdicts
converge: approve.

---

## 7. What I could not verify

- **Cross-platform `Float16` semantics.** All claims are for Apple Swift 6.3.1 on arm64 macOS —
  the only toolchain present. The runtime would not compile on a Swift without native `Float16`
  (M1); I had no such toolchain to confirm the failure mode. IEEE-754 binary16 RNE is
  unambiguous, so any conformant `Float16(Double)` will match the oracle, but that is an
  inference, not a run.
- **In-repo pinning of the end-to-end model bytes.** §4.6 proves the generated model compiles
  and byte-matches, but via *my* /tmp harness, not a committed test. The author's
  `test_swift_runtime_float_vectors` compiles only runtime + corpus, not a generated message.
  Phase 3.2's cross-language gate is the intended backstop; optionally the author could extend
  the existing `swiftc`-gated test to also compile a generated `FloatBox` (low effort, locks in
  the integration path).

Everything load-bearing for Phase-2 done-ness — corpus parity, narrow16 correctness, the
double-rounding avoidance, NaN/±0/±Inf/subnormal handling, overflow non-trapping, decode
width-leniency, codegen, scope/deps — was runnable and is **verified green**.

---

## 8. Reproduction

Harnesses in `/tmp/swift-float-review/`: `cbor.swift` (runtime copy), `gen_corpus_harness.py`
+ corpus `main.swift`, `gen_doubles.py` → `doubles.hex`, `oracle.hex` (Python),
`swift.hex` (Swift), the diff script, double-rounding generators + `dr_*.hex`, `FloatBox.swift`
+ `e2e_main.swift`, and `probe` (overflow / half-lattice / double-rounding sentinel). Compile
with `swiftc cbor.swift <harness>.swift -o <out>`; the file holding top-level code must be named
`main.swift`.
