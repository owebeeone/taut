# Review: taut Codec Cross-Language Parity Plan

> **Review 25 · 2026-07-07**  
> **Document reviewed:** `TautCodecParityPlan.md` (status: PLAN, same date)  
> **Method:** Read the plan against `RustFailClosed.md`, the conformance kit (`corpus/kit.py`, `cli.py`), runtime sources (`wire/cbor.py`, `wire/codec.py`, `gen/runtime/typescript/cbor.ts`, `gen/runtime/cbor.js`), existing tests (`test_rust.py`, `test_corpus_kit.py`, `test_ts.py`), `taut-shape/corpus/log.v0.json`, `taut-shape/matrix/driver.py`, and `glade/wire-rs/src/cbor.rs`.

## Executive summary

The plan is **sound, well-evidenced, and actionable**. The audit in §1 matches what is in the tree today: the conformance gate does not lead, integer extremes are untested cross-language, and fail-closed behaviour exists only on the Rust opt-in path. The phased “RED gate first, then parallel language fixes” ordering is the right discipline.

**Recommendation:** Proceed with Phase 0 immediately (it is correctly decision-independent). Ratify §0 before Phase 1 lands in production defaults. Treat the LOC estimates as lower bounds — especially Phase 0.3 and Phase 3 — and close the gaps called out below before calling the work “done.”

---

## Audit validation (spot-check)

| Plan claim | Verified? | Notes |
|---|---|---|
| `_HARNESS` is Rust-only | ✅ | `kit.py:91-93`; `cli.py:78-80` prints “no parity harness … yet” for other langs |
| `synth.py` ints capped at small values | ✅ | `_INTS = (42, -7, 300, 0)` — nothing near `2^53` |
| `log.v0.json` has no 8-byte int encodings | ✅ | `0` occurrences of `1b` + 16 hex digits in the committed corpus |
| Python fail-open on missing required | ✅ | `codec.py:87-88` — `cv.get(f.tag)` → `None` when absent |
| Python fail-open on wrong scalar type | ✅ | `codec.py:68-69` — passthrough `return cv` |
| TS `Number(bn)` on 64-bit path | ✅ | `gen/runtime/typescript/cbor.ts:220-223`; vendored `taut-shape-ts/.../cbor.ts:225-228` |
| CommonJS `readArg` mishandles info 28–31 | ✅ | `cbor.js:158-163` — no `info === 27` guard; falls through to 8-byte read |
| `--fail-closed` refused for non-Rust | ✅ | `scaffold.py:609-616` |
| `glade/wire-rs` uses default `i64` runtime | ✅ | `glade/wire-rs/src/cbor.rs:8-9` — `Cbor::Int(i64)`, panicking accessors |
| Rust fail-closed inline test is Rust-only | ✅ | `test_rust.py:490-583` — rustc subprocess, not in shared corpus |
| Kit Rust harness is string-checked only | ✅ | `test_corpus_kit.py:45-52` — asserts emitted source shape, never compiles `vectors.rs` |

**Minor audit wording nit:** §1 describes Python truncation as “misdiagnosed as trailing bytes.” In practice truncated inputs today surface as `IndexError` / bare `ValueError`, not consistently as `TrailingBytes`. The fix direction (typed `Truncated`) is right; the diagnosis label in the audit table could be tightened to “untyped / wrong exception class.”

---

## Strengths

1. **Correct root-cause framing.** The problem is not “languages are buggy” but “the gate proves byte replay in a narrow int band and behaviour over jsoncodec, not adversarial decode parity.” That explains why TS/JS and Python gaps survived green CI.

2. **Phase 0 as a barrier.** Building the conformance corpus and replay harness *before* fixes is the highest-leverage choice. It prevents a repeat of per-language tests that assume parity.

3. **Promotion of `DecodeError` to a language-neutral contract.** §2b is essential. Without a shared tag vocabulary, cross-language malformed-input tests devolve into string-matching on error messages.

4. **Scoped language surface.** Restricting Phases 1–3 to rs/py/ts matches what taut-shape, razel, gryth, and glade actually run today. Avoiding a simultaneous C++/Swift/Go/Kotlin/Java sweep keeps the plan shippable.

5. **gwz decoupling.** Phase 4.2 correctly treats gwz as a consumer migration on its own schedule, with no wire-format change — consistent with `RustFailClosed.md`.

6. **Downstream linkage.** §5 ties the plan to razel socket hardening and gryth `bigint` needs without over-scoping the codec work.

---

## Concerns and gaps

### §0 — Default vs opt-in (must ratify)

The recommendation (fail-closed + full range as **default**, legacy behind deprecated opt-out) is the right long-term posture for “ONE contract.” Two additions:

- **Define the migration window explicitly.** How long does the deprecated opt-out survive? What emits a warning? Without a sunset, §0’s “indefinite opt-in” problem reappears under a different name.
- **Clarify generator vs runtime default.** Today `--fail-closed` changes both generated APIs (`Result<_, DecodeError>`, `i128` fields) *and* the vendored `cbor.rs`. Phase 1.1 should state whether “default” means:
  - (A) fail-closed **runtime + infallible generated API** with widened carriers only, or
  - (B) fail-closed **runtime + fallible generated API** everywhere.

  razel needs (B). gwz today uses (neither). The plan should name which default is being flipped so Phase 1 doesn’t accidentally break gwz regen semantics.

**Alternative path (keep opt-in):** The plan fairly states this means “parity is achievable, not enforced.” If stakeholders pick this, Phase 0 should still go RED on all languages using an explicit `--hardened` replay mode — otherwise the gate lies about what production emits.

---

### Phase 0 — Conformance gate (foundational)

**0.1 Int-extreme vectors**

- Good vector set (`0, -1, 2^53+1, 2^63, u64::MAX, -2^64`). Consider also adding **`2^53` exactly** (boundary where `number` is still exact) and **`2^53-1`** to catch off-by-one regressions.
- Specify **where** vectors live: dedicated micro-IR (e.g. `parity_int.taut.py` with one message + one `int` field) vs extending `synth.py`. A micro-IR keeps int-extreme tests independent of message-shape churn in razel/griplab corpora.
- **Map keys vs field values:** Rust keeps map keys as `i64` with `IntOverflow` beyond that. At least one vector should assert that a **map key** at `i64::MAX+1` yields `IntOverflow`, not only message field values.

**0.2 Malformed-input schema**

- Tags with payloads (`UnsupportedInfo(u8)`, `MissingKey(i64)`, `WrongType { expected }`, `UnknownEnum { … }`) need a schema richer than bare `expect_error: <tag>`. Suggest:

  ```json
  { "bytes": "…", "expect": { "tag": "MissingKey", "key": 2 } }
  ```

  Pin this in Phase 0.2 so harnesses don’t fork ad hoc string formats.

- **Authoring authority:** Plan says Python-reference-authored bytes for 0.1 (good). Malformed vectors should likewise be **hex-authored with a comment per vector** explaining the failure class — not synthesized by mutating golden corpus entries — so regressions are reviewable.

- **Coverage gap:** Include at least one vector for **nested** failure (e.g. truncated string inside a map) vs top-level truncation, if the runtime paths differ.

**0.3 Multi-language replay harness**

- **`rust_vectors` today uses the panicking path.** Generated harness calls `decode` / `from_cbor` without `try_decode` / `Result` (`kit.py:49`, `kit.py:81`). Phase 0.3 must extend `rust_vectors` (or add `rust_vectors_fail_closed`) so the parity gate exercises the hardened runtime — not the default `i64`/panic codec. This is easy to miss because `test_rust_fail_closed_runtime_decode_is_fail_closed` already exists elsewhere.

- **Resolve UNVERIFIED decisively:** Either wire `vectors.rs` into a `#[test]` that `cargo test` runs in CI, or delete the illusion of compile-time parity and document that only `tautc corpus --check` string-diff runs today. The plan’s Phase 0 bullet is right; make the outcome binary.

- **`glade/wire-rs`:** Confirmed on default runtime. Say whether glade switches to vendored fail-closed `cbor.rs` in Phase 0.3 or Phase 1.1 — either is fine, but the gate should not stay on `i64`/panic while claiming hardened parity.

- **CI entrypoint:** Name the command developers run (`pytest taut/src/tests/test_parity.py`, `tautc corpus --check`, new `taut parity` subcommand, etc.). “Single parity gate” is the right deliverable; the plan should pin how it is invoked in CI and locally.

- **Python / TS harness pattern:** `test_ts.py` hand-writes a `node:test` file — workable. For Python, prefer a pytest module that imports `wire.codec` directly (no subprocess) for fast feedback, mirroring how `test_rust.py` uses rustc only when necessary.

**LOC note:** ~400 LOC for 0.3 across three languages + CI wiring is optimistic if it includes payload error matching, glade retargeting, and a new test command.

---

### Phase 1 — Rust

- **Do not delete `test_rust.py:490-583` without replacement.** Those tests are the only rustc-driven proof that malformed bytes never panic. Moving cases into the shared corpus is correct; keep a thin smoke test that compiles emitted `--fail-closed` output if the shared harness does not yet `cargo test` vendored consumers.

- **Default flip vs explicit hardened binary:** If §0 picks “gate runs hardened explicitly” (opt-in survives), document that razel/taut-shape-rs must pass a flag to the gate — and that default `tautc gen` output staying soft is intentional.

---

### Phase 2 — Python

