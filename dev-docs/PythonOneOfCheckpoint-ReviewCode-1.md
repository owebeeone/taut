# PythonOneOfCheckpoint — CODE + SURFACE-AXIS RE-REVIEW 1

**Review object:** Remediation round 1, frozen source inventory `3294c812442cfd09d618e8e63d7587932c43cf26dcffbc73125c835654982135`, 165 files, recorded in `D:/projects/limbo/taut-dev/taut/dev-docs/PythonOneOfCheckpoint-Snapshot-1.json`.

**Baseline:** taut HEAD `2cfee5d6156b0179066dc4eed70f60cde489a422`; taut-shape-py HEAD `da79bfb74376802edcd25049ed4ce29de814db44`. Original reviewed source digest: `af9f2516f0dcbf45853fb6ade39d207c7a84b6b282975bffa8fdd385b59cc996`. Source was read directly; inspection and probes were read-only except explicitly permitted scratch outputs.

**Date:** 2026-11-02

**Axis:** Focused Code + Surface re-verdict, including original-counterexample closure and changed-range regression analysis. Independent and adversarial. No other current-round report was consulted. Filed verbatim by the lane owner.

**Verdict: GO** — all three prior Code findings are closed. No new P0–P3 findings were identified in the reviewed changes. No new architectural root cause was identified.

---

## 0. Evidence base

Inputs read:

- The original Code review and retained review context.
- `D:/projects/limbo/taut-dev/taut/dev-docs/PythonOneOfCheckpoint-RePromptCode-1.md`.
- `D:/projects/limbo/taut-dev/taut/dev-docs/PythonOneOfCheckpoint-RemPlan-1.md`.
- `D:/projects/limbo/taut-dev/taut/dev-docs/PythonOneOfCheckpoint-ChangedRange-1.json`.
- The eight changed files identified by the source inventories.

The changed-file inventory was independently recomputed from the original and revised snapshots. It exactly matched the declared **eight files**.

Beginning and ending source checks returned:

```text
3294c812442cfd09d618e8e63d7587932c43cf26dcffbc73125c835654982135 165 files
```

Read-only Git inspection confirmed both assigned HEADs remained unchanged.

All original counterexamples were rerun independently using current source selected by the supplied activation script. Writes remained under:

```text
D:/projects/limbo/taut-dev/taut/dev-docs/examples/python-oneof/scratch/review-code
```

The focused suite was independently rerun:

```text
python -B -m pytest taut-dev/taut/src/tests/test_oneof.py taut-dev/taut/src/tests/test_python_runtime_distribution.py -q -p no:cacheprovider --basetemp D:/projects/limbo/taut-dev/taut/dev-docs/examples/python-oneof/scratch/review-code/round1-pytest
```

Result: **127 passed in 9.35s**.

Existing evidence inspected:

- Feature gate: 127 passed.
- Core regression gate: 809 passed.
- Shape-library gate: 190 passed.
- Codec parity: all 16 variants GREEN; governance clean.
- Refreshed wheel verification explicitly identifies the revised source digest, 12 matching foundation files, 16 isolated behavior/scope rows, compiler imports blocked, and actual library type identity.

The refreshed wheel SHA-256 is:

```text
6474763dc484f6b9416b5471624a9b1ae922ec4d34abb976c7f28ae64ab158e5
```

I independently verified that artifact hash and compared all 12 recorded foundation files inside the wheel byte-for-byte with current canonical source.

These test counts describe separate gates and are not added into an aggregate total.

## Problem, requirement provenance, and scope

The authorized outcome remains the Python reference implementation through the existing compiler route, with mandatory descriptors, optional validation methods, shared validation/report semantics, sparse oneof JSON, canonical source/package runtime ownership, and the necessary shape-library migration.

The operator explicitly confirmed that leading-double-underscore Python fields are unsupported. That decision applies to Python field prefixes across validation and runtime modes; it does not prohibit internal substrings such as `part__name` or authorize restrictions on other targets.

The remediation stays within the original boundary:

- Private-name rejection repairs Python generation preflight.
- Early enum namespace rejection implements a remedy permitted by the original finding and the controlling proposal.
- Normalized compatibility comparison restores the existing compatibility policy.
- Runtime ownership and descriptor checks strengthen previously required boundaries.

No new dependency, toolchain prerequisite, runtime owner, persistence format, application graph rule, or backend implementation was introduced. The patch does not require a new architectural review round with fresh reviewers: these are bounded corrections to already reviewed contract boundaries. The same-axis focused re-review remains appropriate.

## 1. Prior-finding closure

