# Oneof proposal — CONSISTENCY-AXIS RE-REVIEW 1

**Review object:** `/var/folders/02/bn9c9g2x5qj8bb42zb857p7c0000gn/T/taut-oneof-proposal-review-4xo89oy3/Proposal.md` at `02d2a66ae263a5bc143309d1f4de5801998c0712`; clean isolated snapshot.
**Baseline:** Original review at `8d7a8bff959a5711362a0aba107a62aaeee4a94a`. Revised proposal and remediation plan read using `git show 02d2a66ae263a5bc143309d1f4de5801998c0712:`; committed proposal diff inspected.
**Date:** 2 November 2026
**Axis:** Focused Consistency and Surface re-verdict. Independent, adversarial, read-only. No current-round peer report was accessed. Filed verbatim by the lane owner.

**Verdict: GO** — P2-1 is closed; no open findings or new architectural root causes identified. This accepts proposal coherence only.

---

## Prior-finding closure table

| Finding | Original counterexample re-run | Evidence | Disposition |
| --- | --- | --- | --- |
| P2-1: Unconditional virtual-only validator suppression removes validation of non-virtual descendants | Root has only a local virtual group whose populated payload owns Child with a non-virtual oneof and a missing selected payload. Root must expose a validator, report the child failure at its root-relative path and record the virtual group as deferred. After repair, validity is true and completeness remains false. A scalar-only virtual root still has no standalone validator. | `Proposal.md:64–69` qualifies suppression; `288–295` defines transitive eligibility; `329–339` states the complete acceptance case and all-nine-target application. | **Closed** at the proposal-text level. No implementation test was authorized or performed. |

## Changed-range analysis

The patch changes two normative omission clauses and adds a root-traversal acceptance case.

Validator eligibility now depends on reachable owned non-virtual constraints, including through virtual payloads, ordinary fields, lists and maps. Schema reachability must terminate on recursive types. This removes the original contradiction with traversal of all populated owned descendants.

The revision preserves virtual runtime validation deferral: it introduces no virtual discriminator inference, case selection or mutual-exclusion check. Purely virtual reachable schemas retain the deliberate absence of a standalone validator.

I classify this as a bounded clarification of the existing traversal contract, not a new architectural root cause. It does not change construction, mutation, codec behavior, graph-link ownership, compatibility policy or report semantics.

## 0. Evidence base

Read:

- Committed revised `Proposal.md`, all sections, with focused numbered inspection of lines 60–76 and 279–344.
- Committed `RemPlan-1.md`, including its disposition and closure test for Consistency P2-1.
- Unchanged controlling `DRAFT.md`.
- The committed proposal diff from `8d7a8bff959a5711362a0aba107a62aaeee4a94a` to `02d2a66ae263a5bc143309d1f4de5801998c0712`.

The original review’s process-authority reading and cold public-surface inspection remain applicable. The remediation plan’s summary of the prior-round Safety verdict was legitimate prior-round input; no current peer report was read.

At both start and end:

- `git rev-parse HEAD` returned `02d2a66ae263a5bc143309d1f4de5801998c0712`.
- `git status --short` returned no entries.

No implementation, tests, builds or dependency sources were inspected. Nothing was modified.

## Problem, requirement provenance, and scope

The operator requests a coherent proposal for field-local generic oneof declarations, explicitly invoked reports across all nine targets, repairable invalid drafts and JSON omission of absent payloads. `DRAFT.md:4` supplies these requirements and explicitly defers virtual validation while preserving CBOR.

P2-1 concerned an internal inconsistency between validator suppression and the proposal’s existing owned traversal obligation. The correction is localized to the proposal and its acceptance case. It requires no dependency or infrastructure work and does not treat historical probe limitations as delivery prerequisites.

Authorized editable components remain proposal and review/remediation documents. Production/probe source, GARNS resolver, parser and external dependencies remain reference-only. The revision stays within that boundary. Report completeness and traversal details remain evaluated design choices, not newly attributed operator mandates.

No outside-scope shortcoming was established as a blocker.

## 2. Invariant analysis

The original counterexample now has one consistent outcome:

1. Root receives a validator because Child supplies a reachable non-virtual constraint.
2. The populated virtual payload is traversed without selecting or validating the virtual group.
3. Child’s missing selected payload produces a root-relative issue.
4. Root’s virtual group produces a deferred entry.
5. Repairing Child clears the issue while preserving incomplete coverage.
6. Removing reachable non-virtual constraints restores standalone-validator omission.

The generalized wording also covers ordinary wrappers, container elements and recursive schema references. Runtime traversal remains limited to populated contents; schema eligibility is determined independently of a particular draft’s population.

Unchanged invariants remain supported by the original review: explicit Boolean defaults, field-based grouping, field-local Case ownership, coverage/storage independence, non-null presence, preservation of invalid populated data, observational report snapshots, deterministic traversal, graph-link separation and distinct compatibility classifications. Historical probe limits remain subordinate to normative sections 1–4.

## 3. Risks and next action

Implementation correctness and production parity remain unverified and outside this gate. Exact report names and neutral-IR layout remain declared design decisions.

The next action is for the lane owner to merge the two focused verdicts and record acceptance if both report GO on this exact snapshot.
