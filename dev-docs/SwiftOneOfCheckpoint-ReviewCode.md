# SwiftOneOfCheckpoint — CODE+Surface-AXIS REVIEW

**Review object:** Taut `83291c2c7c7b126e41625bd29623870330f3b0d6..c02765930f06cfcb19a522843aa54582db514706`, the exact 45-file checkpoint, controlling `dev-docs/SwiftOneOfCheckpoint-Draft.md` at the latter revision, and workspace managed receipt `45f1e4387f3bcd6b21b6291dc0fab0a262303ba9..a8f37984471654902149d136b7a13a588346b58f`. Committed and frozen; acceptance pending.

**Baseline:**

| Repository | Reviewed HEAD |
| --- | --- |
| Taut | `c02765930f06cfcb19a522843aa54582db514706` |
| Workspace | `a8f37984471654902149d136b7a13a588346b58f` |
| taut-shape-py | `c08c2a1b5197f761c5b0b835c588da512130ceda` |
| taut-shape-rs | `8e92b89ed3a4f218a5a4e018fbfee6301fcc14b4` |
| taut-shape-ts | `1aaeab65e4564a462044d2f5d824cd2f375aae97` |

Sources were read from the isolated full-history clone at `D:/projects/limbo/swift-oneof-scratch/review-r0/code-raw/taut-dev`. Historical emitter/planner controls were read with `git show 83291c2c7c7b126e41625bd29623870330f3b0d6:<path>` and evaluated in memory; no reviewed source was edited.

**Date:** 3 November 2026, Australia/Sydney.

**Axis:** CODE + Surface — architecture, native interfaces, call graphs, compatibility, public generation workflow and the authorized shared ownership-kernel extraction. Independent, adversarial, read-only. The other axis runs in parallel; nothing here relies on it. Filed verbatim by the lane owner.

**Verdict: NO-GO** — one P2 finding blocks acceptance; no P0, P1 or P3 findings. I pre-commit to GO on a revision that resolves P2-1 as specified, passes its originating counterexamples and appropriate focused regressions, and introduces no new blocking defect.

---

## 0. Evidence base

### Cold public-interface pass and authority

Before product code or design inspection, read the complete `docs/SWIFT_API.md` and `dev-docs/examples/swift-oneof/README.md`, and executed the existing compiler's root, `gen`, `corpus`, `json` and `parity` help through `python -m taut.cli`. Compared Swift's new options with the existing target mappings, runtime selection, validation flags and command families. No new installation command family is exposed. An exploratory `python -m taut` invocation has no package entry point; the supported compiler entry used for all generation was `taut.cli` with the isolated source path.

Read the canonical reviewer prompt, review-loop skill, workspace AGENTS/AGENTS_GWZ, Taut AGENTS, the full build proposal sections 1–9, Swift Authority/Draft/Preparation, UserEnumCaseIntegration receipt, native examples/goldens and associated results. Read the historical C++/Go original findings, corrected reviews/verdict, Acceptance-1, FocusedResults-1, Preparation-R1 and both RESULTS-R1 records as evidence of their stated revisions, not current-source global results.

Principal source inspection covered:

| Source | Scope |
| --- | --- |
| `src/taut/gen/swift.py` | Native projection, identifiers, recursion, constructors and codecs |
| `src/taut/gen/swift_metadata.py:1–262` | Preflight, external mappings, publication, fingerprints and typed adapters |
| `src/taut/gen/swift_runtime.py:1–145` | Bindings, canonical closure, explicit builder, artifact verification and ownership wrappers |
| `src/taut/gen/runtime/swift/descriptors.swift:1–332` | Immutable facts, lazy links, registry checks, typed bindings and owner evidence |
| `runtime/swift/paths.swift:1–24`, `reports.swift:1–30`, `validation.swift:1–65` | Owned paths/reports, predicate stream and traversal identity |
| `src/taut/gen/owned_runtime.py:1–128` | Complete extracted planner and manifest checks |
| `src/taut/gen/go_runtime.py` | Old/new extraction comparison and retained path/user checks |
| `src/taut/gen/scaffold.py:635–980` | Target resolution, forwarding, full planning, previous-root checks, locks and application |
| CLI, Swift parity driver, pyproject and changed tests | Complete relevant diff, resource delivery and existing-regression integration |

