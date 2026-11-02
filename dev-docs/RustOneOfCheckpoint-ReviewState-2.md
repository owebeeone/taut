# Rust OneOf checkpoint, remediation 2 — STATE-AXIS REVIEW

**Review object:** Taut `99b3dcf7c1f34985098a5b13add14088b86fe57c` and taut-shape-rs `8e92b89ed3a4f218a5a4e018fbfee6301fcc14b4`, including the controlling draft and authority documents. Status: frozen final remediation checkpoint.

**Baseline:** Previous reviewed Taut `ba4240778143a382be381c0f16d3659ab097ad47`; Rust shape unchanged at `8e92b89ed3a4f218a5a4e018fbfee6301fcc14b4`. Feature baselines remain Taut `7182764c4a3da372557deb6fc6f8f4b7d5f90a05` and Rust shape `959f0f048a671347c0940962c5299ae117d92f8a`. Reference-only Python shape is `c08c2a1b5197f761c5b0b835c588da512130ceda`; workspace root is `2183e4bc89f08837bc2a497e9f2680292ed8ba85`. Sources were inspected through committed diffs and file reads. Targeted comparisons against HEAD found no production-source differences.

**Date:** 2 November 2026, Australia/Sydney.

**Axis:** Durable-state semantics, filesystem identity, ownership, preflight, shared-use accounting and failure direction. Independent, adversarial, read-only. The other axis runs in parallel; nothing here relies on its current-round report. Filed verbatim by the lane owner.

**Verdict: GO** — State/P2-2 is closed by its originating reviewer; State/P2-1 remains closed. No new findings or architectural root cause were established.

---

## Prior-finding closure table

| ID | Disposition claimed | Verified on corrected tree | Status |
| --- | --- | --- | --- |
| Code/P2-1 — unqualified allocator `Box` import collides with schema types | Retain qualified allocator paths | Fresh focused suite compiled and executed all eight message/enum × source/package × validation combinations, with recursive-layout coverage retained. The originating Code reviewer’s remediation-1 closure was read. | **Retained; corroborated by State** |
| State/P2-1 — equivalent owner/root/user spellings delete live runtime components | Retain canonical identities, lexical safety and physical-overlap preflight | Independently repeated the original single-producer and enabled-A/disabled-B `owner/../owner` rebinds. Files, users and engine survived; applications compiled and ran immediately. Equivalent output spelling and safe extended prefixes retained one identity. Engine removal occurred only after the final enabled user disabled validation. | **Closed; originating closure retained** |
| State/P2-2 — Windows namespace-prefix conversion redirects generation into a distinct owner | Reject ambiguous namespace components before normalization | Repeated the original production-emitter counterexample for trailing dot and trailing space, each as schema-output directory and runtime-owner root. All four requests explicitly refused; existing trees remained byte-identical, intended namespace directories remained empty, and no output or lock remained. Shared lock/user/application boundary tests passed. | **Closed by originating State reviewer** |

## Changed-range analysis

Inspected the complete Taut change from `ba424077` to `99b3dcf7`. Rust shape has no changes in this round.

- `src/taut/gen/python_runtime.py` now checks original extended drive/UNC namespace components before resolution and prefix conversion. It rejects trailing dots/spaces, reserved DOS device names and reserved filename characters through the existing shared identity helper.
- Ten added tests cover physically distinct dot/space output directories and runtime roots, plus lock, user and application boundaries. They assert unchanged existing content and absence of new output.
- The README documents the supported-path restriction and retains ordinary extended-prefix equivalence. The draft records the final bounded correction.
- Filed remediation-1 reports/prompts and `RemPlan-2.md` are audit records supporting this round.

The correction is localized to the existing identity/preflight boundary. It does not change the runtime ABI, descriptor/report contracts, semantic engine, foundation ownership, generation options or mutation ordering. Continued-review proofs remain applicable.

**New root causes: none, bounded or architectural.**

## 0. Evidence base

Read or retraced:

- The complete generated State remediation-2 prompt.
- Committed `RustOneOfCheckpoint-Authority.md`, `RustOneOfCheckpoint-RemPlan-2.md`, both remediation-1 filed reports and the originating State findings.
- Every changed production, test and documentation range.
- The shared identity helper and its root, user, lock and application call paths.
- Completed final gate logs and package verification. The controlling proposal, repository rules and established Python baseline evidence remain applicable from prior rounds.

Fresh execution used the prescribed toolchain/environment and confined all new artifacts to `D:/projects/limbo/rust-oneof-scratch/review-state-r2`.

