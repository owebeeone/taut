# JavaScript/TypeScript OneOf checkpoint — controlling DRAFT

Status: **accepted at Taut 57c56d5f7d727eb483ac9fd89c482f6a44f7913e,
shape-ts 1aaeab65e4564a462044d2f5d824cd2f375aae97 and
workspace f4a2e908933b634edffaf17191359b472e34ff03 after
ReviewCode-1 and ReviewState-1 reported GO; this accepts the combined JS/TS
implementation and actual TS library integration only**.
See Verdict-1 for the complete closure ledger and scope. One merged remediation
round was used. The initial immutable source 68c24a89/shape-ts1409634e/rootfe244bc4,
Preparation, initial NO-GO reports and failed r0 global receipts retain their
historical attribution. No push, tag, release or publication follows.

[Authority](EcmaOneOfCheckpoint-Authority.md) records the operator directive,
scope and amendments. [Preparation](EcmaOneOfCheckpoint-Preparation.json) records
the frozen scope and verified working-byte inventory, not acceptance. This DRAFT records
the implementation remedy and evidence; it creates no product requirements.

## Observed problem and required outcome

The accepted Python/Rust/JVM implementation supplies native OneOf/Case facts,
IR3 for constrained schemas, compiler legality checks, conformance semantics and
shared safe output helpers. JS and TS lacked mandatory immutable metadata and
the exact optional instance methods. The old unconditional runtime resource
copying did not implement the new explicit shared-owner distribution lifecycle.
The actual TS library independently vendored codecs and lacked a foundation-only
entry with demonstrably shared CJS/ESM class identity.

The pair extends normal `emit`/`emit_all` and the existing codecs. Every message
publishes complete metadata in both validation modes. Enabled methods are thin
calls to one target engine. Non-null presence includes zero/false/empty values;
payload-free choices, independent groups, wrong-tag dependent-check suppression,
ordinary/nonselected-child traversal, local/recursive scope, active-ancestor
cycles, per-path shared children and intentional virtual deferral follow the
actual Python reference. The fast result equals report-valid AND complete and
does not construct diagnostic/report objects. Reports are owned immutable
snapshots with open namespaced strings and original names/index/key paths.

Field/group/child ordering follows schema field numbers, lists use ascending
indices and maps sort canonical CBOR key bytes lexicographically as unsigned
bytes. Key diagnostics retain str/int/bool type and standard padded-base64 bytes;
i64 keys never pass through lossy Number conversion. Invalid drafts remain mutable
and all populated payloads serialize. No constructor/setter/codec runs semantic
validation. JS/TS dynamic misuse inside known bindings yields located issues;
invalid options or unsupported metadata/versions are usage/configuration errors.

## Concrete projections and owners

JavaScript keeps existing mutable object constructors and CommonJS exports.
`Name.descriptor()` and exported `NameDescriptor` return the same shared immutable
MessageDescriptor in both modes. Enabled messages implement
`validate(options = {recursive:true})` and `isValid(options = {recursive:true})`.
Omitted options or omitted recursive selects true; invalid supplied options fail.
`SchemaBinding` stores generated native classes and captureless field readers;
stable registry-key type links terminate publication on recursive schemas.
Descriptors contain static values, with no live-instance captures or per-field
live wrappers. Frozen null-prototype records protect map inventories rather than
exposing a mutable Map beneath Object.freeze. Safe quoted own fields preserve
prototype-like names; actual codec/validation collisions fail before writing.

The JS owner is `taut.javascript.foundation`, descriptor/codec/engine contract1,
capabilities codec.v1/descriptors.v1/oneof.v1. Canonical resources emit as cbor.js,
ext.js, contracts.js, descriptors.js, reports.js and optional validation.js. A
private local `taut-js-foundation` npm-pack artifact derives from those same
bytes. Its actual CommonJS package/subpaths are executable; Node ESM imports the
same owner. Loaded codec export identity, descriptor types and engine owner/
contract are checked, including a foreign codec behind canonical facades. There
is no actual JS shape library in this workspace and none is fabricated.

TypeScript always exports `NameDescriptor`/`NameBinding`; disabled output retains
the native interface. Enabled output adds `NameFields` and the per-type mutable
class with the proposal's constructor, validate/isValid and static descriptor.
Construction copies top-level declared fields, retaining child values directly;
it never fabricates children or gives object literals methods. The target ABI is
`MessageBinding<T>(descriptor, read, accepts)`, with generated captureless readers,
lazy checked links and shared immutable portable facts. Descriptor/runtime
publication does not require disabled interface-only children to have methods
or native constructors.

