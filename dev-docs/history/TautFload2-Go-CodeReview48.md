# Taut Float — Phase 2 Go — Independent Code Review (48)

**Verdict: APPROVE.** The Go `float` arm is byte-identical to the Python oracle across
**5,246,153 unique doubles, 0 mismatches** (encode, re-encode idempotency, and
decode→bits), including an exhaustive sweep of all 65,536 half values, a 5.1M dense
sweep of the half subnormal/normal transition band, 40 hand-constructed double-rounding
cases, and the full 22-row corpus. The hand-rolled `narrow16` is direct (no
double-rounding), NaN is canonicalised before width selection on encode *and* on the
decode→re-encode path, −0.0 is preserved, and only the three owned files (+ an untracked
parity harness) changed. No new dependencies.

Reviewer stance: independent, skeptical. I built my own harness from scratch in `/tmp`,
did not reuse the prior author's `/tmp` artifacts, and cross-checked CodeReview55's claims
against the code myself.

---

## 1. What I verified and how

### Scope / hygiene (rule: touch only owned files, no new deps)
`git -C …/taut-go status` + `git diff` confirm exactly three tracked files modified
(`src/taut/gen/go.py`, `src/taut/gen/runtime/cbor.go`, `src/tests/test_go.py`) plus two
untracked additions the brief permits (`src/taut/gen/runtime/cbor_float_test.go` parity
harness, and the review docs). No edits to `ir/*`, `wire/*`, `scaffold.py`, the corpus, or
any other language. `cbor.go` imports only `math` + `sort` (both stdlib) — no new deps.

### Build + the author's harness
- `GO111MODULE=off go test .` in `src/taut/gen/runtime` → **ok** (22 corpus rows: encode,
  decode-kind, re-encode, decode-bits; plus all-three-widths-decode test). go1.26.4.
- Independent harness in `/tmp/gofuzz48`: vendored `cbor.go` into a `taut` subpackage +
  a `main.go` that reads f64-bit-hex from stdin and emits `enc  reenc  decbits`. Built clean.

### (a) Corpus parity — PASS (22/22)
Extracted the 22 `f64` bit patterns from `corpus/float_vectors.json`, ran the Go codec and
the Python oracle (`from taut.wire import cbor`) over the identical list, compared against
the committed `cbor` column. Every row: `go_enc == corpus`, `go_reenc == corpus`,
`oracle_enc == corpus`. Re-encode idempotency holds (covers the three NaN rows without a
bit-compare). Commands:
```
PYTHONPATH=src python3 …  # dump f64 bits -> corpus_bits.txt
/tmp/gofuzz48/gofuzz48 < corpus_bits.txt              # Go encode/reencode
PYTHONPATH=src python3 /tmp/gofuzz48/oracle.py < …    # oracle encode/reencode
# side-by-side: all 22 rows OK
```

### (b) Differential fuzz vs the Python oracle — PASS (0 mismatches)
Generated structured + random doubles in Python (deterministic seed) and ran the SAME
bit-patterns through the Go codec and the oracle, diffing encode / re-encode / decode-bits.

| Set | Unique doubles | enc mismatch | reenc mismatch | decbits mismatch (non-NaN) |
|---|---|---|---|---|
| General fuzz (40k random 64-bit patterns + 20k "nice" + 20k near-half + powers-of-two ±1 ULP across the full exponent range + **exhaustive all-65536-half** widened + nudged + edge battery) | 202,387 | **0** | **0** | **0** |
| Dense half subnormal↔normal band (full 52-bit mantissas, biased exp 990–1041, ×2 sign, ×3 round-tie tags) | 5,111,808 | **0** | — | — |
| Constructed double-rounding cases (direct vs via-single half differ by ≥1 ULP) | 40 | **0** | **0** | **0** |
| Edge boundaries (65504/65505/65520, 2⁻¹⁴, 2⁻²⁴, 2⁻²⁵, 2⁻²⁶, 1.5·2⁻²⁵, 2⁻¹⁴⁹, max/over-max single, max double) | 12 | **0** | — | — |
| Corpus | 22 | **0** | **0** | **0** |
| **Total distinct f64 bit-patterns** | **5,246,153** | **0** | **0** | **0** |

