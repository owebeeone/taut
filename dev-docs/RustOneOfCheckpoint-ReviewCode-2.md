# Rust OneOf checkpoint remediation 2 — CODE + SURFACE-AXIS REVIEW

**Review object:** Taut `99b3dcf7c1f34985098a5b13add14088b86fe57c` and taut-shape-rs `8e92b89ed3a4f218a5a4e018fbfee6301fcc14b4`, including committed `dev-docs/RustOneOfCheckpoint-Draft.md`. Status: second and final bounded remediation frozen for review; acceptance and release are not claimed.

**Baseline:** Feature baselines are Taut `7182764c4a3da372557deb6fc6f8f4b7d5f90a05` and Rust shape `959f0f048a671347c0940962c5299ae117d92f8a`. This continued review examines Taut `ba4240778143a382be381c0f16d3659ab097ad47..99b3dcf7c1f34985098a5b13add14088b86fe57c`; Rust shape is unchanged from remediation 1. Reference-only Python shape remains `c08c2a1b5197f761c5b0b835c588da512130ceda`; workspace HEAD remains `2183e4bc89f08837bc2a497e9f2680292ed8ba85`. Sources were inspected through committed diffs and file reads; targeted comparisons confirmed reviewed production files matched HEAD.

**Date:** 2 November 2026, Australia/Sydney.

**Axis:** Code architecture, interfaces, typed ownership/lifetimes, compatibility and public Surface. Independent, adversarial, read-only. The other axis runs in parallel; nothing here relies on its current report. Filed verbatim by the lane owner.

**Verdict: GO** — Code/P2-1 remains closed. The final changed range establishes no new finding or architectural root cause.

---

## Prior-finding closure table

| ID | Disposition claimed | Verified on corrected tree | Status |
| --- | --- | --- | --- |
| Code/P2-1 — unqualified allocator import breaks schema types named `Box` | Retain qualified allocator paths and support `Box` schema types | Repeated the exact original production-emitter counterexample: compilation and execution passed. The fresh suite also compiled all eight message/enum × source/package × validation on/off cases and retained recursive-layout coverage. | **Closed by originating Code reviewer; closure retained** |
| State/P2-1 — equivalent owner/user spellings delete live runtime components | Retain canonical identities, lexical safety and physical-overlap preflight | Fresh tests passed original one-producer/shared-user equivalent-root scenarios with immediate application builds, equivalent output-user identity, safe extended-prefix equivalence, engine retention and junction/overlap protections. | **Originating State closure recorded in remediation 1; retained correction corroborated** |
| State/P2-2 — Windows namespace-prefix removal redirects generation into a distinct owner | Reject ambiguous namespace components before normalization, locking or mutation | Independently repeated physically distinct trailing-dot and trailing-space directory cases for both schema output and runtime-owner roles. Every request failed explicitly; existing trees remained byte-identical, extended destinations stayed empty and no new runtime-consumer destination appeared. Fresh boundary tests also passed. | **Correction corroborated; originating State reviewer determines final closure** |

## Changed-range analysis

Inspected every production, test and public-document change since remediation 1.

- `src/taut/gen/python_runtime.py` adds a lexical check inside the existing shared physical-identity helper. Before resolving or removing extended drive/UNC prefixes, it rejects namespace components with trailing dots/spaces, reserved DOS device names, reserved filename characters or control characters. Ordinary supported extended-prefix equivalence remains.
- `src/tests/test_rust_oneof.py` adds ten cases: four distinct-directory output/runtime refusal cases and six lock/user/application-boundary refusal cases. They check unchanged existing output and absence of new output.
- The README documents the supported-path restriction and its filesystem-identity rationale.
- The draft records the final bounded remediation and prior finding dispositions.
- Remaining additions are prior-round prompts, reports and the remediation plan, providing audit history.
- Rust shape has no new source or generated-artifact changes.

The correction changes neither runtime ABI nor descriptor/report contracts, semantic validation, generation switches, mutation ordering or foundation architecture. It narrows accepted exotic namespace inputs within the existing preflight boundary, as permitted by the prior State finding and selected in the remediation plan.

**New architectural root causes: none.** No new bounded implementation defect was established. Continued-review proofs remain applicable.

## 0. Evidence base

Refreshed live `gen --help` and read the complete public examples README before examining this correction. The initial cold Surface review remains documented in the original Code report.

Read or retraced:

- Complete canonical remediation-2 prompt.
- Committed authority, both remediation-1 reports and `RustOneOfCheckpoint-RemPlan-2.md`.
- Complete changed production/test/document ranges.
- Current shared identity helper and its root, user, lock and application call sites.
- Retained allocator qualification, lexical alias checks, ownership accounting and output contradiction guard.
- Completed focused, broad, parity, package, no_std, Clippy, shape and examples evidence.
- Established Python baseline evidence supporting the three excluded broad-suite failures.

Fresh checks used the required toolchain environment and confined all new artifacts to `D:/projects/limbo/rust-oneof-scratch/review-code-r2`.

