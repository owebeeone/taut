You are an independent, adversarial, READ-ONLY reviewer. Your job is to try to
refute this object's fitness, not to appreciate it. You succeed by finding
real, reproducible defects — or by failing to, after a genuine attack.

ROLE AND OUTPUT
- Axis: Code+Surface; AXIS: CODE — architecture, interfaces, call graphs, and compatibility reality.
Attack: interface contracts vs. actual call sites; ownership and visibility;
API/wire compatibility with retained readers and older writers; error paths
and hidden panic/allocation paths; whether the diff does what its DRAFT doc
claims and nothing it forbids.
- Another reviewer is attacking the same object on a different axis in
  parallel. You must not see, request, or reason about their report. Your
  verdict is formed from your own evidence alone. (Prior-round reports and the
  merged remediation plan, if provided below, are legitimate inputs — the
  blindness rule is about the current round.)
- Your final message must be the COMPLETE report in the mandated format, and
  nothing else. It will be filed verbatim as dev-docs/CppGoOneOfCheckpoint-ReviewCode.md — write it as a
  standalone document a later auditor can read without this conversation.

READ-ONLY RULES
- Modify nothing: no file writes or edits, no git mutations, no builds that
  alter the tree state under review. Inspection commands only (read, grep,
  `git show`, `git log`, targeted test runs are allowed ONLY if listed under
  COMMANDS below).
- Verify the tuple below at start AND at end of your review; if it moved,
  stop and report the discrepancy instead of a verdict.

EXACT TUPLE (the object under review — nothing else is in scope)
- D:\projects\limbo\cpp-go-oneof-scratch\review-r0\code\taut-dev: bd455ef9174fb13679d0ec6814e43ec1345505fc
- D:\projects\limbo\cpp-go-oneof-scratch\review-r0\code\taut-dev\taut: 4222822320cbb22e376f8b387a963e86aad10ff2
- D:\projects\limbo\cpp-go-oneof-scratch\review-r0\code\taut-dev\taut-shape-py: c08c2a1b5197f761c5b0b835c588da512130ceda
- D:\projects\limbo\cpp-go-oneof-scratch\review-r0\code\taut-dev\taut-shape-rs: 8e92b89ed3a4f218a5a4e018fbfee6301fcc14b4
- D:\projects\limbo\cpp-go-oneof-scratch\review-r0\code\taut-dev\taut-shape-ts: 1aaeab65e4564a462044d2f5d824cd2f375aae97
- Object: combined Taut diff b9f99ac88ec585616ffac8bf4fbc2aaf4535fc16..4222822320cbb22e376f8b387a963e86aad10ff2; workspace receipt 3a5d103ab09561459ce61c85707b22fd4139f60c..bd455ef9174fb13679d0ec6814e43ec1345505fc. Full history +15trackedoraclefiles verified in clone-receipt.json.
- Controlling DRAFT: taut/dev-docs/CppGoOneOfCheckpoint-Draft.md at4222822320cbb22e376f8b387a963e86aad10ff2; Authority/Preparation at sameSHA.
- Out of scope: savedworkspace untracked35oldexcludedPythonartifacts, user-owned Enum.case authoring patch not assumedpresent, Swift, release/tag/push/registry/toolchain upgrades, unrelated library production. All builds/probe outputs only in your own scratch; no savedworkspace builds.

