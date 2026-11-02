# PythonOneOfCheckpoint — STATE-AXIS RE-REVIEW, REMEDIATION 2

**Review object:** Python reference checkpoint at working-tree source digest `3dd141a8433aaef152a285327d8091870a2eb3865eba7f8cb3cc78c70f901bd2`, 165 files, recorded in `taut/dev-docs/PythonOneOfCheckpoint-Snapshot-2.json`.

**Baseline:** taut HEAD `2cfee5d6156b0179066dc4eed70f60cde489a422`; taut-shape-py HEAD `da79bfb74376802edcd25049ed4ce29de814db44`. Reviewed current inventoried source bytes. The revised inventory and both repository HEADs matched at review start and completion.

**Date:** 2026-11-02

**Axis:** State — final focused closure of filesystem ownership/preflight findings, retention of earlier closures, and examination of the two changed files. Independent, adversarial, read-only. Nothing here relies on the other current-round review. Filed verbatim by the lane owner.

**Verdict: GO** — all three original State findings are closed, including the extended P2-2 deletion-junction counterexample. No open P0–P3 finding was identified in this focused re-review.

**New architectural root causes:** None. No architectural or interface change requiring fresh reviewers was identified.

---

## 0. Evidence base

Read:

- `PythonOneOfCheckpoint-RePromptState-2.md`.
- `PythonOneOfCheckpoint-RemPlan-2.md`.
- `PythonOneOfCheckpoint-ChangedRange-2.json`.
- The revised source inventory.
- Revised runtime inventory checks in `gen/python_runtime.py:160–171`.
- Revised mutation preflight in `gen/python_runtime.py:199–222`.
- The retained obstruction/link tests and exact cleanup-junction regression in `test_python_runtime_distribution.py:339–387`.

Only `gen/python_runtime.py` and `test_python_runtime_distribution.py` changed from remediation 1. The original authority, controlling requirements and prior State reports remain applicable.

Executed against current source selected by the supplied activation script:

```text
python -B -m pytest taut-dev/taut/src/tests/test_oneof.py taut-dev/taut/src/tests/test_python_runtime_distribution.py --basetemp D:/projects/limbo/taut-dev/taut/dev-docs/examples/python-oneof/scratch/review-state/pytest-r2 -p no:cacheprovider -q
```

Result: **128 passed in 10.34s**.

Independently reran the original obstruction and extended deletion-junction counterexamples under:

```text
dev-docs/examples/python-oneof/scratch/review-state/r2-original-probes
```

Also directly exercised `apply_outputs` with an ordinary planned write and an aliased deletion target, verifying that deletion preflight prevents the ordinary write.

Rechecked the original malformed-descriptor and unavailable-consumer cases. No reviewed source was edited.

Start/end inventory verification returned:

```text
3dd141a8433aaef152a285327d8091870a2eb3865eba7f8cb3cc78c70f901bd2 165 files
```

Both repository HEADs remained unchanged. No commit, push, tag, release, toolchain change or other-backend implementation was performed by this reviewer.

## Problem, requirement provenance, and scope

The required outcome remains the authorized Python reference batch with explicit validation, immutable shared metadata, canonical source/package runtime identity, and safe filesystem ownership and cleanup.

This patch completes the already-required preflight boundary. It does not add a runtime owner, persistence format, dependency, backend implementation or authoring interface. Checking deletion paths alongside write paths is a localized correction; broader crash rollback is unnecessary.

The operator's confirmed Enum reservation policy and leading-double-underscore Python field policy remain unchanged. The new authorization for the lane owner to commit an accepted Python milestone does not expand this review into release activity or Rust production implementation.

No unsupported prerequisite or unauthorized scope expansion was identified.

## Prior-finding closure table

| Original finding | Verification on final source | Closure |
| --- | --- | --- |
| P2-1 — unrecorded consumer-first source use | Package and supplied consumers explicitly bound to an unavailable owner still fail with the named owner-unavailable error, leaving paths and bytes unchanged. The focused suite retains accepted-consumer registration and engine preservation through producer disabling/detachment. | **CLOSED** |
| P2-2 — incomplete filesystem preflight | Original regular-file obstructions fail unchanged for default and external roots. The exact in-owner cleanup-junction sequence now fails before mutation, preserving unowned target files, generated outputs, both manifests and the junction. A direct mixed write/delete plan also fails before its ordinary write. | **CLOSED** |
| P2-3 — malformed known-rule declaration returns success | The original malformed declaration still raises `ConfigurationError` during binding construction; the valid control remains successful. The focused suite retains parameter/group consistency cases. | **CLOSED** |

## 1. Findings

None.

## 2. Changed-range and invariant analysis

**Runtime inventory rejects redirected directories.** The planner now checks the runtime package directory and each scanned entry for aliases/reparse points before proceeding. The exact previously accepted `taut/wire` junction into an unowned, in-owner sibling directory is rejected with a named directory-alias error.

The independent reproduction preserved:

- All four unowned canonical-copy files and their bytes.
- Generated `api.py` and `__init__.py`.
- `.taut-python-outputs.json` and `.taut-runtime.json`.
- The complete observed directory/file inventory and junction.

**The mutation boundary checks writes and deletions.** `apply_outputs` materializes deletions and preflights the union of write and deletion targets. It checks lexical ancestors for aliases or obstructing files before performing any replacement or unlink.

This was verified independently of the inventory scan: an aliased deletion target combined with an ordinary planned marker write raised `ValueError`; the marker was absent afterward and the complete snapshot was unchanged. This demonstrates that the final mutation guard itself covers the previously omitted deletion path.

**The original obstruction remains fixed.** A handwritten regular file at the intended runtime-directory path produced a named preflight error with unchanged paths and bytes in both default-root and explicit external-root probes.

**Earlier closures remain intact.** The unavailable-consumer checks and descriptor binding logic were not changed in this patch. Their original counterexamples were rechecked, and the complete focused suite passed. The retained tests also cover shared-consumer lifecycle, linked write directories, unknown/modified ownership, distribution combinations and report/Boolean behavior.

**No broader state boundary moved.** Manifest format, source-consumer accounting, canonical runtime identity and validation traversal remain unchanged. The patch strengthens checks before the existing write/delete boundary. No new architectural root cause or additional review-axis requirement arose.

## 3. Risks and next action

The documented limit on multi-file crash rollback remains: interrupted mutation can require a fresh output root or explicit user-managed migration. Cooperative generation locks do not promise protection from arbitrary concurrent external edits. Neither limitation invalidates the tested preflight guarantees.

Virtual selection remains deliberately deferred. Existing baseline regression limitations remain separately disclosed. This focused source verdict does not attribute an earlier wheel or incomplete broad-run result to the final digest.

The State axis approves this exact source tuple. The lane owner may merge the independent verdicts, finish and file the final checkpoint evidence, and perform the operator-authorized Python milestone commit. No push, tag, release or Rust production implementation is approved by this report.
