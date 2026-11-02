# BuildProposal.md — CONSISTENCY-AXIS REVIEW

**Review object:** `BuildProposal.md` at isolated snapshot `e6d0c21b22c6c80b86f2e380c179c315a1fae5d8`, `/var/folders/02/bn9c9g2x5qj8bb42zb857p7c0000gn/T/taut-build-proposal-review-hkd1izpi/BuildProposal.md`. DRAFT, proposal-only review; working tree clean at start and end.
**Baseline:** `DRAFT.md` and `BehavioralBaseline.md` from the same isolated commit. Read numbered working-tree files after verifying HEAD and clean status. No implementation repositories inspected.
**Date:** 2 November 2026
**Axis:** Consistency with controlling authority and behavioral contracts, plus public API Surface. Independent, adversarial, read-only. The other axis runs in parallel; nothing here relies on it. Filed verbatim by the lane owner.

**Verdict: GO** — no P0, P1, P2 or P3 findings. This accepts consolidated proposal coherence only.

---

## 0. Evidence base

Read:

- Generated `TautBuild-PromptConsistency.md`, including the exact tuple, scope, deferrals and report requirements.
- Workspace `AGENTS_GWZ.md`.
- Process authority `/Users/owebeeone/.claude/skills/review-loop/SKILL.md`.
- `BuildProposal.md`, lines 1–589, reading its public schema, descriptor and API surfaces before `DRAFT.md`.
- `DRAFT.md`, lines 1–11.
- `BehavioralBaseline.md`, lines 1–623, distinguishing normative behavior, historical probes and the latest descriptor amendment.

Ran only read-only inspection commands. At both review start and end:

- `git rev-parse HEAD` returned `e6d0c21b22c6c80b86f2e380c179c315a1fae5d8`.
- `git status --short` returned no entries.

No source, executable probes, builds, tests, dependency internals or current peer report were inspected. Historical test counts were read as reported evidence, not independently reproduced.

## Problem, requirement provenance, and scope

The requested outcome is a consolidated build/API proposal covering nine languages, with Python first, reusable reports, explicit instance validation, recursive/local selection, a Boolean fast path and mandatory descriptors. `DRAFT.md:3–7` records operator authority and explicitly distinguishes this document gate from implementation acceptance or adapter ABI freeze.

The problem addressed is the fragmentation of earlier behavioral semantics and subsequent API amendments. The proposal consolidates those decisions while preserving invalid draft construction, explicit validation timing and codec responsibility. `BuildProposal.md:24–34` explicitly replaces earlier descriptor optionality, constrained-message eligibility, free/static entry points and disabled-output identity promises. Its detailed sections preserve the remaining behavioral baseline: field-local nomination, coverage modes, sparse JSON payloads, unchanged dense CBOR, owned traversal and observational validation.

Authorized editable components are the proposal and its review/draft/remediation/verdict records. Production Taut, probes, generated code, GARNS resolver/parser and dependencies remain reference-only (`BuildProposal.md:19–22`; `DRAFT.md:9`). No implementation or dependency change is made a prerequisite for this document gate.

The proposal retains the existing compiler/emit route and directs future feasibility checks before infrastructure changes (`BuildProposal.md:85–88`, `319–320`, `565–567`). It considers localized routes rather than requiring broader architecture: typed adapters instead of a mandatory base class, existing Java visibility instead of a public multi-file redesign, and existing JavaScript module conventions instead of an ES-module migration.

Concrete adapter layouts, import prefixes and numeric version allocation remain explicitly unfinished. Their deferral is authorized by `DRAFT.md:7` and accurately repeated in `BuildProposal.md:575–589`. No missing evidence requires widening this review into implementation experiments.

No external shortcomings were established during this document-only review, and none is treated as a current-deliverable blocker.

## 2. Invariant analysis

### Controlling graph and supersessions

The supersession table resolves the material historical conflicts:

- Mandatory descriptors and changed goldens replace the earlier disabled-output identity promise.
- Every enabled message receives methods, replacing reachability-based eligibility and the historical absence of a virtual-only validator.
- Shared reports and instance entry points replace schema-specific/free-function alternatives.
- Virtual runtime validation remains deferred; generating methods does not turn that deferral into success.

The baseline’s historical examples and probe restrictions remain evidence rather than competing implementation requirements. The proposal expressly disclaims adoption of its earlier GO/GO and the 42 probe tests as acceptance of this consolidated contract (`BuildProposal.md:14–17`, `585–589`).

### Surface walkthrough

The document supports a coherent first-use sequence:

1. Generate normally, with mandatory descriptors in either mode. Omitted `--with-validation` and programmatic `validation=False` disable instance validation methods.
2. Enable methods through the generation flag. Construct and mutate ordinary drafts without semantic validation.
3. Run local or default-recursive validation. Report validity and completeness are separate; the Boolean operation equals their conjunction.
4. Serialize drafts without selecting a payload winner or repairing their semantic state.
5. Reuse a separately generated child whose validation methods are disabled through mandatory metadata and typed adapters. Reject an old incompatible child explicitly.
6. Regenerate with validation disabled using fresh output or identified generator-owned cleanup, preserving handwritten files and preventing stale methods from masquerading as disabled output.

The enabled-to-disabled lifecycle has an explicit cleanup/fresh-directory policy (`BuildProposal.md:569–573`). Defaults are stated, including Go’s deliberate distinction between no-options methods and explicitly supplied zero-value options.

### Shared reports and traversal

The shared report inventory supports general diagnostics without per-schema nominal types. Snapshot ownership, immutable paths and protected collections prevent later draft mutation from rewriting earlier reports (`BuildProposal.md:223–249`).

Local scope excludes descendants without calling them deferred. Recursive scope covers ordinary fields, payloads and collection contents, including invalidly populated nonselected payloads. Wrong discriminators skip dependent selection checks without suppressing independent traversal. Virtual groups contribute deferred entries and make the Boolean result false. Deterministic ordering and active-ancestor cycle detection agree with the behavioral baseline.

### Imported types and language projections

The proposal avoids requiring optional child methods for parent traversal. It separates portable descriptor facts from typed host access, requires correct value/descriptor pairing and rejects invalid links before publication.

Language-specific seams are addressed at the promised design level:

- Rust methods belong to the type’s owning crate; parent traversal does not attempt foreign inherent implementations.
- Java preserves package-private schema visibility rather than implying new cross-package public access.
- TypeScript explicitly distinguishes disabled interface output from enabled concrete classes and defines constructor copying and nested-value behavior.
- C++ uses static read-only metadata, avoids RTTI and specifies an allocation-free resource-exhaustion fallback rather than relying on `noexcept` alone.

The remaining adapter ABI work is explicitly assigned before backend implementation. It is not misrepresented as proven or complete.

### Conformance and evidence limits

The corpus covers both generation modes, mandatory descriptors, enabled parent/disabled child composition, incompatible artifacts, report/fast parity, local/recursive behavior, virtual deferral, immutable snapshots and language-specific constraints. All nine backends must compile/import and execute their tests; Python-only completion is not full feature completion (`BuildProposal.md:525–573`).

No current implementation result or release readiness is claimed. The required future tests are consistent with the stated proposal and do not require exercising intentionally deferred virtual semantics as though implemented.

## 3. Risks and next action

Backend feasibility remains unproven, especially typed adapter layouts, runtime linkage, recursive descriptor publication and the C++ allocation-failure path. These are honestly stated implementation-stage risks, not contradictions in this proposal.

The next action is to file this report and merge it with the independent axis verdict on the same tuple. Implementation requires subsequent operator authorization.
