# SwiftOneOfCheckpoint — CODE+Surface-AXIS REVIEW

**Review object:** Remediation round 1, Taut `c02765930f06cfcb19a522843aa54582db514706..848f6e749f607d82b93941095f0cbbc7f10bbabf`, exact 135-path corrective checkpoint: 12 production/test/golden/documentation changes plus attributed evidence. Controlling document: `dev-docs/SwiftOneOfCheckpoint-RemPlan-1.md` at the corrected commit. Workspace `a8f37984471654902149d136b7a13a588346b58f..331e760dc04e0d671b19c8d2ed394dfa4d49c6af` changes exactly two managed receipt files. Production frozen; originating closure pending this review.

**Baseline:**

| Repository | Corrected reviewed HEAD |
| --- | --- |
| Taut | `848f6e749f607d82b93941095f0cbbc7f10bbabf` |
| Workspace | `331e760dc04e0d671b19c8d2ed394dfa4d49c6af` |
| taut-shape-py | `c08c2a1b5197f761c5b0b835c588da512130ceda` |
| taut-shape-rs | `8e92b89ed3a4f218a5a4e018fbfee6301fcc14b4` |
| taut-shape-ts | `1aaeab65e4564a462044d2f5d824cd2f375aae97` |

Sources were inspected in the SAME original isolated full-history clone at `D:/projects/limbo/swift-oneof-scratch/review-r0/code-raw/taut-dev`, updated in place before dispatch. Read committed diffs against `c0276593`; original baseline controls and failed counterexamples retain their earlier revisions and bytes.

**Date:** 3 November 2026, Australia/Sydney.

**Axis:** CODE + Surface — originating closure of Code P2-1, native naming/placement controls, public migration surface and coupled shared-ownership sanity. Independent, adversarial, read-only. The other axis runs in parallel; nothing here relies on its current report. Filed verbatim by the lane owner.

**Verdict: GO** — original Code P2-1 is CLOSED. No open Code P0, P1, P2 or P3 finding and no new architectural or nonarchitectural root identified. This is the original Code reviewer's round-1 closure on the exact corrected tuple; State's originating closure remains its own responsibility.

---

## 0. Evidence base

### Scope, cold surface and source integrity

Read the complete generated continuation prompt and setup. Verified their SHA256 values respectively as `06f0d4ddf5bbdf21aa874913588286032e0cb40722ddf4fc6ee153753b7ef470` and `e292ae45a5db387c6e799259d66b8637589d0582c11a768a55101de554c5572c`.

Before the corrected plan/code, re-read current root/gen help, the complete Swift API page and example build notes. The other command families and their cold-read results remain from the original review; the corrective diff changes no CLI declarations. Subsequently read both complete initial reports, merged initial Verdict, Authority-1, RemPlan-1, Preparation-R1, FocusedResults-1, RESULTS-R1, retained original probes and corrected focused evidence. Original Authority/Draft/Preparation, full build-proposal requirements and applicable AGENTS/review-loop instructions remain the original review context.

Inspected the complete corrective production diff, particularly:

- `swift_metadata.py:46–79,163–170`: placement-scoped preflight and the generated holder's unit result type.
- `runtime/swift/paths.swift:19–23` and `descriptors.swift:46–53,193–318`: defining-module Foundation helpers and qualified Swift identity/reference constraints.
- Complete `owned_runtime.py:1–185`: typed prior-root provenance, planning, positive ownership and remnant checks.
- `scaffold.py:929–969`: previous-root discovery before locks and under-lock provenance expansion rejection.
- New Swift naming/placement tests, shared Go/Swift retirement tests, four attributed goldens and updated Swift build notes.

At BOTH boundaries, verified the exact five HEADs above, empty tracked/index diffs and all **1,237** setup-associated raw tracked-file hashes. No mismatch. Independently verified all 134 non-self Preparation entries, the 30-file source inventory and the exact 135-path committed allowlist. Source inventory identifier: `7be5937d06eab85d3f1b2f579b18cb36b476d3a8cc79de43812675c457f76b49`.