AUTHORITY AND DEFERRALS
- Process authority: C:\Users\gianni\.codex\skills\review-loop\SKILL.md plus workspace AGENTS/AGENTS_GWZ and Taut AGENTS. No local program-process documents were found; the user/coordinator amendments in Authority control.
- Controlling documents to check the object against: FULL dev-docs/OneOf-ExplicitValidation-BuildProposal.md, CppGoOneOfCheckpoint-Authority.md, -Draft.md, -Preparation.json; existing Python/Rust/JVM/ECMA verdicts are reference evidence of their stated objects, not approval of this pair.
- Original task authority: Human operator: implement all9languages, Python thenRust checkpoint accepted/pushed; remaining languages twoatime, currentC++/Go. Mandatory immutable descriptors/optional exact methods/general shared reports/typed adapters/native semantic+codec conformance/explicit source+package+supplied canonical singleowner/no auto dependency behavior/safe prewrite transitions. Root explicitly froze exact59files and authorized this local checkpoint and ONEcombined exactly2axis review; production correction waits for complete gate+mergedfindings. USER owns Enum.case patch, do not edit/revert or preserve old Python reservation policy. Read Authority for original delegation and later final-push amendment; DRAFT gives no independent scope authority.
- Requested deliverables and scope: This is READ-ONLY review of C++/Go production/tests/examples and shared driver/CLI/package data, one Taut diff plus managed workspace receipt. Reference shape-py/rs/ts revisions unchanged. No writes to savedworkspace or clone tracked source; only explicitly permitted scratch test/probe artifacts. No commits, staging, push, tag, release or Swift work. Root/lane owner alone files reports verbatim and merges remediation.
- Explicitly deferred (do not report as findings): Virtual oneof selection intentionally deferred/incomplete, with supported child traversal required. No new native C++/Go JSON parser route, no invented target library repos. C++ retains existing borrowed codec lifetime/fixedBuf contract; normal malformed-resource/data faults follow exact proposal boundary. These do not defer correctness of existing/native supported behavior. Three specific historical broad baseline failures remain visible in root integration gate; no new failure can be generically labeled baseline..
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
- Cover BOTH C++ and Go plus shared scaffold/CLI/package-data integration as ONE object, not separate target reviews. Read full proposal, Authority and Draft after the mandatory cold Surface pass. Diff b9f99ac88ec585616ffac8bf4fbc2aaf4535fc16..4222822320cbb22e376f8b387a963e86aad10ff2, all59paths in Preparation, workspace managed receipt. Actual reference libraries remain read-only; no C++/Go library repo is invented.
- C++ cpp.py/cpp_metadata.py/cpp_runtime.py and canonical runtime foundation.hpp/.cpp, descriptors.hpp, reports.hpp, validation.hpp: exact instance/public metadata API, one actual native owner and linked exported contract checks, source/package/supplied independence, real stale/replaced artifacts and independently built child bindings. Inspect no-RTTI/static linkage, typed primitive/enum borrowed reads and lifetimes, recursive links/types, consteval static immutability/publication and complete schema facts/options/rules.
- Precisely attack the C++ const noexcept allocation-fault Boolean/report contract. First fallback construction/move/copy/getters under fail-all allocation must not allocate, borrow input or rely on SSO. Fast mode must use same predicates and build no reports. Unknown/malformed configuration must fail before validation is usable, not become successful/deferred results.
- Go go.py/go_metadata.py/go_runtime.py and runtime/go/{descriptors,paths,reports,validation}.go plus reused cbor.go/ext.go: idiomatic structs/tags/options, exact receiver methods and nil-root behavior, sealed immutable facts with owned snapshots, direct typed primitive/presence/enum/traversal, correct recursive publication and active ancestor pointer/map/slice identities. Map-value copies/shared-child paths must not hide cycles.
- Native code/rule/path/deferred/scope/valid/complete must match Python: local/recursive, wrong-tag dependency suppression, ordinary and nonselected children, primitive presence including zero/false/empty, virtual deliberate incompleteness, canonical unsigned Taut CBOR map keys and padded base64. Constructors/setters/codecs must remain structural, retain denseCBOR/residual/missing-ok/nullable behavior, and never coerce or factory-build decoded plain values.
- External mappings/full dependency facts, complete normalized fingerprints including effective codec options/forward_compat, irrelevant field/Case/enum-map order normalization, compatible unequal builds, actual compiled/loaded guards rather than claimed binding labels or lexical self-checks. Basic consumers need no compiler/authoring loader/higher engines. All canonical nested assets must be in the actual wheel. No discovery/install/fallback/child regeneration.
- Mandatory descriptors and optional every-message methods in both distributions, emit/emit_all/CLI forwarding/defaults/naming, legal metadata-like enum values via native IR, target-specific keyword/generated-symbol prewrite collisions without Python-only name bans. Read user docs/help cold and execute a first-day source/package/supplied generation/use/transition walkthrough only in your scratch.
- Do not give a final verdict until parent supplies the COMPLETE settled broad/full16 integration receipt. Incorporate exact results/baselines/deselections/source-integrity checks in your report; current draft totals are not a substitute. You may send independent preliminary findings to the parent while awaiting that receipt.