The exhaustive-half sweep is the strongest single check: for *every* value that is exactly
representable as half, the Go `narrow16` round-trip must select F9 and emit the right two
bytes — all 65,536 pass. The dense subnormal band (5.1M) nails the `unbiased ∈ [-25,-14]`
subnormal rounding math where off-by-one shift/tie bugs would live.

### Double-rounding trap (Base §"Two correctness traps" #1) — clean
Constructed 40 doubles where `double→half` (direct RNE, what Go does) differs from
`double→float→half` by ≥1 ULP. None are exactly half-representable, so all correctly fall
through to `fb…` double — and Go matches the oracle on every one. The exactness gate
(`math.Float64bits(halfToFloat64(h)) == math.Float64bits(v)`) is what makes a stray
narrowing harmless: a wrong half can never pass because it won't bit-round-trip. Confirmed
the gate uses **bit** equality (so −0.0 ≠ +0.0), not `==`.

### NaN canonicalisation (rule B) — clean on encode AND decode
- Encode: `math.IsNaN(v)` is the first test in `floatBytes` (cbor.go:140), before any width
  selection — every NaN payload (quiet, signaling, neg, custom, all-ones) emits `f97e00`.
  Verified in the fuzz (6 distinct NaN bit patterns) and corpus (3 NaN rows).
- Decode→re-encode: fed half/single/double NaN wire forms (`f97c01`, `f97e01`, `f9fe00`,
  `fa7fc00000`, `fa7f800001`, `fb7ff8…`, `fb7ff0…000001`) → each decodes to a Go NaN and
  **re-encodes to `f97e00`**. The `halfToFloat64` quiet-NaN reconstruction
  (`sign | 0x7ff8… | frac<<42`) yields a genuine double NaN that `math.IsNaN` catches on the
  way back. `+Inf`/`-Inf` are NOT treated as NaN and round-trip to `f97c00`/`f9fc00`.

### −0.0 (rule C) — preserved
`encode(math.Copysign(0,-1)) == f98000`, and round-trips with the sign bit intact
(`8000000000000000`). (Note: Go's `-0.0` *literal* is +0.0 at compile time — a harness
gotcha, not a codec issue; verified with `Copysign`.)

### ±Inf — half-exact
`+Inf → f97c00`, `-Inf → f9fc00` (encode and decode→re-encode). The `unbiased > 15` and
post-round `halfExp >= 31` overflow paths correctly return `ok=false`, so finite values just
above half-max (65505 → `fa477fe100`) fall through to single, never to a half Inf.

### Decode width-leniency (rule D) — pass
`Decode` major-7 handles info 25/26/27. The author's `TestFloatDecodeAcceptsAllWidths`
proves `f93c00`, `fa3f800000`, `fb3ff0000000000000` all decode to `1.0`. half→double and
single→double widening is exact (verified by 0 decbits mismatches over 200k+ non-NaN rows).

### Value-model integration (Go note) — correct
New `F float64` field added to the `Cbor` struct (cbor.go:40) — **separate from the int `I`
slot** where bool lives. `KFloat` extends the iota block to 7 (cbor.go:23).
`CFloat`/`.Float()` added. `enc` gains `case KFloat`, `dec` gains 25/26/27. Generator
(`go.py`): `_go_ty["float"]→"float64"`, `_enc→CFloat(expr)`, `_dec→expr.Float()`. No
`_default` map for Go (consistent with plan §6 — only kotlin/swift need one).

### Codegen compiles + round-trips (a gap CR55 left open)
Generated the `FloatMsg` codec (scalar+list+map+optional float, forward-compat on),
compiled it against the runtime, and ran a round-trip: scalar `1.5`, a `[]float64`
mixing 0.0/+Inf/65504/100000/π, a `map[int64]float64` with a genuine −0.0 value, and an
optional. `Encode(ToCbor)` → `FromCbor(Decode)` → `Encode(ToCbor)` is **byte-identical**,
fields decode correctly, and the −0.0 map value survives as `8000000000000000`. So the
generator emits compilable, correct Go, not just the right substrings.

### Python suite — green
`PYTHONPATH=src python3 -m pytest src/tests -q` → **166 passed**. `test_go.py` → 4 passed
(adds the float scalar/list/map/optional shape assertions).

---

## 2. Findings by severity

### Blocker — none.
### Major — none.
### Minor — none.