- **Truncation:** `_read_arg` / `_decode` use unchecked indexing (`cbor.py:129+`). Fail-closed work belongs in `cbor.py` bounds checks *before* `codec.py` tag logic — align with Rust `try_decode`.

- **Missing vs explicit null (Step 2.2):** Required today: distinguish `key absent` → `MissingKey` vs `key present, value null` → `null` for optional fields. The plan mentions this; ensure vectors cover both.

- **`--fail-closed` for Python (Step 2.2):** After Python honours the contract, decide whether `--fail-closed` becomes a no-op synonym, applies to codegen (if Python ever gets generated codecs), or gates strict vs legacy interpreter mode during migration. Avoid a flag that means different things per language.

- **jsoncodec.py:** Already uses `str`/`int` for i64 — no change needed for full-range ints. Call this out so implementers don’t duplicate work in Phase 2.

---

### Phase 3 — TS/JS

- **`bigint` blast radius is larger than noted.** Beyond gryth:
  - `scaffold.py:153` — all generated `int` fields become `bigint`
  - `taut-shape-ts`, `glade/client-ts`, and any hand-written arithmetic on int fields
  - `jsoncodec.ts:95-106` — `Number(s)` / `Number(jv)` must become `BigInt` (strings already work for encode via `String(value)` once `value` is `bigint`)
  - Interop matrix transcripts that compare JSON may need canonicalisation updates if ints stringify differently

- **Two TS trees:** Plan correctly lists `gen/runtime/typescript/*` and vendored `taut-shape-ts`. Add an explicit **regen/vendor step** so they cannot drift (same as existing ResExt discipline).

- **CommonJS `cbor.js` map decode (`cbor.js:191`):** Assumes integer keys via `k.i`. Non-int map key vectors should fail with `NonIntegerMapKey`, not an obscure property access error — verify after Step 3.2.

- **Breaking change communication:** Add a short **consumer checklist** (search for `number` int fields, `Number(` on decode paths, jsoncodec int parsing) to Phase 3 or Phase 4.1.

---

### Phase 4 — Governance

- **`CodecContract.md`:** Good promotion from `RustFailClosed.md`. Include:
  - normative int range `[-2^64, 2^64-1]`
  - canonical error tag table with payload shapes
  - corpus file paths and the exact CI command
  - explicit **out-of-scope** languages until they pass the corpus

- **Versioning:** Consider bumping a taut **wire/codec contract version** in the corpus manifest when 0.1/0.2 land so downstream repos know golden bytes may gain new vectors without it being a silent CI surprise.

---

## Items the plan does not need to solve now (acknowledge only)

| Topic | Suggestion |
|---|---|
| C++ / Swift / Go / Kotlin / Java | One sentence in §4 or Phase 4: not in scope; same corpus applies when those targets grow decode harnesses |
| Forward-compat / ResExt residual paths | Fail-closed for hostile *wire* bytes is orthogonal; ext band tests (`test_ts.py`) should keep running but are not a substitute for §0.2 |
| Encode-side validation | Plan correctly focuses on decode; no change needed |
| Matrix vs byte parity | Keep both; matrix proves live framing + jsoncodec behaviour, parity corpus proves byte-level adversarial decode |

---

## Recommended amendments to the plan (concise)

1. Add **§0.1** (or a bullet under §0): migration window + whether default flip includes fallible generated APIs.
2. In Phase 0.1: name **micro-IR** + add `2^53` boundary vectors + one **map-key overflow** vector.
3. In Phase 0.2: specify **error payload JSON schema** and authored-bytes discipline.
4. In Phase 0.3: require **hardened `try_decode` / `Result` path** in Rust harness; pin **CI command**; resolve kit `vectors.rs` compile question with a yes/no outcome.
5. In Phase 1.2: **retain thin rustc smoke** if shared harness is not compiled.
6. In Phase 2: note **jsoncodec.py already safe** for ints.
7. In Phase 3: expand **bigint/jsoncodec** scope and vendor sync between taut runtime and `taut-shape-ts`.
8. In Phase 4.1: **out-of-scope languages** + optional corpus version bump.

---

## Verdict

| Area | Rating |
|---|---|
| Problem diagnosis | **Strong** — matches repo evidence |
| Phase ordering | **Strong** — gate-first is correct |
| Technical contract (§2) | **Strong** — `i128` / unbounded `int` / `bigint` + shared tags |
| §0 decision framing | **Good** — needs migration window + API-default clarity |
| Phase 0 detail | **Good** — needs harness/CI specifics and payload error schema |
| Phase 3 completeness | **Adequate** — understates jsoncodec + consumer churn |
| LOC estimates | **Optimistic** — use as floors, not caps |

**Overall:** Approve the plan for execution. Phase 0 is ready to start without waiting on §0 ratification. Do not merge Phase 1 default-flip work until §0 is decided and documented in `CodecContract.md`.

---

*End of Review 25.*
