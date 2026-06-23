# Taut Float — Phase 2 Rust — Independent Code Review (CR48)

**Verdict:** **APPROVE.** The Rust shortest-form float codec is byte-identical to the
Python oracle across every check I ran — corpus parity, 258,874 differential-fuzz
doubles (0 mismatches), and an exhaustive 65,536-pattern half-decode sweep. The
hand-rolled `narrow16` is correct (direct double→half RNE, no double-rounding, no
new deps). One **minor** packaging risk (the test file is untracked) carried over
from CR55 and one genuinely-minor robustness nit on decode bounds. Nothing blocks
the merge.

Reviewer stance: independent second opinion. I re-derived the narrowing math and
empirically diffed the Rust codec against the Python reference rather than trusting
the existing review.

---

## 1. What I verified and how

Toolchain present: `rustc 1.96.0`, `cargo 1.96.0`, `python3 3.10.15`. The runtime is a
vendored snippet (no `Cargo.toml` in `trial/rs`), so all Rust harnesses live in
`/tmp/taut-rust-review/` and include the **actual file under review** via
`#[path = ".../src/taut/gen/runtime/cbor.rs"]` (not a copy) — so I am testing the
exact bytes that will land.

### (a) Corpus parity — PASS (22/22)
Harness `/tmp/taut-rust-review/corpus_parity.rs` drives all 22 rows of
`corpus/float_vectors.json` through the runtime: (1) `encode(f64::from_bits(bits)) == cbor`,
(2) re-encode idempotence `encode(decode(cbor)) == cbor`, (3) `decode(cbor).to_bits() == bits`
(non-NaN rows), plus width-lenient decode of `1.0` as `f9/fa/fb`.

```
$ rustc -O corpus_parity.rs -o corpus_parity && ./corpus_parity
corpus rows: 22, failures: 0
CORPUS PARITY: PASS
```

### (b) Differential fuzz vs the Python oracle — 0 mismatches across 258,874 doubles
Oracle bytes come from the reference itself:
`cd .../taut-rust && PYTHONPATH=src python3` -> `taut.wire.cbor.dumps(x).hex()`.
The Rust side (`/tmp/taut-rust-review/fuzz_encode.rs`) reads f64-bit-hex lines, encodes
with the runtime, and (self-check) asserts `encode(decode(enc)) == enc` on every value.
I then `paste`/`awk`-diffed the two hex streams.

| Stream | Doubles | Mismatches | Rust self-check fails |
|---|---|---|---|
| Random 64-bit + structured edges (`gen_fuzz.py`) | **17,423** | **0** | 0 |
| Targeted danger-zone sweep (`gen_targeted.py`) | **206,602** | **0** | 0 |
| Double-rounding seam witnesses (`gen_dr` inline) | **34,849** | **0** | 0 |
| **Total** | **258,874** | **0** | **0** |

The random set covers ±0, ±Inf, 10 distinct NaN payloads, plain integers, half/single/double
subnormals, the 65504/65505 boundary, 2^-14 / 2^-24 / 2^-149 / 2^-1074, max-single,
near-miss-not-half values, all powers of two across the exponent range, and 10k uniform
random 64-bit patterns. The targeted sweep densely samples every half ULP seam (all 2^16
half values widened to double **+/-1 ULP**, the subnormal grid `k*2^-24` for k in [0,1100] with
exact tie points, the 65520 round-to-inf seam, the carry-into-next-exponent cases, and the
max-single overflow seam). The double-rounding set hammers `(k+0.5)*2^-24` subnormal ties
and `(frac+0.5)/1024` normal-mantissa ties.

```
$ ./fuzz_encode < doubles.txt > rust_out.txt   # 17423 lines, 0 SELFCHECK_FAIL
$ paste doubles.txt oracle.txt rust_out.txt | awk '$2!=$3{c++} END{print "mismatches:",c+0; print "total:",NR}'
mismatches: 0
total: 17423
$ ./fuzz_encode < t_doubles.txt | paste t_doubles.txt t_oracle.txt - | awk '$2!=$3{c++} END{print c+0, NR}'
0 206602
# double-rounding seam: 0 34849
```

### (c) Exhaustive half-decode parity — PASS (65,536/65,536)
`/tmp/taut-rust-review/half_decode.rs` decodes every `F9 xx xx` pattern and emits
`<f64bits> <re-encode-hex> <isNaN>`; compared against the oracle's decode of the same bytes.
This fully validates `f16_bits_to_f64` and the major-7 `info 25` arm.

```
patterns: 65536
nan-flag mismatches: 0
re-encode mismatches: 0
decoded-bits mismatches (non-nan): 0
```

NaN half patterns (exp=0x1F, frac!=0) decode to a NaN whose payload differs from a specific
f64 NaN — that is expected and correct; I bit-compare only non-NaN and assert NaN-ness +
canonical re-encode (`F9 7E00`) for the NaN patterns, both clean.

