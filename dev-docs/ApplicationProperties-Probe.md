# Application properties — isolated API probe

Date: 2 November 2026. Status: investigation, not an adopted Taut feature.

The operator requested cloning Taut into the GARNS workspace and exploring
application-specific properties on fields and messages. They explicitly clarified
that this is still a probe to choose the right design. Deliver an isolated DSL
experiment, a neutral-JSON metadata round trip, and a GARNS generated-Rust check.

Editable here: `probes/application_properties` and this note. The normal DSL,
model, IR versions, generators, codecs, compatibility policy and release files
remain unchanged. GARNS may change its probe scripts/tests to exercise this
experiment. No dependency pin, publication, commit or push is authorized.

Compare one reusable `annotate(F(...), app(...))` wrapper with convenience
`F(..., app(...))` and `Msg(app(...), ...)` functions. The experiment carries
namespaced JSON properties through Taut's existing declaration naming and enum
resolution. Taut treats their meaning as application-owned; the GARNS probe
interprets reference and tagged-payload rules. Builtin options remain strict.

The real IR currently reserves custom options. Do not smuggle new properties
into version 2 as though older tools support them. Use an explicitly marked
probe envelope for the round trip, then decide the production IR/version and
application compatibility policy separately if this design is adopted.

## Result

The probe succeeds without modifying `src/taut`. `taut_app_probe.py` provides
`app(namespace, value)`, a generic `annotate(definition, ...)` wrapper and
experimental F/Msg convenience functions. Annotated dataclass subclasses pass
through the existing DSL because its naming/type-resolution operations retain
subclass fields via `dataclasses.replace`. Namespaced values are copied,
JSON-checked, and duplicate namespaces on one declaration are rejected.

Nine focused tests pass. Field/message properties survive naming and enum
resolution, and an explicitly marked probe JSON envelope restores them. Standard
IR export, Rust/Python generated files and CBOR bytes remain identical to the
unannotated control. Standard codecs do not run application validation rules.
The `.taut.py` example loads through the existing Taut schema loader.

GARNS also applies this API to its real graph schema in
`garns/tools/probes/field_local_graph_rules.py` (sibling repository). After the
probe JSON round trip, these annotations generate exactly the same Rust macro
checks as the original dictionary. Five generator tests and four compiled Rust
integration tests pass, including a real scheduler-produced graph. The existing
GARNS checked-in transport artifacts still pass their drift check using this
Taut clone.

Both authoring styles are viable. The generic wrapper avoids changing F/Msg at
all; the convenience style is shorter and keeps properties next to field/type
information. Neither syntax is adopted. A production extension would still need
an official IR/version policy, a defined generator-facing property accessor,
application compatibility ownership and a decision about supported annotation
locations. The probe intentionally does not decide these by changing normal IR.
Reference predicates in the first example demonstrate closed complete graphs; pending
and generic targets need their own explicit application rules before adoption.

From this repository, run the isolated tests:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:probes/application_properties \
  python3 -m unittest discover -s probes/application_properties -p test_probe.py -v
```

From the sibling GARNS repository:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=../taut/src:../taut/probes/application_properties \
  python3 tools/probes/resolved_graph_rules.py --field-local-probe --check
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=../taut/src:../taut/probes/application_properties \
  python3 -m unittest discover -s tools/probes -p test_resolved_graph_rules.py -v
```

No production generator, codec, dependency pin or release changed. All work is
uncommitted. The workspace registration was performed by GWZ.

## Follow-on scope: self-contained generated reference validation

The operator approved a second probe after identifying that the first compiler
relied on handwritten GARNS lookup/payload knowledge. Extend only this isolated
probe and the corresponding GARNS probe inputs/tests. Explicitly declare graph
index fields, reference-key fields, tagged payload maps and reference policies.
Generate the actual typed Rust map lookup, union checks and target checks from
those facts; no handwritten GARNS-aware runtime checker may supply them. Compile
against the real generated graph records and test a strict-scheduler source
result plus malformed links/payloads/nulls. Taut production behavior, parser,
grammar, dependency pins, release files and full graph-publication coverage stay
unchanged. No commit or push requested.

## Second probe result: direct generated reference validation

`graph_contract_probe.py` now defines typed annotation constructors:

- `GraphIndex`: the exact graph map, reference record and identity-key field;
- `Tagged`: an enum discriminator and explicit enum-case -> payload-field map;
- `ReferenceCheck`: the graph context and generated function name;
- `GraphLink`: an exact index, ordered target-case path, null policy and explicit
  rejection policies for missing targets, invalid payloads and wrong categories.

