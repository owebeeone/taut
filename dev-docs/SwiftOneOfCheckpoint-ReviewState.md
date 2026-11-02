# SwiftOneOfCheckpoint — STATE-AXIS REVIEW

**Review object:** Taut `83291c2c7c7b126e41625bd29623870330f3b0d6..c02765930f06cfcb19a522843aa54582db514706`, exact 45-file Swift/shared-integration checkpoint; controlling `dev-docs/SwiftOneOfCheckpoint-Draft.md` at the latter commit. Production frozen; acceptance pending. Workspace managed receipt `45f1e4387f3bcd6b21b6291dc0fab0a262303ba9..a8f37984471654902149d136b7a13a588346b58f`.

**Baseline:**

| Repository | Exact reviewed HEAD |
| --- | --- |
| Taut | `c02765930f06cfcb19a522843aa54582db514706` |
| Workspace | `a8f37984471654902149d136b7a13a588346b58f` |
| taut-shape-py | `c08c2a1b5197f761c5b0b835c588da512130ceda` |
| taut-shape-rs | `8e92b89ed3a4f218a5a4e018fbfee6301fcc14b4` |
| taut-shape-ts | `1aaeab65e4564a462044d2f5d824cd2f375aae97` |

Sources were read through committed diffs, historical `git show` and the raw-associated checkout in `D:/projects/limbo/swift-oneof-scratch/review-r0/state-raw/taut-dev`. All executions used that isolated clone and its owned scratch.

**Date:** 3 November 2026, Australia/Sydney.

**Axis:** STATE — durable output transitions, interruption/restart legality, physical ownership and locking, immutable publication, typed bindings, snapshots and native ancestor identity. Independent, adversarial, read-only. The other axis runs in parallel; nothing here relies on it. Filed verbatim by the lane owner.

**Verdict: NO-GO** — one P2 finding blocks; no P0, P1 or P3 finding. I pre-commit to GO on a revision that resolves P2-1 as specified, subject to originating-counterexample verification, appropriate focused checks and preservation of surrounding invariants.

---

## 0. Evidence base

Read the complete assigned canonical prompt, review-loop skill, cloned workspace AGENTS/AGENTS_GWZ and Taut AGENTS, the full build proposal sections 1–9, Swift Authority/Draft/Preparation and UserEnumCaseIntegration receipt. Reviewed the 45-file inventory, Swift API documentation, examples, four attributed goldens, expected normalized stream and retained focused results. The preparation's 44 non-self hash/size records and 29-file source inventory verified; source-before/source-after are identical and carry inventory identity `51c92bf28ff9d9936bb89f1c6a9225fcf2ce6858f816eebef406c6e74b5ee156`. The five protected user-source hashes match the integrated baseline.

Detailed source inspection covered:

- `src/taut/gen/owned_runtime.py:1–128`, the extracted manifest/planning grammar and user retirement.
- `go_runtime.py:1–204` and its accepted predecessor at `c9c5bb0764bbc5a58c65e649468ed5aa67920ded`.
- `swift_runtime.py:1–145`, `swift_metadata.py:1–262` and changed Swift native projection, particularly direct recursive storage and initialization.
- All canonical Swift descriptors, paths, reports and validation resources, including lazy links, registry checks, binding metatype checks and reference identity.
- Shared `scaffold.py:590–976` and unchanged `python_runtime.py:49–163,242–271`: raw namespace checks, physical roots, previous-owner discovery before locks, locked recheck, complete planning and individual replacements/deletions.
- Changed CLI, parity driver, resource glob, Swift feature/existing/distribution tests and nine-target previous-owner alias regression.

Read historical C++/Go original reviews, R1 reviews, Verdict-1, Acceptance-1, Preparation-R1 and both RESULTS-R1 documents. Their acceptance and global results retain their recorded revisions; they are not substituted for this checkpoint's evidence.

At both review boundaries, all five HEADs matched the table, tracked/index diffs were empty, and all **1,114 setup raw-associated checkout hashes** matched: workspace 55, Taut 825, Python shape 75, Rust shape 63, TypeScript shape 96. No reviewed source, reference library, dependency declaration, saved-workspace artifact or Git state was changed.

### Independent executions

