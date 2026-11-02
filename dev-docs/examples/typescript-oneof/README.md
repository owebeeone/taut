# TypeScript descriptors and explicit validation

Every message now exports `NameDescriptor` and `NameBinding`. Disabled output keeps
the native `Name` interface; it needs no runtime constructor and has no validation
methods. It also exports `NameFields` as its structural data alias, giving separate builds an actual
data projection in either mode. Enabled output exports a recursive `NameFields`
data interface and a mutable per-type `Name` class:

```typescript
const data: ContentFields = {kind: "number", number: 0n};
const content = new Content(data);
content.validate();                    // ValidationReport, recursive by default
content.isValid({recursive: false});   // root rules only
Content.descriptor() === ContentDescriptor; // true
```

The constructor copies declared top-level fields. Oneof payloads default to null;
ordinary required/nullable data retains the existing TypeScript projection. Child
values are retained directly, including plain nested data and independently
generated interface-only children. Classes remain assignable to data shapes.
Typed service inputs/results use these recursive data projections: a decoded
object is never promised constructor methods. Plain data objects do not acquire
methods. Mutation and CBOR/JSON codecs
never run semantic validation. All populated payloads serialize, even in invalid
drafts. JSON omits absent oneof payloads; dense CBOR and existing nullable JSON
behavior remain. Ints use bigint in the generated data shape and decimal strings
in JSON. Virtual selection is deliberately deferred, so an issue-free report can
still be incomplete.

`NameFields` and enabled classes also describe optional native `__unknown__` codec
state. Constructors retain that existing residual Map by reference so decoding,
wrapping and re-encoding preserve unknown CBOR tags. It is excluded from portable
descriptors, rule checks and owned-child traversal. Only that exact codec-storage
field name is reserved in either mode; other double-underscore names remain legal.

From the saved Windows project:

```powershell
. D:\projects\limbo\toolchain-readiness-2026-11-02\Activate-TautToolchains.ps1
python D:\projects\limbo\taut-dev\taut\dev-docs\examples\typescript-oneof\run-example.py --out D:\projects\limbo\typescript-oneof-example
```

Use a fresh output directory. The runner calls normal `emit`, builds/extracts a
local foundation artifact, performs strict `tsc` typechecking and transpilation,
executes both distributions in Node, and compares `results.json`. Its application
requires generated modules and the selected foundation only; Python/Taut C are
generation tools. This example does not publish or install the artifact.

## Runtime bindings

`--runtime source` emits the canonical foundation alongside the schema by default;
`--with-runtime` is its alias. `--runtime package` emits package references and
never installs anything. Omission keeps application-supplied runtime behavior.
`--with-validation` independently enables methods on every message. The shared
`emit` and `emit_all` entry points forward the same keyword options.

`--runtime-bindings bindings.json` accepts a `typescript` object with:

- `owner`: `taut.typescript.foundation`;
- `module`: the actual foundation module, default `./foundation.ts` for local
  source/supplied output and `@owebeeone/taut-shape/foundation` for package output;
- `validation_module`: the matching engine module, default `./validation.ts` or
  `@owebeeone/taut-shape/foundation/validation`;
- `source_root`: explicit shared physical source owner; imports are calculated
  relative to it, including a package/supplied consumer of that owner;
- `artifact`: optional local foundation `.tgz` to verify before output mutation;
- `descriptor_contract: 1`, `codec_contract: 1`, and capabilities
  `["codec.v1", "descriptors.v1", "oneof.v1"]`.

Source-mode overrides must name the actual emitted source owner. The compiler
does not infer modes from installed packages or regenerate dependencies. Missing
or old exports and incompatible actual loaded codec/schema/JSON/engine artifacts
fail clearly. Compatible unequal build labels are accepted by contract. Modified,
unrecorded, handwritten, aliased, obstructed and incompatible output files fail
before writes. Shared owner manifests retain every schema user and required engine.
The common physical identity, namespace guard, locks and write/delete preflight
come from the accepted compiler helpers.

Generated modules present the actual selected namespace to
`requireFoundation(selected)`, which verifies exported descriptor/report/codec
identities and returns the checked owner. Publication requires a defined valid
owner token and that exact return identity. Older guards that ignore the namespace
or return no checked owner fail with a named support error; build labels alone
never establish compatibility. Genuine CJS/ESM and explicit source-owner facades
may wrap namespaces while re-exporting the same actual implementation values.

For an independent disabled child, retain its complete native schema facts in the
parent input and pass `--typescript-external-types mappings.json`:

```json
{"Child":{"module":"../child/api.js","export":"Child"},
 "Kind":{"module":"../child/api.js","export":"Kind"}}
```

The map must cover the child's referenced dependency graph. The emitter imports
the actual `ChildDescriptor`/`ChildBinding` and enum descriptors and omits their
declarations. Message types import the child's actual exported `ChildFields`,
which exists with validation either on or off, and re-export it under the logical
`Child` type name. Optional `data_export` selects another explicit compatible data
interface; absent exports fail typechecking. No decoded value claims child class
methods. Fingerprints normalize field/Case/enum-map order and include effective
codec options. Separate compiled artifacts are supported; child methods and runtime
constructors are unnecessary. Missing/old/split-owner/changed-fact children are
configuration errors, including when the requested validation scope is local.

## One actual library owner

Base Taut maintains canonical TypeScript sources under
`src/taut/gen/runtime/typescript`. `typescript_runtime.canonical_sources()` supplies
both emitted source and local package builds. The lightweight closure consists of
`cbor`, `codec`, `schema`, `jsoncodec`, `ext`, `snapshots`, `descriptors`, `reports`
and `foundation`; enabled output additionally needs `validation`. The descriptor
entry never imports the validation engine. Optional source service transports are
separate from this foundation closure.

`python -m taut.gen.typescript_package FRESH_DIRECTORY` builds a private local
foundation-only test artifact using the existing shape package's subpaths. It is
not a newly allocated registry package or release. The actual `taut-shape-ts`
package exposes those same foundation/validation subpaths. Its former vendored
codec modules are compatibility facades, and its generated interfaces publish
metadata from the same owner. CJS contains the implementation; ESM entries re-export
its actual classes and state. Identical source evaluated twice is not treated as
identity, and JavaScript and TypeScript remain distinct codec projections/owners.

The library's explicit development-only `scripts/vendor-foundation.py` records
canonical byte hashes and regenerates metadata from its unchanged native IR.
`pnpm build` compiles the canonical CJS owner plus ESM facades and the existing
library/CLI. For an application with an existing compiled source owner, explicitly
build library facades to it before packaging:

```powershell
node scripts/build-foundation.mjs --owner D:\app\built\owner --output D:\app\library\foundation
```

The selected owner must already contain its compiled foundation, declarations and
required engine. This command writes true re-exports; it does not discover or
copy a second implementation. Application source and package schemas, the actual
delivery engines, generated library descriptors, codecs/errors and reports then
resolve to that one owner. The tests build/extract a real local library package
and exercise source/source, source/package and package/package compositions.

## Descriptor and report contracts

The descriptor ABI is `MessageBinding<T>(descriptor, read, accepts)`. Generated
captureless typed readers select declared data slots by static field index; their
metadata captures no live object. Lazy links handle recursive schemas and are
checked before publication. Every field, including unconstrained primitives,
collections and virtual logical fields, is described, together with enum inventory,
normalized groups/rules, reservations, next ID and declared/effective options.

Constraint inputs are copied into canonical frozen records, including parameter
snapshots. Publication requires the exact normalized oneof parameter grammar and
one constraint for each control; duplicate, missing, coercible or unsupported
declarations are configuration errors. A throwing application accessor reached
through a known field binding produces a located discriminator/shape issue and
report mode continues independent checks. That catch is limited to the field
read: configuration errors and other engine/binding failures remain usage errors.

Reports use shared `ValidationIssue`, `DeferredCheck`, `ValidationReport` and
`PathSegment` classes. They own frozen copies, including paths and options; readonly
annotations alone are insufficient. Namespaced code/rule/reason strings remain
open for future diagnostics. Reports expose `issues`, `deferredChecks`, `scope`,
`isValid()` and `isComplete()`. Fast Boolean validation shares the same predicates
and succeeds only when both report properties would succeed, without building a
report. Map paths carry original str/int/bool key types and padded-base64 canonical
Taut CBOR bytes; indices are safe nonnegative integers. Shared children appear at
each path, and active-ancestor cycles produce located issues.

Field properties use valid quoted/computed access when needed, retaining original
names. Python's double-underscore restriction does not apply. Enum members such as
`name`, `metadata` and `case` work through native IR, independently of the user's
Python authoring accessor change. Enabled fields `constructor`, `validate` and
`isValid`, generated export collisions, and the actual CommonJS `Object` class
intrinsic collision are named preflight errors. Built-in data types are explicitly
qualified through `globalThis` so valid schema types such as `Map` still work.
