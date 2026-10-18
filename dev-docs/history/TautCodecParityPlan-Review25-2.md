# Review 25-2: taut Codec Cross-Language Parity Plan (rev3)

> **Review 25-2 · 2026-07-07**  
> **Document reviewed:** `TautCodecParityPlan.md` — **rev3** (212 lines)  
> **Prior review:** `TautCodecParityPlan-Review25.md` (against rev1; largely superseded)  
> **Method:** Re-read rev3 end-to-end; re-spot-checked `scaffold.py` (`_LANGS`, `_RUNTIMES`, `fail_closed` guard), `wire/cbor.py`, `gen/runtime/cbor_fail_closed.rs`, `gen/{cpp,go,swift,java,kotlin,js}.py`, and `kit.py`.

## Executive summary

**rev3 is a material upgrade.** It closes almost every gap from Review25, expands scope honestly to all nine codec targets (the rev2/rev3 correction is right), adds encode-side `IntOutOfSubset`, duplicate-key strictness, a real malformed-vector schema with `stage` + payload, RED-staging via per-target allowlist, and names Wave 1 vs Wave 2 without pretending five compiled targets don't exist.

**Recommendation:** Proceed with Phase 0. Two items should be **ratified alongside §0** before vectors are frozen: **§2c strictness** (duplicate keys is pinned; non-minimal ints and negative map keys are still "confirm") and **the sunset release identifier** (named version, not "a release version"). Wave 2 (Phase 4) is correctly sequenced but **under-specified on harness mechanics** — flag that before treating "nine targets RED day one" as low-cost.

---

## What rev3 fixed (vs Review25)

| Review25 gap | rev3 response | Adequate? |
|---|---|---|
| Migration window + (A) vs (B) default | §0: sunset + deprecation warning; explicit **(B)**; gwz pinned/regen rule | ✅ — still needs a **named** sunset version |
| Micro-IR, `2^53` boundary, map-key overflow | Phase 0.1: `parity_int.taut.py`, full value list, `i64::MAX+1` map key | ✅ |
| Rich error payload schema | Phase 0.2: `stage` + `schema` + `expect{tag,…}` + `why` | ✅ |
| Hardened Rust harness, CI command, UNVERIFIED | Phase 0.3: `rust_vectors_fail_closed`, `taut parity`, binary resolution | ✅ |
| jsoncodec.py no work | Phase 2.2 parenthetical | ✅ |
| bigint/jsoncodec/vendor blast radius | Phase 3.1 + 3.4 checklist + vendor-sync | ✅ |
| Keep rustc smoke test | Phase 1.2 | ✅ |
| Out-of-scope languages | **Rev3 reverses this** — all nine in scope, Wave 2 | ✅ (see Wave 2 caveats below) |
| LOC as floors | Header + Phase 0.3 | ✅ |
| Contract version bump | Phase 5.3 | ✅ |
| Python truncation wording | §1: "untyped / wrong exception class" | ✅ |
| Rust encode wrap hole | §1 audit + Phase 1.1 + `IntOutOfSubset` | ✅ (verified in tree) |

Review25's overall "approve for execution" verdict still holds; rev3 is the document to execute against.

---

## Audit validation (rev3-specific claims)

| rev3 claim | Verified? | Notes |
|---|---|---|
| Nine codec targets in `_LANGS` | ✅ | `scaffold.py:549-558` — rust, python, typescript, js, cpp, swift, go, kotlin, java |
| Rust `--fail-closed` encode `i128 as u64` wraps | ✅ | `cbor_fail_closed.rs:391-396` — `head(out, 0, *n as u64)` with no subset check |
| Python `_head` rejects out-of-subset on encode | ✅ | `wire/cbor.py:42-44` — `n < 2^64` guard + `ValueError` |
| C++ `long long`, Go `int64`, Swift `Int64`, Java `long`, Kotlin `Long` | ✅ | `cpp.py:59`, `go.py:21`, `swift.py:28`, `java.py:20`, `kotlin.py:31` |
| py/ts duplicate map key last-wins | ✅ | `cbor.py:170` — `result[key] = val` overwrites |
| rust duplicate map key first-wins at read | ✅ | `cbor_fail_closed.rs:528` pushes all pairs; `get()` at `:125-128` returns **first** match |
| `kit.py` can't host boundary/failure vectors | ✅ | `build_corpus` only encodes valid natives → `{message,cbor}`; no failure cases |
| Python has no vendored runtime in `_RUNTIMES` | ✅ | Interpreter lives in `wire/{cbor,codec}.py` — Wave 1 harness imports directly (correct) |