### (d) Overflow / Inf handling — explicitly confirmed
Finite values just past max-single (`2^128`, `3.5e38`, max-single+eps) correctly fall through
to **double `FB`**, *not* single-Inf — because the single test compares `(value as f32 as f64).to_bits()`
against the original; the `as f32` saturation to `f32::INFINITY` widens back to a bit pattern
that != the finite value, so the branch is rejected. +/-Inf -> `F9 7C00 / F9 FC00`.

### (e) Subnormal/normal seam — explicitly confirmed
`1023*2^-24 -> F9 03FF` (max half subnormal), `1024*2^-24 = 2^-14 -> F9 0400` (min half
normal). Near-tie values that are not exactly half-representable (`1023.5*2^-24`,
`0.5*2^-24`, `1.5*2^-24`) correctly fall through to single/double — the exactness gate
`widen(narrow(v)).to_bits() == v.to_bits()` rejects them.

### (f) Generated code compiles + round-trips float (closes a CR55 gap)
CR55 noted the generator test is string-only and never compiles a float-bearing schema.
I generated a message with `float`, `Option<float>`, `List<float>`, and `Map<int,float>`
fields via `rust._emit`, wired it against `cbor.rs`, **compiled with rustc, and ran it**:
the struct round-trips through encode/decode with `-0.0` preserved (optional field), `Inf`
in a list, and double-only values in a map; the `roundtrip("M", ...)` dispatcher is byte-stable.
```
GENERATED FLOAT STRUCT ROUNDTRIP: PASS
```

### (g) Project suite + regen gate + no-new-deps
```
$ PYTHONPATH=src python3 -m pytest src/tests -q            -> 167 passed
$ pytest src/tests/test_rust.py src/tests/test_regen.py -q -> 6 passed
$ git diff --name-only -> src/taut/gen/runtime/cbor.rs, src/taut/gen/rust.py   (only the 2 owned files)
$ grep -nE 'extern crate|half::|use half' cbor.rs -> (none)   # no banned `half` crate, zero deps
```
`test_rust.py::test_rust_runtime_matches_float_vectors` actually invokes `rustc --test` on
the runtime and runs it — a real compiled gate, not just a string match.

---

## 2. D0 rule audit (against the code)

| D0 rule | Code site | Verdict |
|---|---|---|
| Shortest-form half->single->double, **bit** equality | `enc_float` `cbor.rs:199-219` — `f16_bits_to_f64(bits).to_bits() == value.to_bits()`, then `(single as f64).to_bits() == value.to_bits()` | OK; `-0.0 != +0.0` via bit compare |
| narrow16 = RNE, **direct** double->half | `f64_to_f16_bits` `cbor.rs:123-162` operates on the f64 bit pattern; `round_shift_right` `cbor.rs:106` is round-half-to-even | OK; no double->float->half path; 34,849 seam witnesses confirm no double-rounding |
| NaN -> `F9 7E00` **before** width tests | `enc_float` `cbor.rs:200-203` (`value.is_nan()` first); narrowing also maps any NaN payload to `0x7e00` `cbor.rs:130` | OK; all 10 NaN payloads + all NaN half patterns canonical |
| `-0.0 -> F9 8000`; +/-Inf -> `F9 7C00/FC00` | `cbor.rs:132-133` (exp==0 -> `sign`), `cbor.rs:129-130` (inf) | OK; verified |
| decode accepts info 25/26/27, raw payload (not `read_arg`) | `dec` major-7 `cbor.rs:349-362` reads raw 2/4/8 bytes | OK; matches brief |
| value-model: `Float(f64)` variant + `.float()` accessor | `cbor.rs:10`, `cbor.rs:38-44` | OK |
| codegen: `float`->`f64`, encode/encode_ref/decode | `rust.py:35,51-52,72,100` | OK; compiles + round-trips |

**Narrowing math, re-derived and confirmed correct:**
- Subnormal shift `28 - e` (`cbor.rs:139`): `round(mant * 2^(e-52) / 2^-24) = round(mant >> (52-24-e)) = round(mant >> (28-e))`. OK
- Subnormal round-up-into-normal clamp `sub >= 0x400 -> sign|0x0400` (`cbor.rs:143-145`): correct — `0x0400` is the min-normal half (exp=1, frac=0). The exactness gate then rejects it if it wasn't truly exact. OK
- Normal shift `42` (`cbor.rs:153`): drop 53->11 significand bits (52-10). After rounding `sig in [0x400,0x800]`; stored `sig-0x400`. The `sig==0x800` carry bumps the exponent (`cbor.rs:154-160`) and overflows to single via `half_exp>=31 -> None`. OK

---

## 3. Findings by severity