Dot-sourced the assigned `scratch/Activate-Review.ps1`; confirmed imported `taut.__file__` under the isolated clone. Used existing CPython 3.13.5/Swift 6.4.2 and native Go, with bytecode/cache-provider/plugin-autoload exclusions and owned temporary/cache locations.

1. The exact allowed Swift feature/existing command passed **146 tests**, with one duplicate parity wrapper deselected, no failures/skips, **369.88 seconds**. Receipt: `state-raw/scratch/native-tests.xml`. It executed source/package/imported supplied/default flat behavior, disabled children, actual replacements/facades, native recursion/value sharing, snapshots, Unicode/emoji naming, guards, flags, 40 retirement cutoffs and retained native codec/bounds/residual/fuzz tests.
2. A focused selection from `test_go_oneof.py` plus the pair planning and previous-owner alias nodes passed **76 tests**, 79 deselected, no failures/skips, **28.41 seconds**. Receipt: `scratch/shared-tests.xml`. Selection expression: `finite_prefix or default_source_owner or external_retirement or actual_selected_source or source_package_consumer or raw_windows or output_fault or alias_rejected or pair_plans`. This includes original Go finite-prefix and retirement/return counterexamples, surviving users/engine, genuine import remaps, malformed owners, all 40 persisted retirement cutoffs, raw Windows paths and all nine pre-lock junction cases.
3. The real current compiler-wheel test passed **one test**, **34.46 seconds**: `scratch/wheel-tests.xml`. Its wheel SHA256 is `0744e546472e9fbb51d69f84798998bef486bde11e12f4d43cdeb09ea5da4a5d`. Independently reopened that wheel and matched all six canonical Swift resources. Extraction, Python `-I -S` generation and compiler-free native source/package/default-flat applications executed.
4. Independently loaded accepted historical Go planner source through `git show`, then compared it with the extracted current planner on identical physical roots before application. Ten OFF/ON source/reuse/package/return/imported-supplied plans had exactly equal write bytes and deletion sets. Retained result: `scratch/probes/go-equivalence/results.json`. This reinforces the committed old/new proof without treating prior acceptance as blanket approval.
5. Additional persisted owner-receipt-first probes executed entirely in `scratch/probes`. Swift package/imported-supplied controls and original Go package/imported-supplied controls all refused unchanged in OFF/ON modes. Swift default flat supplied instead reproduced P2-1 in both modes. Scripts/results: `receipt-first.py`, `receipt-first-results.json`, `go-receipt-first.py`, `go-receipt-first-results.json`. Script exits were zero; their explicit results distinguish refusal from the defective success. Swift probe SHA256: `8d7355596d0832fb835c714cb646de41f2648b047aec901f31eaf07b89eca003`; result SHA256: `d338ef25c7a15cd781c65841b4f3de63f270e16dfd95db59a227e34ebecfd129`.

Counts overlap and are not summed. No duplicate full/global/parity wrapper or additional dependency installation ran.

### Completed exact-tuple global receipt

Waited for the lane owner's explicit completed-receipt notification before forming this final report. Consumed `D:/projects/limbo/swift-oneof-scratch/global-gate-r0/RESULTS.md`, global-results, execution receipt, evidence inventory, broad log, baseline-source proof, skip/deselection classifications and all three exact failure tracebacks. Independently verified all **37 inventoried evidence files' hashes and sizes**. Inventory SHA256: `93b84b7cca6fa4bf502e45a819b1babc837716335ba225ba35da33ec2650beca`; global-results SHA256: `bad810019879df69ac807a2c8037453c8f116b9aba4da1863c1a3d444c2b75a9`.

The completed gate is associated with exactly the five reviewed HEADs. All **16 require-all codec variants are GREEN**, zero governance violations. Broad pytest: **2,260 passed, three failed, five skipped, eight deselected; 2,268 selected**, exit 1. Pytest duration: 1,167.93 seconds; entire gate: 1,213.7 seconds. There are **zero new broad-test failures**. All 116 Swift feature cases, 30 existing Swift cases, the Swift wheel, all 145 Go feature cases and actual enum.case authoring/metadata tests remained selected.

The three enabled failures are the demonstrated historical baselines: missing `TautProtoApiSurfaceExtensions.md`, `test_go_runtime_and_parity_runner_are_gofmt_clean`, and `test_generated_go_is_gofmt_clean`. Retained Windows scratch files contain CRLF; the separate LF feature regression passed. The unchanged baseline-test/source associations are explicit; the migrated Go generator is not falsely labeled baseline-identical.

