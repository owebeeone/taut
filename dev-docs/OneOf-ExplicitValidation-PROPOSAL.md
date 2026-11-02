# Oneof and explicit validation — revised proposal

Date: 2 November 2026. Status: proposal and isolated probes; not an adopted public API.
The fast-check, traversal-scope, instance-method, mandatory-descriptor and compiler-generation amendments postdate
the earlier review acceptance and require review of this revised document.

This incorporates the operator's requirements: reduce authoring boilerplate,
make oneof a generic Taut feature, share validation rules across languages, and
let callers construct and repair invalid drafts before explicitly validating.
Sections 1–4 are the current normative proposal. The appendix records historical
probe results and limitations; it does not override those sections. The preceding
graph-rule probes remain evidence, not the proposed public API.

## 1. Field-local oneof declarations

Proposed production syntax, with an explicitly marked discriminator:

```python
from taut.ir.dsl import INT, STR, Enum, F, Msg, schema, OneOf, Case

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

This is the requested three-way association:

1. `OneOf(ContentKind, virtual=False, exhaustive=False)` declares that **kind is a oneof
   discriminator** whose choices come from ContentKind. With the default
   non-virtual mode, its generated runtime field remains a required enum and
   retains the existing enum wire representation.
2. `Case(kind=ContentKind.text)` declares that **this payload belongs to kind's text
   choice**. The keyword nominates the field; the qualified member reference
   carries its enum identity and choice. The enclosing F provides the payload's
   name and type. Neither nomination is an unqualified string.
3. Msg provides the enclosing scope. Fields naming the same discriminator form
   its oneof group. Two discriminator fields using the same enum remain distinct
   groups; grouping is by controlling field, not by enum type.

### Virtual discriminator option — first-cut boundary

```python
# Real required discriminator: stored, serialized and explicitly validated.
kind=F(1, OneOf(ContentKind, virtual=False))

# Logical discriminator only: no runtime field, no wire field, no validation yet.
kind=F(1, OneOf(ContentKind, virtual=True))
```

`virtual` is a Boolean parameter, default False. Payload Case nominations stay
identical in both modes: they refer to the logical field in the schema. A virtual
discriminator is not an optional or private runtime attribute. It is removed from
the generated data model and wire projection; existing payload field numbers
remain unchanged. The probe verifies that accessing draft.kind fails to compile
in Rust for a virtual-only message. The enum type can still exist in the API;
there is simply no discriminator *value field* on that record.

Only non-virtual groups are validated in the first cut. A message with only
virtual groups AND no reachable owned non-virtual constraints has no standalone
validator. Local virtual groups do not suppress a root validator needed to
traverse non-virtual descendants. No inference, mutual-exclusion check or externally
supplied expected-kind argument is implemented for a virtual group. Validation
of such groups is deferred, not reported as a successful no-op. Schema-definition
checks (valid enum, case nominations and coverage) still apply to virtual groups.
Changing a previously stored discriminator to virtual removes a runtime/wire
field and must be surfaced as a deliberate compatibility change. The default
False mode preserves the previous non-virtual layout and validator output.

### Exhaustive case coverage — independent schema option

`exhaustive` is a Boolean parameter, default False in the proposed public API:

```python
# Unmentioned enum members implicitly carry no payload.
kind=F(1, OneOf(ContentKind, virtual=False, exhaustive=False))

