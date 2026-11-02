# Java/Kotlin OneOf checkpoint — State-AXIS REVIEW

**Review object:** Remediation1 candidate at Taut `8682555a66e61659c465092b461d3b2cb4c58ff4`, controlled by `dev-docs/JvmOneOfCheckpoint-Draft.md`. Full pair range: `1607b6e0b000f607153b2ec20fc244aeb5952744..8682555a66e61659c465092b461d3b2cb4c58ff4`; corrected range: `92c6894dc9a8d071a5637c086aa56292b649adf1..8682555a66e61659c465092b461d3b2cb4c58ff4`.

**Baseline:**

| Repository | Corrected reviewed HEAD |
| --- | --- |
| Taut | `8682555a66e61659c465092b461d3b2cb4c58ff4` |
| GWZ workspace | `183359cdefae3921d65c208eec85ca048da58db8` |
| Python shape reference | `c08c2a1b5197f761c5b0b835c588da512130ceda` |
| Rust shape reference | `8e92b89ed3a4f218a5a4e018fbfee6301fcc14b4` |

Committed objects and the verified archive snapshot at `D:\projects\limbo\toolchain-readiness-2026-11-02\jvm-review-scratch\source-8682555-64lpy6d5` supplied the reviewed bytes.

**Date:** 2026-11-02

**Axis:** Durable-state semantics, filesystem ownership, failure/restart direction, compatibility publication and immutable observation state across both JVM targets and shared dispatch. Independent, adversarial, read-only. This is the same originating State reviewer. The current Code re-review remains peer-blind; nothing here relies on its result. Filed verbatim by the lane owner.

**Verdict: GO** — originating State P2-1 is closed. No new P0, P1, P2 or P3 findings. The correction is localized and does not materially invalidate the prior architecture or mutation-boundary proofs.

---

## 0. Evidence base

### Tuple, inventory and authority

At review start and end, ran per-command `git -c safe.directory=<repo> -C <repo> rev-parse HEAD` for all four repositories. Every SHA matched the corrected tuple above at both boundaries.

Verified at both boundaries:

- All 108 recorded content hashes and sizes in `JvmOneOfCheckpoint-Inventory-1.json` match committed bytes and the supplied snapshot.
- The full pair diff contains exactly its 109 allowed paths.
- The corrected range contains exactly the 11 existing changed paths and 32 added records identified by that inventory.
- The committed inventory itself matches snapshot bytes. Its SHA256 is `4cfb14fb779799e8c78469814e697e5788c615ffa62bb4d75ac1d22df5e3bf57`.

Read the complete State re-verdict prompt, merged RemPlan-1 and both prior reports. The prior reports are legitimate remediation input. No current-round peer prompt or report was read.

Rechecked the DRAFT amendment, Authority and applicable proposal requirements against the correction. Retained the original State inspection of both complete target implementations, runtime foundations, shared dispatch/ownership helpers and Python/Rust references; inspected the entire corrected range independently.

### Corrected implementation inspection

Examined:

- `java_metadata.py:33–45`: copied message records, field-number normalization and Case normalization before hashing.
- `java.py:141–143`: signed-long enum constructor literals.
- `cli.py:166–184` and `kotlin_package.py:53–61`: help-only changes.
- `test_java_oneof.py:465–573`: reordered dependency composition, genuine mismatch rejection, signed-i64 and help regressions.
- The existing Java literal assertion correction and both golden deltas.
- Updated DRAFT, Java INTEGRATION/RESULTS, inventory and committed remediation/global evidence.

The Java/Kotlin runtime classes, Kotlin emitter/engine, source ownership planners, shared scaffold, physical-path guards, locks and application helper have no remediation-range production changes.

### Independently executed corrected-source checks

Used the prescribed toolchain activation and Python 3.11 interpreter, corrected-snapshot `PYTHONPATH`, disabled bytecode/pytest plugin/cache writes, UTF-8 settings, and scratch TEMP/TMP. All generated outputs stayed under:

`D:\projects\limbo\toolchain-readiness-2026-11-02\jvm-review-scratch\state`

Executed the original independent State two-field declaration-order reproducer against corrected source. Details appear in the closure table below.

Ran the authorized two-file pytest command with:

```text
-k "reordered_external or normalized_external or signed_i64_enum or jvm_help"
```

Result: **17 passed, 144 deselected in 30.59s**.

Separately repeated the State ownership/preflight/namespace/shared-user/CLI/mode-golden selection:

