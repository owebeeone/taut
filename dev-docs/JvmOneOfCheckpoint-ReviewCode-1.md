# Java/Kotlin OneOf checkpoint — Code + Surface-AXIS REVIEW

**Review object:** Remediation 1 at Taut `8682555a66e61659c465092b461d3b2cb4c58ff4`, controlled by [JvmOneOfCheckpoint-Draft.md](D:/projects/limbo/taut-dev/taut/dev-docs/JvmOneOfCheckpoint-Draft.md). Full pair range: `1607b6e0b000f607153b2ec20fc244aeb5952744..8682555a66e61659c465092b461d3b2cb4c58ff4`. Changed range: `92c6894dc9a8d071a5637c086aa56292b649adf1..8682555a66e61659c465092b461d3b2cb4c58ff4`. Status: corrected frozen candidate awaiting originating re-verdicts.

**Baseline:**

| Repository | Reviewed HEAD |
| --- | --- |
| Taut | `8682555a66e61659c465092b461d3b2cb4c58ff4` |
| GWZ workspace | `183359cdefae3921d65c208eec85ca048da58db8` |
| Python shape reference | `c08c2a1b5197f761c5b0b835c588da512130ceda` |
| Rust shape reference | `8e92b89ed3a4f218a5a4e018fbfee6301fcc14b4` |

Sources were inspected through exact Git objects and the verified archive snapshot at `D:/projects/limbo/toolchain-readiness-2026-11-02/jvm-review-scratch/source-8682555-64lpy6d5`.

**Date:** 2 November 2026  
**Axis:** Code architecture, interfaces, compatibility, semantic call graphs, ownership integration, and user-facing Surface. Same originating reviewer, independent, adversarial, read-only. Prior reports and the merged remediation plan were legitimate inputs. No current-round State report was accessed. Filed verbatim by the lane owner.

**Verdict: GO** — both originating P2 findings and the P3 finding are closed. No new findings.

---

## Prior-finding closure table

| ID | Disposition claimed | Verified on corrected tree | Status |
| --- | --- | --- | --- |
| Code P2-1 | Canonicalize message fields and Case nominations before hashing | Re-ran the original independently compiled reordered-child/enabled-parent counterexample: both compilations returned 0; execution returned 0 and printed `true`. Executed all eight reordered field+Case composition cases and all four genuine-mismatch cases. | **Closed** |
| Code P2-2 | Emit Java enum constructor arguments as long literals | Re-ran the original signed-i64-extrema OneOf generation and `javac --release 8` command: compilation returned 0. Executed all four source/package × validation-mode compile/run cases, including values immediately outside signed-int bounds and both i64 extrema. | **Closed** |
| Code P3-1 | Correct supported targets, method spellings, JSON-file inputs, and defaults in help | Read corrected help before code/DRAFT inspection and executed the help regression. Java/Kotlin support, `validate/isValid`, `JSON_FILE`, mapping/binding defaults, and Kotlin package validation defaults are explicit. | **Closed** |
| State P2-1 | Same fingerprint root, corrected once | Read the prior State counterexample and merged disposition. Independently verified the common root through the original Code counterexample and the descriptor-only/enabled composition matrix. The originating State reviewer owns its formal closure. | Common correction verified on this axis |

## Changed-range analysis

The full pair diff contains exactly the corrected inventory’s **109 paths**. The remediation range contains exactly **11 changed existing paths and 32 added review/evidence records**.

The changed production behavior is confined to:

- [java_metadata.py:33](D:/projects/limbo/taut-dev/taut/src/taut/gen/java_metadata.py:33): copy and sort message fields by tag and Case nominations by controlling field/enum/member before hashing.
- [java.py:142](D:/projects/limbo/taut-dev/taut/src/taut/gen/java.py:142): append `L` to enum constructor literals.
- [cli.py:169](D:/projects/limbo/taut-dev/taut/src/taut/cli.py:169): help/metavar text.
- [kotlin_package.py:55](D:/projects/limbo/taut-dev/taut/src/taut/gen/kotlin_package.py:55): argparse help/metavar text.

The remaining existing-path changes are the controlling DRAFT amendment, Java integration/results documentation, the two attributed Java goldens, the new regression matrix, and the existing `BUILT(1)` assertion corrected to `BUILT(1L)`. Both golden diffs contain only enum literal suffix changes. No out-of-plan change was found.

**Reviewer classification: localized implementation correction.** The hash correction implements the already-required equivalence of normalized facts; it does not introduce a different semantic compatibility policy. It retains the other compatibility facts and does not mutate exported input records. The literal correction preserves the declared long values and wire representation. Help changes leave option names, defaults, forwarding, and execution unchanged.

No descriptor/adapter/report API, runtime owner or contract version, engine predicate/traversal, codec algorithm, mutation boundary, locking rule, platform assumption, or dependency route changed. The prior architecture and ownership proofs remain applicable. No new architectural root cause or material change requiring replacement reviewers was established.

## 0. Evidence base

### Object, authority, and integrity

