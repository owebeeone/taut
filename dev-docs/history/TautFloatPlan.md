# Taut — `float` Scalar Support

**Status:** **Phase 1 complete + code-reviewed** (Python reference green — 165 tests). Phase 2 (8-way fan-out) ready. D0 locked: shortest-form.
**Date:** 2026-06-23
**Related:** [TautDecisions.md](TautDecisions.md) (ratify D0 here) ·
[TautModules.md](TautModules.md) · [CodeShape.md](CodeShape.md)

## 1. Why

Taut's scalar set is `INT / STR / BYTES / BOOL` (+ `List`, `Map`) — **no float**.
An oversight, not a deliberate exclusion of real numbers. The frozen CBOR substrate
explicitly omits floats (`wire/cbor.py` docstring: *"No floats…"*), and
`test_cbor.py` actively asserts `cbor.dumps(1.5)` **raises**. Adding a `float`
scalar means extending the frozen wire profile and threading the new kind through
**9 CBOR codecs** + **9 codegen backends**, byte-identically.

Taut keeps **one** `float` type (logical IEEE-754 double); the wire picks the
shortest lossless width. This is *not* protobuf's fixed32/fixed64 float menu — the
width is an encoding detail, never a type the author selects. Taut stays tight.

## 2. Verified ground truth

**Union / map-key collision — non-issue.** `TypeRef` (`ir/model.py`) is a *closed*
union `Scalar | EnumRef | MsgRef | ListOf | MapOf`; there is **no `oneof`/union
type**. Map keys are restricted to `int/str/bool` (`ir/validate.py`), so a key is
always exactly one declared scalar kind — `int(0)` and `float(0.0)` can never
coexist as keys. **Decision:** do **not** add `float` to the key allowlist; float
keys stay rejected (consistent with `bytes` being key-ineligible, and with NaN/−0
being unusable as keys).

**Parity is uneven — in *verification*, not in *type surface*.** All 9 backends map
the four scalars + List/Map + forward-compat residual uniformly, but byte-exact
gating is lopsided:

| Backend | In-repo gate |
|---|---|
| **Python** (`wire/cbor.py` + golden corpus) | RFC vectors + byte-exact golden — **the oracle** |
| **Rust** | `generated.rs` regen + golden bytes |
| **C++** | `static_assert` vs corpus (compile-time) |
| TS, Go, Kotlin, Java, JS, Swift | **shape tests only**; bytes verified **out-of-band** in CI |

→ A float byte divergence in `cbor.{go,kt,js,swift,java,ts}` would **not** be caught
in-repo today. **Phase 3** closes this with a cross-language byte gate driven by the
conformance corpus below.

## 3. Decision D0 — wire profile (LOCKED: shortest-form)

Taut floats follow CBOR **preferred serialization** (§4.1 / §4.2.1) — the same rule
taut already obeys for integer arguments. This keeps floats *consistent* with the
codec's existing `§4.2.1` claim rather than carving out a private exception.

| | Rule | Notes |
|---|---|---|
| **A** | **Shortest of the three IEEE widths** that round-trips the value exactly: try half (`F9`, 2B) → else single (`FA`, 4B) → else double (`FB`, 8B). | Stop at the three float widths. Do **not** fold integer-valued floats into CBOR ints (that's dCBOR; it would collide the float/int wire reps and break taut's typed distinction). |
| **B** | **NaN → canonical `F9 7E00`** (half quiet-NaN). | Platform NaN payloads differ; canonicalising is required for byte-agreement across codecs. |
| **C** | **−0.0 preserved** (shortest: `F9 8000`). | Deterministic; no key hazard (float keys disallowed). |
| **D** | **Decode accepts all three widths** (`info` 25/26/27), widening to double. Width-lenient on decode, exactly like the existing integer decoder. | Half/single → double widening is exact (no rounding). |
| **E** | **Coerce at the scalar boundary** in the Python/TS interpreters (`float(value)`). | `int(0)` into a float field → `F9 0000`. Static targets coerce via their native `f64`/`double`. |

Canonical vectors (illustrative — the **Python reference pins the authoritative,
exhaustive set** incl. subnormal/boundary cases):