The TS owner is `taut.typescript.foundation` with descriptor/codec contracts1,
IR1–3 and the same named capabilities. Its canonical foundation closure contains
cbor/codec/schema/jsoncodec/ext/snapshots/descriptors/reports/foundation, adding
validation only when needed. Mandatory metadata is engine-free. The real
`@owebeeone/taut-shape/foundation` and `/foundation/validation` subpaths expose a
canonical CJS owner with ESM facades re-exporting actual classes/state. Former
vendored runtime modules become true compatibility facades. The existing library
delivery engines remain library-owned. Explicit selected-source-owner facades
support real source/package/library compositions; matching labels/source text
alone do not establish identity. JS and TS remain distinct codec projections.

## Generation, dependency and durable-output boundaries

`--runtime source|package`, legacy source alias and omitted/supplied mode are
independent of validation. Keyword-only emit/emit_all forward `js_external_types`
and `typescript_external_types` along with modes, validation, identity and bindings.
CLI inputs are JSON files; help names defaults. JS bindings select a module/root
and optional verified local tgz; TS additionally selects validation_module.
Imported schema names map to explicit module/export bindings and retain complete
native dependency facts. Imported fingerprints normalize irrelevant field/Case/
enum ordering and include effective codec facts. Tests substitute separately
built children/runtime artifacts rather than trusting caller claims. Compatible
unequal build labels work. There is no automatic installation, fallback, package
presence inference or dependency regeneration.

Typed TS service stubs accept the existing structural call/subscribe transport
API. Source service output separately emits canonical taut_client.ts whose
codec/schema imports name the selected source owner. Package/supplied stubs do
not invent a foundation transport subpath. API-only foundation consumers remain
transport-free. Strict compilation/transpilation and runtime tests cover default
source, shared-source, package and supplied service bindings.

The coordinator required a prefreeze type-soundness correction: decoded
transport values remain plain data, so enabled service results must name a
truthful recursive exported data projection rather than claim class methods.
The TS executor owns those exports and external mapping contract; JS owns
shared service inputs/results and strict/runtime proofs. Shared stubs now call
the TS emitter's data_type helper with validation/external context; disabled
messages also export a Fields alias, and external message data imports default
to the actual ExportFields interface (overridable by explicit data_export).
The corrected focused command passes500 cases with one symlink-privilege skip,
including four new nested strict positive/negative and codec-backed runtime
service proofs. Decoded values remain plain. No implicit class construction or
semantic validation was added.

One additional test-only negative external-artifact case passes separately:
a facade exporting class/descriptor/binding without the mandatory Fields data
export fails strict tsc clearly. It is not relabeled as a501-case full run.
The TS constructor unknown-tag preservation correction is settled in its final
86-case gate. Enabled construction retains the existing optional native residual
Map by reference without placing it in portable descriptors; actual unknown tags
survive decode/construct/reencode and only the exact storage-name collision fails.

Complete target text plans use common output locks, owner/user manifests and
preflight/application helpers. Unknown/handwritten/modified/incompatible files,
obstruction, overlaps, aliases/junctions, unavailable consumers and ambiguous
Windows namespace components fail before mutation. Positive ownership retains
all recorded users across source/package/validation transitions; another schema's
needed engine cannot be removed. Legacy output is never silently adopted.
The shared `validate_namespace_path(value)` checks os.fspath before Path coercion;
`_physical_path` and new JS/TS canonical/user identity callers reuse it. It closes
an observed older-Python ordinary-path conversion loss without a second guard or
a new supported interpreter prerequisite. Affected accepted ownership boundaries
have focused preservation evidence. Interrupted multi-file application remains
fail-closed and may require a fresh root or explicit migration.

## Requirements, choices, evidence and limits

Mandatory metadata, exact methods, single actual owner, canonical source/package
provenance, immutable reports, native semantic parity, structural codec preservation
and safe preflight are operator requirements. Static ABI/table layouts, internal
build labels, local package helper layout and explicit source facade mechanics
are implementation choices. The library's previously declared frozen test dev
dependencies are permitted test setup, not an application-time prerequisite or
license to upgrade/install unrelated dependencies.

JavaScript's corrected recorded gate is **500 passed,1 skipped**, covering JS,
shared distribution/service/wheel tests and existing JS/scaffold/CLI/naming tests.
Its final shared ownership gate is **40 passed,281 deselected**; native/reference
preservation is **95 passed,3 deselected**. The skip needs symlink privilege;
actual junction tests pass. Three old Python enum-name-reservation cases were
explicitly deselected for the user's parallel policy change. Counts overlap and
are not added. Exact commands, scopes, raw logs, local package provenance and
source/package example reports are in [JS RESULTS](examples/js-oneof/RESULTS.md).
The original496-pass receipt is retained separately, not relabeled. The initial
JS36 allowlist gains one final service-correction receipt; its current exact
37-file list is separately recorded there.