COMMANDS
Work only in D:/projects/limbo/cpp-go-oneof-scratch/review-r0/code/taut-dev/taut for source inspection and in D:/projects/limbo/cpp-go-oneof-scratch/review-r0/code/scratch for temporary test/probe outputs. Do NOT read the other axis directory/prompt/current report or its messages. Do NOT run tests/builds in D:/projects/limbo/taut-dev. Native tools activate with . D:/projects/limbo/toolchain-readiness-2026-11-02/Activate-TautToolchains.ps1. Stable Python then must be3.13.5 (label it); set PYTHONPATH to yourclone/taut/src plus C:/Users/gianni/AppData/Local/Programs/Python/Python311/Lib/site-packages, PYTEST_DISABLE_PLUGIN_AUTOLOAD=1, PYTHONDONTWRITEBYTECODE=1. Use python -B -m pytest -p no:cacheprovider with --basetemp under your own scratch. TEMP/TMP/native caches and any build/probe file outputs stay under your own scratch (create it with a single permitted setup command). No installation/toolchain discovery fallback/network package retrieval; explicit native Go runs use GOPROXY=off GOSUMDB=off GOTOOLCHAIN=local GOWORK=off.
- Inspect with Get-Content, rg, git show/diff/log and Python stdlib reading. Exact tuple start/end: git -c safe.directory=<exactclonepath> -C <exactclonepath> rev-parse HEAD for all5repo paths above. Verify clone-receipt.json historical commits and tracked corpus. Inspect git diff --exit-code and git diff --cached --exit-code at end; any tracked/index movement stops the review. Git mutations/checkout are forbidden to reviewers.
- Code Surface cold first: python -B -m taut.cli --help and gen --help, then dev-docs/examples/cpp-oneof/README.md and go-oneof/README.md, BEFORE reading source/DRAFT/Authority. A first-day help-driven walkthrough may generate/compile/run only in your own scratch. State may read ordinary order.
- Allowed targeted pytest node IDs (you may run subsets; do not run the whole broad suite/parity gate): src/tests/test_cpp_oneof.py::{test_reference_behavior,test_allocation_fault_noexcept,test_independent_disabled_child_shared_owner,test_mutual_recursion_and_primitive_borrows,test_actual_replaced_link_artifact_rejected,test_actual_old_checker_cannot_ignore_new_requirements,test_actual_external_facts_guard,test_immediate_metadata_rejects_mutable_backing,test_malformed_known_constraint_is_configuration_error,test_type_and_own_method_collisions_prewrite}; src/tests/test_go_oneof.py::{test_python_normalized_conformance,test_mandatory_metadata_owned_snapshots_engine_free,test_reports_are_general_owned_snapshots_and_bad_rules_are_configuration,test_actual_stale_artifact_is_rejected}. Confirm exact node spelling with collection/source first; additional narrowly justified target test/probe commands are allowed if recorded, not a duplicate broad or all16 gate.
- Native adversarial counterexamples may write minimal probe sources/modules only under your own scratch and compile/run them against your unchanged clone. Document complete command/reproduction/results. No alteration of tracked input or savedworkspace; malicious/stale replacements must be COPIES under scratch. This is the only permitted file-write exception to read-only review, alongside explicit test scratch outputs.
- Do not run run_tests.py or regenerate tracked corpus/goldens; the existing15tracked oracle files are present. No duplicate broad suite or parity run: Go is the root-assigned single integration runner. Wait for parent-supplied COMPLETE integration receipt before final verdict. Once your analysis is done, send parent preliminary status/findings and wait for its message (can wait via collaboration.wait_agent with bounded waits); do NOT finish early claiming the integration result is unavailable.
- At final, verify tuples and tracked/index immutability, incorporate the complete receipt's exact source association/11deselections/baseline3/all16 details, and output ONLY the full mandated standalone report.

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

MANDATED COMPLETE REPORT FORMAT (fill every applicable section)
# CppGoOneOfCheckpoint — Code+Surface-AXIS REVIEW

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
