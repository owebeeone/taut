# Oneof, descriptors and explicit validation — build proposal

Date: 2 November 2026. Status: runtime-distribution amendment consolidated;
amendment-wide acceptance is not claimed.
No production implementation, compatibility test or release is claimed here.

## 1. Authority, scope and precedence

The operator requests one implementation document for all nine supported languages,
with Python implemented first and the others following a common conformance corpus.
The operator subsequently selected mandatory descriptors, opt-in instance validation
methods, general-purpose shared reports, local/recursive modes, a Boolean fast path,
and versioned generation. This document records those latest decisions in one place.

The subsequent packaging decision supports BOTH source-only applications and use
through language-specific Taut packages. Sections 4, 6–9 now consolidate that
amendment: one canonical runtime implementation per language, explicit distribution
selection, and one shared runtime owner across schemas and Taut libraries. This is
newly consolidated text, not an assertion that an earlier review covered packaging.

The [behavioral proposal](OneOf-ExplicitValidation-PROPOSAL.md) supplies earlier
oneof semantics and historical probe evidence. The explicit supersessions below
control where later operator decisions differ. The earlier GO/GO review accepted
that earlier proposal only; it does not accept this build proposal or its amendments.

Authorized work for this task: consolidate and review documentation only. Editable:
this document and its review, draft-brief, remediation and verdict records. Production
Taut, probe source, generated code, GARNS resolver/parser and dependencies are
reference-only. No implementation, version bump, commit, push or release is authorized.

| Earlier design | Current operator-selected contract |
| --- | --- |
| Descriptors optional or absent | Every newly generated message publishes a descriptor. |
| Disabled generation identical to old compiler | Deliberate versioned migration adds descriptors/imports; attribute and review golden changes. |
| Per-type free/static validators | Instance methods with the same names on every message. |
| Methods only on constrained messages | With validation enabled, every message gets methods; unconstrained scope is a no-op. |
| Per-schema diagnostic types | Shared language-runtime report types, reusable across schemas/rule families. |
| Direct generated checking logic | Python uses descriptors, thin wrappers and a shared engine. |
| Shared base/interface for discovery | Not required; new artifacts promise the mandatory descriptor contract. |
| Runtime detection of old libraries | Old/mismatched artifacts are rejected explicitly; no silent fallback. |
| Standalone payload-free Case | Rejected; non-exhaustive unmatched enum choices are payload-free. |

Release numbering, descriptor ABI numeric version and target import/link bindings
are release/build configuration details to record before implementation is frozen,
not invented release numbers or permission to change infrastructure during review.

## 2. Public schema and generation behavior

```python
ContentKind = Enum("ContentKind", text=0, number=1, empty=2)
SCHEMA = schema(
    ContentKind,
    Content=Msg(
        kind=F(1, OneOf(ContentKind, virtual=False, exhaustive=False)),
        text=F(2, STR, Case(kind=ContentKind.text)),
        number=F(3, INT, Case(kind=ContentKind.number)),
        next_id=4,
    ),
)
```

Enum objects are referenceable; Case nominates its controlling field using the
keyword and a qualified enum member. There are no free-hanging Case declarations.
OneOf virtual and exhaustive are actual Booleans, both default False.

- Non-virtual discriminator: required stored enum field. Its selected payload must
  be present, all other group payloads absent. Payload slots remain independently
  mutable and nullable so drafts can be invalid during construction.
- Virtual discriminator: schema-only field, no instance/wire slot. Its fields and
  rules remain described. First-cut runtime selection/mutual-exclusion validation
  is explicitly deferred, not inferred from payloads or reported as passed.
- exhaustive=False: enum choices without a nominated payload are payload-free;
  selecting one requires all group payloads absent. exhaustive=True: every member
  must be nominated on a payload field or schema compilation fails.
- Wrong enum ownership, duplicate member ownership, unknown controlling fields,
  invalid schema types and empty enums are schema errors in either coverage mode.
  Several enum members may select one field, but a field cannot depend on several
  discriminators. Support multiple independent groups per record.

`tautc gen --with-validation` opts into the two instance methods and validation
engine wiring. Omission is off; programmatic emit gains keyword-only
`validation: bool = False`, forwarded by emit_all. Every mode emits mandatory
message/type descriptors and their accessors. Generation does not run validation.
Schema checking, IR rule retention and codec semantics do not depend on this flag.
Existing constructors/setters/encoders/decoders never call semantic validators.

With generation off, omit validate/is_valid methods and validation-only helpers,
but retain descriptors and descriptor-runtime imports. The descriptor runtime and
validation engine/report portions should be separable. With it on, emit methods
on every message, including messages with no constraints or only virtual groups.
Runtime distribution is independent: neither `--runtime source`, `--runtime package`
nor legacy `--with-runtime` enables validation. See section 7 for omission and
programmatic compatibility; validation off still needs the descriptor foundation.

Generate through the existing emit/compiler route, not a second compiler. New
schemas use a versioned native IR extension that preserves constraints and rejects
unsupported versions rather than discarding rules. No application-specific dictionary
or probe shim becomes the production semantic source.

### Presence and serialization

Presence means non-null, not truthiness. Zero, false, empty text and empty collections
are present. JSON omits absent oneof payloads and accepts missing or explicit null
payloads as absent. Non-virtual discriminator remains required. Ordinary nullable
JSON fields and dense CBOR retain their current policies. Primitive/enum/wire
structural checks remain in codecs.

For valid number content, JSON is {"kind":"number","number":"42"}; virtual
form is {"number":"42"}. The quoted number follows existing Taut i64 JSON mapping.
If several payloads are populated, serialize all of them. Never pick a winner,
repair an invalid draft or discard populated values based on the tag. Payload-free
choices emit no payload; missing selected payloads remain representable drafts.
No dynamic message factory, automatic reflective serialization or arbitrary-object
support is added.

## 3. Shared descriptor model

Each language runtime owns reusable descriptor classes/structs. Each generated
schema contributes immutable VALUES/tables, not bespoke descriptor type definitions.
One MessageDescriptor contains its FieldDescriptor sequence. Instances of a generated
message share that metadata; no descriptor graph is allocated per instance.

