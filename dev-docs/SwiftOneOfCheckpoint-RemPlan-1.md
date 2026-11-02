# Swift OneOf checkpoint - merged remediation plan 1

Date: 3 November 2026 (Australia/Sydney). Status: **ROOT AUTHORIZED; merged
remediation round 1 in progress within the exact approved scope.** This is ONE merged patch
for the two original reports, remediation window 1 of at most two. It is not
acceptance, an implementer closure or authorization for a new broad/all16 run.

## Exact object and completed evidence

Initial object: Taut `c02765930f06cfcb19a522843aa54582db514706`, workspace
`a8f37984471654902149d136b7a13a588346b58f`; shape Python/Rust/TypeScript remain
the exact revisions in the [initial verdict](SwiftOneOfCheckpoint-Verdict.md).
The [Code + Surface](SwiftOneOfCheckpoint-ReviewCode.md) and
[State](SwiftOneOfCheckpoint-ReviewState.md) reports are filed verbatim.
Their scope/necessity checks found the requested outcome and component authority
established. Both require localized corrections rather than a new native ABI,
authoring system or dependency infrastructure.

The SINGLE complete root/Go r0 gate is preserved at
`D:/projects/limbo/swift-oneof-scratch/global-gate-r0`, with its machine/human
summary, commands, logs/XML, three baseline traces, skip/deselection receipts,
parity data and complete source/protection/raw-blob before/after proofs. All 37
inventoried files were verified independently by the lane owner and both axes.
All16 GREEN; 2,260 passed / three exact known baseline failures / five skips /
eight duplicate-marker deselections; 2,268 selected; zero new test failures.
No old enum-name exclusion remains. The three baseline failures are not part of
this patch. R0 evidence is never relabeled as corrected-source evidence.

## One disposition and closure test per finding

| Disposition | Finding | Owned correction | Originating closure |
| --- | --- | --- | --- |
| M1: qualify ambient native helper references | Code P2-1 | Swift metadata emission and new canonical Swift resources; native regressions | Replay Data, NSLock, ObjectIdentifier, AnyObject and Void in flat/imported OFF/ON; compile and run, retaining prior legal names. Void also works in source/package. Preserve Unicode, enum cases, disabled method-like fields and imported harmless names. |
| M2: retain retirement provenance across flat-supplied cleanup | State P2-1 | Existing shared Go/Swift planner/manifest and previous-root lock discovery; Swift and Go state regressions | Replay actual planned writes plus owner-receipt-first deletion and retry, OFF/ON and validation changes. Cleanup is positively justified or refusal is named and byte-unchanged. Exercise BOTH Go/Swift default flat, package/imported controls, other users, handwritten content, external prior roots and all pre-lock aliases. |

Neither finding is disputed or omitted. No independent architectural defect was
reported by Code; State calls its recovery defect bounded. Root nevertheless
must authorize M2 because it changes persisted provenance at the shared mutation
boundary. The same two original reviewers retain context and own closure.

## M1: native namespace correction

For `schema(**{name: Msg(value=F(1, INT))})`, all five names compiled using the
integrated parent emitter and unchanged codecs. In r0 generation succeeds but
all five fail flat OFF/ON compilation. Data, NSLock, ObjectIdentifier and AnyObject
have working imported-owner controls; Void fails imported OFF/ON too because
the generated holder declares `guardOwner: Void`.

Qualify new Foundation helpers with their defining module and new standard Swift
types/constraints with `Swift.` where they are ambient helper references rather
than schema references. In particular: Foundation.Data, Foundation.NSLock,
Swift.ObjectIdentifier, Swift.AnyObject and Swift.Void (or native unit syntax).
Audit the newly introduced helper references in metadata/resources for the same
seam; use actual compiler probes for any ambiguity. Keep schema type references
as their actual native declarations. Preserve all five demonstrated names through
qualification; do not add a blanket reservation for imported harmless names.
The root-requested module-shadow probe demonstrated that a message named
Foundation compiled with the ambient r0 helpers but failed native compilation
after qualification: `type 'Foundation' has no member 'Data'` at paths.swift:22.
Exact old-success/new-shadow inputs, commands and stderr are retained in
`remediation-r1/module-shadow/results.json`. Swift was already reserved by the
unchanged emitter; its probe receives the existing prewrite error.

Root subsequently authorized exactly one unavoidable scope restriction: a local
Foundation message or enum refuses prewrite ONLY in default flat supplied mode,
where it hides the defining module. The diagnostic directs users to an explicit
imported runtime binding. Foundation remains legal in imported source/package/
supplied modes, with positive native OFF/ON controls for both declaration kinds.
See [R1 authority](SwiftOneOfCheckpoint-Authority-1.md). No broader reservation,
new module, ABI or concurrency infrastructure is authorized. Any additional
genuinely unavoidable collision still requires exact evidence before expansion.

This changes no native model layout, descriptor/report/codec contracts, instance
API, identity definition or runtime placement. Canonical cbor.swift/ext.swift
remain unchanged. Regenerate only the four attributed Swift example goldens
whose emitted helper spelling changes, then compile/run those exact bytes.

