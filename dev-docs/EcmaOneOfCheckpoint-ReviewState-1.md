# Combined JavaScript/TypeScript OneOf checkpoint, remediation 1 — STATE-AXIS REVIEW

**Review object:** One merged remediation patch, controlled by `dev-docs/EcmaOneOfCheckpoint-Draft.md` and `EcmaOneOfCheckpoint-RemPlan-1.md`, at the corrected tuple below. Status: frozen corrected checkpoint awaiting originating-reviewer verdicts.

**Baseline:**

| Repository | Corrected reviewed HEAD |
| --- | --- |
| Taut | `57c56d5f7d727eb483ac9fd89c482f6a44f7913e` |
| taut-shape-py | `c08c2a1b5197f761c5b0b835c588da512130ceda` |
| taut-shape-rs | `8e92b89ed3a4f218a5a4e018fbfee6301fcc14b4` |
| taut-shape-ts | `1aaeab65e4564a462044d2f5d824cd2f375aae97` |
| workspace | `f4a2e908933b634edffaf17191359b472e34ff03` |

Correction ranges are Taut `68c24a899345367f3026372d3c67737751215a0e..57c56d5f7d727eb483ac9fd89c482f6a44f7913e` and shape-ts `1409634e9b1c8eea0696bf0fee560d5017f34d1f..1aaeab65e4564a462044d2f5d824cd2f375aae97`. Original feature context is retained. Sources were read through committed diffs, original files and verified exact-commit exports.

**Date:** 2 November 2026, Australia/Sydney.

**Axis:** State — originating counterexample closure, immutable publication, input/configuration failure boundaries, actual ownership, durable-output preservation and restart direction. Independent, adversarial, read-only. The other axis runs in parallel; nothing here relies on its current report. Filed verbatim by the lane owner.

**Verdict: GO** — originating State P2-1, P2-2 and P3-1 are closed. No new findings or architectural root cause were established.

---

## 0. Evidence base

### Authority, tuple and inventory

Read the generated R1 State prompt and verified SHA256:

`4368614dc1d93cda0b56b65d19ba377dea91d36330eb6c688ebca3b97f7c856d`

Read the committed Authority/DRAFT amendments, complete RemPlan-1, Inventory-1, Gates-1, Tuple-1, my original filed report, updated TS README/RESULTS-R1 and source associations. Retained the original review’s full proposal, repository/process instructions, both target documents and accepted reference-backend context.

Verified all five HEADs at review start and end. Every SHA matched the table above.

At both boundaries:

- All **104 Taut and 28 shape-ts** R1 snapshot entries matched committed blobs and original working bytes.
- Initial exported review copies also matched those entries.
- Exact correction sets matched **40 Taut and 11 shape-ts paths**.
- All five protected user-source hashes and 35 excluded artifact hashes remained unchanged.
- Dependency declarations remained unchanged.
- Lock SHA256 remained `e110b44300bc75e28489500b7d2165b27414e2c6283853d7e4220b5fc27e06db`.
- R1 snapshot SHA256 remained `60ec204ce47c6e6c914376e18145b7dc4c8d4aec7d99fdd33cfb3cccb48bbefd`.

The snapshot includes the committed Inventory-1 itself, avoiding a circular self-hash claim.

Verified the State export’s 190 corpus files against `review-r1/preparation.json`; all matched. The exports identify the exact reviewed commits and retain the explicit read-only historical Git fixture.

No original source, build output, dependency or configuration was modified. No helpers were spawned. No current R1 peer prompt or report was inspected.

### Changed implementation inspected

Inspected the complete production correction and associated tests, including:

- `runtime/typescript/descriptors.ts`: selected-namespace verification, defined owner return, defensive constraint reconstruction and exact control grammar.
- `runtime/typescript/validation.ts`: limited `readField` boundary and unreadable-payload handling.
- `typescript_metadata.py`: generated selected-owner/token/return checks.
- `typescript_package.py`: builder help.
- Actual-library canonical copies, provenance, generated guard calls and `scripts/build-foundation.mjs`.
- Shared CLI help, the complete retained JVM help test and new ECMA/JVM assertions.
- All 195 lines of `test_typescript_review_closure.py`.

Confirmed that `python_runtime.py`, `js_runtime.py`, `typescript_runtime.py`, `scaffold.py`, `rust_runtime.py`, `java_runtime.py` and `kotlin_runtime.py` are byte-identical to r0.

### Fresh independent execution

All new artifacts remained below:

`D:/projects/limbo/ecma-oneof-scratch/review-r1/state`

Used the prescribed activation, isolated PYTHONPATH, disabled plugin autoload/bytecode and explicit:

`TAUT_R0_REPOSITORY=D:/projects/limbo/taut-dev/taut`