```
value                         width   bytes
0.0                           half    F9 0000
-0.0                          half    F9 8000
1.0                           half    F9 3C00
1.5                           half    F9 3E00
65504.0     (max half)        half    F9 7BFF
5.9604645e-8 (2^-24 subnorm)  half    F9 0001
100000.0                      single  FA 47C35000
3.4028235e38 (max single)     single  FA 7F7FFFFF
0.1                           double  FB 3FB999999999999A
1.1                           double  FB 3FF199999999999A
+Inf / -Inf                   half    F9 7C00 / F9 FC00
NaN  (canonical)              half    F9 7E00
```

**Rejected: fixed-width double.** Simpler to port, but it contradicts taut's own
`§4.2.1` claim, makes float the lone exception to the shortest-form rule ints
follow, and bloats every float ~3×. Implementation simplicity is not a design input
(see [TautDecisions.md](TautDecisions.md)).

## 4. The codec / backend surface

**9 hand-rolled CBOR codecs** gain a byte-identical float arm:

> `wire/cbor.py` (oracle) · `gen/runtime/{cbor.rs, cbor.hpp, cbor.swift, cbor.go,
> cbor.kt, cbor.js, Cbor.java}` · `trial/ts/src/cbor.ts`

The shared crux is a **`narrow16` / `narrow32` round-trip helper**: most targets
have no native half (Go/Java/JS/Kotlin/C++/Rust-stable), so each ports the same
round-to-nearest-even narrowing (subnormal + overflow→Inf handling) plus the
trivial widen-back. The Python reference is the authoritative implementation; the
**conformance corpus is the real contract** (§5, Phase 1.5).

Two value-model idioms — the edit differs:
- **Enum-style** (Rust, Swift, Kotlin, TS): add a `Float(f64)` **variant** + accessor.
- **Struct/class-style** (Go, Java): bool lives in the int slot, so add a **new
  field** (`F float64` / `double d`) + kind constant + constructor.

## 5. Plan — reference, then 8-way fan-out

Phase 1 builds Python as the fully-tested **oracle** and lands **every shared
file**, so Phase 2 is 8 agents on **disjoint** files — embarrassingly parallel.
LOC budgets aspirational (< 500/step).

### Phase 1 — Python reference + all shared surface  *(milestone: the fork gate)* — ✅ DONE 2026-06-23
Single-threaded. On completion, Python encodes/decodes shortest-form float,
exhaustively green, and the conformance corpus + all shared files are committed.
- **1.1** IR core: `FLOAT = Scalar("float")` (`ir/dsl.py`); add `"float"` to the
  scalar allowlist in `ir/validate.py` (**leave the key allowlist**); float-coerce
  the scalar branch in `wire/codec.py` (rule E); doc the kind in `ir/model.py`. *(~80 LOC)*
- **1.2** `wire/cbor.py`: shortest-form encode (`narrow16`/`narrow32` + width
  select + NaN canonical, rules A–C) and width-lenient decode (rule D). Pin the
  **exhaustive edge-case vectors** in `test_cbor.py` **and invert** the
  `cbor.dumps(1.5)`-rejects assertion. *(~180 LOC)* — critical path; produces the oracle bytes.
- **1.3** `wire/jsoncodec.py` float arm: finite → JSON number; `NaN/±Inf` →
  `"NaN"/"Infinity"/"-Infinity"` (proto3 JSON); reverse on decode; tests. *(~100 LOC)*
- **1.4** Shared codegen surface: add `"float"` to **all 9** `scaffold.py`
  `_<lang>_ty` maps (incl. `_py_ty`, `_ts_ty`) so Phase-2 agents never touch
  `scaffold.py`. *(~30 LOC)*