### Nits (non-blocking, no fix required for Phase 2 sign-off)
1. **Dead-but-correct NaN arm in `float64ToHalfBits`** (cbor.go:177–179). The
   `exp == 0x7ff && frac != 0 → (0x7e00, true)` branch is unreachable from the encoder
   because `floatBytes` filters NaN first (cbor.go:140). It is harmless (and arguably good
   defensive symmetry), but a reader may wonder why it returns `ok=true` for a NaN. Optional:
   a one-line comment noting NaN is pre-filtered on the encode path. Not a defect.
2. **`roundShiftEven` `shift == 0` guard is dead code** (cbor.go:159–161). From the encoder,
   `shift` is always 42 (normal) or 43–53 (subnormal, `28 - unbiased` with
   `unbiased ∈ [-25,-15]`); it is never 0. Defensive only; no behavioural impact, no overflow
   risk (`1<<(shift-1)` ≤ `1<<52`, fits uint64). Fine to leave.
3. **Harness not runnable from repo root in module mode.** `go test ./src/taut/gen/runtime`
   fails (no root `go.mod`); needs `GO111MODULE=off`. This matches the runtime's nature
   (vendored snippet, not a standalone module) and CR55 already noted it. Documentation-only.

---

## 3. Independent take on CodeReview55

**Net: I agree with CR55's bottom line (no correctness issues), and my 5.2M-double
differential fuzz upgrades its confidence from "I inspected the boundaries" to "byte-exact,
empirically, against the oracle."**

- **Agree** — the value-model claims (new `KFloat` + separate `F float64`, not the int
  slot), NaN-before-width, −0.0 via bit-equality, three-width decode, and the generator
  mappings are all accurate to the code (I re-checked each line cited).
- **Agree** — its three "residual risks" are real and fairly stated: (a) module-mode
  invocation needs `GO111MODULE=off`; (b) the Python test is string-shape only, no compiled
  generated-message roundtrip; (c) the hand-rolled double→half path had no
  exhaustive/randomized cross-check *in this change*.
- **What I add that CR55 did not do** — I closed risks (b) and (c) empirically:
  (c) is now exhaustive over all 65,536 halves + 5.1M subnormal-band probes + 40 constructed
  double-rounding cases + 202k random doubles, 0 mismatches; (b) I compiled the generated
  `FloatMsg` codec against the runtime and proved a byte-identical round-trip (incl. −0.0 in
  a map). Neither was strictly required for Phase-2 sign-off, but they remove the two
  standing doubts.
- **Nothing overstated** in CR55. The only thing it *missed* is the two dead-code nits above —
  immaterial.
- **Caveat on CR55's commands** — it reported the Homebrew `python3` (3.14) lacks pytest and
  fell back to `python`. In *this* environment `python3` is 3.10.15 with pytest present and
  the taut import working, so the suite ran directly under `python3`. Doesn't change the
  conclusion; just an environment difference.

CR55 is a correct, fair review — not a rubber stamp. I concur with it and reinforce it.

---

## 4. What I could not verify
Nothing material was unrunnable. Both toolchains (go1.26.4, Python 3.10.15 with the taut
package) were available; I built and ran every check above. The cross-language in-repo byte
gate (plan Phase 3.2) does not exist yet by design, so byte-parity for Go is currently
proven out-of-band — which is exactly what this review (and CR55) provide for Phase 2.

---

## Appendix — key commands
```
# build/run author harness
cd src/taut/gen/runtime && GO111MODULE=off go test .

# independent harness (vendored cbor.go in /tmp/gofuzz48/taut + main.go)
cd /tmp/gofuzz48 && go build -o gofuzz48 .

# corpus parity
python3 (dump corpus f64 bits) ; ./gofuzz48 < corpus_bits.txt ; oracle.py < corpus_bits.txt

# differential fuzz (general 202k)
python3 gen.py > bits.txt
./gofuzz48 < bits.txt > go_out.txt
PYTHONPATH=src python3 /tmp/gofuzz48/oracle.py < bits.txt > oracle_out.txt
# diff enc/reenc/decbits -> 0/0/0

# dense subnormal band (5.1M) and double-rounding (40) and edges (12): all enc 0 mismatch
# generated FloatMsg compiled against runtime + byte-identical round-trip incl -0.0

# python suite
PYTHONPATH=src python3 -m pytest src/tests -q   # 166 passed
```
