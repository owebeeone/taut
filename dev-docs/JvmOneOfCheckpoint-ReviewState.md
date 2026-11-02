# Java/Kotlin OneOf checkpoint — State-AXIS REVIEW

**Review object:** Full 77-file Java/Kotlin pair diff `1607b6e0b000f607153b2ec20fc244aeb5952744..92c6894dc9a8d071a5637c086aa56292b649adf1`, controlled by `dev-docs/JvmOneOfCheckpoint-Draft.md` at the latter revision. Status: frozen acceptance-review candidate.

**Baseline:** Taut `92c6894dc9a8d071a5637c086aa56292b649adf1`; GWZ workspace `07b5853cf31911e45945b88eabc270b0b7680de5`; Python shape reference `c08c2a1b5197f761c5b0b835c588da512130ceda`; Rust shape reference `8e92b89ed3a4f218a5a4e018fbfee6301fcc14b4`. Sources were read through committed Git objects and the verified isolated archive snapshot.

**Date:** 2026-11-02

**Axis:** Durable-state semantics, filesystem ownership, restart/failure behavior, compatibility publication and immutable observation state across both targets and shared dispatch. Independent, adversarial, read-only. The other axis runs in parallel; nothing here relies on it. Filed verbatim by the lane owner.

**Verdict: NO-GO** — one P2 compatibility finding blocks. No P0 or P1 findings. I pre-commit to GO on a revision that resolves P2-1 as specified and passes its regression and applicable focused gates.

---

## 0. Evidence base

### Object and authority verification

At review start and end, ran per-command `git -c safe.directory=<repo> -C <repo> rev-parse HEAD` for all four repositories. All four SHAs matched the tuple above at both boundaries.

Verified that:

- The committed diff contains exactly the inventory’s 77 allowed paths.
- All 76 recorded, non-self inventory SHA256 values match committed bytes.
- Those committed bytes, including the inventory itself, match the isolated snapshot.
- End-of-review inventory SHA256 is `823fcd7b14ca47a936c017a9df9d6f203679c7ef91892552374b74804d2984fe`.

Read the State prompt, review-loop skill and canonical template, workspace `AGENTS.md`/`AGENTS_GWZ.md`, Taut `AGENTS.md`, proposal, Authority, DRAFT, Inventory and Preparation records. The other current-round prompt/report was neither requested nor read.

### Implementation and reference inspection

Inspected both targets and their integration, including:

- `java_metadata.py:1–188`, `java_runtime.py:1–244`, Java emitter changes and all new Java descriptor/report/adapter/engine classes.
- `kotlin_metadata.py:1–213`, `kotlin_runtime.py:1–163`, `kotlin_package.py:1–59`, Kotlin emitter changes, `descriptors.kt:1–223` and `validation.kt:1–109`.
- `scaffold.py:583–831`, CLI changes, package-data declarations, Java parity source enumeration and codec changes.
- Both OneOf test files, changed existing backend tests, compiler-wheel test, examples, goldens and provenance/report evidence.
- Accepted Python `validation.py`, `descriptors.py`, `rules.py`, `facts.py`; Rust runtime descriptor/validation code, `rust_metadata.py:63–78`, and Python/Rust physical-path, planner, lock and apply seams.
- Both languages’ README/INTEGRATION/RESULTS documents, checkpoint WheelGate, accepted Python baseline-evidence JSON and Rust broad-regression failure evidence.
- Committed Python shape static-fact loading and Rust shape foundation re-exports as reference-only integration evidence.

### Independently executed checks

Used the specified Python 3.11 interpreter, activated prepared toolchains, snapshot-only `PYTHONPATH`, disabled bytecode/pytest plugins/cache, UTF-8 Java options, and confined generated outputs to:

`D:\projects\limbo\toolchain-readiness-2026-11-02\jvm-review-scratch\state`

Executed both cold CLI help commands.

Ran the authorized two-file pytest command with these selections:

1. Ownership/preflight/namespace/shared-user/CLI/mode-golden selection:

   `-k 'preflight or shared_users or shared_source_users or guarded_outputs or modified_unknown or unknown_shared_user or ambiguous_roots or namespace_identity or bad_programmatic_modes or cli_conflicts or cli_agreeing or keyword_forwarding or goldens'`

   **66 passed, 78 deselected in 1.98s.**

2. Descriptor-only, runtime-publication, artifact-replacement and observation-state selection:

   `-k 'descriptor_without_engine or descriptors_without_engine or actual_artifacts or runtime_build_labels or separately_linked or immutable_metadata or recursive_virtual_cycle or enabled_parent_disabled or inconsistent_import_facts or mismatched_child_facts or artifact_provenance'`

   **19 passed, 125 deselected in 198.02s.**