Read the complete canonical R1 prompt, both prior reports, [RemPlan-1](D:/projects/limbo/taut-dev/taut/dev-docs/JvmOneOfCheckpoint-RemPlan-1.md), corrected DRAFT, corrected inventory, changed integration/results documentation, and actual remediation/global evidence logs. Retained the original review’s authority, proposal, reference-source, and pair-wide implementation analysis.

Verified the R1 prompt SHA256:

```text
13fe08cb9bb78eebaf63ac1a8b611c70e694c0ea5ccef0607e92b234e85f6f05
```

At start and end, ran `git -c safe.directory=<repo> -C <repo> rev-parse HEAD` for all four repositories. Every SHA matched the tuple above.

Verified:

- Full baseline-to-corrected diff paths equal the 109-file allowlist.
- Changed-range paths equal the 11 existing-path and 32 new-evidence lists.
- All 108 non-self recorded hashes and sizes match exact committed Git blobs and snapshot bytes.
- Committed inventory bytes match the snapshot at both boundaries.

End inventory SHA256:

```text
4cfb14fb779799e8c78469814e697e5788c615ffa62bb4d75ac1d22df5e3bf57
```

No reviewed repository or snapshot was modified.

### Cold Surface reads

Before changed-code/DRAFT inspection, read:

```text
python -m taut.cli --help
python -m taut.cli gen --help
python -m taut.gen.kotlin_package --help
```

Also read both languages’ README and INTEGRATION pages. These corrected help outputs directly resolve the original cold-help counterexample.

### Independently executed corrected-source checks

Used the prescribed Python 3.11 interpreter, prepared toolchain activation, corrected snapshot `PYTHONPATH`, disabled bytecode/pytest-plugin/cache writes, and UTF-8 settings. All generated outputs remained under:

`D:/projects/limbo/toolchain-readiness-2026-11-02/jvm-review-scratch/code`

| Check | Result |
| --- | --- |
| Required selection across both feature files: `-k 'reordered_external or normalized_external or signed_i64_enum or jvm_help'` | **17 passed, 144 deselected in 31.03s** |
| Compiler-wheel, scaffold, CLI, and corrected existing Java literal assertion | **15 passed in 13.02s** |
| Original declaration-order reproducer | Child compilation 0; parent compilation 0; execution 0, output `true` |
| Original signed-i64 OneOf reproducer | Generation accepted; complete emitted source compiled successfully with `--release 8` |
| Java/Kotlin × source/package/supplied × validation off/on walkthrough | All 12 generated, compiled, and ran; source cleanup transitions passed |
| Java/Kotlin/Rust physical-root probes | Equivalent roots/users, safe namespaces, ambiguity rejection, obstruction rejection, and actual junction refusal passed |
| Common physical-overlap application probe | Rejected before mutation |

The original counterexamples were rerun without changing their schema or behavioral substance. Only the corrected import snapshot and fresh scratch destinations changed.

### Regression inspection

Inspected [test_java_oneof.py:467](D:/projects/limbo/taut-dev/taut/src/tests/test_java_oneof.py:467) through its new help test:

- Eight independent child/parent combinations cover field and Case reorderings, disabled children, both parent validation modes, and source/package combinations.
- Child API bytes remain unchanged after parent generation.
- Descriptor-only composition and recursive enabled-parent behavior execute against the actual compiled child.
- Field type, rule nomination, reservation, and inherited effective-option changes still fail actual publication.
- Four signed-i64 cases cover source/package and validation off/on, checking wire numbers, descriptors, payload behavior, roundtrips, and validation results.
- Help assertions exercise the actual CLI and Kotlin helper.

The fingerprint test also verifies that hashing leaves exported facts unchanged.

### Committed corrected-source evidence

Read the actual logs under `D:/projects/limbo/taut-dev/taut/dev-docs/examples/jvm-oneof/remediation-r1`:

- New closure cases: **17 passed**.
- Affected target command: **141 passed, 1 failed**. The sole failure was the obsolete `BUILT(1)` spelling assertion.
- Corrected assertion’s isolated rerun: **1 passed**, with production unchanged.
- Preservation gate: **865 passed**.
- Java source/package conformance and engine-free adapter examples passed.

This is evidence for 142 distinct affected target cases across the 141+1 runs, not a claim of one clean 142-case run. The original failed-first log is preserved. My independent current-source wiring run also passed the corrected assertion.

### Historical global evidence

Consumed the committed original global receipts under `D:/projects/limbo/taut-dev/taut/dev-docs/examples/jvm-oneof/global-r0`.

They remain explicitly tied to:

- Taut `92c6894dc9a8d071a5637c086aa56292b649adf1`.
- Workspace `07b5853cf31911e45945b88eabc270b0b7680de5`.
- The unchanged shape-reference SHAs.

All 16 codec variants were GREEN. The broad result was **1620 passed, 3 established baseline failures, 4 skipped, 8 deselected**; broad exit code 1 is retained. The only failures were the historical missing document and two Windows Go CRLF/gofmt cases.

