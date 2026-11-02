# SwiftOneOfCheckpoint — STATE-AXIS REVIEW

**Review object:** Originating State closure, remediation round 1: Taut `c02765930f06cfcb19a522843aa54582db514706..848f6e749f607d82b93941095f0cbbc7f10bbabf`, exact 135-path corrected checkpoint, with controlling `dev-docs/SwiftOneOfCheckpoint-RemPlan-1.md` at the corrected commit. Production frozen; acceptance pending. Workspace `a8f37984471654902149d136b7a13a588346b58f..331e760dc04e0d671b19c8d2ed394dfa4d49c6af` contains two managed receipt changes. The original Swift package remains review context.

**Baseline:**

| Repository | Exact corrected HEAD |
| --- | --- |
| Taut | `848f6e749f607d82b93941095f0cbbc7f10bbabf` |
| Workspace | `331e760dc04e0d671b19c8d2ed394dfa4d49c6af` |
| taut-shape-py | `c08c2a1b5197f761c5b0b835c588da512130ceda` |
| taut-shape-rs | `8e92b89ed3a4f218a5a4e018fbfee6301fcc14b4` |
| taut-shape-ts | `1aaeab65e4564a462044d2f5d824cd2f375aae97` |

Source inspection used the committed diff, historical `git show` and the same original isolated full-history clone, updated in place at `D:/projects/limbo/swift-oneof-scratch/review-r0/state-raw/taut-dev`. All new execution outputs stayed in `D:/projects/limbo/swift-oneof-scratch/review-r1/state-raw/scratch`.

**Date:** 3 November 2026, Australia/Sydney.

**Axis:** STATE - durable ownership transitions, restart legality, physical roots and locks, immutable metadata, typed native identity and snapshots. Independent, adversarial, read-only. The other axis runs in parallel; nothing here relies on its current-round report. Filed verbatim by the lane owner.

**Verdict: GO** - original State P2-1 is CLOSED. No open P0, P1, P2 or P3 State finding and no new architectural or nonarchitectural root established. This is originating State closure on the exact corrected tuple, not a claim of overall acceptance or a corrected-source global gate.

---

## 0. Evidence base

### Authority, diff and integrity

Read the full generated R1 canonical prompt and setup, both initial complete reports, merged initial verdict, root-authorized RemPlan-1, Authority-1, Preparation-R1, FocusedResults-1, RESULTS-R1 and the pertinent retained probes/results. The full build proposal and original Authority/Draft/Preparation/UserEnumCaseIntegration requirements remain the previously read controlling context; their historical source association was preserved.

Prompt SHA256 verified as `d1e1207bc9988d47cd92393859ec84e66e9bfff00a06b7431c84bce3a5622990`; setup SHA256 verified as `9ce568b07addef322f6e6aeda491613e4af70bb02c8ed1f9cfae4c0f320171ea`. Imported `taut.__file__` resolved inside the updated isolated clone after dot-sourcing the new R1 activation.

Reviewed the complete corrective production diff, exactly these 12 paths:

- `src/taut/gen/owned_runtime.py`: typed retiring-root grammar, root participation, remnant checks, positive ownership and durable provenance.
- `src/taut/gen/scaffold.py`: previous-root discovery, existing lock coverage and locked provenance expansion checks.
- `src/taut/gen/swift_metadata.py`: native unit result type and the narrowly scoped Foundation diagnostic.
- `src/taut/gen/runtime/swift/{paths,descriptors}.swift`: defining-module helper qualification.
- `src/tests/{test_go_oneof,test_swift_oneof}.py`: shared recovery and native namespace controls.
- Four existing Swift surface goldens and `docs/SWIFT_API.md`.

Detailed State inspection covered `owned_runtime.py:11-49,51-186`, `scaffold.py:932-966`, and unchanged `python_runtime.py:49-163,242-271`. Revisited the affected descriptor link, native binding and reference-identity code, original predicates/reports and native recursive projection. Verified that the Swift emitter, canonical CBOR/extension sources, report resource and validation resource are byte-identical to r0. Go emitter/metadata bytes also retain their accepted association.