The unchanged Python engine was consulted for field/group/child ordering, presence, paths and deferred semantics. The existing ownership application and namespace helpers were inspected for raw `os.fspath` checks, aliases, physical target collisions and fail-closed mutation.

### Integrity and execution environment

At start and end, all five HEADs matched the table, tracked/index diffs were empty, and all **1,114** tracked files across the five clones matched their setup SHA256 values. All 44 non-self Preparation entries and the 29-file frozen source inventory matched. The latter retains source inventory identifier `51c92bf28ff9d9936bb89f1c6a9225fcf2ce6858f816eebef406c6e74b5ee156`. The five protected user-source files and original Swift CBOR/extension resources have no diff from the integrated parent.

Dot-sourced only the assigned scratch activation. Independently confirmed CPython **3.13.5**, Swift **6.4.2**, target `x86_64-unknown-windows-msvc`, and imported `taut.__file__` under this isolated clone. TEMP/TMP, native outputs, caches and all counterexamples stayed under `code-raw/scratch`; no saved-workspace build was run by this reviewer. No source mutation, install, fetch, commit, push or release operation was performed.

Independent focused executions used `python -m pytest -p no:cacheprovider`, scratch basetemps and XML receipts:

| Selection | Result |
| --- | --- |
| `test_swift_oneof.py test_swift.py -m 'not gate'` | **146 passed, one deselected**, 376.96 seconds |
| Swift/pair distribution, scaffold and Go files with `-k 'wheel or pair_plans or previous_owner_alias or default_source_owner_retires or external_retirement or selected_source_import_remap'` | **68 passed, 101 deselected**, 77.96 seconds |
| Complete `test_scaffold.py` plus exact JVM help test | **13 passed**, 1.27 seconds |
| Exact existing ECMA/JVM shared-help test | **1 passed**, 0.60 seconds |

The single Swift deselection is the duplicate parity wrapper. The 101 nonselected cases reflect the explicit focused `-k` selection. These runs overlap the complete gate and are not additive totals. XML receipts are `scratch/native-tests.xml`, `shared-tests.xml`, `help-tests.xml` and `ecma-help.xml`.

Independent scratch probes additionally retained:

- `probes/walkthrough/results.json`: exact CLI commands and manual native build/link commands; source first use, enabled→disabled, source→package native use, package→source, and preservation of a handwritten file all passed.
- `probes/kernel/results.json`: ten exact old/new Go write-byte/deletion-set comparisons on identical physical roots, validation off/on, source reuse, retirement and return. All maps matched. Missing prior owner states refused unchanged.
- `probes/receipt-first/results.json`: after persisting the new schema receipt/API and removing the runtime-owner receipt before stale source deletion, all four package/imported-supplied × off/on states refused unchanged for Go, and all four corresponding Swift states did likewise. Errors identified unknown runtime files; no orphan source was adopted.
- `probes/names/results.json`, `probes/names/more-results.json`, `probes/names-matrix/results.json`: original P2-1 sources, raw compiler errors and baseline/placement/mode controls. The matrix receipt includes exact compiler argument arrays.

### Completed exact-tuple global receipt

Waited for the lane owner's explicit completion message before forming this final verdict. Consumed the completed package at `D:/projects/limbo/swift-oneof-scratch/global-gate-r0`, including RESULTS, global-results, execution-receipt, full broad log, baseline-source proof, skip/deselection classifications and all three failure tracebacks. Inspected raw parity and before/after integrity receipts. Independently verified all **37** inventoried evidence files against size/SHA256; no mismatch.