The workspace delta is exactly `gwz.conf/gwz.lock.yml` and `gwz.conf/markers/conf-integrity.yml`. Confirmed unchanged common application machinery, Swift native representation emitter, canonical CBOR/extension sources, report/validation resources, protected authoring sources and dependency manifest. Reference HEADs remain unchanged. Excluded 35 saved-workspace artifacts are covered by the retained protection receipts, not by a claim that this isolated clone rebuilt them.

Used the NEW R1 scratch activation, existing CPython 3.13.5/Swift 6.4.2/Go tools, disabled plugin autoload/bytecode/cache provider, and confirmed imported compiler source under the isolated clone. Every new probe/output stayed under `D:/projects/limbo/swift-oneof-scratch/review-r1/code-raw/scratch`. No reviewed source edit, install, Git mutation, network operation or saved-workspace build was performed.

### Independent original-counterexample replay

Executed the scratch script:

```text
python D:/projects/limbo/swift-oneof-scratch/review-r1/code-raw/scratch/probes/native-replay.py
```

It explicitly builds current canonical foundation artifacts separately for validation OFF and ON. OFF artifacts contain no report/engine sources. It then generates each original schema unchanged:

```python
schema(**{name: Msg(value=F(1, INT))})
```

Every native compilation and executable returned zero:

| Replay | Native applications |
| --- | ---: |
| Data, NSLock, ObjectIdentifier, AnyObject, Void × flat/imported × OFF/ON | 20 |
| Void × source/package × OFF/ON | 4 |
| Foundation message/enum × imported source/package/supplied × OFF/ON | 12 |

The applications exercise construction, mandatory descriptors, codec round trips and enabled validation/report completeness. Source-mode delivered resources are checked byte-for-byte against the current canonical closure. No generated content rewriting is used.

Four additional Foundation message/enum × OFF/ON flat requests reject with the explicit imported-runtime migration diagnostic BEFORE any generation lock opens or output directory is created. The probe records all 72 application compile/run command arrays, exits/stdout/stderr and four refusal records in `scratch/probes/native-replay/results.json`. The unchanged original R0 failed matrices and baseline controls remain preserved.

An initial scratch script-export attempt failed before execution because the new probes directory did not exist; after creating that owned directory, the complete replay above ran successfully. It supplied no native result before that correction.

### Independent focused checks and coupled-state probes

Executed the prescribed naming selection from `test_swift_oneof.py`:

```text
-k "native_helper_type_names or foundation_module_shadow or foundation_flat_collision or attributed_native_surface_goldens or existing_valid_native_enum_case_spellings or native_emoji or imported_qualified_engine_helpers"
```

Result: **47 passed, 109 focus-nonselected**, no failures/skips, 151.73 seconds. Receipt: `scratch/native-tests.xml`.

Executed `test_go_oneof.py -k retiring`: **242 passed, 145 focus-nonselected**, no failures/skips, 14.52 seconds. Receipt: `scratch/shared-state.xml`. This covers both targets, actual receipt-first writes, default-flat cutoffs, validation changes, same/separate roots, remaining users, multiple actual unfinished moves, malformed/aliased provenance, dangling Windows junction remnants, locked expansion and multi-target planning.

Executed the current Swift wheel test, all nine previous-owner alias nodes, pair preplanning, the exact disabled-name/keyword test and both existing JVM/ECMA help nodes: **14 passed**, no failures/skips, 36.52 seconds. Receipt: `scratch/delivery-checks.xml`.

Independently reopened that freshly built wheel, SHA256 `2c2557c87f92281f95d5dd6557f49fd735f52286832e6e3f0d994202e136be5f`, and matched all six canonical Swift resources plus current `owned_runtime.py`, `scaffold.py` and `swift_metadata.py` bytes. The wheel test executes isolated `-I -S` generation and native source/package/default-flat applications.

Also executed an independently written coupled-state script:

```text
python D:/projects/limbo/swift-oneof-scratch/review-r1/code-raw/scratch/probes/flat-recovery.py
```

For Go AND Swift, it intercepts the actual common application boundary, persists actual planned default-flat writes, deletes only the actual prior runtime receipt from the stale set, and interrupts before source deletion. Across old/new validation OFF/ON and same/separate prior roots, all **16** retries refuse with named unknown-runtime errors and identical retry-state bytes. Handwritten content survives and locks release. Separate fresh/repeated nonowning flat and clean-retirement/proof-clearing controls pass for both targets. Receipt: `scratch/probes/flat-recovery/results.json`.

