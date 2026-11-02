# Combined JavaScript/TypeScript OneOf checkpoint — CODE+SURFACE-AXIS REVIEW

**Review object:** Frozen combined JavaScript/TypeScript implementation, actual `taut-shape-ts` integration, shared compiler boundaries, and controlling `dev-docs/EcmaOneOfCheckpoint-Draft.md` at Taut `68c24a899345367f3026372d3c67737751215a0e`.

**Baseline:**

| Repository | Reviewed HEAD |
| --- | --- |
| Taut | `68c24a899345367f3026372d3c67737751215a0e` |
| taut-shape-ts | `1409634e9b1c8eea0696bf0fee560d5017f34d1f` |
| taut-shape-py, reference only | `c08c2a1b5197f761c5b0b835c588da512130ceda` |
| taut-shape-rs, reference only | `8e92b89ed3a4f218a5a4e018fbfee6301fcc14b4` |
| GWZ workspace | `fe244bc4915acbce58198889feae633f778fe649` |

Reviewed implementation ranges are Taut `8c113e36a927cda5c50848f25ab828185080272d..68c24a899345367f3026372d3c67737751215a0e` and shape-ts `74597e5e3a1d3845e93644866b97b68080f4bbbe..1409634e9b1c8eea0696bf0fee560d5017f34d1f`. Original checkout files were inspected read-only; executable checks used the exported Code scratch copies.

**Date:** 2 November 2026, Australia/Sydney.

**Axis:** Code architecture, interfaces, compatibility, actual loaded ownership, error paths, and public Surface. Independent, adversarial, read-only. The other axis runs in parallel; nothing here relies on it. Filed verbatim by the lane owner.

**Verdict: NO-GO** — one P2 compatibility finding blocks. Two P3 findings are also open. I pre-commit to GO on a revision resolving **P2-1** as specified, provided the revised evidence establishes its closure without introducing another blocker.

---

## 0. Evidence base

### Authority and source inspection

Read the controlling generated prompt and verified its SHA256:

`a1a93d5c76859dac032574a268d6ba64f712fd945905355b6d3c1d2e0be3503a`.

Read:

- The complete `OneOf-ExplicitValidation-BuildProposal.md`.
- Committed `EcmaOneOfCheckpoint-Authority.md`, `EcmaOneOfCheckpoint-Draft.md`, and `EcmaOneOfCheckpoint-Preparation.json`.
- Workspace `AGENTS.md` and `AGENTS_GWZ.md`, both changed repositories’ `AGENTS.md`, the review-loop skill and its canonical template.
- Both runnable example READMEs and RESULTS documents, plus JavaScript INTEGRATION.
- Accepted Python/Rust/JVM verdicts and the historical Rust equivalent-root and namespace findings and closure evidence.
- JS emitter, metadata, runtime ownership/package helpers, canonical descriptor/report/validation resources, and codec changes.
- TS emitter, metadata, runtime/package helpers, canonical foundation resources, shared scaffold/service wiring, CLI and package-data changes.
- Actual shape-ts foundation exports, compatibility facades, vendor/build scripts, framing adaptation, generated metadata, package declarations and foundation tests.

The skill and canonical-template hashes match Preparation. The named checkpoint/process documents are absent at the checked Taut dev-docs location, as disclosed.

### Frozen-object verification

Verified all five tuple members at the start and again at the end.

Independently hashed committed Git blobs against `frozen-r0/snapshot.json`:

- All **73 Taut files** match, including Preparation’s committed blob.
- All **28 shape-ts files** match.
- Final original-checkout disk hashes also match all 101 snapshot entries.
- All **35 excluded artifacts** and **five protected user files** match their preservation hashes at both checks.
- Shape-ts dependency maps are unchanged.
- `pnpm-lock.yaml` is byte-identical to baseline, SHA256  
  `e110b44300bc75e28489500b7d2165b27414e2c6283853d7e4220b5fc27e06db`.
- The workspace change contains only the two managed receipt paths.

No reviewed production source was edited.

### Fresh execution

All principal probe artifacts are beneath:

`D:/projects/limbo/ecma-oneof-scratch/review-r0/code`.

