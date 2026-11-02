# PythonOneOfCheckpoint — CODE + SURFACE-AXIS RE-REVIEW 2

**Review object:** Final bounded remediation, frozen source digest `3dd141a8433aaef152a285327d8091870a2eb3865eba7f8cb3cc78c70f901bd2`, 165 files, recorded in `D:/projects/limbo/taut-dev/taut/dev-docs/PythonOneOfCheckpoint-Snapshot-2.json`.

**Baseline:** taut HEAD `2cfee5d6156b0179066dc4eed70f60cde489a422`; taut-shape-py HEAD `da79bfb74376802edcd25049ed4ce29de814db44`. Previous reviewed source digest: `3294c812442cfd09d618e8e63d7587932c43cf26dcffbc73125c835654982135`.

**Date:** 2026-11-02

**Axis:** Focused Code + Surface re-verdict, retaining prior finding closure and inspecting cleanup preflight changes. Independent, adversarial and read-only except authorized scratch probes. No other current-round report was consulted. Filed verbatim by the lane owner.

**Verdict: GO** — all three originating Code findings remain closed. No new P0–P3 finding or new architectural root cause was identified.

---

## 0. Evidence base

Read the final re-review prompt, `PythonOneOfCheckpoint-RemPlan-2.md`, `PythonOneOfCheckpoint-ChangedRange-2.json`, both changed files, and retained prior-round Code reports and context.

The source inventories were independently compared. Exactly two files changed from remediation 1:

- `D:/projects/limbo/taut-dev/taut/src/taut/gen/python_runtime.py`
- `D:/projects/limbo/taut-dev/taut/src/tests/test_python_runtime_distribution.py`

Beginning and ending snapshot checks both returned:

```text
3dd141a8433aaef152a285327d8091870a2eb3865eba7f8cb3cc78c70f901bd2 165 files
```

Read-only Git inspection confirmed both assigned HEADs remained unchanged.

Independent current-source probes reran:

- All three original Code counterexamples.
- The original regular-file runtime-directory obstruction, with default and explicitly bound runtime owners.
- The extended source-to-package cleanup sequence using a directory junction pointing to unowned, byte-identical runtime files.

All scratch writes remained under:

```text
D:/projects/limbo/taut-dev/taut/dev-docs/examples/python-oneof/scratch/review-code
```

The focused suite was independently rerun with current-source activation, plugin autoload disabled and scratch basetemp:

```text
python -B -m pytest taut-dev/taut/src/tests/test_oneof.py taut-dev/taut/src/tests/test_python_runtime_distribution.py -q -p no:cacheprovider --basetemp D:/projects/limbo/taut-dev/taut/dev-docs/examples/python-oneof/scratch/review-code/round2-pytest
```

Result: **128 passed in 10.98s**.

The recorded feature and shape logs report **128 passed** and **190 passed**, respectively. The prior core 809 and codec parity evidence remains prior-run evidence; no final broad-run result was assumed.

At inspection, wheel verification still identified remediation-1 digest `3294c8…`. This report does not attribute that artifact verification to the final source digest.

## Problem, requirement provenance, and scope

The requested outcome remains the complete Python reference checkpoint, including explicit runtime ownership and safe generator-owned output transitions.

The final correction addresses the already identified filesystem preflight boundary: cleanup must not traverse an alias and delete unowned files merely because their bytes match recorded runtime hashes. Protecting deletion targets is necessary for the existing ownership contract; it adds no new feature or prerequisite.

The operator’s naming decisions remain unchanged: leading-double-underscore Python fields are rejected, internal substrings remain permitted, and the referenceable Enum API retains its documented metadata reservations.

The operator now authorizes the lane owner to commit the intended Python milestone after successful review and checkpoint completion. That authority does not authorize reviewer mutations, release operations, or Rust implementation in this review.

No new runtime owner, persistence format, platform baseline, dependency, backend implementation or architectural boundary was introduced. Continuing with the original reviewers is appropriate.

## 1. Prior-finding closure

| Finding | Original counterexample rerun on final source | Disposition |
| --- | --- | --- |
| **P2-1 — private-name mangling** | `F("__private", 1, INT)` rejected with a named diagnostic and unchanged outputs in source/package/supplied modes, validation off/on. | **Closed; remains closed** |
| **P2-2 — enum metadata collisions** | Original sequences using members `name`, `members`, and `options` stop at declaration with the documented metadata-namespace diagnostic. | **Closed; remains closed** |
| **P2-3 — false compatibility breaks** | Unrelated `MISSING_OK` field addition and declaration reordering remain accepted by the compatibility gate. | **Closed; remains closed** |

The naming and compatibility implementation files did not change in this round. Their extended regression cases also remain in the passing 128-test focused suite.

No new finding is raised.

## 2. Changed-range and invariant analysis

### Runtime inventory checks

At `D:/projects/limbo/taut-dev/taut/src/taut/gen/python_runtime.py:160–166`, runtime inventory scanning now rejects aliases/reparse points at the runtime directory and encountered paths before planning mutation.

This closes the cleanup route in which a recorded runtime subdirectory is replaced with an in-owner junction to unowned files whose content hashes happen to match.

### Mutation preflight

At `D:/projects/limbo/taut-dev/taut/src/taut/gen/python_runtime.py:203–211`, preflight covers the union of write and deletion targets. It checks their lexical ancestors and target aliases before the first replacement or deletion.

The change extends the existing preflight boundary to cleanup. It does not replace ownership metadata, introduce adoption behavior, or change runtime-mode selection.

### Independent obstruction and cleanup probes

Both original regular-file obstruction variants failed before output changes.

For the extended cleanup sequence, the independent probe:

1. Generated a source runtime.
2. Copied its four wire files into an unowned sibling directory.
3. Replaced only the verified scratch-generated wire directory with a Windows junction to that sibling.
4. Requested a source-to-package transition.
5. Compared the complete file-content snapshot before and after rejection.

Generation rejected the aliased wire directory with:

```text
unsafe/obstructed output directory alias
```

All four unowned target files survived unchanged. Generated API files and both ownership metadata contents also remained unchanged.

The new regression at `D:/projects/limbo/taut-dev/taut/src/tests/test_python_runtime_distribution.py:367` covers this sequence. Existing obstruction, linked-write-directory, consumer lifecycle and normal transition tests remain passing.

### Surface and architecture

No CLI flag, default, authoring interface, validation signature or distribution-selection meaning changed. The correction strengthens the existing promise that unknown or aliased paths fail before output mutation.

This remains the same bounded preflight root cause. No new architectural root cause or material change requiring fresh reviewers was identified.

## 3. Risks and next action

This GO covers the final frozen source on the Code + Surface axis. It does not claim a completed final broad regression run or refreshed final-digest wheel verification.

Virtual selection remains deliberately incomplete. Other backend implementation and release operations remain outside this checkpoint.

The lane owner should merge the two independent final verdicts at this exact digest, complete and record the remaining final evidence, then perform only the authorized Python milestone commit. The reviewed source digest and both repository HEADs remained unchanged through final verification.
