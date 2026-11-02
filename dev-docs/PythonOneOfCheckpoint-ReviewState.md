# PythonOneOfCheckpoint — STATE-AXIS REVIEW

**Review object:** Python reference checkpoint, hash-identified working tree, 2 November 2026. Source inventory: `af9f2516f0dcbf45853fb6ade39d207c7a84b6b282975bffa8fdd385b59cc996`, 165 files, recorded in `taut/dev-docs/PythonOneOfCheckpoint-Snapshot.json`.

**Baseline:** taut HEAD `2cfee5d6156b0179066dc4eed70f60cde489a422`; taut-shape-py HEAD `da79bfb74376802edcd25049ed4ce29de814db44`. Reviewed current source bytes covered by the inventory, not an inferred committed patch. Both HEADs and the complete source inventory matched at review start and end. The operator prohibits commits.

**Date:** 2026-11-02

**Axis:** State — filesystem ownership, preflight, shared-runtime lifecycle, concurrency and restart behavior, immutable snapshots, traversal adversity, and fail-closed descriptor configuration. Independent, adversarial, read-only. The other axis runs in parallel; nothing here relies on it. Filed verbatim by the lane owner.

**Verdict: NO-GO** — three P2 findings block. I pre-commit to GO on a revision that resolves P2-1, P2-2 and P2-3 as specified, passes their regression cases and the focused existing gates, and introduces no material new defect.

---

## 0. Evidence base

Paths below are relative to `D:/projects/limbo/taut-dev` unless stated otherwise.

Read:

- Workspace `AGENTS.md`, `AGENTS_GWZ.md`, both component `AGENTS.md` files, and `C:/Users/gianni/.codex/skills/review-loop/SKILL.md`.
- The canonical State prompt, including its corrected exact tuple and permitted commands.
- `taut/dev-docs/PythonOneOfCheckpoint-Draft.md`.
- Python-relevant requirements throughout build-proposal sections 2–8, particularly descriptor publication, explicit validation semantics, source/package bindings, ownership transitions and conformance.
- The behavioral proposal's native authoring, presence, construction and serialization requirements.
- `taut/dev-docs/examples/python-oneof/README.md`, snapshot script, feature/shape/core/parity results, and baseline evidence.
- Complete `taut/src/taut/gen/python_runtime.py`, `descriptors.py`, `validation.py`, `contracts.py`, `gen/python.py`, and `rules.py`.
- `gen/scaffold.py:639–777`, canonical fact definitions and freezing, shape-library foundation aliases and static-schema loading.
- Complete `test_oneof.py` and `test_python_runtime_distribution.py`.

Executed:

1. At start and end:

   ```text
   python -B taut-dev/taut/dev-docs/examples/python-oneof/review_snapshot.py --check taut-dev/taut/dev-docs/PythonOneOfCheckpoint-Snapshot.json
   ```

   Both returned:

   ```text
   af9f2516f0dcbf45853fb6ade39d207c7a84b6b282975bffa8fdd385b59cc996 165 files
   ```

   Read-only `git rev-parse HEAD`, using command-local `safe.directory`, independently confirmed both recorded HEADs.

2. After selecting current source with the supplied activation script:

   ```text
   python -B -m pytest taut-dev/taut/src/tests/test_oneof.py taut-dev/taut/src/tests/test_python_runtime_distribution.py --basetemp D:/projects/limbo/taut-dev/taut/dev-docs/examples/python-oneof/scratch/review-state/pytest -p no:cacheprovider -q
   ```

   Result: **105 passed in 7.70s**.

3. Scratch generation probe under `scratch/review-state/path-kind`: a handwritten regular file at `<out>/python/taut` caused `FileExistsError` after generation had written `api.py` and `__init__.py`. Before/after file snapshots differed. See P2-2.

4. Scratch generation/import probe under `scratch/review-state/early-consumer`: an explicitly bound package consumer generated before its source owner was omitted from the eventual owner-user inventory. Disabling the producer's validation removed the engine and broke the previously working consumer import. See P2-1.

5. In-memory descriptor-configuration probe using current `python_api`, frozen descriptor replacements, `SchemaBinding`, `validate_record` and `is_record_valid`: a known-rule constraint referring to no field/group was accepted and returned valid, complete success. See P2-3.

The scratch probes used current source, `-B`, and isolated application subprocesses with `-I -S -B`. No reviewed source was edited. No build, release, commit, push, tag or toolchain change was performed.

Existing logs were inspected, not added to the independently rerun test total: shape **190 passed**, core **809 passed**, and **16 existing codec parity variants GREEN**, with clean governance. Baseline evidence records the isolated unchanged-HEAD missing-document and Go newline failures, the original Java encoding failure, and the Git ownership error; its corrected Java/Git result is two passes. These are distinct evidence sets, not an additive feature-test total.

## Problem, requirement provenance, and scope

The operator authorized a complete Python reference batch through the existing native compiler route: mandatory immutable descriptors, optional thin validation methods, shared local/recursive report and Boolean validation, sparse oneof JSON, canonical runtime distribution, and necessary shape-library integration.