```text
-k "preflight or shared_users or shared_source_users or guarded_outputs
or modified_unknown or unknown_shared_user or ambiguous_roots
or namespace_identity or bad_programmatic_modes or cli_conflicts
or cli_agreeing or keyword_forwarding or goldens"
```

Result: **66 passed, 95 deselected in 1.39s**.

Both invocations used `-q -p no:cacheprovider` and separate scratch `--basetemp` directories.

Repeated independent historical-root probes against corrected Java, Kotlin and accepted Rust helpers. All passed:

- Equivalent `..` roots preserved another active user’s engine.
- Safe extended Windows namespace spellings retained physical identity.
- Ambiguous extended namespace trailing-dot/space, reserved-name and ADS components were rejected without output changes.
- File obstructions and actual NTFS junction owner roots failed closed.
- Equivalent extended/`..` spellings could not bypass an existing generation lock.
- Physical-alias overlapping writes failed before replacing existing bytes.

Also ran corrected `taut.cli --help`, `taut.cli gen --help` and `taut.gen.kotlin_package --help`.

### Committed gate evidence and its limits

Read the actual remediation logs:

- `java-closure-tests.log`: **17 passed**.
- `target-gate.log`: **141 passed, 1 failed**; failure was the obsolete source assertion expecting `BUILT(1)`.
- `literal-expectation.log`: corrected `BUILT(1L)` assertion’s isolated rerun **1 passed**.
- `preservation-gate.log`: **865 passed**.
- `examples.log`: source/package reports identical; Java8 compilation/execution and engine-free descriptor/adapter routes passed.

The target log is not relabeled as a clean 142-pass single run. Production was unchanged between that run and the isolated assertion rerun. These overlapping runs are not added into a cumulative pass total.

Consumed the committed original global receipts under `dev-docs/examples/jvm-oneof/global-r0`, including exact tuple/results, parity log, broad failure traces and baseline-source proof.

That global gate remains at **Taut `92c6894d…` / workspace `07b5853c…`**, not the corrected tuple:

- All 16 codec variants GREEN, zero failures or governance violations.
- Broad suite: **1620 passed, 3 established baseline failures, 4 skipped, 8 deselected**.
- The three failures were the historical missing document and two Windows Go CRLF/gofmt cases.
- Relevant baseline source blobs were unchanged; source and tuple were unchanged during that run.

No duplicate broad/all16 matrix was run. This report relies on the original global evidence only within the unchanged implementation boundary, supplemented by corrected-source focused evidence.

## Problem, requirement provenance, and scope

The authorized outcome remains Java/Kotlin implementation of mandatory immutable descriptors, optional thin instance validation, shared lightweight foundations, source/package/supplied delivery, independent dependency composition and protected output ownership.

Original implementation work addressed the demonstrated absence of those facilities through the existing compiler and standalone JVM routes. Remediation addresses two concrete Java generation defects and incomplete help identified by the original reviews.

The fingerprint remedy restores the required equivalence of normalized dependency facts. Long literals make existing signed-i64 enum values usable without changing their numeric or wire meaning. Help changes document existing inputs and defaults. Each is a localized remedy; none requires new infrastructure or expansion into another backend.

The changed production components fall within the authorized Java/shared ownership and Kotlin package-help contribution. No user authoring source, accepted reference implementation or unrelated project changed. No installation, dependency upgrade, fabricated shape repository, public Java projection, serializer or publication prerequisite was introduced.

No scope or necessity gap remains on this axis.

## Prior-finding closure table

| ID | Disposition claimed | Verified on corrected tree | Status |
| --- | --- | --- | --- |
| State P2-1 | Canonicalize Java message fields and Case nominations without weakening genuine mismatch checks | Reran my original two-field, separately compiled, engine-free package composition. Both fingerprints now match; both compilation steps succeed; `Parent.descriptor()` publishes successfully. Independently ran all eight field+Case reorder composition combinations and all four genuine-mismatch rejection cases. | **CLOSED** |

The prior Code findings were reviewed as legitimate context. The independently rerun signed-i64 and help regression cases corroborate their remedies; their originating closure testimony belongs to the Code re-verdict.

### Original State counterexample rerun

Generated outputs are retained under:

`D:\projects\limbo\toolchain-readiness-2026-11-02\jvm-review-scratch\state\r1-java-order-probe`

Used the original native definitions:

```python
a = schema(Msg("Child", F("a", 1, INT), F("b", 2, INT)))

b = dataclasses.replace(
    a,
    messages={
        "Child": dataclasses.replace(
            a.messages["Child"],
            fields=tuple(reversed(a.messages["Child"].fields)),
        ),
        **schema(Msg("Parent", F("child", 1, Ref.Child))).messages,
    },
)
```

Built the corrected canonical foundation with `validation=False`, separately generated/compiled the disabled child, then generated/compiled the parent against the unchanged child using its explicit compatible external binding.

Both `javac --release 8` compilation steps returned 0. The original `OrderProbe` calling `Parent.descriptor().name()` now returned **exit 0** and printed:

```text
Parent
```

Both Java fingerprints were:

```text
bc202c0821110b3ea3c1fc5c7a5c81e677c8b6d015b708dc749a1f78e3f041d8
```

The accepted normalized reference comparison also remained equal. The original runtime publication failure is no longer reproducible.

The positive regression matrix additionally verifies unchanged disabled-child API bytes, descriptor identity, canonical field order, enabled-parent recursive behavior, local scope and codec composition across all four source/package combinations and both parent validation modes.

The negative matrix actually compiles and executes parents with changed field type, rule nominations, reservations and inherited effective decode options. Every case still rejects descriptor publication with the imported-facts mismatch diagnostic.

## Changed-range analysis

The 11 existing changed paths consist of:

- Two Java generation corrections: fingerprint normalization and enum literal spelling.
- Shared CLI and Kotlin package-helper help text.
- Java regression additions, one obsolete literal assertion update and two attributed goldens.
- DRAFT and Java integration/results documentation.

The 32 added paths are inventory, prior review/plan/verdict and execution-evidence records. No out-of-plan change was found.

Fingerprinting copies the message and field records before sorting, so it does not mutate exported input facts. It changes only treatment of declaration order already canonicalized by emitted descriptors. Effective options and genuine field/rule/reservation differences remain included and rejected when different.

Adding `L` to enum constructor arguments preserves accepted values, signatures, descriptor facts and CBOR behavior. Both i64 extrema and values immediately outside signed-int bounds compiled and ran in the independently repeated regression matrix. The golden changes are confined to these suffixes.

Help changes affect descriptions and metavariables, not parsing behavior, option names or defaults. Kotlin package-building behavior is unchanged.

**Reviewer classification:** These are localized implementation/documentation corrections within the intended contract. They do not introduce a material architecture, public interface, mutation-boundary, platform or semantic compatibility-rule change requiring replacement reviewers. No new architectural root cause was identified.

## 1. Findings

No new findings. Originating State P2-1 is closed by the corrected implementation, original-counterexample rerun and positive/negative regression evidence.

## 2. Invariant analysis

**Compatibility publication:** Equivalent Java dependency facts now publish successfully. Actual field, rule, reservation and inherited-option mismatches remain configuration failures before usable validation. Normalization does not admit incomplete-data success or regenerate dependencies.

**Mandatory metadata and typed ownership:** Descriptor-only composition still works without the optional engine. Positive tests retain one actual foundation and child descriptor identity while preserving disabled-child bytes. Runtime adapter/report/engine APIs and optional-child traversal dependencies are unchanged from the original reviewed implementation.

**Filesystem lifecycle:** Repeated tests and independent probes preserved shared users and engine requirements across mode transitions. Modified/unknown contents, namespace ambiguity, junctions, obstructions, aliases and locks remained fail-closed. The correction does not alter write ordering or deletion authority.

**Observation state:** Report/path snapshots, active-ancestor traversal and virtual incompleteness implementations are unchanged. Their original executable proofs remain applicable; the new composition tests exercise recursive behavior through independently compiled disabled children.

**Distribution:** Corrected-source target evidence includes the real compiler-wheel/resource/generate/compile/run route for both targets. Canonical foundation sources are unchanged. Normal applications continue to require the selected JVM foundation rather than compiler or delivery engines.

## 3. Risks and next action

The broad/all16 gate was not repeated on `8682555a…`; its evidence remains explicitly limited to the original tuple. The localized changed range, corrected-source focused gates and unchanged runtime/mutation boundaries support carrying that evidence forward without claiming a new global run.

Whole-generation crash atomicity remains outside the accepted substrate’s promise. Per-file replacement and stale-lock/manual-inspection behavior are unchanged.

The next action is for the lane owner to merge this State GO with the independent Code re-verdict on the exact corrected tuple and record acceptance only if both axes permit it. This verdict authorizes no push, release, installation or publication.
