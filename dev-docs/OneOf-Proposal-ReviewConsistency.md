# Oneof proposal — CONSISTENCY-AXIS REVIEW

**Review object:** `/var/folders/02/bn9c9g2x5qj8bb42zb857p7c0000gn/T/taut-oneof-proposal-review-4xo89oy3/Proposal.md` at `8d7a8bff959a5711362a0aba107a62aaeee4a94a`; clean isolated snapshot.
**Baseline:** Proposal read through `git show 8d7a8bff959a5711362a0aba107a62aaeee4a94a:Proposal.md` and numbered file inspection; controlling `DRAFT.md` read from the same clean snapshot.
**Date:** 2 November 2026
**Axis:** Consistency and public Surface. Independent, adversarial, read-only. The other axis runs in parallel; nothing here relies on it. Filed verbatim by the lane owner.

**Verdict: NO-GO** — one P2 finding blocks. I pre-commit to GO on a revision that resolves P2-1 as specified.

---

## 0. Evidence base

Read:

- `Proposal.md`, lines 1–560. Public examples and sections 1–4 were read before the controlling draft. Sections 1–4 were treated as normative; appendix statements were treated as historical evidence.
- `DRAFT.md`, lines 1–7.
- `/Users/owebeeone/.claude/skills/review-loop/SKILL.md`, including scope/provenance checks, Consistency and Surface mandates, severity definitions and report requirements.
- Workspace `AGENTS_GWZ.md`.

Inspection commands:

- Start: `git rev-parse HEAD` returned `8d7a8bff959a5711362a0aba107a62aaeee4a94a`; `git status --short` returned no entries.
- `git show 8d7a8bff959a5711362a0aba107a62aaeee4a94a:Proposal.md` supplied the committed proposal.
- End: the same SHA and empty status were confirmed.

No implementation, probe source, peer report, tests or builds were inspected or run. Nothing was modified.

## Problem, requirement provenance, and scope

The requested outcome is a coherent proposal for generic field-local oneof declarations and explicitly invoked validation across all nine targets. The concrete design problem is expressing discriminator/payload associations without repeated manual maps while preserving mutable invalid drafts, serialization before validation, repair and later revalidation.

`DRAFT.md:4` supplies the operator requirements: referenceable enum objects, qualified member references, field-local Case, discriminator storage modes, exhaustive coverage behavior, explicit reports, JSON omission based on non-null presence, preservation of invalid populated fields and unchanged CBOR. `DRAFT.md:5` distinguishes lane-owner choices—including report completeness and traversal machinery—from operator mandates.

The authorized editable boundary is proposal and review/remediation documents only. Production/probe source, GARNS resolution, parser code and external dependencies remain reference-only. No dependency or infrastructure change is asserted as a prerequisite to this document deliverable. Historical probe claims were not treated as proof of production completion.

The proposal generally addresses the requested problem within that boundary. A localized clarification to validator generation, described in P2-1, is sufficient; no implementation or dependency expansion is necessary. Virtual runtime validation remains deferred. The finding concerns traversal of non-virtual descendants, not reconsideration of that deferral.

## 1. Findings

### [P2-1] Unconditional virtual-only validator suppression removes validation of non-virtual descendants

**Location:** `Proposal.md:64–67` and `281–287`, conflicting with `290–297`.

**Violated invariant:** An explicit validator traverses all populated owned nested records and reports their non-virtual oneof failures. Deferring a virtual group must not suppress independent non-virtual checks inside its populated payloads.

**Reproduction:**

1. Define `Child` with a stored, non-virtual oneof.
2. Define `Root` whose only local group is virtual, with a Case payload containing an owned `Child`.
3. Populate that child with a known discriminator and a missing selected payload.
4. Ask to validate `Root`.

Lines 64–65 unconditionally say no validator is generated for a virtual-only message; lines 286–287 repeat the absence of a standalone validator. `Root` fits that local description. Consequently, the caller has no root validator through which to obtain the child failure or the root group’s deferred entry.

Conversely, generating a root validator that traverses the child satisfies lines 290–297 but contradicts the unconditional suppression rule. The text does not define “virtual-only” transitively or exempt messages containing non-virtual descendant constraints.

**Impact:** The proposed public surface is inconsistent for a supported nested schema shape. Backends can reasonably diverge between omitting the root entry point and generating it. Calling the child validator manually cannot produce the root-relative report and deferred coverage described by the proposal.

**Required correction:** Define validator eligibility using reachable owned constraints, including through virtual payloads, ordinary wrappers and containers. Restrict validator omission to messages whose reachable owned contents contain no checks eligible for this cut, or state another explicit rule that preserves root-level traversal of non-virtual descendants. Keep the virtual group itself deferred and do not infer its discriminator.

**Closure/regression test:** Add a proposal acceptance case with a virtual local group owning a non-virtual constrained child. Require a root entry point that:

- Reports the child’s missing selected payload at its root-relative path.
- Includes the encountered virtual group in `deferred_checks`.
- After child repair, returns `is_valid() == true` and `is_complete() == false`.
- Preserves the existing deliberate behavior for a genuinely virtual-only message with no reachable non-virtual checks.

Verify the corrected normative clauses select this behavior consistently across all nine targets.

## 2. Invariant analysis

The following attacks did not produce additional findings:

- **Authoring and grouping:** The primary example associates the enum object, explicit controlling field and field-local Case. Grouping is by discriminator field, so two fields using the same enum do not merge. Duplicate ownership and wrong enum membership are rejected.
- **Option defaults:** Both `virtual` and `exhaustive` have explicit Boolean defaults of False. Coverage and storage are independent. Exhaustive mode requires payload nominations; permissive mode supplies payload-free choices without free-hanging Case.
- **Invalid-draft lifecycle:** Existing mutable records remain constructible. Constructors, mutations and codecs do not invoke semantic validation. Invalid populated payloads survive serialization; repair and repeated explicit calls remain possible.
- **Presence:** Zero, false, empty strings and empty collections are present. JSON omits absent Case payloads, accepts omitted or explicit-null inputs, and preserves multiple populated payloads. Dense CBOR is explicitly unchanged.
- **Reports and repair:** Invalid data returns issues rather than a validation exception. Reports are immutable snapshots, validation is observational and later mutation requires a new call. Validity and completeness are distinguished for encountered virtual groups.
- **Traversal:** Apart from P2-1’s entry-point problem, ordering and scope are coherent: independent groups continue after an invalid discriminator; populated selected and nonselected children are traversed; ordinary fields and containers participate; application node-ID links are not ownership edges. Active-ancestor cycle detection preserves diagnostics for shared objects reached through different paths.
- **Compatibility:** Runtime/wire field removal, nullable presence changes, JSON projection and validation acceptance are distinguished. New rules must survive neutral IR, and old tools must not silently discard them.
- **Nine-language surface:** All nine targets are named and bound to equivalent semantics. Target-appropriate module/function/static-class forms are permitted without requiring a language-specific sum-type rewrite. Exact type names are expressly provisional.
- **Historical evidence:** The appendix’s single-group, selected-child-only and Rust/Python probe limits do not override current production requirements. Its coverage-switch revision explicitly supersedes the earlier strict-coverage experiment.

## 3. Risks and next action

Exact report names and IR layout remain acknowledged design decisions, appropriate to this proposal stage. Historical test claims were not independently verified because implementation and test execution are outside this review’s scope.

The next action is a bounded proposal-text correction for P2-1, followed by a focused re-verdict against a new settled snapshot.
