# Swift drafts, metadata and explicit validation

Generate through the normal compiler. Validation is optional; metadata is always
present. Constructors, properties and CBOR codecs never perform oneof validation.

```powershell
python -m taut.cli gen content.taut.py --out generated --lang swift --api-only --runtime source --with-validation
```

The generated API publishes `Content.descriptor`, `Content.schemaDescriptor` and
the typed `Content.tautBinding`. Enabled messages add these exact instance methods:

```swift
let draft = Content(kind: .text)
let missing = draft.validate()                  // missing selected payload
draft.text = ""                                // empty text is present
precondition(draft.isValid())
draft.number = 0                                // an invalid draft remains usable
let encoded = encode(draft.toCbor())             // preserves both populated payloads
let local = draft.validate(recursive: false)
let recursive = draft.validate()                // traverses every owned child
```

`ValidationReport.isValid` means no issues; `isComplete` means no deferred checks.
Both are needed for success. Virtual oneof selection remains deferred, so a valid
virtual record is incomplete and `isValid()` returns false. Paths retain original
field names, ascending list indices and canonical CBOR map-key bytes. Reports own
their strings, paths and collections, so later draft mutation cannot change them.

Ordinary records stay mutable Swift structs. Recursive arrays/dictionaries also
stay values: copies, shared backing and finite prefixes are not ownership cycles.
Only a component with a direct recursive stored-message edge becomes `final class`;
Swift rejects the equivalent recursive struct, including optional self storage.
This applies to self and mutual recursion. A class can express a real reference
cycle, which validation reports using the actual reference, native type and schema
binding. Required recursive fields keep their required initializer parameters.
No default nil, wrapper box, common message base or reflective factory is added.

Schema identifiers use Swift's normal Unicode identifier ranges, including emoji;
they do not use Python's identifier rules. Keyword members retain backtick escaping,
and metadata/reports retain original names. Empty raw-value enums are rejected
before output, because the native projection cannot represent them. Native naming
follows [Swift's lexical rules](https://docs.swift.org/latest/documentation/the-swift-programming-language/lexicalstructure/).

## One foundation owner, three selections

Source mode emits canonical Swift source. Build it once as `TautFoundation`, then
import/link that same module for every schema. Keep compiled artifacts in a
separate build directory. For example, in an activated Windows toolchain shell:

```powershell
New-Item -ItemType Directory -Force built | Out-Null
swiftc -emit-library -emit-module -module-name TautFoundation generated/swift/cbor.swift generated/swift/ext.swift generated/swift/paths.swift generated/swift/descriptors.swift generated/swift/reports.swift generated/swift/validation.swift -o built/TautFoundation.dll -emit-module-path built/TautFoundation.swiftmodule
swiftc -I built -L built -lTautFoundation generated/swift/api.swift main.swift -o built/app.exe
./built/app.exe
```

For validation-off applications omit `reports.swift` and `validation.swift`. The
remaining files support codecs and the complete descriptor inventory independently.
On platforms using shared objects, use the platform's normal library filename and
loader search path. The canonical source is identical across both placements.

Package mode means a real application-supplied compiled module/library. There is
no assumed Swift package repository, registry dependency or automatic installation.
For `--runtime package`, pass `--runtime-bindings bindings.json` with:

```json
{"swift":{"module":"TautFoundation"}}
```

The application supplies the module search and link paths. An optional `artifact`
directory points to a local foundation built explicitly by the development helper
`taut.gen.swift_runtime.build_foundation`; its provenance is checked before writes.
The helper is a build tool, never an application dependency or an implicit step in
schema generation. True re-export facades may share the same actual types; two
independently compiled copies under different module identities cannot.

Omitting runtime options retains **default flat supplied mode**: no runtime files
and no foundation import are emitted. Compile the canonical runtime sources once
alongside all generated schema files in the application module:

```powershell
New-Item -ItemType Directory -Force assembled | Out-Null
Copy-Item child/swift/api.swift assembled/Child.swift
Copy-Item parent/swift/api.swift assembled/Parent.swift
swiftc supplied/cbor.swift supplied/ext.swift supplied/paths.swift supplied/descriptors.swift supplied/reports.swift supplied/validation.swift assembled/Child.swift assembled/Parent.swift main.swift -o app.exe
```

Swift requires unique source basenames in one module. These filename-only build
copies retain the generated bytes exactly; no source content is rewritten.
Those supplied files are the exact canonical source from a delivered bundle. For
an explicitly imported supplied owner, use the same `module` binding as package
mode while omitting `--runtime`. `--with-runtime` is the source-mode alias; it does
not enable validation. `source_root` shares one generator-owned source directory
between generation runs. Changing modes removes only verified owned files and
keeps components needed by other users. Unknown or modified artifacts are refused.

## Separately generated children

The parent compiler receives the complete dependency schema and an explicit
`--swift-external-types` JSON mapping. An imported child's entries name its actual
module, type and compatible foundation contracts:

```json
{"Child":{"module":"ChildSchema","type":"Child","owner":"taut.swift.foundation","descriptor_contract":1,"codec_contract":1,"capabilities":["codec.v1","descriptors.v1","oneof.v1"]}}
```

Include entries for the entire dependency graph, including its enums. For child
files compiled in the **same application module**, use `"module":""` instead.
The parent reuses their existing native declarations and mandatory bindings. The
child needs no validation methods and is never regenerated. Imported child modules
require an explicitly shared foundation module; nominal types must agree.

Metadata publication verifies actual imported enums/messages and native codec
fingerprints, including bounds, forward compatibility and class/struct form.
Changing declaration order does not change those facts. A replaced child module
with incompatible facts is rejected. Native Swift does not promise binary layout
resilience for an arbitrary modified child struct: rebuild applications against
the replacement module, retaining the original generated parent's checks.

## Run the example

From the saved checkout, activate `toolchain-readiness-2026-11-02/Activate-TautToolchains.ps1`,
then run this explicit generation/build demonstration with a fresh output directory:

```powershell
python dev-docs/examples/swift-oneof/run_example.py --out D:/projects/limbo/swift-oneof-scratch/example-run
```

It executes source, package, imported supplied and default flat supplied OFF/ON
applications (five native executions). The first three match the committed
Python-normalized `expected.tsv`; applications compile and run entirely as Swift.
`results.json` records commands, source hashes and output. No install, publication,
release or tag occurs. Focused regressions additionally build independent child
and parent modules, replace child artifacts, test true alias and forged facades,
and exercise output ownership, Windows aliases and interruption recovery.
