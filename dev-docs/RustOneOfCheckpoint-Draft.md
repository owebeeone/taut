# Rust OneOf checkpoint — draft and review object

Status: implementation source frozen for a dual Code+Surface / State review.
Acceptance and GitHub publication are not claimed by this draft. The exact source
tuple is supplied by the checkpoint commit and the generated reviewer prompts.

Authority: [RustOneOfCheckpoint-Authority.md](RustOneOfCheckpoint-Authority.md)
records the original implementation directive, the Python freeze/clearance,
current commit/push authorization and no-release boundary. The controlling design
is [OneOf-ExplicitValidation-BuildProposal.md](OneOf-ExplicitValidation-BuildProposal.md),
with its old documentation-only/no-implementation/Python-first stop superseded by
that directive. Python's accepted implementation is reference evidence, not a
substitute for the operator's requirements. Applicable repository rules are the
workspace AGENTS/AGENTS_GWZ, Taut AGENTS and taut-shape-rs AGENTS. There is no Taut
CurrentProgramCheckpoint/AgentProcessRules file. Review process is the installed
`review-loop` skill, with two peer-blind axes and at most two remediation rounds.

Review tier: dual, because this freezes public generated APIs, descriptor/access
ABI, runtime distribution and filesystem ownership. The lane owner drafted the
implementation; reviewer agents are read-only, independent and restricted to the
committed object plus explicitly allowed isolated test outputs.

## Observed problem and resulting behavior

The accepted Python batch supplies native OneOf/Case, versioned rules/IR, facts,
descriptors, validation, safe generation and Python library/runtime composition.
Rust lacked mandatory metadata, typed adapters and explicit validation. Its source
runtime copy route lacked the new ownership lifecycle, and the Rust shape library
compiled a separate private CBOR implementation. The Rust change fills those gaps
through the existing compiler, reuses native semantics and preserves codecs as
independent structural operations. It does not implement another schema compiler.

Every newly emitted owned Rust message now publishes descriptor/binding accessors.
Validation-enabled output adds the exact four required instance methods on every
owned message. Disabled foreign children keep their own metadata/adapters; parents
do not add foreign inherent methods. Invalid drafts stay mutable and can round-trip
through existing codecs before repair. Zero, false, empty scalar/collection values
are present. Nonexhaustive unmatched choices are payload-free. Local checks exclude
children; recursive checks visit all populated owned paths, including nonselected
payloads. Virtual groups remain deferred/incomplete and still permit supported
child traversal. Reports own snapshots, and both sinks share the same predicates.

## Concrete ABI and owner

The isolated Limbo ABI probe was specified/run before production integration and
re-probed for owned facts, immutable static references and higher-ranked scalar
borrows. The actual final backend additionally compiles positive/negative lifetime,
typed-pairing and cross-crate probes through the production emitter.

`SchemaBinding<T>` owns one immutable MessageDescriptor and function pointers for
dependency publication checks, `for<'a> fn(&'a T, usize) -> FieldState<'a>` and
synchronous child traversal. `PrimitiveValue<'a>` copies scalar numbers/Booleans/
enum wire tags and borrows text/bytes. `bind<'a>(&'static self, &'a T)` yields a
private two-pointer Bound; only that runtime wrapper implements the sealed engine
adapter trait. Messages have no common trait/base. Existing unrelated descriptors
cannot be passed to a binding constructor; wrong live types and escaping primitive
borrows fail compilation. No instances are captured in metadata and there are no
per-field heap wrappers or per-instance graphs.

Descriptor, registry, enum and binding tables are immutable static references to
promoted values. Recursive message links are accessors; inline recursive owned
edges use Box and container edges use Vec/BTreeMap. Metadata publication is finite
without lazy mutable globals. Field/name/type/enum/group/constraint links are
checked; imported actual metadata is published/checked even for a local request.
Generated owned trees cannot express Python-style runtime alias cycles or wrong
enum types safely; those cases are type-satisfied here rather than fabricated.

Canonical sources are in base Taut `src/taut/gen/runtime`:

| Output | Canonical source | Required |
| --- | --- | --- |
| cbor.rs | cbor_fail_closed.rs | all source users |
| descriptors.rs | descriptors.rs | all source users, nested in the CBOR owner |
| ext.rs | ext.rs | all source users |
| validation.rs | validation.rs | union of enabled recorded source users |

The new local crate `rust/taut-foundation` is derived byte-for-byte with
`rust/sync_foundation.py`; provenance hashes and `--check` detect drift. It is
no_std+alloc, dependency-free and has optional `validation`. Its root descriptor
export aliases `cbor::descriptors`. Engine/report identity attaches once to the
descriptor owner's FoundationOwner type, so Rust rejects compiling the canonical
engine in a foreign facade or twice for the same owner. Compatibility facades
must re-export the actual validation module too.

`taut-shape-rs` uses this foundation through a versioned dependency bound by one
local Cargo patch. Applications may select the base local package or an emitted
source owner; the same patch binds both schemas and the actual library. The shape
CBOR module is a facade; six native generated schema modules have mandatory
metadata but no optional validation methods. The library's validation feature
re-exports the owner's report/engine. No basic consumer is forced to take shape
engines. No registry publication, dependency install or fictional repository is
assumed. The exact user-facing binding and runnable example commands are in
[the examples README](examples/rust-oneof/README.md).

