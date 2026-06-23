# Taut Float Phase-2 — TypeScript codec — Independent Code Review (48)

**Verdict: APPROVE-WITH-NITS.** The runtime float codec is byte-exact against the Python
oracle across **247,484** doubles (0 mismatches) including the full 65,536-pattern half
space and a dense double-rounding stress band; all D0 rules (shortest-form, direct
double→half RNE, NaN-canonical-first, ±0, ±Inf, width-lenient decode) are implemented
correctly. The one real defect is a **type-level** one carried over from Phase 1 and
already flagged by CodeReview55: `schema.ts`'s `TypeRef` scalar union omits `"float"`, so
`codec.ts:17` is a `tsc --strict` no-overlap error and the test fixture must cast `as never`.
Runtime is unaffected. `schema.ts` is outside this agent's owned-file set, so this is a
scope/hand-off issue, not a runtime bug.

Implementation under review (NOTE — it does **not** live in this `taut-ts` worktree; the
TS codec is a sibling repo):
- `/Users/owebeeone/limbo/glial-dev/trial/ts/src/cbor.ts` (the float arm — modified)
- `/Users/owebeeone/limbo/glial-dev/trial/ts/src/codec.ts` (scalar coercion — modified)
- `/Users/owebeeone/limbo/glial-dev/trial/ts/test/float.test.ts` (new, untracked)
- `/Users/owebeeone/limbo/glial-dev/trial/ts/test/float_vectors.json` (new, untracked; byte-identical copy of the taut oracle)

---

## 1. What I verified and how

### Toolchain
- Node `v22.19.0` (`node --experimental-strip-types`), Python `3.10.15`, `tsc` only via
  `npx -p typescript@5` (none installed in the package — matches CodeReview55).

### Owned-file scope / no new deps (PASS)
```
$ git -C /Users/owebeeone/limbo/glial-dev/trial diff --name-only
ts/src/cbor.ts
ts/src/codec.ts
$ git -C .../trial status --short   # untracked
?? ts/test/float.test.ts
?? ts/test/float_vectors.json
$ git diff -- ts/package.json   # (empty — no dependency change)
```
Only `cbor.ts` + `codec.ts` modified; only `test/float*.{ts,json}` added. The brief's
owned set is exactly `cbor.ts`, `codec.ts`, a test under `test/`. `float_vectors.json` is a
verbatim copy of `corpus/float_vectors.json` (`diff` → identical). No new dependencies,
stdlib/DataView only. **Confirmed.**

### (a) Corpus parity (PASS)
In-repo test driving all 22 oracle rows (encode == cbor, decode→re-encode idempotent,
decode-bits == f64 for non-nan rows):
```
$ cd /Users/owebeeone/limbo/glial-dev/trial/ts
$ node --experimental-strip-types --test test/float.test.ts
# tests 2  # pass 2  # fail 0
```
Full package suite (incl. golden corpus, glade corpus, forward-compat, rust interop, and
on a second run the python-server interop test):
```
$ node --experimental-strip-types --test test/*.test.ts
# tests 18  # pass 18  # fail 0  # cancelled 0
```
(CodeReview55 saw `interop.test.ts` fail on "server did not start" — environmental, it
spawns `../../py`; it passed in my runs. Not float-related either way: `grep -i float
test/interop.test.ts` → no hits.)

### (b) Differential fuzz vs the Python reference (PASS — the decisive check)
Oracle bytes were produced by the **actual reference** `taut.wire.cbor.dumps(x).hex()`
(not a re-implementation). The TS side imports the real `cbor.ts` under review and encodes
`new CborFloat(value)`. Harnesses + data in `/tmp/floatfuzz/`. Each run diffs three
streams: TS-encode vs oracle, TS decode→re-encode idempotence, and decode-bits round-trip.

