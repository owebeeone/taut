# OneOf Proposal — SAFETY-AXIS REVIEW

**Review object:** `Proposal.md` at `02d2a66ae263a5bc143309d1f4de5801998c0712`, in `/var/folders/02/bn9c9g2x5qj8bb42zb857p7c0000gn/T/taut-oneof-proposal-review-4xo89oy3`. Clean snapshot, verified at start and end.
**Baseline:** Previous reviewed snapshot `8d7a8bff959a5711362a0aba107a62aaeee4a94a`. Revised proposal, unchanged controlling `DRAFT.md`, and `RemPlan-1.md` read using `git show` at the revised SHA.
**Date:** 2 November 2026
**Axis:** Safety: degraded paths, compatibility, data preservation, validation coverage and authorized scope. Independent, adversarial, read-only. The other axis runs in parallel; nothing here relies on its current report. Filed verbatim by the lane owner.

**Verdict: GO** — no P0, P1, P2 or P3 findings. The Safety GO continues on the revised tuple.

---

## Prior-finding closure table

| Prior Safety findings | Verification | Disposition |
| --- | --- | --- |
| None; initial Safety verdict was GO | Reviewed the complete committed revision, changed ranges and their traversal consequences | Continued GO |

`RemPlan-1.md` identifies a prior Consistency finding. Its originating reviewer owns formal closure; this report independently assesses the correction’s Safety consequences.

## Changed-range analysis

The three changed ranges clarify validator eligibility in section 1, define transitive eligibility in section 3, and add the required root-traversal acceptance case.

The revised rule distinguishes schema reachability, which determines whether an entry point exists, from populated runtime ownership, which determines actual traversal. A root with a local virtual group therefore cannot suppress validation of its populated non-virtual descendants.

The documented counterexample now has an explicit outcome:

1. Root’s virtual payload owns Child with a non-virtual oneof.
2. Root receives a validator because a non-virtual constraint is schema-reachable.
3. A populated Child missing its selected payload produces a root-relative issue; Root contributes a deferred virtual-group entry.
4. Repairing Child yields `is_valid() == true` and `is_complete() == false`.
5. Replacing Child’s schema with unconstrained scalar data removes the reachable non-virtual checks and consequently the standalone validator.

Ordinary wrappers, lists, maps and recursive schema references receive the same eligibility rule across all nine targets. Schema reachability must terminate on recursive types; runtime traversal retains its separate active-ancestor cycle handling.

The change neither infers a virtual discriminator nor validates virtual case selection or mutual exclusion. It also leaves constructor, mutation, codec and compatibility behavior unchanged. I found no new architectural root cause.

## 0. Evidence base

Read during this focused review:

- Committed `Proposal.md` at `02d2a66ae263a5bc143309d1f4de5801998c0712`, including normative sections 1–4 and the historical appendix.
- Committed `DRAFT.md` at the same SHA.
- Committed `RemPlan-1.md` at the same SHA.
- `git diff 8d7a8bff959a5711362a0aba107a62aaeee4a94a..02d2a66ae263a5bc143309d1f4de5801998c0712 -- Proposal.md`.

Process authority and workspace instructions were read in the initial review and remain applicable.

Before and after inspection, `git rev-parse HEAD` returned the revised required SHA and `git status --short` returned empty output. No files were changed. No implementation, tests, builds or current peer report were inspected.

## Problem, requirement provenance, and scope

The unchanged controlling draft requests a coherent oneof proposal: referenceable enum members, field-local Case declarations, independent virtual and exhaustive options, repairable invalid drafts, explicit report-returning validators across nine languages, and preservation of populated payloads during JSON serialization.

The remediation addresses a document-level eligibility ambiguity that could prevent callers from reaching already-required descendant checks. Generating a root entry point for reachable non-virtual constraints directly supports the requested explicit validation behavior. It does not turn deferred virtual validation into a prerequisite.

Authorization remains proposal and review/remediation documents only. Production/probe source, GARNS resolution, parser and external dependencies remain reference-only. No dependency or infrastructure change is required by this correction, and no such change was reviewed or performed.

The localized clarification is sufficient for this document deliverable. It preserves the existing owned-record construction model, traversal boundary and application-specific graph validation boundary. No unsupported prerequisite or unauthorized scope expansion was found.

## 2. Invariant analysis

The changed text survived the following attacks:

- **Local virtual groups concealing invalid descendants:** Eligibility now includes all owned schema-reachable non-virtual constraints, including those behind virtual payloads.
- **Repair being mistaken for complete validation:** The acceptance case explicitly retains Root’s deferred entry after Child is repaired.
- **Absent runtime children being fabricated or checked:** Existing traversal still visits populated owned records only. Schema eligibility does not require runtime payload population.
- **Recursive schemas preventing generator termination:** Reachability explicitly terminates on recursive types; runtime ownership cycles retain their distinct diagnostic rule.
- **Virtual traversal introducing virtual validation:** The added acceptance case explicitly excludes virtual selection and mutual-exclusion checks.
- **Traversal widening into application graph references:** Owned reachability remains subject to the existing prohibition on following application node-ID links.
- **Language-specific omission of root entry points:** The acceptance case expressly applies to all nine targets.

Unchanged protections remain intact: validators are observational, reports are immutable snapshots, codecs preserve populated inconsistent payloads, structural codec checks remain active, and compatibility dimensions remain separately classified.

## 3. Risks and next action

This remains a proposal review. Generator termination, runtime traversal and cross-language parity require future implementation evidence; this report does not establish those implementations.

The next action is for the lane owner to merge this continued Safety GO with the other axis’s focused verdict on `02d2a66ae263a5bc143309d1f4de5801998c0712`. No implementation, release or dependency change is authorized by this verdict.