- Evidence-inventory SHA256: `93b84b7cca6fa4bf502e45a819b1babc837716335ba225ba35da33ec2650beca`.
- Global-results SHA256: `bad810019879df69ac807a2c8037453c8f116b9aba4da1863c1a3d444c2b75a9`.
- All **16 require-all codec variants GREEN**, zero governance violations, no unavailable variant.
- Broad: **2,260 passed, three failed, five skipped, eight deselected; 2,268 selected**, pytest exit 1. Raw pytest duration 1167.93 seconds; complete gate elapsed 1213.7 seconds.
- The three failures remain the disclosed historical missing proto-surface document and two Windows Go CRLF/gofmt assertions. Their tracebacks and unchanged-test/source proof agree; the current LF regression passed. **No new integration failure** was reported.
- The five skips are the Windows symlink-privilege case, three POSIX tool/PATH tests, and unavailable Rust wasm32 target. Junction coverage ran separately.
- Exactly eight duplicate parity-marker wrappers were deselected. User enum.case/metadata tests stayed enabled; no obsolete three-name reservation exclusion remains.
- Swift 116 feature, 30 existing and one distribution cases passed; all 145 Go feature cases and all 11 pair distribution cases passed.
- Tuple/source/raw-blob/protected before/after receipt bytes matched. The gate records 718 selected source files, 736 raw-blob comparisons, all 45 Swift files, five protected sources, 35 excluded artifacts, five indices and 47 locks/manifests unchanged.

The accepted TypeScript library's existing 315-test/typecheck/build evidence was source-associated using its corrected inventory. No fresh standalone library run is claimed. The 35 excluded saved-workspace Python artifacts were absent from this isolated clone; their preservation is supported by the complete coordinator receipts, not by a claim that this reviewer built them.

## Problem, requirement provenance, and scope

The operator requested all nine native backends, with Swift last: mandatory immutable descriptors, optional exact instance validation, shared general reports, typed local/recursive traversal, preserved mutable drafts/codecs and explicit runtime delivery through one actual owner. Swift lacked that foundation. The existing direct-recursive struct projection also failed native compilation.

The full build proposal supplies the behavioral requirements. Its earlier documentation-only restriction is superseded by the later implementation directions preserved in Authority and this review dispatch. Root explicitly authorized the bounded direct-recursive final-class choice, final necessary scaffold/CLI/driver/wheel integration, and behavior-preserving extraction of the accepted Go planner. These are not inferred mandates from a generated plan.

The changed production components fit that boundary. The pyproject change adds the nested Swift resource glob; it does not change dependencies. User authoring/model/IR, other target codecs/validators and the three shape repositories remain reference-only. The integrated enum.case commit is the protected baseline. Release, registry, tag and publication operations are outside this reviewer's authority.

No unsupported infrastructure prerequisite was identified. Existing Swift compilation demonstrably supports source and application-supplied module consumers; the existing compiler builds a real current wheel with the canonical closure. A direct native probe confirms why optional direct self/mutual struct storage needs a reference boundary. Ordinary and collection-indirect recursion need no class conversion. No fabricated Swift repository, automatic install, child regeneration, second compiler or application compiler/loader dependency is necessary.

Localized corrections suffice for P2-1: make helper name resolution safe, or reject genuinely unavoidable collisions before writes with placement-aware diagnostics. The observation does not justify broader schema-authoring, runtime ownership or dependency redesign. No blocking provenance/necessity gap was found. Virtual selection, absence of a native Swift JSON route and the three historical baseline failures retain their explicit limited deferrals.

## 1. Findings

### [P2-1] Unqualified helper types bypass name preflight and produce uncompilable accepted schemas

**Location:** `src/taut/gen/swift_metadata.py:51–61,163`; `src/taut/gen/runtime/swift/paths.swift:22`; `src/taut/gen/runtime/swift/descriptors.swift:49,191,237,284,288–318`.

**Violated invariant:** Supported schema names must either generate compilable native code or receive an explicit actual-collision error before output. Mandatory metadata must not silently break previously valid native names, including in the legacy flat supplied placement. Imported-owner configurations must retain harmless names that do not share a declaration scope with the runtime.

The new implementation uses ambient `Data`, `NSLock`, `ObjectIdentifier`, `AnyObject` and `Void` names without fully accounting for schema declarations that shadow them. Flat supplied mode compiles the canonical runtime and generated schema into the same module. Its reservation list names the new runtime declarations but omits these helper types. Independently, every generated holder declares `guardOwner: Void`, so a schema named `Void` shadows that result type in both flat and imported placements.

**Exact source counterexample:** For each name independently, generate:

```python
s = schema(**{name: Msg(value=F(1, INT))})
emit(s, output, langs=['swift'], services=[], validation=enabled)
```