| Record | Required semantic content |
| --- | --- |
| MessageDescriptor | name, qualified_name, descriptor_contract_version, fields, oneofs, constraints, reserved_numbers, reserved_names, next_id, declared options, effective_options |
| FieldDescriptor | original name, generated access identity, field number, TypeDescriptor, presence, transient, virtual, declared options |
| EnumDescriptor | name, qualified_name, member names/numbers/options, declared options |
| OneOfDescriptor | controlling field, enum reference, virtual, exhaustive, complete normalized member-to-payload map; payload=None means implicit payload-free |
| ConstraintDescriptor | namespaced rule identifier and immutable parameters, for future non-oneof families |
| SchemaDescriptor | descriptor/IR versions, schema identity, immutable message/enum registries, declared/effective options |
| SchemaBinding | host-language typed access attachments; separate from portable schema facts |

Fields are ordered by schema field number; preserve original field names in reports.
Presence distinguishes required, nullable and missing_ok. Virtual/transient are
independent. A virtual discriminator retains a logical field descriptor but no value
accessor. Reserved numbers/names and next_id remain metadata, not live fields.
Descriptors include unconstrained and scalar fields, not just fields needed today.
RPC/service metadata remains in native IR; it is not needed by this record engine.

All sequences/maps/options are immutable snapshots; do not expose a mutable backing
container. Validate descriptor links and versions before publication. Derived field
lookups may be cached once in the immutable registry, never re-created per instance.

### TypeDescriptor is schema information, not necessarily a host type object

Use a discriminated kind with exactly its applicable data:

| Kind | Data |
| --- | --- |
| Int, String, Bool, Bytes, Float | Primitive tag with Taut semantics, e.g. signed i64 for Int. |
| Message | Reference/accessor to MessageDescriptor. |
| Enum | Reference/accessor to EnumDescriptor. |
| List | Element TypeDescriptor. |
| Map | Key and value TypeDescriptor. |

C++ primitive kinds are a fixed enum and map to fixed native storage, e.g. String
to std::string. Do not manufacture runtime C++ class objects or require RTTI.
Other languages preserve the same schema meaning even with different physical layouts.
Python class objects or Java Class<?> tokens may be optional host attachments if
useful, but the engine must not require them for all primitive/message kinds.

Portable IR stores qualified reference identities; publication links those once
to shared descriptors. Recursive schemas use stable links or lazy descriptor accessors,
not eagerly expanded nested descriptor copies. All references outlive their uses.
Dangling/wrong-category/version links are configuration failures, not successful
validation or silently absent children. Publication terminates on recursive schemas.

### Typed access without a common message base

Descriptors carry schema facts; generated adapters supply typed access to actual
values. Their required operations are presence, primitive/enum value reading and
owned child/list/map iteration. The adapter must pair a value with its correct
message descriptor and lifetime; do not permit an unchecked mismatched pair to
reach the engine. The concrete low-level adapter ABI is target-specific and must
be specified/probed before its backend implementation, not inferred from field offsets.

Python uses recorded generated attribute names and a frozen mapping from schema
names to real generated enum/message classes. C++ may use typed member pointers or
captureless lambdas in static tables/function pointers. Java/Kotlin use generated
typed accessors, not Field.get, MethodHandles, annotation scanning, KSP or reflection.
Accessors receive the current message; descriptors never capture live instances.
No generic heap wrapper object per live field is required. Space is the design
priority; this plan imposes no speed gate or speculative optimization prerequisite.

## 4. Descriptor publication and separate dependencies

Every new generated message has the mandatory versioned descriptor access contract.
There is no need to infer which random application classes have this capability:
Taut operates on schema-defined types. A base class/marker interface is not required.

| Target | Message descriptor publication | Representation |
| --- | --- | --- |
| Python | class ClassVar DESCRIPTOR | Frozen slotted runtime records; tuple fields; immutable mappings. |
| Rust | Content::descriptor() -> &'static MessageDescriptor | Static descriptor/reference tables; private runtime record storage/read-only getters. |
| C++ | static const MessageDescriptor& descriptor() noexcept | Immutable static tables; kind enum, descriptor pointers/accessor functions; no RTTI. |
| Java | public static MessageDescriptor descriptor() | Shared public final descriptor classes, private final storage, immutable lists/maps. |
| Kotlin | companion Content.descriptor(): MessageDescriptor | Shared immutable descriptor classes and protected collection snapshots. |
| TypeScript | exported ContentDescriptor; static descriptor() also returns it on enabled classes | Frozen descriptor objects. Export exists even when Content is an interface. |
| JavaScript | class static descriptor(), exported ContentDescriptor alias | Same immutable object, CommonJS conventions preserved. |
| Go | DescribeContent() and (*Content).Descriptor() | Same shared descriptor pointer; private runtime storage and copy-protecting getters. |
| Swift | static let descriptor | Shared immutable value metadata; registry references avoid recursive inline values. |

Publication spellings apply to every generated message, in both compiler modes.
The shared runtime defines MessageDescriptor/FieldDescriptor once, with the common
inventory in section 3. Properties/accessors use snake_case in Python/Rust/C++,
camelCase in Java/Kotlin/Swift/JS/TS, PascalCase getters in Go. C++ exposed array
views are read-only non-owning ranges over static storage. C++ descriptor queries
are noexcept and allocation-free. Go's receiver descriptor accessor need not
dereference a nil receiver. Python ClassVar is not a dataclass/constructor/wire field.

The owner is application-wide, including any language-specific Taut libraries the
application uses. Generated schema modules supply descriptor VALUES and adapters;
they do not define local copies of descriptor/report classes. Library exports and
compatibility facades must alias/re-export the chosen owner's actual types. Equal
source text compiled into two Rust crates, loaded at two Python/JS module identities,
or built into two Swift modules does not establish shared nominal identity. Matching
contract versions alone cannot cure that split. Section 7 defines distribution and
the per-target import/link routes; reject unsupported split-owner compositions.

