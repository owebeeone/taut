# Combined JavaScript/TypeScript OneOf checkpoint, remediation 1 — CODE+SURFACE-AXIS REVIEW

**Review object:** The single merged remediation patch, controlled by committed `EcmaOneOfCheckpoint-Draft.md` and `EcmaOneOfCheckpoint-RemPlan-1.md`. Status: corrected local checkpoint, awaiting originating-reviewer verdicts.

**Baseline:**

| Repository | Corrected reviewed HEAD |
| --- | --- |
| Taut | `57c56d5f7d727eb483ac9fd89c482f6a44f7913e` |
| Actual shape-ts | `1aaeab65e4564a462044d2f5d824cd2f375aae97` |
| GWZ workspace | `f4a2e908933b634edffaf17191359b472e34ff03` |
| Python shape, unchanged reference | `c08c2a1b5197f761c5b0b835c588da512130ceda` |
| Rust shape, unchanged reference | `8e92b89ed3a4f218a5a4e018fbfee6301fcc14b4` |

Correction ranges:

- Taut `68c24a899345367f3026372d3c67737751215a0e..57c56d5f7d727eb483ac9fd89c482f6a44f7913e`.
- Shape-ts `1409634e9b1c8eea0696bf0fee560d5017f34d1f..1aaeab65e4564a462044d2f5d824cd2f375aae97`.
- Workspace `fe244bc4915acbce58198889feae633f778fe649..f4a2e908933b634edffaf17191359b472e34ff03`.

Sources were inspected through committed diffs and read-only file reads. Execution used exact-commit isolated exports under `D:/projects/limbo/ecma-oneof-scratch/review-r1/code`.

**Date:** 2 November 2026, Australia/Sydney.

**Axis:** Code architecture, interfaces, actual loaded ownership, compatibility, error paths and public Surface. Continued originating review; independent, adversarial, read-only. The other axis runs in parallel; nothing here relies on its current report. Filed verbatim by the lane owner.

**Verdict: GO** — originating **Code/P2-1, Code/P3-1 and Code/P3-2 are closed**. No new finding or architectural root cause was established. State’s originating reviewer determines closure of its findings.

---

## 0. Evidence base

### Controlling records and changed source

Verified the R1 prompt SHA256:

`8d4bf8b385f50995b1350d77168486545d1001d6b59aeedfd1f64e91eee86509`.

Read the merged RemPlan-1, corrected Authority and DRAFT amendments, Inventory-1, Gates-1, Tuple-1, current target documentation and receipts. The original complete Code report, full product proposal and applicable process/repository instructions remain part of this continued review.

Before reading corrected implementation or the remediation plan, refreshed actual top-level/gen help, TypeScript package-builder help and both public example READMEs plus JS INTEGRATION. The original cold comparison-family walkthrough remains recorded in the original Code report.

Inspected the complete correction range, including:

- `typescript/descriptors.ts`: selected-namespace checks, checked-owner return, canonical constraint snapshots and exact publication grammar.
- `typescript/validation.ts`: bounded field-read handling and independent traversal.
- `typescript_metadata.py`: defined-token and checked-return requirements.
- Package-builder help, shared CLI help and complete retained JVM help test.
- Closure tests and shared help regression.
- Actual-library canonical copies, provenance, build-time selected-owner check, six generated metadata modules and CJS/ESM checks.

### Tuple, snapshot and source associations

All five HEADs matched at the beginning and end.

Verified the immutable R1 snapshot SHA256:

`60ec204ce47c6e6c914376e18145b7dc4c8d4aec7d99fdd33cfb3cccb48bbefd`.

At both snapshot checks:

- All **104 Taut** and **28 shape-ts** committed blobs matched.
- Original-checkout disk bytes matched those same entries.
- All **35 excluded artifacts** and **five protected user sources** matched.
- Dependency maps remained unchanged.
- The lock retained SHA256  
  `e110b44300bc75e28489500b7d2165b27414e2c6283853d7e4220b5fc27e06db`.

The correction is exactly **40 Taut paths and 11 shape-ts paths**. Many Taut paths are filed review/evidence records rather than production changes.

Checked current evidence associations independently:

- Shared before/after inventories are identical; their **31 Taut and 28 shape-ts** source entries match current bytes.
- TS R1 manifest associations match all **18 Taut and 11 shape-ts** entries.
- All **10 canonical library resource copies** match base Taut and recorded provenance.

### Fresh execution

Used the prescribed activated environment, isolated PYTHONPATH, disabled plugin autoload, no bytecode writes and explicit read-only historical origin.

