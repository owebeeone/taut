# Kotlin descriptors and explicit validation

Internal build `kotlin-oneof-reference.1`, descriptor/codec contract 1, native IR
versions 1–3. This is a local foundation build, not a published Maven coordinate.
Kotlin keeps the existing `package taut` messages, mutable properties, constructor
defaults, CBOR structural checks, dense nullable slots, and JVM 1.8 target. The
existing standalone Kotlin route has no native JSON codec; none is added here.
No Gradle, Android SDK, emulator, reflection, kotlin-reflect, KSP, common message
base, delivery engine, or compiler library is needed by the resulting application.

Every message publishes `Message.descriptor()` and typed `Message.tautBinding()`
in its companion, even when validation is off. `--with-validation` adds
`validate(recursive: Boolean = true)` and `isValid(recursive: Boolean = true)`
instance methods on every message. Reports are immutable shared runtime types in
`taut.validation`; metadata types are in `taut.validation.descriptors`. `isValid`
requires both an issue-free and a complete report. Virtual selection is deferred;
supported child validation continues. Invalid mutable drafts remain encodable.

Canonical codec/extension sources are `runtime/cbor.kt` and `runtime/ext.kt`;
descriptors and engine are `runtime/kotlin/{descriptors,validation}.kt`. The
package builder and source emitter consume these exact files. Validation-off
source/package closure omits the engine and report definitions. Build provenance
records content hashes inside `META-INF/taut-kotlin-foundation.json` in the jar.

From the saved Windows project, using a fresh output directory:

```powershell
. D:\projects\limbo\toolchain-readiness-2026-11-02\Activate-TautToolchains.ps1
$env:PYTHONPATH='D:\projects\limbo\taut-dev\taut\src'
python D:\projects\limbo\taut-dev\taut\dev-docs\examples\kotlin-oneof\run-example.py --out D:\projects\limbo\toolchain-readiness-2026-11-02\kotlin-example
```

The runner generates through normal `emit`, builds the local jar from canonical
sources, compiles JVM1.8 programs for both distributions, executes both, compares
results, and writes `results.json`. Application execution uses only the JVM,
Kotlin standard library bundled by `-include-runtime`, the generated schema, and
the selected foundation. Python and Taut C are build tools only.

To build the package alone:

```powershell
python -m taut.gen.kotlin_package D:\local-build\kotlin-foundation
# Add --without-validation for a descriptor/codec-only jar.
```

Use `--runtime source` (or its `--with-runtime` alias) for source; use
`--runtime package` to emit references and explicitly put the jar on the compiler
and JVM classpath. Omission keeps application-supplied runtime mode. Generation
does not install or discover packages. Repeated differing modes fail before
writes. `--runtime-bindings JSON` accepts a `kotlin` object with `owner`
(`taut.kotlin.foundation`), optional absolute `source_root`,
`descriptor_contract: 1`, `codec_contract: 1`, and capabilities
`["codec.v1", "descriptors.v1", "oneof.v1"]`. Packages are deliberately fixed;
source/package schemas share one actual JVM type owner. Do not compile another
private copy into a schema or a library. Java and Kotlin foundations are distinct
targets and cannot be combined by treating their package names as compatibility.

For independent dependencies, compose the complete child schema facts into the
parent input and pass `--kotlin-external-types JSON` (programmatic
`kotlin_external_types={"Child": "taut.Child", "ChildKind": "taut.ChildKind"}`).
The map names actual already generated classes; parent emission omits their
declarations. The child jar, parent, and foundation must be on one classpath.
Disabled child validation methods are not required. Public mandatory bindings,
codec contracts, owner and per-type fact fingerprints reject old/incompatible
children before usable validation. Different compatible build labels are allowed.
Missing jars/exports fail the target build; no dependency regeneration occurs.
Only the existing Kotlin schema package projection is generated; arbitrary
application classes are not inferred or scanned for adapters.

Kotlin keywords retain backtick access names in metadata and original names in
reports; keyword type names are escaped too. Schema exports use unique JVM file
facades so independently generated `api.kt` files can coexist. Actual generated API and native enum collisions are rejected before
writes. For example Kotlin Enum.name/ordinal and generated descriptor/tautBinding
symbols cannot be enum entries; this is independent of Python's authoring access
syntax. Ordinary names such as `metadata` and leading double underscores do not
inherit Python-specific restrictions.

Source ownership uses the accepted physical-path guards, hashes, lock/application
helpers, and separate schema/runtime manifests. Modified, unknown, handwritten,
incompatible, reparse, ambiguous Windows namespace and overlapping outputs fail
preflight. Shared users preserve the engine needed by another schema across
validation and source/package transitions; no adoption or silent upgrade occurs.

Executable coverage lives in `src/tests/test_kotlin_oneof.py` and the existing
`test_kotlin.py`/parity corpus. The feature corpus checks normalized Python report
parity, source/package/supplied routes, absent engine, independently built child
identity, cycles and per-path sharing, ordering and canonical map keys, immutable
snapshots, direct primitive reads, descriptor inventory, contracts, names, CLI,
and output transitions. See `RESULTS.md` for the final actual run, not this design
description, before treating the backend as reviewed.
