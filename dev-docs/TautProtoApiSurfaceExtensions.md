# taut API Surface Extensions

Status: SPEC. This document defines a pluggable architecture for alternate
generated API surfaces over the same governed taut IR and deterministic taut wire.

The immediate motivation is to let taut stay low-opinion and low-threshold while
still allowing opinionated projections such as proto2-style builders,
proto3-style default/presence APIs, and capnproto-style Reader/Builder APIs.
These are API-compat profiles, not wire-compat profiles. The canonical taut wire
and golden corpus remain the conformance oracle unless an extension explicitly
declares a separate wire profile in a future spec.

References for the language build plan:

- Protocol Buffers Overview: protoc directly supports C++, C#, Java, Kotlin,
  Objective-C, PHP, Python, and Ruby; Google-supported plugins cover Dart and Go.
  <https://protobuf.dev/overview/>
- Protocol Buffers Reference Guides also list Rust API reference material.
  <https://protobuf.dev/reference/>
- Protocol Buffers releases publish pre-built protocol compiler artifacts; the
  recommended initial compiler pin is `protoc` `v35.0` as of 2026-06-09.
  <https://github.com/protocolbuffers/protobuf/releases>

## Design Goals

1. taut core MUST remain small: IR validation, deterministic wire, corpus,
   compatibility gate, and a minimal built-in generator stay in-tree.
2. API surface profiles MUST be replaceable without changing the IR or the taut
   CBOR wire.
3. An extension MUST be able to own generation, runtime emission, and tests for a
   `(surface, language)` pair.
4. `tautc` MUST provide one stable orchestration interface for built-ins,
   Python modules, PATH executables, and `TAUT_EXTENSION_PATH` executables.
5. Extension output MUST be reproducible: generated files, runtime files, and test
   files are returned through a manifest and can be checked by CI.
6. The golden corpus MUST remain the first correctness gate. Surface-specific
   API behavior tests are additional gates, not replacements.

Non-goals:

- A proto2/proto3 extension MUST NOT emit protobuf wire bytes by default.
- A capnproto API extension MUST NOT claim true zero-copy semantics over CBOR.
  It MAY expose borrowed views where the backing CBOR bytes make that safe, but
  true capnproto zero-copy requires a separate capnproto wire backend.
- Extensions MUST NOT mutate the loaded schema. They may reject schemas they
  cannot project.

## Extension Contract

An extension is a generator provider for a surface and language:

```text
surface:  owned | proto2 | proto3 | capnproto | <custom>
language: rust | cpp | python | java | go | ...
```

Python namespace modules use the direct Python provider API. Executable adapters
use a request/response JSON protocol over stdin/stdout only at the process
boundary. The first stable protocol is `taut.extension.v1`.

### Commands

`describe`
: Return capabilities without generating files.

`generate`
: Generate API files, client/server files when requested, runtime files when
  requested, and optional surface tests.

`runtime`
: Emit runtime support only. This is useful for packaging runtime libraries
  separately from schema-specific generated APIs.

`test`
: Run the extension's own generated test regime against an output directory and
  corpus. The extension owns language-specific execution details.

### Direct Python Provider API

The canonical provider module is:

```text
taut_extensions.<surface>.<language>.provider
```

It MUST expose these callables:

```python
def describe() -> dict: ...

def generate(
    taut_ir_json: dict,
    files,
    options: dict,
) -> dict: ...

def runtime(files, options: dict) -> dict: ...

def test(
    taut_ir_json: dict,
    files,
    options: dict,
    test_context: dict,
) -> dict: ...
```

`taut_ir_json` is the canonical JSON-serializable taut IR object. `tautc` owns
schema loading, validation, and canonicalization before the provider is called.

`describe()` MUST return a capability manifest before `tautc` calls generation
or tests:

```json
{
  "protocol": "taut.extension.v1",
  "provider_id": "taut_extensions.proto2.java",
  "surface": "proto2",
  "language": "java",
  "api_version": "taut.python-provider.v1",
  "layout_version": "taut.layout.v1",
  "supports_runtime": true,
  "supports_tests": true,
  "commands": ["describe", "generate", "runtime", "test"],
  "toolchain_requirements": [
    {"name": "protoc", "version": "35.0"},
    {"name": "protobuf-java", "version": "4.35.0"}
  ]
}
```

`tautc` MUST validate `protocol`, `provider_id`, `surface`, `language`,
`api_version`, `layout_version`, and command support before it calls
`generate`, `runtime`, or `test`.

`files` is a caller-owned file sink. It MUST provide a file-like API so the
caller can choose direct filesystem writes, in-memory caching, content-addressed
storage, or test doubles without changing provider code. The minimum API is:

```python
with files.open("src/main/java/com/acme/protocol/Thing.java", kind="api", mode="w", encoding="utf-8") as f:
    f.write(generated_source)
```

The sink MUST also provide a package-aware helper so providers do not hard-code
language source roots:

```python
layout = options["layout"]
with files.open_package(
    "Thing.java",
    kind="api",
    package_id=layout["default_package"],
    language="java",
    mode="w",
    encoding="utf-8",
) as f:
    f.write(generated_source)
```

