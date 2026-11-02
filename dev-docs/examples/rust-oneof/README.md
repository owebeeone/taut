# Rust OneOf checkpoint

This implements the Rust portion of [the build proposal](../../OneOf-ExplicitValidation-BuildProposal.md)
against the accepted Python reference. It uses the same
[native schema](../python-oneof/content.taut.py), native compiler/IR and
`python-oneof-conformance.1` behavior. The implementation directive supersedes
the proposal's old documentation-only/Python-first stop. This checkpoint does
not implement the other seven targets or authorize a release.

## Run it

From PowerShell in `D:\projects\limbo`:

```powershell
. .\toolchain-readiness-2026-11-02\Activate-TautToolchains.ps1
$examples = 'D:\projects\limbo\taut-dev\taut\dev-docs\examples\rust-oneof'
python "$examples\generate_examples.py"
& "$examples\Verify-RustCheckpoint.ps1"
# Existing codec parity across all targets, without regenerating their corpora:
& "$examples\Verify-RustCheckpoint.ps1" -Parity
```

The generator builds and executes source, package and descriptor-only Rust
applications with Cargo offline. Generated applications are under `generated/`;
their build and execution use no Python, Taut compiler, DSL loader or shape
engine. The development generation scripts use the normal Taut compiler.
`main.rs` is the runnable application body; `results/` records actual outcomes.
`verify_package.py` also builds a local `.crate`, extracts it and runs an
application against that artifact. It does not publish or install a package.

| Example | valid | complete | Boolean |
| --- | --- | --- | --- |
| Selected zero, false, empty text or list | true | true | true |
| Payload-free choice | true | true | true |
| Number selected, extra text, missing number | false | true | false |
| Same draft serialized, decoded and repaired | true | true | true |
| Invalid child, local scope | true | true | true |
| Invalid child, recursive scope | false | true | false |
| Virtual group after child repair | true | false | false |

The earlier report retains its two issues after repair. Invalid drafts serialize
every populated payload; dense CBOR retains all five stored fields. Virtual
discriminators have metadata but no instance/wire slot. Rust has no existing
native JSON parser route: the existing Taut JSON/CBOR bridge accepts the emitted
Rust bytes and produces `{"kind":"number","text":"extra"}` for the invalid
draft, preserving the payload. `results/invalid-draft.cbor` and `.json` are that
bridge example, not an additional Rust serializer.

## Public API and ABI

Every message, with validation on or off, provides:

```rust
pub fn descriptor() -> &'static MessageDescriptor;
pub fn taut_binding() -> &'static SchemaBinding<Self>; // low-level typed adapter
```

With `--with-validation`, every owned message also provides:

```rust
pub fn validate(&self) -> ValidationReport;
pub fn validate_with_options(&self, options: ValidationOptions) -> ValidationReport;
pub fn is_valid(&self) -> bool;
pub fn is_valid_with_options(&self, options: ValidationOptions) -> bool;
```

`ValidationOptions { recursive: false }` selects local checks; `Default` and both
no-options methods select recursive checks. Reports own their paths/strings and
offer private storage/read-only snake_case getters. `is_valid()` on a report
means no issues; `is_complete()` means no deferred checks. The instance Boolean
requires both, short-circuits and constructs no report or diagnostic objects.
Both paths use the same predicates/traversal. Virtual rules remain explicitly
deferred, while supported children are still traversed.

The ABI was first specified and compiled in the isolated Limbo `abi-probe`
before production integration, then re-probed with owned facts/static references.
`SchemaBinding<T>` owns its immutable descriptor value and contains dependency,
field-state and child-visitor function pointers. `bind<'a>(&'static self, &'a T)`
creates a private, two-pointer `Bound<'a,T>`. Only that runtime wrapper implements
the sealed adapter trait; generated messages implement no common base/discovery
trait. Adapters are stack values, with synchronous borrowed child visits, no
reflection, Any/downcasts, raw offsets, unsafe casts or per-field heap wrappers.
An application cannot construct an erased value/descriptor pair or bind a value
of a different message type. Foreign binding signatures enforce nominal owner
identity at compile time. Metadata captures no instances and allocates no
per-instance graph.

Field readers use `for<'a> fn(&'a T, usize) -> FieldState<'a>` and return copied
numbers/Booleans/enum tags or borrowed text/bytes through `PrimitiveValue<'a>`.
Presence includes false, zero and empty values. The compiler prevents scalar
borrows from outliving the bound input. Collection/record traversal stays in
typed synchronous visitors rather than allocating a value wrapper per field.

The engine also attaches one inherent identity to the descriptor foundation's
private-construction `FoundationOwner` type. Rust's orphan/duplicate-definition
rules reject a copied engine/report implementation behind a foreign codec alias,
or two engines attached to the same owner. Facades must re-export the actual
validation module too.

Static accessors link recursive descriptors finitely. Inline owned recursive
record edges use `Box`; list/map edges use their existing allocated storage.
Generated Rust owns trees without Rc/RefCell references, so wrong enum values,
shared live children and ownership cycles cannot be fabricated through its safe
type API. Dynamic Python misuse/cycle cases are type-satisfied restrictions here;
Rust still visits every populated owned path, including nonselected payloads.

## One foundation owner and both delivery modes

Canonical runtime sources live in `src/taut/gen/runtime`: `cbor_fail_closed.rs`,
`descriptors.rs`, `ext.rs` and optional `validation.rs`. The CBOR owner's nested
`cbor::descriptors` module fixes descriptor identity alongside codec/errors.
The new local crate `rust/taut-foundation` re-exports that same descriptor module
at its root. It is `no_std + alloc`, has no dependencies, and enables its report
engine only with feature `validation`. It is a real new local package in base
Taut, not an assumed existing `taut-rs` repository or a published registry crate.