| Check | Result |
| --- | --- |
| Complete permitted five-target focused command | **260 passed, 1 existing symlink-privilege skip** |
| Actual-library `pnpm typecheck` | Passed |
| Actual-library `pnpm build` | Passed |
| Actual-library `pnpm test` | **315 passed, zero failed/skipped** |
| Original State getter/duplicate/extra probe, adapted only to R1 paths | Passed corrected expectations |
| Original strict mutable-constraint program | Compiled; published rule remained immutable |
| Original mutable-constraint attack against built actual library | Published record and parameters remained frozen |
| Independent expanded source/library getter, configuration and control probes | Passed |
| Independent source/library fast-path constructor instrumentation | No diagnostic/report construction |
| Original crash-step probe on corrected generation | Preserved fail-closed outcomes |

The focused command ran:

```text
python -m pytest
  src/tests/test_typescript_review_closure.py
  src/tests/test_typescript_oneof.py
  src/tests/test_js_oneof.py
  src/tests/test_js_ts_distribution.py
  src/tests/test_java_oneof.py::test_jvm_help_describes_supported_targets_json_files_and_defaults
  -q --tb=short
  --basetemp D:/projects/limbo/ecma-oneof-scratch/review-r1/state/pytest-state-r1
```

Independent probes are retained as `original-state-probe.py`, `independent-probes/mutable-strict.ts`, `mutable-constraint.cjs`, `independent-r1.py`, `independent-fast.cjs` and `crash-probe.py`.

The original source probes were replayed separately from the implementer regression suite. The expanded independent program exercised both emitted source and the built actual-library owner.

### Receipt association and historical evidence

Verified all hashes in the TS R1 owned manifest against current files. Independently checked the shared receipt’s **59 source entries** against current bytes and confirmed its before/after inventories are equal.

Current implementer receipts remain separately attributed:

- Shared affected gate: **503 passed, 1 skip**.
- TS affected gate: **169 passed**.
- Actual library: typecheck/build passed and **315 tests passed**.

These counts overlap independent checks and are not summed.

Read the completed historical r0 `RESULTS.md` and verified all **27 files** in its evidence inventory. Its results remain:

- All **16 parity variants GREEN**.
- Broad **1,807 passed, 4 failed, 5 skipped, 11 deselected**, exit 1.
- Three established baseline failures and the original shared-help failure.

No broad/all16 run was repeated. R1 focused help success does not rewrite the failed r0 receipt or make it current-source global evidence.

## Problem, requirement provenance, and scope

The authorized outcome remains working JS/TS mandatory metadata, optional explicit validation, one actual foundation owner, honest structural service data and safe source/package/supplied delivery through the existing compiler route.

The original State defects were concrete: unreadable known generated fields escaped report/Boolean validation, and published constraints retained mutable caller records while accepting malformed normalized controls. The original global gate also exposed the stale JVM help assertion.

The committed Authority R1 amendment explicitly authorizes one merged correction addressing these roots, selected-namespace ownership and builder/shared help, followed by the same two originators. The merged plan records the accessor-boundary interpretation disagreement rather than claiming unanimous discovery or a universal no-throw requirement.

The implemented remedy stays within that bounded authority:

- It catches application access failures only at an already-known binding’s direct field read.
- It reconstructs canonical immutable constraint snapshots and validates their existing grammar.
- It strengthens the existing actual-owner admission check.
- It corrects help and preserves the substantive JVM regression checks.

The existing source/package and actual-library routes remain feasible. Fresh strict compilation, packed compositions and actual-library builds require no new compiler, installation, dependency upgrade, owner discovery, factory or infrastructure prerequisite.

No unauthorized component expansion or necessity gap was found. User Enum.case work, other backend production, dependency declarations, lockfiles, wire behavior and output mutation infrastructure remain unchanged. No release or publication follows from this verdict.

## Prior-finding closure table

| Original ID | Original counterexample and independent rerun | Correction, regression and gate evidence | Disposition |
| --- | --- | --- | --- |
| **State P2-1** | Replayed the original nested `Child.kind` throwing getter. It now returns `oneof.invalid_discriminator` at `child.kind`; `isValid()` returns false. Independently expanded through emitted source and actual library to unreadable discriminator, selected payload and ordinary slots. Exact located issues and the independent `child.extra` missing-payload issue survived. Local/recursive behavior remained correct. Shared `ConfigurationError` propagated by identity. | The catch surrounds only `binding.read`; shared configuration errors are rethrown. Failed payload reads are not duplicated in traversal. Fresh closure cases and independent source/library probes passed. Constructor instrumentation confirmed fast true/false paths allocate no diagnostic/report records. | **CLOSED by originating State reviewer** |
| **State P2-2** | Replayed the original strict mutable-record program without `any`, plus the original actual-library attack. Caller mutation no longer changes the published rule or parameter values. Both record and parameters are frozen canonical snapshots. Original duplicate-control and extra-parameter inputs now throw configuration errors. Independent source/library probes also rejected missing controls, arrays/objects coercible to a control, numeric/Boolean controls, unsupported rules and coercible group controls. | `MessageDescriptor` reconstructs constraints as canonical frozen records. Publication checks exact parameter shape, string controls and a one-to-one control set. Fresh malformed-grammar and valid independent/virtual regression cases passed through both owners. | **CLOSED by originating State reviewer** |
| **State P3-1** | The complete original JVM help test now passes, including assertions after the formerly failing grouping check. Expanded ECMA/JVM help assertions also pass. | Only the obsolete target-group expectation changed; method/default/JSON/owner checks remain. Shared help explicitly distinguishes Java jar and JS/TS tgz artifacts. Included in the fresh 260-case command and current 503-case receipt. | **CLOSED by originating State reviewer** |