| Set | What it stresses | N | encode≠oracle | re-encode≠ | dec-bits≠ |
|---|---|---:|---:|---:|---:|
| 1 | 10k random f64 + structured edges (±0, ±Inf, 7 NaN payloads, all subnormal classes, 65504/65505/65520, 2^-14/-24/-149, max-single, near-miss-not-half, ±2050 ints, huge mags, common decimals, half-ULP ties) | 36,261 | **0** | **0** | **0** |
| 2 | **Exhaustive: every one of the 65,536 half bit patterns widened to double** + overflow/subnormal/carry tie boundaries | 63,767 | **0** | **0** | **0** |
| 3 | **Double-rounding trap band**: half-ULP exact ties and their nextafter neighbours across 36 exponents (the `double→float→half` failure zone) | 147,456 | **0** | **0** | **0** |
| **Total** | | **247,484** | **0** | **0** | **0** |

The Set-3 band is the spec's trap #1: it densely covers values exactly halfway between two
half-representables (where rounding-to-single-first would tip the tie wrong). Zero divergence
proves the implementation narrows **double→half directly** — confirmed by reading
`doubleToHalfBits` (it works off `f64Bits`, never `Math.fround`).

Reproduce:
```
$ python3 /tmp/floatfuzz/gen_doubles.py            # set 1 -> doubles.hex
$ PYTHONPATH=src python3 /tmp/floatfuzz/oracle.py  # -> oracle.hex (real reference)
$ node --experimental-strip-types /tmp/floatfuzz/ts_harness.ts  # -> ts_enc/reenc/decbits
$ python3 /tmp/floatfuzz/compare.py                # N, mismatch counts
# (sets 2/3 swap in gen_exhaustive.py / the double-rounding band, same compare)
```

### D0 rule audit (direct probes, `/tmp/floatfuzz/nan_probe.ts`, `narrow_unit.ts`, `decode_lenient.ts`)
- **Shortest-form by bit-equality** — `pushShortestFloat` (`cbor.ts:128`): half iff
  `f64BitsEqual(halfToNumber(halfBits), value)`, else single iff `f64BitsEqual(Math.fround(value), value)`,
  else double. Bit-equality via `f64Bits` (DataView `getBigUint64`) so **−0.0 ≠ +0.0**. PASS.
- **NaN → `f97e00` first** (`cbor.ts:129`) — 9 distinct NaN payloads (quiet/signaling,
  ±sign, hi/lo fraction bits) all → `f97e00`. PASS.
- **−0.0 → `f98000`, +0.0 → `f90000`** (distinct). **+Inf → `f97c00`, −Inf → `f9fc00`.** PASS.
- **Direct double→half RNE** — `doubleToHalfBits` + `roundToEvenInt` operate on the f64
  mantissa/exponent directly; verified byte-exact on the 147k double-rounding band. PASS.
- **Width-lenient decode (info 25/26/27 → double)** — `f93c00`, `fa3f800000`,
  `fb3ff0000000000000` all decode to logical `1.0` (bits `3ff0…`); non-preferred `fb`/`fa`
  forms decode correctly. I additionally stressed the `DataView(data.buffer, data.byteOffset
  + off, …)` slice on a non-zero-`byteOffset` `subarray` (info 26/27 path) — correct. PASS.
- **Rule E coercion at the scalar boundary** — `codec.ts:17` `Number(value)` and
  `codec.ts:47` unwrap. Verified **byte-identical to `wire/codec.py`** on a composite native
  value exercising bool→float, int→float, `list<float>`, `map<int,float>`:
  ```
  native { f: true, lst:[false,1,1.5], mp:{5:0.0} }
  PY codec.encode  = a301f93c000283f90000f93c00f93e000381a2010502f90000
  TS codec.encode  = a301f93c000283f90000f93c00f93e000381a2010502f90000   MATCH
  ```
  So `Number(true)→1.0→f93c00`, `Number(false)→0.0→f90000`, `1→1.0`, and recursive
  list/map float scalars all match the reference. PASS. (This closes CodeReview55's P3
  coverage-gap concern — I verified the paths are byte-correct, not merely present.)

