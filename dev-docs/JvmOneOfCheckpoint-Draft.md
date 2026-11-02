# Java/Kotlin OneOf checkpoint — controlling DRAFT

Status: **pair source frozen for one committed Java/Kotlin acceptance review**.
Both executors reported REVIEW-READY; the coordinator explicitly authorized the
precise allowlist and scoped LOCAL GWZ checkpoint on 2 November 2026. Production
edits are on HOLD. The settled source revision is the commit containing this
DRAFT; generated reviewer prompts name its exact SHA and full diff range. No
review acceptance or push/tag/release/publication is claimed. Exactly two
peer-blind reviewers will review this same pair, Code+Surface and State.

The controlling authority is
[JvmOneOfCheckpoint-Authority.md](JvmOneOfCheckpoint-Authority.md). This DRAFT
records the implementation remedy and evidence, not new product requirements.
The review tier is dual: the pair changes generated APIs, compiler flags,
shared nominal runtime contracts and durable output ownership. Review is one
pair-wide Code+Surface axis and one pair-wide State axis, peer-blind.

## Observed problem and required behavior

The accepted Python/Rust baseline already has native OneOf/Case authoring,
normalized rules, versioned native IR, immutable emitted facts and common
preflight/application helpers. Java and Kotlin lacked mandatory descriptors,
typed runtime adapters and the explicit validation instance surface; their
legacy runtime resource copying also lacked the new ownership lifecycle.
The pair extends the existing emit/compiler route and derives source/package
foundation deliveries from each language's canonical low-level implementation.

Every message publishes metadata with validation off or on. Enabled methods
are thin calls to one language runtime engine, including no-rule and virtual-only
messages. Non-null presence includes false, zero, empty text and collections.
Invalid drafts remain mutable and structurally encodable; constructors, setters
and codecs do not run validators. Local scope checks root groups only. Recursive
scope follows all populated owned paths, including extra nonselected payloads;
wrong/missing tags suppress only dependent selection checks. Virtual groups are
explicitly deferred/incomplete and supported children still run. Reports own
snapshots; Boolean success requires valid AND complete and uses the same
predicates without constructing full report/issue/deferred objects.

Original schema names, field-number/group/child order, list indices and unsigned
canonical Taut CBOR map-key byte order remain observable. Shared children report
per path; only active-ancestor cycles diagnose ownership cycles. Unsupported
configuration, old/mismatched artifact contracts and missing descriptor/codec
capabilities fail distinctly before usable validation. No native JSON route
exists for these two existing standalone backends; no reflective serializer is
added. Existing shared compiler JSON conversion remains the sparse-oneof route.

## Concrete design and bindings

Java uses immutable public final descriptor/report classes in
`taut.validation[.descriptors]`. Private final fields and defensive snapshots
protect collections and portable metadata. `MessageAdapter<T>` pairs a checked
Class<T> attachment and MessageDescriptor with static `FieldBinding<T,V>` direct
field lambdas and typed ValueAdapter<V> operations. Stable lazy links support
recursive schemas; a per-schema SchemaBinding validates publication links.
Class tokens perform ordinary type checks only. No reflective field access,
mandatory message base/interface or per-live-field metadata wrapper is used.
Java keeps package-private messages in package `taut` and the exact four public
validation overloads, plus mandatory public static descriptor().

Kotlin uses companion descriptor/binding publication and static direct typed
callbacks, separate immutable portable facts and typed value attachments, lazy
recursive links and one shared engine. Its exact final ABI/binding evidence is
in the companion's INTEGRATION/RESULTS documents. Schema-derived
@file:kotlin.jvm.JvmName facades let separately generated api.kt units coexist.
Runtime-read immutable codec/owner/fingerprint values preserve compatibility
checks across separately compiled jar substitutions. Both languages retain original schema names in diagnostics
and record actual target field-access identities; native projection collisions
are errors. Java fields and methods can legally share descriptor/validate/isValid
spellings. Kotlin's true Enum/native symbol collisions remain target-specific.

