# YIDL/Taut Python Records Patch Release — CODE + SURFACE-AXIS CLOSURE REVIEW

**Review object:** Taut `2dbc07d51f9c358e5681f507ba3778fdbe057dad`; unchanged YIDL dataclass `48ba94efd26ff300345f3bdca38987b90a13f79b`. Bounded remediation round 1, controlled by `dev-docs/YIDLRecordsPatchRelease-RemPlan-1.md`.

**Baseline:** Original reviewed Taut `f81a206d64b58d705d9cc853e5bea69550fb9e98`. Sources inspected through immutable Git objects and the exact correction diff.

**Date:** 2026-11-03

**Axis:** Same-originator Code + Surface closure. Independent, adversarial, read-only; nothing here relies on another reviewer’s verdict. Filed verbatim by the lane owner.

**Verdict: GO** — P2-1 is closed; no remaining findings on this axis. Acceptance covers these sources entering the mandatory remaining qualification gates, not completed publication.

---

## 0. Evidence base

Read the committed remediation plan and complete `f81a206..2dbc07d` diff. Inspected the generator guard, README restriction and regression tests. Read `taut-name-fix-tests.log`, recording **30 passed**.

Both named objects resolved to their exact supplied SHAs at the start and end. No tests, builds, installations, writes, Git mutations or credential access were performed.

## Problem, requirement provenance, and scope

The original defect allowed YIDL generation to succeed for fields that YIDL rejects during module import. The human explicitly selected rejection only with the YIDL backend, rather than attribute projection.

The correction implements that authorized choice locally. It introduces no SDK, runtime, ownership or architectural change. The unchanged original review conclusions remain applicable outside this bounded correction.

## 1. Prior-finding closure

| Finding | Verification | Disposition |
|---|---|---|
| P2-1: YIDL-specific field restrictions discovered after output writes | The generator now collects a schema-qualified collision for stored `self`, `cls` and `_y_dc_*` fields when—and only when—YIDL is selected. Existing collision handling raises before source return or output application. | **Closed** |

The regression matrix covers all three original counterexamples × validation OFF/ON × programmatic/CLI entry points. Each case checks an absent output directory and preservation of an existing handwritten file. The same schemas import and construct with stdlib records. The legal `freeze` field is exercised with validation OFF/ON.

## 2. Invariant analysis

The guard is conditional on `yidl_records` and excludes virtual fields, which do not become stored Python declarations. Stdlib name acceptance remains unchanged. Existing preflight ordering prevents both new output creation and modification of existing output.

The changed range consists of the localized guard, focused tests, README clarification, remediation plan and filed prior reports. No new architectural root cause or unrelated implementation change was introduced.

## Surface

The README now explicitly identifies `self`, `cls` and `_y_dc_*` as unsupported stored names for YIDL, states that rejection occurs before writes, and preserves their legality under stdlib. This closes the original diagnostic and documentation gap.

## 3. Risks and next action

Proceed through the configured dependency-first release gates. Exact YIDL qualification/publication, Taut qualification against the public dependency, candidate/version/tag verification, hosted publication, artifact provenance and fresh public consumers remain mandatory. The focused 30-test result does not replace those gates.