---

## 2. Findings by severity

### Blocker
None.

### Major
**M1 — `TypeRef` scalar union omits `"float"`; `codec.ts:17` is a `tsc --strict` no-overlap error.**
`/Users/owebeeone/limbo/glial-dev/trial/ts/src/schema.ts:6` declares
`{ k: "scalar"; scalar: "int" | "str" | "bytes" | "bool" }`. With `"float"` absent:
```
$ npx -p typescript@5 tsc --noEmit --strict ... codec-probe.ts
error TS2367: This comparison appears to be unintentional because the types
'"bytes" | "int" | "str" | "bool"' and '"float"' have no overlap.   # mirrors codec.ts:17
error TS2322: Type '"float"' is not assignable to type '"bytes" | "int" | "str" | "bool"'.
                                                              # constructing a float TypeRef
```
Consequences: (1) the new float branch in `codec.ts:17` is *unreachable per the type
checker* — the package would not pass `tsc --strict`; (2) `float.test.ts:36` masks it with
`} as never)`; (3) a caller cannot construct a float `TypeRef` without a cast.
**Why runtime is fine:** schemas are loaded via `loadSchema(json as Schema)` from JSON
(`schema.ts:108`), so at runtime `t.scalar` does carry the string `"float"` and the branch
executes — proven by the 247k fuzz and the codec-parity match above.
**Fix:** add `"float"` to the union — `schema.ts:6`:
`{ k: "scalar"; scalar: "int" | "str" | "bytes" | "bool" | "float" }`, then drop the
`as never` cast in `float.test.ts:36`.
**Scope caveat (the real judgment call):** `schema.ts` is **not** in this agent's owned-file
set (the Ts brief names `cbor.ts`, `codec.ts`, a test; it says only to *read* `schema.ts`).
The one-line union is also part of the cross-language IR contract Phase 1 authored, so the
agent was arguably right not to edit it unilaterally. I rate this **Major** because it leaves
the public TS type surface lying about a supported scalar and blocks a clean `tsc --strict`,
but it is a Phase-1/hand-off gap, not a defect in the float logic the agent wrote. It needs
an explicit follow-up (owner of `schema.ts` adds `"float"`), not a runtime fix.

### Minor
**m1 — `pushHead` 8-byte arm is dead for floats but technically reachable for huge int
map keys / array lengths via `BigInt(n)` on a non-safe-integer `n`.** Not float-related and
pre-existing; noting only that float review did not touch it. No action.

### Nit
**n1 — `doubleToHalfBits` line 59 returns `signBits | (frac===0n ? 0x7c00 : 0x7e00)` for the
NaN/Inf exponent.** For a *negative* NaN this would yield `0xfe00`, not canonical `0x7e00`.
The path is **unreachable for NaN** because `pushShortestFloat` (`cbor.ts:129`) intercepts
NaN before calling `doubleToHalfBits`, and decode→re-encode also routes NaN through that
guard. So it is correct as wired, but the `0x7e00` here is a latent non-canonical NaN that
only the upstream guard makes safe. Harmless; optionally simplify to compute Inf only
(`frac===0n` case) since the NaN sub-case is structurally dead. No behavioral impact.

**n2 — Decode of half subnormals uses `frac * 2 ** -24` and normals `(1 + frac/1024) * 2 **
(exp-15)` (`cbor.ts:99,108`).** These are exact in double for all 1024×31 half values
(verified via the decode-bits round-trip over the exhaustive set = 0 mismatches), so the
float-arithmetic form is fine here. No action.

---

## 3. Independent take on CodeReview55