These counts overlap each other and supplied gates; they are not added into a broad total. No full broad, all16 parity wrapper or redundant full Swift suite was run.

### Retained evidence and source association

Independently verified all **55** files in the R1 evidence inventory and all **37** files in the copied completed `results-global-r0` inventory against recorded size/SHA256; no mismatch. Read current human/machine summaries and retained failure/integrity evidence.

Final-source implementer receipts at inventory `7be5937d…` report 101 Swift affected passes, 405 Go/shared passes, 11 wheel/prelock/planning passes and five native examples, without skips. The 405 comprises 145 existing Go cases, 242 new shared state cases, 12 scaffold, four map and two help cases. Counts overlap. The earlier full 186-pass Swift receipt remains associated with inventory `48d9bddb…`; it is not relabeled as a full run after the final alias-remnant change. Native generator/canonical bytes were unchanged by that last delta, and affected checks/current wheel/examples followed it.

Read the retained Go comparison evidence: six old/current maps are exactly equal; four differ ONLY by the intentional retirement-provenance receipt fact. All other write bytes and deletion sets match. Universal byte equality is no longer claimed after the authorized M2 correction.

The complete global package remains OLD-TUPLE evidence at Taut `c02765930f06cfcb19a522843aa54582db514706` / workspace `a8f37984471654902149d136b7a13a588346b58f`: all16 require-all GREEN, zero violations; 2,260 broad passes, three exact historical baseline failures, five classified skips, eight duplicate-marker deselections, 2,268 selected. User enum.case tests stayed enabled. The missing historical proto-surface document and two Windows CRLF/gofmt failures remain visible. No corrected-source broad-green result or new standalone library gate is claimed, and no new global wait barrier applies.

## Problem, requirement provenance, and scope

The original operator outcome remains mandatory immutable native metadata, explicit optional validation, shared reports/typed traversal, preserved drafts/codecs and canonical single-owner source/package/supplied delivery across all nine backends. Code P2-1 demonstrated that new ambient helper references broke five previously compiling Swift message names. State P2-1 separately demonstrated false success after default-flat receipt-first retirement.

Root expressly authorized ONE merged RemPlan-1 window and the exact component scope. M1 qualifies Foundation/Swift helpers and preserves all five original names. M2 adds optional typed retiring-root provenance within existing schema receipts/locks; it grants no file ownership. The dangling-junction condition uses the existing lstat/reparse helper within the same unknown-remnant refusal scope. No new module, descriptor/codec/report ABI, public option, transaction engine, dependency or historical orphan-repair process is introduced.

The Foundation exception has concrete necessity evidence: the retained native probe compiles the ambient-helper Foundation declaration, then fails after qualification with `type 'Foundation' has no member 'Data'`. Root specifically approved that one flat declaration restriction after seeing the evidence. It is not an agent-created blanket name ban. Imported message/enum source/package/supplied OFF/ON routes remain usable and independently passed. Swift was already reserved; the initial raw-emitter probe bypassed its normal preflight, and its mistaken expectation is preserved and corrected in the evidence.

The remedy addresses both observed failures locally. Unconditional filename scanning would break legitimate nonowning flat callers, while deletion ordering alone loses separate prior-root identity. Retaining the prior root in the existing receipt preserves evidence without inventing ownership or infrastructure. Unknown remnants still refuse; only verified manifests/users/hashes permit deletion.

The 12 changed production/test/golden/documentation paths fit the approved scope. Protected user sources, other codecs/validators, libraries, dependencies and original canonical CBOR/extension bytes remain preserved. No unsupported prerequisite, unauthorized expansion or blocking provenance gap was identified.

## 1. Findings and prior-finding closure

No new finding is raised. Closure below is the original Code reviewer's independent judgment, not implementer self-closure.

