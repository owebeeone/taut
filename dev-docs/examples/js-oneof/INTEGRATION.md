# JavaScript foundation ownership and bindings

Canonical implementation lives in base Taut's runtime resources. Source output
and local package payloads derive from the same bytes. Owner:
`taut.javascript.foundation`; codec/descriptor/engine contracts are each 1;
capabilities are `codec.v1`, `descriptors.v1`, `oneof.v1`. Build labels are
informational and compatible unequal patch/build labels work.

Foundation modules are `cbor.js`, `ext.js`, `contracts.js`, `descriptors.js`,
`reports.js` and optional `validation.js`. Metadata import does not import the
engine. Application closure needs Node and generated/foundation files; it needs
no compiler, authoring loader, Taut installation, shape engine or dependencies.

`emit(..., langs=['js'], validation=False, runtime_mode='source'|'package'|None,
runtime_bindings={'js': {...}}, js_external_types={...})` is keyword-only;
`emit_all` forwards the same choices. Omission means supplied runtime.
`runtime=True` / `--with-runtime` aliases source and never enables validation.
The CLI accepts `--runtime-bindings JSON_FILE` and `--js-external-types JSON_FILE`.
Bindings permit `owner`, `module`, `source_root`, optional `artifact` local tgz,
`descriptor_contract`, `codec_contract`, `capabilities`. Defaults select the
current output directory for source/supplied and `taut-js-foundation` for package.
That package name describes the locally built artifact; no registry availability
is assumed. Use `taut.gen.js_runtime.build_foundation(path)` to build it without
installation. The package root and explicit subpath exports are CommonJS; Node
ESM imports its same CommonJS owner, with no separate implementation.

A `module` identifies the owner directory/package, whose submodules are imported
explicitly. To share source across schemas, bind both to one absolute `source_root`;
generated relative imports resolve there. The producer must exist before a
package/supplied consumer binds that source root. To use an extracted package,
bind both modules to the same extracted physical directory, or arrange that local
package in the application's module resolution and retain the default package name.
No generation/application path installs, searches for or substitutes packages.

For independent child builds, supply the full dependency schema plus explicit
`{'Child': {'module':'../child/api.js','export':'Child'}}` mappings for all imported
message/enum dependencies. The export key is optional and defaults to the schema
name. Import the already-generated native classes, descriptors and `$tautBinding`;
never regenerate children or require their optional methods. Static bindings have
one generated class and captureless readers per message. Registry-key type links
support recursion without expanding descriptor graphs. Actual loaded owner/type
identity and normalized fingerprints check compatibility before publication.

Do not copy the same source under two module identities: separate loaded owners
are incompatible. All schemas in one JS application must resolve to one actual
codec/descriptor/report/engine owner. There is no standalone JavaScript shape
library in this workspace; the actual `taut-shape-ts` library uses the separate
TypeScript codec projection. This checkpoint does not claim JS/TS native codec
interoperability or invent a JS library repository.

Safe output receipts protect schema/runtime files and retain every recorded shared
user. Unknown, modified, handwritten, unavailable, incompatible or physically
aliased owners fail before mutation; a mode change removes only positively owned
stale files. Interrupted multi-file application remains fail-closed and can require
a fresh root or explicit migration. Windows ambiguous namespace components are
unsupported. Plain object misuse inside known bindings produces located issues;
invalid options and incompatible descriptors remain usage/configuration errors.

Virtual selection is deliberately deferred/incomplete. No constructor, mutation,
encoder or decoder invokes semantic validation. Nonselected populated payloads
remain serialized and recursively checked.