Compile separate generation units normally: a parent's typed adapter sees the
child's public descriptor declaration before instantiation/use. C++ descriptor
traits may delegate to the generated accessor; SFINAE can test availability but
must not turn a required missing child into a silently skipped check. Recursive
header declarations must not eagerly instantiate a descriptor tree.

External ownership/import mapping remains a distinct need: full dependency schema
stays available to Taut while a target mapping identifies the actual generated
class, package/module/crate/header and compatible descriptor/codec owner. Existing
Rust external-type support is reference evidence, not proof all targets support it.
The new feature must define these mappings for its independently generated dependency
tests, without inspecting Java binaries in Taut C or supporting arbitrary classes.
No forced simultaneous generation and no automatic dependency regeneration.
Runtime-owner bindings and external schema/type mappings are distinct configuration:
both parent and child, and any Taut library, must resolve to the same codec/descriptor/
report owner. Traversal uses the child's mandatory metadata and typed adapter even
when its optional validation methods were not generated. Distribution selection
must not regenerate that child, add foreign inherent methods, or duplicate its types.

Old artifacts lacking descriptors are incompatible with this contract. Require
regeneration or an explicitly supplied compatible typed adapter+metadata. Missing
support is a named generation/build/configuration error BEFORE claiming recursive
validation, not a deferred success. A runtime local request does not remove compiled
recursive adapter dependencies; no local-only generation profile is proposed.

## 5. Shared validation reports and semantics

Report types belong to one shared runtime per language, not a schema or generated
holder class. Independently generated schemas must return the SAME nominal types.
Vendored source distribution is permitted, but the application includes one shared
runtime identity; avoid copies under schema-specific namespaces. No Taut compiler
is required for normal application builds. Import paths are configured per target.

| Record | Fields |
| --- | --- |
| PathSegment | kind and applicable field_name, index, or key_type/key_cbor_base64 |
| ValidationIssue | code, rule, path, message |
| DeferredCheck | rule, path, reason_code, message |
| ValidationReport | issues, deferred_checks, scope |

Code/rule/reason are open namespaced strings, not oneof-specific enums. Shared records
can represent future constraints without new report classes. This does not implement
new rule families, arbitrary executable predicates or runtime plugin registration.
Unknown future rule identifiers are unsupported schema/runtime configuration, not
silently accepted. Known deliberately deferred virtual rules are handled as below.

Records own immutable snapshots; collections/paths never retain mutable input
references. Constructors accept fields in the listed order; report scope defaults
to recursive and its two collections default empty where language conventions permit.
Getters return immutable views or defensive copies. is_valid()/isValid()/IsValid()
means issues empty; is_complete()/isComplete()/IsComplete() means deferred_checks
empty. Both are required to assert success within the requested scope. Diagnostics
are returned, not exceptions. Normal host resource-failure policies remain, except
the explicit C++ noexcept boundary below.

Scope is local or recursive and appears on every report. recursive=True is default
on both methods. Local checks only the supplied record's rules/payload presence;
it does not traverse contained messages or collection elements. Excluded descendants
are outside the requested scope, not deferred checks. Recursive traverses populated
owned records, including ordinary fields, payloads and list/map elements. Never follow
application ID links. A no-rule local scope returns true/empty complete report; a
wrapper's recursive result still includes child rules.

Virtual-group checks remain deferred in this cut. Each encountered group contributes
a deferred entry, so a virtual-only record's methods return an incomplete report and
Boolean false, not a pretend no-rule success. A root with virtual local groups still
traverses supported non-virtual children. After repairing such a child, the report
may be valid but incomplete. Missing descriptor support is NOT this intentional
deferral: it is the incompatible-artifact error in section 4.

Report mode collects all independently detectable issues; fast mode stops as soon
as a failure/deferred check makes true impossible and does not allocate a full report.
Fast result equals report-valid AND report-complete for the same input/scope. Both
modes share rule predicates, not two independently implemented validators.

Wrong/missing discriminator reports one issue at its field, skips only dependent
selection checks and continues independent rules/children. For known tags, check
selected presence and nonselected absence. Also traverse all populated children,
including invalidly populated nonselected payloads. Do not repair/coerce/freeze input.
Dynamic shape misuse encountered in Python/JS/TS becomes a located issue; invalid
options or descriptor configuration remain API usage/configuration errors.

Order by schema field number: group checks at its discriminator's position, payload
issues by payload field number, child traversal at the child's field position. Lists
use ascending zero-based indices. Maps sort by unsigned-byte lexicographic canonical
Taut CBOR key encoding, not host iteration order. Paths use original schema field
names, Index and Key(type, canonical bytes). Report key bytes as standard padded
base64 plus str/int/bool type tag. Shared children yield per-path issues. An object
already on the active ancestor path yields validation.ownership_cycle and traversal
continues elsewhere; no global visited set hides errors at another path. Languages
whose owned values cannot express a cycle need not manufacture one.

### C++ no-throw contract

Both public instance methods are const noexcept. Do not simply wrap throwing code
in noexcept. On allocation failure, fast mode returns false; report mode produces
a bounded allocation-free fallback: one root validation.resource_exhausted issue
and a root deferred entry with that reason. Validity/completeness are false.
Fallback text/path storage is static/inline, never borrowed from the input. Report
construction/move/getters for this fallback allocate nothing; verify by allocation
fault injection, not assumptions about small-string optimization. Expose shared
read-only ranges (begin/end/size), not a vector-reference API that cannot represent
inline fallback storage. Unrecoverable process faults are outside this contract.

## 6. Exact instance-method projections

The signatures below are API declaration sketches; compiled definitions have bodies.
Every message gets both operations only when validation generation is enabled.
Report/helper types stay in the shared runtime. No per-type free validator names.

### Python

Proposed runtime homes are `taut.descriptors` and `taut.validation` alongside the
existing `taut.wire` foundation. They are new design paths, not existing modules.
This supersedes the earlier sketch's separate `taut_validation` package name;
source and package routes must expose the same owner through the section 7 binding.
Existing generated mutable slotted dataclasses remain. Add:

```python
def validate(self, *, recursive: bool = True) -> ValidationReport: ...
def is_valid(self, *, recursive: bool = True) -> bool: ...
```