Code-owned findings remain subject to the originating Code reviewer’s formal closure. The required State ownership attacks below independently corroborate the corrected guard behavior; they do not substitute for that verdict.

## Changed-range and materiality analysis

The production changes are confined to the existing TS ownership/publication and known-field-read boundaries, their canonical library copies/callers, and help text. Other changed paths are tests, documentation and auditable evidence.

The owner helper now receives the selected namespace and returns the verified Foundation token. This is a real linkage-check change. It enforces the already-required single-owner invariant: new generated callers reject a void-return historical checker that cannot establish selected-namespace support. Existing zero-argument checks remain usable, genuine aliases remain supported, and build-label equality is not introduced.

The additional descriptor imports inspect the foundation’s existing codec/report closure; they do not import the validation engine or a delivery engine. Guard calls in the six library-generated modules use the same corrected seam. Their native facts and wire projections are unchanged.

The read helper adds no object discovery or reflective access. It catches only direct access through the existing generated adapter, rethrows canonical configuration errors and leaves binding discovery, links, options, predicates and report construction outside the catch.

Constraint reconstruction restores owned immutable publication. Exact control-set checks enforce the existing normalized rule contract rather than introducing a new rule family or metadata architecture.

**Classification:** bounded restoration of existing invariants. No material architecture, public instance-method API, wire contract, output mutation boundary, platform baseline or compatibility-policy redesign requiring replacement reviewers was established. Focused fresh proofs cover the changed guard/read/publication call edges. Continuing the same originating reviewers is appropriate.

**New architectural root causes: none.**

## 1. Findings

None. All originating State findings are closed.

## 2. Invariant analysis

**Actual selected ownership:** Freshly executed substitutions used the exact committed r0 void-return checker, with and without foreign codec exports and with and without the Foundation token, in both validation modes. All eight combinations refused import. Missing tokens did not pass an `undefined === undefined` comparison.

Modern split/partial facades also refused across source and actual-library ownership. Genuine namespace-value wrappers and CJS/ESM aliases passed. Existing compatible-label and actual-library composition checks remained successful.

**Located reads and configuration distinction:** Ordinary accessor errors at known slots now produce the required paths and false fast results. Report collection continues independent checks. Canonical `ConfigurationError` escapes unchanged. This does not establish a universal no-throw promise for arbitrary objects or failures elsewhere in the engine.

**Immutable normalized state:** Caller-owned constraint records are copied into canonical frozen values. Post-publication mutation cannot invent a new rule or redirect a control. Duplicate, missing, unsupported and coercible declarations fail configuration checking. Valid independent and virtual groups retain valid/complete/fast semantics.

**Fast/report relationship:** The shared generator predicates remain in use. Independent instrumentation replaced issue, deferred-check and report constructors with throwing proxies after publication. Both valid and unreadable-input fast paths succeeded in returning their expected Booleans without constructing those records.

**Native and distribution preservation:** Fresh focused tests retained disabled-child composition, engine-free descriptors, native residual roundtrip, recursive plain Fields service results, Python-normalized reports, i64 paths, cycles, source/package/supplied delivery and actual packed library identity.

**Durable-output boundary:** Seven relevant shared/other-backend ownership helpers are byte-identical to r0. Fresh JS/TS transition, namespace, junction, obstruction and shared-user checks passed. The independent crash-step replay again produced either an untouched retryable state, explicit fail-closed refusal after interruption, or a completed retryable transition. No interrupted transition was accepted as complete.

The original Rust equivalent-root/raw-namespace and Python/JVM preservation evidence remains tied to its tested source. This patch does not change those helpers; it does not relabel that evidence as a newly repeated reference-backend matrix.

**Evidence integrity:** Corrected-source focused/library evidence is distinct from historical r0 global evidence. The original four failures remain visible. Protected user work, excluded artifacts, dependency declarations and lock bytes remain unchanged.

## 3. Risks and next action

Multi-file crash rollback remains unsupported; interrupted generation may require inspection, a fresh root or explicit migration. Cooperative locks do not promise protection from arbitrary external filesystem mutation. Virtual selection and recorded environment coverage limits remain unchanged.

The next action is to merge this State GO with the independent originating Code verdict on the exact corrected tuple and complete only the authorized checkpoint process. No additional global run, release, push, tag, publication or next backend is authorized by this report.
