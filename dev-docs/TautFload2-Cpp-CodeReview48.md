# Taut Float — Phase 2 C++ — Independent Code Review (CR48)

**Verdict:** **Approve with nits.** The C++ float port is byte-exact to the Python
oracle across the corpus and >1.2M differential doubles (including the decisive
double-rounding witnesses), genuinely constexpr, and touches only the owned files.
The two open items are process/pre-existing, not float correctness: the C++ shape
test is untracked (must be committed), and a `Map(<scalar>, <scalar>)` schema does
not compile under C++20 on Apple libc++ — a **pre-existing** `std::map`+constexpr
limitation, **not** introduced by this change.

Reviewer: independent senior review. Toolchain: Apple clang 21.0.0 (clang-2100),
arm64-darwin, `-std=c++20` / `-std=c++23`. Python 3.10.15.

---

## 1. What I verified and how

### (a) Corpus parity — PASS (22/22)
Built a runtime harness (`/tmp/cppreview/harness.cpp`) that `#include`s the
**actual runtime under review** (`src/taut/gen/runtime/cbor.hpp`), reads f64
bit-patterns on stdin, and for each emits: `Buf::float_` encoding, the
re-encode (`encode_value(parse(enc))`), and the decoded f64 bits.

```
clang++ -std=c++20 -O2 -I src/taut/gen/runtime harness.cpp -o harness
```

Drove all 22 rows of `corpus/float_vectors.json` through it and checked the three
contract obligations per row (Base brief §"The oracle"):

| Check | Result |
|---|---|
| encode(double from `f64` bits) == `cbor` | **22/22** |
| re-encode parity `encode(decode(cbor)) == cbor` | **22/22** |
| decode→bits `f64_bits(decode(cbor)) == f64` (non-nan rows) | **19/19** |

Every row printed `OK` (zero, neg-zero, one, neg-one, one-and-half, half-min-subnormal,
half-min-normal, half-max, near-miss-not-half-exact-single, single-100000, single-max,
single-min-subnormal, double-tenth/1.1/pi/min-subnormal/max, pos-inf, neg-inf, and the
three NaN rows → `f97e00`). **0 failures.**

### (b) Differential fuzz vs the Python oracle — PASS (1,249,000 distinct doubles, 0 mismatches)
Oracle bytes generated exactly as the brief prescribes:
`cd taut-cpp && PYTHONPATH=src python3` → `from taut.wire import cbor; cbor.dumps(v).hex()`
(plus `cbor.loads`→re-`dumps` for re-encode parity, and decoded f64 bits).
The **same** f64 bit-patterns were fed to the C++ harness and the two hex streams diffed.

Four batches (deduplicated, union = **1,249,000 distinct doubles**):

| Batch | Doubles | Encode mismatch | Re-encode mismatch | Decode-bits mismatch |
|---|---|---|---|---|
| Structured edges + random bits + random reals + half/single-targeted | 16,777 | 0 | 0 | 0 |
| **Exhaustive half space** (all 65,536 half patterns widened to double) | 65,536 | 0 | — | — |
| **Double-rounding witnesses** (midpoints between every adjacent half pair, ±n double-ULPs, + multiples of ½·min-subnormal) | 318,454 | 0 | — | — |
| Single-precision midpoint stress + half/single-max boundary deltas + 50k random 64-bit | 854,949 | 0 | 0 | — |

Structured edges covered (per brief): ±0, ±Inf, 9 distinct NaN payloads (quiet,
signaling, neg, max-payload, etc.), half/single/double subnormals, boundaries
65504/65505/65519/65520, 2^-14, 2^-24, 2^-25, 2^-149, max-single and just-over,
the corpus near-miss `0x3ff0020000000000`, plain integers (-300..300 and 2^23/24/52/53
neighbours), and huge magnitudes (1e300, 1e308, 5e-324).