- **1.5** Conformance artifact: emit/commit `corpus/float_vectors.json` — a
  **parse-free** oracle of `{f64: "<16 hex bits>", cbor: "<hex>"}` rows covering
  every edge case (each width, ±0, ±Inf, canonical NaN, max-half/single, subnormals,
  near-miss values that must *not* shrink). Every Phase-2 codec tests against this:
  build the double from the bit pattern, encode → assert `cbor`; decode `cbor` →
  assert bits. Wired into `run_tests.py` regen with a lockstep gate
  (`corpus/float_build.py` → `corpus/float_vectors.json`, 22 rows). *(~150 LOC, mostly data)*
  *(The float-bearing message in the **shared griplab golden** is deferred to Phase 3.1
  — its regen emits the Rust/C++ corpora, which can't encode float until Phase 2 lands.)*

  *Edge cases 1.2/1.5 must cover:* half/single/double selection boundaries, the
  round-trip near-misses (e.g. a value exact in single but not half), −0 vs +0,
  ±Inf, canonical NaN, max-half `65504`, max-single, smallest half/double
  subnormals, and width-lenient decode (a `FB`-encoded `1.0` still decodes to `1.0`).

### Phase 2 — language fan-out  *(milestone: all 9 codecs byte-match the oracle)*
**8 agents, one per language, each in its own git worktree.** Each edits ONLY its
three disjoint files and verifies against `corpus/float_vectors.json`:
`gen/runtime/cbor.<lang>` (port encode/decode + `narrow16`/`narrow32`) ·
`gen/<lang>.py` (type / encode / decode dicts) · `tests/test_<lang>.py` (float case).
- **2.1** Rust · **2.2** C++ · **2.3** Swift · **2.4** Go · **2.5** Kotlin ·
  **2.6** JavaScript · **2.7** Java · **2.8** TypeScript (`cbor.ts` + `codec.ts`).
  *(~150–300 LOC each; Go/Java also add the struct field + kind constant per §4.)*

By construction there is **zero shared-file contention** (Phase 1 pre-landed IR
core, the `scaffold.py` maps, and the corpus). Merge each worktree on green.

### Phase 3 — convergence & gate  *(milestone: float byte-exactness gated in-repo)*
- **3.1** Float in the shared golden: add a float field to a griplab/glade corpus
  message; regen `*.golden.json` + the Rust/C++ corpora (now that every target
  encodes float). *(~120 LOC, mostly data)* — depends on 2.x.
- **3.2** Cross-language byte-exact harness: drive `corpus/float_vectors.json`
  through every language's codec so float drift in the 6 out-of-band langs (§2) is
  caught **in-repo**, not just in CI. *(~300 LOC)* — depends on 2.x.
- **3.3** Docs + ratify: the `wire/cbor.py` "No floats" docstring is updated (done in
  Phase 1); sweep `README`; record D0 in `TautDecisions.md`. *(~60 LOC)*

## 6. Edit-site appendix (cold-pickup map)

- **IR core** — `ir/dsl.py:30-33` (scalars) · `ir/model.py:19,39` (docs) ·
  `ir/validate.py:22` (scalar allowlist; **not** `:33`, the key allowlist) ·
  `wire/codec.py:42` (coerce).
- **Python wire** — `wire/cbor.py:49-83` (encode), `:142-149` (decode), `:14`
  (docstring) · `test_cbor.py:6-14, 32-35` · `wire/jsoncodec.py:36-41, 72-77`.
- **Runtimes** — `gen/runtime/cbor.rs` (enum `:8`, enc `:80`, dec `:191`) ·
  `Cbor.java` (field/kind `:12-30`, enc `:54`, dec `:94`) · `cbor.go`
  (kind/field `:10-43`, enc `:91`, dec `:200`) · `cbor.hpp` (`:146`) · `cbor.swift`
  · `cbor.kt` · `cbor.js` · `trial/ts/src/cbor.ts`.
- **Codegen** — `gen/{rust,cpp,go,java,js,kotlin,swift}.py` (type / enc / dec dicts;
  kotlin & swift also `_default`) · `gen/scaffold.py` stub maps (`_py_ty:57`,
  `_ts_ty:140`, `_rs_ty:221`, `_cpp_ty:281`, `_swift_ty:332`, `_go_ty:377`,
  `_kt_ty:421`, `_java_ty:491`).

## 7. Risks

1. **`narrow16` agreement** — the half-precision round-to-nearest-even narrowing is
   the riskiest shared code; it must be byte-identical across ~7 hand-rolled codecs.
   The conformance corpus (incl. subnormal/boundary rows) is the gate that catches drift.
2. **NaN canonicalisation (rule B)** — verify `F9 7E00` first in every codec.
3. **Inverted guard test** — `test_cbor.py`'s `1.5`-rejects case *changes meaning*;
   update it, don't just append.
4. **scaffold.py duplication** — each compiled lang has *two* scalar maps (codec in
   `gen/<lang>.py`, stubs in `scaffold.py`); Phase 1.4 lands the stub side so agents
   only touch the codec side.