TypeScript's final [owned manifest](examples/typescript-oneof/TypeScript-OwnedFiles.json)
enumerates33 Taut and28 actual shape-ts files and declares production hashes.
Its [RESULTS](examples/typescript-oneof/RESULTS.md) associates the final86-case
gate with current source:72 feature cases plus14 existing codec/runtime cases,
using stable Python3.13.5, strict tsc7.0.2 transpilation and Node24.22.0.
Actual library typecheck/build (including CLI) pass with frozen declared
TypeScript5.9.2/@types/node24.3.0 test dependencies, unchanged lock/dependency
maps, and315 Node tests passing with zero failures/skips. Source/package examples
produce identical results. Real packed/extracted library compositions exercise
same-owner CJS/ESM classes/state, independent enabled/disabled artifacts and
source/package/library mixed owners, not just matching labels or equal JSON.
Failed-first78+1, pre-data79 and pre-residual84 receipts retain historical labels;
none is added to or substituted for final86.

The reconciled proposed pair list is73 Taut files (37 JS/shared,33 TS and the
three preparation records), plus28 shape-ts files. The lists do not overlap.
Preparation verifies the actual TS manifest production hashes, canonical
foundation copies/provenance, all changed/untracked paths against that precise
scope, protected user/old-artifact hashes and empty indices. No unknown production
path is silently adopted. These verified lists now have the coordinator's explicit
local staging/checkpoint authority; they are not acceptance. Post-checkpoint
tuple/prompt/verbatim-report evidence is authorized separately from production.

No new full nine-language global gate is claimed. Root coordinates any one full
matrix. Historical JVM all16 GREEN/broad1620 evidence belongs to its original
92c6894d/root07b5853c tuple, with later focused closure evidence at8682555a;
neither is current-pair evidence. The three established baseline failures are
the absent historical dev document and two Windows Go CRLF/gofmt checks. Their
original-source proofs remain intact; no baseline test is weakened.

Virtual selection remains deferred/incomplete; JS has no native JSON codec;
cross-target JS/TS native codec interchangeability is not claimed. User-owned
Enum.case work and old Python generated/wheel files are excluded/protected. The
freeze must compare their current hashes to Preparation and reconcile incoming
user work with the coordinator instead of sweeping it into this checkpoint.

## Freeze and review procedure

Both readiness reports, exact two-repo reconciliation and explicit root freeze
are present. The final Preparation is the source inventory for the authorized
local checkpoint. Capture the committed tuple after the scoped GWZ operations. Verify a final
per-file inventory and protected hashes; verify empty indices and account for
every changed/untracked path. Stage only individually enumerated authorized files
through GWZ. Any managed workspace receipt is generated by GWZ, never handwritten.
Record the exact committed Taut/shape-ts/root tuple and unchanged Python/Rust refs,
full baseline-to-source ranges and immutable snapshot hashes before dispatch.

Generate exactly two peer-blind prompts from the skill's canonical template:
Code+Surface and State, each covering the entire pair and actual library. Code
reads CLI/docs cold first, then performs the common requirement/necessity/scope
check; State independently attacks ownership, restart, races, aliases, transition
and fail-closed behavior. Both must verify the exact tuple at start/end and consume
any coordinator-required final integration evidence. Prior-root retraces and all
closure/regression duties belong within these two mandates, never a third reviewer.

File reports verbatim and merge exact-tuple verdicts. Any blocker maps to a
disposition and original-counterexample closure in one bounded merged patch.
Implementers cannot self-close. Continue originating reviewers unless material
change triggers replacement under the skill; maximum two remediation rounds.
No push, tag, release, publication or next backend follows from a local checkpoint
or GO verdict. Production remains held until explicitly coordinated otherwise.

## Remediation1 candidate amendment

Both original axes reported NO-GO on the initial tuple. Verbatim ReviewCode and
ReviewState plus the ONE RemPlan-1 govern the correction. Three P2 roots concern
actual selected TS facade exports, read-access diagnostics through known bindings,
and defensive immutable normalized constraint publication. Two P3 roots concern
TS package-builder defaults and shared JVM/ECMA help coverage. The accessor scope
interpretation difference is recorded; State owns its original-counterexample
closure, and Code independently judges the changed boundary. No implementer
self-closure or claim of unanimous discovery is made.

The original r0 gate is all16GREEN and broad 1807passed/4failed/5skipped/11deselected,
including one NEW help failure beyond baseline3. It is not corrected-source
evidence. Root directs affected closure/conformance/library/shared-preservation
checks after this localized patch rather than automatic repeat global execution.
The runtime/wire/output-mutation architecture, public instance methods, user
authoring boundaries and frozen declared dependencies remain unchanged in scope.
