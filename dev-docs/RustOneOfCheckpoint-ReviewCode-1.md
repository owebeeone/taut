# Rust OneOf checkpoint remediation 1 — CODE + SURFACE-AXIS REVIEW

**Review object:** Taut `ba4240778143a382be381c0f16d3659ab097ad47` and taut-shape-rs `8e92b89ed3a4f218a5a4e018fbfee6301fcc14b4`, including committed `dev-docs/RustOneOfCheckpoint-Draft.md`. Status: remediation 1 frozen for review; acceptance and release are not claimed.

**Baseline:** Feature baselines are Taut `7182764c4a3da372557deb6fc6f8f4b7d5f90a05` and Rust shape `959f0f048a671347c0940962c5299ae117d92f8a`. This continued review examines changes from previously reviewed Taut `020f7b08d379e2a27720eda102c2782dfcc55e3e` and Rust shape `b55cd89e76830e61f8580c5f5e0b38519e7cef95`. Reference-only Python shape remains `c08c2a1b5197f761c5b0b835c588da512130ceda`; workspace HEAD remains `2183e4bc89f08837bc2a497e9f2680292ed8ba85`. Sources were read through committed diffs and file reads; final targeted `git diff --exit-code HEAD` checks confirmed production source matched the commits.

**Date:** 2 November 2026, Australia/Sydney.

**Axis:** Code architecture, interfaces, typed ownership/lifetimes, compatibility and public Surface. Independent, adversarial, read-only. The other axis runs in parallel; nothing here relies on its current re-verdict. Filed verbatim by the lane owner.

**Verdict: GO** — Code/P2-1 is closed. No new findings or architectural root cause were established.

---

## Prior-finding closure table

| ID | Disposition claimed | Verified on corrected tree | Status |
| --- | --- | --- | --- |
| Code/P2-1 — unconditional unqualified `Box` import breaks generated schema types | Support schema types named `Box` by removing the import and qualifying allocator storage/construction | Re-ran the exact original production-emitter counterexample: compilation and execution now pass. Independently compiled and ran all eight message/enum × source/package × validation on/off combinations. A recursive schema itself named `Box` also round-tripped and validated successfully. | **Closed by originating Code reviewer** |
| State/P2-1 — equivalent owner/root/user spellings delete live runtime components | Normalize identities after lexical safety checks; reject physical output contradictions before mutation | Independently repeated the original one-producer and enabled-A/disabled-B equivalent-root rebinds. Runtime files/users/engine survived and applications compiled and ran immediately. Fresh focused tests also passed equivalent output-directory, Windows extended-path, overlap rejection and junction-protection cases. | **Corroborated in changed-range review; originating State closure remains that reviewer’s responsibility** |

## Changed-range analysis

The complete production and generated-output changes since the original tuple belong to the two recorded dispositions:

- **Rust generator:** `rust_metadata.py` removes the unqualified allocator import. `rust.py` qualifies boxed field storage and decoder construction with `alloc::boxed::Box`. This fixes the collision without imposing a new schema-name restriction.
- **Generated artifacts:** Four Taut goldens and six Rust shape modules change only the corresponding import. Shape provenance updates the generated hashes while retaining the same schema hashes.
- **Rust ownership planning:** `rust_runtime.py` checks lexical paths and ancestors before physical normalization; normalizes current/prior roots, output directories and user identities; replaces equivalent spellings of the current user; and rejects ambiguous duplicate user records.
- **Shared application safety:** `python_runtime.py` adds physical identity normalization, including Windows extended drive/UNC spelling, uses it for lock deduplication, and rejects overlapping physical output targets before applying writes or deletions.
- **Scaffold:** Rust output-directory planning uses the same lexical-checking canonicalization helper.
- **Tests:** Thirteen added cases cover the eight `Box` combinations and five physical-path/accounting protections.
- **Documentation and audit records:** The draft and README describe the corrections; the original prompts, reports and merged remediation plan record the prior gate.

These changes preserve the public descriptor/report ABI, validation semantics, foundation owner, generation switches and existing pre-write mutation boundary. The additional contradiction check strengthens that boundary rather than relocating it. The prior code/lifetime/composition proofs remain applicable.

**New architectural root causes: none.** This is a bounded correction suitable for continued review by the same two reviewers.

## 0. Evidence base

Public help and the complete Rust examples README were refreshed before inspecting remediation design/code. The original review’s cold Surface examination remains recorded in the filed Code report.

Read or retraced:

- The complete canonical remediation prompt.
- `RustOneOfCheckpoint-Authority.md`, both original filed reviews and `RustOneOfCheckpoint-RemPlan-1.md`.
- The changed draft and README against the controlling build proposal and original authority.
- Complete remediation production diffs for `rust.py`, `rust_metadata.py`, `rust_runtime.py`, `python_runtime.py` and `scaffold.py`.
- Current physical-path, alias-checking, locking and output-application call paths.
- All added tests, four changed goldens, six shape generated-file changes and their provenance updates.
- Completed combined/broad/parity results, package verification and relevant no_std/Clippy evidence. Established Python baseline evidence remains applicable.

Fresh execution used the required toolchain environment, disabled bytecode/plugin autoload/cache, and confined all new artifacts to `D:/projects/limbo/rust-oneof-scratch/review-code-r1`.

