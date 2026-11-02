# OneOf Proposal — SAFETY-AXIS REVIEW

**Review object:** `Proposal.md` at `8d7a8bff959a5711362a0aba107a62aaeee4a94a`, in `/var/folders/02/bn9c9g2x5qj8bb42zb857p7c0000gn/T/taut-oneof-proposal-review-4xo89oy3`. Clean snapshot, verified at start and end.
**Baseline:** Isolated proposal snapshot and its controlling `DRAFT.md` at the same SHA. Sources read with numbered file inspection after verifying HEAD and clean status.
**Date:** 2 November 2026
**Axis:** Safety: degraded paths, compatibility, data preservation, validation coverage and scope. Independent, adversarial, read-only. The other axis runs in parallel; nothing here relies on it. Filed verbatim by the lane owner.

**Verdict: GO** — no P0, P1, P2 or P3 findings.

---

## 0. Evidence base

Read:

- Canonical `OneOf-Proposal-PromptSafety.md`.
- `/Users/owebeeone/.claude/skills/review-loop/SKILL.md`.
- Workspace `AGENTS_GWZ.md`.
- Snapshot `DRAFT.md`, lines 1–7.
- Snapshot `Proposal.md`, lines 1–560: sections 1–4 as the current contract; appendix as historical evidence only.

Executed `git rev-parse HEAD` and `git status --short` against the isolated snapshot before and after review. Both checks returned the required SHA and empty status. No files were changed, no tests or builds were run, and no implementation or peer report was inspected.

## Problem, requirement provenance, and scope

The controlling draft authorizes proposal review and amendment only. Its requested outcome is a coherent generic oneof proposal with referenceable enum members, field-local Case declarations, independently controlled virtual storage and exhaustive coverage, repairable invalid drafts, explicit report-returning validation, and JSON omission of absent payloads across nine target languages.

The concrete design problem is that oneof relationships and validation must be expressible without forcing immediate validity or losing inconsistent draft data. The proposed nullable payload slots, explicit discriminator association and observational validators address that problem.

The editable boundary belongs to the lane owner: the Taut proposal and review/remediation documents. Production/probe source, GARNS resolution, parser and external dependencies remain reference-only. This review made no changes.

No dependency or infrastructure modification is made a prerequisite for completing this document review. A native versioned IR extension is proposed for eventual production constraints, with rejection of unsupported rules and preservation of existing output for unannotated schemas. That is an implementation design choice within the proposed Taut feature, not authorization to modify dependencies now.

Localized alternatives were considered against the contract: retaining dense CBOR avoids expanding the JSON requirement into another format decision; keeping ordinary records and explicit validators avoids imposing a replacement construction model; separating graph-reference checks preserves the Taut/GARNS ownership boundary.

Historical probe limitations do not establish production acceptance and are expressly labelled accordingly. No unsupported prerequisite or unauthorized component expansion was found.

## 2. Invariant analysis

The following attacks did not establish a defect:

- **Draft data loss during encoding:** A mismatched discriminator or several populated payloads cannot authorize selecting a winner. Lines 199–204 require preserving every populated payload. Zero, false, empty strings and empty collections remain present under lines 173–177. Missing selected payloads remain absent and repairable.

- **Validation blocking draft recovery:** Lines 159–169 and 220–237 separate construction, mutation and codecs from semantic validation. Validation is observational; later mutation requires another call. Existing structural codec rejection remains explicit, so the draft-serialization promise does not silently disable primitive, enum or wire checks.

- **Virtual checks masquerading as completed validation:** Lines 64–68 explicitly defer virtual runtime validation. Lines 281–288 require deferred entries during containing-record traversal and distinguish validity in the checked scope from completeness. Virtual-only messages have an explicit no-validator boundary.

- **Coverage changing runtime storage or virtual behavior:** Lines 85–100 separate schema coverage from runtime presence. Exhaustive coverage applies to virtual groups without enabling their deferred runtime checks. Unmatched known members select payload-free cases only under non-exhaustive coverage.

- **An invalid discriminator concealing unrelated errors:** Lines 290–297 require continuing other groups and populated nested records after an absent or wrong discriminator. Populated nonselected payloads still undergo nested validation. Selection-dependent checks alone are skipped.

- **Traversal silently missing ordinary wrappers or shared children:** The traversal includes ordinary owned fields and list/map elements, not just selected payloads. Shared owned objects produce diagnostics at each path. Active-ancestor cycle detection reports the back edge and continues independent branches; it does not use a global visited set to suppress other paths.

- **Graph links amplifying traversal or widening authority:** Lines 297 and 314–327 distinguish owned edges from application node-ID references. Graph-index checking remains application-specific. The graph-level once-per-owned-node instruction is separate from local owned-path reporting.

- **Mixed-version loss of constraints or unacknowledged compatibility changes:** Lines 153–155 prohibit silently dropping rules in old IR. Lines 331–344 distinguish JSON projection, CBOR wire, generated API and validation-contract changes. Stored-to-virtual conversion and newly nullable payload slots are explicitly classified as compatibility changes.

- **Partial language rollout being treated as completion:** Lines 211–218 require equivalent JSON and validation behavior across Python, TypeScript, JavaScript, Rust, C++, Go, Java, Kotlin and Swift. Historical Rust/Python evidence is not presented as completing that requirement.

These conclusions assess the proposed contract, not implementation conformance.

## 3. Risks and next action

Production multi-language behavior, resource handling and compatibility-gate implementation remain unverified. Those are declared future implementation obligations, not defects in this proposal-only deliverable. Sparse CBOR and virtual runtime validation remain explicitly deferred.

The next action is for the lane owner to merge this independent GO with the other axis’s verdict at the same snapshot. This verdict authorizes no implementation, release, dependency change or workspace mutation.
