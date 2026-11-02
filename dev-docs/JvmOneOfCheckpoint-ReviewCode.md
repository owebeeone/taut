# Java/Kotlin OneOf checkpoint — Code + Surface-AXIS REVIEW

**Review object:** Full Java/Kotlin pair diff `1607b6e0b000f607153b2ec20fc244aeb5952744..92c6894dc9a8d071a5637c086aa56292b649adf1`, the 77-file committed inventory, and controlling `JvmOneOfCheckpoint-Draft.md`. Status: frozen implementation awaiting acceptance.

**Baseline:**

| Repository | Reviewed HEAD |
| --- | --- |
| Taut | `92c6894dc9a8d071a5637c086aa56292b649adf1` |
| GWZ workspace | `07b5853cf31911e45945b88eabc270b0b7680de5` |
| Python shape reference | `c08c2a1b5197f761c5b0b835c588da512130ceda` |
| Rust shape reference | `8e92b89ed3a4f218a5a4e018fbfee6301fcc14b4` |

Committed sources were inspected through `git show`/`git diff` and the verified archive snapshot at `D:/projects/limbo/toolchain-readiness-2026-11-02/jvm-review-scratch/source-92c6894-9jeev2qt`. All four HEADs matched at the start and end. The snapshot inventory matched committed bytes; all 76 listed content hashes and sizes matched at both checks. The inventory excludes its own hash and contains 77 allowlisted files.

**Date:** 2 November 2026  
**Axis:** Code architecture, interfaces, compatibility, semantic call graphs, ownership integration, and the cold user-facing Surface. Independent, adversarial, read-only. The other axis runs in parallel; nothing here relies on it. Filed verbatim by the lane owner.

**Verdict: NO-GO** — two P2 findings block; one P3 finding is nonblocking. I pre-commit to GO on a revision that resolves P2-1 and P2-2 as specified.

---

## 0. Evidence base

### Authority and source inspection

Read the review-loop skill and canonical prompt template, workspace AGENTS/AGENTS_GWZ, Taut AGENTS, and these controlling documents at the reviewed revision:

- [Authority](D:/projects/limbo/taut-dev/taut/dev-docs/JvmOneOfCheckpoint-Authority.md), including the explicit pair-freeze amendment.
- [Controlling DRAFT](D:/projects/limbo/taut-dev/taut/dev-docs/JvmOneOfCheckpoint-Draft.md), all sections.
- [Inventory](D:/projects/limbo/taut-dev/taut/dev-docs/JvmOneOfCheckpoint-Inventory.json).
- [Build proposal](D:/projects/limbo/taut-dev/taut/dev-docs/OneOf-ExplicitValidation-BuildProposal.md), particularly descriptor inventory/publication, semantics, exact JVM methods, foundation ownership, compatibility, and conformance gates.

Read both languages’ README, INTEGRATION, RESULTS, examples, adapters, runners, recorded outputs and provenance. The first reads were snapshot `taut.cli --help`, `taut.cli gen --help`, and both example README/INTEGRATION pages, before implementation or DRAFT inspection. Also inspected the `corpus`, `json`, `parity`, and Kotlin package-builder help.

Reviewed the full changed production set:

- `D:/projects/limbo/taut-dev/taut/src/taut/gen/{java,java_metadata,java_runtime,kotlin,kotlin_metadata,kotlin_runtime,kotlin_package,scaffold}.py`.
- `D:/projects/limbo/taut-dev/taut/src/taut/{cli.py,corpus/parity_java.py}` and `D:/projects/limbo/taut-dev/taut/pyproject.toml`.
- Both canonical codec changes, all Java validation/descriptor classes, and both Kotlin foundation files.
- Both complete feature-test files, compiler-wheel test, changed existing regressions, and validation-mode goldens.

Retraced actual Python `validation.py`, `descriptors.py`, `rules.py`, and `facts.py`; Rust metadata/runtime/validation references; accepted physical-path/lock/application helpers; and the shape repositories’ committed foundation integration boundaries.

### Executed checks

All reviewer-generated files stayed under:

`D:/projects/limbo/toolchain-readiness-2026-11-02/jvm-review-scratch/code`

Used the prescribed toolchain activation, Python 3.11, snapshot `PYTHONPATH`, disabled bytecode/plugin/cache writes, UTF-8 settings, and scratch TEMP/TMP.

| Check | Result |
| --- | --- |
| Both complete JVM feature files, `pytest -q -p no:cacheprovider --basetemp …/code/pytest` | **144 passed in 401.90s** |
| Compiler-wheel, scaffold, and CLI files, same isolation with separate basetemp | **14 passed in 28.26s** |
| Independent first-day matrix: Java/Kotlin × source/package/supplied × validation off/on | All 12 generated, compiled, and ran successfully; source cleanup transitions passed |
| Independent Java declaration-order compatibility reproducer | Both compilation steps passed; execution failed with imported-message-facts mismatch |
| Independent Java signed-i64 OneOf reproducer | Generation accepted; `javac --release 8` failed on enum literals |
| Physical identity probes across Java/Kotlin/Rust planners | Equivalent `..` roots/users and safe extended namespaces retained identity; ambiguous components and obstructions rejected |
| Actual Windows junction probes | All three planners and common application preflight rejected traversal; target sentinel preserved |
| Common physical-overlap probe | Rejected before writing either conflicting target |

The initial feature invocation encountered an absent scratch-parent directory before target fixtures could run. After creating that expressly authorized scratch directory, the complete invocation above passed. That setup failure is not attributed to the product.

### Completed global gate

Consumed the completed sole watcher evidence, including:

- [Global results](D:/projects/limbo/jvm-oneof-scratch/global-gate-r0/global-results.json).
- [Codec parity log](D:/projects/limbo/jvm-oneof-scratch/global-gate-r0/codec-parity.log) and its JSON result.
- [Broad regression log](D:/projects/limbo/jvm-oneof-scratch/global-gate-r0/broad-regression-tests.log).
- [Baseline source proof](D:/projects/limbo/jvm-oneof-scratch/global-gate-r0/baseline-source-proof.json).
- The watcher script, before/after tuple records, and both 207-entry source inventories.

All 16 codec variants were GREEN with `require_all=True`, `jobs=2`, no unavailable target, no failing case, and no governance violation.

The broad run completed with **1620 passed, 3 failed, 4 skipped, 8 deselected in 797.86s**. Its exit code was correctly 1. The three failures were precisely the missing historical document and two Windows Go gofmt/CRLF failures. The baseline proof establishes unchanged relevant source blobs from `2cfee5d6156b0179066dc4eed70f60cde489a422`, and the document is absent in both revisions. `new_failures=[]`; source and tuple inventories were unchanged. The baseline-aware watcher exited successfully.

These runs overlap; their counts are not added together.

## Problem, requirement provenance, and scope

The authorized outcome is the next backend pair for the accepted native OneOf/mandatory-descriptor/explicit-validation proposal. Java and Kotlin previously lacked the mandatory immutable descriptors, typed attachments, optional instance operations, shared semantic engines, concrete foundation distributions, and ownership lifecycle needed by that proposal.

The authority explicitly permits each target’s runtime/emitter/tests/examples, local foundation compilation and provenance, and the shared CLI/scaffold/package-resource changes. The inspected component changes remain within those boundaries. Python/Rust/core/shape sources are references; user-owned Enum.case work and the disclosed Python generated/wheel noise remain excluded.

No new dependency, registry installation, Gradle/Android infrastructure, fabricated shape repository, or public Java multi-file projection was necessary. Existing standalone JVM routes demonstrably compile and execute the foundations and generated consumers. Java’s additional `--release 8` compatibility is implemented through localized syntax/collection substitutions and exercised by retained codec gates.

The chosen foundations address the observed gap through the existing compiler route. Typed callbacks and canonical runtime sources are sufficient; reflection, common message inheritance, and application-time compiler or delivery engines are unnecessary.

