# JavaScript/TypeScript checkpoint — merged remediation plan1

Status: **coordinator AUTHORIZED ONE merged correction window for round1**.
Initial Code+Surface and State both reported NO-GO on the same settled tuple.
No implementer closure is claimed. Round1 is in progress; maximum2.

## Reviewed object and immutable evidence

| Repository | Initial reviewed revision |
| --- | --- |
| Taut | `68c24a899345367f3026372d3c67737751215a0e` |
| shape-ts | `1409634e9b1c8eea0696bf0fee560d5017f34d1f` |
| workspace | `fe244bc4915acbce58198889feae633f778fe649` |
| Python reference | `c08c2a1b5197f761c5b0b835c588da512130ceda` |
| Rust reference | `8e92b89ed3a4f218a5a4e018fbfee6301fcc14b4` |

The complete [Code](EcmaOneOfCheckpoint-ReviewCode.md) and
[State](EcmaOneOfCheckpoint-ReviewState.md) reports are filed verbatim. Their
original independent probes remain under ecma-oneof-scratch/review-r0/{code,state}.
The original101-file snapshot, tuple checks and protected35+5 hashes remain intact.
No current-round report or suspicion was shared between reviewers before their
final reports. Surface remained part of Code; no third reviewer was launched.

The one settled r0 integration gate is complete and immutable under
`D:/projects/limbo/ecma-oneof-scratch/global-gate-r0`: all16 codec variants GREEN;
broad1807passed/4failed/5skipped/11deselected. Baseline3 are proven; the fourth
failure is the current help assertion below. Exit1 is retained. Source, tuple,
protected files and frozen lock stayed unchanged. Neither correction evidence
nor later acceptance may relabel this original gate as green/current R1 source.

## Findings, roots, dispositions and original closure

| Finding | Root / disposition | Owner and original closure |
| --- | --- | --- |
| Code/P2-1 | R1: actual selected TS facade exports are not checked; the checker inspects lexical imports only. Correct namespace verification against the actual owner, preserving genuine re-exports. | TS executor; original Code reviewer reruns separately evaluated and partial-facade codec/error/CborFloat probes. |
| State/P2-1 | R2: generated TS field reads lack a located input-access failure boundary. Correct only known-bound field reads, preserving configuration errors and independent checks. | TS executor; original State reviewer reruns nested discriminator/payload/ordinary getter probes, exact paths, local/recursive and fast behavior through source/library artifacts. |
| State/P2-2 | R3: published constraint elements/grammar are not checked as immutable normalized records. Own defensive canonical immutable snapshots, exact parameter shape/types and one-to-one group controls; refuse invalid configuration. | TS executor; original State reviewer reruns strict mutable-record, post-publication mutation, duplicate/missing/extra/coercible controls and unsupported-parameter probes against source/actual library. |
| Code/P3-1 | R4: TS package-builder public help omits included-by-default validation and fresh-directory explanation. Help-only correction plus actual-help assertion. | TS executor; original Code reviewer cold-reads actual module help and verifies defaults/output guidance. |
| Code/P3-2 and State/P3-1 | R5: expanded shared help was not reconciled with the retained JVM help contract. Preserve truthful named target/method/JSON/default/artifact guidance and make the complete existing test pass. Never suppress or baseline-relabel it. | JS/shared executor; both original reviewers verify their original help failure and the complete assertion sequence. |

There are **three independent P2 roots** and **two P3 roots**. The two help findings
share the same external global evidence and are merged once as R5; this is not
claimed as independent blind discovery of that shared-input failure. Both axes
independently encountered the getter behavior, but Code explicitly did not promote
it to a blocking prerequisite; the disagreement is recorded below rather than
presenting false unanimous convergence. No other finding is silently dropped.

### Bounded requirement interpretation for R2

Code treats arbitrary user accessor containment as beyond ordinary malformed data;
State applies the required located-diagnostic contract to a mutable generated slot
made unreadable. The chosen correction is limited to direct reads through an
already known generated binding. It must not add reflection, arbitrary-object
discovery, factories, a universal no-throw promise, or catch configuration failures
around the entire validator. This satisfies State's concrete path/report/Boolean
counterexample without expanding supported metadata or object discovery. State
still owns closure; Code must independently judge the actual changed boundary.

## Proposed correction limits

R1 must inspect the actual selected namespace, including low-level CBOR exports,
codec/schema/JSON namespaces, nominal errors and CborFloat, against the descriptor
owner. Matching labels, types, or a lexically captured checker are insufficient.
Generated source can supply the selected namespace to the foundation check; do
not execute target modules in the compiler, require a second owner, change codec
semantics, break real CJS/ESM/source facades or invent registry dependencies.
The exact helper signature remains the TS executor's implementation choice.

The coordinator adds one required same-root artifact retrace: call sites passing
a selected namespace cannot rely on an old guard honoring an extra argument.
Substitute the exact r0 guard artifact (or its existing zero-argument wrapper)
in an otherwise compatible-looking facade and require fail-closed capability/
return-contract/publication proof. Merely testing the new checker against mutated
new exports is insufficient. Preserve genuine forwarding alias wrappers and
compatible unequal labels; do not replace actual capability proof with a blanket
version-label ban. The original Code reviewer evaluates this as R1, not a new
architectural loop or additional reviewer.

That capability proof must also establish a defined valid owner token: an old
void guard plus an omitted Foundation export must not pass by comparing
undefined===undefined. Include the stripped-token/r0-guard facade in the same
negative substitution matrix, and retain genuine forwarding aliases as positives.