`GraphRules` attaches union/reference-entry declarations to a message. No record,
index, identity field, discriminator or payload name is supplied by a handwritten
application runtime helper. The probe compiler validates these facts against the
Taut field/map/reference/enum types and emits the Rust lookup, payload selection
and target checks directly. A macro layer was unnecessary for this experiment.

Seven focused tests pass in `test_graph_contract.py`. They reject missing index
contracts, missing keys/cases, incomplete union maps, contradictory null policy
and annotated links with no check entry. Crucially, a graph with unrelated names
(`Registry.catalog`, `Pointer.token`, `Cell.which`, `object_data`, `text_data`)
is generated with the ordinary Taut Rust generator. The generated validator is
compiled with rustc and executed against valid, missing, mismatched-payload and
wrong-target cases. Thus the compiler cannot be relying on GARNS's node-table,
identity-field or payload naming conventions.

The sibling GARNS `explicit_graph_contract.py` declares the corresponding facts
for its real record schema, round-trips those annotations through the probe JSON
envelope, and emits `direct_rules_probe.rs`. Four compiled integration tests
pass against a strict-scheduler source graph and malformed copies. They cover
outer and nested union integrity, scalar/authored record type links, null-as-
absence versus required references, missing targets and wrong categories. The
Rust integration test supplies no handwritten validator, macro or GARNS-aware
runtime host. The generated code's error enum and lookup/union functions are
part of the generated artifact. The direct-output drift check passes.

This closes the requested fully specified *reference case*. It does not prove
all graph rules are declared or implement language evaluation, cycle rules,
binding admission, sequence integrity, state-dependent root policy, graph
publication or the entire semantic graph. The required-type-root test entry is
explicitly for the completed type-root case; it is not applied universally to
pending, failed or world roots. Existing graph-import validation is unchanged.
The API remains isolated and unadopted; all work remains uncommitted.

Reproduce the second probe:

```sh
# Taut member:
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:probes/application_properties \
  python3 -m unittest discover -s probes/application_properties -p test_graph_contract.py -v
# GARNS member:
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=../taut/src:../taut/probes/application_properties \
  python3 tools/probes/explicit_graph_contract.py --check
# GARNS native workspace:
cargo test -p garns_resolver --test resolved_graph_direct_rules_probe --locked
```


The readable, self-contained authoring example is now
`probes/application_properties/graph_contract.taut.py`. It declares its own
minimal graph/index/reference/union/type-link contract and generates lookup code
without a companion rule table. It is a small illustrative schema, not a
replacement for GARNS's authoritative graph schema. The seventh compiler test
loads this actual file and checks its generated lookup and nested type selection.

## Ownership direction from the operator

The operator identified discriminated oneof as a deferred generic Taut feature
and directed that its declaration and generated validator belong in Taut, rather
than in GARNS application metadata. `Tagged` in the present probe represents that
oneof constraint; it is not a separate graph-domain feature. `ReferenceCheck`
currently names a generated checking function and its graph context. Graph-index,
reference-key and allowed-target rules remain the application-specific part of
this probe. This records the intended separation; native production oneof/IR/
codecs have not been implemented or adopted by this documentation amendment.

## Field-local oneof syntax proposal — not implemented

The operator requested reducing boilerplate by putting oneof membership on each
payload's F declaration and referencing an existing tag field. Candidate syntax:

```python
NodeRecord = Msg(
    tag=F(1, Ref.NodeTag),
    declaration=F(2, Ref.DeclarationRecord,
                  Case("tag", "declaration"), optional=True),
    value=F(3, Ref.ValueRecord,
            Case("tag", "value"), optional=True),
    next_id=4,
)
```

`Case` is a proposed generic Taut rule, not an implemented API. Its first argument
names a discriminator field of the same message; the second names a member of
that field's enum. The containing Msg supplies grouping, the enclosing F supplies
the payload field and type, and the discriminator F supplies its enum. The
compiler can assemble the case map internally. There is no separate GraphRules
or Tagged wrapper to author for this oneof.

The explicit optional=True keeps the prototype's existing nullable inactive-slot
representation visible; it does not make the selected payload optional. Inferring
that storage presence from Case is a separate authoring/encoding decision. Empty
variants, partial enum coverage, multiple groups and unknown future tags still
need explicit policies before a production oneof feature is adopted. The user
has not authorized promoting the probe to production.

