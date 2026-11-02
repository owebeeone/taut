# Go descriptors and explicit validation

From the saved Limbo project:

```powershell
. D:\projects\limbo\toolchain-readiness-2026-11-02\Activate-TautToolchains.ps1
$env:PYTHONPATH='D:\projects\limbo\taut-dev\taut\src'
python D:\projects\limbo\taut-dev\taut\dev-docs\examples\go-oneof\run-example.py
```

The runner generates six source/package/supplied × validation-off/on consumers,
builds a local Go module from canonical sources, extracts its zip, compiles each
consumer, and runs its native executable with Python and Go absent from PATH.
Both enabled report streams and disabled metadata results must agree across all
three distributions. It writes `results.json` under a fresh Limbo scratch root.
The compiler is a development tool; the executable uses only the shared Go
foundation and operating system. Nothing is installed, downloaded or published.

`Content` keeps native mutable structs, named int64 enums, pointers for nullable
payloads, slices/maps, and existing structural CBOR behavior. For example:

```go
value := Content{Kind: ContentKindNumber}
report := value.Validate() // selected number is absent
number := int64(0)
value.Number = &number
value.IsValid()            // true; zero is present
value.ToCbor()             // codecs do not run semantic validation
```

Every message publishes `DescribeContent()` and `(*Content).Descriptor()` in both
modes, including a nil descriptor receiver. They return the same shared pointer
through the sealed runtime `MessageDescriptor` reader interface. The underlying
struct is private: callers cannot overwrite published state through a pointer.
Collections/options/parameters are defensive snapshots; type links resolve once
and recursive schema publication terminates. `DescribeSchema()` exposes the full
message/enum registry, logical virtual fields, reservations, next ID, declared and
effective options, normalized constraints, and native IR version 2 or 3.

`TautBindingContent()` exposes the shared typed adapter. Static generated functions
read fields directly and never capture a live instance. `Present` and `Read` use
original schema names and check actual native type identity; virtual fields have
no value accessor. Owned-child traversal covers ordinary fields, payloads, lists,
maps, and invalidly populated nonselected payloads. There is no message superclass,
reflective field discovery, object factory, or per-live-field metadata object.

With validation enabled, every owned message adds pointer-receiver `Validate()`,
`ValidateWithOptions(ValidationOptions)`, `IsValid()`, and
`IsValidWithOptions(ValidationOptions)`. No-options calls recurse; explicitly passing
zero-value `ValidationOptions{}` selects local scope. A nil root produces one
root `validation.type_mismatch` issue and Boolean false. Fast mode shares the
report predicates and constructs no reports or diagnostics. Success requires both
validity and completeness. Virtual selection stays deliberately deferred while
supported child checks continue. Maps use unsigned canonical Taut-CBOR key bytes
for validation order; paths expose padded base64 plus str/int/bool key types.

Reports are shared general runtime values with private owned storage:
`NewValidationIssue(code, rule, path, message)`,
`NewDeferredCheck(rule, path, reason, message)`, and
`NewValidationReport(issues, deferred, scope)`. Empty scope selects recursive.
`Issues()`, `DeferredChecks()`, and `Path()` return copies. `IsValid()` on a report
means issue-free; `IsComplete()` means no deferred checks. The earlier report stays
unchanged after repair of a mutable draft. The zero report is empty, complete and
recursive. Invalid rule grammar or incompatible descriptors are configuration
panics, distinct from diagnostics for invalid application data.

## Explicit runtime ownership

Use `--runtime source` or its `--with-runtime` alias to emit canonical sources.
Omission retains application-supplied runtime mode. `--runtime package` requires
an application-supplied Go import path; no registry/module name is invented.
`--with-validation` is independent. Normal compiler `emit`/`emit_all` and CLI
options use the same route.

`--runtime-bindings bindings.json` accepts:

```json
{"go":{"owner":"taut.go.foundation","import_path":"your.actual/module/foundation","source_root":"D:/your/source/foundation","descriptor_contract":1,"codec_contract":1,"capabilities":["codec.v1","descriptors.v1","oneof.v1"]}}
```

For same-package source/supplied applications, omit `import_path` and
`source_root`: the foundation lives with `<out>/go/api.go` in `package taut`.
Separate schema packages supply the shared owner's real `import_path` and physical
`source_root`. Application Go module configuration makes that import resolve there.
Imported source mode needs a separate source root to avoid self-imports.
Do not compile a private foundation copy inside every schema package.