| Finding | Original counterexample rerun | Result | Disposition |
| --- | --- | --- | --- |
| **P2-1** — private-name mangling | `schema(Msg("Record", F("__private", 1, INT)))` through source, package and supplied runtime, validation off/on | All six combinations fail with a named `Record.__private` diagnostic before changing output contents. `part__name` still generates and binds correctly in both validation modes. | **Closed** |
| **P2-2** — enum metadata collisions | Original `Enum("Choice", name=0)`/`Case(tag=choice.name)` sequence, repeated for `members` and `options` | Each sequence now stops at `Enum` declaration with a member-specific metadata-namespace diagnostic. Ordinary qualified members remain supported. | **Closed** |
| **P2-3** — false compatibility breaks | Original unrelated `MISSING_OK` addition and declaration-order reversal | Addition produces only its compatible field-addition result; reordering produces no changes. The compatibility gate accepts both. | **Closed** |

### P2-1 closure evidence

`D:/projects/limbo/taut-dev/taut/src/taut/gen/python.py:29–31` rejects fields whose names start with `__` before source emission.

Independent probes preserved a handwritten marker and compared complete output-file snapshots before and after every rejected generation. All six snapshots were unchanged.

The internal-substring probe generated `part__name` in both validation modes and verified both instance access and its recorded descriptor attribute. This follows the operator’s scoped decision without broadening it.

### P2-2 closure evidence

`D:/projects/limbo/taut-dev/taut/src/taut/ir/dsl.py:118–121` reserves `name`, `members`, and `options` at enum declaration.

Each original counterexample now reports the conflicting member and the definition-metadata namespace, before `Case` can receive an unrelated metadata value. The README documents the policy and ordinary qualified-member syntax. No alternate authoring interface was added.

The focused suite retains ordinary qualified-member behavior and wrong-enum rejection.

### P2-3 closure evidence

`D:/projects/limbo/taut-dev/taut/src/taut/ir/compat.py:97–100` compares constraint-bearing facts by field name and normalizes Case ordering.

The original addition now returns:

```text
Change(level='compatible',
       detail='Record.later (tag 3) added (missing_ok)')
```

The original declaration-order reversal returns:

```text
[]
```

Independent positive-break probes used coherent schemas and confirmed that changes to payload ownership, virtual policy, exhaustive policy, rule removal, and controlling-field identity still produce the constraint/projection breaking result.

## 2. Changed-range and invariant analysis

The eight changed files were inspected as follows:

| Changed component | Analysis |
| --- | --- |
| Python generator | Adds early private-name rejection; existing keyword projection and descriptor/validation reservations remain intact. |
| Native DSL | Adds the documented enum metadata reservation at declaration; ordinary reference construction is unchanged. |
| Compatibility classifier | Ignores unrelated fields and declaration order when comparing constraints; genuine semantic/projection changes remain visible. |
| Descriptor binding | Checks duplicate controllers, exhaustive coverage, exact supported constraint parameters, group/declaration correspondence, and typed descriptor links before publication. Shared descriptor identities and traversal entry points remain unchanged. |
| Runtime output handling | Rejects unavailable explicitly bound source consumers and preflights obstructed/linked output components before applying writes. It preserves existing ownership metadata formats and explicit distribution selection. |
| Feature tests | Adds targeted regressions for private names, internal substrings, enum reservations, compatibility normalization, and malformed constraint configuration. |
| Distribution tests | Adds consumer-first rejection, registered-consumer retention, obstructed runtime paths, and linked-directory rejection. These ran in the independent 127-test gate. |
| Example README | Documents the accepted field and enum namespace policies without claiming additional backend completion or release authorization. |

### Surface and compatibility

The corrections make rejected names diagnosable before generated artifacts are written. The README now explains both name policies. No CLI flag, default, command placement, runtime-selection meaning, or validation signature changed.

The focused distribution suite continues to exercise source/package/supplied delivery, enabled/disabled generation, CLI conflicts and forwarding, independently generated dependencies, actual shape-library identity, source-only application imports, and reversible owned-output transitions.

The refreshed wheel contains the revised canonical descriptor implementation. Its recorded isolated application and library identity checks therefore apply to the revised source rather than the earlier artifact.

No material interface, architecture, mutation-boundary, compatibility-policy, platform-assumption, or call-graph replacement was found that invalidates continuation with the original reviewers.

## 3. Risks and next action

This GO covers the revised Python source checkpoint and the focused remediation on this axis. Virtual selection remains intentionally incomplete. Other backend feature implementation, releases, commits, pushes and tags remain outside scope.

The previously documented unrelated baseline failures remain disclosed; this report makes no full-suite-green claim.

The next action is for the lane owner to merge this re-verdict with the other axis’s independent re-verdict on the same source digest and record the resulting checkpoint status. The source inventory and both repository HEADs remained unchanged through final verification.
