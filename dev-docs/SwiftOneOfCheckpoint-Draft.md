# Swift OneOf checkpoint — controlling DRAFT

Status: **production frozen by root at source inventory
`51c92bf28ff9d9936bb89f1c6a9225fcf2ce6858f816eebef406c6e74b5ee156`;
exact source inventory/focused evidence in Preparation; checkpoint/review/global
gate pending**.
[Authority](SwiftOneOfCheckpoint-Authority.md) records the controlling operator
directions. This document supplies implementation details, not new authority.

## Problem and scope

Swift was the ninth remaining backend without mandatory complete descriptors,
optional explicit validation, one immutable report family, native adapters and
explicit shared runtime delivery. The old direct recursive struct projection
also failed native compilation. The remedy extends the existing compiler/codecs
and completes shared emit/emit_all/CLI/package-data wiring. User authoring/model/IR,
other target semantics, dependency locks and reference libraries remain preserved.

## Native projection and ABI

Ordinary messages and collection-indirect recursive messages remain mutable
structs. Only strongly connected components of direct stored-message edges become
`final class`; optionality does not make inline recursive storage finite. Self and
mutual direct recursion compile using native references. Required arguments stay
required. Public enum/initializer/property/CBOR/bounds/decode conventions otherwise
remain unchanged. No per-field box, common message base/protocol or generic
reflective factory is introduced. No native JSON route is invented.

Every message exposes `static let descriptor: MessageDescriptor`,
`static var schemaDescriptor: SchemaDescriptor` and
`static let tautBinding: MessageBinding<NativeType>`. Enabled messages add exactly
`validate(recursive: Bool = true) -> ValidationReport` and
`isValid(recursive: Bool = true) -> Bool`, as public extension members calling one
engine. Per-type schema access avoids conflicting global schema functions when
disjoint schemas share an application module. Enum metadata is also published.

The foundation owns immutable value descriptors, typed paths and optional general
reports. Closed `MetadataValue` values retain nested owned snapshots without Any
references. Arrays/dictionaries/strings retain Swift value semantics. Private,
locked lazy links cache one validated typed edge and do not recursively expand
message graphs. Schema publication checks category/version/registry ownership.
Native enum/message fingerprints normalize irrelevant declaration order and
include effective codec facts, residual preservation and class/struct form.
The parent's complete imported graph checks enum inventories even when no local
parent field directly names an enum.

`MessageBinding<V>` receives the current native value through typed presence,
enum-read, primitive-read and child/list/map walk closures. Static closures never
capture a live instance. Bindings verify the descriptor's native metatype token;
no unchecked erased value/descriptor pair reaches validation. `RecordTraversal`
is an engine callback boundary, not a message discovery protocol. Value bindings
have no identity. Reference bindings use actual `ObjectIdentifier` together with
native type, qualified schema identity and fingerprint. Active ancestors yield
cycle issues; shared children remain checked independently at each path.

Non-null presence includes zero/false/empty. Wrong discriminator reads skip only
dependent selections; unrelated groups and populated children still run. Virtual
selection remains deliberately deferred. Local excludes descendants; recursive
walks ordinary, list/map and populated nonselected children. Field/group/child
order uses field numbers, indices ascend and map paths sort unsigned canonical
CBOR key bytes with padded base64/type tags. Fast and collecting modes share one
predicate stream; instrumentation proves fast mode constructs no reports/issues.
Reports survive later draft mutation. Constructors/setters/codecs do not validate
or repair semantics and preserve populated invalid payloads. Cyclic object graphs
have no finite CBOR representation; no cycle-serialization guarantee is added.

Names follow Swift's normal Unicode identifier ranges, not Python XID rules;
native IR emoji names compile/run and retain original metadata/report spelling.
Existing valid enum case spellings are retained. Actual codec/generated symbol
collisions are escaped or rejected before writes; validation-only names depend on
generation mode and real qualifier scope. Empty raw-value enum inventories fail
prewrite instead of producing uncompilable Swift.

## Delivery and actual owner

Owner `taut.swift.foundation`, codec/descriptor contract 1, capabilities
codec.v1/descriptors.v1/oneof.v1. The single canonical closure is existing
`runtime/cbor.swift`, `runtime/ext.swift` plus new
`runtime/swift/{paths,descriptors,reports,validation}.swift`. Off mode omits reports
and engine. Basic applications use only Swift/standard libraries, without the
compiler, loader, authoring DSL, delivery engine or transport dependencies.

Source defaults to an explicitly shared `TautFoundation` module built once from
those bytes. Package mode requires a real supplied module binding and normal
native module/library search/link paths; no Swift package repository is invented.
An optional local artifact inventory is checked before writes. The explicit
development builder compiles a module/library from the canonical closure; schema
emission never executes it. Actual selected exports are checked independently in
generated code using a defined evidence result, owner/contracts/capabilities, so
old no-op compatibility guards cannot hide stale selected exports. True re-export
facades preserve nominal identity; split compiled modules fail native composition.
Compatible unequal build labels are accepted by contract.

Omitted runtime selection preserves flat supplied mode: emit no runtime or import,
and compile canonical sources once alongside schemas in the application module.
Explicit supplied module bindings select a shared imported owner without copying.
Both placements use identical canonical bytes. Swift requires unique source
basenames within one module; byte-identical filename-only build copies of separate
`api.swift` files satisfy this native requirement without rewriting generated code.
The example documents exact commands.

External mappings specify module/type/owner/contracts/capabilities for the full
dependency graph. Empty dependency module explicitly identifies existing types in
the same application module. Imported child modules require an explicitly shared
foundation module. Parent generation never regenerates children or adds their
optional methods. Native rebuild/link tests replace actual child artifacts while
retaining original generated parent expectations. Arbitrary changed Swift struct
layouts are not promised binary resilience; applications rebuild against the actual
replacement module before checking its facts.

## Shared output boundary

`owned_runtime.plan_outputs(profile, directory, texts, *, mode, validation,
source_root, consume_source=False, external=False)` and `manifest(profile, path,
kind)` extract the accepted Go algorithm without changing its transitions. Go
retains wrappers; profiles supply resource/import/path/owner facts. Swift uses that
same kernel, existing physical-path/raw-fspath checks, locks, preflight, manifests
and user accounting. No target-specific retirement state machine is added.

Selected live source-owner import remaps fail. Legitimate unused source-owner
retirement remains distinct, preserves other users/engines and deletes only owned,
hash-matching stale files. Unknown/modified/handwritten/incompatible sources,
obstructions, aliases and overlapping targets refuse unchanged. Interrupted
multi-file updates recover safely or refuse unchanged; no orphan adoption or
success with ambiguous old owners is claimed. The existing pre-lock previous-root
junction regression now covers all nine targets.

## Evidence and limits

Preparation records exact commands, per-run source association, counts, source
hashes, owned-file allowlist, protection checks and remaining coordinator steps.
Historical failed development attempts remain distinguishable from passing final
focused receipts. Counts overlap and are not summed. The real wheel is built,
extracted and used by isolated Python generation followed by native source/package
compilation/execution. Native tests cover imported and flat supplied OFF/ON,
disabled independent children, artifact replacements, true/forged facades, cycles,
finite/shared values, metadata, naming, flags and durable transitions.

The accepted Go kernel is compared against the extracted helper using exact write
bytes/deletion sets on identical physical roots, with existing native/state and
retirement cutoff regressions preserved. Previous full-global/all-16 results retain
their original tuples. Root's final settled global receipt and two reviewer
verdicts remain mandatory before acceptance and final publication.
