# Oneof, descriptors and explicit validation — build proposal

Date: 2 November 2026. Status: DRAFT, consolidated for proposal-only review.
No production implementation, compatibility test or release is claimed here.

## 1. Authority, scope and precedence

The operator requests one implementation document for all nine supported languages,
with Python implemented first and the others following a common conformance corpus.
The operator subsequently selected mandatory descriptors, opt-in instance validation
methods, general-purpose shared reports, local/recursive modes, a Boolean fast path,
and versioned generation. This document records those latest decisions in one place.

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

Release numbering, descriptor ABI numeric version and exact import prefix selection
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

Shared packages taut_validation (reports/engine) and taut_validation.descriptors.
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

Shared application-level taut_validation runtime/module defines reports/descriptors.
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

Shared runtime module taut-validation. Always export ContentDescriptor. Disabled
output may retain the existing Content interface; no runtime class is needed merely
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

Shared CommonJS taut-validation runtime. Generate methods on existing message classes:

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

Shared module TautValidation owns public immutable report/descriptor structs.
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

Shared runtime types must retain one nominal identity per application. Vendor its
source once or use the supported versioned library route; do not copy reports into
each schema package. Generator output with runtime requested installs/reuses one
runtime location. Without runtime emission, require compatible application-supplied
runtime. Detect incompatible versions without overwriting handwritten/other-version
files. Establish import prefixes and linkage for each target before its backend
handoff; no external dependency is changed merely because this plan mentions it.

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

1. Native authoring/model/IR support and compatibility checks for enums, OneOf/Case,
   presence, coverage and normalized typed descriptor facts. No probe-only annotations.
2. Shared Python descriptor/report/runtime definitions and immutable registry binding;
   mandatory metadata and thin optional instance wrappers through normal compiler emit.
3. Shared engine with common predicates, local/recursive traversal, Boolean short-circuit,
   full reports, deferred virtual checks and observational snapshot semantics.
4. JSON sparse payload projection on existing supported route; dense CBOR unchanged.
5. Both generation-mode goldens, executable fixtures and old/new contract diagnostics.
   Record a Python-complete checkpoint, exact runtime/IR contract, package imports and
   corpus version. Only then delegate remaining eight backends against this document.

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
- C++ no-RTTI/static access route and allocation-fault noexcept fallback; Java/Kotlin
  direct adapters with no reflection; supported Android toolchain route without new
  baseline assumptions. Test the existing route before demanding infrastructure changes.

Use fresh output directories for mode goldens. Separately test enabled->disabled
regeneration: remove only positively identified generator-owned stale files; otherwise
report the stale outputs and require a fresh directory rather than deleting unknown
content. Old methods cannot remain looking like current disabled output. Handwritten
files survive. Record target/track/reason for each golden change.

## 9. What is settled, what remains, and evidence limits

Settled here: shared descriptor inventory and publication, primitive schema kinds,
mandatory metadata/optional instance methods, report shape and scopes, no-throw C++,
known imported Taut types, explicit contract errors and Python-first/all-nine completion.
Concrete low-level typed-access adapter layouts, configured import prefixes and numeric
IR/descriptor version allocation remain backend/release design details to settle and
probe before their implementation. They are not permission for a common base class,
reflection, unrelated dependencies, faster algorithms or a dynamic message factory.

Current evidence is reference-source inspection and earlier isolated Python/Rust probes.
The earlier 42 probe tests are not tests of this consolidated contract. No production
compiler, runtime, target code or dependency has been changed/tested for this document.
The next deliverable is the proposal-only dual review loop with filed verdicts. A GO
accepts document coherence, not implementation completeness or release authorization.