# Every enum member must be associated with a payload field.
kind=F(1, OneOf(ContentKind, virtual=False, exhaustive=True))
```

In the primary example, `empty` has no Case nomination. With exhaustive=False,
selecting it is valid only when all this group's payload fields are absent.
Standalone Case rules are not part of the proposed syntax. With exhaustive=True,
every enum member must be nominated by a Case on a payload field; an unmatched
member is a schema error. To allow an unmatched, payload-free member, use
exhaustive=False instead.
This is schema coverage, not a requirement to populate every payload at runtime.
Unknown enum choices, wrong enum ownership and duplicate case ownership remain
errors in both modes. An enum with no alternatives is also rejected.

The options are independent. Exhaustive coverage is checked even for virtual
groups, but virtual runtime validation remains deferred. The normalizer records
the coverage option and inferred payload-free members in explicit probe metadata
and supplies a complete case map to both validator generators. This changes the
earlier probe's default coverage policy; authors wanting its former strict
coverage must now write exhaustive=True. It does not change record/wire layout.

For the GARNS records, the same shape is:

```python
NodeRecord = Msg(
    tag=F(1, OneOf(NodeTag)),
    declaration=F(2, Ref.DeclarationRecord, Case(tag=NodeTag.declaration)),
    value=F(3, Ref.ValueRecord, Case(tag=NodeTag.value)),
    next_id=4,
)
```

There is no separate GraphRules, Tagged, manual case map or generated-function-
name declaration for intrinsic oneof. Case must refer to a field explicitly
marked OneOf, not just an arbitrary enum field. The compiler checks both the
field nomination and membership in that field's enum. Unknown tag fields, unknown
enum choices and duplicate ownership are errors in both coverage modes. Missing
case coverage is an error only in exhaustive mode. These constructors remain experimental and are not production imports.

Recommended storage rule: Case implies a nullable payload slot, so optional=True
need not be repeated. That is storage for inactive cases, not permission to omit
the selected payload when validating. This must be visible in normalized IR.
Adding Case to an already nullable field keeps its CBOR encoding but changes
canonical JSON output for absent payloads from explicit null to omission. Adding it
to a previously non-nullable field changes presence and must be reported by the
existing compatibility gate; the shorthand must never hide that change.

At schema compilation, require an existing non-nullable OneOf enum discriminator,
members belonging to the nominated enum and unambiguous case ownership. Require
complete explicit payload-field coverage only when exhaustive=True. Payload-free
enum members are inferred when exhaustive=False, without a free-hanging Case:

```python
# Any NodeTag member not nominated by a payload field has no payload.
NodeRecord = Msg(
    tag=F(1, OneOf(NodeTag, exhaustive=False)),
    declaration=F(2, Ref.DeclarationRecord, Case(tag=NodeTag.declaration)),
    value=F(3, Ref.ValueRecord, Case(tag=NodeTag.value)),
    next_id=4,
)
```

Each enum choice selects one payload field or, in non-exhaustive mode, an inferred
payload-free case. Case is accepted only on a payload F, never directly in Msg.
Multiple case annotations may select the same payload field if they use the same
discriminator. A payload may not depend ambiguously on different tag fields.
Production generation must support multiple independent groups in one message;
validation checks each group independently. The single-group restriction in the
probe is not a production scope limit. Unknown enum values retain the existing
codec rejection policy; a newly declared known member is payload-free by default
in non-exhaustive mode, but needs a payload nomination in exhaustive mode.

The compiler assembles the normalized discriminator/case map internally. Portable
IR must retain that rule so each language generates from the same facts. Do not
infer semantic grouping from field names or silently drop rules in an old IR.

## 2. Construction, codecs and validation are separate

Keep the existing owned record/struct model and constructors. Invalid *oneof
combinations* must remain representable during assembly. Do not replace every
record with a language-specific enum/sealed hierarchy that forces immediate
validity or changes the existing public construction API.

Neither constructors, mutation, encode nor decode automatically run the new
semantic validator. Existing structural wire checks remain unchanged: malformed
CBOR, invalid primitive types, missing ordinary required keys, depth/size limits and
unknown enum values still follow Taut's existing codec contract. This proposal
adds caller-controlled semantic checks; it does not disable codec checks. The
oneof payload-presence encoding change below is explicit, not an unchanged-codec claim.

### Sparse oneof payload encoding — proposed, not yet implemented

In JSON, omit every absent oneof payload rather than writing its key with null.
Keep populated payloads. Presence means non-null, not truthiness: zero, false,
empty strings and empty collections are present and must be emitted. Ordinary
nullable fields retain their current encoding; this rule is specific to fields
associated with a oneof Case.

For a valid number choice, the non-virtual form includes the stored discriminator:

```json
{"kind":"number","number":"42"}
```

For the corresponding virtual group, no discriminator exists in the record or
wire representation, so populated payloads alone determine the emitted fields:

```json
{"number":"42"}
```

The quoted integer follows Taut's existing JSON i64 mapping. Neither form emits
the absent text payload. Missing payload keys decode into absent slots; readers
also accept an explicit null for a payload as absent, allowing the older dense
JSON representation to be read. A non-virtual discriminator stays required.
Do not synthesize a virtual tag on import: presence identifies the payload slot,
not necessarily a unique enum member when several members share a payload.

A well-formed value with a populated payload emits one group payload. A
payload-free choice emits none. This is not an implicit validation/repair step:
if a draft has several populated payloads, emit all of them, preserving the
inconsistency for caller-controlled validation. Never select a winner or drop
populated data based on the discriminator. A missing selected payload remains
absent on the wire and is diagnosed when the explicit validator is called.
Virtual-group runtime validation remains deferred in this first cut.

This revision specifies JSON omission. It does not silently change the existing
dense CBOR encoding; sparse CBOR would need an explicit format decision and
compatibility evidence. Canonical JSON output for new oneof declarations changes
from null-valued keys to omitted keys, while existing dense JSON remains readable.
Unannotated records keep their existing wire behavior. All nine supported language
backends must implement these rules and equivalent explicit validation reports;
a Rust/Python-only rollout does not complete the requested Taut feature.

Acceptance covers both discriminator modes, no/one/multiple populated payloads,
zero/false/empty data, dense-input acceptance, omitted-input acceptance, draft
round trips, and matching behavior across all nine languages. This section is
a production proposal revision; the isolated codecs still emit explicit nulls.

Oneof validation is observational. It does not repair, freeze, resolve, normalize
or mutate the supplied records. It checks the current contents at the instant of
that call. A later mutation requires another explicit call if the consumer wants
a fresh result; never cache success against a mutable object without a revision.

Example of the intended lifecycle (proposed API):

```python
draft = NodeRecord(tag=NodeTag.declaration)   # selected payload not set yet
# Further construction or repair is allowed here.
draft.declaration = declaration
report = validators.validate_node_record(draft)
assert report.is_valid()
```

Taut transport records remain mutable. An application may explicitly validate
and publish a read-only graph at its own boundary. GARNS's existing Rust graph
publication/import policy and read-only views are not weakened by this proposal.

## 3. Opt-in generated instance validators

The operator now selects instance methods on each eligible message: validate
returns the general diagnostic report and is_valid/isValid the Boolean fast check,
with local/recursive scope available on both. Generate them only when requested.
Report types and internal helpers may remain in a separate module. This replaces
the earlier free-function/static entry-point proposal across all nine targets.
Exact per-language method spellings and TypeScript projection considerations are
in the build proposal, section 7. Member-name collisions are schema-generation
errors for the opted-in projection, not grounds for silently renaming methods.

Validator source generation is opt-in: tautc gen --with-validation, default off.
Programmatic generation uses validation=False by default. With generation enabled,
emit the extra module for eligible roots; generating code is not running it.
Disabling it does not disable schema checks, remove IR rules or change JSON/CBOR
behavior. Stale generated validator files must not be silently treated as current;
use safe ownership tracking or require a fresh output directory. Schemas with no new constraints must
retain their existing artifacts exactly. Existing constructors and codec entry
points keep their names, arguments and return/error types. Annotated oneof JSON
presence changes only as specified in section 2; unannotated behavior is unchanged.

Proposed Rust call shape:

```rust
let mut draft = api::NodeRecord::default();
// Fill or repair the draft using the ordinary generated record API.
let report = draft.validate();
assert!(report.is_valid());
```

Proposed Python call shape:

```python
report = draft.validate()
if not report.is_valid():
    inspect(report.issues)
