# Taut Build Proposal — SAFETY-AXIS REVIEW

**Review object:** `/var/folders/02/bn9c9g2x5qj8bb42zb857p7c0000gn/T/taut-build-proposal-review-hkd1izpi/BuildProposal.md` at `e6d0c21b22c6c80b86f2e380c179c315a1fae5d8`. DRAFT; proposal-only review. Snapshot clean at start and end.

**Baseline:** `BuildProposal.md`, `DRAFT.md` and `BehavioralBaseline.md` in the same isolated commit. Read their working-tree contents with numbered inspection commands, bracketed by clean-status and exact-HEAD verification. No production repository revision or implementation is accepted by this review.

**Date:** 2 November 2026

**Axis:** Safety — degraded paths, mixed-version compatibility, lifetime/type safety, incomplete validation, resource failure, regeneration and authorized scope. Independent, adversarial, read-only. The other axis runs in parallel; nothing here relies on it. Filed verbatim by the lane owner.

**Verdict: GO** — zero P0, P1, P2 or P3 findings. This accepts the consolidated proposal’s coherence on this axis, not implementation correctness, adapter ABI readiness or release fitness.

---

## 0. Evidence base

Read:

- `BuildProposal.md`, lines 1–589: authority and supersessions; schema behavior; descriptor model/publication; dependency handling; reports and traversal; C++ fallback; all nine language projections; distribution/migration; conformance gates; remaining design work.
- `DRAFT.md`, lines 1–11: recorded operator requirements, proposal-only gate, explicit deferrals, editable components and process boundaries.
- `BehavioralBaseline.md`, lines 1–623: normative oneof and observational-validation semantics, traversal amendment, ownership/compatibility separation, historical probe limitations and mandatory-descriptor amendment.
- `/Users/owebeeone/.claude/skills/review-loop/SKILL.md`: independent review, requirement provenance, severity and verdict rules.
- Applicable workspace `AGENTS_GWZ.md`.

Verification commands, run at both review boundaries inside the isolated snapshot:

- `git rev-parse HEAD` returned `e6d0c21b22c6c80b86f2e380c179c315a1fae5d8`.
- `git status --short` returned no entries.

No files were changed. No builds, tests, probes or implementation inspections were performed. No current peer report was accessed.

## Problem, requirement provenance, and scope

The requested outcome is one coherent Python-first, all-nine-language build/API proposal. The concrete design problem is carrying native oneof rules through ordinary generation while allowing invalid mutable drafts, explicit validation, portable diagnostic reports and separately generated dependencies.

The recorded operator authority is `DRAFT.md:5`. It supports mandatory descriptors, optional instance methods, shared general reports, selectable local/recursive scope, Boolean fast checks, C++ noexcept behavior, known imported Taut types and enabled/disabled goldens. The proposal’s supersession table at `BuildProposal.md:24–34` makes the consequential changes explicit rather than treating earlier acceptance as authority for them.

Current editable scope is documentation and its review records only (`DRAFT.md:9`; `BuildProposal.md:19–22`). Taut source, generated artifacts, probes, GARNS resolver/parser, external dependencies and release configuration remain reference-only. Future Python implementation is expressly conditioned on document acceptance and operator approval (`BuildProposal.md:527–538`).

No dependency or infrastructure change is imposed as a prerequisite for this documentation deliverable. The proposal retains the existing compiler/emit route, supported language baselines and direct access mechanisms. It requires testing the existing Android route before demanding infrastructure changes (`BuildProposal.md:565–567`). Earlier probes are identified as limited evidence, not proof that the consolidated contract works (`BuildProposal.md:585–589`).

The proposal considers bounded alternatives: compatible typed adapters for older dependencies, source vendoring or a supported runtime library, and fresh output directories when stale-file ownership cannot be established. It neither requires dependency regeneration automatically nor authorizes broader Java projection, reflection, common message inheritance or dependency changes.

No blocking authority or necessity gap was identified. Concrete adapter layouts, import-prefix configuration and numeric contract versions remain openly deferred to focused design before backend implementation. Those deferrals are compatible with this gate and do not conceal an implementation acceptance claim.

## 2. Invariant analysis

The following attacks did not produce a proposal-level defect:

- **Enabled parent with disabled child.** Mandatory metadata exists in both modes, and recursive traversal uses descriptors/adapters rather than optional child methods (`BuildProposal.md:73–83`, `201–219`, `514–517`). The required independently generated dependency corpus includes this combination (`562–564`).

- **Old or incompatible child mistaken for a valid leaf.** Missing descriptors, incompatible versions and invalid links must fail explicitly before recursive validation is claimed. Local requests do not erase compiled recursive dependencies (`152–165`, `215–219`, `510–517`). No silent-success fallback is permitted.

- **Dangling, mismatched or recursively expanded descriptor links.** Metadata must be immutable, links validated before publication, recursive references stable or lazy, and references longer-lived than their uses. Typed adapters must preserve the value/descriptor/lifetime pairing (`130–165`). These are substantive constraints for the deferred ABI work.

- **Incomplete validation presented as success.** Report validity and completeness are separate; Boolean success requires both. Encountered virtual groups produce deferred entries, including virtual-only records. Local exclusion is explicitly scoped rather than represented as whole-tree coverage (`242–269`).

- **Invalid discriminator hiding independent failures.** Selection-dependent checks alone are skipped. Independent rules and populated children, including nonselected payloads, remain traversed (`271–285`). Shared objects produce per-path diagnostics; active-ancestor detection prevents ownership cycles from becoming successful omissions.

- **Stale results after draft repair.** Reports own immutable snapshots, retain no mutable input references and do not freeze or repair inputs (`242–249`, `271–274`). Mutation and snapshot behavior are required corpus cases (`554–555`).

- **C++ allocation failure causing termination through a superficial noexcept wrapper.** The proposal expressly prohibits that wrapper approach. It specifies false for the fast path and an allocation-free report fallback with invalid/incomplete status, static or inline storage, suitable read-only ranges and allocation-fault verification (`288–298`). Physical implementation remains unproven but the required behavior is coherent.

- **Language ownership/access shortcuts broadening scope.** Rust external inherent methods remain the type owner’s responsibility (`345–347`). Java preserves its existing visibility boundary (`387–389`). TypeScript distinguishes disabled interfaces from opted-in concrete classes and does not fabricate nested values (`408–435`). No common message base or reflective discovery is introduced to bypass these constraints.

- **Mode changes deleting handwritten content or leaving enabled artifacts masquerading as disabled output.** Fresh directories are required for mode goldens. Regeneration removes only positively identified generator-owned files; otherwise it reports stale output and requires a fresh directory (`569–573`).

- **Historical alternatives remaining controlling.** Current mandatory descriptors, methods on every enabled message, instance entry points and deliberate disabled-output migration are explicit supersessions. Historical probes are not presented as current implementation evidence.

All-nine completion requires compiled/imported executable tests, common portable assertions, both generation modes and dependency compatibility cases (`540–567`). This prevents Python/Rust probe success or generated text alone from satisfying the stated completion gate.

## 3. Risks and next action

The chief residual risk is implementation feasibility at each target’s typed-access and linkage seam. Concrete adapter layouts, configured imports, recursive publication mechanics and contract numbers still need focused design and evidence before backend implementation. C++ fault handling and mixed-mode dependency traversal particularly require the specified executable checks.

These are acknowledged future obligations, not defects in this proposal-only object. No separate external shortcoming was established by this document-only inspection.

**Next action:** file this report verbatim and merge the two independent verdicts for the same snapshot. This GO grants no implementation, dependency, version, publication or release authorization.