All 134 non-self Preparation hash/size records verified, as did all 30 frozen source-inventory entries. The current inventory identity is `7be5937d06eab85d3f1b2f579b18cb36b476d3a8cc79de43812675c457f76b49`. Independently verified 55 R1 evidence-inventory files and the copied 37-file r0 global inventory. The five protected user sources match their integrated hashes. The supplied pre-staging protection receipts retain the 35 excluded artifacts, five indices and 47 locks/manifests; excluded saved-workspace artifacts were not built or modified by this reviewer.

At start and end, all five HEADs matched the table, tracked/index diffs were empty, and all **1,237 setup raw-associated hashes** matched: workspace 55, Taut 948, Python shape 75, Rust shape 63, TypeScript shape 96. No reviewed source, Git state, dependency, reference library or original r0 probe was modified.

### Original counterexample replay

Copied my original `receipt-first.py` into new R1 scratch without changing its bytes. Its SHA256 remains `8d7355596d0832fb835c714cb646de41f2648b047aec901f31eaf07b89eca003`.

The unchanged probe uses the actual current plan and normal application function: generate source; request runtime/module omission; persist every actual planned write; delete only the runtime-owner receipt from the actual stale set; raise the persisted cutoff; then retry. It does not manufacture a manifest or substitute filename-based ownership.

Both original default-flat OFF/ON counterexamples now produce a named `unknown/handwritten Swift runtime ...` refusal, with every retry-state byte unchanged. The four runtime sources in OFF mode, or six in ON mode, remain untouched. The schema receipt retains the canonical prior root in `retiring_source_roots` despite `source_root=null`. Package and imported-supplied controls continue to refuse unchanged. No stale generation lock remains.

Receipt: `scratch/probes/receipt-first-results.json`, SHA256 `465347ba3ca2a06f11040ce9eda2ec97b0109eea2ae918b43c377df9104117c1`. The script exited zero and explicitly records all six named refusals and unchanged snapshots. The original failing r0 result remains preserved separately.

### Independent focused execution

Used the assigned R1 activation, existing CPython 3.13.5/Swift 6.4.2/native Go, disabled bytecode/plugin autoload/cache provider and owned scratch basetemps/XML paths. No install, saved-workspace build, broad suite or parity wrapper ran.

| Independent execution | Result |
| --- | --- |
| `test_go_oneof.py -k 'retiring or default_source_owner_retires or external_retirement or actual_selected_source_import_remap or source_package_consumer'` | **299 passed, 88 focus-nonselected**, no failures/skips, 31.16 seconds; `scratch/state-tests.xml` |
| Swift namespace/supporting identity selection described below | **50 passed, 106 focus-nonselected**, no failures/skips, 167.62 seconds; `scratch/native-tests.xml` |
| Pair complete-plan node plus all nine previous-owner alias-before-lock cases | **10 passed**, no failures/skips, 0.67 seconds; `scratch/prelock-tests.xml` |

All used `python -m pytest -q -p no:cacheprovider` with R1-owned `--basetemp` and `--junitxml`.

The 299 include both Go and Swift: actual receipt-first OFF/ON and validation changes, same/separate prior roots, package/imported/default-flat placements, 160 ordinary default-flat cutoff combinations, proof clearing and source return, legitimate caller-supplied files, users/engine retention, multiple actual unfinished moves, positive-owner failures, malformed/raw provenance, pending-root aliases, actual dangling aliases, locked expansion and multi-target planning. Existing native Go retirement/return/remap/consumer controls also execute.

The Swift selection expression was `native_helper_type_names or foundation_module_shadow or foundation_flat_collision or attributed_native_surface_goldens or existing_valid_native_enum_case_spellings or native_emoji or imported_qualified_engine_helpers or native_struct_class_mutual or owned_metadata_lazy or binding_type_mismatch`. It compiles/runs all five original helper-type names OFF/ON in flat/imported scopes, Void source/package, Foundation message/enum imported source/package/supplied OFF/ON, and supporting identity, snapshot, lazy-link, binding/configuration, native-name and golden controls. Flat Foundation/unchanged Swift refusals occur before locks/output.

Separately crafted actual Windows dangling-junction controls for BOTH Go and Swift. Each starts from a real source retirement with retained prior-root proof; creates a junction at a canonical runtime filename; removes its empty target directory; records `exists=false`, `is_symlink=false`, lstat reparse=true and `_is_alias=true`; then retries. Both now refuse named and byte-unchanged, keep the junction and retiring proof, and release locks. The probe exited zero. Receipt: `scratch/probes/dangling-independent-results.json`, SHA256 `9efd8a6349d7b8501485730c46760f749258cc06b4f352751bf75a41be6e5ab8`.