The observed starting gaps recorded by the brief and controlling design are the absence of that native semantic/runtime support and application-time authoring-schema loading in the Python shape library. The chosen implementation addresses those gaps through the existing emit route. Canonical facts, runtime-only imports and generated shape facts are necessary to the expressly requested compiler-free application path; the isolated source/package/library tests demonstrate that this route is feasible without a new dependency or toolchain prerequisite.

Authorized editable components are the Python runtime/compiler/tests/examples and the necessary `taut-shape-py` foundation/generated-fact integration. Other backends remain reference/regression dependencies. Nothing in this report requires implementing another backend, virtual selection, application graph rules, release machinery or unrelated baseline repairs.

The three findings are localized implementation defects within that authorization. They require neither a second compiler nor a broader runtime architecture. In particular:

- P2-1 concerns accounting for an explicitly named source consumer.
- P2-2 concerns an ordinary filesystem conflict detectable before mutation, not a demand for multi-file crash rollback.
- P2-3 concerns rejecting malformed configuration at the existing public binding boundary.

The documented unchanged baseline defects do not demonstrably block this Python deliverable. No unauthorized prerequisite or component expansion was established.

## 1. Findings

### [P2-1] Consumers generated before the source owner are omitted from shared-use accounting

**Location:** `taut/src/taut/gen/python_runtime.py:133–138, 162–172`, especially the `owner_path.exists()` condition at line 136.

**Violated invariant:** Disabling one schema must not delete the validation engine required by another schema sharing its owner. Build proposal §7.1 expressly preserves the shared engine for other schemas; §7.4 requires cleanup to respect shared use, and §8 requires exercising source/package compositions and shared users.

**Reproduction:** With an otherwise unconstrained `Record(data: INT)` schema and an explicit binding to a fresh `foundation` root:

1. Emit consumer A with `runtime_mode="package"`, `validation=True`, and that `source_root`.
2. Emit producer B with `runtime_mode="source"`, `validation=True`, and the same binding.
3. Import A in a clean subprocess using the newly created foundation. `A.Record(1).is_valid()` returns `True`.
4. Re-emit B with source mode and `validation=False`.
5. Import A again.

Observed:

```text
owner manifest after consumer: False
registered users: {<producer manifest>: {'validation': True}}
consumer import exit before transition: 0
validation engine after producer off: False
consumer import exit after transition: 1
```

The final diagnostic reports that the required validation engine is missing/incompatible.

A's schema-output manifest records the selected source root, but A is not recorded in the runtime's users. Consumer registration is conditional on the runtime manifest already existing. The subsequent producer does not recover the earlier consumer registration. Cleanup therefore deletes `validation.py` while a successfully operating generated consumer still requires it.

**Impact:** A supported generation ordering becomes operational, then a producer-only mode change breaks another schema. The break is fail-closed at import, but the shared-runtime lifecycle is incorrect.

**Required correction:** Do not successfully accept an explicit source-consumer binding while silently omitting its use requirement. Either preserve that requirement safely before owner materialization, or reject the unavailable explicit source-owner binding before writing consumer outputs with an actionable diagnostic. Later cleanup must account for every accepted consumer.

**Closure/regression test:** Cover consumer-first package/source and supplied/source ordering with consumer validation enabled. After successful composition, disable or detach the producer and verify that the consumer still imports and validates. If the chosen policy rejects consumer-first generation, assert that rejection occurs before writes; then generate the owner, register the consumer, and verify subsequent cleanup preserves its engine.

### [P2-2] A regular file at the runtime-directory path bypasses preflight and leaves partial outputs

**Location:** `taut/src/taut/gen/python_runtime.py:142–155`; failure becomes visible in `apply_outputs` at lines 181–187. Schema writes are already planned at lines 113 and applied first.

**Violated invariant:** Source emission must preflight the complete output set and fail before replacing outputs on handwritten/path conflicts. This is required by build proposal §7.4 and the explicit §8 partial-write conformance requirement.

**Reproduction:** Under a fresh output root:

```python
(root / "python").mkdir(parents=True)
(root / "python/taut").write_text("HANDWRITTEN RUNTIME PATH")
emit(schema(Record=Msg(data=F(1, INT))),
     root, langs=["python"], runtime=True)
```

Observed:

```text
FileExistsError [WinError 183]: ...\python\taut
before: ['python\taut']
after: ['python\__init__.py', 'python\api.py', 'python\taut']
unchanged: False
handwritten preserved: HANDWRITTEN RUNTIME PATH
```

`runtime_dir.exists()` is true, but `rglob("*")` on the regular file yields no conflicting entries. Checks for individual desired runtime files also miss the obstructing ancestor. `apply_outputs` writes the schema files, then fails trying to create the `taut` directory.

**Impact:** The handwritten file survives, but generation leaves schema outputs that were not present before the rejected operation, without their completed ownership manifest/runtime. A later attempt can encounter those new files as unknown outputs. This is a deterministic preflight defect, not an interrupted-write or resource-failure case.

**Required correction:** Preflight the type and suitability of existing directory components for all planned writes, including the runtime package directory, before applying any write. Reject a regular file occupying a required directory with a named-path migration/fresh-root diagnostic.