```

Invalid data returns a report rather than throwing a validation exception or
preventing construction. Recommend a portable ValidationReport with issues;
validity is derived from an empty issue collection. Each issue has a stable code,
structured field/index/map-key path and human-readable message. Code and path,
not message matching, are the portable diagnostic contract. Exact report type
names remain provisional rather than adopted production APIs. The earlier
Result-returning probe is retained as comparison evidence. The new isolated
report probe implements ValidationReport in both Rust and Python with explicit
calls and matching code/path results; see the implementation section below.

ValidationReport contains issues and deferred_checks, both immutable snapshots.
Each deferred entry carries a path and rule identifier. is_valid() means no
issues were detected in the checked scope; is_complete() means deferred_checks
is empty. A caller claiming full validation must require both. A mixed message
records a deferred entry for each encountered virtual group, even when its
non-virtual checks pass. Generate a standalone validator for any message whose
owned schema-reachable contents include non-virtual constraints, through ordinary
fields, virtual payloads, lists or maps. Compute reachability over the schema
without looping on recursive types. A message lacking all such reachable checks
has no standalone validator in this cut; a containing validator still records
its encountered deferred virtual groups. Thus virtual-only here means the entire
reachable owned schema, not just the root's locally declared groups.
These coverage facts do not turn on virtual validation or infer a discriminator.

Collect every independently detectable failure, rather than stopping at the
first. Traverse multiple groups and all populated owned nested records, including
ordinary fields and list/map elements. A wrong or absent discriminator produces
an issue at that field; skip that group's selection-dependent checks, but continue
other groups and populated nested records. For a known discriminator, report
missing selected and populated nonselected payloads; also validate the nested
contents of any populated payload, selected or not. An absent nested slot has no
contents to traverse. Do not follow application node-ID links as ownership edges.

Order checks by field number, with each group's checks at its discriminator's
position and each owned child traversed at its field position. Within a group,
order payload issues by payload field number. Lists use ascending zero-based
indices. Maps use the lexicographic unsigned-byte order of each key's canonical
Taut CBOR encoding, independent of host map iteration order. Paths use typed
Field(schema name), Index(zero-based index), and Key(key type, canonical key
encoding) segments. Do not use generated-language field names in paths.
Multiple paths to a shared owned object yield issues at each path. Recursive
schemas are allowed; for a runtime ownership cycle, detect an object already on
the active ancestor path, report validation.ownership_cycle at the back edge,
and continue independent branches. No global visited-set skipping may hide a
second path's issues. Languages whose owned model cannot represent such a cycle
need not manufacture one. Ordinary runtime resource exhaustion remains outside
the invalid-data report guarantee.

Validators use the deterministic traversal above and report their checked
scope explicitly. They do not rerun the compiler. Intrinsic oneof checks require
only the record. Graph-reference rules need the owning graph/index and belong
to an application-specific validator. An application-level graph validator may
compose Taut's local validators with those graph checks, at a caller-selected
point. Shared targets must not be recursively revalidated once per incoming
reference; visit owned nodes once and validate links against the index.

### Operator amendment: fast checks and selectable traversal

Each eligible type exposes both a report-returning validator and a Boolean fast
check. The fast check short-circuits without constructing all diagnostic records;
for the same scope it returns exactly report.is_valid() AND report.is_complete().
Both functions accept recursive traversal selection, default True. With False,
check only rules declared on the supplied record, including local payload presence
and local deferred checks; do not validate contained records or collection elements.
With True, use the full owned traversal described above. ID references are never
followed. Scope is recorded as local/recursive in each report. Completeness and
validity apply to that requested scope; intentionally excluding descendants in
local mode is not deferred coverage. No caller should infer whole-tree validity
from a local result. Per-language exact call shapes and generation options are in
OneOf-ExplicitValidation-BuildProposal.md; they remain draft APIs.

The following root-traversal acceptance case uses the default recursive scope.

### Required root-traversal acceptance case

Define Root with only a local virtual group, whose payload owns Child with a
non-virtual oneof. Root must receive a validator. With Child's selected payload
missing, the report includes its root-relative missing-payload issue and Root's
deferred virtual-group entry. Repairing Child yields is_valid() == true and
is_complete() == false. Replacing Child with unconstrained scalar data leaves no
reachable non-virtual checks, so that genuinely virtual-only root has no standalone
validator. Apply the same eligibility rule through ordinary wrappers, containers
and recursive schema references across all nine targets. No virtual case selection
or mutual-exclusion validation is added by this traversal requirement.

## 4. Ownership and compatibility

Taut owns Case, oneof normalization, generic validation constraints and generated
validators. Application annotations remain a separate experimental facility.
GARNS owns which fields are node references, which graph resolves them and what
targets are permitted. Oneof must not be encoded as a GARNS metadata convention.
ReferenceCheck's function-name boilerplate is unnecessary for native oneof;
normal validator names can derive from message names.

Keep wire compatibility, generated-API compatibility and validation acceptance
separate. Adding a rule can reject values only when a caller chooses to validate;
the oneof JSON presence change is an explicit format policy, while unannotated
codec behavior remains unchanged. Nevertheless, adding or
narrowing rules is a validation-contract change and must be surfaced, not labelled
meaningless metadata. Classify CBOR wire changes, JSON projection changes, API
changes and validation-contract changes separately; do not claim that adding a
Case is universally encoding-neutral.

A versioned neutral-IR extension is required for native constraints. Recommend
using a new IR version when these rules are present so older tools reject it
rather than discard them; preserve current version-2 output for schemas without
new features. The exact version/IR layout remains a design decision. Keep current
codec implementations and checked-in generated artifacts stable during probing.

## Appendix — historical probe evidence, not normative requirements

The sections below are chronological snapshots. Counts and statements about
missing functionality describe their stage, not the final production scope.
The latest checkpoint is the coverage-switch revision at the end.

### Initial graph and lifecycle probes

Existing evidence: field/message-local metadata survives normalization and an
explicit probe JSON round trip; direct generated Rust checks work with both a
real scheduler-produced graph and a differently named graph. They do not rely on
a handwritten GARNS lookup helper. These are graph-integrity probes, not a
complete validator API or complete Rust graph publication.

The follow-on lifecycle test now constructs an invalid oneof in mutable real
transport records, round-trips it through the unchanged Taut record codec,
explicitly observes validation failure, repairs the same draft and validates
success. It then mutates it again and observes failure on the next call.
Validation leaves the records unchanged throughout.

Next probe deliverables: implement field-local Case in Taut's development DSL/
normalized model; generate separate Rust and Python validator modules; compare
portable issue codes/paths on the same valid and invalid fixtures; prove unchanged
unannotated artifacts and wire bytes; exercise invalid -> repair -> validate and
serialization before validation. Explicitly test false/zero/empty payload values,
unit cases, repeated calls, nested constraints and multiple discriminator groups.
No production rollout, release, commit or push is authorized by this proposal.

Additional lifecycle evidence: the unrelated-name Taut-generated Rust harness
also encodes the invalid draft to actual CBOR bytes and decodes it successfully
before calling the semantic validator. After repair, explicit validation succeeds
without mutating the input. The seven focused Taut compiler/harness tests and
five GARNS Rust integration tests pass. This proves the proposed separation of
codec and validation timing; the new Case syntax and portable report API remain
proposal work, not implemented production features.

## Executable explicit-discriminator syntax probe

The operator clarified that the tag must itself be explicitly declared as a
oneof over a particular enum. That exact syntax now has an isolated executable
example at `probes/application_properties/oneof_fields.taut.py`, importing the
experimental F/Msg/OneOf/Case helpers from `oneof_fields_probe.py`. The proposed
production imports shown above still do not exist in `taut.ir.dsl`.

OneOf is unwrapped to the original enum type for ordinary generated data and
wire encoding; its source marker requires explicit Case nominations. Case
implies nullable payload storage. The probe normalizes those declarations into
the earlier explicit constraint model internally, without an authored GraphRules
or Tagged wrapper. It then emits a separate callable Rust validator; inspect
`probes/application_properties/oneof_fields.validation.rs`. No constructor or
codec calls that validator automatically. The result is currently a Rust Result,
not the proposed cross-language report API.

Six focused tests pass, including compiling and executing generated Rust. They
cover marked-enum association, same-record case nomination, invalid enum/field
references, duplicate or incomplete coverage, normal record-layout equivalence,
normalized probe-JSON retention, explicit validation, wire round trip before
validation, zero/false/empty text and a payload-free unit choice. The validator
artifact passes its regeneration check. Seven existing explicit-contract probe
tests also pass after extending union generation to support scalar payloads.

Limits: this syntax is an isolated DSL shim, not native production Taut support;
raw standard IR export does not retain the new source markers. The probe must
normalize them before its explicit probe-IR export. Multiple discriminator groups
are explicitly rejected by this first prototype. Native IR support, multiple
groups, Python validator generation and the report API remain next work. The
normal Taut compiler, codec and dependency pin are unchanged.

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:probes/application_properties \
  python3 -m unittest discover -s probes/application_properties -p test_oneof_fields.py -v
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:probes/application_properties \
  python3 probes/application_properties/oneof_fields_probe.py --check
```