**Not yet verifiable (pre-Phase 0):** whether `parity_int.taut.py` with `map<int,int>` compiles through the DSL loader — `MapOf` exists in `ir/model.py:38-40` and generators handle it; no blocker found, but the micro-IR file doesn't exist yet.

---

## Strengths of rev3 (beyond Review25)

1. **Codec vs shape separation (§0, §6).** The rev3 correction is the right abstraction: nine generated codecs, three reference *shape* implementations. This prevents future "we only ship rs/py/ts" regressions in planning.

2. **Bidirectional integer contract (§2a).** Adding `IntOutOfSubset` on **encode** closes a real hole — hardened Rust today can still emit wrong bytes for out-of-range `i128` values. Pairing decode full-range with encode rejection is the correct symmetric contract.

3. **§2c duplicate-map-key policy.** Same bytes, different semantics (py/ts last-wins vs rust first-wins) is exactly the kind of silent cross-language divergence a leading gate should catch. Pinning `DuplicateMapKey` is high value.

4. **Phase 0 realizability admission.** Acknowledging the kit can't host this "as-is" and specifying a **new fixture** (`int.vectors.json`, `malformed.vectors.json`) avoids bolting failure cases onto `golden.json`.

5. **RED-staging allowlist.** Practical CI hygiene: land the gate RED without blocking mainline, remove targets as they green. Better than pretending Wave 2 is green on day one.

6. **`stage` in malformed vectors.** Splitting `raw_decode | from_cbor | from_wire` is necessary — `MissingKey` and `UnknownEnum` aren't properties of bare CBOR bytes alone.

---

## New concerns (not adequately addressed in rev3)

### 1. §2c still has an open fork — ratify before 0.2 freezes

`DuplicateMapKey` is decided; **non-minimal int encodings** and **negative map keys** remain "Recommended (confirm)." Each needs Phase 0 vectors if enforced. Leaving them ambiguous means implementers may author conflicting `malformed.vectors.json` rows mid-Phase 0.

**Suggestion:** Add a §2c ratification bullet parallel to §0: either **strict canonical subset** (reject non-minimal ints + negative keys — recommended, matches deterministic encoder) or **permissive decode** (accept any CBOR int encoding in range). Don't ship vectors for the permissive path and strict policy simultaneously.

---

### 2. Phase 0.1 encode-fail vectors need an explicit harness assertion path

0.1 lists encode-fail cases (`2^64`, `-2^64-1` → `IntOutOfSubset`) alongside round-trip values. Phase 0.3 says replay asserts "exact value" for 0.1 — that covers decode round-trips, not **encode must fail**.

**Suggestion:** Split 0.1 schema into `round_trip` rows and `encode_fail` rows (or a `expect` discriminant: `{ "value": … }` vs `{ "encode_error": "IntOutOfSubset" }`). Without this, Phase 1.1's encode fix has no shared gate.

---

### 3. `--fail-closed` propagation timeline is unclear post-Phase 1

Today `scaffold.py:609-616` refuses `--fail-closed` for non-Rust. Phase 1 flips Rust to default **(B)**. Phase 2 lifts the Python rejection. Phases 3–4 don't say when **cpp/swift/go/kotlin/java** get `fail_closed` threading in `emit()` — or whether default **(B)** applies to all nine once Phase 4 completes while Wave 1 langs are already green under interpreter/runtime fixes without codegen changes.