Use frozen slotted diagnostic dataclasses, tuple collections, snake_case fields,
methods is_valid()/is_complete(), static PathSegment.for_field/for_index/for_key.
Optional path components use None; index is nonnegative int. Schema-only output
must be importable without selecting a service; fix package initialization through
the existing supported output route. Descriptor attaches after all class/registry
construction. Both methods are thin shared-engine calls, not per-message check bodies.

Shared engine receives (value, MessageDescriptor, SchemaBinding, recursive=True)
through validate_record and is_record_valid. Binding pairs values with the correct
types; descriptor mismatch is configuration failure. Generated class fields use
recorded attributes, not runtime field discovery. One schema registry per graph,
not a process-global mutable registry. No common Python base class required.

### Rust

The configured shared runtime owner exposes descriptor/validation modules. A local
`taut_validation` alias, if used, re-exports that owner; it is not another crate's
independently compiled copy. No new registry crate name is selected here.
Generated same-crate impl blocks on the schema message provide:

```rust
pub fn validate(&self) -> ValidationReport;
pub fn validate_with_options(&self, options: ValidationOptions) -> ValidationReport;
pub fn is_valid(&self) -> bool;
pub fn is_valid_with_options(&self, options: ValidationOptions) -> bool;
```

ValidationOptions has pub recursive: bool; Default sets true. No-options methods
use Default. Runtime structs have private fields, owned strings/Vecs and read-only
snake_case accessors returning str/slices; no input borrow escapes in a report.
Path factories for_field/for_index/for_key, index usize, optional components Option.
External dependency methods must be generated by the type owner; do not try to add
inherent impl methods to a foreign type. Parent traversal uses descriptors/adapters,
not a requirement that child optional validation methods be present.

### C++

Shared namespace taut::validation. Message declarations in generated api.hpp;
inline method definitions may live in a generated helper included without cycles:

```cpp
validation::ValidationReport validate(bool recursive = true) const noexcept;
bool is_valid(bool recursive = true) const noexcept;
```

Reports/descriptors are shared runtime classes, not per-schema copies. Snake_case
getters; descriptor static array views; report read-only ranges support fallback
storage. Strings use std::string/string_view as owned/view contracts require;
indices size_t; optional path components std::optional. PathSegment factories
for_field/for_index/for_key. Match current supported C++ baseline; no RTTI,
std::function allocation or baseline upgrade prerequisite.

### Java

Shared public top-level reports in package taut.validation; descriptors in
package taut.validation.descriptors. No per-schema TautValidation holder types.
Generated message instance methods:

```java
public ValidationReport validate();
public ValidationReport validate(boolean recursive);
public boolean isValid();
public boolean isValid(boolean recursive);
```

No-argument methods select true. Reports have private final fields, public constructors
and record-style getters issues(), deferredChecks(), scope(), etc. Methods isValid()
and isComplete(); immutable defensive java.util.List copies. Path optional values
use nullable components, index boxed Long; factories forField/forIndex/forKey.
No Java records or newer baseline requirement. Descriptor typed accessors avoid
Java reflection and Android hidden APIs. A null receiver follows ordinary Java
call semantics, not a static validator returning a type-mismatch report.

Today's api.java types are package-private; keep that existing visibility boundary.
A general public/multi-file schema projection is separate work, not a prerequisite.
A Java Class<?> token, if used as attachment, does not authorize reflective access.

### Kotlin

Shared top-level reports in taut.validation, descriptors in taut.validation.descriptors:

```kotlin
fun validate(recursive: Boolean = true): ValidationReport
fun isValid(recursive: Boolean = true): Boolean
```

CamelCase val fields, protected immutable snapshot collections, report isValid()/
isComplete(), PathSegment companion forField/forIndex/forKey. Nullable path members
T?, index Long. No common message superclass/interface, KSP or kotlin-reflect.
Generated direct field adapters supply access under the mandatory descriptor contract.
A null receiver remains normal language misuse, not a validation result.

### TypeScript

The configured runtime import exposes shared descriptor/report/engine exports;
`taut-validation` was a sketch name, not an existing npm package requirement.
Always export ContentDescriptor. Disabled output may retain the existing Content
interface; no runtime class is needed merely
for its exported metadata. Enabled output additionally supplies the concrete class:

```typescript
export interface ValidationOptions { readonly recursive?: boolean; }
export class Content {
  constructor(fields: ContentFields);
  validate(options?: ValidationOptions): ValidationReport;
  isValid(options?: ValidationOptions): boolean;
  static descriptor(): MessageDescriptor;
}
```

ContentFields is the existing data-field shape without validation methods. Constructor
copies the supplied top-level schema fields without semantic validation; required/
nullable/default behavior follows the declared schema/native projection. Nested
message fields use their native generated values; do not silently fabricate or
convert children. Plain object literals do not acquire methods. Enabled constructors
and disabled interfaces are a deliberate opted-in API projection; provide migration
examples. Constructor is not a dynamic message factory—it is per generated type.

Omitted options/recursive property select true. Diagnostics/descriptors are readonly
snapshot classes backed by actual freezing/copying, not TypeScript-only annotations.
CamelCase fields, methods isValid()/isComplete(), null optional components, safe
nonnegative integer index. Key i64 values remain canonical bytes, not lossy numbers.
Path factories forField/forIndex/forKey. Descriptor attachment of native constructors
is optional and not required for disabled interface-only metadata.

### JavaScript

The configured CommonJS runtime entry exposes the shared owner. Its exports must
preserve identity if a package also offers an ESM entry; no separate ESM/CJS class
implementations. Generate methods on existing message classes:

```javascript
validate(options = { recursive: true }) { /* returns shared ValidationReport */ }
isValid(options = { recursive: true }) { /* returns Boolean */ }
static descriptor() { /* returns shared MessageDescriptor */ }
```

Omitted options or omitted recursive property select true; invalid supplied options
are API usage errors. CommonJS exports preserved. Reports/descriptors have camelCase
fields, deeply protected collections and isValid()/isComplete(); PathSegment factories
forField/forIndex/forKey. No captured message in static accessors. No per-instance
accessor object. No ES-module migration or reflective class discovery prerequisite.