**Closure/regression test:** Put a handwritten regular file at the intended runtime directory, snapshot all output bytes and paths, request source generation, and assert a named preflight error with an identical snapshot afterward. Also cover an explicit external source root and preserve the existing ownership-conflict tests.

### [P2-3] Known-rule constraint parameters can be invalid while validation reports complete success

**Location:** `taut/src/taut/descriptors.py:175–177`; `taut/src/taut/validation.py:212–215`.

**Violated invariant:** Descriptor links and configuration must be checked before use; invalid descriptor configuration is a configuration error, not successful validation. Build proposal §§3, 5 and 6 require this, including the shared `(value, descriptor, binding)` engine interface.

**Reproduction:** Generate a normal `Record(data: INT)` module in memory. Construct frozen replacements:

```python
d = replace(
    m.Record.DESCRIPTOR,
    constraints=(ConstraintDescriptor(
        "taut.oneof.v1",
        {"controlling_field": "not_a_field", "version": 999},
    ),),
)
registry = replace(m.SCHEMA_DESCRIPTOR, messages={"Record": d})
binding = SchemaBinding(
    registry, m.BINDING.message_classes, m.BINDING.enum_classes
)
report = validate_record(m.Record(1), d, binding)
```

Observed:

```text
binding accepted, report valid: True complete: True fast: True
```

This descriptor declares a known oneof constraint with a nonexistent controlling field, no corresponding oneof group, and an unrecognized parameter. `SchemaBinding` checks only the rule identifier. The engine evaluates `desc.oneofs` and never interprets or validates that constraint declaration, so it returns empty, complete success.

No generated source was modified. This exercises the public shared binding/engine configuration boundary in the same manner as the existing malformed-descriptor tests.

**Impact:** Malformed declared constraints are silently ignored. Recognizing a rule name is insufficient to establish that its parameters and links are supported. The existing unknown-rule test does not cover this route.

**Required correction:** Validate the supported parameter shape and links for each known constraint, including consistency with its normalized oneof group. Reject dangling, malformed, unsupported or unrepresented declarations before the binding can be used. Keep one authoritative evaluation path.

**Closure/regression test:** Assert configuration failure for a known-rule constraint with a nonexistent controller, missing corresponding group, and unsupported parameters. Include a valid matching constraint control case and retain rejection of unknown rule identifiers and unsupported contract/IR versions. Neither report nor Boolean validation may return success for the malformed configuration.

## 2. Invariant analysis

The following attacks held within the tested scope:

- **Tuple stability:** Both repository HEADs and all 165 inventoried source hashes remained unchanged.
- **Recorded-content protection:** Manifest reads verify recorded files against hashes; focused tests reject modified files, handwritten/unknown runtime files, incompatible contracts and conflicting mode selections without changing their snapshots.
- **Existing-owner sharing:** Repeated source emission shares one owner; existing registered consumers preserve required shared components. The uncovered exception is consumer registration before owner creation, P2-1.
- **Locking:** Lock roots are resolved and acquired in a stable order; scaffold includes the previous owner root and checks for an intervening owner-root change. The existing nested-lock test passes. No claim is made that these cooperative locks prevent arbitrary external filesystem edits.
- **Recovery direction:** Individual replacements are atomic, and subsequent hash checks reject inconsistent recorded state. The documented fresh-root/user-managed migration limit after interrupted multi-file writes is consistent with the authorized contract. P2-2 is a preventable preflight conflict outside that exception.
- **Immutable snapshots:** Published descriptor containers and diagnostic collections are frozen/copied. Tests preserve earlier reports and paths after message, map and source metadata mutations.
- **Traversal:** Tests cover independent groups, wrong discriminator isolation, populated nonselected children, shared child paths, recursive schemas, active-ancestor cycles and continuation into independent branches.
- **Scope and completeness:** Local validation excludes descendants; virtual groups contribute deferred checks; supported child traversal continues. Boolean results equal report validity and completeness for the covered inputs.
- **Runtime composition:** Isolated tests exercise actual source/package/supplied imports, disabled children, shape-library aliases, shared codec/descriptor/report identity and rejection of missing/incompatible owners. No application-time compiler or authoring-loader dependency was required.
- **Configuration rejection:** Unknown rule identifiers, incompatible descriptor/IR contracts and incorrect root/descriptor pairings are rejected. Known-rule parameter/link consistency remains open as P2-3.

All three findings are bounded implementation corrections. None requires changing the authorized ownership architecture or implementing deferred feature scope.

## 3. Risks and next action

The focused suite passes, but it does not cover the three reproduced counterexamples. Existing parity evidence establishes codec regression coverage, not completeness of the new feature.

Multi-file crash rollback remains explicitly outside the promise. Virtual selection remains intentionally deferred and incomplete. Unchanged baseline documentation/newline failures remain disclosed external limitations.

The next action is one merged remediation patch for P2-1 through P2-3, with their regression tests, followed by verification of the original counterexamples and the focused gates against a newly recorded source tuple. No commit or release action is authorized.