| Check | Result |
| --- | --- |
| Permitted four-file pytest selection | **189 passed, 1 skipped**, 59.95 seconds |
| Actual shape-ts `pnpm typecheck` | Passed |
| Actual shape-ts `pnpm build` and local pack/extraction through target fixture | Passed |
| Actual shape-ts `pnpm test` | **315 passed, zero failed/skipped** |
| JS documented source example | Passed |
| TS documented source/package runner | Strict compilation and execution passed; results identical |
| Independent JS package/supplied, validation on/off applications | Passed |
| CLI enabled → disabled regeneration, both targets | Optional methods/classes and owned engines removed as expected |
| Independent equivalent-root/shared-user retraces, both targets | Passed |
| Raw namespace/physical-helper retraces | Explicit refusal |
| Independent TS selected-foundation facade probes | Reproduced **P2-1** |

The standalone library suite used the coordinator-exported committed oracle corpus from `taut-shape89916c4d017123d7c16f094eb2fba6ece98facc0`. Its reference manifest SHA256 is:

`3d0df94c2ae067ff1e513a1f7ee24c903ee4016ba0969e73ee2c54c972fc0e23`.

### Completed settled global evidence

Consumed the completed `global-gate-r0/RESULTS.md`, `global-results.json`, command/environment receipts, parity output, broad log/XML, baseline proof, skip/deselection classifications, source/protected/tuple before-and-after inventories, and evidence inventory. Every listed evidence hash checked matched.

The sole current-source global run reports:

- **All 16 codec variants GREEN**, zero governance violations.
- **1807 passed, four failed, five skipped, 11 deselected**.
- Three failures are the established missing historical document and two Windows Go CRLF/gofmt cases.
- One new failure is the JVM CLI-help assertion described in **P3-2**.
- Eight deselections avoid repeating the already completed parity gate.
- Three explicitly named deselections preserve the pending user-owned Enum.case policy boundary.
- No deselection is unclassified.

The global source, protected-file and tuple before/after JSON files are byte-identical. All five HEADs remained exact. This gate is complete and **not green**.

The six baseline-relevant source hashes match the historical isolated-baseline proof. The historical document is absent from both the pair baseline and reviewed commit. Historical JVM global counts retain their original attribution; no overlapping totals are added here.

## Problem, requirement provenance, and scope

The requested outcome is the next authorized two-backend implementation checkpoint: mandatory immutable descriptors, exact optional instance validation, preserved native structural codecs, explicit source/package/supplied delivery, independent-schema composition and actual TS library foundation ownership.

The concrete baseline gaps are supported by source inspection: JS/TS lacked the required metadata and methods; TS’s native interfaces could not themselves supply opted-in instance methods; the actual TS library vendored its codec implementation without the required lightweight shared foundation export.

Authority records the original all-nine implementation instruction, Python/Rust checkpoint, two-at-a-time continuation, JS/TS assignments, explicit service-data and residual-state corrections, and combined freeze/review authorization. Those instructions supersede the proposal’s historical documentation-only/Python-stop clauses.

The changed components fit those assignments. The shared raw-namespace correction is localized to the existing ownership helper. Its necessity is supported by the demonstrated pre-Path-conversion spelling loss and executable retraces. No new compiler, JS library repository, application-time loader, registry publication or unrelated dependency upgrade is needed.

Existing supported routes remain feasible: the actual library builds with its unchanged declared dependencies, and independent source/package consumers execute. A separate package identity, automatic installation or infrastructure migration is unnecessary.

The implementation broadly addresses the requested problem. However, **P2-1** leaves the required actual-owner verification incomplete for a supported explicit TS module binding. No additional scope or authority gap was established.

## 1. Findings

### [P2-1] TypeScript checks lexical foundation imports instead of the selected facade’s actual exports

**Location:** Taut `src/taut/gen/runtime/typescript/descriptors.ts:16–23`, generated call at `src/taut/gen/typescript_metadata.py:112`, and the identical canonical copy at shape-ts `foundation-src/descriptors.ts`.

**Violated invariant:** A configured foundation facade must expose one actual codec/descriptor/report owner. Matching declarations, source text and contract labels cannot establish identity. Unsupported split artifacts must fail before usable validation.

`requireFoundation()` validates its own module’s lexical imports. Generated code invokes it without presenting the selected `_taut` namespace. Therefore, a selected facade can retain canonical descriptors, reports, `Foundation` and `requireFoundation`, while exporting incompatible codec classes from a second evaluation of the canonical sources.

