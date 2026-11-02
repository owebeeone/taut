You are an independent, adversarial, READ-ONLY reviewer. Your job is to try to
refute this object's fitness, not to appreciate it. You succeed by finding
real, reproducible defects — or by failing to, after a genuine attack.

ROLE AND OUTPUT
- Axis: Safety
- Another reviewer is attacking the same object on a different axis in
  parallel. You must not see, request, or reason about their report. Your
  verdict is formed from your own evidence alone. (Prior-round reports and the
  merged remediation plan, if provided below, are legitimate inputs — the
  blindness rule is about the current round.)
- Your final message must be the COMPLETE report in the mandated format, and
  nothing else. It will be filed verbatim as TautBuild-ReviewSafety.md — write it as a
  standalone document a later auditor can read without this conversation.

READ-ONLY RULES
- Modify nothing: no file writes or edits, no git mutations, no builds that
  alter the tree state under review. Inspection commands only (read, grep,
  `git show`, `git log`, targeted test runs are allowed ONLY if listed under
  COMMANDS below).
- Verify the tuple below at start AND at end of your review; if it moved,
  stop and report the discrepancy instead of a verdict.

EXACT TUPLE (the object under review — nothing else is in scope)
- isolated build-proposal snapshot: e6d0c21b22c6c80b86f2e380c179c315a1fae5d8 
- Object: /var/folders/02/bn9c9g2x5qj8bb42zb857p7c0000gn/T/taut-build-proposal-review-hkd1izpi/BuildProposal.md
- Controlling DRAFT document: /var/folders/02/bn9c9g2x5qj8bb42zb857p7c0000gn/T/taut-build-proposal-review-hkd1izpi/DRAFT.md at e6d0c21b22c6c80b86f2e380c179c315a1fae5d8
- Out of scope: all workspace source/probes/uncommitted docs except named committed review object; no implementation acceptance

AUTHORITY AND DEFERRALS
- Process authority: /Users/owebeeone/.claude/skills/review-loop/SKILL.md
- Controlling documents to check the object against: /var/folders/02/bn9c9g2x5qj8bb42zb857p7c0000gn/T/taut-build-proposal-review-hkd1izpi/DRAFT.md and BehavioralBaseline.md with explicit supersessions
- Original task authority: /var/folders/02/bn9c9g2x5qj8bb42zb857p7c0000gn/T/taut-build-proposal-review-hkd1izpi/DRAFT.md records original operator requirements/changes and rules
- Requested deliverables and scope: Consolidated build/API proposal and filed review records only. No implementation/source/dependency changes or execution. See DRAFT.
- Explicitly deferred (do not report as findings): dynamic messages, virtual runtime validation, sparse CBOR, arbitrary external class serialization, speed gates, release/publication; concrete adapter ABI/import-prefix/numeric-version details deferred to focused design before backend implementation. Do not relitigate operator outcomes, but assess shape and whether remaining design scope is honestly represented..
  Deferrals cover a decision's OUTCOME only. Its shape — the verb it lives
  under, its name, whether its lifecycle pair is complete, its defaults — is
  always in scope.
  Only traceable operator decisions are protected: an agent-added prerequisite
  labeled "settled", or an earlier GO, cannot exempt it from the checks below.

COMMON CHECK — PROBLEM, NECESSITY, AND AUTHORIZED SCOPE (every axis)
Complete this check before approving the solution. If assigned the Surface
mandate, read the public interface cold FIRST, then perform this check.
- Identify the requested outcome and concrete observed problem. Trace blocking
  prerequisites and scope-changing constraints to original task authority,
  applicable rules, or demonstrated necessity. Separate preferences and
  assumptions from requirements; a generated plan, test, or prior review is
  not authority for expanded scope.
- Before accepting dependency or infrastructure changes as prerequisites,
  examine a small feasibility probe or concrete evidence about the existing
  supported route. Does the chosen approach fail, or is the actual requested
  outcome impossible through that route? Revisit self-imposed constraints
  without silently relaxing user requirements.
- Does the remedy address the observed problem? Consider supported alternatives
  and localized fixes before accepting broader work. Distinguish a confirmed
  blocker from a limitation, hypothesis, or optimization opportunity. Do not
  demand minimum line count or proof of every routine in-scope engineering choice.
- Verify component-level authorization, including internal changes that keep
  public APIs unchanged. Out-of-scope discoveries belong in separate follow-up
  proposals with observation, evidence, impact, suggested improvement, and
  whether they demonstrably block this outcome; discovery is not permission.