The sink MUST reject paths outside the requested output root. It SHOULD record
path, kind, byte length, and digest for the response manifest. A convenience
`files.write(path, data, *, kind="api")` MAY be offered, but providers SHOULD
prefer the file-like `open(...).write(...)` flow for large generated files.

The Python provider return value is the response manifest as a Python `dict`.
It MUST have the same fields as the executable JSON response shape. The provider
MUST NOT write to stdout for normal generation results; stdout/stderr MAY be used
only for diagnostic logs that `tautc` captures.

`test_context` MUST make test execution explicit instead of burying it in opaque
options:

```json
{
  "generated_root": "build/taut-extensions/proto2-java",
  "corpus": {
    "golden_path": "corpus/griplab.golden.json",
    "ir_path": "corpus/griplab.ir.json"
  },
  "provider_under_test": "taut",
  "report_format": "junit",
  "regenerate": true,
  "env": {
    "PROTOC": ".taut-tools/protoc/v35.0/bin/protoc"
  }
}
```

Providers MUST treat `test_context` as execution policy from `tautc`; provider
defaults MAY fill omitted optional fields but MUST NOT silently switch corpus,
provider, or output roots.

### Provider Layout

`tautc` MUST pass `options["layout"]` to every provider. The layout object
separates "which package/module is this?" from "where should generated files be
written on this caller's filesystem?".

Minimum layout shape:

```json
{
  "default_package": "main",
  "packages": {
    "main": {
      "roots": {
        "api": "src/main/java",
        "runtime": "src/main/java",
        "test": "src/test/java"
      },
      "namespace": "com.acme.protocol",
      "java_package": "com.acme.protocol",
      "python_package": "acme.protocol",
      "paths": {
        "java_path": "com/acme/protocol",
        "python_path": "acme/protocol"
      },
      "python_package_mode": "explicit-init"
    },
    "common": {
      "roots": {
        "api": "src/main/java",
        "runtime": "src/main/java",
        "test": "src/test/java"
      },
      "namespace": "com.acme.common",
      "java_package": "com.acme.common",
      "python_package": "acme.common",
      "paths": {
        "java_path": "com/acme/common",
        "python_path": "acme/common"
      },
      "python_package_mode": "explicit-init"
    }
  }
}
```

Rules:

- `default_package` names the package entry used when a provider writes a file
  without an explicit `package_id`.
- `packages` maps stable package IDs to placement metadata. Package IDs SHOULD
  come from the taut module identity or import handle when the IR contains
  multiple modules; otherwise `main` is the default.
- Each package `roots` maps manifest kinds to caller-selected roots relative to
  the output root. Providers MUST NOT assume `src/main/java`, `src/`, or any
  other root unless the selected package layout says so.
- Each package `namespace` is the active target namespace for that package.
- Each package `paths` object carries language-specific package paths. `java_path`
  is derived from `java_package`; `python_path` is derived from `python_package`.
  Providers MUST NOT use one language's path for another language.
- `java_package` is the Java `package` declaration for that package. When set,
  Java providers MUST place API/runtime files under
  `{packages[package_id].roots.api}/{packages[package_id].paths.java_path}/ClassName.java`
  and tests under
  `{packages[package_id].roots.test}/{packages[package_id].paths.java_path}/ClassNameTest.java`.
- `python_package` is the Python import package for that package. When set,
  Python providers MUST derive `paths.python_path` from it and place API/runtime
  files under
  `{packages[package_id].roots.api}/{packages[package_id].paths.python_path}/module.py`.
  The default Python roots are `src/` for API/runtime code and `tests/` for
  tests.
- `python_package_mode` controls generated package marker files for each Python
  package. `explicit-init` means the Python provider SHOULD emit `__init__.py`
  files for generated application packages. `namespace` means it MUST NOT emit
  package markers. This rule applies to generated user packages only; the
  extension provider namespace `taut_extensions.*` still MUST remain an implicit
  namespace package.
- `files.open_package(name, kind=..., package_id=..., language=...)` MUST select
  `layout["packages"][package_id]`, resolve the final path as
  `{roots[kind]}/{paths[language + "_path"]}/{name}`, and then apply the same
  path traversal checks as `files.open(...)`. If `package_id` is omitted, the
  sink MUST use `layout["default_package"]`; if `language` is omitted, the sink
  MUST use the provider's selected target language.
- Providers MAY pass `package_path` only for generated support files that have no
  language package identity. API, runtime, and test files for schema declarations
  MUST use `package_id`.
- The response manifest SHOULD include `package_id` for every generated file that
  is package-scoped.

Recommended defaults:

| language | api root | runtime root | test root | package field |
| --- | --- | --- | --- | --- |
| Java | `src/main/java` | `src/main/java` | `src/test/java` | `java_package` |
| Python | `src/` | `src/` | `tests/` | `python_package` |

Required file location tests:

- Java tests MUST assert exact paths for the default package and at least one
  secondary package, for example
  `src/main/java/com/acme/protocol/Thing.java` and
  `src/main/java/com/acme/common/CommonThing.java`.
- Python tests MUST assert exact paths for the default package and at least one
  secondary package, for example `src/acme/protocol/thing.py` and
  `src/acme/common/common_thing.py`.