The five skips are Windows symlink privilege, three POSIX shell/PATH-specific tool tests and the unavailable Rust wasm32 target. Eight deselections are only duplicate parity-marker wrappers. Old enum-reservation exclusions are obsolete and were not used.

Global before/after evidence reports unchanged five HEADs, 718 selected source hashes, 736 raw associations, all 45 Swift owned files, five protected sources, 35 excluded artifacts, five indices and 47 locks/manifests. The unchanged accepted TypeScript R1 315-test/typecheck/build evidence is reused with its exact 28-file/11-file-override association; no fresh standalone library gate is claimed. Passing broad tests do not cover or close the additional flat-supplied cutoff below.

## Problem, requirement provenance, and scope

The operator requested all nine native backends, with Swift last: mandatory complete immutable metadata, opt-in exact instance validation, one canonical foundation/report owner, preserved mutable drafts and codecs, explicit runtime delivery and executable conformance. The controlling Authority records later implementation/review/regression/checkpoint directions superseding the proposal's earlier documentation-only restriction. The concrete Swift gaps were absent metadata/validation/delivery and uncompilable direct recursive structs.

The assigned component scope authorizes Swift production/resources/tests/examples and necessary shared scaffold/CLI/driver/wheel integration. Root expressly authorized direct-size recursive SCCs as final classes and the behavior-preserving Go ownership-kernel extraction. User authoring files, reference libraries, other codecs/validators and dependencies remain reference-only; the resource glob is the bounded packaging exception.

Existing toolchains and compiler routes demonstrate feasibility: the native test compiles the old recursive struct and observes its recursive-storage rejection; the current class projection and source/package/flat applications compile/run. No new dependency, library repository, discovery mechanism, compiler or infrastructure prerequisite was introduced. Source/package and explicit/supplied alternatives were exercised through the existing route. Local fixes remain appropriate for the recovery defect; it does not justify authoring redesign or broader native changes.

No unsupported prerequisite, unauthorized expansion or missing authority was established. Virtual selection, native Swift JSON absence, cyclic-object serialization and arbitrary changed-struct binary resilience retain their expressly documented limits. Those limits do not exempt default-flat output recovery from the required fail-closed contract.

## 1. Findings

### [P2-1] Flat supplied retry falsely succeeds after the runtime owner receipt retires first

**Location:** `src/taut/gen/owned_runtime.py:50–54,86–95`; reached through `swift_runtime.py:82–85`. The persistence ordering is `python_runtime.py:262–271`: all writes precede iteration over the unordered deletion set.

**Violated invariant:** Interrupted retirement must either complete known cleanup or refuse unchanged. It must never report success while obsolete runtime sources remain without ownership evidence. The default flat supplied placement has the same recovery obligation as package and explicitly imported supplied placements.

**Exact reproduction:** Run the retained `scratch/probes/receipt-first.py` with the assigned activation and cloned compiler. For each validation setting:

1. Generate `schema(Record=Msg(value=F(1, INT)))` using `emit(..., langs=['swift'], services=[], runtime=True, validation=enabled)` in a fresh owned scratch root. Default source mode records/imports `TautFoundation` and positively owns four OFF-mode or six ON-mode runtime files.
2. Request the same schema with runtime options and module binding omitted: `emit(..., langs=['swift'], services=[], validation=enabled)`. This is the explicitly supported default flat supplied placement.
3. Persist the **actual planned writes** using the normal application function. This installs the new flat API and schema receipt with `mode='supplied'`, `source_root=null`. Persist deletion of only `.taut-swift-runtime.json`, then inject `OSError` before deleting any runtime source. The owner receipt is a member of the actual deletion set; deleting it first is a permitted iteration order. Context cleanup releases the generation locks. No invented manifest or source content is used.
4. Retry the identical flat request.

**Observed result, both OFF and ON:** generation returns successfully, every retry-state byte remains unchanged, and all four/six old runtime sources remain while their owner receipt is absent and the schema receipt says `source_root=null`.

OFF leftovers are `cbor.swift`, `ext.swift`, `paths.swift`, `descriptors.swift`; ON additionally retains `reports.swift`, `validation.swift`.

**Expected:** Complete positively justified cleanup, or a named unchanged refusal requiring inspection/migration. Success is not a legal result for this incomplete retirement.