## Revised validation API proposal

The operator requested caller-controlled validation and a revised proposal before
adopting any public API. See `OneOf-ExplicitValidation-PROPOSAL.md`. It recommends
field-local Case declarations, standalone generated validator modules, portable
validation reports and no implicit semantic validation in constructors, mutation
or codecs. The Case API and report model are proposed, not implemented public
Taut features. The existing direct Rust graph probe now has five passing tests,
including invalid draft -> existing codec round trip -> explicit failure ->
repair -> explicit success -> later mutation -> explicit failure. The validator
is observational; no success is cached across mutation. No production Taut source,
wire behavior, dependency pin, release or application graph boundary changed.

## Explicit OneOf discriminator clarification

The operator clarified the desired syntax: the tag field itself says
`OneOf(Ref.Enum)` and payload F declarations nominate that field plus an enum
choice with Case. The revised proposal includes a self-contained generic
Content example and the GARNS NodeRecord shape. An executable version lives in
`oneof_fields.taut.py` with isolated helpers in `oneof_fields_probe.py`; generated
standalone Rust validation is inspectable in `oneof_fields.validation.rs`.
Six focused syntax/normalization/lifecycle checks pass; generated Rust compiles
and runs, the artifact drift check passes, and seven earlier explicit-contract
checks pass. This is still a probe: no production Taut DSL/IR/API was changed,
and the portable report/Python validator APIs remain proposed. See the revised
proposal for limitations, normalization requirements and reproduction commands.

## Enum-object and keyword case references

The operator requested naming the enum outside schema, using the enum object in
OneOf and qualified members in keyword Case nominations. The executable example
now uses OneOf(ContentKind) and Case(kind=ContentKind.text). Probe enum objects
expose qualified members; normalization verifies enum ownership, not merely a
member-name string. Nine syntax checks pass, including wrong-enum same-name
rejection and keyword nomination validation; generated Rust drift is unchanged.
The revised proposal compares Protobuf's implicit active member with this
explicit-discriminator, caller-validated design and cites the official guide.
Enum-object attribute-name collisions remain an explicit prototype limitation.
No production Taut source/IR/API, codec behavior or dependency pin changed.

## Authorized continuation: standalone validator API probe

The operator resumed implementation after the syntax-only discussion. Continue
only the isolated probe: generate separate Rust/Python validator modules from
the same normalized oneof rules, give them matching code/path results, test
explicit invocation and mutable-draft repair, and keep virtual-group validation
deferred. Editable: this probe directory, proposal/evidence notes, and GARNS's
continuation log. Production `src/taut`, official IR versions, normal codegens,
wire codecs, dependency pins, releases and GARNS production resolver remain
reference-only. No commit or push requested. This is not authorization to adopt
the probe as a production public API or complete Rust graph publication.

## Standalone Rust/Python validation report probe complete

After the operator resumed implementation, the probe now emits separate callable
Rust/Python validation modules with common report semantics. `oneof_reports_probe.py`
consumes the normalized Case/OneOf rules and emits `oneof_fields.reports.rs` and
`oneof_fields.reports.py`. No new constructor/codec call sites invoke them.
ValidationReport has is_valid() and snapshot issues with code/path/message.

All 37 focused tests pass. Fifteen shared cases match across the compiled Rust
and generated Python validators, including multiple errors, selected nested
payloads, explicit repair, stale-report snapshots and zero/false/empty/unit data.
Virtual discriminators are absent from records/wire and virtual-only validators
are not generated. The first cut does not infer or validate virtual groups.
Unsupported nested constraint containers/wrappers fail generation explicitly.
The older and report validator artifacts pass drift checks; normal GARNS Taut
record generation also passes drift. The implementation remains isolated and
uncommitted. See the revised proposal for exact scope and reproduction commands.

## Coverage switch and removal of standalone cases

The operator requested OneOf(..., exhaustive=False/True) and rejected free-hanging
Case declarations. The isolated probe now defaults exhaustive to False, inferring
payload-free choices for unmatched enum values. True requires every member to be
nominated on a payload field. Msg rejects standalone Case; virtual storage remains
independent and virtual runtime validation remains deferred. Normalized probe
metadata preserves the option and inferred members. All 42 focused tests pass,
including the same 15 Rust/Python conformance cases with implicit unit choices.
The proposal and inspectable generated validators are updated. No production Taut
or GARNS resolver changes, commit or push.