## Qualified enum-object references and Protobuf comparison

The operator requested referencing the enum object and its members directly,
defining it before the schema call. The executable probe now uses
`ContentKind = Enum("ContentKind", ...)`, passes that object to `OneOf`, includes
it in `schema`, and writes `Case(kind=ContentKind.text)`. The keyword nominates
the owning field. A qualified member carries the enum declaration and member;
using another enum's same-named member is rejected. Unknown members fail on
attribute access. The earlier positional/string spelling remains a historical
comparison input only. Nine focused syntax tests now pass, and validator
regeneration produces the same Rust file.

Protobuf's [oneof guide](https://protobuf.dev/programming-guides/proto3/#oneof)
defines a group of member fields, not a separate user enum/discriminator field:

```protobuf
message Content {
  oneof payload {
    string text = 1;
    int64 number = 2;
  }
}
```

The numeric field tags remain required. Which member is present identifies the
active case, and no member may be set. Setting one member clears its siblings;
parsing multiple different members retains the last encountered case. The
current Taut proposal instead keeps an explicit enum field and independently
mutable nullable payload slots, with caller-selected validation and no automatic
clearing. It requires the selected payload (or an inferred payload-free choice in
non-exhaustive mode); adopting
Protobuf's unset semantics would be a separate policy decision. These are
intentional API/validation differences, not assertions that Protobuf needs an
optional discriminator field.