**P2 (TypeRef excludes float) — AGREE, and I confirmed it with a compiler.** CodeReview55
asserted this by source inspection only (`tsc` not installed). I reproduced it:
`tsc --strict` emits `TS2367` on the `codec.ts:17` comparison *and* `TS2322` on constructing
a float `TypeRef`. CodeReview55 is correct that the `as never` cast masks the gap and that
the public schema model contradicts the supported scalar. If anything CodeReview55
**understated** it slightly: it framed the failure as "a real TypeScript checker would flag
the comparison" — it does, and it means the package does not pass `tsc --strict` as shipped,
not merely that callers need a cast. I rate it Major (CodeReview55 rated it P2 ≈ Major), with
the scope caveat above that `schema.ts` is outside the owned set.

**P3 (width-lenient decode not directly tested) — AGREE it was a test gap; DISAGREE it is an
open risk.** CodeReview55 correctly noted the in-repo test only decodes preferred-width
vectors. I closed it empirically: `decode_lenient.ts` shows `f93c00` / `fa3f800000` /
`fb3ff0000000000000` all decode to `1.0`, and the 247k fuzz exercises decode→re-encode on
non-preferred widths via the corpus's `fb`/`fa` rows. The implementation is correct; only the
*test* under-covers it. Test-only.

**P3 (codec covers only top-level float + int coercion; missing list/map/bool) — AGREE on the
test gap; the behavior is CORRECT.** CodeReview55 said the impl "appears to recurse correctly
by inspection." I went further and proved it byte-identical to `wire/codec.py` for
`bool→float`, `list<float>`, and `map<int,float>` (the composite-value match above). So the
parity gap is purely in test coverage, not behavior.

**"No CBOR byte-parity bug … 2,012 raw f64 patterns, zero mismatches" — AGREE, and
substantially extended.** CodeReview55's 2,012-pattern probe was directionally right but thin
on the two stated traps. My 247,484-double run — including the **complete** 65,536-pattern
half space and a 147k **double-rounding** band — independently confirms zero byte divergence
and specifically rules out the double-rounding trap and false half-exactness near the 65520
overflow tie. No disagreement; stronger evidence.

**Untracked test files note — AGREE.** `float.test.ts` and `float_vectors.json` are
untracked; they must land with the change. Confirmed via `git status --short`.

Net: CodeReview55's findings are accurate and well-targeted. It missed nothing material on
the float logic. Its main limitation was the absence of a compiler run (now supplied) and a
shallow fuzz (now deepened). I add nit n1 (latent non-canonical NaN in the dead Inf/NaN arm
of `doubleToHalfBits`), which CodeReview55 did not mention.

---

## 4. What I could not verify
- **`tsc --strict` on the package as a whole.** No `tsc`/`node_modules` in the package; I
  type-checked isolated probe files against the real `schema.ts` via `npx -p typescript@5`.
  That is sufficient to confirm M1/P2 (the errors are local to the `scalar` union), but I did
  not run a full-project type-check with the package's own tsconfig (there is none invoked by
  the test runner — it uses `node --experimental-strip-types`, which **strips** types without
  checking them; this is why the `as never` cast suffices at runtime).
- **`interop.test.ts` python-server path** is environment-dependent (spawns `../../py`); it
  passed in my runs but is not float-relevant.

---

## 5. Bottom line
The hand-rolled float narrowing is correct: direct double→half RNE, NaN-canonical-first,
signed-zero/Inf exact, width-lenient decode, and rule-E coercion are all byte-identical to the
Python oracle across a quarter-million doubles with zero mismatches, including the two spec
traps. Ship the runtime. The one outstanding item is the `schema.ts` `TypeRef` union (M1/P2)
— a Phase-1 contract line outside this agent's owned files; route it to the `schema.ts` owner
to add `"float"` and drop the `as never` cast, so the package type-checks under `--strict`.
```
verified by: independent reviewer (review 48) — 2026-06-23
fuzz artifacts: /tmp/floatfuzz/  (gen_doubles.py, gen_exhaustive.py, oracle.py, ts_harness.ts, compare.py)
```
