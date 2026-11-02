You are an independent, adversarial, READ-ONLY reviewer. Your job is to try to
refute this object's fitness, not to appreciate it. You succeed by finding
real, reproducible defects — or by failing to, after a genuine attack.

ROLE AND OUTPUT
- Axis: State
- Another reviewer is attacking the same object on a different axis in
  parallel. You must not see, request, or reason about their report. Your
  verdict is formed from your own evidence alone. (Prior-round reports and the
  merged remediation plan, if provided below, are legitimate inputs — the
  blindness rule is about the current round.)
- Your final message must be the COMPLETE report in the mandated format, and
  nothing else. It will be filed verbatim as PythonOneOfCheckpoint-ReviewState.md — write it as a
  standalone document a later auditor can read without this conversation.

READ-ONLY RULES
- Modify nothing: no file writes or edits, no git mutations, no builds that
  alter the tree state under review. Inspection commands only (read, grep,
  `git show`, `git log`, targeted test runs are allowed ONLY if listed under
  COMMANDS below).
- Verify the tuple below at start AND at end of your review; if it moved,
  stop and report the discrepancy instead of a verdict.

EXACT TUPLE (the object under review — nothing else is in scope)
- taut HEAD 2cfee5d6156b0179066dc4eed70f60cde489a422; taut-shape-py HEAD da79bfb74376802edcd25049ed4ce29de814db44. Uncommitted source inventory digest af9f2516f0dcbf45853fb6ade39d207c7a84b6b282975bffa8fdd385b59cc996, 165 files, at D:/projects/limbo/taut-dev/taut/dev-docs/PythonOneOfCheckpoint-Snapshot.json. User prohibits commits; this hash tuple is authoritative.
- Object: Python reference implementation only, files listed in snapshot. Other backend source is reference/regression only; unchanged.
- Controlling DRAFT document: D:/projects/limbo/taut-dev/taut/dev-docs/PythonOneOfCheckpoint-Draft.md (hash in snapshot)
- Out of scope: generated bundles/wheel/results/scratch and review artifacts are evidence outside code digest; no other backend implementation or releases; known baseline failures documented with isolated HEAD proof.

AUTHORITY AND DEFERRALS
- Process authority: C:/Users/gianni/.codex/skills/review-loop/SKILL.md; applicable taut-dev/AGENTS.md, AGENTS_GWZ.md, component AGENTS.md. No local AgentProcessRules.md exists.
- Controlling documents to check the object against: D:/projects/limbo/taut-dev/taut/dev-docs/OneOf-ExplicitValidation-BuildProposal.md (full Python sections 2-8); behavioral proposal referenced therein; D:/projects/limbo/taut-dev/taut/dev-docs/examples/python-oneof/README.md.
- Original task authority: Original operator: implement complete Python reference batch through native model/IR/compiler, mandatory shared immutable descriptors, optional thin methods, one shared descriptor-driven local/recursive report/Boolean engine, sparse oneof JSON, no implicit validation, canonical source/package runtime and shape-library migration; stop before other backend implementation. Production authorization supersedes older documentation-only proposal language. Use saved Limbo directly, no worktree. No commits/pushes/tags/releases/toolchain changes. Concrete unchanged-HEAD evidence required for remaining regression failures, no double counting test totals.
- Requested deliverables and scope: Complete tested Python batch; taut canonical runtime/compiler/tests, necessary taut-shape-py generated-fact/foundation integration, executable examples and honest report. Remaining eight backends are reference-only. Inspect actual code against the full authority, not claims/tests alone.
- Explicitly deferred (do not report as findings): Virtual group selection/mutual exclusion is deferred and must be incomplete; other language new features; application graph ID/reference rules; releases/commits. Missing unrelated baseline doc and unchanged Windows Go newline tests do not block if proven unchanged and no new Python regressions. No exemption for Python API/CLI shape..
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
AXIS: STATE — durable-state semantics and adversity. Attack gen/python_runtime.py and scaffold write planning, owner/user manifests, filesystem/preflight failure atomicity, locks across roots, stale cleanup with shared source consumers, source/package and validation transitions, unknown/modified/legacy files, duplicate runtime owners. Also examine immutability/snapshots, cycles/independent branches and fail-closed descriptor/configuration errors; unsupported rules/versions must not become false successful reports. Runtime multi-file crash rollback is not promised: interrupted writes may fail closed requiring fresh output/migration, but no user data loss or invented ownership. Distinguish concrete defect from scope expansion.

COMMANDS
Working directory D:/projects/limbo. Read/rg/Git diff/show are allowed (use command-local -c safe.directory for the repository). Start and end with:
python -B taut-dev/taut/dev-docs/examples/python-oneof/review_snapshot.py --check taut-dev/taut/dev-docs/PythonOneOfCheckpoint-Snapshot.json
Before Python application/CLI probes, dot-source D:/projects/limbo/toolchain-readiness-2026-11-02/Activate-TautToolchains.ps1 (selects stable Python and sets PYTHONPATH to current src). Do not use the installed baseline taut package. For pytest add C:/Users/gianni/AppData/Local/Programs/Python/Python311/Lib/site-packages to PYTHONPATH; set PYTEST_DISABLE_PLUGIN_AUTOLOAD=1.
Explicitly permitted scratch generation walkthroughs/in-memory probes and focused pytest tests: src/tests/test_oneof.py and src/tests/test_python_runtime_distribution.py, with --basetemp D:/projects/limbo/taut-dev/taut/dev-docs/examples/python-oneof/scratch/review-state. All probe outputs must stay under scratch/review-state, excluded from the source digest. No source edits. Cold Surface help command: python -B -m taut.cli gen --help. Inspect actual logs: feature 105 passed, shape 190 passed, core 809 passed, parity 16 GREEN; baseline-evidence.json proves prior failure classification. No broad-suite rerun or wheel rebuild is needed.

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

Use this exact report structure (fill placeholders):
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
{Location Â· violated invariant Â· reproduction or state sequence Â· impact Â·
remedy Â· closure test.}
{… one subsection per finding, severity-ordered. Omit section if none.}

## 2. Invariant analysis
{The invariants attacked and the evidence they held — attacks that FAILED are
part of the result; they are what a GO rests on.}

## 3. Risks and next action
{Residual risks below the finding bar; the single next action this verdict
implies.}