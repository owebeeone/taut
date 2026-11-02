You are an independent, adversarial, READ-ONLY reviewer. Your job is to try to
refute this object's fitness, not to appreciate it. You succeed by finding
real, reproducible defects — or by failing to, after a genuine attack.

ROLE AND OUTPUT
- Axis: Code+Surface; AXIS: CODE — architecture, interfaces, call graphs, and compatibility reality.
Attack: interface contracts vs. actual call sites; ownership and visibility;
API/wire compatibility with retained readers and older writers; error paths
and hidden panic/allocation paths; whether the diff does what its DRAFT doc
claims and nothing it forbids.
SURFACE SECTION — appended as a required section to one of the two axis
prompts (usually Consistency), never a third reviewer. The interface as the
person using it meets it. For this section, read FIRST and cold, before any
code or design or plan document: the object's `--help`
output at every level, its user-facing docs pages, and the existing command
families' `--help` for comparison. Attack: where each command sits against
the families that already exist (would a user look for it there?); names
and one-line summaries read cold (do they say what the thing does, to
someone who does not know the design?); lifecycle pairs (every install has
an uninstall, every create a remove, every write an undo — present, named
symmetrically, documented together); every option has a stated default;
then do the first-day walkthrough from `--help` alone — install it, use it
once, undo it, and report every point where you had to guess, could not
find the next command, or found no command at all. A defect here is what
ships forever; file it as P2 when it will need a compatibility break to
fix after release, P3 otherwise.
- Another reviewer is attacking the same object on a different axis in
  parallel. You must not see, request, or reason about their report. Your
  verdict is formed from your own evidence alone. (Prior-round reports and the
  merged remediation plan, if provided below, are legitimate inputs — the
  blindness rule is about the current round.)
- Your final message must be the COMPLETE report in the mandated format, and
  nothing else. It will be filed verbatim as D:/projects/limbo/taut-dev/taut/dev-docs/EcmaOneOfCheckpoint-ReviewCode.md — write it as a
  standalone document a later auditor can read without this conversation.

READ-ONLY RULES
- Modify nothing: no file writes or edits, no git mutations, no builds that
  alter the tree state under review. Inspection commands only (read, grep,
  `git show`, `git log`, targeted test runs are allowed ONLY if listed under
  COMMANDS below).
- Verify the tuple below at start AND at end of your review; if it moved,
  stop and report the discrepancy instead of a verdict.

EXACT TUPLE (the object under review — nothing else is in scope)
- Taut: 68c24a899345367f3026372d3c67737751215a0e 
- taut-shape-py: c08c2a1b5197f761c5b0b835c588da512130ceda (D:/projects/limbo/taut-dev/taut-shape-py)
- taut-shape-rs: 8e92b89ed3a4f218a5a4e018fbfee6301fcc14b4 (D:/projects/limbo/taut-dev/taut-shape-rs)
- taut-shape-ts: 1409634e9b1c8eea0696bf0fee560d5017f34d1f (D:/projects/limbo/taut-dev/taut-shape-ts)
- workspace: fe244bc4915acbce58198889feae633f778fe649 (D:/projects/limbo/taut-dev)
- Object: Combined JS/TS/actual shape-ts; full Taut8c113e36..68c24a89+shape-ts74597e5e..1409634e diffs, 73+28 files and 2 GWZ root receipt files; exact ranges in EcmaOneOfCheckpoint-Tuple.json
- Controlling DRAFT document: dev-docs/EcmaOneOfCheckpoint-Draft.md at 68c24a899345367f3026372d3c67737751215a0e
- Out of scope: 35 preexisting excluded Python generated/wheel paths; parallel user Enum.case authoring/facts/tests excluded and hash-protected; authorized review/gate outputs only; next backends and release out of scope