**Reproduction:**

1. Build a canonical foundation and copy its compiled CJS tree to a second directory, creating independently evaluated owners.
2. Create an explicit supplied/package facade equivalent to:

   ```javascript
   const canonical = require("CANONICAL/foundation.js");
   const foreign = require("FOREIGN/foundation.js");

   module.exports = {
     ...canonical,
     CborFloat: foreign.CborFloat,
     DecodeError: foreign.DecodeError,
     EncodeError: foreign.EncodeError,
     encode: foreign.encode,
     decode: foreign.decode
   };
   ```

3. Supply declarations re-exporting the canonical foundation declarations.
4. Generate an enabled `Item(value: STR)` through normal `emit`, binding `module` to this facade and `validation_module` to the canonical engine.
5. Strictly compile and execute:

   ```typescript
   const value = new Item({
     value: "ok",
     __unknown__: new Map([[9, new foundation.CborFloat(1.5)]])
   });

   value.isValid();
   foundation.codec.encode(CODEC_SCHEMA, "Item", value);
   ```

Generation, strict compilation and publication succeed. `isValid()` returns `true`. Encoding then throws:

```text
type not in the frozen CBOR subset
```

The facade’s exported `CborFloat` is incompatible with its own advertised codec. A companion probe also establishes:

```text
codec split true
requireFoundation accepted split
foreign DecodeError true canonical DecodeError false
```

Retained reproduction artifacts include `probe-split.py`, `split-foundation.cjs`, `split-foundation-partial.cjs`, their declarations, `split-generated`, `split-partial-generated/main.ts`, and compiled outputs beneath the Code scratch root.

**Impact:** An explicitly bound runtime can pass the new compatibility guard while exposing incompatible nominal codec classes. Applications encounter codec failures or failed error-class checks after successful schema publication. Native residual values make the incompatibility observable without changing schema facts.

**Required correction:** Verify the actual selected module exports and codec namespaces against the descriptor owner’s actual implementation. A check of metadata labels or the checker’s lexical dependencies is insufficient. Preserve legitimate identity-preserving facades, compatible unequal build labels, engine-free metadata and the no-target-execution-in-compiler boundary.

**Closure test:** Retain the separately evaluated artifact and partial-facade counterexample. Strict compilation must remain possible, but module import/publication must reject the split clearly before validation becomes usable. Cover validation enabled and disabled, nominal errors/CborFloat, and codec/schema/JSON facade substitutions. Genuine CJS/ESM and selected-source-owner re-exports must still pass.

### [P3-1] The public TypeScript package-builder help omits its validation-payload default

**Location:** Taut `src/taut/gen/typescript_package.py:76–80`.

**Violated invariant:** Public options must state their defaults.

**Reproduction:**

```text
python -m taut.gen.typescript_package --help
```

The documented package-building entry displays:

```text
--without-validation
```

with no explanation or default. The implementation includes validation by default, but the help does not state that.

**Impact:** A first-time package consumer cannot determine the default engine inventory from help alone.

**Required correction:** Describe the option and state that validation is included by default. Describe the required fresh output directory in the positional argument help.

**Closure test:** Assert those facts in the actual module’s `--help` output. No API change is needed.

### [P3-2] Expanded shared CLI help was not reconciled with the retained JVM contract test

**Location:** Taut `src/taut/cli.py:180–183` and `src/tests/test_java_oneof.py:562–569`.

**Violated invariant:** Changes to the shared public interface must retain truthful accepted-target guidance and keep its regression checks executable.

**Reproduction:** The completed settled global gate fails:

`src/tests/test_java_oneof.py::test_jvm_help_describes_supported_targets_json_files_and_defaults`.

Line 564 requires the literal:

```text
Java/Kotlin methods: validate/isValid
```

Current help says:

```text
JS/TS/JVM methods: validate/isValid
```

The assertion stops the remaining checks. Inspection also shows a later `optional artifact jar` expectation against newly generalized artifact wording.

**Impact:** The required current-source integration gate has a new failure beyond the three established baselines. Subsequent assertions in this help-contract test are not reached.