- Tests MUST cover a multi-package generation run in which two package IDs emit
  API files, runtime files, and tests without path collision.
- Tests MUST verify that generated Java `package` declarations and generated
  Python import/package paths match the selected `package_id`.
- Tests MUST verify path traversal rejection, unknown `package_id` rejection,
  and manifest entries that preserve file location, kind, and `package_id`.

### Executable Adapter Request Shape

Executable adapters receive the same command data as JSON on stdin. They exist
for non-Python implementations and shell integration, not as the canonical Python
provider path.

```json
{
  "protocol": "taut.extension.v1",
  "command": "generate",
  "surface": "proto2",
  "language": "java",
  "schema": { "version": 1, "messages": [], "enums": [], "services": [] },
  "out_dir": "gen/java",
  "services": ["GripLab"],
  "api_only": false,
  "with_runtime": true,
  "with_tests": true,
  "forward_compat": true,
  "corpus": {
    "golden_path": "corpus/golden.json",
    "ir_path": "corpus/schema.ir.json"
  },
  "options": {
    "visibility": "public",
    "layout": {
      "default_package": "main",
      "packages": {
        "main": {
          "roots": {
            "api": "src/main/java",
            "runtime": "src/main/java",
            "test": "src/test/java"
          },
          "namespace": "com.acme.protocol",
          "java_package": "com.acme.protocol",
          "python_package": "acme.protocol",
          "paths": {
            "java_path": "com/acme/protocol",
            "python_path": "acme/protocol"
          },
          "python_package_mode": "explicit-init"
        },
        "common": {
          "roots": {
            "api": "src/main/java",
            "runtime": "src/main/java",
            "test": "src/test/java"
          },
          "namespace": "com.acme.common",
          "java_package": "com.acme.common",
          "python_package": "acme.common",
          "paths": {
            "java_path": "com/acme/common",
            "python_path": "acme/common"
          },
          "python_package_mode": "explicit-init"
        }
      }
    }
  }
}
```

### Response Shape

```json
{
  "protocol": "taut.extension.v1",
  "status": "ok",
  "surface": "proto2",
  "language": "java",
  "files": [
    {"path": "src/main/java/com/acme/protocol/Thing.java", "kind": "api", "package_id": "main"},
    {"path": "src/main/java/com/acme/common/CommonThing.java", "kind": "api", "package_id": "common"},
    {"path": "src/main/java/com/acme/protocol/TautRuntime.java", "kind": "runtime", "package_id": "main"},
    {"path": "src/test/java/com/acme/protocol/ThingTest.java", "kind": "test", "package_id": "main"}
  ],
  "runtime": {
    "required": true,
    "package": "taut_proto2_runtime",
    "version": "0.1.0"
  },
  "tests": [
    {
      "name": "proto2-java-golden",
      "command": ["mvn", "test"]
    }
  ],
  "warnings": []
}
```

Rules:

- The extension MUST write only through the supplied file sink or under
  `out_dir` for executable adapters unless `tautc` passes an explicit writable
  path in `options`.
- The extension MUST report every generated file in `files`.
- The extension MUST return non-zero on generation or test failure.
- The extension SHOULD use deterministic file ordering in the response.
- `tests[].command` MAY be omitted when the extension runs tests internally for
  the `test` command.

## tautc Interface

`tautc gen` grows a surface selector:

```sh
tautc gen api.taut.py -o gen --lang rust --api-surface owned
tautc gen api.taut.py -o gen --lang rust --api-surface proto2 --with-runtime --with-tests
tautc gen api.taut.py -o gen --lang cpp,java --api-surface proto3
tautc gen api.taut.py -o gen --lang rust --api-surface capnproto --api-only
```

`owned` is the current built-in taut projection. `proto2`, `proto3`, and
`capnproto` may be built-in once implemented, but `tautc` MUST treat them exactly
like external extensions after discovery.

Additional interface:

```sh
tautc extensions list
tautc extensions describe --api-surface proto2 --lang rust
tautc extensions test --api-surface proto2 --lang rust ir/griplab.taut.py
tautc corpus ir/griplab.taut.py -o corpus --api-surface proto2 --lang rust
```

Selection rules:

1. `--api-surface` selects the surface profile.
2. `--lang` selects the target language.
3. `--extension NAME` MAY force a specific `provider_id` when multiple providers
   match the same `(surface, language)`.
4. `--extension-opt KEY=VALUE` forwards opaque provider options.
5. `--with-runtime` asks the provider to emit runtime support.
6. `--with-tests` asks the provider to emit and/or register tests.

`tautc` MUST fail early when no provider supports the selected pair. It MUST
print the discovered candidates and the discovery source to make PATH/module
resolution auditable.

For v1, `tautc corpus ... --api-surface` is not a new canonical corpus mode. It
MAY generate non-canonical parity fixtures under a caller-selected build/test
directory, but it MUST NOT update the checked-in golden corpus or publish a
surface-specific corpus as a conformance oracle.

## Discovery

Discovery is deterministic. `tautc` resolves providers in this order:

1. Built-in providers registered by taut itself.
2. Importable Python namespace modules derived from the selected pair:
   `taut_extensions.<surface>.<language>`.
3. Python package entry points in group `taut.api_surfaces`.
4. Executables found in directories listed by `TAUT_EXTENSION_PATH`.
5. Executables found on `PATH`.

Every discovered provider MUST be represented as a candidate record before
selection:

```json
{
  "provider_id": "taut_extensions.proto2.java",
  "source_kind": "python_namespace",
  "source_path": "/site-packages/taut_extensions/proto2/java/provider.py",
  "surface": "proto2",
  "language": "java",
  "priority": 20,
  "describe": {
    "protocol": "taut.extension.v1",
    "api_version": "taut.python-provider.v1",
    "layout_version": "taut.layout.v1"
  }
}
```

`source_kind` MUST be one of `builtin`, `python_namespace`, `python_entry_point`,
`taut_extension_path`, or `path_executable`. `source_path` MUST be the import
origin or executable path. `tautc extensions list` MUST display these records.
`--extension NAME` matches `provider_id`; it MUST NOT match distribution names.

The canonical Python provider name is derived, not configured:

```text
surface=proto2, language=java    -> taut_extensions.proto2.java
surface=proto3, language=python  -> taut_extensions.proto3.python
surface=capnproto, language=cpp  -> taut_extensions.capnproto.cpp
```

`surface` and `language` identifiers MUST be normalized to lowercase
`[a-z0-9_]+` module path segments before import. Hyphens MUST become
underscores. Invalid identifiers MUST fail before import.

`taut_extensions.<surface>.<language>` MUST be an implicit namespace package
layout. Extension distributions MUST NOT ship `__init__.py` in
`taut_extensions/`, `taut_extensions/<surface>/`, or
`taut_extensions/<surface>/<language>/`. This allows independently installed
Python distributions to contribute generator, runtime, fixture, and test modules
under the same derived provider namespace without coordinating one monolithic
package.

A runnable Python provider MUST expose exactly one provider module at:

```text
taut_extensions.<surface>.<language>.provider
```

`tautc` SHOULD locate the provider with `importlib.util.find_spec` so
`tautc extensions list` can report candidates without executing them. For
`describe`, `generate`, `runtime`, and `test`, `tautc` MUST import the provider
module and call the direct Python provider API in-process.

```python
from taut_extensions.proto2.java import provider

manifest = provider.generate(taut_ir_json, files, options)
```

`tautc` MUST enumerate the namespace package search locations for the selected
provider and fail if more than one `provider.py` is visible for the same
`(surface, language)` pair. Other modules under the provider namespace MAY be
supplied by multiple distributions.

Python distribution names are not part of provider identity. A wheel named
`taut-proto-surfaces`, `taut-proto2-java`, or `acme-taut-apis` MAY all provide
`taut_extensions.proto2.java`; the derived module path is the contract.

Executable names:

- Preferred adapter: `taut-extension-<surface>-<language>`
- Generic surface provider: `taut-extension-<surface>`
- Language provider that accepts the requested surface in JSON:
  `taut-extension-<language>`

Examples:

```text
taut-extension-proto2-rust
taut-extension-proto3-java
taut-extension-capnproto-cpp
taut-extension-cpp
```

Executable providers exist for non-Python implementations and shell adapters.
For Python implementations, the executable SHOULD import
`taut_extensions.<surface>.<language>.provider` and delegate to the direct API
instead of owning separate provider logic. If a distribution offers a `python -m`
entry point for manual debugging, that entry point MUST be an adapter over the
direct provider API.

`TAUT_EXTENSION_PATH` is a platform path-list. On Unix it is colon-separated; on
Windows it is semicolon-separated. Entries are searched before normal `PATH`.

Security rule: executable providers are local code execution. `tautc extensions
list` SHOULD show candidates without running them when possible. `describe`,
`generate`, and `test` MAY execute providers and MUST show the resolved path.

## Surface Profiles

### proto2

The proto2 API surface is explicit-presence first.

It SHOULD generate:

- immutable message values where the language supports that cleanly;
- builders with setters, clearers, and `build()` validation;
- `has_<field>()` / `clear_<field>()` for optional fields;
- required-field validation at build time, not decode time;
- repeated collection APIs;
- typed unknown/residual field sets;
- typed extension accessors for taut extension-band messages;
- parse/decode methods that preserve unknown fields and can re-emit the original
  taut bytes after a known-field edit.

It MUST still encode to taut CBOR and match the golden corpus.

### proto3

The proto3 API surface is default-value oriented.

It SHOULD generate:

- scalar getters that return language defaults when a field is absent;
- explicit-presence APIs only for taut optional fields;
- no `required` builder failure for proto3-style profiles;
- repeated collection APIs;
- unknown/residual preservation even though older proto3 JSON mappings dropped
  unknown fields;
- enum unknown-value behavior that matches the target language where practical.

It MUST document any divergence from real protobuf generated APIs.

### capnproto

The capnproto API surface is Reader/Builder oriented.

It SHOULD generate:

- `Reader<'a>` / `Builder` style names for languages that can express the model;
- result-returning accessors where malformed or absent pointer-like fields are
  possible;