### Blocker — none.
### Major — none.

### Minor

- **M1 — `src/tests/test_rust.py` is untracked; the compiled parity gate can be dropped on merge.**
  `git status --short` shows `?? src/tests/test_rust.py` while the staged-able diff is only the
  two runtime/codegen files. If only the tracked diff lands, Phase 2 ships *without* its
  rustc-backed corpus gate and the Python shape test. This is the one real CR55 finding and I
  **agree** with it. **Fix:** `git add src/tests/test_rust.py` before committing.

### Nits

- **N1 — decode reads payload bytes without a length check (`cbor.rs:349-362`, also `read_arg` `:272-291`).**
  A truncated `F9`/`FA`/`FB` (e.g. bytes `[0xf9]`) indexes `data[off]`/`data[off+1]` and panics
  with an out-of-bounds slice rather than a domain error. The Python reference has the same
  shape (it would short-read / struct.error), and the brief scopes this to trusted in-repo
  corpus bytes, so it's not a regression — but a `data.get(off..off+2)` guard returning a clean
  error would harden the decoder. Out of scope for this change; flag only.

- **N2 — `f16_bits_to_f64` reconstructs via float arithmetic, not bit assembly (`cbor.rs:164-197`).**
  `(1.0 + frac/1024.0) * 2f64.powi(exp-15)` and `frac * 2^-24` happen to be **exact** for all
  half values (verified: 65,536/65,536 bit-exact vs the oracle), so this is correct today. A
  pure bit-shift widening would be marginally more obviously-exact and dodge any future doubt
  about `powi`, but there is no bug. Leave as-is.

- **N3 — cosmetic reflow churn in the diff.** The edit reflowed several pre-existing one-line
  `if let ... else ...` accessors (`int`/`text`/`bytes`/`boolean`/`array`/`map_entries`) and two
  `read_arg`/`dec` arms into multi-line form. Behavior-neutral, but it inflates the diff beyond
  the float change. Per the repo's "keep moves byte-identical, don't reflow" habit this is mild
  noise; not worth a re-roll.

---

## 4. Independent take on CodeReview55

- **CR55's sole finding (P2: untracked `test_rust.py`) — I AGREE.** Confirmed independently via
  `git status --short`. This is the only thing that could actually bite the merge. Carried here as M1.
- **CR55's "no P0/P1 correctness issues" — I AGREE, and I went further to earn it.** CR55's runtime
  evidence was the 22-row corpus + an exhaustive half-payload re-encode + an f32 `-0.0`/NaN check.
  That is sound but thin on the *encode* side — it does not stress the narrow16 RNE seams or the
  double-rounding trap, which is exactly where a hand-rolled narrower fails. My 258,874-double
  differential fuzz (incl. 34,849 tie/seam witnesses) and the explicit double-rounding,
  overflow, and subnormal-seam probes close that gap and corroborate the conclusion.
- **CR55's residual risk "no Cargo.toml in `trial/rs`, couldn't run a crate parity test" — I AGREE**
  it's absent, and I confirmed `trial/rs` has no `Cargo.toml`. I worked around it with a `/tmp`
  harness that `#[path]`-includes the real file (encode + exhaustive decode) and a standalone
  rustc compile of a generated float-bearing struct — so the *substance* of that gate is now
  covered out-of-band, even though the in-repo crate gate still doesn't exist (Phase 3.2's job).
- **CR55's residual risk "generator test is string-only, no compiled generated schema" — I AGREE,
  and I closed it:** generated a float-bearing message, compiled it with rustc, ran a round-trip.
  See section 1(f). CR55 left this as an open risk; it is now discharged.
- **Nothing in CR55 is overstated.** I found no claim to walk back. The items I add beyond it are
  N1-N3 (all minor/nit) and the empirical encode-side proof CR55 lacked.

---

## 5. What I could not verify

- **In-repo Rust crate `corpus_byte_parity` gate.** `trial/rs` has no `Cargo.toml`/`vectors.rs`,
  so there is no consuming crate to run. I substituted out-of-band `/tmp` harnesses that include
  the exact runtime file; the *bytes* are proven, but the in-repo crate-level gate remains
  Phase 3.2 work (consistent with the plan).
- **Float in the shared griplab golden corpus.** Deferred to Phase 3.1 by design; `generated.rs`
  has no float field yet, so the golden-regen path doesn't exercise float. Not in scope for P2.1.
- **The other 7 languages.** Out of scope — this review is Rust only.

---

### Harness artifacts (all under `/tmp/taut-rust-review/`, none written into the repo)
`corpus_parity.rs` . `fuzz_encode.rs` . `half_decode.rs` . `gen_fuzz.py` . `gen_targeted.py` .
`crate_test/` (generated-struct compile) — reproducible with `rustc -O` + the `paste|awk` diffs shown above.