**Suggestion:** One sentence per wave:
- **Wave 1:** Python/TS/JS parity via `wire/*` + runtime templates; `--fail-closed` becomes no-op or removed for py after Phase 2.
- **Wave 2:** Each compiled generator gains `fail_closed=True` default in `emit()` mirroring Rust Phase 1 — not only runtime `try_decode`.

Otherwise Phase 1's "default (B)" reads as Rust-only while the north star says "every language taut emits a codec for."

---

### 4. Wave 2 harness stubs — cost and shape are underspecified

Phase 0.3 says cpp/swift/go/kotlin/java get a harness stub on the RED allowlist. Phase 4 greens them. What's missing:

| Target | Runtime | Harness reality |
|---|---|---|
| **C++** | `cbor.hpp` + **constexpr** `from_cbor` (`cpp.py:115-133`) | Malformed-byte replay needs a **runtime** fallible decode path — today's C++ story is compile-time `static_assert` corpus, not `try_decode` |
| **Go** | `cbor.go` vendored | Needs `go test` subprocess + module wiring in CI |
| **Java/Kotlin** | `Cbor.java` / `cbor.kt` | JVM compile + test; slower CI |
| **Swift** | `cbor.swift` | `swift test` or `xcrun` availability in CI |

**Suggestion:** Phase 0.3 stub = **allowlist entry + skipped test with reason**, not an empty pass. Phase 4.1 should list **per-target harness command** (like `_TOOLS` in `matrix/driver.py`). C++ may need a deliberate split: keep constexpr corpus for encode golden bytes, add a small runtime test binary for malformed replay.

---

### 5. Carrier choices (§2a) — platform and API caveats

rev3's carrier table is directionally right but glosses over integration pain:

- **Swift `Int128`:** Available only on newer OS versions / Swift versions. Phase 4.1 should require a **availability guard** or a big-int fallback, or Swift becomes the long pole of Wave 2.
- **Go `math/big.Int`:** Correct for range, but every int field becomes heap-allocated and non-comparable — affects generated struct equality and hot paths. A fixed **signed 128-bit struct** (two `uint64`) may be preferable for generated codecs; call this an explicit Phase 4.1 decision.
- **C++ `__int128`:** GCC/Clang extension, not portable MSVC. If taut targets MSVC consumers, `std::array<uint64_t,2>` or a small int128 type may be required.

**Suggestion:** Phase 4.1 deliverable = a short **carrier ADR per language** (one paragraph each), not just a pick-from-menu list.

---

### 6. `js` vs `typescript` — Phase 3 should name `js.py` explicitly

Wave 1 lists "ts (+ js)". Phase 3 steps cite `typescript/cbor.ts` and `cbor.js` but not **`js.py` codegen** (field types, `CInt` storage). `js.py:5` still documents "JS numbers (safe to 2^53)." After `bigint`, generated JS classes need native `bigint` fields and `CInt` must carry `bigint` — parallel to `scaffold.py:153` for TS.

**Suggestion:** Phase 3.1 bullet: update **`js.py` + `js_api`** field types and `cbor.js` `CInt` representation, not only the TS scaffold path.

---

### 7. RED allowlist governance — prevent rot

The allowlist pattern is good; rev3 doesn't say how to keep it honest.

**Suggestion:**
- Allowlist lives in one file (e.g. `parity/allowlist.json`) checked into the repo.
- CI **fails if a green target remains allowlisted** (inverse check once Phase N completes).
- Each entry: `{ "target": "go", "phase": "4", "owner": "…" }` — no anonymous xfails.

---

### 8. Coexistence with existing `tautc corpus`

Phase 0 builds a **new** parity fixture; `tautc corpus` + `kit.build_corpus` + `log.v0.json` continue for shape/message golden bytes. rev3 doesn't state how these relate.

