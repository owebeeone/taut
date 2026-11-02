# Kotlin integration contract (2 November 2026)

Kotlin executor owns `gen/kotlin.py`, `gen/kotlin_metadata.py`,
`gen/kotlin_runtime.py`, canonical `gen/runtime/kotlin/*.kt`,
`tests/test_kotlin_oneof.py`, and this example directory. Java executor owns
all shared scaffold/CLI wiring. No new registry package or release is selected.

Shared wiring needed:

* `kotlin.emit_types(schema, forward_compat=False, *, validation=False,
  external_types=None, identity=None)` (existing dispatcher may call directly).
* `emit`/`emit_all` keyword `kotlin_external_types=None`; name-to-qualified-Kotlin
  type mapping, forwarded to `external_types`. CLI equivalent if the shared CLI
  supports external type maps for Java/Kotlin.
* `kotlin_runtime.binding(runtime_bindings, directory, mode)` returns
  `(source_root: Path, consume_source: bool)` after complete binding checks.
* Collect API/client/server Kotlin text in a `kotlin_texts` mapping. Do not use
  legacy `_RUNTIMES` writes for Kotlin. Under the existing output locks call
  `kotlin_runtime.plan_outputs(directory, texts, *, mode, validation,
  source_root, consume_source=False, external=False)` returning `(writes, deletes)`.
  Use `.taut-kotlin-outputs.json` as previous-output metadata, lock selected and
  prior source roots, and reuse common `apply_outputs`. Kotlin planner reuses
  physical path/ownership guards from the accepted Python/Rust helper.
* Allow validation and source/package runtime selection for Kotlin; omission is
  supplied runtime. Runtime binding keys: `owner`, `source_root`,
  `descriptor_contract`, `codec_contract`, `capabilities`. Fixed canonical packages
  `taut`, `taut.validation`, `taut.validation.descriptors`; supplied/package
  consumers link these exact nominal types. Owner is `taut.kotlin.foundation`,
  descriptor/codec contract 1, capabilities `descriptors.v1`, `codec.v1`, `oneof.v1`.
  Source ownership is explicit, not dependency discovery. No Java nominal type
  interchange is claimed. Build label is internal `kotlin-oneof-reference.1`.

ABI probe: AdapterProbe.kt compiled using installed Kotlin 2.4, JVM target 1.8,
and ran on JDK17. It proves typed generic binding, direct borrowed String and
enum-wire reads, non-null presence, direct child pairing, copied/protected lists.
Production binding uses one static SchemaBinding<T> per generated message;
its bind(T) makes a typed bound record. Generated callbacks never capture a live
message; metadata never contains instance wrappers. Child callbacks call the
child's mandatory `tautBinding()` even when optional validation methods are off.
Descriptors use lazy stable accessors for recursive links. One shared engine
uses this ABI for full and Boolean traversal. Kotlin has no existing JSON route;
this implementation preserves its existing CBOR route and dense null slots.

Package proof will build a local foundation-only jar from the exact canonical
source inventory (no Gradle, SDK, compiler library or shape engine). This is a
local build/export binding, not a published Maven coordinate.
