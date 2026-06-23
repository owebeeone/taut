# Taut Float — Phase 2 Base Brief (all language ports)

Read this first. Your per-language brief (`TautFloatP2-<Lang>.md`) adds the specifics
and overrides nothing here. Companion to [TautFloatPlan.md](TautFloatPlan.md).

## Mission
Phase 1 landed `float` in the **Python reference** (on `main`). Your job: implement the
same **shortest-form CBOR float** in ONE target language's hand-rolled codec so it is
**byte-identical** to the Python oracle. One agent per language, in an isolated git
worktree, touching only your own files.

## The wire profile (locked — D0)
A taut `float` is a logical IEEE-754 **double**; the wire picks the shortest lossless
width (CBOR *preferred serialization*, RFC 8949 §4.2.1):

- **A.** Emit the smallest of half (`0xF9`, 2B) / single (`0xFA`, 4B) / double (`0xFB`, 8B)
  that round-trips the value **exactly**; payload is big-endian IEEE-754.
- **B.** **NaN → canonical `F9 7E00`**, checked FIRST (before any width test).
- **C.** **−0.0 preserved** (`F9 8000`).
- **D.** **Decode accepts all three widths** (`info` 25/26/27), widening to double —
  width-lenient, like the existing integer decoder.
- **E.** (Interpreter langs only) coerce the field value to double at the scalar boundary.

### Encode algorithm — port this faithfully
```
encode_float(v):
  if isNaN(v):            emit F9 7E 00; return        # B — before width tests
  if half_exact(v):       emit F9 + half_bits(v)       # 2 bytes BE
  elif single_exact(v):   emit FA + f32_bits(v)        # 4 bytes BE
  else:                   emit FB + f64_bits(v)        # 8 bytes BE

half_exact(v)   = widen16(narrow16(v)) bit-equals v   (and narrow16 didn't overflow)
single_exact(v) = (double)(float)v     bit-equals v   (and didn't overflow)
```
Compare with **bit equality** so `−0.0 ≠ +0.0` (NaN already handled). `±Inf` are
half-exact → `F9 7C00` / `F9 FC00`.

### ⚠ Two correctness traps
1. **Double-rounding.** Narrow double→half **directly** (round-to-nearest-even). Do NOT
   go double→float→half — rounding twice yields wrong bytes for some values.
2. **NaN payloads.** Many bit patterns are NaN; every one must emit `F9 7E00`. Test
   `isNaN` before width selection.

## The oracle — `corpus/float_vectors.json`
22 rows of `{note, f64: "<16 hex bits>", cbor: "<hex>"}`. **This file is the contract.**
For every row your codec must satisfy:
1. **encode** — build the double from the `f64` bit pattern → `encode` produces `cbor`.
2. **re-encode parity** — `encode(decode(unhex(cbor))) == cbor` (covers NaN without a bit-compare).
3. **decode→bits** (skip `nan*` rows) — `f64_bits(decode(unhex(cbor))) == f64`.

Second oracle: the Python reference `src/taut/wire/cbor.py` — `_float_bytes` (encode) and
the major-7 `info 25/26/27` decode arm. It uses `struct` for narrowing; you hand-roll
unless your language has native half (your brief says which).

## Scope — touch ONLY your files
Your brief names exactly the files you own. **Do NOT edit** `ir/*`, `wire/cbor.py` /
`codec.py` / `jsoncodec.py`, `gen/scaffold.py`, `corpus/float_build.py`,
`corpus/float_vectors.json`, or any other language's files — Phase 1 already landed the
shared surface (incl. all `scaffold.py` stub maps). **No new dependencies** — every
runtime is hand-rolled / stdlib-only; keep it that way.

## Workflow (AGENTS.md Rule 0 — TDD, non-negotiable)
1. Write a failing test driving your float arm against `corpus/float_vectors.json` (or the
   language's parity harness).
2. Implement the smallest change to pass.
3. **If your toolchain is in the worktree, compile + run** the parity harness — the
   strongest check. If not, mirror the Python reference line-for-line and hand-verify every
   corpus row; Phase 3.2 adds the in-repo cross-language gate as backstop.
4. Update `gen/<lang>.py` so generated code emits/decodes float, and extend the Python-side
   shape test `src/tests/test_<lang>.py` — it runs in the main suite without your target
   compiler.
5. Keep the suite green: `PYTHONPATH=src python3 -m pytest src/tests -q`.

## Value-model idioms (how each runtime holds a CBOR value)
- **Enum/variant** (Rust, Swift, Kotlin*, TS-wrapper): add a `Float` arm.
- **Struct/class** (Go, Java, Kotlin): bool lives in the int slot — add a **new**
  `double`/`float64` field + a kind constant; do NOT reuse the int slot.
- **Tagged object** (JS): `{ kind: FLOAT, f }`.
- **Structural** (TS `cbor.ts`): a `number` already means an int — floats need a wrapper class.

## Definition of done
Runtime byte-matches all 22 corpus rows (compiled+run where possible) · `gen/<lang>.py`
emits the float native type + codec calls · Python shape test green · no other files
touched · no new deps.
