# PythonOneOfCheckpoint — STATE-AXIS RE-REVIEW, REMEDIATION 1

**Review object:** Python reference checkpoint at working-tree source digest `3294c812442cfd09d618e8e63d7587932c43cf26dcffbc73125c835654982135`, 165 files, recorded in `taut/dev-docs/PythonOneOfCheckpoint-Snapshot-1.json`.

**Baseline:** taut HEAD `2cfee5d6156b0179066dc4eed70f60cde489a422`; taut-shape-py HEAD `da79bfb74376802edcd25049ed4ce29de814db44`. Reviewed current inventoried source bytes. The revised inventory and both HEADs were verified before substantive probes and again at completion.

**Date:** 2026-11-02

**Axis:** State — focused closure of the three original State findings and inspection of the remediation's changed ranges. Independent, adversarial, read-only. This report does not rely on the other current-round review. Filed verbatim by the lane owner.

**Verdict: NO-GO** — P2-1 and P2-3 are closed; P2-2 remains open because directory-alias preflight protects writes but not cleanup deletions. I pre-commit to GO when P2-2 is corrected as specified below, its original and extended counterexamples pass, and the focused gates remain green.

**New architectural root causes:** None. The remaining defect continues the existing filesystem preflight finding. The remediation does not require fresh reviewers on architectural grounds.

---

## 0. Evidence base

Read:

- `PythonOneOfCheckpoint-RePromptState-1.md`.
- `PythonOneOfCheckpoint-RemPlan-1.md`.
- `PythonOneOfCheckpoint-ChangedRange-1.json`.
- The revised source inventory.
- Complete revised `gen/python_runtime.py`.
- Revised descriptor binding checks, including `descriptors.py:160–215`.
- Changed Python field-name checks, Enum DSL reservation checks, normalized compatibility comparison, corresponding tests, and README migration/consumer-order documentation.

The original authority, common scope checks and controlling build-proposal requirements remain applicable.

Executed against current source selected by the supplied activation script:

```text
python -B -m pytest taut-dev/taut/src/tests/test_oneof.py taut-dev/taut/src/tests/test_python_runtime_distribution.py --basetemp D:/projects/limbo/taut-dev/taut/dev-docs/examples/python-oneof/scratch/review-state/pytest-r1 -p no:cacheprovider -q
```

Result: **127 passed in 9.43s**.

Independently reran all three original counterexamples, rather than relying only on the added tests. Additional lifecycle and deletion-alias probes stayed under `scratch/review-state`. Application imports used clean `-I -S -B` subprocesses. No reviewed source was edited.

Start/end revised inventory verification returned:

```text
3294c812442cfd09d618e8e63d7587932c43cf26dcffbc73125c835654982135 165 files
```

Both repository HEADs remained unchanged.

Existing result logs were inspected separately: feature 127 passes, core 809 passes, shape 190 passes, and 16 codec variants GREEN with clean governance. These are not added to the independently rerun feature count. Existing unchanged-baseline limitations remain disclosed.

## Problem, requirement provenance, and scope

The required outcome remains the authorized complete Python reference batch through the existing compiler/runtime route, with safe runtime ownership and cleanup, immutable descriptors and reports, and explicit validation.

The merged patch addresses the six accepted findings within the existing Python scope. The additional leading-double-underscore restriction is traceable to the operator's explicit decision; the Enum metadata reservation is documented and checked early. The source-consumer ordering rule is a bounded fail-closed correction permitted by the original State remedy, not a new infrastructure prerequisite.

No new dependency, backend implementation, runtime owner, persistence format or release action is introduced. A localized fix at the existing manifest/preflight boundary remains sufficient for the open defect. Neither multi-file crash rollback nor deferred virtual selection is required to close it.

## Prior-finding closure table

| Original finding | Original counterexample on revised source | Closure verdict |
| --- | --- | --- |
| P2-1 — unrecorded consumer-first source use | Package and supplied consumers explicitly bound to an unavailable source owner now fail with a named `ValueError`, leaving files and directories unchanged. After owner-first generation, accepted consumers remain registered; disabling and then detaching the producer preserves their engine and successful isolated imports. | **CLOSED** |
| P2-2 — obstructed runtime directory bypasses preflight | A regular file occupying the runtime directory now causes a named preflight error with an unchanged snapshot, for both default and external owner roots. However, the same ancestor/alias safety check is absent from cleanup deletions; the extended probe below deletes unowned target files through a directory junction. | **OPEN** |
| P2-3 — malformed known-rule declarations return success | The exact original malformed constraint now raises `ConfigurationError` during binding construction. A dangling controller without the extra parameter also fails. A valid unchanged binding still returns valid, complete report and Boolean success. | **CLOSED** |

## 1. Findings

### [P2-2] Cleanup deletions bypass directory-alias preflight and delete unowned target files