The first attempted ownership invocation encountered only missing scratch-parent setup errors. After creating the expressly authorized State scratch directory, the same selection passed. Those setup errors are not product failures.

Independent executable filesystem probes passed for Java, Kotlin and historical Rust ownership roots:

- Equivalent `..` spellings preserved another active user’s engine.
- Safe extended Windows namespace spellings retained physical identity.
- Extended namespace trailing-dot/space, reserved-name and ADS spellings failed before output changes.
- File obstructions and actual NTFS junction owner roots failed closed.
- Physically aliased overlapping writes were rejected without replacing existing bytes.
- Equivalent extended/`..` owner spellings could not bypass an existing generation lock. Existing lock bytes survived, and newly created empty schema directories were removed.

The separate Java dependency-order reproducer described in P2-1 compiled successfully and then failed descriptor publication as reported.

### Completed sole global gate

Consumed the completed watcher evidence under:

`D:\projects\limbo\jvm-oneof-scratch\global-gate-r0`

Read `global-results.json`, parity log/JSON, broad-regression failure output, baseline-source proof, source/tuple before-and-after records and `run-global-gate.py`.

The watcher ran `parity.run_gate(require_all=True, jobs=2)`: **all 16 variants GREEN**, every variant available, zero failed results and no governance violations.

Its broad command used Python 3.13:

```text
python.exe -m pytest D:\projects\limbo\taut-dev\taut\src\tests
-q -m "not gate" -p no:cacheprovider
--basetemp D:\projects\limbo\jvm-oneof-scratch\global-gate-r0\pytest-temp
--junitxml D:\projects\limbo\jvm-oneof-scratch\global-gate-r0\broad-results.xml
```

Result: **1620 passed, 3 failed, 4 skipped, 8 deselected in 797.86s**. The broad process correctly exited 1. Its only failures were:

- Missing `TautProtoApiSurfaceExtensions.md`.
- Go runtime/parity-runner gofmt cleanliness under Windows CRLF.
- Generated Go gofmt cleanliness under Windows CRLF.

The baseline proof shows six relevant source blobs unchanged from original baseline `2cfee5d6156b0179066dc4eed70f60cde489a422`, with the document absent at both baseline and frozen revision. These match the previously recorded baseline counterexamples. `new_failures=[]`.

The watcher recorded unchanged tuples and unchanged source inventory; independently compared its 207 before/after source entries and found zero changes. Aggregate watcher elapsed time was 840.63s. These results satisfy the global-gate dependency but do not cover P2-1.

## Problem, requirement provenance, and scope

The requested outcome is the next authorized backend pair after accepted Python/Rust: mandatory immutable message descriptors in both validation modes, optional thin instance validation, shared lightweight target foundations, source/package/supplied delivery, independent dependency composition, and protected output ownership.

The observed gap was concrete: Java/Kotlin lacked those descriptors, adapters and validation surfaces, while legacy resource copying lacked the required ownership lifecycle. Extending the existing compiler/emitter and canonical runtimes addresses that gap.

Authority explicitly covers Java/Kotlin implementation, tests/examples, local package-build proof and necessary shared CLI/scaffold/package-resource wiring. The inventory matches that component boundary. Accepted core/Python/Rust and shape repositories remained reference-only; concurrent USER Enum.case work and disclosed generated/wheel noise were excluded.

The existing standalone `javac` and `kotlinc` routes were feasible. Local compilation, descriptor-only closures, independent child composition and compiler-wheel evidence demonstrate that no new dependency infrastructure, toolchain upgrade, invented shape repository, native JSON serializer or public multi-file Java projection was necessary. Java 8 syntax adjustments are localized implementation choices backed by retained codec gates.

No unauthorized expansion or unsupported prerequisite was established. The remaining defect is within the required independent-artifact compatibility boundary: semantically identical Java dependency facts are rejected because their authoring declaration order differs.

## 1. Findings

### [P2-1] Java fingerprints treat equivalent field declaration order as an incompatible dependency

**Location:** `src/taut/gen/java_metadata.py:33–34`, used for published message fingerprints at line 168 and imported-message checks at lines 183–184. The same emitter already sorts descriptor fields by tag at lines 150–156 and 168.

**Violated invariant:** Independently generated artifacts with equivalent normalized native facts must compose against the same foundation. Compatibility checks must retain semantic differences while ignoring authoring order that the emitted metadata itself canonicalizes.

