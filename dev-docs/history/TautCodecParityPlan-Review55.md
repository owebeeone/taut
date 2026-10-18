# taut Codec Parity Plan Review 55

## Findings

1. **[P1] The plan claims "all taut target languages" but only gates and remediates a subset.**

   References: `dev-docs/TautCodecParityPlan.md:3` through `dev-docs/TautCodecParityPlan.md:7`; `dev-docs/TautCodecParityPlan.md:11` through `dev-docs/TautCodecParityPlan.md:19`; `dev-docs/TautCodecParityPlan.md:60` through `dev-docs/TautCodecParityPlan.md:79`; `dev-docs/TautCodecParityPlan.md:113` through `dev-docs/TautCodecParityPlan.md:117`; `src/taut/gen/scaffold.py:549` through `src/taut/gen/scaffold.py:558`; `src/taut/gen/scaffold.py:32` through `src/taut/gen/scaffold.py:47`.

   The stated north star is one codec contract in every target language, and Phase 4 says the corpus runs for every language in CI. The actual Phase 0 harness is scoped to rs/py/ts, and the remediation phases cover Rust, Python, TypeScript, and CommonJS JS only. Existing first-class scaffold targets also include C++, Swift, Go, Kotlin, and Java, with runtime files already vendored for those targets. Several of those generated surfaces still use signed 64-bit carriers and infallible/panicking decode shapes, for example Go `int64`, Swift `Int64`, Java `long`, Kotlin `Long`, and C++ `long long`.

   Completing this plan as written would let Phase 4 declare a language-neutral contract while existing generated targets remain outside both the audit table and the parity gate. Either narrow the plan explicitly to the rs/py/ts/js surface, or add audit rows, Phase-0 harness entries, and follow-on remediation/migration phases for every existing target in `_LANGS`.

2. **[P1] The malformed-vector schema cannot express several of the errors it proposes to pin.**

   References: `dev-docs/TautCodecParityPlan.md:69` through `dev-docs/TautCodecParityPlan.md:77`; `src/tests/test_rust.py:537` through `src/tests/test_rust.py:569`; `src/taut/gen/runtime/cbor_fail_closed.rs:35` through `src/taut/gen/runtime/cbor_fail_closed.rs:65`; `src/taut/gen/runtime/cbor_fail_closed.rs:190` through `src/taut/gen/runtime/cbor_fail_closed.rs:201`.

   Step 0.2 defines malformed vectors as only `{ bytes: <hex>, expect_error: <canonical-tag> }`, but `MissingKey`, `WrongType`, and `UnknownEnum` are not raw-CBOR decode properties. They only emerge after decoding the bytes against a particular generated message or enum. The current Rust proof demonstrates that split: `try_decode` catches raw truncation/trailing/unsupported-major errors, while `M::from_cbor(...)` is what returns `WrongType` and `MissingKey`, and `Color::from_wire(...)` returns `UnknownEnum`.

   The vector row needs at least an entrypoint/stage and schema/message/enum identity, and probably expected payload fields for errors that carry data: missing key, wrong expected type, enum name/value, unsupported info/major. Otherwise implementations can pass tag-only tests while losing the discriminability the plan says is part of the contract.

3. **[P1] Phase 0 is described as a small extension of the existing corpus kit, but the current kit shape cannot host this gate.**

   References: `dev-docs/TautCodecParityPlan.md:65` through `dev-docs/TautCodecParityPlan.md:79`; `src/taut/corpus/kit.py:17` through `src/taut/corpus/kit.py:27`; `src/taut/corpus/synth.py:16` through `src/taut/corpus/synth.py:18`; `src/taut/corpus/kit.py:57` through `src/taut/corpus/kit.py:86`; `src/tests/test_corpus_kit.py:45` through `src/tests/test_corpus_kit.py:52`.

   `kit.build_corpus` currently accepts a map of valid native values and emits `{message, cbor}` rows. The default synthesized integer values are only `(42, -7, 300, 0)`, and the Rust harness assumes an infallible `from_cbor(c).to_cbor()` reencode path. That shape does not cover multiple hand-authored boundary values for one `taut int` field, does not cover expected failures, and does not type-check as-is against the fail-closed Rust API where `from_cbor` returns `Result`.

   Phase 0 should name the exact new fixture IR/message, vector file locations, row schemas, generated versus hand-written harness ownership, and CI command. It should also state how the deliberately red gate is staged without breaking unrelated mainline CI before Phases 1-3 are ready.