### Go

Shared descriptor/report package import prefix comes from generation configuration,
not a hardcoded application module. Generated package aliases imported runtime types
if useful, without defining nominal copies. Pointer receiver methods:

```go
type ValidationOptions struct { Recursive bool }
func (value *Content) Validate() validation.ValidationReport
func (value *Content) ValidateWithOptions(options ValidationOptions) validation.ValidationReport
func (value *Content) IsValid() bool
func (value *Content) IsValidWithOptions(options ValidationOptions) bool
```

No-options methods choose true; explicitly passed zero-value options choose local.
Report private fields with exported NewValidationReport/NewValidationIssue/
NewDeferredCheck constructors and copy-returning Issues(), DeferredChecks(), Scope()
getters. IsValid()/IsComplete(). Path factories FieldPath/IndexPath/KeyPath; index
uint64, optional getters (T,bool). Nil root receiver validation returns a root
validation.type_mismatch issue/false. Descriptor receiver need not dereference nil.
No reflect.Type requirement or embedding a common message struct.

### Swift

The configured shared Swift module (called TautValidation in these API sketches)
owns public immutable report/descriptor structs. Source mode builds that module
once; copying definitions into each schema module would create different types.
Generated same-schema-module extensions provide nonmutating instance methods:

```swift
public func validate(recursive: Bool = true) -> TautValidation.ValidationReport
public func isValid(recursive: Bool = true) -> Bool
```

CamelCase public let fields, arrays/strings have value semantics; public initializers
in common field order. isValid/isComplete are computed Bool properties. Scope is a
string local/recursive. Path factories forField/forIndex/forKey; optional components
use Optionals; index Int. No throws or fatalError for invalid drafts. Static descriptor
publication uses registry links rather than recursively embedded value structs.
No common message protocol is required for discovery.

## 7. Distribution, naming and version migration

### 7.1 One implementation, two distribution routes

Operator acceptance recorded 2 November 2026: the base `taut` repository owns the
canonical lightweight serialization foundation, including low-level CBOR/JSON
encoding and decoding runtimes, descriptors and validation, with one maintained
implementation per language. Language-specific Taut libraries own higher-level
delivery-shape engines, messaging behavior and transports, and distribute/re-export
that same versioned foundation through the source/package arrangements below.
The operator explicitly agreed after clarification that base ownership includes
codecs as well as descriptors/validation. This accepts that ownership boundary only;
it does not blanket-approve packaging details, waive readiness gates or authorize
production implementation, release, commit or push.

Keep Taut's lightweight deployment model: an application can receive all required
runtime source alongside its generated schemas and build/run without the compiler,
CLI, schema authoring tools or generator installation. Alternatively it can import
the compatible foundation through the language-specific Taut package route. Both
routes publish the same codec, descriptor, report and validation behavior and types.
Neither route introduces implicit semantic validation.

The canonical implementation remains in the `taut` repository: Python's runtime
source under `src/taut`, and other targets' distributable runtime source under
`src/taut/gen/runtime` (the existing `_RUNTIMES` resource route). New modules must
join that single source of truth. Source bundles and language-package payloads are
assembled from those sources, with provenance/contract metadata and reproducible
content checks. Packaging wrappers/import facades may differ; predicates and public
record definitions must not be maintained twice. Existing library copies migrate by
recorded re-vendoring or re-export/dependency changes, never independent hand fixes.

The foundation has separable codec/extension support, descriptors and immutable
schema facts, and validation engine/reports. Validation-off generated code requires
the first two layers, not the engine. An already shared runtime may contain the
engine for another schema; disabling one schema must not remove that shared engine.
Delivery-shape engines, transports, tools and unrelated dependencies are a higher
layer. Basic source consumers do not receive or depend on that layer. A package
route must provide a foundation-only build/import surface; where a separate small
package/target is needed to avoid pulling in the engine, it uses the same sources
and is re-exported by the language-specific library. This document does not allocate
new package names or claim such surfaces already exist for all nine targets.

### 7.2 CLI selection and compatibility defaults

Current `cli.py` forwards store-true `--with-runtime` as `emit(runtime=...)`,
defaulting to False;
`scaffold.py` copies existing resources only when true and otherwise leaves runtime
resolution to the application. It does not select imports by finding installed
packages. Preserve that default while adding explicit selection:

| Invocation | Proposed behavior |
| --- | --- |
| Neither runtime option | Legacy supplied-runtime mode: emit no runtime source; preserve the target's existing import/link convention, extended for mandatory descriptors. The application supplies a compatible shared owner. This is NOT an implicit `package` selection. |
| `--runtime source` | Emit/reuse canonical runtime source at the configured shared location and generate bindings to that owner. Without an override, retain the existing `<out>/<language>` layout for current runtime files. Add the missing Python source route. |
| `--with-runtime` | Compatibility alias for source mode, including the new foundation required by this version's descriptor contract. Existing invocations keep requesting source, not package imports. |
| `--runtime package` | Emit no runtime implementation; generate imports/link references to the configured compatible language-package foundation owner. Do not install, download, discover or upgrade a package. |
| `--with-runtime --runtime source` | Accept; redundant requests for the same mode. |
| `--with-runtime --runtime package` | Explicit option conflict; fail before writing outputs. |

Only `source` and `package` are accepted explicit values. Repeated identical
`--runtime` values are harmless; different repeated values are a conflict, never
last-one-wins. Missing/unknown values fail argument parsing. `--with-validation`
and its omission work with each row independently. Package availability must never
change the selected mode. An unavailable configured package/export produces a named
configuration/build/import error, not fallback to copied source.

Current Rust external-type generation rejects `runtime=True`: the dependency's
owner must supply the shared runtime. Preserve that guard for `--with-runtime` and
`--runtime source` with a nonempty external-type map. Use supplied-runtime mode or
explicit package mode bound to that owner; do not emit a second Rust runtime beside
the dependency. Broader source-bundle assembly for several crates is application
build configuration, not permission to weaken the guard or regenerate dependencies.

