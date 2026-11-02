# Java foundation and adapter contract

Java's supported generated surface remains one package-private `api.java` in
package `taut`. Every message publishes public static `descriptor()`, whether
validation is enabled or disabled. Enabled messages add the four required
public instance overloads. Fields and methods may legally share names in Java;
`descriptor`, `validate`, and `isValid` fields therefore remain accepted. Java
keywords receive a trailing underscore, recorded in FieldDescriptor.attribute().
Uppercase enum projection is retained and actual projection collisions fail
before writes. Reports retain original schema field/member names.

The internal build label is `java-oneof-reference.1`; foundation owner is
`taut.java.foundation`; descriptor and codec contracts are 1, portable IR versions
1–3 are accepted, and capabilities are descriptors.v1/codec.v1/oneof.v1. This is
not a registry name, released version, or Maven coordinate. Contract-compatible
package build labels may differ. Existing repository code used modern Java
syntax; this implementation additionally compiles its complete canonical
foundation and generated API with `javac --release 8`. The runtime switch rewrite
and emitted stream collection/list construction changes preserve codec behavior.
JDK17 is the tested execution toolchain. No Android SDK or hidden API is needed.

Shared public immutable classes live in `taut.validation` and
`taut.validation.descriptors`. Private final storage and defensive collection
snapshots keep metadata and reports independent of mutable input. Message,
enum, type, field, constraint, oneof and schema records include the proposal's
full inventory. Stable supplier links represent recursive message/enum references.
A per-schema immutable registry checks all descriptor/adapter links before the
message descriptor accessor returns. External dependencies supply their own
mandatory metadata/typed adapters, regardless of optional validation methods.

The concrete adapter ABI was compiled against the canonical foundation before
integrating its Java emitter. `MessageAdapter<T>` pairs a Class<T> checked type
attachment and one immutable MessageDescriptor with static
`FieldBinding<T,V>` values. Each field binding owns a generated Function<T,V>
that directly reads the declared field, and a typed ValueAdapter<V> that reads
primitives/enums or traverses message/list/map values. Virtual field bindings
have no reader. `readValue`, `present`, and `enumName` expose typed operations;
`Traversal` is the engine-independent typed traversal SPI. Adapters never capture
a live instance or allocate a wrapper per live field. Class tokens perform only
ordinary runtime type checks; there is no reflection, annotation scanning,
MethodHandles, common generated superclass, or mandatory message interface.

`ValidationEngine` is the sole semantic engine. Its shared traversal/predicates
feed report or early-stop Boolean sinks; the Boolean sink does not instantiate
reports/issues/deferred records. Local scope runs root groups only. Recursive
scope walks every populated child path, including extra nonselected payloads,
and tracks active ancestors rather than globally suppressing shared children.
Maps use unsigned lexicographic canonical Taut CBOR key bytes and standard
padded base64 paths. Virtual groups emit deferred checks and keep supported
children active. Configuration failures throw ConfigurationException; data
issues remain immutable report values. Invalid drafts remain mutable and
structurally serializable; dense CBOR and ordinary nullable slots are preserved.
There is no existing Java native JSON route, and this change adds no reflective
serializer. Shared compiler JSON conversion already implements sparse oneof JSON.

Source mode uses the same canonical `runtime/Cbor.java`, `runtime/Ext.java`, and
`runtime/java/**/*.java` as the local package helper. The optional engine source
is `taut/validation/ValidationEngine.java`; descriptors/adapters work without it.
The low-level codec classes remain in package `taut`, so independent generated
units use the existing codec and KV identity through Java's same-package access.
No generated message visibility expansion or copied codec facade is necessary.
Normal applications require only this JDK foundation, with no Taut compiler,
authoring loader, shape engine, transport library, Gradle or registry dependency.

`runtime_bindings['java']` accepts `owner`, `module` (fixed `taut`),
`source_root`, `artifact`, `descriptor_contract`, `codec_contract`, `capabilities`.
`source_root` names the one shared source owner; consumers must generate that
owner first. `artifact` optionally supplies an explicit local foundation jar;
codegen verifies its contracts, content hashes, source inventory and exports
without executing it. Missing artifacts/exports fail generation or compilation;
there is no installation, discovery, fallback, private runtime copy, or upgrade.
`build_foundation(path, validation=True|False)` compiles only the canonical
foundation into a fresh local jar, records exact source and class content hashes,
and includes canonical source payloads for provenance. Both distributions resolve
the same package/class nominal identity. The caller puts exactly that selected
foundation directory/jar on the application classpath. Java/Kotlin foundations
are separate targets and are not binary-interchangeable implementations.

`java_external_types` / CLI `--java-external-types JSON` maps schema names to
objects with `type` (fixed `taut.Name`), `owner`, `descriptor_contract`,
`codec_contract`, and `capabilities`. The complete native dependency schema stays
in the IR. Mapped declarations are omitted, and generated adapters call the
child's descriptor/$adapter accessors. Compilation rejects old missing accessors;
publication checks fingerprints of expected immutable facts, catching a supplied
child with inconsistent fields/options/reservations/rules. No child regeneration
or copied native type occurs. Independent units can be compiled in separate
steps against the chosen foundation and then linked on one classpath.

Output handling follows the accepted Rust planner and common physical-path,
lock and apply guards, including Windows namespace/reparse/obstruction checks.
Schema and source-owner manifests carry provenance, exact hashes and absolute
canonical user identities. Complete preflight precedes mutation; transitions
preserve positively identified other users and refuse unknown/modified files.

Shared integration ownership: this executor owns scaffold.py, cli.py,
pyproject.toml runtime resource declarations, and the Java corpus source-file
inventory update. Kotlin-specific files are owned by the companion executor.