- borrowed text/data views where the taut CBOR decode path can safely preserve a
  backing byte slice;
- owned conversion methods for callers that want the current taut shape;
- field-number/evolution checks that reject schemas that cannot be represented
  honestly in a capnproto-like API.

It MUST NOT claim capnproto wire compatibility or true capnproto zero-copy unless
a future capnproto wire profile is selected.

## Testing Regime

The testing regime has two layers: taut core tests and extension-owned tests.

### taut Core Tests

taut core MUST test:

- provider discovery by built-in registry, Python module, `TAUT_EXTENSION_PATH`,
  and `PATH`;
- command request/response validation for `describe`, `generate`, `runtime`, and
  `test`;
- extension selection errors and duplicate-provider diagnostics;
- manifest drift checks for generated files;
- layout builder behavior for exact file location, package roots, and
  multi-package generation;
- package-aware sink behavior for `package_id`, unknown `package_id`, path
  traversal rejection, and manifest `package_id` recording;
- forwarding of `--with-runtime`, `--with-tests`, `--api-only`, service filters,
  `--forward-compat`, `--extension-opt`, and `options["layout"]`.

These tests use fake extensions with tiny generated files. At least one fake
extension MUST emit files for two package IDs in a single generation run and the
test MUST assert exact Java and Python-style paths. They MUST NOT require
toolchains for every language.

### Extension Tests

Each extension MUST own a language-specific fixture suite. At minimum it MUST
cover:

- generation from a simple schema;
- compile/typecheck of generated code;
- encode generated API values to the existing golden corpus bytes;
- decode golden corpus bytes into generated API values;
- decode -> edit known field -> re-encode while preserving unknown fields;
- optional and required presence behavior for proto2;
- default-value behavior for proto3;
- Reader/Builder access semantics for capnproto;
- maps, lists, nested messages, enums, bytes, bools, and extension-band fields;
- client/server stubs when `api_only` is false.
- API parity against real `protoc` output for every protobuf-like surface.

Recommended fixture set:

```text
basic.taut.py          scalars, enum, nested message
presence.taut.py       required, optional, null, missing field
collections.taut.py    list, map, bytes
unknowns.taut.py       cross-version v1/v2 preservation
extensions.taut.py     extension-band message accessors
services.taut.py       unary, atom, log, stream, swmr, crdt slots
```

`tautc extensions test` SHOULD run:

1. `tautc corpus` for the fixture IR.
2. Extension `generate --with-runtime --with-tests`.
3. The extension manifest's test commands.
4. A drift check that regenerated files byte-match.

The result SHOULD be emitted as TAP or JUnit XML when the target ecosystem has a
standard, plus normal stdout/stderr for local debugging.

## Protoc API Parity Harness

The proto2 and proto3 API surfaces MUST be compared against real protobuf
generated classes, not only against taut's intended behavior. The extension test
suite therefore has a dual-run harness:

1. Generate a `.proto` fixture from the taut IR subset under test.
2. Run `protoc` plus the language's official or Google-supported plugin to
   produce canonical protobuf classes.
3. Generate the taut API-surface classes for the same IR.
4. Run the same API behavior tests against both generated class sets.
5. Run taut-specific wire tests only against the taut classes, because the
   protobuf classes encode protobuf wire bytes and the taut classes encode taut
   CBOR bytes.

The harness MUST install or locate the complete protobuf toolchain before
protobuf-like extension tests run. CI MUST pin `protoc` `v35.0` for the first
roll-build and MUST record `protoc --version` in test output. Local runs MAY use
a `PROTOC` environment variable to select a compiler, but the parity harness
MUST reject it unless `protoc --version` reports `libprotoc 35.0`. Otherwise the
harness MUST use the repo-local compiler installed under
`.taut-tools/protoc/v35.0`.

`protoc` alone is not the toolchain contract. `dev-docs/toolchains/protoc.lock`
MUST also record language runtime packages, codegen plugins, build tools, host
platforms, artifact source, artifact URLs, checksums, dependency resolver, and
exact generation commands. The first Java roll-build MUST lock at least:

- `protoc` / `libprotoc` `35.0`;
- `com.google.protobuf:protobuf-java` `4.35.0`;
- the JDK used for compile/test;
- the Java build runner used to compile generated code, such as direct `javac`,
  Maven, or Gradle;
- the dependency resolver and artifact source used to obtain `protobuf-java`.

Later Go, Kotlin, C#, Dart, Ruby, PHP, Objective-C, and Rust phases MUST add
their official runtime/plugin entries before the language phase starts. For
example, Go MUST lock `protoc-gen-go` and the Go protobuf module version, not
only `protoc`.

The parity boundary is API behavior, not bytes. The same API behavior tests MUST
exercise construction, mutation/build, field presence, defaults, repeated
collections, nested messages, enum access, unknown-field APIs where the official
runtime exposes them, JSON mapping when the surface claims JSON compatibility,
and error behavior for missing required fields.

The harness SHOULD be generated from one abstract test description per fixture:

```json
{
  "fixture": "presence",
  "surface": "proto2",
  "language": "java",
  "cases": [
    {"name": "builder_rejects_missing_required"},
    {"name": "optional_has_and_clear"},
    {"name": "repeated_preserves_order"}
  ]
}
```