Use each of `Data`, `NSLock`, `ObjectIdentifier`, `AnyObject`, `Void`; test `enabled=False` and `True`. Copy `canonical_sources(validation=enabled)` byte-for-byte into a scratch supplied directory, and compile those files plus the unmodified generated API and a `main.swift` that constructs the record. Every generation accepts and writes output. Every flat native compilation exits **1**.

For example, the executed OFF `Data` command was:

```text
swiftc D:/projects/limbo/swift-oneof-scratch/review-r0/code-raw/scratch/probes/names-matrix/off/cbor.swift D:/projects/limbo/swift-oneof-scratch/review-r0/code-raw/scratch/probes/names-matrix/off/ext.swift D:/projects/limbo/swift-oneof-scratch/review-r0/code-raw/scratch/probes/names-matrix/off/paths.swift D:/projects/limbo/swift-oneof-scratch/review-r0/code-raw/scratch/probes/names-matrix/off/descriptors.swift D:/projects/limbo/swift-oneof-scratch/review-r0/code-raw/scratch/probes/names-matrix/Data/flat-off/swift/api.swift D:/projects/limbo/swift-oneof-scratch/review-r0/code-raw/scratch/probes/names-matrix/Data/flat-off/main.swift -o D:/projects/limbo/swift-oneof-scratch/review-r0/code-raw/scratch/probes/names-matrix/Data/flat-off/app.exe
```

The native diagnostics identify actual resolution failures:

- `Data(bytes).base64EncodedString()` resolves to the schema record: missing argument label `value:`, `[UInt8]` cannot convert to `Int64`, and schema `Data` has no `base64EncodedString`.
- `NSLock()` resolves to the schema record: missing argument for parameter `value`.
- `ObjectIdentifier` resolves to the schema record: `ReferenceIdentity` loses Hashable/Equatable conformance and native-metatype construction fails.
- `RecordTraversal: AnyObject` resolves to a non-protocol, non-class schema type; the reference-binding constraint fails too.
- `guardOwner: Void` expects the schema record, and its closure reports `missing return in closure expected to return 'Void'`.

**Controls and bounded extent:** All five schemas compile using the baseline `83291c2` Swift emitter with unchanged CBOR/extension sources. At the reviewed revision, all five fail flat compilation with validation both OFF and ON, so omitting optional validation is not a workaround. With an actual separately compiled `TautFoundation`, imported OFF controls for `Data`, `NSLock`, `ObjectIdentifier` and `AnyObject` compile successfully. `Void` still fails imported compilation OFF and ON because the unqualified type is emitted into the schema holder itself. Thus the problem includes the explicit imported-owner route and is not merely incorrect flat assembly or duplicate filenames. Exact command arrays, generated bytes and full stderr remain in the three naming receipts listed above.

**Impact:** The compiler reports successful generation and creates owned output that cannot build for previously usable schemas. Users encounter downstream Swift errors rather than the required prewrite diagnostic. `Void` is affected independently of runtime placement; the other demonstrated names fail the explicitly retained default flat supplied route. The complete suite misses this namespace seam, so its passing feature cases do not close the finding.

**Required correction:** Qualify generated helper references wherever feasible, including the holder's unit result type, and audit newly introduced runtime/helper references against same-module schema declarations. For any unavoidable actual collision, reject it explicitly before writes with correct placement/mode scope and migration guidance. Do not blanket-reserve harmless imported-runtime names. Preserve Unicode/emoji names, existing enum cases and allowed validation-disabled method-like fields.

**Closure/regression test:** Replay the exact five schemas in OFF/ON flat and imported owner configurations. Each must either compile/run through the supported route or fail deliberately before output with the specific unavoidable collision identified; prefer preserving the previously valid names through qualification. In particular, `Void` must no longer generate an invalid holder in any source/package/imported/default placement. Assert unchanged output on any deliberate preflight refusal, preserve the successful imported controls, and retain the existing keyword, enum-case, emoji, qualified-helper and disabled-name tests. Re-run appropriate Swift generator/native/wheel and shared-help checks after the bounded fix.

## 2. Invariant analysis