The controls isolate the cause: the exact owner-receipt-first sequence for Swift package and explicitly imported supplied placement refuses unchanged in both modes. The original four Go package/imported-supplied states also refuse unchanged.

The planner writes away `old.source_root` before stale deletions complete. After the runtime receipt disappears, a retry's manifest defaults to an empty owner. Its unknown-runtime scan runs only for source/package, a nonempty import, explicit consumption or an existing owner receipt. Flat supplied has none of those conditions. It therefore overlooks the orphaned sources and publishes success. Existing Swift cutoff tests pass `module='TautFoundation'` even for `mode=None`, so they exercise the nonempty-import control rather than this placement.

**Impact:** A normal supported source-to-flat-supplied transition can falsely appear complete after an ordinary persisted interruption, leaving generator output that is no longer tracked as owned runtime state. Subsequent generation cannot safely account for those files; applications assembling runtime sources can encounter unexplained stale/duplicate definitions. This is a concrete recovery and diagnosability defect, without demonstrated data loss.

**Required correction:** Preserve enough retirement evidence, or otherwise enforce safe cleanup/refusal, so omission of an import cannot turn this reachable incomplete retirement into success. Preserve the supported fresh default-flat route, actual single-owner composition, positively owned cleanup, other users/engines and unknown/handwritten-file preservation. No silent orphan adoption or deletion based only on filenames.

**Closure test:** Replay the exact persisted receipt-first sequence for default flat supplied with validation OFF/ON, requiring complete known retirement or unchanged named refusal. Include mode changes in validation, ordinary cutoff positions, package/imported controls, surviving shared users and handwritten files. Keep all nine pre-lock alias checks, accepted Go old/new behavior and existing native/default-flat composition checks passing. The originating State reviewer must verify the actual corrected counterexample.

## 2. Invariant analysis

**Native identity and report ownership held in the executed cases.** Direct nullable self/mutual recursion becomes final classes; ordinary and collection-recursive storage remains structs, with required initializer arguments retained. Actual object/type/schema/fingerprint identity detects real cycles while finite prefixes, copied values and shared children retain every reachable path. Local excludes descendants; recursive traverses populated nonselected children. Fast/report results share the predicate stream. Instrumented fast calls construct no issue/report, and old reports retain snapshots after mutation.

**Metadata and binding boundaries held.** Static descriptors retain complete normalized inventories and immutable value snapshots. Lazy links resolve typed edges without expanding recursive graphs per instance. Registry category/owner checks, metatype-bound adapters and unsupported-rule rejection fail as configuration. Actual separately built disabled children are reused; replacement enums/rules/effective codec/forward-compat facts reject, including enum inventories referenced only inside imported children. Reordered equivalent facts and unequal compatible build labels pass. True re-export facades preserve nominal ownership; selected stale/no-op facade exports and split foundation modules fail.

**Canonical delivery held.** The real wheel includes nested canonical Swift resources; isolated generation and native applications use those bytes. OFF applications compile without reports/engine. Default-flat multi-schema/disabled-child cases preserve generated bytes through filename-only copies. Unicode/emoji native IR retains original metadata/report names. Constructors/setters/CBOR preserve invalid drafts; no implicit selection or validation is introduced.

**Shared ownership held except P2-1.** The extraction reproduced accepted Go write/deletion plans exactly in the independent comparisons. Native retirement/return, live remap rejection, remaining users/engine, malformed/modified/missing ownership, raw namespace checks and nine-target previous-root alias-before-lock checks passed. Complete planning and common preflight protect unknown/handwritten output from partial conflict mutation. Persisted package/imported-supplied cutoffs recover or refuse unchanged, including forced receipt-first states. The new default-flat placement exposes the missing branch; passing those other states does not establish a closed recovery grammar for it.

## 3. Risks and next action

One bounded recovery defect remains open. The completed exact-tuple global gate has no new test failures and all16 parity is green, but neither result exercises the demonstrated default-flat receipt-first state. The three historical baseline failures remain visible and outside this correction.

The next action is one lane-owner merged remediation plan that resolves P2-1 alongside any independently filed blocking findings, followed by a corrected settled tuple and originating-axis closure. Preserve the failed probe, exact global receipt and original testimony. This review authorizes no production edit, release, tag, registry publication or reviewer Git operation.