| Fresh check | Result |
| --- | --- |
| Original distinct-namespace output counterexample, trailing dot | Explicit refusal; both trees unchanged; no new output/lock |
| Original distinct-namespace output counterexample, trailing space | Explicit refusal; both trees unchanged; no new output/lock |
| Distinct-namespace runtime-owner counterpart, both suffixes | Explicit refusal; existing owner/application unchanged; second application absent |
| Original single-producer equivalent-root rebind | Files/user retained; immediate compilation and execution passed |
| Original enabled-A/disabled-B rebind | Both users and engine retained; immediate compilation and execution passed |
| Equivalent output-directory and safe extended-prefix identities | User counts preserved; immediate compilation and execution passed |
| Shared engine disable lifecycle | Engine retained for enabled user, removed after final disable |
| Additional reserved-name probes | Device components refused; accepted ordinary names retained actual identity |
| Permitted four-file Rust/shared/Python pytest selection | **238 passed in 76.16 seconds** |
| Canonical foundation synchronization `--check` | Passed |
| Start/end verification of all four tuple members | Exact requested SHAs |
| Targeted production-source comparisons against HEAD | No differences |

An initial pytest invocation encountered fixture setup errors because its new scratch parent had not yet been created. After creating the permitted scratch directory, the complete rerun passed as recorded above.

Completed supplied gates inspected:

- Combined feature/regression gate: **272 passed, one existing skip**.
- Final broad gate: **1,473 passed, three failed, four skipped, eight deselected in 411.51 seconds**.
- The three broad failures are exactly the established missing `TautProtoApiSurfaceExtensions.md` document and two Go CRLF/gofmt cases.
- All **16 codec parity variants GREEN**, with clean governance.
- Foundation/shape no_std and Clippy logs completed successfully.
- Exact unchanged process-global checker: **42 files, one permanent allowlist item, nothing new**.
- Source/package examples and extracted-package application passed. Package verification records no compiler or shape-engine dependency.

No source, configuration, checker or allowlist was modified during review.

## Problem, requirement provenance, and scope

The operator-authorized outcome remains working Rust mandatory metadata, safe typed access and optional explicit validation against accepted Python behavior, with lightweight canonical runtime delivery, actual Rust shape-library composition and executable conformance. The authority document records supersession of the older documentation-only/Python stop and preserves the no-release boundary.

The original implementation addresses concrete missing Rust metadata/validation and separate nominal runtime ownership. Existing source/package applications, independently generated dependency tests and actual shape-library builds establish feasibility without registry publication, installation or additional infrastructure.

This round addresses the demonstrated namespace redirection defect through the conservative refusal explicitly selected in `RemPlan-2.md`, an allowed remedy in the originating finding. Supporting exotic Windows namespace filenames is not necessary for the requested outcome. The restriction is documented, while safe ordinary extended-prefix spellings remain usable.

The shared helper change is within the authorized output-ownership boundary and has fresh Python/shared regression coverage. No unrelated backend, project or infrastructure expansion was found. No scope or necessity evidence gap remains blocking this checkpoint.

## 2. Invariant analysis

- **Namespace meaning:** The original physically distinct directory attacks no longer reach generation application. All four output/runtime cases refuse with the offending namespace component named and preserve existing state.
- **Consistent boundaries:** Roots, users, lock deduplication and physical-target checks use the same refusal policy. The fresh lock/user/application tests passed for both suffixes.
- **Equivalent identities:** Original `..` owner/output spellings and safe extended drive prefixes still unify correctly. They neither delete required files nor introduce phantom users.
- **Shared-use accounting:** Enabled and disabled users remain independently recorded. A disabled user’s regeneration preserves another user’s engine; cleanup removes it only when no recorded user requires it.
- **Lexical alias protection:** Junction/reparse and path-kind obstruction tests remain green. Identity normalization does not authorize following an unsafe directory alias.
- **Complete preflight:** Physical write/delete overlap and unknown, modified, handwritten or incompatible outputs remain explicitly rejected before replacement.
- **Failure direction:** The new restriction raises a configuration error rather than claiming success or redirecting writes. Per-file atomic application and the previously reviewed fail-closed partial-output behavior remain unchanged.
- **Rust/API preservation:** Qualified allocator paths, recursive storage, mandatory metadata, optional methods, typed lifetime boundaries, report snapshots and fast/report equivalence remain covered by the passing focused suite.
- **Composition and provenance:** No new nominal owner or runtime implementation was introduced. Canonical synchronization, actual library checks and extracted-package evidence remain consistent.
- **Regression boundaries:** The broad run is complete. Its only failures match established baseline evidence; broad-suite success is not overstated.

## 3. Risks and next action

The documented Windows namespace restriction is intentional. Existing wasm-target coverage and Windows `python3` harness limitations remain disclosed. This review does not establish whole-tree crash rollback or protection against arbitrary external filesystem mutation during application.

The next action is for the lane owner to combine this GO with the independent Code re-verdict on the same tuple and complete the authorized checkpoint process. This report does not authorize a release.