| Fresh check | Result |
| --- | --- |
| Permitted R1 pytest selection | **185 passed**, 90.45 seconds |
| Independent original split/partial-facade replay | Rejected before publication in both validation modes |
| Exact r0 guard, foreign codec × token presence × validation mode | All eight rejected by corrected publication |
| Independent genuine namespace-value wrappers | Strict compilation, publication and residual encoding passed |
| Actual-library `pnpm typecheck` | Passed |
| Actual-library build/pack/extraction through target fixture | Passed |
| Actual-library `pnpm test` | **315 passed**, zero failures/skips |
| Documented TS source/package example | Strict compilation/execution passed; identical results |
| TS validation disable regeneration | Interface restored; owned engine removed |
| JS source example and validation disable regeneration | Passed; methods/owned engine removed |

The fresh pytest command selected:

```text
src/tests/test_typescript_review_closure.py
src/tests/test_typescript_oneof.py
src/tests/test_js_ts_distribution.py
src/tests/test_java_oneof.py::test_jvm_help_describes_supported_targets_json_files_and_defaults
```

Its unique basetemp was `review-r1/code/pytest-code-r1`.

### Historical and current gates

Consumed current corrected-source evidence:

- Shared affected gate: **503 passed, one existing symlink-privilege skip**.
- TS affected gate: **169 passed**.
- Actual library: typecheck/build and **315 passing tests**.

These overlap fresh and historical checks and are not added together. Retained failed-first TS evidence remains disclosed.

The original r0 global gate remains unchanged:

- All **16 parity variants GREEN**.
- Broad **1807 passed, four failed, five skipped, 11 deselected**.
- Exit 1 retained.
- Three established baseline failures and the original new help failure remain attributed to r0.

Rechecked its evidence inventory: no hash mismatch. No broad suite or all-parity gate was repeated or relabeled as R1 evidence.

## Problem, requirement provenance, and scope

The authorized outcome remains the combined JS/TS implementation with mandatory immutable metadata, optional exact instance methods, retained native codecs, lightweight explicit distribution and one actual same-target foundation owner.

The original review demonstrated that the selected TS facade could expose incompatible codec classes while publication succeeded. The merged prior plan also records State’s known-bound read and mutable-constraint counterexamples. These are concrete existing-contract failures, rather than prerequisites inferred from a generated plan.

The coordinator explicitly authorized one bounded correction window and the corrected local checkpoint. The authorized components are the existing TS guard/read/publication seams, canonical library re-vendoring, package-builder help, shared CLI guidance and affected tests/evidence. That authority is recorded in the committed amendment.

The remedies are localized. They require no new compiler, discovery mechanism, runtime installation, dependency change, wire projection or output-ownership architecture. Genuine current source/package/library routes remain executable. Python/Rust and later backend production remain reference-only; protected authoring and excluded artifacts remain untouched.

The selected-namespace check and defined-token return proof address the original owner defect directly. The limited field-read catch does not impose a universal no-throw contract. Defensive constraint reconstruction restores the already required immutable publication boundary. No blocking necessity or scope gap was found.

## Prior-finding closure table

| Finding | Original counterexample and fresh observation | Correction, regression and focused evidence | Disposition |
| --- | --- | --- | --- |
| **Code/P2-1** — selected facade exports bypass actual-owner checking | Independently recreated the original whole-codec and partial-codec facades using separately evaluated canonical owners. Strict compilation remains possible; corrected generated import rejects both facades in both validation modes before publication. | Checker compares actual selected descriptor/report/CBOR and codec/schema/JSON/ext values. Generated code requires a defined valid token and exact checked-owner return. Independent replay and passing selected-facade source/library regressions establish closure. | **CLOSED by originating Code reviewer** |
| **Code/P3-1** — package-builder default absent from help | Actual module help now states fresh `OUTPUT`, descriptor/codec-only behavior and “validation is included by default.” | Help correction and actual-help assertion pass in the fresh selection. | **CLOSED by originating Code reviewer** |
| **Code/P3-2** — retained JVM help test fails after expanded shared help | The complete original test now executes successfully, including assertions after its former first failure. | Expanded target/method assertion retains substantive checks; CLI restores Java jar guidance and explicitly distinguishes JS/TS tgz. Fresh complete JVM test and shared help regression pass. Original failed global receipt remains intact. | **CLOSED by originating Code reviewer** |

### Required same-root guard retraces

The independent replay is retained as:

`review-r1/code/replay-original.py`

with final artifacts under:

`review-r1/code/original-owner-replay2`.