**Suggestion:** One line in Phase 5.1 or Phase 0: **parity corpus supplements, does not replace** message golden corpora. `taut parity` runs adversarial + int-extreme vectors; `tautc corpus` / `log.v0.json` remain byte-parity for real IR messages. Avoid two commands asserting the same thing differently.

---

### 9. Sunset version is still unnamed

§0 says "a release version after which regeneration is intentionally breaking" but doesn't anchor it (e.g. `taut v0.5.0` or "two minor releases after Phase 1 merges"). Without a name, gwz and razel can't plan.

**Suggestion:** Pick a placeholder in the plan (`TBD at §0 ratification`) and require `CodecContract.md` to state the resolved version before Phase 1.1 merges.

---

## Phase-by-phase notes (delta only)

### Phase 0
- **Strong.** Ready to implement.
- Add encode-fail harness shape (concern #2).
- Ratify §2c fork (concern #1).
- Wave-2 stubs: document skip semantics (concern #4).

### Phase 1
- **Strong.** `IntOutOfSubset` + encode fix is the right first green after gate lands.
- Clarify fail-closed default scope for non-Rust codegen (concern #3).

### Phase 2–3
- **Adequate** — rev3 incorporated Review25 TS/jsoncodec scope.
- Add explicit `js.py` (concern #6).

### Phase 4 (Wave 2)
- **Directionally right, mechanically thin.** The ×N cost is acknowledged as a forcing function; the plan still understates C++ runtime-vs-constexpr and CI harness work (concern #4–5).
- Recommend Phase 4.0 (optional): spike one Wave-2 target (Go is the simplest vendored-runtime story) to validate harness pattern before parallelizing five.

### Phase 5
- **Strong** governance close. Status list of nine greens is the right anti-over-claim device.

---

## Items correctly deferred (§6)

No pushback on shape-layer separation, ResExt orthogonality, or encode validation beyond `IntOutOfSubset`. One addition: **float byte contract** (`corpus/float_vectors.json` referenced in `cbor.py:52-53`) should be named as **out of scope but must not regress** when int carriers widen — int work must not touch float encode paths.

---

## Recommended amendments (rev3 → rev4)

1. **Ratify §2c** alongside §0 (strict vs permissive for non-minimal ints / negative map keys).
2. **Split 0.1 schema** for round-trip vs `encode_fail` assertions.
3. **Name sunset version** placeholder in §0.
4. **Timeline for `--fail-closed` / default (B)** across all nine targets in `emit()`.
5. **Phase 4.1:** per-language carrier ADR + per-target CI harness command; C++ runtime fallible decode called out explicitly.
6. **Phase 3.1:** `js.py` / JS API types alongside TS.
7. **Allowlist governance** rules in Phase 0.3.
8. **Corpus coexistence** one-liner (`taut parity` vs `tautc corpus`).

---

## Verdict (rev3)

| Area | Rating | vs Review25 |
|---|---|---|
| Problem diagnosis | **Strong** | — |
| Scope honesty (9 codecs) | **Strong** | ↑ from "rs/py/ts only" |
| Phase 0 specification | **Strong** | ↑ (micro-IR, schema, allowlist) |
| §0 / migration framing | **Strong** | ↑ (sunset, (B), gwz rule) |
| Integer contract (decode + encode) | **Strong** | ↑ (`IntOutOfSubset`) |
| Wave 2 / Phase 4 mechanics | **Adequate** | new gap — harness + C++ runtime |
| Open decisions | **Needs ratification** | §2c + sunset version |
| LOC estimates | **Honest floors** | ↑ |

**Overall:** **Approve rev3 for execution.** Phase 0 remains decision-independent. Resolve §2c and encode-fail harness shape before committing `malformed.vectors.json` and `int.vectors.json`. Do not underestimate Phase 4 — Wave 2 is parallelizable in *code*, not necessarily in *CI infra*; a single Go spike de-risks the pattern.

---

*End of Review 25-2.*