Re-executed the retained old/current Go comparison in owned scratch after rebinding only its repository path to the isolated clone. Ten plans yield **six exact maps and four intentional schema-receipt provenance-only deltas**. Every other write byte and deletion set matches accepted behavior. Receipt: `scratch/probes/go-equivalence-r1-independent.json`. No universal byte-equality claim is made after the authorized persistence correction.

These results overlap supplied gates and are not summed.

### Supplied corrected-source and historical evidence

Verified current source association and XML for the final inventory: Swift affected **101 passed**, 55 focus-nonselected; Go/shared **405 passed**; current wheel/prelock/planning **11 passed**; five native example executions succeeded. No skips/failures are reported. The earlier 186-pass full Swift receipt stays at source inventory `48d9bddb268230d07ce50201bb051a3d5c80ca6e48b0959359416f3f431520c6`, before the final alias-remnant hardening. It is not relabeled as a final-source full-suite run.

Independently opened the retained current wheel, SHA256 `80384ae2d6e78873b3fd3c28f79d136442c565251fcdd0921649d83c3a326bc9`. All six canonical Swift resources plus current `owned_runtime.py`, `scaffold.py` and `swift_metadata.py` match its archive bytes. Its current receipt covers extracted-wheel `-I -S` generation and native source/package/default-flat applications. No redundant wheel build was needed.

The complete r0 global package remains evidence of **Taut c0276593/workspace a8f37984**, with the three unchanged shape revisions, not this corrected tuple. Its 37 inventory files verified in the clone; human/machine summary, execution/integrity data, baseline proof, classifications and retained failure tracebacks remain consistent with the complete receipt consumed in my original review:

- All 16 require-all codec variants GREEN; zero governance violations.
- Broad **2,260 passed, three exact historical failures, five skips, eight duplicate parity-marker deselections; 2,268 selected**, pytest exit 1.
- Failures remain the missing historical proto-surface document and two Windows Go CRLF/gofmt checks. User enum.case tests stayed enabled; no obsolete reservation exclusion returns.
- Skips retain the Windows symlink-privilege case, three POSIX-specific tool/PATH cases and unavailable Rust wasm32 target. Real junction controls execute independently.
- Prior TypeScript R1 315-test/typecheck/build receipts retain their exact source association; no fresh standalone library result is claimed.

There is no corrected-source broad/full16 claim or new global wait barrier.

## Problem, requirement provenance, and scope

The operator's requested Swift outcome remains immutable mandatory metadata, optional exact validation, shared canonical runtime delivery, native typed traversal and preserved mutable drafts/codecs. Original State P2-1 demonstrated a concrete failure of its supported source-to-default-flat lifecycle: after actual writes and owner-receipt-first retirement, retry reported success while losing all provenance for leftover runtime files. The initial Code report independently demonstrated ambient helper-name compilation failures.

Authority-1 and the root-authorized merged RemPlan-1 explicitly permit this one corrective window, its optional typed retiring-root fact, existing lock discovery/recheck extension, helper qualification and proved Foundation-only flat restriction. The final dangling-junction predicate is within that same unknown/alias-remnant refusal scope. The exact 12 production paths and attributed evidence fit that authority. Reference shapes, dependencies, authoring/model/IR and other native codecs/validators remain preserved.

The persisted fact is necessary at the demonstrated boundary: unconditional scanning would reject legitimate nonowning flat caller sources; deletion ordering alone would not preserve a separate prior root after the active pointer changes. Keeping prior canonical root provenance inside the existing schema receipt supports safe refusal without a new journal, transaction engine, public option or orphan-adoption authority. Native qualification preserves the five original names. The separate Foundation shadow probe demonstrates the defining-module collision, and the authorized flat restriction has a working imported alternative rather than a blanket name ban.

No unsupported infrastructure prerequisite, unauthorized component expansion or unresolved necessity gap was established. Existing compilers, runtime resources, receipts and application routes suffice. The correction does not repair already-stranded historical r0 scratch states whose provenance was erased; no authority is invented to infer ownership there.

## 1. Findings and prior-finding closure

No new finding is raised. This is my independent originating-axis closure, not implementer self-closure or adoption of the current peer verdict.