Confirmed nonblocking prototype limitation: enum member names colliding with
the definition object's own attributes (for example members/name/options) are
rejected rather than returning the wrong object through dot access. A focused
test covers this. A production referenceable-enum API needs an unambiguous escape
or namespace policy for such names. This does not block ContentKind.text/number;
no core DSL change for that follow-up was made.

The ninth syntax check invokes the generator in a fresh Python process, covering
qualified enum-member references through the command-line regeneration route.
The generated-validator drift check passes as well.


## Standalone report API implementation — isolated probe

The operator resumed validation implementation after specifying virtual modes.
`oneof_reports_probe.py` now emits separate Rust and Python validator modules
from the same normalized rules. Inspect `oneof_fields.reports.rs` and
`oneof_fields.reports.py`. The original data/codec generators do not import or
invoke those modules. Runtime callers explicitly use:

```python
from . import api, validation

draft = api.Content(kind=api.ContentKind.text, text=None, number=None)
report = validation.validate_content(draft)
assert not report.is_valid()
assert report.issues[0].code == "oneof.payload_missing"

draft.text = "ready"
assert validation.validate_content(draft).is_valid()
assert not report.is_valid()  # previous report is a snapshot
```

```rust
let mut draft = api::Content::default();
let report = validation::validate_content(&draft);
assert!(!report.is_valid());
draft.text = Some("ready".to_owned());
assert!(validation::validate_content(&draft).is_valid());
assert!(!report.is_valid());
```