Each language extension translates that abstract description into idiomatic
tests for both providers:

```text
provider=protoc  -> generated protobuf classes
provider=taut    -> generated taut proto2/proto3 API classes
```

The same API behavior tests MUST run through a provider adapter DSL. The adapter
layer normalizes construction, field lookup, builder calls, exceptions,
unknown-field access, and provider root class names without hiding public API
divergence. For Java proto2/proto3, the generated taut API SHOULD expose official
protobuf Java naming and builder conventions (`getFoo`, `hasFoo`, `clearFoo`,
`newBuilder`, camelCase methods) unless a manifest warning records a deliberate
surface divergence. The adapter MAY bridge package roots and provider-specific
test setup; it MUST NOT compensate for missing public API behavior.

An extension MAY skip a parity case only with a manifest warning that names the
specific official-runtime divergence. Silent gaps are test failures.

## Recommended Decisions

These decisions make the extension work roll-buildable. They supersede the open
questions that were left in earlier drafts.

1. Provider identity MUST be the derived Python namespace module
   `taut_extensions.<surface>.<language>`. Extension distribution packages MAY
   contain one provider or many providers; the wheel/package boundary is not part
   of the contract. The namespace directories MUST be implicit namespace
   packages and MUST NOT ship `__init__.py`. The canonical provider interface is
   `taut_extensions.<surface>.<language>.provider` with the direct Python
   provider API. `taut-extension-*` executables are optional adapters or
   non-Python providers.
2. `tautc` MUST supply `options["layout"]` for every provider call. Layout roots
   are caller policy; package/module path derivation is provider contract. The
   layout MUST support multiple entries in `packages`, and providers MUST select
   placement with `package_id`. Java providers MUST honor `java_package`, Python
   providers MUST honor `python_package`, package paths MUST be language-specific
   through `paths.java_path` and `paths.python_path`, and tests MUST assert exact
   file location for both default and secondary packages.
3. The first real API surface MUST be `proto2`; the first languages MUST be Java,
   then Python, then Rust. Java gives the strictest builder/presence comparison
   against official generated classes, Python gives the fastest fixture loop, and
   Rust gives the strongest ownership pressure.
4. The first protobuf toolchain lock MUST pin `protoc` `v35.0` plus the
   language runtime/plugin/build stack. The roll-build MUST download or locate
   the compiler into `.taut-tools/protoc/v35.0` and record artifact URLs,
   checksums, host platform, `protoc --version`, runtime package versions,
   plugin versions, build tool versions, and generation commands in
   `dev-docs/toolchains/protoc.lock`. The first Java slice MUST lock
   `protobuf-java`, the JDK, Java build runner (`javac`, Maven, or Gradle),
   dependency resolver, and artifact source. Global package-manager installs MAY
   be used only as a cache source; they MUST NOT define the pinned toolchain
   contract.
5. `PROTOC` MAY override the repo-local binary only when it reports exactly
   `libprotoc 35.0`. A mismatched override MUST fail before tests generate files.
6. `tautc corpus --api-surface` MUST NOT create a new canonical API-surface
   corpus in v1. Extension tests MUST run against the existing taut golden corpus
   and MAY generate temporary surface-specific fixtures under their test output
   directories.
7. Future protobuf-wire or capnproto-wire support MUST be a separate wire-profile
   protocol. This API extension protocol is for generated class shape and runtime
   behavior over taut CBOR.
8. Executable discovery through `TAUT_EXTENSION_PATH` and `PATH` MUST be
   implemented, but generation MUST execute an external provider only after the
   user explicitly selects a non-`owned` `--api-surface` and provider resolution
   has exactly one match, or after `--extension` names the provider. Listing
   candidates MUST remain non-invasive when possible.
9. The compatibility oracle order MUST be: schema/IR validation, taut golden
   corpus wire tests, generated-code compile/typecheck, then `protoc` API parity.
   A provider that passes API parity but fails the golden corpus is not complete.

## Roll-Build Plan

The implementation SHOULD be executed as a roll-build in
`plan-docs/plans/GLP-0005-taut-api-surface-extensions/`. This stable design doc
is the architecture source; the plan directory is the execution ledger.

Preconditions:

1. The tree MUST be clean before P00 starts.
2. The current checkout and current branch MUST be the owning integration
   checkout. The roll-build MUST NOT create sibling worktrees or parallel rollout
   branches unless the user explicitly asks for that in the roll-build request.
3. The start point MUST be tagged `taut-ext-p00-start`.
4. P00 MUST create the complete required plan-docs shape under
   `plan-docs/plans/GLP-0005-taut-api-surface-extensions/`: `Plan.md`,
   `State.md`, `Workstreams.md`, `Checkpoints.md`, `Decisions.md`, `Risks.md`,
   `Reviews/`, `Support/`, and `Handoff.md`.
5. P00 MUST add GLP-0005 rows to `plan-docs/Registry.md` and
   `plan-docs/ActiveWork.md`, including owner, branch/checkout, affected
   modules, write scope, and current checkpoint.