4. **[P1] The integer contract covers boundary round-trip but not out-of-subset encode, leaving a silent-wrap hole.**

   References: `dev-docs/TautCodecParityPlan.md:11` through `dev-docs/TautCodecParityPlan.md:16`; `dev-docs/TautCodecParityPlan.md:48` through `dev-docs/TautCodecParityPlan.md:50`; `dev-docs/TautCodecParityPlan.md:65` through `dev-docs/TautCodecParityPlan.md:68`; `src/taut/gen/runtime/cbor_fail_closed.rs:389` through `src/taut/gen/runtime/cbor_fail_closed.rs:396`; `src/taut/wire/cbor.py:31` through `src/taut/wire/cbor.py:44`.

   The plan pins values at the frozen bounds, but it does not define behavior for native values just outside the frozen subset, such as `2^64` or `-2^64 - 1`. That matters because the proposed Rust carrier is `i128` and the proposed TS/JS carrier is `bigint`, both of which can represent values outside the CBOR subset. The current hardened Rust runtime still encodes `Cbor::Int(i128)` by casting to `u64`, so an out-of-subset positive or negative value can silently wrap during encode. Python's `_head` rejects the same class once the argument no longer fits 64 bits.

   If "no silent truncation or wrap" is part of the contract, Phase 0 needs encode-failure vectors just outside both bounds and each language needs a typed encode error or constructor/type guard. If out-of-subset native values are intentionally out of scope, the plan should say where that invariant is enforced.

5. **[P1] Duplicate map keys are an omitted hostile input class, and current runtimes disagree on their meaning.**

   References: `dev-docs/TautCodecParityPlan.md:69` through `dev-docs/TautCodecParityPlan.md:74`; `src/taut/wire/cbor.py:164` through `src/taut/wire/cbor.py:171`; `src/taut/gen/runtime/typescript/cbor.ts:256` through `src/taut/gen/runtime/typescript/cbor.ts:265`; `src/taut/gen/runtime/cbor.rs:20` through `src/taut/gen/runtime/cbor.rs:31`; `src/taut/gen/runtime/cbor_fail_closed.rs:192` through `src/taut/gen/runtime/cbor_fail_closed.rs:201`; `src/taut/gen/runtime/cbor.go:58` through `src/taut/gen/runtime/cbor.go:66`.

   The malformed corpus lists non-integer map keys and map-key overflow, but not duplicate integer keys. A duplicate field tag is a realistic hostile message shape: Python stores decoded maps in a dict and therefore keeps the last value; TypeScript `Map.set` also keeps the last value; Rust and Go map accessors scan the entry vector and return the first value. That can make the same bytes decode to different field values or different error outcomes across languages.

   Add a `DuplicateMapKey` canonical error, or explicitly define and gate a cross-language duplicate-key policy. The same section should decide whether negative map keys and non-canonical integer encodings are accepted, normalized, or rejected, because the deterministic encoder never emits them but hostile decoders can receive them.

6. **[P2] The gwz migration note is too strong if the recommended default flip is adopted.**

   References: `dev-docs/TautCodecParityPlan.md:21` through `dev-docs/TautCodecParityPlan.md:29`; `dev-docs/TautCodecParityPlan.md:118` through `dev-docs/TautCodecParityPlan.md:121`; `dev-docs/RustFailClosed.md:154` through `dev-docs/RustFailClosed.md:166`.

   The plan recommends making fail-closed/full-range the default and keeping legacy behavior behind a deprecated opt-out. Later it says gwz is unaffected until it opts in. Those are only simultaneously true if gwz stays pinned to an older taut revision or if every gwz regeneration during the migration window passes the legacy opt-out flag. Otherwise a normal taut upgrade and regeneration would change Rust `from_cbor` to return `Result` and widen int fields to `i128`.

   The plan should spell out the actual compatibility rule: pinned consumers are unaffected; regenerating consumers must either migrate or pass the legacy opt-out during the deprecation window; after the window, regeneration is intentionally breaking.

7. **[P2] The TS JSON work is under-scoped relative to the bigint change.**

   References: `dev-docs/TautCodecParityPlan.md:48` through `dev-docs/TautCodecParityPlan.md:50`; `dev-docs/TautCodecParityPlan.md:102` through `dev-docs/TautCodecParityPlan.md:105`; `taut-shape-ts/src/taut/jsoncodec.ts:10` through `taut-shape-ts/src/taut/jsoncodec.ts:24`; `taut-shape-ts/src/taut/jsoncodec.ts:55` through `taut-shape-ts/src/taut/jsoncodec.ts:56`; `taut-shape-ts/src/taut/jsoncodec.ts:94` through `taut-shape-ts/src/taut/jsoncodec.ts:106`.

   Step 3.1 calls out `jsoncodec.ts:95`, but that is only map-key parsing. The scalar int path also uses `Number(jv)` at line 106, and the file-level contract still says native TS ints are JS numbers because the log schema fits within `2^53`. If TS native ints become `bigint`, JSON parsing, JSON emission, map-key parsing, comments/docs, and any tests that compare native values all need to move together.

   This is not a separate architecture problem, but the prompt should name the whole TS JSON surface so an implementation does not fix CBOR while leaving JSON round-trips lossy.

## Verification Notes

- Read `dev-docs/TautCodecParityPlan.md` and `dev-docs/RustFailClosed.md`.
- Inspected the current scaffold target list and runtime vendoring table in `src/taut/gen/scaffold.py`.
- Inspected Python, Rust, TypeScript, CommonJS JS, Go, Swift, Java, Kotlin, and C++ codec/generator shapes enough to verify integer carriers and decode surfaces.
- Inspected `taut-shape-ts/src/taut/cbor.ts`, `taut-shape-ts/src/taut/jsoncodec.ts`, and `taut-shape/matrix/driver.py` for the referenced external matrix/TS behavior.
- No tests were run; this was a document and implementation-plan review.
