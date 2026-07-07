# taut Codec Parity Plan Review 55-2

## Findings

1. **[P1] The plan conflates CBOR map keys with schema-level `map<int, int>` keys.**

   References: `dev-docs/TautCodecParityPlan.md:76` through `dev-docs/TautCodecParityPlan.md:81`; `dev-docs/TautCodecParityPlan.md:102` through `dev-docs/TautCodecParityPlan.md:105`; `src/taut/wire/codec.py:48` through `src/taut/wire/codec.py:53`; `src/taut/gen/rust.py:82` through `src/taut/gen/rust.py:84`; `src/taut/gen/runtime/cbor_fail_closed.rs:11` through `src/taut/gen/runtime/cbor_fail_closed.rs:15`.

   Section 2a says `>i64 map key -> IntOverflow`, and Phase 0.1 proposes a micro-IR with one `map<int,int>` plus a map-key `i64::MAX+1` expected to fail with `IntOverflow`. In taut's schema codec, though, `map<int,int>` is not encoded as a CBOR map keyed by the user's int. It is encoded as a CBOR array of entry maps `{1: key, 2: value}`. The user map key is therefore an ordinary taut `int` value and should be covered by the same full-range contract as any other int field, including values above `i64::MAX`.

   `IntOverflow` makes sense for CBOR field-tag keys and residual/raw CBOR map keys, which the Rust fail-closed runtime deliberately keeps as `i64`. It should not apply to a schema-level `map<int,T>` key. Phase 0.1 should split these tests: one vector proving `map<int,int>` keys round-trip through the full frozen int range, and a separate malformed raw-CBOR message whose field tag/map key exceeds `i64::MAX` and yields `IntOverflow`.

2. **[P1] `IntOutOfSubset` requires a fallible encode API, but the plan only specifies fallible decode.**

   References: `dev-docs/TautCodecParityPlan.md:11` through `dev-docs/TautCodecParityPlan.md:18`; `dev-docs/TautCodecParityPlan.md:84` through `dev-docs/TautCodecParityPlan.md:87`; `dev-docs/TautCodecParityPlan.md:130` through `dev-docs/TautCodecParityPlan.md:132`; `src/taut/gen/rust.py:223` through `src/taut/gen/rust.py:237`; `src/taut/gen/runtime/cbor_fail_closed.rs:31` through `src/taut/gen/runtime/cbor_fail_closed.rs:35`; `src/taut/gen/runtime/cbor_fail_closed.rs:383` through `src/taut/gen/runtime/cbor_fail_closed.rs:396`.

   The revised contract correctly adds typed encode failure for native values outside `[-2^64, 2^64-1]`, but the implementation phases still describe the hardened Rust shape as `from_cbor -> Result` plus a hardened runtime. The generated Rust `to_cbor` still returns `Cbor`, and the runtime `encode` still returns `Vec<u8>`. There is nowhere for a typed `IntOutOfSubset` error to go unless `to_cbor`, `encode`, or the integer carrier itself becomes fallible/validated.

   This is a contract-shaping decision, not a small runtime fix. The plan should choose an encode surface for every target, for example `try_to_cbor`/`try_encode -> Result`, a validated `TautInt` newtype, or an explicit split where construction validates and encode remains infallible. It should also avoid reusing a Rust `DecodeError` type whose own docs say every variant comes from input bytes if that type is going to carry encode failures.

3. **[P1] Phase 0 says it gates all nine targets, but Wave 2 only gets stubs until Phase 4.**

   References: `dev-docs/TautCodecParityPlan.md:28` through `dev-docs/TautCodecParityPlan.md:29`; `dev-docs/TautCodecParityPlan.md:96` through `dev-docs/TautCodecParityPlan.md:100`; `dev-docs/TautCodecParityPlan.md:114` through `dev-docs/TautCodecParityPlan.md:126`; `dev-docs/TautCodecParityPlan.md:156` through `dev-docs/TautCodecParityPlan.md:166`; `dev-docs/TautCodecParityPlan.md:178` through `dev-docs/TautCodecParityPlan.md:182`.

   Rev3 says each of the five Wave 2 targets is a red row in the leading gate from day one, and Phase 0 is a barrier before remediation. But Phase 0.3 says C++/Swift/Go/Kotlin/Java get harness stubs and only receive real harnesses as Wave 2 reaches them. A stub on an xfail allowlist is not a conformance replay harness; it cannot prove the current target is red for the right reason, and it cannot detect drift while the target remains allowlisted.

   If the gate is meant to lead for all nine targets, Phase 0 should include real corpus replay for all nine, even if five are marked expected-fail. If that is too much for Phase 0, the plan should weaken the claim: Wave 1 is gated first, and Wave 2 becomes genuinely gated when each real harness lands. Also specify strict xfail behavior and whether an allowlisted target must still execute the corpus and report exact observed failures.

4. **[P2] The strictness policy adds rejection cases without canonical error tags.**

   References: `dev-docs/TautCodecParityPlan.md:84` through `dev-docs/TautCodecParityPlan.md:92`; `dev-docs/TautCodecParityPlan.md:106` through `dev-docs/TautCodecParityPlan.md:113`.

   Section 2c recommends rejecting non-minimal/non-canonical int encodings and negative map keys, and says each is a Phase-0 vector. The canonical vocabulary in 2b has no tag for either class. They are not `UnsupportedInfo`, because the additional-info forms are otherwise supported, and a negative map key is still an integer key rather than `NonIntegerMapKey`.

   If these strictness rules are part of the contract, add tags such as `NonCanonicalInt` and `NegativeMapKey`, or explicitly map them to existing tags in 2b. Otherwise the vector schema cannot assert exact typed tag+payload for every hostile class it says it covers.

5. **[P2] Phase 4 under-scopes the native API fallout of big-int carriers, especially maps.**

   References: `dev-docs/TautCodecParityPlan.md:76` through `dev-docs/TautCodecParityPlan.md:80`; `dev-docs/TautCodecParityPlan.md:156` through `dev-docs/TautCodecParityPlan.md:164`; `src/taut/gen/go.py:19` through `src/taut/gen/go.py:27`; `src/taut/gen/go.py:91` through `src/taut/gen/go.py:99`; `src/taut/gen/java.py:19` through `src/taut/gen/java.py:21`; `src/taut/gen/kotlin.py:30` through `src/taut/gen/kotlin.py:31`.

   Phase 4 treats carrier choice as the first design step, but the carrier choice changes more than scalar field types. The current Go generator emits native maps as `map[K]V` and sorts keys with `<`; `math/big.Int` is not a drop-in key type for that shape, and a pointer key would compare by identity rather than integer value. Java/Kotlin `BigInteger` likewise changes comparison, equality, enum wire values, JSON conversion, and generated API ergonomics.

   Phase 4 should explicitly include per-language native map representation and ordering, enum wire representation, JSON/native conversion, and equality/comparison semantics as owned work. Otherwise an implementer can "pick BigInteger" for scalar fields and still leave `map<int,T>` or enum paths non-parity.

## Verification Notes

- Re-read the revised `dev-docs/TautCodecParityPlan.md` rev3 and prior `TautCodecParityPlan-Review55.md`.
- Inspected the current Python codec, Rust generator, Rust fail-closed runtime, and Go/Java/Kotlin generator shapes for the referenced API and map-key behavior.
- Attempted lightweight Swift/Go toolchain checks, but the machine reported only about 117 MiB free on `/` and Go failed creating its build work directory with "no space left on device". No compile/test verification was run.