It compiles current canonical resources and the exact immutable r0 blobs from Taut `68c24a899345367f3026372d3c67737751215a0e`. It does not import implementer test helpers.

The eight stale-checker combinations cover:

- Clean or foreign-codec facade.
- Present or omitted `Foundation` export.
- Validation enabled or disabled.

An independent direct invocation confirms that every compatible-looking stale facade’s exact r0 checker accepts its labels and returns `undefined`. Corrected generated publication rejects all eight: missing-token cases fail explicitly, and remaining stale guards fail the checked-return requirement. `undefined === undefined` cannot establish support.

An initial independent fixture omitted the legacy top-level labels and rejected earlier inside the old checker. Only that reproduction fixture was corrected to reach the required void-return boundary; no implementation or committed test was edited.

Genuine namespace wrappers preserving actual exported values pass in both modes, including native float residual encoding. Thus closure does not depend on rejecting every wrapper or requiring equal build labels.

## 1. Findings

No new findings were established.

## 2. Invariant analysis

### Changed-range and materiality assessment

The actual correction restores existing invariants at existing boundaries:

- `requireFoundation` receives the selected namespace and returns the checked owner. Generated and actual-library callers require that result.
- The helper’s no-argument publication call remains supported.
- Known generated callers and the explicit library owner-binding script are updated consistently.
- Public message constructors, validation methods, Fields projections, wire codecs and distribution selection remain unchanged.
- The new read catch surrounds only `MessageBinding.read`, preserves shared `ConfigurationError`, and does not surround descriptor discovery, options, traversal or report construction.
- Constraint inputs are reconstructed into owned canonical records and checked against the existing normalized oneof grammar.
- Output planning, locking, ownership accounting, write/delete application and platform assumptions are unchanged.

The guard return is a capability proof for the original single-owner requirement. The old void checker never provided the required selected-export verification. Its explicit rejection restores that compatibility invariant rather than creating a new composition architecture.

I therefore classify this as **bounded remediation**, not a material redesign requiring replacement reviewers under Step 5.5. The original proofs for unchanged codecs, filesystem mutation boundaries and native projections remain applicable. No new architectural root cause was found.

### Ownership and compatibility

The original Code attack now fails at import/publication rather than a later codec call. The checker compares implementation values rather than namespace-object equality, so genuine CJS/ESM and namespace-value wrappers remain supported.

Fresh tests cover separately built source and actual-library artifacts, disabled children, genuine selected-owner compositions, old artifacts, changed facts and compatible unequal labels. The actual library’s six generated metadata modules use the corrected token/return boundary. Canonical resources remain byte-identical across repositories.

### Bound-field and constraint corrections

The fresh closure selection corroborates the merged R2/R3 corrections through source and actual-library owners:

- Unreadable discriminator, selected payload and ordinary slots produce located issues.
- Report mode retains independent issues.
- Local/recursive behavior and false fast results remain correct.
- Shared `ConfigurationError` is not swallowed.
- Instrumented fast validation does not construct issue/deferred/report records.
- Strict mutable constraint records become independent frozen canonical snapshots.
- Duplicate, missing, extra, coercible and unsupported constraint controls/parameters are rejected.
- Valid independent and virtual groups still publish and validate.

These are corroborating Code results. State’s originating reviewer owns its original-counterexample closure.

### Surface

The package-builder’s previously missing default is now explicit. Shared help preserves supported target names, exact validation spellings, JSON-file inputs, defaults, owner details and artifact formats. The complete retained JVM assertion sequence passes.

Fresh JS and TS walkthroughs preserve mutable invalid drafts, explicit validation, descriptor access and supported cleanup. TS source/package results match. Omitting validation restores disabled output and removes only the unused owned engine. No installation, publication or guessed new command was required.

No new Surface defect was established.

### Preserved boundaries

The fresh affected tests retain recursive service data projections, actual external Fields imports, native residual state, engine-free descriptors, immutable reports and structural codecs without implicit semantic validation.

The historical equivalent-root and raw-namespace corrections remain unchanged. R1 does not modify the common physical-identity helpers, runtime planners or mutation application. Protected user files, excluded artifacts, dependency declarations, lock and Python/Rust references remain exact.

## 3. Risks and next action

The documented virtual incompleteness, separate JS/TS native codecs, interrupted-output recovery limit and existing platform coverage gaps remain. The r0 global run remains a failed historical gate; current focused help closure does not rewrite it.

The next action is to merge this originating **GO** with the independent State verdict on the same corrected tuple. This report closes the Code findings only and authorizes no push, tag, release, publication or next backend.