## Contracts and generation safety

- Native constrained IR: 3; ordinary exported IR: 2.
- Descriptor and codec contracts: 1 each. Validation-engine contract: 1.
- Runtime owner: `taut.rust.foundation`; generator build: `rust-oneof-reference.1`
  (unreleased development provenance, distinct from release numbering).
- Foundation capabilities: descriptors.v1, codec.v1 and oneof.v1. Generated
  requirements are checked against the actual built runtime at publication;
  optional engine version is checked at build time. Compatible unequal patch
  generator labels are accepted. Missing/old exports, mismatched portable facts,
  descriptor versions, capabilities and split nominal owners cannot yield an
  empty successful report. Equivalent reordered field/case facts remain compatible.
- Shared behavior reference: `python-oneof-conformance.1`. No target-specific
  rule source or application probe annotations are added.

Source/package selection is independent of validation. `--with-runtime` remains a
source alias. Omission remains application-supplied runtime. Package default imports
the real new local foundation; source/supplied default binds crate. Explicit Rust
runtime bindings select an owner module/root/contracts/capabilities. Source requests
with foreign types require an explicit existing source owner and non-crate module;
they reuse/update that owner and never create a parent-private copy. Full dependency
schemas and ownership mappings stay available; children are not regenerated.

The Rust planner reuses the accepted shared locks/application preflight while
keeping target-specific inventories. `.taut-rust-outputs.json` and
`.taut-rust-runtime.json` record provenance, hashes and all producer/consumer users.
The common scaffold now plans both Python and Rust before applying any outputs.
Unknown/modified/handwritten/incompatible files and directory aliases/obstructions
fail before mutation; source/package/validation transitions remove only positively
owned stale outputs and preserve shared components. Consumer-first use of a missing
source owner fails explicitly. Runtime labels never repair nominal split identity.

Rust-only identifier checks/raw field escaping preserve schema names in reports.
The native validator gains an optional target filter for name reservations; its
default and Python behavior remain unchanged. Rust fields may coexist with methods
named validate. Actual helper/runtime symbols and enum variant collisions are
rejected. Python private-name restrictions are not copied. Shared compiler changes
otherwise consist of dispatch/preflight/CLI forwarding and Rust corpus closure;
the native OneOf rule source is unchanged.

## Verification and limits

Runnable scripts and logs are in `dev-docs/examples/rust-oneof`. The source object
is frozen; evidence outputs may finish/update during read-only review and are
explicitly outside source mutation. Acceptance requires completed gates and both
GO reports. Final exact counts are recorded in the verdict, not inferred from an
intermediate transcript.

Executable coverage includes all primitive reads with engine absent; no escaping
borrows/mismatched typed handles; all virtual/exhaustive combinations; multiple
member nominations/groups; zero/false/empty/payload-free; invalid serialize/repair/
snapshot; local/recursive equivalence; all owned child paths; recursive schemas;
all three canonical map-key kinds and original paths; general open-string reports;
source/package/supplied and validation-on/off; four output goldens; independent
disabled children/enabled parents in all four distribution combinations; actual
shape-library owner builds; old/facts/version/capability/split-owner rejection;
compatible patch releases/reordered dependencies; handwritten/modified inventories,
shared lifecycles, directory-junction cleanup and mixed-target unchanged preflight.

Existing Rust codec regressions, no_std checks, strict Clippy, whole shape workspace
tests, local packaged/extracted runtime builds, shared/Python feature checks and
all 16 existing codec parity variants are exercised. JSON remains Rust's existing
Taut JSON/CBOR bridge, which preserves populated invalid payloads; no native Rust
JSON parser/serializer has been invented. Source applications have no compiler,
DSL-loader, CLI or shape-engine dependency.

Baseline limits remain disclosed: a missing old documentation file and two Go
CRLF/gofmt tests reproduce the prior Python baseline failures on Windows. Broad
verification is not claimed wholly green. The absent wasm32 target keeps one
existing Rust check skipped. The unchanged shape test's `python3` resolves to a
Windows Store alias; its exact process-global checker is run with verified stable
python, with every other workspace test run normally. The checker/allowlist remain
unchanged, and immutable static references pass the guard. Initial environment
failure evidence is retained separately. No tool reinstall was needed.

## Review and landing boundary

Review object: the committed Taut diff from `7182764c` and Rust shape diff from
`959f0f04`, plus this committed draft and authority document. Exact final SHAs are
in both generated prompts. Existing Python implementation and shape-Python
checkpoint are reference-only. Other seven backends, their unchanged ordinary
codec implementations, other projects, releases/tags/registry operations and local
scratch/generated/package/wheel artifacts are outside this object. Evidence and
review outputs are authorized exceptions to a clean tracked source tree.

After both axes report GO and required checks finish, file their reports/verdict,
commit only intended Rust/shared/library/documentation changes, capture/commit the
managed workspace receipt and push only intended main branches in dependency order.
Verify advertised GitHub commit identities. The root coordinator resumes the other
seven targets after the combined checkpoint is verified; this Rust lane stops there.