## M2: precise provenance and locking boundary

The original sequence is a supported source-to-omitted-runtime transition.
The new flat API and schema receipt (`mode=supplied`, `source_root=null`) are
written, then the unordered stale set can remove the runtime owner receipt
before its four/six runtime sources. On retry there is no source root/import/
consumption/existing owner to trigger the unknown-source scan, so it succeeds.

An unconditional filename scan would reject legitimate first-time, nonowning
flat applications that intentionally supply the canonical runtime themselves.
Changing deletion order alone does not give the schema receipt evidence of an
old separate physical root after its source_root has already been replaced.
The proposed correction retains that existing positive root provenance until
a later plan can verify the retirement state. This is an additive ownership
receipt fact and existing preflight extension, not a transaction engine, journal,
new public option, automatic repair or new runtime-owner identity.

Proposed internal schema-receipt field: optional `retiring_source_roots`, a typed
deduplicated list of canonical absolute root strings. It applies only to the
shared Go/Swift planner's own schema receipts; absent means the existing grammar.
It names old physical source roots whose stale runtime deletion this plan will
schedule and which the new active `source_root` no longer retains. It grants no
ownership of any file and contains no authority to adopt/delete an orphan.

The bounded algorithm is:

1. Read and validate the optional root list before path coercion or lock creation,
   using the same raw namespace, absolute-path, ancestor/alias/obstruction checks
   as the existing previous source_root. Add these previous roots to the existing
   lock set. Under the lock recheck that every recorded prior root is covered;
   reject concurrent provenance expansion. Malformed/unknown shape refuses before
   mutation. Do not loosen ordinary missing-active-owner handling.
2. Plan against current root, old active root and retained retiring roots using
   the existing owner/contracts/hash/user checks. A retiring root is checked for
   unknown canonical source files even with empty import/default supplied mode.
   If its owner is missing but any canonical runtime file remains, refuse named
   and unchanged. Do not infer ownership from names or matching canonical bytes.
3. If owner evidence exists, retain existing live-user/engine/remap rules. Only
   recorded hash-matching stale files may be scheduled for removal. A partial
   owner inventory or modified/unknown file still refuses unchanged.
4. The new schema receipt carries every root for which this plan schedules stale
   runtime deletion and loses the active root pointer. This fact is in the normal
   schema write before deletions, so receipt-first deletion cannot erase all
   provenance. Keep prior pending roots while further cleanup is scheduled.
5. Drop a prior retiring-root fact only in a later plan that observes a verified
   consistent owner with no pending/unknown remnants, or absent owner AND no
   canonical runtime files. In that latter case there is nothing left to adopt
   or delete. Normal clean retirement may therefore leave a harmless provenance
   entry until the next generation verifies completion. Preserve handwritten
   unrelated paths and another user's verified owner/needed engine.

The common `apply_outputs` write/replace/delete machinery, public runtime bindings,
owner/import identities and resource inventory remain unchanged. No extra
sidecar, automatic cleanup process or source-root rediscovery is introduced.
The expected byte delta to Go receipts is confined to retirement provenance;
accepted native transitions, remap refusals and file deletion sets stay valid.
Old/new planner equality continues on non-retirement routes; tests explicitly
attribute the intended receipt delta on retirement rather than claiming universal
byte equality after this change.

Fresh default flat generation has no retiring-root fact and remains nonowning:
caller-supplied runtime sources remain allowed and untouched, including repeated
generation and validation OFF/ON. Once a recorded retirement is verified complete,
the fact can clear; subsequent legitimate flat runtime placement remains allowed.
An ambiguous still-recorded retirement refuses rather than adopting caller files.
Already-stranded r0 scratch outputs with every proof erased cannot be safely
distinguished from legitimate unowned flat sources. R0 is unaccepted/unpublished;
the correction must preserve evidence on newly executed transitions and must not
invent authority to repair such historical ambiguous scratch states.

## Expected owned paths and protection

Proposed production/test allowlist, subject to root reconciliation:

- `src/taut/gen/swift_metadata.py`
- `src/taut/gen/runtime/swift/paths.swift`
- `src/taut/gen/runtime/swift/descriptors.swift`
- `src/taut/gen/runtime/swift/reports.swift` and `validation.swift` only if the
  new-helper audit proves the same ambient reference issue there
- `src/taut/gen/owned_runtime.py`
- `src/taut/gen/scaffold.py` (retiring-root namespace/lock discovery and recheck)
- `src/tests/test_swift_oneof.py`
- `src/tests/test_go_oneof.py` (newly attributed shared-helper flat controls)
- Four existing `dev-docs/examples/swift-oneof/golden/*.swift`
- Necessary `docs/SWIFT_API.md` explanation of the retirement provenance/refusal
  behavior if native user instructions need it; no public flag/API addition

