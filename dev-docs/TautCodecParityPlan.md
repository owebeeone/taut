# taut Codec — Cross-Language Parity Plan

> **Status: PLAN — rev5 (2026-07-07).** Audit (§1) empirical and holds. **rev5 is a scope simplification
> (Gianni's call):** the frozen wire int subset is now **`i64` (`[-2^63, 2^63-1]`)**, not the full CBOR
> `[-2^64, 2^64-1]`. That deletes the `i128`/`BigInteger` carrier churn in native-width targets and collapses
> Phase 4 to "fail-closed decode + an `i64` range check." **TS/JS remain the one exactness exception:** full
> codec parity over `i64` requires `bigint`, because `number` is not faithful above `2^53`. The Rust
> fail-closed path is being reverted `i128`→`i64` now (separate agent). **fail-closed decode is the real
> parity property; wide-int churn razel doesn't need is gone.** LOC = floors. Log: §7.
>
> **rev6 (2026-07-07): D1 + D2 RATIFIED (Gianni: "go ahead with the recommendations") — execution started.**
> D1 = fail-closed default as (B), opt-out `--legacy-codec` sunsets per the two-minor rule (flip @ v0.8.0 →
> delete @ v0.10.0; literals confirmed in `CodecContract.md` at the flip release). D2 = strict-canonical
> decode (`NonCanonicalInt` / `NegativeMapKey` / `DuplicateMapKey` unconditional). Phase 0 (the RED gate)
> is building; Phase 1 follows.
>
> **rev7 (2026-07-10): D2 + D1 LANDED for Wave-1.** D2 — `NonCanonicalInt` (non-minimal int arg) and
> `NegativeMapKey` (raw map key < 0) are now rejected in all four Wave-1 codecs (rust `cbor_fail_closed.rs`,
> python `wire/cbor.py`, ts `cbor.ts`, js `cbor.js`); `tautc parity` shows rust/python/typescript/js
> **gated + GREEN** and the Wave-1 allowlist is emptied (only Wave-2 remains). D1 — `tautc gen` / `emit()`
> emit the fail-closed codec **by default**; `--legacy-codec` is the deprecated byte-for-byte opt-out (warns +
> banner, sunset v0.10.0), `--fail-closed` is a redundant no-op alias, and the flag is a no-op for non-rust
> targets. `CodecContract.md` not yet created — sunset literals recorded in the CLI help + `RustFailClosed.md`.
> **Follow-ups (out of scope, separate pins):** re-vendor `taut-shape-rs/…/cbor.rs` (drifted at rev `70e17b7`,
> pre-`DuplicateMapKey`); retarget `glade/wire-rs` onto the fail-closed runtime (no documented regen command;
> its generated codec + `lib.rs` tests assume the panicking runtime).

## 0. North star + scope + decisions to ratify

**North star.** taut's wire codec is **ONE contract**, identical in every language taut emits a codec for:
1. **`i64` integers** — the frozen subset `[-2^63, 2^63-1]` round-trips value-for-value; a native value or a
   received CBOR int **outside** it is a **typed error** (encode *and* decode), never a silent wrap. (`i64`
   is chosen because razel — and, pending confirmation, gwz/glade — need nothing wider; CBOR *can* carry the
   u64 top half, so the decoder must *reject* it, not carry it. If a real need for wider/unsigned appears,
   add a distinct type later — §6, and the `u64` note below.)
2. **Fail-closed decode** — every malformed/hostile input yields a *typed, discriminable* error and never
   panics, throws-untyped, or silently fails open. **This is the property razel actually needs** (untrusted
   socket bytes); it drove the whole plan.

…**enforced by a leading cross-language conformance corpus** (Phase 0) that goes RED when a *gated* target drifts.

**Scope — codec ≠ shape.** All **nine** codec targets (`_LANGS`: rust, python, typescript, js, cpp, swift,
go, kotlin, java) are in scope for codec parity. The rs/py/ts-only thing is the higher **delivery-*shape***
layer (`taut-shape-*`) — a separate concern this plan sits beneath (§6). Sequenced: **Wave 1 = rs/py/ts(+js)**
(live boundaries — razel socket, gryth) Phases 1-3; **Wave 2 = cpp/swift/go/kotlin/java** Phase 4.

**⚖️ Decisions — RATIFIED 2026-07-07 (Gianni: "go ahead with the recommendations"):**
- **D1 — RATIFIED: fail-closed is the default contract**, as **(B) fallible generated API + hardened
  runtime**. Legacy stays behind a deprecated opt-out (`--legacy-codec`) that warns on use. **Sunset rule:**
  the opt-out survives **two minor releases after the flip release** — current release is v0.7.0, so the flip
  lands in **v0.8.0** and the opt-out (+ the legacy runtime template) is **deleted at v0.10.0** (versions
  derived from the ratified rule; `CodecContract.md` records the literal numbers when the flip release is
  cut). Migration: pinned consumers unaffected; regen-in-window migrates or opts out; after v0.10.0,
  regeneration is intentionally breaking.
- **D2 — RATIFIED: strict-canonical decode.** The decoder accepts exactly the bytes the canonical encoder
  could emit: non-minimal integer encodings → `NonCanonicalInt`; negative raw map keys → `NegativeMapKey`;
  (with the already-decided `DuplicateMapKey`). Law: `decode(bytes)` ok ⇒ `encode(decode(bytes)) == bytes`.
  `malformed.vectors.json` includes these rows unconditionally.
- *(D3 from rev4 — the encode surface — is **RESOLVED by the `i64` decision, no ratification needed.** With a
  native `i64` carrier an out-of-subset value is unrepresentable — the type IS the guard — so encode stays
  **byte-identical and infallible**; no fallible `try_encode`, no `EncodeError`. Verified: the Rust revert kept
  `enc()` byte-identical to the default runtime. The only residual encode-side check is in the
  **unbounded-carrier** languages — **Python** (`int`; tighten `_head` from `2^64` to reject `> i64`, Phase 2.1)
  and **TS/js `bigint`** — a bound-check-that-raises at the existing validation point, not a new API. The
  `i128`→`u64` wrap this item guarded against is gone at the type level.)*

**`--fail-closed` timeline:** Wave 1 reaches parity via `wire/*`+runtime; the flag becomes a no-op/removed for
py after Phase 2. Wave 2: each compiled generator gains `fail_closed=True` default in `emit()`.

## 1. Audit verdict (evidence base)

| Language | `i64` int range | Fail-closed decode |
|---|---|---|
| **Rust `--fail-closed`** | ⚠ was widened to `i128` — **being reverted to `i64` + out-of-subset rejection** (this rev) | ✅ typed `DecodeError`, never panics |
| **Rust default** | ✅ `i64` carrier — but **wraps/does-not-reject** out-of-`i64` CBOR ints | ❌ panics |
| **Python** | ✅ unbounded `int` (holds `i64`); `_head` currently allows up to `2^64` — **must tighten to reject > `i64`** | ❌ 2 silent fail-open + untyped elsewhere; non-int key accepted; `--fail-closed` refused |
| **TS / JS** | ⚠ current `f64` `number` corrupts `i64` values above **2^53**; parity requires `bigint` for generated `int` fields (Phase 3.1) | ❌ untyped, fails open (utf-8/wrong-type/missing→`null`/non-int key); `cbor.js` worse (reserved info; no enum validation) |
| **C++ / Swift / Go / Kotlin / Java** | ✅ `long long`/`Int64`/`int64`/`Long`/`long` — native `i64`; but **wrap/no-reject** out-of-subset | ❌ infallible/panicking |

**The good news from the i64 decision:** all non-JS native-width targets avoid `i128`/`BigInteger` churn; the
remaining int work is a **range check** (reject out-of-`i64`) folded into fail-closed. **TS/JS must still move
generated `int` fields to `bigint` to satisfy the same full-`i64` corpus.** **Root cause of the gap is
unchanged:** the gate doesn't lead — no
adversarial/out-of-range vectors, byte-parity replay is Rust-only (`kit.py:91-93`), matrix proves jsoncodec
behaviour not adversarial decode, `glade/wire-rs` runs the unhardened codec. **UNVERIFIED (Phase 0.3):** is
emitted `rust/vectors.rs` compiled or only string-checked.

## 2. The contract

**2a. Integers — exact `i64`.** Carriers: Rust `i64` · Go `int64` · C++ `long long` · Swift
`Int64` · Java `long` · Kotlin `Long` · Python `int` · **TS/JS `bigint` for generated codec `int` fields**.
No 128-bit carrier work outside JS exactness. A native value outside `[-2^63, 2^63-1]` → typed **encode**
error; a received CBOR int outside it (CBOR can carry `[-2^64, 2^64-1]`) → typed **decode** error. Schema
`map<int,V>` keys are ordinary `i64` values (round-trip); `IntOverflow` is the "outside `i64`" tag (raw
structural keys *and* any out-of-subset int).

> **TS/JS exactness decision.** The Phase-0 corpus intentionally includes `2^53`, `i64::MAX`, and `i64::MIN`.
> Therefore TS/JS cannot pass the shared codec gate with `number`. The Wave-1 audit can still document that
> current protocol values are probably ≤ `2^53`, but that is not the codec contract. Phase 3 uses `bigint` for
> generated codec `int` fields and rejects out-of-`i64` `bigint` values on encode/decode.

**2b. Canonical error-tag vocabulary** (Rust-only `DecodeError` → language-neutral taut artifact): `Truncated ·
TrailingBytes · InvalidUtf8 · UnsupportedInfo{info} · UnsupportedMajor{major} · NonIntegerMapKey · IntOverflow
(= outside i64) · DuplicateMapKey · MissingKey{tag} · WrongType{expected} · UnknownEnum{enum, value}` (decode);
`IntOutOfSubset` (encode; real only for unbounded-carrier languages per the D3 resolution). **Per D2-strict
(ratified):** `NonCanonicalInt`, `NegativeMapKey` — unconditional members of the vocabulary.

**2c. Strictness (D2 ratified: strict-canonical).** Fail-closed = reject: duplicate map key →
`DuplicateMapKey`; non-minimal int encodings → `NonCanonicalInt`; negative raw map keys → `NegativeMapKey`.
The decoder accepts exactly what the canonical encoder can emit (`decode` ok ⇒ byte-identical re-encode).

## 3. Phases

### Phase 0 — The leading conformance gate *(foundational)*
New fixture + per-target harness (the kit can't host boundary/failure vectors as-is); vectors are
language-neutral but a target is **gated only once its real replay harness lands** (§0.3).
- **0.1 — Int-range vectors, split by assertion.** Micro-IR `ir/parity_int.taut.py` (one `int`
  field + one `map<int,int>`), Python-authored `…/int.vectors.json`:
  - `round_trip {value}`: `0, -1, 2^53-1, 2^53, i64::MAX, i64::MIN` + a `map<int,int>` entry keyed at
    `i64::MAX`/`i64::MIN` (full-range keys round-trip).
  - `encode_fail {encode_error: IntOutOfSubset}`: native `2^63` (=`i64::MAX+1`), `-2^63-1`, `u64::MAX`.
  - a **raw-CBOR** decode vector (in 0.2, `stage: raw_decode`) with a major-0 value `> i64::MAX` → `IntOverflow`.
  (~150 LOC.)
- **0.2 — Malformed-input vectors, richly typed.** `{ bytes, stage: raw_decode|from_cbor|from_wire, schema,
  expect:{tag, …payload}, why }`; every §2b tag + a nested failure; the D2-strict rows (`NonCanonicalInt`,
  `NegativeMapKey`, `DuplicateMapKey`) are included (D2 ratified). Hex-authored + per-vector `why`.
  `…/malformed.vectors.json`. (~300 LOC.)
- **0.3 — Per-target replay harness, RED-staged + governed.** Wave-1 harnesses run now: Rust
  `rust_vectors_fail_closed` (`try_decode`/`Result`; encode-fail rows are construction/validation checks for
  dynamic carriers, not a new Rust `try_encode`; resolve the UNVERIFIED
  compile question binary), Python pytest importing `wire.codec`, TS/js `node:test`. **Honest Wave-2 gating:** a
  target is gated only when its real harness lands (Phase 4); until then a documented **skip-with-reason**, not
  a fake red — a harnessed-but-allowlisted target must **run + report observed failures**. **Allowlist
  governance:** `corpus/parity/allowlist.json`, entries `{target,phase,owner,reason}`, **CI fails if a
  green target stays listed**. Retarget `glade/wire-rs` to the fail-closed runtime. **CI:** one `tautc parity`
  entrypoint (in `CodecContract.md`); it **supplements, not replaces** `tautc corpus`/`log.v0.json`.

### Phase 1 — Rust to green *(mostly done + the revert)*
- **1.1 —** The `i128`→`i64` revert + out-of-subset encode/decode rejection is landing now (agent). Then
  realize **D1** default (B) + sunset opt-out; repoint `glade/wire-rs`.
- **1.2 —** Green Rust; move inline malformed cases into the shared corpus — keep a thin rustc smoke test.

### Phase 2 — Python to parity *(concentrated: `wire/{cbor,codec}.py`)*
- **2.1 —** Typed Python `DecodeError` + the encode error; fail-closed (missing→`MissingKey`, wrong-type,
  utf-8, non-int/dup key); bounds-check in `cbor.py` before `codec.py`; **tighten `_head` to reject > `i64`**
  (currently allows `2^64`) → `IntOutOfSubset`.
- **2.2 —** Lift the py `--fail-closed` rejection; missing-vs-null; decide the flag's Python meaning.
  *(jsoncodec.py already i64-as-string — no work.)*
- **2.3 —** Green Python.

### Phase 3 — TS/JS to parity *(Wave-1; carrier decision explicit)*
- **3.1 — BigInt carrier for generated codec `int`.** Audit Wave-1 protocol int fields to find downstream
  `number` assumptions, but do not use that audit to weaken the codec contract. Move generated TS/js `int`
  fields and `map<int,...>` keys/values to `bigint` where needed across `scaffold.py:153` TS + `js.py`/`js_api`
  + `cbor.js` `CInt` + jsoncodec `:95`/`:106` both directions + `glade/client-ts` + vendor-sync. Add helpers
  only at explicit app boundaries that intentionally downcast after `Number.isSafeInteger` checks.
- **3.2 — Fail-closed decode (the real TS/JS work):** typed error; reject utf-8 (fatal `TextDecoder`)/wrong-type/
  missing/non-int & dup key; CommonJS reserved-info-28-31 guard + enum validation; reject out-of-`i64` via
  `bigint` comparisons → `IntOverflow`.
- **3.3 —** Green TS+js in harness + matrix.

### Phase 4 — Wave 2: cpp / swift / go / kotlin / java *(now thin — no carrier work)*
The `i64` decision **deletes the carrier ADR** — every Wave-2 target already has a native `i64`. Remaining per target:
fail-closed decode (typed error carrying §2b tags; bounds-checked reads, no panic), the **out-of-`i64` range
rejection** on encode+decode, §2c/D2 strictness, `fail_closed=True` default in `emit()`, and the CI harness.
- **4.0 —** De-risk with a **Go spike** (simplest vendored runtime) to validate the harness pattern.
- **4.1 —** Per-target fail-closed decode + range check + `emit()` default; named CI harness command
  (`go test`, `swift test`, JVM, …). **C++ split:** keep the constexpr corpus for encode goldens, add a small
  **runtime** test binary for malformed replay (constexpr can't host `try_decode`).
- **4.2 —** Green each; remove from the allowlist. Parallelizes in code; CI toolchains are the real cost.

### Phase 5 — Governance
- **5.1 — `CodecContract.md`:** the two invariants (`i64` + fail-closed), the tag table + payloads +
  `IntOutOfSubset`, D2 outcome, corpus paths + `tautc parity`, the resolved **D1 sunset**, the "not parity until
  it passes the corpus" rule, a **live nine-target status list**, and a note that the shape layer's rs/py/ts
  scope is separate.
- **5.2 — gwz migration** per D1 (pinned / regen / sunset).
- **5.3 —** Bump a wire/codec-contract version when 0.1/0.2 land.

## 4. Ordering & parallelism
Phase 0 = barrier. Then Wave 1 (1/2/3) parallelizes; Wave 2's five parallelize in code, gate on CI toolchains,
run after the 4.0 Go spike. Phase 5 closes. Parity-gate-leads.

## 5. What this unblocks
- **razel comms-protocol (socket):** D1-(B) hardened **Rust** codec + fail-closed + the leading gate;
  `RazelV4CommsProtocolLockdown` waits on this. (razel's ints are `i64`/≤2^53 — no wide-int need.)
- **gryth (TS client):** fail-closed **TS/js** with exact `i64` codec values; app code may downcast only at
  explicit safe-int boundaries.
- **gwz / glade:** same contract; **the `i64` subset needs a quick confirm they carry no u64-top-half field**
  (§6) — if one does, that field motivates a future `u64` type, not a global carrier widening.

## 6. Deferred (acknowledged)
- **A `u64` type / values needing the u64 top half or `i128`:** deferred (YAGNI). *If/when needed*, add a
  **distinct `u64` taut type** — it's a **small ask, not a big one**: native carrier in Rust (`u64`), Go
  (`uint64`), C++ (`uint64_t`), Swift (`UInt64`), **Kotlin (`ULong`)**, Python (`int`); **Java** carries it in
  `long` + `Long.*Unsigned` helpers (moderate, *not* `BigInteger`); TS/js `bigint` (the `>2^53` cost, same as
  any large int). **Free on the wire** — CBOR major-0 *is* unsigned-64. So a `u64` type is bounded, per-field,
  and additive; don't add it speculatively.
- **Delivery-*shape* layer** (`taut-shape-*`): separate, higher; today rs/py/ts — not this plan.
- **Forward-compat / ResExt residual paths:** orthogonal; ext tests keep running.
- **Float byte contract** (`corpus/float_vectors.json`): out of scope **but must not regress** — int work must
  not touch float encode paths.

## 7. Change log
**rev5 (i64 simplification — Gianni):** frozen subset `[-2^64,2^64-1]` → **`i64` `[-2^63,2^63-1]`**. Deletes the
`i128`/`BigInteger` carrier churn; the int work becomes an **out-of-`i64` range check** folded into fail-closed.
Phase 4's carrier ADR **removed**. TS/js still require `bigint` for exact full-`i64` codec parity because
`number` corrupts values above `2^53`; the Phase 3 audit now finds downstream safe-int assumptions rather than
deciding the contract. Rust `i128` path being reverted to `i64` (agent). A future **`u64` type** is deferred but
noted as a *small* ask (§6), free on the CBOR wire. fail-closed decode is unchanged — it's the real parity
property razel needs.
**rev4 (round-2 reviews):** schema-map-key≠CBOR-key fix; encode surface (D3); honest Wave-2 gating; strictness
tags; Phase-4 carrier ADR (now moot under rev5); split 0.1 assertions; `--fail-closed` timeline; `js.py`
explicit; allowlist governance; corpus coexistence; named sunset; Go spike; C++ constexpr-vs-runtime.
**rev3:** all nine codec targets in scope (codec≠shape). **rev2:** Review25+55 (encode hole, dup-key, malformed
schema, Phase-0 realizability, gwz migration, TS surface).