| Original finding | Original-counterexample result at corrected tuple | Correction and closure evidence | Disposition |
| --- | --- | --- | --- |
| **Code P2-1 — Unqualified helper types produce uncompilable accepted schemas** | All five unchanged message schemas compile AND run in OFF/ON flat/imported placements. Void also compiles/runs through source/package. | `Foundation.Data`, `Foundation.NSLock`, `Swift.ObjectIdentifier`, `Swift.AnyObject` and native `()` holder result remove the demonstrated ambiguity. Independent 20+4 application replay, 47 focused native/surface cases and current wheel verification pass. Foundation's approved flat-only restriction rejects before locks/output, while 12 independent imported Foundation applications pass. | **CLOSED** |

The merged State P2-1 received supporting Code sanity verification through 16 independently forced default-flat retries, fresh/clean controls and 242 shared regressions. That evidence is not a Code claim to close the State finding; its original reviewer retains closure authority.

**New-root classification:** None identified. The Foundation migration restriction is a bounded, explicitly authorized consequence of M1's defining-module qualification, with preserved imported alternatives. The final dangling-junction check is a bounded M2 remnant-detection correction using the existing alias helper. Neither introduces a new architectural root, new native model or new mutation engine. No unresolved nonarchitectural finding was established.

## 2. Invariant analysis

**Naming and public Surface.** The five original names are preserved rather than reserved. The holder uses native unit syntax, so schema Void no longer changes its result type. Foundation helpers bind to the defining framework; Swift identity/reference constraints bind to the standard module. Current help retains runtime omission/source/package defaults, optional validation and external mappings under `gen`. No new lifecycle verb or option is introduced. Updated API notes explain the one Foundation flat restriction, explicit imported migration, retirement refusal and fresh/repeated nonowning route. The original first-day lifecycle remains applicable; corrected native source/package/default-flat uses execute through the current wheel and replay. Keyword, native enum-case, emoji and validation-disabled field controls pass.

**Typed metadata and native semantics.** Qualification names the same actual helper types; it does not change public descriptor/report/codec contracts. Native representation, engine, reports and core codec sources are unchanged. Binding metatype/representation checks and actual object/type/schema/fingerprint identity remain intact. No instance graph or nominal owner copy is introduced. The original native identity, invalid-draft, local/recursive, fast/report, imported-child and snapshot proofs retain their unchanged implementation boundary; the current wheel, goldens and naming applications verify the changed resource route.

**Persisted provenance is not ownership.** `retiring_source_roots` accepts a deduplicated canonical absolute list, checks raw namespace/aliases before coercion/locks, joins the normal lock set, and is re-read under lock. A concurrently expanded root set refuses before application. Roots with scheduled stale cleanup persist in the normal schema receipt before deletions. A later consistent plan may clear completed provenance; partial/missing active owners remain errors. Retiring roots with unknown canonical files or actual dangling reparse remnants refuse unchanged. File names and canonical byte equality do not authorize adoption/deletion.

**Recovery and composition.** Independent receipt-first probes use actual writes/deletes, including omitted default-flat configuration; they now refuse safely for both targets and validation changes. The 242-case selection also exercises all persisted cutoff prefixes, same/separate roots, multiple unfinished moves, other users/engine, malformed metadata, aliases and under-lock expansion. Fresh/repeated caller runtime files remain legal. Verified cleanup can retire and return; eventual consistent proof clearing works. All-target planning prevents one target's failure from partially mutating another. Common apply machinery is unchanged.

**Compatibility and evidence limits.** Normal Go plans remain equal outside the attributed provenance changes; runtime owner/import identities and public bindings are preserved. Actual current wheel resources match source and compile/run isolated applications. The old all16/broad package supports its original tuple only. The final one-line alias hardening is covered by final affected checks, wheel/examples and independent coupled controls without inventing a new full-suite result.

## 3. Risks and next action

Original documented limits remain: virtual selection is intentionally incomplete, no native Swift JSON route is invented, cyclic object graphs have no finite CBOR serialization promise, arbitrary changed child layouts require native rebuilds, and three historical broad baseline failures remain disclosed. Inconsistent interrupted outputs may require inspection/migration or a fresh root; the correction guarantees safe refusal rather than automatic orphan repair.

The next action is the lane owner's merge of the SAME two original reviewers' verdicts on this exact corrected tuple. This Code GO authorizes no additional production work, global gate, push, release, tag or registry publication by the reviewer.
