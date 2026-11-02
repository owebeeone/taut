# Kotlin implementation evidence — 2 November 2026

Status: REVIEW-READY; Kotlin production edits are on HOLD for the coordinator's
combined Java/Kotlin freeze and independent review. No acceptance verdict, registry publication,
release, tag, commit or push is asserted by this record.

The controlling scope is the delegated Kotlin implementation of
`OneOf-ExplicitValidation-BuildProposal.md`, with the accepted Python/Rust
checkpoint as semantic baseline. Java owns shared CLI/scaffold/package-data
wiring; Kotlin has not edited those shared files or the user's Enum authoring
change. Kotlin does not reserve Python's metadata names as a general rule.
Kotlin's native Enum.name/ordinal collisions are separately diagnosed.

## Executed evidence

The final current-production-byte Kotlin gate passed **74 tests in 362.71
seconds**, covering 55 feature tests and all 19 existing Kotlin regressions.
The subsequently added mode/provenance golden test passed separately in 0.43
seconds: **75 distinct Kotlin tests passed** across those two runs. Production
bytes were unchanged between them. See `test-results.txt` for the saved output.

* Earlier full gate: 73 passed in 328.43 seconds. This includes the feature
  corpus plus all 19 existing Kotlin tests, including both parity variants,
  float, nullable/missing behavior, extension/residual/fuzz and map-key tests.
* Final source/source composition probe: 1 passed (three independently
  generated schemas, enabled parent/disabled child, one actual foundation,
  shared report/issue types and a library facade retaining descriptor/codec/
  report identity). Each generated `api.kt` has a unique schema-derived JVM
  file facade so their public schema exports coexist.
* Final binary-link/escaping edge probes: 3 passed. They actually compile and
  execute child/codec jar substitution, compatible unequal build labels,
  target escaping and signed i64 enum extrema.
* Final recursive-reference edge probes: 3 passed. They compare normalized
  recursive, local, virtual, cycle, list and canonical-key reports with Python;
  verify inherited decode-option mismatch rejection; and accept equivalent
  enum map declaration ordering.
* Mode/provenance golden probe: 1 passed in 0.43 seconds. Source/package/supplied
  APIs match for each validation mode. The only enabled-source deltas are the
  wrappers/import/engine check. Every emitted source byte and ownership hash
  matches the package builder's canonical source closure.
* Core/Python-reference regressions: 788 passed in 9.80 seconds, from
  `test_oneof.py`, `test_python_runtime_distribution.py`, `test_scaffold.py`,
  `test_reserved_names.py`, `test_options.py`, `test_options_validate.py`,
  `test_ir_v2.py` and `test_cli.py`.
* AdapterProbe.kt compiled and ran on Kotlin 2.4/JDK17 at JVM target 1.8 before
  production implementation. Direct primitive/enum reads, child pairing,
  presence and protected snapshots passed.
* The installed Kotlin 1.9 compiler compiled and ran the final source example
  at JVM target 1.8 on JDK17. Kotlin 2.4 compiled and executed both the source
  and local-package example routes. No new compiler/JVM baseline is required.

The feature tests compare 160 scalar/tag/presence report cases plus 12
recursive/local/virtual/cycle/list/map reports against the actual emitted Python
reference. They compare code, rule, complete path components, deferred reason,
validity, completeness and scope; wording is not a parity gate. Other executable
checks cover independent groups, nonselected populated children, exhaustive and
virtual combinations, Boolean short-circuit, immutable reports/options/registry
links, configurations, old children, typed-pair compilation errors, all message
methods, source ownership transitions and Windows namespace guards.

The existing golden assertions changed only to account for mandatory companion
metadata, to inspect the codec portion independently of metadata's own empty
collections, and to include the mandatory descriptor foundation in a direct
Kotlin compile. Existing decode-bound and codec behavior assertions remain.

## Runnable example and build closure

See README.md for commands and `results.json` for the actual source/package
output and canonical SHA-256 inventory. `run-example.py` uses normal `emit`,
builds a real local jar, compiles both applications, executes them, compares
outputs, and writes the receipt. Expected actual output is:

```text
oneof.payload_unexpected:text, oneof.payload_missing:number
repaired=true; snapshotIssues=2; virtualComplete=false
descriptor=kotlin-oneof-example.Content; fields=5
```

Runtime owner `taut.kotlin.foundation`; descriptor/codec/validation contracts 1;
internal build label `kotlin-oneof-reference.1`; native IR 1–3. Source and package
use the same canonical files:

| Emitted filename | Canonical source under src/taut/gen/runtime |
| --- | --- |
| cbor.kt | cbor.kt |
| ext.kt | ext.kt |
| descriptors.kt | kotlin/descriptors.kt |
| validation.kt | kotlin/validation.kt (only when needed) |

The package build target is `python -m taut.gen.kotlin_package OUTPUT`, producing
the local `taut-kotlin-foundation.jar` and a provenance record, with the same
record embedded at `META-INF/taut-kotlin-foundation.json`. The compiler and JVM
classpath explicitly bind the jar; generation never installs or discovers one.
This filename is not a registry coordinate. There is no new Kotlin library repo.

Runtime-read immutable compatibility/fingerprint values prevent JVM constant
inlining from bypassing checks when separately compiled jars are replaced.
Child fingerprints include effective decode options. The canonical codec owns
its own version/identity attachment. Checked generic bindings manufacture the
erased record pair inside the foundation; generated messages require no base.
Descriptors retain cached stable recursive links and immutable value tables.
The engine owns shared predicates and ancestor-path traversal; wrappers contain
no checking bodies. The Boolean sink constructs no report or diagnostic records.

## Kotlin-owned review allowlist

* `src/taut/gen/kotlin.py`
* `src/taut/gen/kotlin_metadata.py`
* `src/taut/gen/kotlin_runtime.py`
* `src/taut/gen/kotlin_package.py`
* `src/taut/gen/runtime/cbor.kt`
* `src/taut/gen/runtime/kotlin/descriptors.kt`
* `src/taut/gen/runtime/kotlin/validation.kt`
* `src/tests/test_kotlin.py`
* `src/tests/test_kotlin_oneof.py`
* `dev-docs/examples/kotlin-oneof/AdapterProbe.kt`
* `dev-docs/examples/kotlin-oneof/Example.kt`
* `dev-docs/examples/kotlin-oneof/INTEGRATION.md`
* `dev-docs/examples/kotlin-oneof/README.md`
* `dev-docs/examples/kotlin-oneof/RESULTS.md`
* `dev-docs/examples/kotlin-oneof/results.json`
* `dev-docs/examples/kotlin-oneof/run-example.py`
* `dev-docs/examples/kotlin-oneof/test-results.txt`

No Kotlin edits are authorized to shared scaffold/CLI/IR/ownership modules or
companion Java files. Those shared changes belong in Java's combined pair scope.

## Exact limitations

Kotlin has no existing native JSON serialization route; the implementation adds
none. Its existing dense CBOR and ordinary nullable policies are preserved.
Virtual oneof selection remains explicitly deferred/incomplete and is never
inferred from payloads. No higher-level Kotlin shape library exists in this
checkout; the facade test proves the re-export/alias boundary, not such a library.
The generated schema package remains the existing `taut` projection. External
maps name actual compatible generated owners, not arbitrary application objects.
There is no annotation scanning, KSP, reflection, kotlin-reflect dependency,
Gradle build, Android SDK/emulator run, package installation or publication.