6. Every completed phase MUST append the phase, tag, verification commands,
   result, and Rollback notes to `Checkpoints.md` before the commit/tag is made.

Recommended checkpoints:

| phase | tag | scope | verification | Rollback |
| --- | --- | --- | --- | --- |
| P00 | `taut-ext-p00-plan` | Adopt this design into the complete GLP-0005 plan directory, create `State.md`/`Workstreams.md`/`Reviews/`/`Support/`/`Handoff.md`, update `Registry.md` and `ActiveWork.md`, and copy the roll-build guardrails into `Checkpoints.md`. No generator behavior changes. | `python -m pytest src/tests/test_dev_docs.py -q`; `python run_tests.py` | Remove the GLP-0005 plan directory, remove the GLP-0005 rows from `Registry.md`/`ActiveWork.md`, and revert this doc/test update. |
| P01a | `taut-ext-p01a-cli-surface` | Add `--api-surface`, `--extension`, `--extension-opt`, and `--with-tests` parsing plus no-op `owned` behavior. No provider loading yet. | CLI parser and existing generator tests. | Remove the new CLI flags and parser tests. |
| P01b | `taut-ext-p01b-provider-discovery` | Add provider candidate records, `describe()` capability validation, derived namespace-module discovery, duplicate diagnostics, and `--extension provider_id` selection with fake `taut_extensions.proto2.java.provider` modules. No file generation yet. | Provider discovery/selection tests covering `provider_id`, `source_kind`, `source_path`, duplicate namespace providers, and capability mismatch. | Remove provider registry/discovery code, fake namespace fixtures, and discovery tests. |
| P01c | `taut-ext-p01c-layout-file-sink` | Add `options["layout"]`, package-aware file sink, in-memory sink, exact Java/Python file location tests, multi-package tests, unknown `package_id`, path traversal rejection, and manifest `package_id` recording. No executable adapters yet. | File sink and layout tests only, plus existing generator tests. | Remove file sink, layout builder, fake generated files, and layout tests. |
| P01d | `taut-ext-p01d-executable-adapters` | Add executable JSON adapter discovery through `TAUT_EXTENSION_PATH` and `PATH`, keeping Python providers on the direct API. No real protobuf generation. | Executable discovery/adapter tests with fake commands and no language toolchains. | Remove executable adapter code, fake commands, and adapter tests. |
| P02 | `taut-ext-p02-protobuf-toolchain-lock` | Add `protoc` `v35.0` bootstrap, `PROTOC` validation, full protobuf toolchain lock model, Java `protobuf-java`/JDK/build-runner/dependency-resolver/artifact-source lock entries, exact generation command recording, and a tiny `.proto` compiler smoke test. | `python -m pytest src/tests/test_protoc_toolchain.py -q`; Java toolchain smoke test when available; full suite where practical. | Remove `.taut-tools` bootstrap code, checked-in toolchain lock entries, smoke tests, and any untracked `.taut-tools` downloads. |
| P03 | `taut-ext-p03-proto-fixtures` | Project the taut fixture subset to `.proto`: scalars, enums, nested messages, required/optional fields, lists, maps, bytes, and package options. Compile Java official output only. | `.proto` golden text tests; Java `protoc` compile smoke test; package path assertions. | Remove the projection module, fixture outputs, and compile harness. |
| P04 | `taut-ext-p04-parity-harness` | Add the abstract parity runner, provider adapter DSL, and explicit `test_context`; execute the same API behavior tests with `provider=protoc` and `provider=taut` using a fake taut provider. | Parity-runner unit tests proving each case runs against both providers, adapters cannot hide missing public APIs, and skips are reported explicitly. | Remove the parity runner, adapter DSL, generated test adapters, and `test_context` tests. |
| P05 | `taut-ext-p05-java-proto2-basic` | Implement `taut_extensions.proto2.java` for basic messages, builders, immutables, required validation, optional presence, and repeated fields. | Java parity tests against `protoc`; taut golden corpus encode/decode tests. | Remove the Java proto2 namespace modules and registration. |
| P06 | `taut-ext-p06-java-proto2-fixtures` | Expand `taut_extensions.proto2.java` to maps, nested messages, enums, unknown/residual preservation, extension-band accessors, and service stubs. | Full Java proto2 fixture matrix; golden corpus drift check. | Revert to the P05 Java proto2 modules and remove expanded fixtures. |
| P07 | `taut-ext-p07-python-proto2-basic` | Implement `taut_extensions.proto2.python` for the P05 feature slice. | Python parity tests against `protoc`; taut golden corpus encode/decode tests. | Remove the Python proto2 namespace modules and registration. |
| P08 | `taut-ext-p08-rust-proto2-basic` | Implement `taut_extensions.proto2.rust` for the P05 feature slice. | Rust parity tests against `protoc`; taut golden corpus encode/decode tests. | Remove the Rust proto2 namespace modules and registration. |

P09 and later SHOULD be separate roll-build plans unless P00-P08 complete without
material redesign. The next natural plans are Java/Python/Rust `proto3`, then
the remaining protobuf languages, then capnproto API compatibility.

Pause criteria:

- Stop before the next phase if the current phase cannot be verified by its
  focused tests.