Swift executor owns this one merged correction, tests and evidence. No helper,
extra reviewer, independent target patch or production commit occurs before root
authorizes the plan and exact scope. Root may assign Go read/run preservation
to its existing executor; that executor is not another review axis.

Evidence-only additions include the exact prompts/setup/dispatch, initial reports,
verdict, this plan, original failed probe receipts, r0 global package, corrected
focused/native/example/wheel receipts, R1 source inventory/Preparation/tuple and
same-originator re-verdicts. Keep original Authority/Draft/Preparation and r0
45-file evidence unedited as historical records; add attributed R1 records.

Protected five user authoring files, old excluded 35, canonical Swift cbor/ext,
other target codecs/validators, reference libraries, dependency/lock/version files
and user source trees remain unchanged. No manual gwz.conf edit, worktree, install,
tags, publication or push. GWZ owns authorized local stage/commit/capture actions.

## Focused gates, settled correction and acceptance

1. Run the exact native five-name matrix OFF/ON in flat and imported placements,
   and Void through source/package. Compile/run accepted names; retained baseline
   counterexamples remain historical failures. Preserve existing emoji/native-IR,
   enum-case, helper qualification and validation-disabled field controls.
2. Add persisted M2 fault tests that invoke the real plan/application boundary:
   actual planned writes, forced owner-receipt-first deletion, all ordinary
   cutoff prefixes, validation changes, same and separate old roots; BOTH Go
   and Swift actual omitted/default-flat routes. Include first-time/repeated
   caller-supplied flat sources, successful retirement/return, other users/engine,
   handwritten files, modified/unknown leftovers, package/imported controls,
   genuine source remaps, multiple retained roots and typed malformed provenance.
   Every refusal must leave all bytes unchanged and release locks.
3. Retain all nine previous-owner junction-before-lock cases; extend the same raw
   namespace/alias-before-lock counterexample to retained retiring roots. Exercise
   locked provenance recheck and multi-target all-or-nothing planning.
4. Run meaningful Swift feature/existing native suites, actual current wheel
   extraction and isolated source/package/default-flat builds, and five corrected
   examples. Run existing Go ownership/retirement/remap/cutoff/native cases plus
   the new default-flat controls, shared planning/preflight and unchanged shared
   help nodes. Keep counts/source hashes/commands and original failed attempts.
5. Do not repeat full broad/all16 automatically. The r0 full gate remains valid
   only at its old tuple. If focused results show wider shared impact, report
   the concrete evidence to root before widening gates or source scope.
6. Reconcile exact owned raw hashes, protected five/excluded 35/indices/locks and
   reference HEADs. Root authorizes ONE scoped local GWZ correction and managed
   receipt; freeze the corrected production and record the complete tuple.
7. Continue the SAME two original reviewer contexts with the merged plan, exact
   diff, tuple and focused evidence. Code replays Code P2-1; State replays State
   P2-1 and shared controls. Each classifies any new root and verifies its own
   original counterexample. Neither implementer tests nor root authorization
   closes a finding. File both re-verdicts verbatim.

Acceptance requires GO from both original axes on the SAME corrected tuple,
every P0/P1/P2 closed by its originator, preserved compatibility/protection and
complete evidence. The two-remediation-window cap remains operative; any third
new architectural root is an operator redesign-or-accept decision. Root owns
the later fresh-remote inspection and final push after acceptance.

## Implemented R1 record and freeze

Production is now frozen at 30-file source inventory
`7be5937d06eab85d3f1b2f579b18cb36b476d3a8cc79de43812675c457f76b49`,
with exactly 12 changed production/test/example paths from the approved list.
The canonical reports/validation resources needed no new ambient-reference change;
cbor/ext, other target codecs, user sources and shape libraries remain unchanged.
All five original names are preserved. The root-approved Foundation exception
and unchanged Swift reservation have positive/negative declaration controls.

An actual dangling Windows junction at a canonical runtime filename exposed an
exists-only remnant check during the same uncommitted M2 window. The final scan
also uses the existing `_is_alias` lstat/reparse helper; it covers dangling
junctions as well as symlinks. Root explicitly confirmed this is within M2's
unknown/alias-remnant refusal scope. Both Go/Swift real-junction regressions pass;
no unavailable symlink-privilege control was weakened or relabeled.

[FocusedResults-1](SwiftOneOfCheckpoint-FocusedResults-1.json) and
[RESULTS-R1](examples/swift-oneof/RESULTS-R1.md) retain commands, raw logs/XML,
source hashes and all original failed probes. Final-source results are 101 Swift
affected cases, 405 Go/shared cases, 11 current-wheel/prelock/planning cases and
five native examples, all passing without skips. Counts overlap. The prior full
186-pass Swift run remains explicitly at its earlier R1 hash, before the final
one-line alias hardening; it is not relabeled. Ten accepted-old/current Go planner
comparisons have six exact maps and four intentional provenance-only receipt
deltas; all other write bytes and deletion sets match.

The next steps are the already authorized exact local GWZ correction/managed
receipt and SAME-two-originator closure. Both initial findings remain open.