The internal owners are `taut.java.foundation` and `taut.kotlin.foundation`, with
descriptor=1, codec=1, IR1–3 and descriptors.v1/codec.v1/oneof.v1 capabilities.
Internal `*-oneof-reference.1` build labels are not registry names or released
versions. Compatible unequal labels are accepted by contracts. Java and Kotlin
are separate targets; identical package spellings do not make the implementations
binary interchangeable. Independently generated schemas resolve one actual
foundation identity per language. Optional child methods are never a recursive
traversal dependency; full external native facts and explicit type mappings
avoid dependency regeneration or duplicate message/enum declarations.

`--runtime source|package` and `--with-runtime` source alias stay independent of
`--with-validation`; omission preserves application-supplied mode. Differing or
conflicting modes fail before writes. Keyword-only emit/emit_all forward modes,
validation, target bindings and external type mappings. Source roots are explicit;
package consumers put the selected compatible foundation on the compiler/JVM
classpath. There is no installation, package discovery, fallback or silent
upgrade. The local artifact helpers compile canonical foundation-only sources,
record content provenance and exercise actual compilation/execution.

Complete source/schema plans pass through accepted output locks and physical
application guards. Positive manifests record owner, contracts, provenance,
content hashes and canonical schema-user identities. Unknown, modified,
handwritten, incompatible, obstructed, reparse and ambiguous namespace paths
are refused. Source/package and validation transitions preserve another
identified user's required foundation/engine; unowned content is never adopted
or deleted. The State reviewer must independently attack these shared seams,
including prior Rust root-alias and Windows namespace failures.

## Requirements versus implementation choices

Mandatory metadata, opt-in instance validation, shared engines/reports,
source/package/supplied delivery, single actual runtime ownership, explicit
external dependencies, immutable snapshots, semantic parity, safe preflight and
retained codecs are operator requirements. Java package-private visibility and
the existing standalone Kotlin route are explicit scope constraints.

The concrete generic adapter shapes, source-file layout, local jar helper
interfaces and internal build labels are implementation choices selected to
meet those requirements. Java8 compatibility is a demonstrated localized
additional capability; the old runtime did use newer syntax. No infrastructure
change, new dependency/toolchain or fabricated library repository was required.
The probes/gates support these choices; they do not create additional authority.

## Evidence and current limits

Java's main final target/CLI/wheel gate reported **117 passed**, including both
Java codec parity variants. Eight later contract-only cases passed separately;
no production code changed after that main gate. The current Java feature file
has 88 cases. Python/Rust/reference and reserved-name preservation reported
**591 passed**. Exact commands and logs are in
[Java RESULTS](examples/java-oneof/RESULTS.md). These counts are distinct runs,
not one cumulative test total or a full-repository claim.

The real local compiler-wheel gate checks every Java/Kotlin canonical resource
against the built wheel, imports the unpacked wheel in isolation, generates
both targets, then compiles and runs the resulting source programs. Java's
complete foundation/API compiles with --release8 and runs on JDK17. The actual
source/package Java report corpus matches the Python reference's normalized
codes/rules/paths/deferred/validity/completeness/scope. Separate compilation
proves enabled-parent/disabled-child traversal and nominal runtime identity in
both source/package directions. Actual post-compilation child/runtime/codec
replacement is rejected; an unequal compatible build label links. Descriptor
and typed-adapter probes run with the engine absent.