Programmatic `emit` and `emit_all` gain keyword-only `runtime_mode: str | None = None`
and `validation: bool = False`. Preserve `emit`'s existing keyword-only
`runtime: bool = False`; add that compatible keyword to `emit_all`, keeping its
three existing positional parameters. Both entry points use the same resolution:

| `runtime` | `runtime_mode` | Resolution |
| --- | --- | --- |
| False/omitted | None | Legacy supplied-runtime mode. |
| True | None or `"source"` | Source mode. |
| False/omitted | `"source"` or `"package"` | Explicit selected mode. |
| True | `"package"` | ValueError before writes. |

`False` is the existing neutral default, not an explicit instruction forbidding
source. Reject unknown modes and non-Boolean flag values as API usage errors.
`emit_all` forwards selection, validation and runtime binding configuration to
`emit`; it must not silently discard them. The proposed binding configuration is
target-keyed and keyword-only; its concrete CLI/config-file syntax is a backend
handoff detail, not another mode or an agreed new flag spelling.

### 7.3 Runtime bindings and existing language libraries

Each target binding records the runtime owner identity, source output location
(if emitting), generated import/include/module/crate prefix, link/build target as
applicable, and required contract/capabilities. It separately records external
schema owners. Explicit package mode needs a known supported binding, either the
target's documented package default or a supplied mapping. A missing binding is
an error before writes, not a guessed package name. Source mode permits several
generation runs to name one shared owner/output root; copying beside every schema
is not the composition strategy. Supplied-runtime mode can bind to that same source
owner or package owner without copying it.

The table records inspected current routes and the required integration. New public
exports/targets described here are design work, not claims about current packages.

| Target | Existing route and required owner binding |
| --- | --- |
| Python | Distribution `taut-proto`, import `taut`; `taut-shape-py` distributes `taut-shape`/imports `taut_shape` and depends on `taut-proto>=0.10.0,<0.11`. Bind both generated schemas and the library to the same `taut.wire`, proposed `taut.descriptors` and `taut.validation` modules. A source bundle exposes that runtime namespace once, without a nested schema-local `taut` copy or mixing partial installed/vendored namespaces. |
| Rust | Current generated codecs use `crate::cbor`; `taut-shape-rs`'s `taut-shape` crate publicly owns vendored `cbor.rs` and generated messages. Bind codec/descriptor/report paths to one shared crate owner; preserve `crate::cbor` via a true re-export when needed. Migrate library internals to that owner or use a supported library foundation export, retaining `no_std` + `alloc` support. A separate lightweight foundation crate/target is required if the library route otherwise makes basic applications take the shape engine. Two crates compiling identical runtime source are not interchangeable owners. |
| TypeScript | `taut-shape-ts` publishes `@owebeeone/taut-shape` and vendors `src/taut/{cbor,codec,schema,jsoncodec}.ts`. Current package exports are `.`, `./engine`, `./cli`, with no public foundation subpath. Add a foundation export/re-export route bound to the one canonical module graph; generated imports use that configured specifier or the shared source path. Do not import the engine barrel just to obtain descriptors/reports. |
| JavaScript | Existing generated CommonJS codecs require `./cbor.js`. Source mode shares one configured module path; package mode requires a supported CommonJS foundation entry. The existing TS library is ESM and is not evidence of a usable CommonJS runtime entry. Aliases must resolve to the same loaded exports, including dual-format applications. |
| C++ | Existing generated code includes `taut/cbor.hpp` in namespace `taut`. Bind all schemas/libraries to one include root and compatible runtime build/link target; new descriptors and `taut::validation` live there. Source mode shares the headers/definitions once; package mode supplies that same include/link surface. Avoid duplicate definitions/ODR violations. |
| Java | Current runtime and generated `api.java` share package `taut`; message classes remain package-private. Source mode compiles one shared foundation; package mode supplies compatible public runtime classes on the configured classpath/module route. Reports/descriptors keep section 6's public packages. Package-private codec helpers may need a public foundation bridge; do not solve this by copying nominal types or expanding generated-message visibility. |
| Kotlin | Current codecs/runtime share package `taut`. Bind source compilation or a compatible artifact to one foundation with section 6's `taut.validation` packages, direct typed adapters and explicit codec visibility. Java and Kotlin are separate targets; do not assume their package spellings imply binary-interchangeable implementations. |
| Go | Current `api.go`, `cbor.go`, `ext.go` compile in the same `package taut`. For independent schema packages, bind exported codec/descriptor/report APIs to one shared import path; any compatibility aliases are Go type aliases, not new defined types. The application supplies the module path; package mode must not invent one. |
| Swift | Current source runtime compiles with generated types. Build the proposed shared descriptor/report foundation in one configured Swift module/target for all schemas and libraries; import it through either source or package build configuration. New exported codec access must cross that module boundary explicitly. Do not compile report structs independently into each schema module. |

Only Python, Rust and TypeScript shape libraries were found in this checkout; there
are no assumed `taut-py`/`taut-rs` repositories or existing package-mode support for
the other targets. Before each backend is called complete, record its concrete
foundation package/export and build/import binding and exercise both routes. The
single-owner requirement applies to the current codec types/errors as well as the
new descriptors/reports; preserving an import spelling through a facade is allowed.

Python needs particular work: today's `python_api` emits mutable slotted dataclasses
and enums, not a standalone copied codec, and `_RUNTIMES` has no Python entry.
Current Python codec/jsoncodec use `taut.ir.model` and `taut.ir.options`; model also
uses `ir.shapes`. The source bundle must include the exact minimal transitive runtime
closure (or a fact-only extraction from those same canonical sources), immutable
schema/codec facts and generated bindings, CBOR/JSON codecs and extension helpers
when used, mandatory descriptors, and optional validation engine/reports. Supply
runtime-only package initializers and version/contract metadata. Enumerate and test
that closure in the Python checkpoint; copying only `cbor.py` is insufficient.