**Required correction:** Reconcile the expanded help and test while preserving checks for supported targets, exact method names, JSON-file inputs, defaults and target-specific artifact guidance. Do not suppress the test or classify this new failure as baseline.

**Closure test:** Run the complete named test after correction and preserve the original failed global receipt. The full assertion sequence must pass.

## 2. Invariant analysis

### Code Surface cold walkthrough

Top-level and `gen --help`, comparison-family help (`corpus`, `json`, `parity`), both runnable READMEs and JS INTEGRATION were read before Authority, DRAFT or implementation source.

The new choices belong under the existing `gen` family. Runtime selection, validation enablement, external-type mappings and owner bindings describe generation decisions. No unrelated top-level family was introduced.

Help states the primary defaults: supplied-runtime omission, validation off, mandatory descriptors, service selection and binding contracts. Documentation explains recursive validation, local scope and intentional virtual incompleteness.

The documented JS source application and TS source/package example ran successfully. Independent JS package/supplied applications also passed with validation on and off. Local artifacts were built/extracted; nothing was installed or published.

Disabling validation by omitting the flag is documented and executable: JS methods disappear, TS returns to interfaces, metadata remains and positively owned unused engines are removed. Shared-user retraces preserve another enabled user’s engine.

My initial guessed `python -m taut` invocation failed; the documented `python -m taut.cli` route worked. This was a reviewer invocation error, not a defect in the documented route. Package setup requires the integration documentation to select/build a local owner; the public package-helper default omission is recorded as P3-1.

### Descriptors, methods and semantics

The fresh target selection supports:

- Mandatory metadata in both modes and exact optional methods.
- Shared immutable descriptor/report classes and engine-free metadata imports.
- Static generated readers and terminating recursive publication.
- Non-null presence, independent groups, payload-free choices and wrong-tag dependent-check suppression.
- Traversal of ordinary and nonselected populated children.
- Local/recursive scope, active-ancestor cycles and per-path shared-child diagnostics.
- Deterministic field/index/canonical-CBOR-key paths, including exact i64 keys.
- Owned snapshots, open diagnostic strings and fast/report equivalence.
- Mutable invalid drafts, retained populated payloads and no implicit semantic validation.

The fast implementations share event predicates and do not construct issue/deferred/report objects.

A supplementary probe found that throwing application property accessors can escape TS readers. I have not promoted arbitrary user-defined accessor exception containment into an additional prerequisite; the ordinary malformed scalar/collection-data cases are covered by the passing located-diagnostic tests.

### Native projections and actual library

JS preserves CommonJS and native object constructors. TS preserves disabled interfaces and enabled per-type classes with recursive Fields projections. Service tests establish recursively plain decoded data rather than promised instance methods, including actual external Fields exports and strict negative method-use checks.

The enabled TS constructor retains native `__unknown__` state by reference. Its descriptor exclusion and exact storage-name reservation are covered by the passing tests.

The actual TS library builds and runs. Canonical source hashes, local packaging, generated metadata and genuine CJS/ESM identities are exercised. Positive composition tests pass; **P2-1** demonstrates that their negative selected-facade coverage is incomplete.

### Historical-root retraces and preserved boundaries

Independently repeated, for both targets:

1. Enabled producer A and disabled user B sharing one owner.
2. B regeneration through `owner/../owner`.
3. Verification of exactly two users and retained engine.
4. Last enabled-user disable, removing only the engine.
5. Re-enable followed by immediate JS and strict-tsc/Node application execution.

All passed.

The common raw namespace and physical helpers explicitly refuse trailing-dot, trailing-space, `CON`, `x:y` and `x:stream` spellings. The target selection also exercises actual junction refusal.

Python/Rust/JVM reference boundaries remain intact in source and completed global behavior evidence. User authoring files, old excluded artifacts and frozen dependencies remain unchanged.

## 3. Risks and next action

Virtual selection remains intentionally incomplete. JS and TS retain distinct native codec projections. The documented interrupted-output recovery limitation, Windows symlink privilege gap, unavailable wasm target and three established baseline failures remain disclosed.

The single next action is the coordinator’s bounded merged correction: resolve **P2-1**, address the two P3 items, preserve the failed r0 global evidence, and return the revised settled tuple for required closure. Production remains on HOLD; this report authorizes no publication or next backend.