| Original State finding | Exact replay and corrected behavior | Closure evidence | Disposition |
| --- | --- | --- | --- |
| **P2-1 - Flat supplied retry falsely succeeds after owner receipt retires first** | Unchanged original probe source, actual planned writes, original OFF/ON default-flat sequence and receipt-first deletion now retain the physical prior root and refuse unknown runtime unchanged. Package/imported controls remain safe. | Original-source replay receipt; 299-case both-target state gate including validation changes/separate roots/cutoffs/users/locks; independent actual dangling-junction controls; inspected persistence and lock grammar. | **CLOSED** |

The prior Code P2-1 was legitimate merged-round input. I independently exercised its coupled State-relevant native controls, but its originating Code reviewer retains responsibility for that ID.

**New-root classification:** This review established no new architectural or nonarchitectural defect at the corrected tuple. The retained failed pre-freeze dangling-junction probe is an incomplete remnant predicate within the same M2 recovery root: exists-only checking missed an actual lstat reparse point. Its bounded correction reuses the existing alias helper and is independently replayed above. It adds no new ownership model, public ABI or architectural root. The Foundation restriction is the explicitly authorized, evidenced namespace disposition within M1, not an agent-invented prerequisite.

## 2. Invariant analysis

**Provenance survives every relevant write/delete boundary.** New retiring roots are stored in the ordinary schema-receipt write before stale deletion starts. Both active and retained roots participate in planning. Missing active owners still fail. A missing retiring owner with any canonical source remnant refuses; positive file hashes, contracts and users remain required for deletion. The retained list itself grants no file ownership. The original receipt-first state cannot erase its last known root before the refusal scan on retry.

**The recovery grammar clears proof only after observation.** Clean retirement may retain a harmless root entry for one further generation. A subsequent consistent owner or absent owner without canonical remnants permits proof clearing. Caller-owned flat sources are legal in fresh/repeated nonowning generation and after completion has been verified. Modified, unknown, partially missing or aliased runtime state is not adopted. Actual two-move interleavings retain both old roots; an unresolved earlier root prevents a later false success.

**Physical identity and lock coverage remain fail closed.** Typed strings are checked before Path coercion/lock creation, reject malformed, duplicate/noncanonical, relative, ambiguous namespace and reparse/obstructed roots, and share the existing physical identity rules. Prior roots are locked before planning; the locked reread refuses expansion to an uncovered root. All nine old active-owner alias-before-lock cases still pass. Complete multi-target planning prevents an orphan in one target from partially applying another target's changes. The common atomic replacement/deletion implementation is unchanged.

**Users and engines remain positively accounted.** Clean source retirement, return and actual live import remap refusal continue working. Remaining source users retain the owner and any needed validation engine. Unrelated handwritten files survive. Retained old-root proof does not change Go's native outputs or deletion sets; the independently observed receipt deltas are the intended add/remove provenance fact.

**Native metadata and values preserve their semantics.** Defining-module qualification changes helper resolution, not type identity or representation. Static metatype-bound adapters and reference identity still distinguish actual objects/types/schema bindings; ordinary and collection recursion remain values, direct recursion remains final classes. Replayed cycles/shared values, finite prefixes, copied values, snapshots, lazy links and mismatch configuration checks pass. Immutable reports and the common predicate stream are byte-unchanged. No constructor/setter/codec acquires implicit semantic validation.

**Namespace correction is narrowly bounded.** Data, NSLock, ObjectIdentifier, AnyObject and Void compile in their original supported placements. Void uses native unit syntax in the holder. Foundation refuses only where its local declaration hides the defining module; source/package/imported-supplied message/enum controls pass. The pre-existing Swift reservation stays intact. Unicode/emoji, existing enum cases, qualified helper fields and attributed goldens remain supported. No blanket imported-name restriction, new module or discovery/build invocation was introduced.

## 3. Risks and next action

No open State defect remains at the corrected tuple. R1 evidence is focused corrected-source execution and verified current packaging, with the complete global package retained only at its original r0 tuple. The three historical broad failures remain visible; virtual selection, native JSON absence and existing native serialization/layout limits retain their original scope.

The next action is the lane owner's merge of the same two originating reviewers' verdicts on this exact corrected tuple and verbatim filing of the closure reports. This State GO does not itself authorize release, tagging, registry publication, an individual push or another global gate. No source fix or Git mutation was performed by this reviewer.