Normal application imports/codec calls must not require `taut.cli`, `taut.gen`,
`taut.ir.load`, authoring DSL execution, corpus tools, build tooling or compiler
dependencies. Generate the required immutable facts ahead of time through the
existing compiler route. `taut-shape-py` currently loads bundled `.taut.py` schemas
through `_schema.py`/`taut.ir.load`, and its README uses sibling `taut/src` on
PYTHONPATH. Its integration must migrate normal wire operations to emitted facts
and the shared owner; compiler/authoring use may remain an explicit development tool.
This is a required migration, not existing source-only Python capability. Installing
the full current `taut-proto` package can remain supported, but does not make its
compiler modules necessary application dependencies or justify shipping shape engines
to basic source consumers.

### 7.4 Compatibility, identity and safe output ownership

Generated artifacts declare generator provenance, descriptor contract, codec contract
and required capabilities (including validation rules when used). Runtime bundles and
package exports declare supported contracts and their owner identity. Distribution
mode alone is not a version. Compatible package and source artifacts may compose
only when their bindings resolve to the SAME actual owner, e.g. a library re-export
of the application-selected foundation. A private source copy inside a prebuilt
library cannot be unified by relabeling a version string: rebuild/reconfigure that
library against the shared owner or reject the composition explicitly.

Check all supplied metadata and mappings before generation writes; verify remaining
requirements at target compile/link/import/descriptor publication, before validation
is usable. Do not require executing a target package inside the compiler. Errors name
the offending artifact/owner, required and found contracts/capabilities, and the
regeneration/rebinding action. Missing packages, old descriptors, unsupported rules,
incompatible codec contracts and duplicate owners are configuration failures, never
empty successful reports. No package installation, dependency regeneration or silent
upgrade/fallback occurs. Patch versions may interoperate under declared contracts.

Source emission preflights the complete output set. Reuse matching runtime content
at the selected owner; update only positively identified generator-owned, unmodified
files under the recorded compatible generation policy. Record paths, provenance,
contract and content hashes in generator ownership metadata. Detect handwritten,
modified, unknown-owner or incompatible-version files and fail with named paths
before replacing anything; a header alone is insufficient ownership proof. Existing
untracked legacy copies need explicit migration/adoption or a fresh output root.
The present scaffold writes resources directly; these protections are requirements
for the amendment, not a description of current overwrite safety.

On source/package or validation-mode changes, remove only stale files whose recorded
ownership and prior content still match, and only if no other recorded schema needs
that shared component. Never delete a shared owner on behalf of one schema. If
ownership/use cannot be established, report the stale outputs and require a fresh
directory or explicit user-managed migration. Package mode must not leave private
source copies looking like the selected owner. No handwritten runtime file is
silently overwritten or deleted.

### 7.5 Naming and version migration

Preflight generated names before output: descriptor accessors/constants, validation
methods, options and helper symbols against schema fields/codec names and target
escaping. Reject actual collisions explicitly, never silently rename API/fields.
Descriptor names are reserved for BOTH new generation modes; validation method names
only for enabled mode. A message field validate can remain allowed when validation
methods are disabled, if no descriptor collision exists. Changes from older compiler
name acceptance are documented migration changes, not compatibility claims.

Release under a distinct Taut C version. Generated code identifies both generator
release and descriptor-contract version; the shared runtime declares compatibility.
IR version, descriptor-contract version and release version have different meanings.
Patch releases may share a contract; do not require arbitrary exact release equality.
Missing or incompatible imported descriptors/codecs produce explicit errors identifying
the artifact and required contract, not a cryptic successful partial validation.
No runtime search through Java binaries and no assumption that old code was generated
with validation enabled. New child descriptors work even with its methods disabled.

Update all affected goldens deliberately for the new contract. Preserve the prior
baseline as migration evidence; attribute every change to descriptors/imports/version
markers, opted-in methods or explicitly authorized oneof JSON. This supersedes the
old byte-identical disabled-output promise but does not permit unrelated changes.
Release numbering follows repository policy; publishing still needs explicit instruction.

## 8. Python-first delivery and conformance gates

One coherent Python reference batch, after document acceptance and operator approval:

1. Freeze Python's runtime binding, source-bundle file closure and contract metadata;
   provide source and package delivery from the same canonical runtime sources,
   including the `taut-shape-py` integration boundary. No compiler at application time.
2. Native authoring/model/IR support and compatibility checks for enums, OneOf/Case,
   presence, coverage and normalized typed descriptor facts. No probe-only annotations.
3. Shared Python descriptor/report/runtime definitions and immutable registry binding;
   mandatory metadata and thin optional instance wrappers through normal compiler emit.
4. Shared engine with common predicates, local/recursive traversal, Boolean short-circuit,
   full reports, deferred virtual checks and observational snapshot semantics.
5. JSON sparse payload projection on existing supported route; dense CBOR unchanged.
6. Validation-on/off goldens in both runtime distributions, supplied-runtime regression
   cases, executable fixtures and old/new contract diagnostics.
   Record a Python-complete checkpoint, exact runtime/IR contract, package imports and
   source file inventory, ownership metadata and corpus version. Only then proceed
   to the remaining eight backends against this document. Each backend first freezes
   its foundation package/export and target binding from section 7; Python package
   availability is not evidence that another language's package route exists.

Each backend must compile/import and RUN its tests; text generation alone is not support.
No backend invents API variants or weakens fixtures to pass. All nine are required for
full feature completion. Fixtures compare code/rule/path/deferred data and validity/
completeness/scope, not host repr or human message wording.

Required corpus includes:

- Every virtual/exhaustive combination, defaults and invalid nominations/flags;
  scalar/enum/collection types, unconstrained fields and complete metadata inventories.
- Missing selected, extra nonselected, zero/false/empty, payload-free choices, wrong
  discriminator, multiple independent groups and populated nonselected nested children.
- Local/recursive equivalence of fast versus report; no-rule messages and wrappers;
  virtual-only incomplete results; virtual root/nonvirtual child with root-relative
  issue and deferred group after child repair.
- Ordinary nested fields/list/map keys, shared paths, recursive schemas/runtime cycles,
  stable paths/order, snapshots after mutation, and invalid->serialize->repair->validate.
- Missing/null JSON acceptance; preservation of multiple populated payloads; no implicit
  validation in construction/mutation/codecs; CBOR behavior remains its existing contract.