**The double-rounding batch is the decisive narrow16 check** (Base brief trap #1):
318,454 values placed exactly where a `double→float→half` two-step would diverge from
direct `double→half` RNE. **0 mismatches** ⇒ the encoder narrows directly, correctly.

I also probed the **decode-side widening** independently: a probe printing
`half_to_double(h)` for all 65,536 half patterns matched the Python `struct '>e'`
widening on **0 mismatches** (NaN payloads allowed to differ, as decode need only
produce *a* NaN — re-encode canonicalizes regardless).

### (c) constexpr / static_assert compile — PASS
Reconstructed the static_assert harness that `test_cpp.py` builds (per-row
`consteval` encode + reemit + decode-bits `static_assert`s over the corpus hex) and
compiled it:
```
clang++ -std=c++20 -I src/taut/gen/runtime static_assert.cpp -o sa   # rc=0
```
All 22 rows' **compile-time** asserts pass (rc=0, binary runs, exit 0). The narrowing,
round-trip, decode, and re-emit are genuinely constexpr — `narrow_half`,
`round_shift_right`, `half_to_double`, `single_exact`, `Buf::float_`, `parse`, and
`encode_value` are all `constexpr`, and `std::bit_cast` is used for the bits (C++20
constexpr). Confirmed live.

### (d) Delivered test suite — PASS
`PYTHONPATH=src python3 -m pytest src/tests/test_cpp.py -q` → **2 passed** (the shape
test and the compile-the-static_assert-harness test; clang++ is on PATH here so the
compile path actually ran). Full suite `src/tests -q` → **167 passed**.

### (e) Scope / dependencies — PASS
`git status`: only `src/taut/gen/cpp.py` and `src/taut/gen/runtime/cbor.hpp` modified;
`src/tests/test_cpp.py` and this review are untracked. New includes are stdlib only
(`<bit>`, `<cstdint>`); new Python import is stdlib `struct`. **No new dependencies.**
No forbidden file touched.

---

## 2. Findings by severity

### Blockers
None.

### Major
**M1 — `src/tests/test_cpp.py` is untracked; commit it before merge.**
`git status` reports `?? src/tests/test_cpp.py`; `git diff --name-only` lists only the
two runtime/codegen files. The Base brief (step 4) and Cpp brief require extending the
shape test, and it is the in-repo gate that runs without a compiler. If the worktree is
committed via `git diff`/staged-only, the test silently drops out and CI sees
implementation-only. **Fix:** `git add src/tests/test_cpp.py` and include it in the
commit. *(Agrees with CR55 finding #1 — confirmed independently.)*

### Minor
**m1 — The test advertises `Map(INT, FLOAT)` but never compiles that path; it does not
compile under C++20 on Apple libc++.** `test_cpp.py:14-17` declares
`F("by_id", 3, Map(INT, FLOAT))`, and `test_cpp_codegen_threads_float_scalar` asserts
the map line is emitted as a **string** (`"std::map<long long, double> by_id;"`,
`"b.float_(v);"`) — it never compiles it. I generated `_emit_types(S)` for that schema
and compiled it:
```
types.hpp:25: error: variable of non-literal type 'const_iterator' ...
  cannot be defined in a constexpr function before C++23
```
**Root cause (independently established, refines CR55):** this is **entirely
pre-existing and float-independent.** I compiled a `Map(INT, INT)` schema with *no
float anywhere* and it fails **identically** under C++20 — libc++'s
`std::map::const_iterator` is non-literal pre-C++23, so any generated `constexpr
to_cbor` that range-iterates a `std::map` is rejected. The same `Map(INT, FLOAT)`
header **compiles cleanly under `-std=c++23`**, and the scalar-only / `List(FLOAT)`
float header **compiles under C++20**. So the float port did not regress anything; the
test merely *names* a map field whose constexpr-ness was already broken on this stdlib.
**Fix options (all out of the float port's core scope, author's discretion):** drop the
`Map` field from this test's schema (it adds no float-specific coverage the scalar+list
case doesn't), gate the compile test at `-std=c++23`, or leave a comment noting the
field is string-checked only. Not a correctness issue in the float arm.

### Nits
**n1 — `Buf` fixed 512-byte buffer, no bounds check** (`cbor.hpp:133`). Pre-existing,
not float-introduced; float adds at most 9 bytes. Out of scope, noted for completeness.

**n2 — `narrow_half` overflow guard `abs > 0x40effc0000000000`** (`cbor.hpp:94`) treats
*every* value above max-half (e.g. 65505, 65519) as "not half", even though IEEE half
rounding would map [65504, 65520) → 65504. This is **correct for shortest-form**: such
values are not *exactly* half-representable, so they must fall through to single/double
anyway; the guard is just a fast reject. Verified against the oracle (65505 → `fac77fe100`,
etc., all match). No action — documenting that the shortcut is intentional and sound.

**n3 — `round_shift_right` shift-≥64 safety** (`cbor.hpp:43`): the `if (shift >= 64)
return 0;` guard precedes `1ULL << (shift-1)`, so no UB for deep subnormals (smallest
normal double hits shift=1050). Confirmed correct; the subnormal arm reaches shift up to
~63 for real half-subnormal rounding and ≥64 only when the true value is < ½ ULP of zero.

---

## 3. Independent take on CR55

**Finding #1 (test_cpp.py untracked) — AGREE.** Re-verified: `git status` shows
`?? src/tests/test_cpp.py`. Real and must be fixed before commit. (My M1.)

**Finding #2 (Map(INT,FLOAT) constexpr fails under C++20; string-checked only) —
AGREE on the symptom, and I strengthen its root-cause.** CR55 hedged ("This *may* be a
pre-existing C++ map/constexpr limitation"). I confirmed it **definitively is**: a
`Map(INT, INT)` schema with **no float** fails identically under C++20, and the same
map schema compiles under C++23 — so the float change is not the cause. CR55's reproduction
(libc++ non-literal `const_iterator`, scalar/list float header OK) matches mine exactly.
I downgrade this to **minor** because it is pre-existing and float-orthogonal; CR55's P2
labelling is defensible but slightly overstates the float port's responsibility.

**CR55 "Runtime Parity Notes" (no correctness issues in `Buf::float_`, width selection,
NaN canonicalization, −0.0, decode 25/26/27, re-emit) — AGREE, and I went further.**
CR55 ran ~20,018 raw-bit probes + ~20,003 f32 probes + 3 signaling-NaN compile probes.
That is sound but light on the *double-rounding* axis. My 318,454 adjacent-half-midpoint
witnesses plus the exhaustive 65,536-pattern half space close that gap empirically: the
direct-RNE narrowing is proven, not just argued. Net: I **concur** with CR55's runtime
verdict and consider it under-tested only on the single highest-risk path, which I have
now exercised to ~1.25M doubles with 0 mismatches.

**One environment correction:** CR55 reported pytest unavailable on their default Python
and that the suite couldn't run. On this checkout (`PYTHONPATH=src python3 -m pytest`),
pytest IS available and `test_cpp.py` runs **green (2 passed)** — including the actual
clang++ static_assert compile — and the full suite is **167 passed**. So the C++
static_assert harness is verified to compile and pass here, which CR55 could not confirm.

---

## 4. What I could not verify
- **Compiler matrix.** Only Apple clang 21 / libc++ was available (same limitation CR55
  noted). I exercised `-std=c++20` and `-std=c++23`; I did **not** test g++/libstdc++,
  MSVC, or older clang. The `Map`/constexpr behaviour is libc++-specific and may differ
  on libstdc++ (which made `std::map` constexpr-friendlier earlier).
- **Phase-3 shared golden.** The float-bearing GripLab corpus row is deferred to Phase 3.1
  (per the plan), so the shared `*.golden.json` cross-language byte gate is not yet
  exercised here — out of scope for Phase 2.

---

## 5. Bottom line
The float narrowing is correct — including the constexpr requirement and the
double-rounding trap that is the whole point of the C++ brief — and byte-identical to
the Python oracle across the corpus and >1.2M doubles. Ship it after **committing
`test_cpp.py` (M1)**. The `Map`/C++20 item (m1) is a pre-existing stdlib constraint the
test happens to surface, not a float regression; clean it up at the author's discretion.