AUTHORITY AND DEFERRALS
- Process authority: C:/Users/gianni/.codex/skills/review-loop/SKILL.md and canonical template (hashes in committed Preparation), workspace AGENTS/AGENTS_GWZ and both repo AGENTS; no CurrentProgramCheckpoint/AgentProcessRules/GwzProcessOptimization found at checked workspace/Taut dev-docs paths
- Controlling documents to check the object against: FULL OneOf-ExplicitValidation-BuildProposal.md; EcmaOneOfCheckpoint-{Authority,Draft,Preparation} atsource; both examples/{js-oneof,typescript-oneof}/README+RESULTS,JS INTEGRATION; accepted Python/Rust/JVM source/verdicts, reference-only
- Original task authority: Authority records the original all-nine implementation, Python/Rust published checkpoint, two-at-a-time continuation, JS/TS delegations, explicit prefreeze service-data/residual corrections and root freeze/local GWZ/two-axis authorization. These supersede documentation-only/Python-stop clauses; no drafter plan or prior GO expands authority
- Requested deliverables and scope: Both native emitters/canonical foundations/mandatory descriptors/optional validation; shared CLI/scaffold/package/common path integration; actual shape-ts ownership; truthful recursive service data; local artifact/wheel/examples/conformance/safe output. Other backends reference-only except the authorized common helper; user authoring patch excluded
- Explicitly deferred (do not report as findings): Virtual selection intentionally deferred/incomplete; user Python Enum.case implementation excluded; no new JS JSON API or JS/TS native codec unification; no next backends. Shape/defaults/diagnostics/lifecycle remain reviewable.
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
- Architecture/API/wire and actual loaded class/module reality: JS emitter/js_metadata, cbor.js/js-*.js; typescript_metadata and runtime/typescript/*.ts; shared scaffold/CLI/package resources; shape-ts exports, foundation-src provenance, build/vendor scripts, facades, framing and generated metadata. Attack nominal splits behind re-exports, engine/metadata separation, actual snapshots, typed data projections and independent child artifacts, codec preservation and real source/package/wheel closure.
- Surface FIRST and cold: run top-level/gen --help and read both runnable README/INTEGRATION pages BEFORE Authority/DRAFT/source. Perform the first-day source/package/supplied and validation-on/off walkthrough from help alone in isolated scratch. Inspect transitions/cleanup ownership, external data exports, defaults and actual package entries. Do not install/publish. Record each point requiring a guess. Surface is this same Code axis, never a third reviewer.
- Both axes independently establish problem, requirement provenance, necessity and authorized scope. Read the FULL proposal, committed Authority/DRAFT/Preparation and both targets' RESULTS/README. The actual all-nine implementation, two-at-a-time continuation and freeze instructions supersede the historical documentation-only/Python-stop clauses. Prior GO or DRAFT cannot expand authority. User Enum.case authoring, facts and tests are protected and excluded; Python field restrictions do not become JS/TS restrictions.
- Cover BOTH JS and TS plus actual shape-ts. Check reusable, complete, immutable descriptors in both modes; exact optional methods on every message; static typed adapters and terminating checked recursive links; actual loaded contracts and one nominal codec/descriptor/report/engine owner. No per-schema diagnostic classes, second validator/compiler or mandatory message base. Basic foundation applications must omit compiler/DSL/shape engines/transports; metadata must omit the validation engine.
- Attack non-null presence, independent groups and payload-free choices, exhaustive/nominations legality, wrong-tag suppression of dependent selection only, all populated owned paths including nonselected children, local/recursive scope, virtual incompleteness, active cycles and per-path shared children. Verify deterministic field/index/canonical unsigned CBOR key order, str/int/bool plus padded-base64 bytes, exact i64, owned snapshots and open strings, fast equals valid AND complete without report allocation, mutable invalid drafts and no implicit validation/coercion/discard.
- Native projections remain honest: JS CommonJS/object constructors; TS disabled interfaces and enabled Fields/classes. Decoded transport/service results are recursive plain Fields data, including actual external ExportFields imports (optional data_export); they must not promise instance methods. TS constructors retain the native __unknown__ Map by reference outside descriptors and reject only the exact storage-name collision.
- Distribution and compatibility: source/package/supplied independent of validation; CLI defaults and emit_all forwarding; no automatic installation/fallback/owner inference or dependency regeneration. Separately built enabled-parent/disabled-child, actual old/changed/split artifact rejection, effective codec fingerprints with irrelevant field/Case/enum ordering normalized, compatible unequal labels, real package/wheel provenance and CJS/ESM class/module identity. Distinct JS/TS codec projections are intentional; no invented JS library is required.
- Verify committed 73 Taut + 28 shape-ts files against frozen-r0/snapshot.json, including Preparation's own committed blob and protected five user files/35 excluded artifacts. Verify unchanged lock and dependency declarations. Retrace accepted Rust equivalent-root/raw-namespace counterexamples through common helpers and preserve Python/Rust/JVM boundaries. Historical JVM global logs retain their original source attribution; never add overlapping test counts.

COMMANDS
The ORIGINAL checkout D:/projects/limbo/taut-dev is READ-ONLY: no writes, Git mutations, builds or ignored-output changes there. Read/Get-Content/rg and git show/log/diff are allowed. For each original repo use `git -c safe.directory=D:/projects/limbo/taut-dev/REPO -C D:/projects/limbo/taut-dev/REPO rev-parse HEAD` (same root without /REPO). Verify all five tuple refs at START and END, committed blobs against frozen-r0/snapshot.json, and protected/excluded hashes. Read-only GWZ status runs only from workspace ROOT with process-local XDG_CONFIG_HOME=D:/projects/limbo/ecma-oneof-scratch/gwz-xdg and explicit targets. No global trust changes or installations.
Exact committed full trees are exported at D:/projects/limbo/ecma-oneof-scratch/review-r0/code/{taut,taut-shape-ts,taut-shape-py,taut-shape-rs}. These isolated review copies have no reviewed Git state. Existing frozen declared node_modules are reused through a read-only dependency junction. ONLY below D:/projects/limbo/ecma-oneof-scratch/review-r0/code may allowed tests/probes create scratch outputs. Never edit implementation/test source to make a result pass. New independent Python/Node/tsc reproduction probes are allowed below D:/projects/limbo/ecma-oneof-scratch/review-r0/code; record commands/results. This scratch-write exception preserves READ-ONLY of the reviewed object and does not permit original-tree changes or access to the other current-round report. No network/install/publish/global full suite/all-parity run.
Every test shell:
. D:/projects/limbo/toolchain-readiness-2026-11-02/Activate-TautToolchains.ps1
$env:PYTHONPATH='D:/projects/limbo/ecma-oneof-scratch/review-r0/code/taut/src;C:/Users/gianni/AppData/Local/Programs/Python/Python311/Lib/site-packages'
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
$env:PYTHONDONTWRITEBYTECODE='1'
Set-Location D:/projects/limbo/ecma-oneof-scratch/review-r0/code/taut
Allowed targeted command: python -m pytest src/tests/test_js_oneof.py src/tests/test_js_ts_distribution.py src/tests/test_typescript_oneof.py src/tests/test_ts.py -q --tb=short --basetemp D:/projects/limbo/ecma-oneof-scratch/review-r0/code/pytest-code-first (or individual tests in these files). Use unique --basetemp paths below D:/projects/limbo/ecma-oneof-scratch/review-r0/code per run. Isolated actual-library checks may run from D:/projects/limbo/ecma-oneof-scratch/review-r0/code/taut-shape-ts: pnpm typecheck; pnpm build; pnpm test; npm pack --ignore-scripts --json --pack-destination D:/projects/limbo/ecma-oneof-scratch/review-r0/code/new-package-dir (create the scratch directory). No dependency installation/upgrade. CLI-help/generation/Node/tsc walkthroughs may run in these copies, writing only below D:/projects/limbo/ecma-oneof-scratch/review-r0/code. The actual library fixture builds its containing repository: NEVER run it from original sources.
Root assigned TS exactly ONE settled global integration gate. Final results will appear under D:/projects/limbo/ecma-oneof-scratch/global-gate-r0. Consume completed results, exact source/hash before/after, baseline attribution and exclusions BEFORE your FINAL VERDICT. Do not duplicate the global matrix. If unfinished, continue attacks/contact the lane owner through collaboration messaging and await final evidence. Known baseline failures are the missing historical dev document and two original Windows Go CRLF/gofmt cases; verify provenance without weakening/hiding failures.
Write no report file. Return the COMPLETE standalone report as final; the lane owner files it verbatim. Never inspect/request the other current-round report or prompt. Authorized tuple/prompt/report/global evidence may appear untracked; production SHAs must not move.

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
  revision that resolves your blocking finding IDs as specified." This makes the re-verdict cheap
  and is encouraged when honest.


MANDATED COMPLETE REPORT FORMAT (fill canonical template):

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

Required sections: common problem/necessity/scope on both axes; Code Surface cold walkthrough; independent roots with severity/location/reproduction/impact/correction/closure; historical-root retraces; exact tuple/snapshot verification at both ends; completed settled global evidence attribution; binary verdict. Preserve peer blindness.