- General shared reports accept a synthetic non-oneof diagnostic without API changes;
  independent schemas aggregate shared runtime issue types without conversion.
- Mandatory descriptors with validation off; descriptor+methods with it on; default and
  programmatic flag forwarding; name collisions and unchanged unrelated construction APIs.
- Separately generated child/parent, enabled parent/disabled child, old dependency rejection,
  accepted/rejected contract versions and shared-runtime identity/linkage. No forced
  all-at-once compilation or automatic regeneration of dependencies.
- Runtime selection matrix: source and package, each with validation on/off; default
  supplied-runtime behavior; `--with-runtime` alias; agreeing/conflicting/repeated flags;
  programmatic `emit`/`emit_all` forwarding and Rust external-owner guards. Failures
  leave output unchanged. Installed-package presence does not alter mode or imports.
- Run the same behavioral corpus through both distributions; compare package payload
  and source-bundle provenance/content against the canonical sources. Verify descriptor
  queries with the validation engine absent and no implicit semantic validation.
- At least two separately generated schemas and a generated schema plus the actual
  language-specific library share descriptor/issue/report AND codec type identities.
  Cover source/source, package/package and source/package generation combinations:
  all must bind/re-export one actual owner, with enabled/disabled child combinations.
  Check native type assignability/identity or compile/link evidence, not equal JSON
  or equal version labels. Deliberately split owners must fail with a clear diagnostic.
- Compatible unequal patch releases accepted by contract; mismatched descriptor/codec
  contracts, unsupported capabilities/rules, missing package exports and old children
  rejected before validation. No automatic install, fallback or child regeneration.
- A clean source-only application imports/builds and runs codecs/descriptors/validation
  with no compiler, CLI, generator, authoring loader, shape engine or unrelated runtime
  dependency available. Python tests exclude compiler modules and DSL loading, including
  the library wire path; package tests use the foundation-only entry/build target.
- C++ no-RTTI/static access route and allocation-fault noexcept fallback; Java/Kotlin
  direct adapters with no reflection; supported Android toolchain route without new
  baseline assumptions. Test the existing route before demanding infrastructure changes.

Use fresh output directories for mode goldens. Separately test enabled->disabled
regeneration: remove only positively identified generator-owned stale files; otherwise
report the stale outputs and require a fresh directory rather than deleting unknown
content. Old methods cannot remain looking like current disabled output. Handwritten
files survive. Record target/track/reason for each golden change.

Also test source->package, package->source, same-owner reuse across generation runs,
modified/handwritten/unknown runtime files, contract changes and shared-runtime users.
Verify preflight prevents partial writes on conflicts and one schema's cleanup never
removes another schema's foundation or validation engine. Preserve legacy file/layout
evidence and distinguish mandatory descriptor migration from optional mode changes.

## 9. What is settled, what remains, and evidence limits

Settled here: shared descriptor inventory and publication, primitive schema kinds,
mandatory metadata/optional instance methods, report shape and scopes, no-throw C++,
known imported Taut types, explicit contract errors and Python-first/all-nine completion.
The runtime amendment settles explicit source/package selection, the source alias,
legacy supplied-runtime omission, conflict handling, compatible Boolean programmatic
options, a single canonical implementation and shared application/library owner,
foundation/shape-engine separation, Python's missing source-runtime work, version
checks and safe generator-owned output transitions. No additional user choice is
needed to consolidate those behaviors.

Concrete low-level typed-access adapter layouts, target binding configuration syntax,
foundation package/export names and numeric IR/descriptor/codec version allocation
remain recorded implementation handoff details. In particular, Rust must freeze the
lightweight shared-crate/re-export route; TypeScript must add a foundation-only export;
JavaScript needs a usable CommonJS entry; Python must enumerate the runtime closure
and remove application-time schema loading from the library wire path. The remaining
targets need real package/build bindings before claiming package support. These are
backend readiness gates, not assertions of existing support or newly agreed registry
names. Resolve them in the Python checkpoint and each subsequent backend handoff;
escalate a concrete incompatibility if the one-owner/no-engine contract cannot be met.
They are not permission for a common base class, reflection, unrelated dependencies,
faster algorithms or a dynamic message factory.

Inspected checkout evidence (paths relative to `taut-dev`):

- `taut/src/taut/cli.py`: `--with-runtime` store-true and forwarding; no explicit
  runtime mode or validation option yet.
- `taut/src/taut/gen/scaffold.py`: keyword-only `runtime=False`, `_RUNTIMES`,
  resource writes, Rust external-type conflict, Python dataclasses/enums and
  service-dependent package initializer; current `emit_all` takes three arguments.
- `taut/pyproject.toml` and `taut/src/taut/wire/{codec,jsoncodec}.py`: `taut-proto`
  distribution, stdlib-only dependencies and runtime IR-fact imports.
- `taut-shape-py/{pyproject.toml,README.md,src/taut_shape/_schema.py}`: dependency
  on `taut-proto`, sibling-PYTHONPATH examples and application-time DSL schema load.
- `taut-shape-rs/{README.md,crates/taut-shape/Cargo.toml}` and that crate's
  `src/{lib,cbor,generated}.rs`: public vendored CBOR owner, no_std/alloc and
  generated `crate::cbor` references.
- `taut-shape-ts/{README.md,package.json,src/index.ts}` and `src/taut/*.ts`:
  vendored foundation, ESM package exports and current engine-bearing barrel.
- `taut/src/taut/gen/{cpp,go,java,kotlin,js,swift}.py` and their runtime resources:
  existing include/package/module conventions underlying the section 7 table.

Current evidence is reference-source inspection and earlier isolated Python/Rust probes.
The earlier 42 probe tests are not tests of this consolidated contract. No production
compiler, runtime, target code or dependency has been changed/tested for this document.
The historical proposal/draft/review records remain evidence of their stated review
objects; they are not acceptance records for this packaging amendment. The next
step is the amendment consistency check and backend readiness handoff, with any
requested review filed against this actual revision. Implementation requires the
operator's separate instruction. No review success, implementation completeness or
release authorization follows from this consolidation.