The report has is_valid() and a read-only issue collection (issues() in Rust,
issues in Python). Issues carry code, structured path and message. Missing and
unexpected payloads have distinct codes and all applicable payload issues are
collected in field declaration order. Selected direct nested oneof payloads
extend the path. Invalid data is a report, not an exception/panic. Python also
reports an invalid discriminator/record rather than crashing during dispatch.
Validation leaves input records unchanged and reports retain no mutable input
references or cached success across edits.

Scope: checks declared non-virtual oneof groups and selected direct nested oneof
payloads. It is not a replacement for codec type checks or GARNS graph-reference
validation. Multiple groups remain outside the syntax prototype. Containers or
non-case wrappers containing nested oneof constraints are rejected by this report
probe's generator rather than silently skipped. Virtual groups receive no runtime
validation, including no automatic mutual-exclusion inference. These limitations
prevent claiming this is already a complete production validation API.

Evidence: all 37 focused probe tests pass. Fifteen shared fixture cases produce
identical Rust/Python validity, issue codes, paths and messages. The compiled
Rust harness and Python checks exercise invalid -> serialize -> repair ->
explicit validation, stale-report snapshots, zero/false/empty/unit payloads,
multiple errors and nested paths. Both languages omit virtual discriminator data
and no virtual-only validator is emitted. Ordinary type/codec artifacts are
unchanged; older and report validator drift checks pass. No broad resolver or
multi-language Taut release suite was rerun.