`fingerprint()` uses JSON key sorting but does not normalize message field arrays or Case arrays. Consequently, identical fields declared in another order produce different fingerprints even though generated descriptor fields are published in the same field-number order. Accepted Rust normalization explicitly sorts fields and cases; Kotlin uses that normalization.

**Executed reproduction:** All generated files are retained under:

`D:\projects\limbo\toolchain-readiness-2026-11-02\jvm-review-scratch\state\java-order-probe`

The essential schema construction was:

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

Built an engine-free canonical foundation using `java_runtime.build_foundation(..., validation=False)`. Emitted and separately compiled `a` as the child in package mode. Emitted `b` as the parent in package mode with the explicit compatible external binding:

```python
{
    "Child": {
        "type": "taut.Child",
        "owner": "taut.java.foundation",
        "descriptor_contract": 1,
        "codec_contract": 1,
        "capabilities": ["codec.v1", "descriptors.v1", "oneof.v1"],
    }
}
```

Both `javac --release 8` compilations succeeded. The parent probe was:

```java
package taut;
public class OrderProbe {
    public static void main(String[] args) {
        System.out.println(Parent.descriptor().name());
    }
}
```

Ran:

```text
java -cp <parent-classes>;<child-classes>;<foundation.jar> taut.OrderProbe
```

Actual result: exit 1, `ExceptionInInitializerError`, caused by:

```text
taut.validation.ConfigurationException:
Child: imported message facts mismatch;
regenerate/rebind the compatible foundation and schema artifacts
```

The Java fingerprints were:

```text
a,b declaration: bc202c0821110b3ea3c1fc5c7a5c81e677c8b6d015b708dc749a1f78e3f041d8
b,a declaration: 4aafcee108bb985df16be7486ed656cfe8c081fc2d03c1b3a4807d904830c32f
```

The accepted normalized reference fingerprints compared equal for these same two native message definitions.

**Impact:** A harmless declaration reorder prevents an independently compiled Java dependency from publishing mandatory descriptors. It affects validation-off composition as reproduced; enabling validation cannot repair the shared publication failure. The diagnostic incorrectly directs regeneration/rebinding for artifacts whose semantic facts already agree.

**Required correction:** Canonicalize message facts before computing both published and expected Java fingerprints. Sort fields by numeric tag and normalize Case ordering consistently, while retaining effective options, reservations, rules and other actual compatibility facts. Do not weaken genuine mismatch rejection.

**Closure/regression test:** Separately compile a disabled child, then compile and execute a parent supplied the same dependency facts with reversed field declaration order. Require successful descriptor publication and recursive enabled-parent behavior against that unchanged child. Include reordered equivalent Case declarations, both validation modes, and source/package composition. Retain a nearby genuine field/rule/effective-option mismatch case that must still fail publication.

## 2. Invariant analysis

**Filesystem ownership and transitions:** Both planners maintain separate schema/runtime manifests, verify recorded content, preserve positive shared users and remove an engine only when no recorded user needs it. Targeted tests and independent probes resisted modified/unknown contents, incompatible manifests, equivalent roots, junctions, namespace ambiguity, obstructions, overlapping plans and lock aliasing.

**Failure and restart direction:** Shared dispatch collects plans under selected/prior-root locks and invokes common physical-target preflight before replacement. Files are replaced individually. A crash can leave a stale lock or a partially applied generation requiring inspection/migration; whole-generation crash atomicity is not promised by the accepted substrate. I found no additional concrete pair regression warranting a finding under that boundary.

**Runtime identity and publication:** Actual old/split/substituted artifacts and mismatched dependency facts were rejected in focused executable tests. Compatible unequal build labels linked. Descriptor-only closures worked without optional engines, and disabled child validation methods were not traversal dependencies. P2-1 is an over-rejection within this otherwise fail-closed publication mechanism.

**Metadata and observation state:** Inspected static typed attachment paths, recursive publication links, immutable metadata collections/bytes and report/path snapshots. Focused tests preserved snapshots after mutation, distinguished virtual incompleteness from success, retained supported child traversal, and matched recursive/local/cycle/key reports to the reference. Shared children were observed per path; active-ancestor cycles produced diagnostics.

**Distribution and compiler separation:** Canonical source/package inventories and compiler-wheel evidence cover both target resource closures. Normal target applications use the selected JVM foundation and generated schema rather than compiler, authoring or delivery engines.

## 3. Risks and next action

The passing global matrix has no new failures, but it lacks the equivalent Java dependency-order composition case. Its existing mismatch tests therefore do not close P2-1.

The single next action is a bounded, coordinated remediation of P2-1 with the specified regression, followed by originating State verification on a newly settled tuple. Production was not edited during this review. No push, release, installation or publication is implied by this verdict.