`python rust/sync_foundation.py` derives the package files byte-for-byte from the
canonical resources; `--check` verifies its recorded provenance hashes. Shape
libraries do not own another low-level implementation. `taut-shape-rs` re-exports
the foundation's actual Cbor/errors/descriptors; feature `validation` exposes
the same report/engine types. Its six schema files are regenerated from native
schemas by `scripts/regenerate_foundation_bindings.py`, with provenance.

`--runtime source` copies one canonical source closure, records hashes/users, and
never installs packages. `--with-runtime` is its alias. With validation off the
source closure has no `validation.rs`; another recorded shared user can keep
that engine alive. `--runtime package` emits imports without copying runtime
sources. Omission retains application-supplied mode and references `crate`,
without silently selecting package mode. None of these switches enables methods.

`--runtime-bindings JSON` accepts `rust` keys `owner`, `module`, `source_root`,
`descriptor_contract`, `codec_contract`, and `capabilities`. The owner label is
`taut.rust.foundation`; default module is `crate` in source/supplied mode and
`taut_foundation` in package mode. Module paths may refer to genuine re-exports,
including `taut_shape`. Labels alone never unify independently compiled copies.

For a package application and optional shape library, use one explicit local
Cargo owner (replace the absolute paths for your checkout):

```toml
[dependencies]
taut-foundation = { path = "D:/projects/limbo/taut-dev/taut/rust/taut-foundation", features = ["validation"] }
taut-shape = { path = "D:/projects/limbo/taut-dev/taut-shape-rs/crates/taut-shape", default-features = false, features = ["validation"] }

[patch.crates-io]
taut-foundation = { path = "D:/projects/limbo/taut-dev/taut/rust/taut-foundation" }
```

The local patch binds the shape dependency to the same owner; no registry lookup
or publication is needed for these offline builds. Basic consumers omit
`taut-shape` entirely. A source-only application includes `pub mod cbor;` and,
when enabled, `pub mod validation;` in its root. It may optionally re-export
`pub use cbor::descriptors;`. No library crate is required for that simple route.

For source composition with separately compiled libraries, generate the shared
closure into one owner crate's `src` using `source_root`, use the foundation's
lightweight Cargo/lib wrapper, and point every consumer's Cargo owner/patch to
that same crate. An explicit source owner must already exist before a consuming
package/supplied generation. External-type source requests additionally require
an explicit existing `source_root` and non-`crate` owner module; they reuse/update
that recorded owner, never emit a new parent-private runtime. A prebuilt library
against another nominal owner must be rebuilt/rebound; its version label cannot
repair identity. The tests compile this actual shape-library composition.

`--rust-external-types JSON` maps schema names to the type owner's Rust paths.
Retain the full dependency schema and map its referenced dependency type graph.
Disabled children still own descriptors/bindings; enabled parents use those
without adding foreign inherent methods or regenerating children.

## Contracts, migration and evidence limits

Constrained native IR is version 3 (ordinary schemas retain version 2).
Descriptor/codec contracts are each 1; rule ID is `taut.oneof.v1`; the unreleased
generator build is `rust-oneof-reference.1`. Release numbers are distinct from
these contracts. Compatible unequal patch generator labels are accepted. Missing
child metadata, incompatible contracts/facts, split nominal owners and missing
validation exports fail explicitly at generation/build/publication; they never
become an empty successful report.

Source/output ownership is recorded in `.taut-rust-runtime.json` and
`.taut-rust-outputs.json`. Preflight covers the complete mixed-target write/delete
set before application. Handwritten/modified/unknown/incompatible outputs are
preserved with named errors; directory aliases/obstructions are rejected before
mutation. Mode changes remove only unmodified tracked stale files and retain
components needed by other producers/consumers. Legacy untracked copies require
a fresh directory or explicit user-managed migration. Headers alone are no proof.
Windows extended drive/UNC prefix spellings are accepted for ordinary filename
components. Namespace components with trailing dots/spaces, DOS device names or
reserved filename characters are rejected before locking or writing: removing
their prefix can change which filesystem object they identify. Use ordinary
filename components for schema outputs and runtime owners.

Mandatory descriptors/imports, the new owner module dependency and adapter/facts
constants are an intentional generated-code migration in both modes. The four
goldens cover validation on/off in source/package routes. Rust raw keyword field
identifiers retain their original schema names in reports. Metadata helper/type
symbols and enum variant collisions are rejected explicitly; ordinary fields
named `validate` remain valid because Rust fields and methods use separate access
syntax. Python's leading-double-underscore restriction is not copied to Rust.
Allocator boxes use qualified paths, so schema messages/enums named `Box` remain
valid in both modes. Owner roots and schema-user identities are normalized only
after lexical alias/obstruction checks; equivalent `..` spellings share one
owner. Physical write/delete contradictions are rejected before application.

Actual test totals and baseline limits are recorded in the checkpoint draft and
verdict. `-AllRegression` also runs the broad suite; three previously reproduced
baseline failures remain outside this change (missing old document and two Go
CRLF/gofmt checks on Windows). The wasm32 compile check is skipped when that
target is absent. All-language codec parity is existing-wire coverage, not a claim
that the seven deferred backends implement this feature. No release is authorized.

The unchanged shape workspace test harness names `python3`, which resolves to a
Windows Store alias on this host. The verification script runs its exact
process-global checker with verified stable `python` and runs every other
workspace test normally. The initial harness failure is retained separately;
the checker, its one-entry allowlist and its rules are unchanged. The generated
tables use immutable static references, which pass that existing checker.