P2-1 concerns newly introduced compatibility checking. P2-2 is inherited literal-generation behavior, verified in the baseline, but now demonstrably blocks valid native enum discriminators in the required OneOf backend. It needs a localized emitter correction, not broader infrastructure work. Neither finding authorizes changes to another backend or the user’s authoring patch.

The historical missing-document and Go formatting failures are separate baseline shortcomings and do not independently block this pair.

## 1. Findings

### [P2-1] Java dependency fingerprints reject equivalent field declarations

**Location:** [java_metadata.py:33](D:/projects/limbo/taut-dev/taut/src/taut/gen/java_metadata.py:33), and its message fingerprint emission/comparison at lines 168 and 184.

**Violated invariant:** Independently generated compatible children must compose using their normalized portable facts. Descriptor fields are explicitly ordered by field number. Declaration order is not a different native field contract.

`fingerprint()` sorts JSON object keys but leaves the message’s `fields` list and field `cases` lists in author declaration order. The descriptor emitter separately sorts fields by tag. Consequently, two inputs can publish the same ordered descriptor facts and compatible native types while receiving different fingerprints.

**Executed reproduction:** Under `…/code/declaration-order`:

1. Built the canonical foundation jar.
2. Generated and separately compiled this disabled child:

   ```python
   child = schema(
       Child=Msg(second=F(2, INT), first=F(1, INT))
   )
   ```

3. Constructed the parent input with the identical child fields reversed to field-number order, plus `Parent.child: Ref("Child")`.
4. Generated the enabled parent with the complete explicit Java external binding for `Child`, then separately compiled it against the child and same foundation.
5. Ran a harness constructing `Parent` and `Child` and calling `p.isValid()`.

Both `javac --release 8` compilations returned 0. Execution returned 1:

```text
Exception in thread "main" java.lang.ExceptionInInitializerError
Caused by: taut.validation.ConfigurationException:
Child: imported message facts mismatch;
regenerate/rebind the compatible foundation and schema artifacts
```

The concrete generation and build sequence was:

```python
emit(child, p / "child", langs=["java"], services=[],
     runtime_mode="package", schema_identity="child")

emit(parent, p / "parent", langs=["java"], services=[],
     runtime_mode="package", validation=True,
     java_external_types={
         "Child": {
             "type": "taut.Child",
             "owner": OWNER,
             "descriptor_contract": 1,
             "codec_contract": 1,
             "capabilities": sorted(CAPABILITIES),
         }
     },
     schema_identity="parent")
```

The harness was:

```java
package taut;
public class Order {
    public static void main(String[] args) {
        Parent p = new Parent();
        p.child = new Child();
        System.out.println(p.isValid());
    }
}
```

**Impact:** A parent cannot use an otherwise compatible, independently compiled child when its complete dependency facts have been serialized or assembled in a different declaration order. Regeneration/rebinding guidance cannot resolve the underlying semantic false mismatch reliably. This also affects mandatory descriptor publication independently of validation.

**Required correction:** Canonicalize the portable per-type facts before hashing, including fields by tag and semantically unordered Case nominations. Preserve checks for actual field, rule, option, reservation, and effective-codec differences. The Rust portable fingerprint routine already demonstrates localized normalization.

**Closure test:** Separately compile a disabled child and enabled parent with reordered equivalent field declarations and Case nominations. Assert descriptor publication, recursive validation, and codec composition succeed. Retain negative tests for genuinely changed fields, rules, reservations, and inherited decode options. Exercise source/package composition without regenerating the child.

### [P2-2] Java cannot compile valid OneOf enums outside the signed-int literal range

**Location:** [java.py:142](D:/projects/limbo/taut-dev/taut/src/taut/gen/java.py:142), `_emit_enum()`.

**Violated invariant:** The new native OneOf route must support accepted enum wire numbers and preserve native enum/codec semantics. The enum’s native storage and descriptors use `long`, but generated constructor arguments use unsuffixed decimal literals.

**Executed reproduction:** Under `…/code/i64-enum`:

```python
e = Enum("Tag", low=-(1 << 63), high=(1 << 63) - 1)
s = schema(
    e,
    Record=Msg(
        kind=F(1, OneOf(e)),
        text=F(2, STR, Case(kind=e.high)),
    ),
)
emit(s, p, langs=["java"], services=[],
     runtime_mode="source", validation=True)
```

Generation accepted the schema. Compiling all emitted sources with:

```text
javac --release 8 -encoding UTF-8 -d <scratch>/classes <all emitted .java files>
```

returned 1:

```text
api.java:6: error: integer number too large
    LOW(-9223372036854775808), HIGH(9223372036854775807);
         ^
api.java:6: error: integer number too large
    LOW(-9223372036854775808), HIGH(9223372036854775807);
                                    ^
```

This occurs because Java does not infer a decimal literal’s type from the receiving `long` parameter. The failure starts outside the signed-int literal range, not only at i64 extrema.

**Baseline distinction:** Inspection of `1607b6e0…:src/taut/gen/java.py` confirms unsuffixed enum arguments were inherited. This is not claimed as a newly introduced regression. It blocks the current deliverable because the accepted new OneOf schema above cannot produce a usable Java program; no Java discriminator-range restriction was authorized. Kotlin’s executable i64-enum coverage passes.

**Required correction:** Emit valid long literals for enum constructor arguments, including both signed-i64 extrema. Keep wire numbers and descriptor facts unchanged.

**Closure test:** Generate, compile, and run OneOf messages using values just outside signed-int bounds and both signed-i64 extrema. Verify enum decode/encode, payload selection, descriptor numbers, and fast/report equivalence in source and package distributions and both validation modes.

### [P3-1] JVM options are exposed through incomplete help and unstated defaults

**Location:** [cli.py:169](D:/projects/limbo/taut-dev/taut/src/taut/cli.py:169), especially lines 169–179; [kotlin_package.py:55](D:/projects/limbo/taut-dev/taut/src/taut/gen/kotlin_package.py:55).

**Violated invariant:** The shipped interface must identify supported targets, actual method spellings, configuration input shape, and option defaults without requiring implementation knowledge.

The cold `gen --help` still describes `--with-validation` as emitting `validate/is_valid` on “every Python/Rust message.” The flag now enables Java and Kotlin operations named `validate` and `isValid`. The binding description similarly supplies only Python/Rust keys and defaults.

The newly introduced external-type flags use metavar `JSON` without saying that the argument is a JSON **file path**, or stating the omitted default. The new Kotlin package helper prints `--without-validation` with no description or stated default.

**Reproduction:** Run snapshot:

```text
python -m taut.cli gen --help
python -m taut.gen.kotlin_package --help
```

The output contains the descriptions above.

**Impact:** A first-day JVM user must guess whether validation is supported, which method names appear, whether JSON is inline or file-backed, and which package closure is built by default. This is correctable documentation and does not require an option-name compatibility break.

**Required correction:** Update the help for all four supported validation targets, camelCase JVM operations, JSON-file inputs, relevant JVM binding keys/defaults, omitted external mappings, and the package helper’s default validation behavior.

**Closure test:** Assert the relevant help output describes Java/Kotlin support, JVM method spellings, file-backed JSON inputs, and defaults; follow those commands against fresh output roots.

## 2. Invariant analysis

### Mandatory metadata and typed traversal

Both emitters produce mandatory message descriptors with validation disabled. Enabled methods delegate to a shared engine. Descriptor/report storage uses defensive snapshots and immutable public access.

Java’s generated field bindings directly read typed fields; Kotlin supplies typed binding callbacks and foundation-created bound records. Neither implementation relies on reflective field access, a generated common message base, or per-live-field descriptor wrappers.

Recursive links are stable/lazy. Executable descriptor-only tests passed with the validation engine absent. Wrong typed pairs fail compilation; missing old child accessors fail actual target builds. Actual inconsistent child facts and substituted runtime/codec artifacts are rejected. P2-1 identifies the false-rejection boundary still present in Java.

### Engine semantics

Inspection and executed behavioral/reference cases supported:

- Local scope checks root groups without descendant traversal.
- Recursive scope reaches populated ordinary and nonselected payload children.
- Invalid discriminators skip dependent selection checks while independent groups and children continue.
- False, zero, empty text, and empty collections count as present.
- Payload-free choices and exhaustive/virtual combinations behave as specified.
- Virtual selection produces deferred/incomplete results while supported children remain active.
- Field/group ordering, list indices, canonical CBOR map-key ordering, and original schema path names are retained.
- Shared children report at each path; active-ancestor cycles diagnose without a global visited suppression.
- Fast results equal report validity and completeness; fast sinks do not construct full reports/issues/deferred records.
- Reports remain snapshots after input repair, and invalid drafts remain mutable and structurally encodable.

P2-2 is a generation boundary that prevents these semantics from being usable for some accepted Java enum values.

### Foundation identity, package closure, and compatibility

Both source and package routes derive from canonical sources. The real compiler-wheel test passed for the nested Java and Kotlin resource inventories and compiled/executed consumers generated from the unpacked wheel.

Independent enabled-parent/disabled-child cases passed across source/package combinations. Child optional methods are not traversal dependencies. Codec, descriptor, issue, and report identity checks use actual shared native types. Compatible unequal build labels passed; actual incompatible substitutions failed.

Application execution used the JVM, generated classes, selected foundation, and Kotlin standard library where applicable. It required no Python compiler, authoring loader, shape/delivery engine, Gradle, reflection library, or package installation.

### Ownership and historical-root retrace

Both target planners use the accepted common locking/application path. Independent probes verified:

- Equivalent `..` spellings normalize to one root/user identity without dropping another active user.
- Safe `\\?\` drive paths retain physical identity.
- Ambiguous namespace components fail before mutation.
- Parent obstructions fail closed.
- Actual directory junctions are rejected before lexical evidence is normalized away.
- Physically overlapping output targets fail before writes.
- Modified/unknown outputs, shared users, validation transitions, and source/package transitions passed the feature tests.

Creating directory symlinks was unavailable under the Windows token (`WinError 1314`); an actual junction fixture was then created and tested successfully. Its target remained unchanged.

### Surface

Generation belongs under the existing `gen` family. The mode names and source alias remain coherent, validation remains independently opt-in, and conflicting runtime flags fail before writes.

The scripted walkthrough used the snapshot example schema and this command shape for each language:

```text
python -m taut.cli gen <snapshot-example.taut.py> -o <fresh-scratch-output>
    -l java|kotlin --api-only
    [--runtime source|package] [--with-validation]
```

Omission exercised supplied-runtime mode. Java applications compiled with `javac --release 8`; Kotlin applications compiled at JVM target 1.8. Each queried mandatory descriptors and, when enabled, invoked `isValid()`. All 12 combinations ran successfully using the selected canonical foundation. Regeneration from source to package removed owned runtime sources, and temporary walkthrough directories were cleaned.

The cold walkthrough required information beyond help for local Java foundation construction, JVM bindings/classpaths, and cleanup transitions. The example integration pages supply most of that context, but the help omissions and missing defaults are recorded in P3-1. No install/uninstall lifecycle is introduced: registry installation/publication is explicitly deferred, and the exercised package is a local artifact.

Java’s package-private messages and same-package usage are clearly documented and explicitly authorized. Kotlin’s companion methods and schema-derived JVM facade names compiled across independent schemas. No additional visibility or facade defect was reproduced.

## 3. Risks and next action

The completed broad/parity gates establish substantial retained behavior, but neither includes the two independent Java counterexamples above. Passing those gates therefore does not close P2-1 or P2-2.

No additional Kotlin implementation blocker was reproduced. Runtime execution was tested on JDK17; Java8 compatibility here means `--release 8` compilation, not execution on a separately tested Java8 JVM.

The next action is one bounded remediation patch addressing P2-1 and P2-2, with their stated regression cases, followed by originating/same-axis verification under the review-loop process. P3-1 can be corrected in that patch. Preserve the user’s Enum.case work and keep publication and other backends outside this remediation.