R2 must preserve located discriminator versus shape codes, independent report
collection and Boolean short-circuit without constructing full reports. Static
metadata/options/binding failures remain named configuration errors. No live
instance may be captured in static metadata. Do not convert children or validate
implicitly in constructors/codecs.

R3 must own defensive canonical immutable constraint snapshots and reject invalid
configuration before publication. A duplicate left control cannot substitute for a
missing right control. Unknown parameters and non-string/coercible controls must
fail clearly. Valid independent/virtual groups and engine-free descriptor use
remain supported. No general rule-plugin implementation is added.

R4 is documentation/help only. R5 updates the obsolete target-group assertion to
the expanded supported grouping while preserving every substantive accepted JVM
method/default/JSON/owner check. Keep or restore truthful target-specific artifact
formats in help and add current JS/TS coverage. Do not weaken/delete the regression,
change runtime selection semantics or edit unrelated JVM production. Retain the
original failed r0 log. JS/shared owns cli.py, the single named JVM help test and
shared JS/TS help assertions; TS owns typescript_package.py and its help assertions.

Base Taut remains canonical. TS updates its actual-library foundation sources and
provenance through the explicit vendor/build route, including generated metadata
when the checker invocation changes. No app-time compiler/loader/install/fallback,
dependency upgrade, lock change, delivery-engine redesign or other backend work.

## Patch, validation and refreeze procedure

1. Coordinator assigns one correction window and confirms the bounded scope. TS
   owns R1–R4 implementation and target/artifact tests; JS/shared owns R5 and shared
   help assertions. Corrections form ONE merged patch, not independent target
   commits or separate reviews. All user sources,35 old artifacts, other backend
   production, dependency maps and frozen lock remain protected.
2. Add closure tests based on the exact original reproductions, including strict
   compilation and actual separately built package/source artifact substitution.
   Preserve positive CJS/ESM/selected-source-owner/library and disabled-child cases;
   preserve non-oneof reports, engine-free metadata, i64/native residual behavior,
   ordinary malformed shapes and no-report fast behavior.
3. Run meaningful affected TS/JS/shared CLI/service/package/wheel/name/contract
   gates and actual library typecheck/build/test. Run the complete old JVM help
   test and justified shared preservation. No automatic second broad/all16 gate:
   r0 is historical evidence; root decides if actual shared impact justifies more.
   Record exact source associations and never add overlapping counts.
4. Reconcile the exact R1 allowlist and changed-range hashes, protect user/excluded
   files and verify clean unrelated indices. Obtain the coordinator's scoped local
   checkpoint authority, use GWZ for the merged member checkpoint/managed receipt,
   and record a revised exact tuple plus immutable R1 snapshot. Preserve r0 records.
5. Generate canonical-template focused re-verdict prompts for the SAME two
   originating agents with this now-legitimate merged plan and exact changed range.
   Each reviewer must rerun its ORIGINAL counterexamples and provide the skill's
   prior-finding closure table and changed-range analysis. Implementers do not
   self-close blockers. Material interface/architecture/mutation/compatibility
   changes trigger the skill's replacement rules; the original reviewers classify
   the actual patch, not a drafter's assertion. Never exceed two reviewers/revision.

## Root classification and next action

The proposed remedies restore explicit existing owner, immutable-publication,
located-diagnostic and help requirements. They appear bounded; no delivery-engine,
wire, output mutation boundary, platform baseline or user-facing validation API
redesign is proposed. R1's selected-namespace checking seam and R2's limited
read-error boundary require careful original-reviewer changed-range assessment.
This is a proposal for coordinator disposition, not permission to make a material
architecture change or a claim that the corrected tree is accepted.

Next action: TS completes its assigned source/tests/evidence and returns HOLD;
JS/shared aggregates the affected checks and exact R1 allowlist. All P2
findings remain OPEN. No push, tag, release, publication, extra reviewer or next
backend is authorized.

Coordinator assessment after reading the merged NO-GO summary: these are bounded
strengthenings of existing adapter/publication boundaries, not grounds for a
descriptor redesign or additional reviewers. A narrow application-read catch may
produce located dynamic issues, but binding/configuration/version errors must
remain explicit. Actual selected exports must be inspected and constraint state
must be an owned canonical snapshot. The same two original reviewers continue;
no fresh broad gate is planned by default. The coordinator subsequently explicitly
assigned this merged window to those owners and authorized a scoped local GWZ
corrected checkpoint once the patch and affected gates are complete, followed by
the SAME original reviewers' counterexample replay on the revised exact tuple.
No source change outside this bounded patch, automatic repeat broad gate or
additional reviewer is authorized.

## Merged implementation evidence before corrected checkpoint

R1-R5 have implementer corrections and original-counterexample regressions.
The shared affected gate passed503tests with1existing Windows symlink skip;
its source, indices, protected files and lock stayed identical before/after.
The TS final affected gate passed169tests, including83closure variants; actual
library typecheck/build and315Node tests passed. See Gates-1 and TS RESULTS-R1
for separate source associations, commands and retained failed-first evidence.
These counts overlap historical/independent runs and are not summed. No broad
or all16 gate was repeated, and the original failed r0 receipt remains intact.

The corrected local checkpoint freezes ONE merged patch and its evidence for
the SAME two original reviewers. This records implementation readiness only:
all three P2 findings remain OPEN pending originating original-counterexample
replay and explicit prior-finding closure tables on the revised exact tuple.