Checked the preserved baseline-source proof, identical 207-entry before/after source inventories, identical before/after tuples, and all 16 available parity reports containing only passing or type-satisfied statuses.

This global matrix was **not rerun on R1** and is not represented as corrected-tuple evidence. No duplicate global matrix was run. Counts across these overlapping runs are not added.

## Problem, requirement provenance, and scope

The authorized outcome remains the Java/Kotlin continuation of the accepted native OneOf/mandatory-descriptor/explicit-validation proposal: immutable mandatory metadata, optional thin instance methods, shared semantic engines, lightweight canonical foundations, explicit source/package/supplied binding, independent dependency composition, and protected output ownership.

The original review identified two concrete Java blockers: equivalent dependency facts falsely rejected at publication, and valid long-valued OneOf enums failing compilation. The merged plan accepts both and authorizes localized corrections with originating verification. The help correction addresses the separately recorded documentation defect.

The remedy directly addresses those observed failures through the existing compiler and JVM routes. No new dependency, toolchain, package installation, registry infrastructure, reflection, common message base, shape repository, or serializer was needed. Independent compilation and execution demonstrate feasibility.

Changed components remain within the approved Java/shared implementation and Kotlin help-only ownership boundaries. Python/Rust/core/shape sources remain references. User Enum.case work, other backends/projects, and the disclosed generated/wheel noise remain excluded.

No unsupported prerequisite, unauthorized scope expansion, or unresolved authority gap was found. The three historical broad-suite failures remain separate baseline shortcomings.

## 2. Invariant analysis

### Compatibility correction

The corrected fingerprint sorts only the order-insensitive message arrays identified by the original counterexample. Copies prevent mutation of the exporter’s records. Both published and expected fingerprints use the same routine.

Actual execution now accepts equivalent field/Case declarations while retaining rejection of genuine field, rule, reservation, and effective-codec differences. No mismatch check was removed.

The original enabled-parent/disabled-child counterexample now completes successfully. The added descriptor-only cases verify that closure also holds when optional validation methods and engines are absent.

### Native enum and wire preservation

Long literal suffixes make accepted enum numbers legal Java source without changing their numeric values, native storage, descriptor values, or CBOR encoding.

Both original extrema now compile. Executed source/package cases additionally cover values immediately outside signed-int bounds, payload selection, payload-free choices, descriptors, and roundtrips. Validation-on/off behavior remains separate.

### Retained architecture and semantics

The semantic engines, typed callback/adaptor paths, immutable descriptor/report classes, recursive links, optional-child-method independence, runtime identities, and contract checks are unchanged from the pair-wide review.

The previous evidence for local/recursive scope, independent checks, populated nonselected children, zero/false/empty presence, virtual incompleteness, canonical paths, shared children, cycles, snapshots, and fast/report equivalence remains applicable. The corrected-source target and preservation evidence adds coverage at the modified boundaries.

The independently rerun compiler-wheel check verifies both current JVM resource closures and compiles/runs generated Java and Kotlin consumers from the unpacked wheel.

### Ownership and historical-root retrace

Neither target planner nor common lock/application code changed. Nevertheless, independently repeated the historical-root probes against the corrected snapshot:

- Equivalent `..` user/root spellings preserved another active user.
- Safe extended Windows namespaces retained physical identity.
- Trailing-dot/space, reserved-name, and alternate-stream namespace components failed.
- Parent file obstructions and actual directory junctions were rejected.
- Junction targets remained unchanged.
- Physically overlapping writes failed before creating the target.

No new ownership or mutation-boundary defect was reproduced.

### Surface

The original help mismatch is resolved. Help now identifies Java/Kotlin validation support and camelCase methods, JSON-file arguments, omitted external mappings, relevant bindings/defaults, classpath responsibility, and the Kotlin package helper’s validation default.

The first-day command shape was:

```text
python -m taut.cli gen <snapshot-example.taut.py>
    -o <fresh-scratch-output> -l java|kotlin --api-only
    [--runtime source|package] [--with-validation]
```

Omission exercised supplied-runtime mode. All 12 combinations generated, compiled, and executed descriptor queries and enabled validation calls. Regeneration from source to package removed owned runtime sources; temporary walkthrough outputs were cleaned.

Java’s package-private messages remain documented and authorized. Kotlin companion methods, facade naming, and runtime identities were not changed. No install/uninstall surface was introduced; local package artifacts remain explicitly supplied and publication remains deferred.

## 3. Risks and next action

The full global matrix belongs to the original tuple. Corrected-tuple confidence rests on the localized changed-range analysis, independently repeated original counterexamples, new positive/negative closure matrix, current compiler-wheel/wiring execution, first-day walkthrough, and recorded target/preservation gates. This evidence is sufficient for this bounded correction; no material change requiring a new architectural review was found.

Java compatibility remains `--release 8` compilation with execution on JDK17; a separate Java8 JVM execution claim is not made.

The next action is the lane owner’s exact-tuple verdict merge with the independent State re-verdict. This GO closes the originating Code findings and accepts this pair’s reviewed scope only; it authorizes no push, release, installation, publication, or other-backend continuation.