| Fresh check | Result |
| --- | --- |
| Exact original `Box` compiler counterexample | Compilation and execution passed |
| Allowed four-file Rust/shared/Python pytest selection, isolated basetemp and no cache provider | **238 passed in 78.59 seconds** |
| Distinct extended trailing-dot output directory | Explicit refusal; trees unchanged |
| Distinct extended trailing-space output directory | Explicit refusal; trees unchanged |
| Distinct extended trailing-dot runtime owner | Explicit refusal; trees unchanged; no consumer destination created |
| Distinct extended trailing-space runtime owner | Explicit refusal; trees unchanged; no consumer destination created |
| Additional DOS-name, reserved-character and control-character namespace probes | Explicit refusal |
| Canonical foundation `--check` | Passed |
| Fresh CLI source/package/descriptor-only walkthrough | All compiled and executed |
| Source → package and validation on → off transition | Expected tracked-runtime cleanup and optional-method removal passed |
| Actual shape offline/locked no_std check with validation | Passed |
| Exact unchanged process-global checker | Passed: 42 files, one permanent allowlist item, nothing new |
| Start/end Taut and Rust shape HEAD verification | Exact requested commits |
| Final Python shape/workspace reference verification | Exact requested commits |
| Targeted production comparisons against HEAD | No differences |

Completed supplied gates, inspected before verdict:

- Combined feature/regression gate: **272 passed, one existing skip**.
- Final broad gate: **1,473 passed, three failed, four skipped, eight deselected**, completed in 411.51 seconds.
- Failure identities are exactly the established missing `TautProtoApiSurfaceExtensions.md` and two Windows Go CRLF/gofmt cases.
- All **16 codec parity variants GREEN**, with clean governance.
- Foundation/shape no_std and Clippy checks, shape tests and examples completed successfully.
- Extracted local foundation package application passed, with no compiler or shape-engine dependency.

No source, configuration, checker or allowlist was modified during review.

## Problem, requirement provenance, and scope

The operator-authorized outcome remains working Rust metadata, safe typed access and optional explicit validation against the accepted Python behavior, with independent structural codecs, lightweight canonical runtime delivery and actual Rust shape-library composition. The committed authority supersedes the earlier documentation-only/Python stop and authorizes the checkpoint without release operations.

The original Rust gaps and foundation-route necessity remain supported by baseline inspection, executable source/package consumers and actual library composition. No registry publication, installation or additional infrastructure is required.

The current observed problem was demonstrated in the prior State review: prefix removal could redirect an extended namespace path into a physically distinct ordinary directory. The selected remedy explicitly refuses the affected path class. Supporting exotic Windows namespace filenames is not necessary for the requested checkpoint, and the supported ordinary routes remain executable.

The shared helper is the appropriate localized correction point because roots, users, locks and application targets already use it. No unrelated component expansion or unsupported prerequisite was found. Python remains reference-only except for the authorized shared boundary and regression coverage; the other seven feature backends remain deferred.

## 2. Invariant analysis

- **Namespace identity:** Dangerous original namespace components are examined before resolution and prefix removal. The four independent production-emitter probes no longer redirect generation or alter another owner.
- **Failure direction:** Refusal is explicit and names the offending namespace component. Tests and probes confirm no successful partial generation, new lock or consumer output in the demonstrated cases.
- **Consistency across boundaries:** Roots/users, lock deduplication and application targets use the corrected shared identity helper. The added boundary tests passed.
- **Retained equivalence:** Ordinary extended-prefix and `..` spellings continue sharing the intended owner and schema-user identity. Shared validation remains while an enabled user requires it.
- **Lexical safety:** Existing junction/reparse, obstruction and physical write/delete protections remain in place and pass the fresh suite.
- **Generated-name correctness:** The original `Box` failure remains corrected without banning the schema name. All required combinations compile.
- **Runtime/API preservation:** Descriptor/report resources and validation semantics are unchanged. Fresh conformance tests retain recursive defaults, local scope, virtual incompleteness, fast/report equivalence, owned snapshots and invalid-draft round trips.
- **Composition and delivery:** Independent dependency and actual shape cases pass. Fresh source/package/descriptor-only consumers run without generation-time installation or application-time compiler dependencies.
- **Regression evidence:** The final broad run completed and introduced no new failure identity.

### Surface

The README clearly documents the conservative namespace restriction, its reason and the ordinary-filename remedy. The error identifies the rejected component. This introduces no new command, lifecycle operation or setting.

The existing `gen` placement, source/package/supplied defaults, source alias and validation-off default remain unchanged. The four instance methods, recursive defaults, getters and Cargo owner binding remain intact.

Fresh first-day source, package and descriptor-only walkthroughs passed. The documented mode transition removed tracked source files and optional methods. No hidden installation or release assumption was needed. No new Surface finding was established.

## 3. Risks and next action

The existing wasm coverage limitation, Windows `python3` harness limitation and three established broad-suite baseline failures remain disclosed. Exotic namespace filenames in the documented rejected class are intentionally unsupported.

The next action is for the lane owner to combine this **GO** with the originating State reviewer’s final verdict on the same tuple, then complete the authorized checkpoint process. This report does not authorize a release.
