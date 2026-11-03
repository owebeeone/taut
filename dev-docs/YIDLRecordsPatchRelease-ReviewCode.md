# YIDL/Taut Python Records Patch Release — CODE + SURFACE-AXIS REVIEW

**Review object:** YIDL dataclass `48ba94efd26ff300345f3bdca38987b90a13f79b` and Taut `f81a206d64b58d705d9cc853e5bea69550fb9e98`. Controlling documents: YIDL `dev-docs/ConfigurableFreezeRelease.md` and `CurrentProgramCheckpoint.md`; Taut `dev-docs/YIDLRecordsPatchRelease-DRAFT.md`. Status: source review before remaining release gates.

**Baseline:** Published YIDL `a71917a2a146433e7ceb9309865e99759fcf1d3b`, Taut `0258b49e92c8b4ccd95027b4b10ad0b2f3992c52`; prototype baselines YIDL `6c39c45ec31aca46665c29eaf69d2033cb4fe594`, Taut `fcfbe0cfface9241c2b68542973936a166a0c8bc`. Source read through immutable `git show` and named-range diffs.

**Date:** 2026-11-03

**Axis:** Code + Surface. Independent, adversarial, read-only. The other axis runs in parallel; nothing here relies on its report. Filed verbatim by the lane owner.

**Verdict: NO-GO** — one P2 finding blocks acceptance of the paired source. No P0/P1 findings. I pre-commit to GO on a bounded revision resolving P2-1 as specified, subject to inspection of that revision. No blocking defect was identified in the YIDL naming change itself.

---

## 0. Evidence base

Read both repositories’ `AGENTS.md`, `RELEASE.md`, controlling documents, release configurations, and relevant publication workflow changes.

Inspected the complete published/prototype range inventories and new implementation diffs. The YIDL published-to-prototype range contains the earlier documentation/site work; its new runtime delta carries `freeze_method` through normalization, inheritance, typed-child inference, authored YIDL resources and generated base. Golden changes are common decorator snapshots and formatted counterparts, rather than changed model expectations. Taut’s published-to-prototype difference is the previously added Python 3.15 CI entry.

Principal source inspection:

- YIDL decorator/options, harvester, policy/inheritance plans, freeze generation, authored `dataclass_core.yidl` and `dataclass_freeze.yidl`, generated base, copy resources, new naming tests and existing runtime-freeze tests.
- Taut `gen/python.py`, `gen/scaffold.py`, `records.py`, descriptors, validation, runtime-source closure, optional dependency declaration and new backend tests.
- Public README/API/freezing guides and CLI option/signature changes, read before the controlling DRAFT and implementation. Existing prototype environment `python -m taut.cli gen --help` corroborated the exposed option.
- `PROTOTYPE_RESULTS.json`, installed-final consumer results and consumer script; current YIDL candidate log observed as provisional.

The prototype receipts identify older prototype commits and local wheels, including a feature-bearing wheel still numbered `0.1.1`. They are not proof of public dependency availability or exact final-candidate qualification.

No tests, builds, installs, writes, Git mutations or credential access were performed. Both named source objects resolved to their exact supplied SHAs at the start and end.

## Problem, requirement provenance, and scope

The human authorized configurable YIDL freezing names, a Taut-owned decorator, a Python-only optional record backend, and dependency-first point releases. The concrete conflict is YIDL’s default `freeze` operation versus a legal Taut field named `freeze`.

The selected remedy addresses that conflict locally: YIDL makes the operation configurable; Taut chooses `_taut_freeze` within its reserved namespace. Existing dependency wheels and installed prototype consumers demonstrate feasibility without SDK implementation changes. Astichi 1.1.3 and YIDL 0.1.2 remain reference dependencies.

The two Python projects and their tests/docs/release setup are authorized. No shape, Rust foundation, unrelated workspace or SDK implementation change is necessary. Atomic freezing, automatic validation, alternate-language backends and performance claims remain deferred. P2-1 concerns the new backend’s own generation boundary and requires no scope expansion.

## 1. Findings

### [P2-1] YIDL-specific field restrictions are discovered only when generated output is imported

**Location:** Taut `src/taut/gen/python.py:41–49`, `106–112`, `135–139`; corresponding YIDL restrictions in `src/yidl_dataclass/dataclass_harvester.py:51–64`.

**Violated invariant:** Successful generation must produce usable output, or reject unsupported selected-backend names before output writes.

**Reproduction by source trace:** Construct `schema(Record=Msg(cls=F(1, INT)))`, then generate Python using `python_records="yidl"`. Taut’s collision checks permit `cls`, emit that annotation unchanged and return successfully after a syntax-only `compile`. `emit` can consequently write the module. Importing it invokes `taut_dataclass`; YIDL’s harvester deterministically raises `DataclassDefinitionError` because `cls` is reserved. Fields beginning `_y_dc_`, such as `_y_dc_value`, follow the same failure path. These restrictions are absent from Taut’s selected-backend checks and public backend instructions.

This counterexample was established through immutable source inspection, not executed during this read-only review.

**Impact:** A valid schema can produce apparently successful generation followed by an unusable module. Users receive a dependency-level decoration error after files have been written.

**Required correction:** Account for the selected backend’s complete field-name restrictions before writes. Either project these names to safe Python attributes while retaining descriptor/wire names, or explicitly reject unsupported names with a schema-qualified backend diagnostic and document the limitation. Preserve existing stdlib acceptance.

**Closure test:** Cover `cls`, `self` and `_y_dc_value`, validation OFF/ON, through programmatic and CLI generation. Each must either import and retain its wire contract, or fail before creating/changing output. Confirm stdlib behavior remains unchanged and `freeze` still works with the YIDL backend.

**Classification:** Bounded backend-adaptation omission; no architectural redesign required.

## 2. Invariant analysis

The inspected YIDL path retains the default name, rejects invalid/reserved configured names, checks field/method collisions and enforces consistent inheritance names. Typed-child inference captures each child’s configured operation; explicit hooks retain precedence. The authored template receives the configured identifier directly, rather than renaming methods afterward.

The freeze traversal retains completed/in-progress guards and clears the latter in `finally`. Copy-state handling includes freeze flags; replacement constructs mutable records. These preserve the documented optimistic, nontransactional lifecycle.

Taut centralizes decoration and requires `records.yidl.v1`. SDK import remains deferred to backend use. Schema-derived hooks handle nullable values, nested containers and message children; containers detach while child identity is retained. Ordinary FrozenDict mutation entry points are blocked, with explicit copy/deepcopy/pickle support. Validation widens container representations only for frozen YIDL records.

Explicit backend options without Python are rejected before writes. The stdlib API-generation branch remains equivalent, and other-language generators receive no backend option. Source runtime closure includes the new adapter.

## Surface

The CLI exposes `--python-records {stdlib,yidl}` and its default. Taut’s README supplies installation, generation, mutation, `_taut_freeze()`, optional validation, platform limits, external-child requirements and partial-failure semantics. The underscore-prefixed operation is discoverable.

YIDL’s API reference exposes `freeze_method="freeze"` and a custom-name example. Both products avoid promises of rollback, synchronization or automatic validation. The material surface gap is P2-1: backend-specific rejected field names are neither preflighted nor explained.

## 3. Risks and next action

Correct P2-1 and return the committed bounded revision for same-originator closure.

Thereafter, mandatory gates remain: exact YIDL matrix/package qualification and public dependency publication, Taut’s strict native/WSL and parity/package checks against that public dependency, exact version/tag inspection, terminal hosted publication, public artifact provenance and fresh installed consumers. This report does not declare those gates or workspace completion achieved.