- Stop if an implementation fact invalidates the API-vs-wire boundary, the
  `protoc` pin, or the derived namespace-module provider decision.
- Stop if the phase begins cycling on the same failure mode instead of producing
  a trustworthy checkpoint.
- Stop if a checkpoint would be misleadingly partial or hard to roll back.

## Language Build Plan

The longer plan targets languages with official protobuf references or
Google-supported plugins, then keeps Rust because taut already has a Rust target
and protobuf.dev has Rust reference material. The table below is backlog order,
not a single roll-build. Each row after P08 SHOULD get its own checkpoint or its
own follow-on roll-build plan.

### Phase 0: Extension Harness and Protobuf Toolchain Baseline

Build in taut core through roll-build checkpoints P01a-P02:

- `--api-surface`, `--extension`, `--extension-opt`, and `--with-tests`;
- provider candidate records, `provider_id` selection, and validated
  `describe()` capability manifests;
- direct Python provider API, layout builder, package-aware file sink, and exact
  multi-package file location tests;
- executable JSON adapter protocol;
- fake namespace-module extension tests;
- manifest drift checking;
- `tautc extensions list|describe|test`.
- `protoc` discovery through `PROTOC` then repo-local lock, then compatible
  `PATH`;
- CI documentation for installing and pinning the full protobuf toolchain,
  including runtime/plugin/build-tool versions;
- a tiny `.proto` fixture compiler smoke test.

Exit criteria: a fake `taut_extensions.proto2.rust` module can take over
generation and tests without changing taut's built-in generators, exact
multi-package layout paths are asserted, and the Java protobuf toolchain lock can
compile a tiny `.proto` fixture with versions recorded.

### Phase 1: proto2 Reference Slice

Build `proto2` for Java and Python first, then Rust.

| language | extension module | reason |
| --- | --- | --- |
| Java | `taut_extensions.proto2.java` | official protoc output is mature and gives the clearest builder/presence baseline |
| Python | `taut_extensions.proto2.python` | fastest fixture iteration; mirrors current IR-driven runtime |
| Rust | `taut_extensions.proto2.rust` | strictest ownership/presence feedback; existing taut Rust corpus target |

Exit criteria: immutable values, builders, required build failures, optional
presence, unknown field preservation, extension accessors, golden corpus byte
parity, and the same API behavior tests pass against both `protoc` classes and
taut-generated classes.

### Phase 2: JVM, C++, and Go

Build the remaining high-value production languages next.

| language | extension module | test command |
| --- | --- | --- |
| C++ | `taut_extensions.proto2.cpp` | `cmake --build` or direct `c++` fixture compile |
| Kotlin | `taut_extensions.proto2.kotlin` | `kotlinc` fixture compile/run |
| Go | `taut_extensions.proto2.go` | `go test` |

Exit criteria: each target compiles, round-trips the golden corpus, and exposes
idiomatic presence/build APIs that pass the shared parity cases against `protoc`
output for that language.

### Phase 3: Remaining Protobuf Surface Languages

Build the remaining official protobuf API languages.

| language | extension module | notes |
| --- | --- | --- |
| C# | `taut_extensions.proto2.csharp` | `dotnet test`; model immutable/builder profile explicitly |
| Dart | `taut_extensions.proto2.dart` | Google-supported plugin language; `dart test` |
| Objective-C | `taut_extensions.proto2.objc` | macOS-only CI lane; `xcodebuild` or clang fixture |
| PHP | `taut_extensions.proto2.php` | `php` fixture runner; class presence APIs |
| Ruby | `taut_extensions.proto2.ruby` | `ruby` fixture runner; dynamic presence APIs |

Exit criteria: fixture generation and corpus parity pass on supported local or CI
runners, and the same API behavior tests pass against `protoc` output.
Objective-C MAY be conditional on macOS.

### Phase 4: proto3 Surface

After proto2 is stable, build proto3 as a second surface over the same extension
protocol.

Order:

1. Java + Python, to pin default/presence behavior against mature `protoc`
   output and a fast dynamic target.
2. Go + C++ + Rust, to catch common proto3 API expectations across compiled
   targets.
3. Remaining languages from Phase 3.

Exit criteria: proto3 default-value behavior is documented per language and the
same API behavior tests pass against `protoc` output while the taut golden corpus
remains unchanged.

### Phase 5: capnproto API Surface

Build capnproto API compatibility where the target language can express it well.

Order:

1. Rust: `Reader<'a>` / `Builder` shape and owned conversion.
2. C++: reader/builder names and borrowed `string_view`/byte spans where safe.
3. Go/Python as lower-opinion reader/writer wrappers.

Exit criteria: capnproto-style APIs are honest about CBOR-backed parsing costs,
do not claim capnproto wire compatibility, and still pass taut corpus parity.

## Deferred Decisions

1. Distribution grouping is deferred and non-blocking. A distribution MAY ship
   one provider module or many provider modules as long as the derived namespace
   module contract stays stable.
2. API-surface-specific canonical corpora are deferred until an extension needs
   them for a proven gap that the existing golden corpus plus generated parity
   fixtures cannot cover.
3. Wire-profile extensibility is deferred to a separate protocol design.