| Fresh check | Result |
| --- | --- |
| Exact original `Box` counterexample | Compilation and execution passed |
| Message/enum `Box`, source/package, validation on/off | **All eight passed** |
| Recursive schema named `Box` | Validation and CBOR round-trip passed |
| Original equivalent-root single-producer reproduction | Runtime/user retained; immediate compilation/execution passed |
| Original equivalent-root enabled-A/disabled-B reproduction | Both users and engine retained; immediate compilation/execution passed |
| Allowed four-file Rust/shared/Python pytest selection | **228 passed in 41.09 seconds** |
| Canonical foundation `--check` | Passed |
| Fresh CLI source/package/descriptor-only walkthrough | All compiled and executed |
| Source → package, validation on → off transition | Expected tracked runtime cleanup and optional-method removal passed |
| Actual shape `cargo check --offline --locked`, no default features, validation enabled | Passed |
| Exact unchanged process-global checker with verified Python | Passed: 42 files, one permanent allowlist entry, nothing new |
| Start/end Taut and Rust shape HEAD checks | Exact requested commits |
| Final Python shape/workspace reference checks | Exact requested commits |
| Final targeted tracked-source comparisons against HEAD | No differences |

Completed supplied gates:

- Combined feature/regression gate: **262 passed, one existing skip**.
- Final broad gate: **1,463 passed, three failed, four skipped, eight deselected**.
- The three broad failures are exactly the established missing old document and two Windows Go CRLF/gofmt cases.
- All **16 codec parity variants GREEN**, with clean governance.
- Extracted local foundation package application passed without compiler or shape-engine dependency.
- Recorded foundation/shape no_std, Clippy, examples and shape checks passed.

No source, configuration, checker or allowlist was modified during this review.

## Problem, requirement provenance, and scope

The operator-authorized outcome remains working Rust metadata, typed access and optional explicit validation against accepted Python behavior, with independent structural codecs, canonical lightweight runtime delivery and actual Rust shape-library composition. The committed authority records the shared checkout, checkpoint commit/push authorization, superseded documentation-only/Python stop and explicit prohibition on release operations.

The original implementation addressed concrete missing Rust metadata/validation and the shape library’s separate nominal CBOR owner. The foundation route remains justified by the requirements for one actual owner and basic `no_std + alloc` consumption without shape engines. Existing executable source/package and actual-library proofs establish feasibility without publication or installation.

Remediation addresses two demonstrated defects within that scope. Removing the allocator import is a localized compatibility-preserving correction. Physical identity normalization and the shared contradiction guard directly address successful generation deleting required output; they are necessary within the existing authorized ownership/preflight implementation.

No unsupported infrastructure prerequisite, unrelated backend implementation or unauthorized component expansion was established. Python remains reference-only except for the authorized shared application boundary and regression coverage.

## 2. Invariant analysis

- **Generated-name correctness:** Removing the import eliminates the original collision. Qualified allocator references continue working when the schema itself owns the name `Box`, including recursive storage and decode.
- **Equivalent ownership identity:** Current/prior roots now deduplicate before accounting. Equivalent schema-output spellings replace one user identity rather than creating competing users. Original one- and two-user counterexamples no longer lose files or the validation engine.
- **Lexical safety:** Rust canonicalization checks the original path and ancestors before resolving identity. Existing junction/obstruction tests remain green; normalization does not silently authorize reparse paths.
- **Physical application preflight:** Identity collisions and write/delete overlap are rejected before replacement. The new guard operates within the existing complete preflight boundary.
- **Shared Python behavior:** The fresh shared/Python tests passed with the updated lock/application helpers. The final broad gate adds no new failure identity.
- **Validation/API preservation:** Descriptor/report resources and method semantics are unchanged. Fresh behavioral tests and walkthroughs retain recursive defaults, local scope, virtual incompleteness, fast/report equivalence, owned snapshots and invalid-draft serialization.
- **Composition preservation:** Independent dependency and actual shape cases remain covered by the fresh focused suite. The shape-generated changes introduce no new owner, descriptor type or report engine.
- **Provenance:** Canonical foundation synchronization passes. Shape artifact changes are limited to the corrected generated import and associated hashes.

### Surface

The correction preserves the existing `gen` command placement, switches and defaults. The README now explicitly states that schema messages/enums named `Box` are supported through qualified allocator paths and describes equivalent-path ownership behavior.

Fresh source, package and descriptor-only use succeeded using the documented module/foundation routes. Regeneration with package mode and validation disabled removed the tracked source closure and optional methods as documented. No installation, registry release or hidden owner-selection assumption was needed.

The four instance methods, recursive defaults, read-only report getters and single-owner Cargo binding remain unchanged. No new Surface finding was established.

## 3. Risks and next action

The existing wasm-target coverage limitation, Windows `python3` harness limitation and three demonstrated broad-suite baseline failures remain disclosed. This review does not establish whole-tree crash rollback or protection against arbitrary external filesystem mutation during application; neither is introduced as a checkpoint requirement.

The next action is for the lane owner to combine this **GO** with the independent State re-verdict on the same tuple and proceed through the authorized checkpoint process. This report does not authorize a release.