Kotlin's final combined gate reported **74 passed** in 362.71 seconds: 55
feature tests and all 19 existing regressions including both codec parity/fuzz
variants. One subsequently added mode/provenance golden passed in 0.43 seconds,
with production unchanged: **75 distinct Kotlin tests** across those runs.
Core/Python/scaffold/options/IR/CLI preservation reported **788 passed**. See
[Kotlin RESULTS](examples/kotlin-oneof/RESULTS.md) and its saved test-results.txt.
Kotlin compares 160 scalar/tag/presence cases and 12 recursive/local/virtual/
cycle/list/map reports with the actual Python reference. Source/source
three-schema/facade, package/package and mixed independently compiled disabled
child composition prove shared nominal identity. Actual child/codec jar swaps,
inherited decode-option fingerprints, schema-derived JVM facades, and compatible
unequal labels are executable gates. Kotlin1.9 and2.4 compile/run its JVM1.8
example on JDK17 without a baseline upgrade. Source/package examples match.
The final-current-pair compiler-wheel check is recorded in
[WheelGate](JvmOneOfCheckpoint-WheelGate.log); it verifies the exact nested
resource payload and wheel-generated Java/Kotlin source compilation/execution.

The established broad-suite baseline has three unrelated failures: the absent
old `dev-docs/TautProtoApiSurfaceExtensions.md` test and two Windows Go CRLF/
gofmt tests. Reference evidence is the accepted Python baseline-evidence JSON
and Rust broad-regression log (3 failed/1473 passed/4 skipped/8 deselected).
They are disclosed baselines, not waived new regressions. Reviewers must trace
any observed failure to actual current/baseline evidence and must not weaken tests.

No Java/Kotlin shape-library repo exists in this checkout. General public
multi-file Java schemas and native JSON serializers remain outside this pair.
The user-owned Enum.case authoring change remains parallel work outside the
pair allowlist. It is not yet present at this freeze; the coordinator explicitly
authorized reviewing the pair without waiting for it. Accepted native
EnumMemberRef facts remain the semantic input. Preserve and separately integrate/
test the user's patch when it arrives; do not freeze the old Python reservation
policy as a permanent language-independent restriction.

## Settled object and review workflow

[Preparation inventory](JvmOneOfCheckpoint-Preparation.json) is the historical
pre-freeze observation. [Final inventory](JvmOneOfCheckpoint-Inventory.json)
records the authorized exact allowlist, baseline, monitored user-source hashes,
production/evidence hashes and excluded noise at the freeze. Its own hash is
intentionally excluded to avoid a self-reference. The reviewed source revision
is the commit containing that inventory and this DRAFT; exact committed tuple
and full baseline-to-source range are recorded in both canonical-template
reviewer prompts after the scoped GWZ checkpoint/receipt.

Baseline: workspacef703be38, Taut1607b6e0, shape-Pythonc08c2a1b and
shape-Rust8e92b89e. No user-owned authoring/facts/tests are part of the allowlist.
Pre-stage verification requires the monitored sources to retain their recorded
hashes, an empty prior index, and all tracked changes to belong to the precise
pair allowlist. Index contents and hashes must match that list before commit.
Old Python generated bundles/wheels, temporary archives/classes/jars/builds/
scratch, and unrelated/user-owned modifications stay excluded and untouched.

The coordinator authorized this local checkpoint and any GWZ-managed local
receipt required to settle the tuple. After it, the coordinator assigns Kotlin
ONE broad-suite plus all16 codec-parity integration run against those source
bytes; the lane owner does not duplicate that global gate. Both independent
reviewers must consume the completed global results before final verdicts.
They receive the same full pair diff, DRAFT, authority, relevant reference source,
both languages' evidence and baseline failures. Code reads Surface cold first;
State independently attacks both targets and the shared durable-state boundary.
No reviewer's current-round findings or implementer suspicions are shown to the
other. Prior-root retraces and all regression/closure duties live within these
two mandates, never a supplementary reviewer.

File complete reports verbatim and merge GO/NO-GO on the exact tuple. Any
blocking finding gets a disposition and closure test in one merged remediation
plan/patch. Kotlin owns Kotlin corrections; Java owns Java/shared corrections;
the coordinator coordinates refreezing. Originating/same-axis reviewers must
verify their original counterexamples; implementers do not self-close findings.
Use the skill's at-most-two-remediation cap and material-change reviewer
replacement rules. No push, tag, release, registry publication or other backend
is authorized by a local checkpoint or a GO verdict.