**Status:** Continuation of the original P2-2 filesystem preflight root cause. The original regular-file obstruction is fixed; the remediation's alias protection is incomplete.

**Location:** `taut/src/taut/gen/python_runtime.py:73–78, 160–167, 180–187, 199–206, 216–217`.

**Violated invariant:** Unknown directory aliases must not redirect generator mutation into unowned files. Cleanup may remove only positively identified, unmodified generator-owned files. Build proposal §7.4 requires detecting unknown ownership before mutation and protecting handwritten/unowned runtime content; §8 requires safe transition cleanup.

**Reproduction on the revised source:**

1. Emit a source-mode schema normally.
2. Copy its generated `python/taut/wire` directory into `python/handwritten-wire`, an unowned sibling directory under the same owner root.
3. Remove the original generated `wire` directory and replace it with a Windows directory junction pointing to `python/handwritten-wire`.
4. Re-emit the schema in package mode without an explicit source binding, requesting cleanup of its former source owner.

No ownership manifest was edited. The unowned target's files contain identical canonical bytes, so the existing hash checks pass.

Observed:

```text
handwritten target before: ['__init__.py', 'cbor.py', 'codec.py', 'jsoncodec.py']
generation accepted
handwritten target after: []
```

The probe ran under:

```text
dev-docs/examples/python-oneof/scratch/review-state/r1-deletion-alias
```

**Root cause:** Manifest verification resolves recorded paths and accepts targets that remain inside the owner root and match their recorded hashes. It does not reject the newly introduced directory junction. The runtime scan also does not reject that directory alias. `apply_outputs` then checks ancestors only for paths in `writes`; it performs `deletes` without the equivalent check.

Consequently, a recorded lexical path redirects cleanup into a different, unowned directory. Matching bytes do not establish ownership of that target location.

**Impact:** An accepted source-to-package transition deletes unowned copies of four runtime files through a redirected directory path. The demonstrated files are recoverable canonical copies; this finding does not claim that arbitrary modified content bypasses hash verification.

**Required correction:** Preflight deletion targets and their lexical directory components as well as write targets, rejecting unknown symlink/junction/reparse redirection before any output mutation. Alternatively, reject such redirected recorded paths during ownership verification before planning cleanup. Preserve the existing named diagnostic and unchanged-snapshot behavior.

**Closure/regression test:**

- Reproduce the in-owner directory-junction sequence above.
- Request source-to-package cleanup.
- Assert a named preflight failure and identical snapshots of schema outputs, runtime files, ownership metadata and the unowned target.
- Retain the original default/external regular-file obstruction tests and the empty linked-directory write test.
- Re-run the focused feature gate.

This is a bounded correction at the existing mutation boundary. It is **not a new architectural root cause**.

## 2. Changed-range analysis and invariant checks

**`gen/python_runtime.py`:** The unavailable explicit source-owner check correctly rejects consumer-first generation before output writes. Both package and supplied routes were independently exercised. Accepted owner-first consumers are recorded and preserve the engine across producer validation-off and producer detachment.

The new file/directory suitability checks correctly fix the original regular-file obstruction. Alias/reparse detection also protects the linked write-directory case exercised by the focused suite. The deletion path remains outside that preflight, as P2-2 demonstrates.

**`descriptors.py`:** Known oneof constraints now require the exact supported parameter set, a string controller, and a one-to-one relationship with normalized groups. Duplicate controllers and unsupported type/key configurations receive explicit checks. The original malformed declaration and a pure dangling-controller variant both fail at construction. Valid publication, report validation and Boolean validation continue to work.

**`gen/python.py`, `ir/dsl.py`, `ir/compat.py`:** The inspected changes implement bounded naming and compatibility corrections within the existing route. Leading private field names fail early; internal double-underscore substrings remain allowed. Enum metadata reservations are explicit. Compatibility compares normalized constraint-bearing facts independently of ordinary fields and ordering. Their focused tests pass. This State report does not substitute for the other axis's originating-finding closure.

**Tests and README:** The added cases cover the original State reproductions, accepted-consumer lifecycle, linked write directories and malformed known-rule variants. Documentation now states the owner-first requirement. The missing case is alias redirection during deletion.

No descriptor/report mutability regression, traversal change, runtime identity split, implicit validation path or new dependency was found in the changed ranges. The source tuple remained stable throughout the probes.

## 3. Risks and next action

The passing 127-case suite does not cover deletion through an aliased recorded directory. That concrete gap prevents closing P2-2 and accepting this revision.

Multi-file crash rollback remains outside the promise; virtual selection remains deliberately deferred; unchanged baseline regression limitations remain outside this Python remediation.

The next action is a bounded correction for deletion-target preflight, its regression test, and focused re-verification against a new source tuple. No commit, release or other-backend work is required or authorized.