**Surface and first-day lifecycle.** The new mapping belongs under the existing `gen` family alongside other target mappings. Help states validation defaults off, runtime omission means supplied, source defaults to `TautFoundation`, package requires an explicit module, and mappings default absent. The documentation gives the actual module/link commands and distinguishes an explicit development builder from schema generation. There is no new install lifecycle or automatic package operation requiring an uninstall counterpart. Generation's relevant reverse operations are disabling validation and changing ownership mode; the independent walkthrough exercised both and a return transition, preserving handwritten content. Native building requires the linked example's commands beyond `gen --help`; they are present and worked. P2-1 is the concrete Surface/code failure where accepted names reach an unusable native interface.

**Native values, recursion and snapshots.** Ordinary and collection-indirect recursion remain structs. Only direct-size recursive components become final classes; optional direct edges and mutual recursion are included, and required initializer arguments remain required. Actual reference identity combines the object, native type, qualified schema binding and fingerprint. Value bindings invent no temporary or array-backing pointer identity. Native tests exercised copied/nested values, shared children, finite prefixes, self/mutual recursion, genuine cycles, continued sibling traversal and report snapshots after mutation.

**Descriptors and semantic traversal.** Static value metadata owns arrays/dictionaries/strings; lazy links cache typed edges without recursively allocating a message graph per instance. Native binding construction checks metatype/representation. Publication checks links, categories, registries and contracts. Exact thin public instance wrappers call the shared engine. The same predicate stream drives report and Boolean modes; fast mode avoids diagnostic/report construction. Presence retains zero/false/empty, invalid drafts survive constructors/mutation/CBOR, local excludes descendants, recursive traverses populated nonselected children, and field/index/canonical-key order matches the Python reference. Virtual checks remain deferred while supported descendants continue.

**Actual dependency and foundation compatibility.** Focused native tests compiled enabled parents against separately generated disabled children, including imported and same-module mappings. Full mapped enum graphs, enum-only child dependencies, real artifact replacements, effective codec bounds, forward compatibility, native class/struct form and declaration-order equivalence were exercised. Compatible unequal build labels and true alias facades work; split nominal owners, stale/forged selected exports, absent descriptors and incompatible child facts fail. No child optional method is required or regenerated. Native Swift enum limitations are acknowledged without fabricating invalid bit patterns.

**Delivery.** The current compiler wheel contains byte-identical nested Swift canonical resources and is extracted for isolated `-I -S` generation. Native source/package/default flat applications compile and execute without a compiler/loader/delivery engine in their application route. Validation-off metadata/codec consumers compile without report/engine sources. Filename-only copies used for same-module child/parent builds preserve generated bytes. Builder invocation remains explicit; generation tests reject target execution.

**Shared ownership extraction and recovery.** Old/new Go plans matched on the same roots; the extraction retains wrappers and the accepted algorithm. Native retirement/return, remaining users and engines, selected-source remap rejection, unknown/missing/modified owner refusal and 40 persisted retirement cutoffs passed. Independent forced receipt-first states reject leftovers unchanged for both Go and Swift. The nine-target previous-owner junction cases proved refusal before lock opens. Raw ambiguous namespace checks precede Path coercion; physical aliases, obstructions, locks and output conflicts remain preflighted. No evidence supports orphan adoption, silent repair or deletion of another user's engine. The authorized recovery contract permits an interrupted inconsistent state to refuse unchanged and require inspection/migration; it does not promise transactional success across all files.

**Integration scope.** The completed exact-tuple global gate has no new failures and all 16 codec variants are green. The three historical failures remain visible, not deselected or relabeled as broad green. This supports surrounding compatibility but does not supersede the independent native P2-1 counterexample.

## 3. Risks and next action

The remaining documented limits are deliberate virtual incompleteness, no invented native Swift JSON route, no finite CBOR serialization promise for cyclic object graphs, normal Swift child-layout rebuild requirements and the disclosed historical baseline failures. No additional concern reached the finding bar.

The single next action is one root-authorized merged remediation plan and bounded patch, followed by originating-axis replay of P2-1 and relevant focused checks on a newly settled tuple. No source correction or finding self-closure was performed by this reviewer. This NO-GO does not authorize publication or another global gate.