For local package artifacts, omit `source_root` and optionally give `artifact` as
the explicit extracted module directory. `build_foundation(destination, import_path,
validation=True)` builds that local module from the same canonical files and
records `.taut-go-foundation.json` with provenance, contracts and content hashes.
The application explicitly supplies `require`/`replace` module configuration.
Generation checks inventory/hashes without executing Go. Generated typed guard
tokens and checks against actual compiled owner/contracts/capability exports reject
old/replaced artifacts before application validation. Explicit package-build and
test probes compile and execute the actual artifact. Compatible unequal build
labels remain allowed. There is no discovery, installation, fallback or child
regeneration.

Canonical closure: existing `runtime/cbor.go` and `runtime/ext.go`, plus
`runtime/go/descriptors.go` and `runtime/go/paths.go`. Validation additionally
includes `runtime/go/reports.go` and `runtime/go/validation.go`. Off consumers need
no report/engine source. Basic consumers need no shape engine, transport, external
dependency, schema loader or compiler package. No Go shape-library repository
exists in this checkout; none is claimed or invented.

## Independently generated children

Keep full dependency schema facts in the parent's native IR and pass
`--go-external-types mapping.json` (programmatic `go_external_types`). Each mapped
message/enum uses this exact entry, with its own original type name:

```json
{"Child":{"type":"Child","import_path":"your.actual/module/child","owner":"taut.go.foundation","descriptor_contract":1,"codec_contract":1,"capabilities":["codec.v1","descriptors.v1","oneof.v1"]}}
```

Map the complete dependency graph, including child enums and nested messages.
Parent output uses actual Go type aliases and delegates codec/metadata bindings;
it defines no duplicate child types or foreign methods. Separately generated
disabled children work through mandatory metadata/adapters. Actual descriptor and
binding fingerprints include effective codec facts, normalize declaration/Case/
enum-map ordering, and reject incompatible child replacements. Split foundation
owners fail Go's native codec/report assignability and sealed-interface checks.
Imported messages must match the requested `forward_compat` profile as well as
their schema/codec bounds; mismatches require explicit regeneration/rebinding.
Unicode is emitted as UTF-8 scalar literals, including supplementary Go letters,
so native names and original report paths do not become illegal surrogate escapes.

Output manifests protect handwritten, changed, unknown and incompatible files.
One physical source owner tracks every schema user. Validation/mode transitions
remove only positively owned unused files, preserve another user's engine, and
refuse unavailable old roots, import-path remapping, obstructed directories,
physical overlap, aliases and ambiguous Windows namespaces before mutation.
Interrupted multi-file updates fail closed and may need a fresh root or explicit
user-managed migration.

Go keyword/native generated-symbol collisions are named prewrite errors. Original
schema names remain in descriptors/reports. Validation method names are reserved
only when enabled; descriptor collisions are reserved in both modes. Python's
field/enum authoring restrictions are not transplanted to Go. The schema here uses
`ContentKind` because the existing codec already owns the native Go type `Kind`.
Go has no existing native Taut JSON codec route; none is introduced. Dense CBOR,
nullable slots, and forward-compat `WireResidual` remain structural and unchanged.

Run target checks after activation:

```powershell
$env:PYTHONPATH='D:\projects\limbo\taut-dev\taut\src;C:\Users\gianni\AppData\Local\Programs\Python\Python311\Lib\site-packages'
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
python -m pytest D:\projects\limbo\taut-dev\taut\src\tests\test_go_oneof.py -q
```

The original two Windows CRLF/gofmt checks remain in `test_go.py`. A separate new
check feeds LF source directly to `gofmt` and requires exact output equality for
all established schemas, new on/off outputs, and the canonical runtime closure.
No new formatting failure is classified as the historical newline baseline.

`goldens/legacy-api.go` preserves the prior codec-only projection at the dispatched
Taut checkpoint `b9f99ac88ec585616ffac8bf4fbc2aaf4535fc16`. `off.go` attributes the
mandatory descriptor/adapter/provenance migration; `on.go` additionally attributes
only the optional instance wrappers. The native struct and codec bodies use the
same minimal ordinary nullable schema in all three snapshots. No unrelated API
golden changes or tracked corpus regeneration is part of this lane.