Reproduce from the Taut member:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:probes/application_properties \
  python3 -m unittest discover -s probes/application_properties -p 'test_*.py' -v
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:probes/application_properties \
  python3 probes/application_properties/oneof_reports_probe.py --check
```

This completes the bounded validation API probe, not production DSL/IR adoption
or full Rust graph publication. Normal Taut source, official IR, normal generators,
codec behavior, dependency pins and release files remain unchanged. No commit or
push was requested or performed.

## Coverage-switch revision — current probe result

The operator requested a coverage option and rejected free-hanging Case rules.
The current isolated API is OneOf(enum, virtual=False, exhaustive=False).
Both options require actual Boolean values. Every Case must be on its payload F.
With exhaustive=False, unmentioned enum values implicitly select no payload;
validation rejects any populated payload field in that group. With exhaustive=True,
all enum values must be nominated by payload fields or schema normalization fails.
There is no standalone payload-free declaration. This supersedes the earlier
explicit-coverage/unit-declaration experiment described in historical evidence.

The primary example and shared fixture now exercise implicit payload-free choices.
Normalized probe metadata retains exhaustive and the inferred member list across
JSON transport. Ordinary data and codec generation do not change for the same
field/enum definitions. Virtual controls storage independently; exhaustive schema
checks apply in either storage mode, while virtual runtime validation stays deferred.

All 42 focused probe tests pass, including the 15 common Rust/Python report cases,
strict/permissive coverage, virtual combinations, rejected standalone declarations,
and metadata round trips. Generated validator drift checks pass. Only isolated
probe code, generated probe artifacts and evidence notes changed. Production Taut,
GARNS resolution and dependency pins remain unchanged. Nothing is committed/pushed.


## Latest operator amendment — mandatory descriptors and versioned generation

All newly generated Taut messages must publish a descriptor regardless of whether
--with-validation is requested. The flag controls optional instance validation
methods, not descriptor availability. Recursive validation uses child descriptors,
so a dependency does not need its own optional validation methods. No shared base
class or runtime capability-discovery interface is required by this choice.

The operator explicitly accepts corresponding golden changes, superseding the
previous byte-identical old disabled-output requirement. New enabled/disabled
golden tracks share mandatory descriptors; disabled output omits validation methods.
Older dependencies must be regenerated or explicitly adapted, never silently skipped.
A distinct Taut C release and explicit generated descriptor-contract version must
distinguish old/new artifacts. Release numbering follows the repository's existing
policy; no release or version change is performed by this proposal. Details and
migration acceptance are in build proposal section 13. This operator amendment
supersedes earlier descriptor-optional wording; it has not passed the prior review.