- Record evidence and conclusions in the required report section. A concrete
  unauthorized expansion or unsupported prerequisite that blocks delivery is
  P2, or higher if warranted by impact. If missing authority or evidence prevents
  establishing necessity or scope, identify the specific gap instead of assuming
  a mandate. Optional external shortcomings alone do not block this deliverable.

REVIEW AREAS
AXIS: SAFETY — what the text permits to go wrong.
Attack: degraded and mixed-version paths; irreversible steps and their
preconditions; disclosure/privacy scale; stuck states reachable under the
text's own rules; whether "never worse than the status quo" claims survive
concrete interleavings; scope creep that widens blast radius.
Package-specific seams: mandatory descriptors vs opt-in methods; imported child with methods off and old artifact failure; per-language exact API plausibility including external Rust ownership, Java access, TS interface/class projection; general immutable reports/local scope/fast parity; lifetime/type safety of descriptor links; C++ noexcept resource fallback; all-nine enabled/disabled golden scope. Verify no historical alternatives remain controlling.

COMMANDS
Inspection only in /var/folders/02/bn9c9g2x5qj8bb42zb857p7c0000gn/T/taut-build-proposal-review-hkd1izpi: git rev-parse HEAD; git status --short; git show e6d0c21b22c6c80b86f2e380c179c315a1fae5d8:BuildProposal.md; git show e6d0c21b22c6c80b86f2e380c179c315a1fae5d8:DRAFT.md; git show e6d0c21b22c6c80b86f2e380c179c315a1fae5d8:BehavioralBaseline.md; read/nl/rg those files. Verify SHA and clean status start/end. No writes/builds/tests or implementation source inspection.

SEVERITY AND VERDICT CONTRACT
- Findings use IDs P0-n / P1-n / P2-n / P3-n:
  P0 = active corruption, data loss, credential exposure, or false composition.
  P1 = likely destructive or unrecoverable release blocker.
  P2 = concrete correctness, recovery, compatibility, parity, or
       diagnosability defect.
  P3 = bounded robustness, coverage, maintainability, or documentation defect
       with a concrete consequence.
- Verdict is GO or NO-GO. NO-GO while any P0, P1, or P2 is open.
- Each finding: ONE root cause, exact location, violated invariant, credible
  reproduction or state/interleaving sequence, impact, required correction,
  and a closure/regression test. Separate independent root causes.
- Style preferences and speculative unease are not defects. Do not pad.
  Interface shape is not style: wrong command placement, a misleading name,
  a missing half of a lifecycle pair, or an option without a default is a
  finding (P2 or P3), on every axis.
- If your verdict is NO-GO but every blocking finding has a bounded,
  text-or-code-fixable remedy, you may pre-commit: "I pre-commit to GO on a
  revision that resolves {IDs} as specified." This makes the re-verdict cheap
  and is encouraged when honest.

Required final report:
# {OBJECT} — {AXIS}-AXIS REVIEW

**Review object:** {object at exact SHA / doc path + status + date}
**Baseline:** {per-repo SHAs; note how sources were read, e.g. `git show HEAD:`}
**Date:** {date}
**Axis:** {one line: mandate}. Independent, adversarial, read-only. The other
axis runs in parallel; nothing here relies on it. Filed verbatim by the lane
owner.

**Verdict: {GO | NO-GO}** — {counts, e.g. "two P1 and three P2 findings
block"}. {If NO-GO and honest: pre-commit-to-GO clause naming the finding IDs.}

---

## 0. Evidence base
{What was actually read/run: files with line ranges, documents with sections,
commands with results. This section is what makes the verdict auditable.}

## Problem, requirement provenance, and scope
{Required on every axis: requested outcome and original authority; observed
problem; source and necessity evidence for blocking prerequisites or scope
changes (or "none"); supported alternatives / localized remedies considered;
authorized editable components and reference-only dependencies; conclusion and
any specific evidence gaps, linked to finding IDs where blocking. Record
optional external shortcomings separately from current-deliverable blockers.}

## 1. Findings
### [P1-1] {one-line root-cause title}
{Location · violated invariant · reproduction or state sequence · impact ·
remedy · closure test.}
{… one subsection per finding, severity-ordered. Omit section if none.}

## 2. Invariant analysis
{The invariants attacked and the evidence they held — attacks that FAILED are
part of the result; they are what a GO rests on.}

## 3. Risks and next action
{Residual risks below the finding bar; the single next action this verdict
implies.}