# Python reference checkpoint

This is the Python batch of [the build proposal](../../OneOf-ExplicitValidation-BuildProposal.md).
The operator's implementation directive supersedes its older documentation-only
authorization. This milestone covers Python. The operator now separately authorizes
Rust implementation and scoped implementation commits; Rust is owned by its separate
chat and follows the reviewed Python commit. The other seven backends, releases,
pushes and tags remain out of scope. Review status is recorded in the checkpoint verdict.

## Try the behavior

From PowerShell in `D:\projects\limbo`:

```powershell
. .\toolchain-readiness-2026-11-02\Activate-TautToolchains.ps1
$examples = 'D:\projects\limbo\taut-dev\taut\dev-docs\examples\python-oneof'
python "$examples\generate_examples.py"
python -I -S -B "$examples\inspect_examples.py" --mode source
python -I -S -B "$examples\inspect_examples.py" --mode package --runtime-root D:\projects\limbo\taut-dev\taut\src
python -I -S -B "$examples\inspect_examples.py" --mode disabled
```

`-I -S` excludes installed packages and environment Python paths. The application
script explicitly selects its foundation and rejects compiler/authoring/build
imports. It uses an explicit adapter for `Content` to the existing dictionary codec
API; there is no reflective serializer or dynamic message factory.

The schema is [content.taut.py](content.taut.py). Generated outputs are under
`generated/source`, `generated/package` and `generated/disabled`. These use the
production compiler/emit route. Repeating generation reuses recorded ownership.

Observed examples:

| Case | valid | complete | fast Boolean | Result |
| --- | --- | --- | --- | --- |
| Number 42 | true | true | true | `{"kind":"number","number":"42"}` |
| Missing selected number | false | true | false | `oneof.payload_missing` at `number` |
| Number plus text | false | true | false | `oneof.payload_unexpected` at `text` |
| Number 0, flag false, text empty, list empty | true | true | true | Each non-null value is preserved |
| Payload-free `empty` | true | true | true | `{"kind":"empty"}` |
| Envelope with invalid child, local | true | true | true | Child is outside requested scope |
| Same envelope, recursive | false | true | false | Issue at `content.text` |
| Virtual envelope with invalid child | false | false | false | Child issue plus virtual deferred check |
| Same virtual envelope after child repair | true | false | false | Virtual rule remains deferred |

The draft example starts with an extra text payload and missing selected number,
serializes both the populated text and absent number without validation, round-trips
through dense CBOR (five fields), repairs the mutable dataclass, then validates.
The earlier immutable report still contains its two original issues. JSON omits only
absent Case payloads; ordinary nullable JSON and dense CBOR policies are preserved.

Validation-disabled output has mandatory descriptors and codec facts, no instance
validation methods, and no `taut/validation.py` in its source bundle.

## Reproduce tests and evidence

```powershell
# Feature tests, actual shape-library tests, and all examples; writes results/*.log.
& "$examples\Verify-PythonCheckpoint.ps1"
# Also run the existing codec gate for all targets (not new-feature conformance).
& "$examples\Verify-PythonCheckpoint.ps1" -Parity
# Broad existing suite; known unchanged baseline failures are documented below.
& "$examples\Verify-PythonCheckpoint.ps1" -AllRegression
# Prove the remaining baseline/environment failures without resetting source.
python "$examples\baseline_evidence.py"
```

The script reuses stable Python 3.13.5 and the already installed pytest 9.1.1
packages from Python 3.11, with plugin autoload disabled; it installs nothing.
It selects UTF-8 Java stdout and a command-local Git ownership exception. All
temporary project artifacts stay under Limbo. It does not run `run_tests.py` or
regenerate the existing codec corpora.

Evidence files are under [results](results/). The feature corpus version is
`python-oneof-conformance.1`; it includes native schema/IR checks, publication and
immutable inventories, local/recursive reports, fast-path equality, independent
groups, nonselected children, maps with canonical CBOR key paths, shared paths,
recursive schemas/cycles, misuse/configuration errors, CLI/programmatic selection,
mode goldens and ownership transitions. Independent generation tests cover
source/source, package/package, source/package, package/source and supplied owners,
including enabled parent/disabled child and the actual shape library.

The broad regression run reported **1,339 passed, 5 failed, 4 skipped, 8 deselected**.
It included the then-current **94** new feature tests among those 1,339 passes;
the later expanded feature run is a replacement verification, not an additive
total. The shape library's **190** tests are a separate repository suite. Current
feature totals are in `results/feature-tests.log` and the final checkpoint report.
No full-suite-green claim is made.

| Exact broad-run failure | Concrete evidence and corrected outcome |
| --- | --- |
| `test_dev_docs.py::test_proto_api_surface_extensions_doc_exists_and_covers_contract` | `git cat-file -e HEAD:dev-docs/TautProtoApiSurfaceExtensions.md` fails; isolated HEAD archive reproduces the missing file. Unresolved unrelated baseline document. |
| `test_go.py::test_go_runtime_and_parity_runner_are_gofmt_clean` | Test, generator, runner and all Go runtime sources match HEAD. Original HEAD test fails in the isolated archive. Its default `Path.write_text` writes CRLF on Windows; identical source written with LF is gofmt-clean. Original test remains failing. |
| `test_go.py::test_generated_go_is_gofmt_clean` | Same unchanged-HEAD reproduction and LF probe, for every generated file. Original test remains failing; no Go implementation or fixture was changed. |
| `test_java.py::test_java_decode_error_key_is_text` | Original HEAD test reproduces the JDK stdout encoding mismatch. Passes with `JAVA_TOOL_OPTIONS=-Dfile.encoding=UTF-8`. |
| `test_rust.py::test_glade_build_names_the_release_tag_its_checkout_descends_from` | Read-only `git describe` reproduces dubious-ownership exit 128. Passes with command-local `safe.directory` for this checkout. No global Git setting was changed. |

See `results/baseline-evidence.json`, `baseline-head-tests.log`,
`baseline-java-encoding.log` and `corrected-environment-tests.log`. Baseline HEAD is
`2cfee5d6156b0179066dc4eed70f60cde489a422`; no original source was reset or rolled back.
The missing document and two Windows newline checks are retained limits, outside
this Python feature's scope. The 16 existing codec parity variants all ran GREEN
with clean governance; that evidence is distinct from the new-feature tests.

## Runtime and contract inventory

One canonical owner is `taut.python.foundation`, loaded once as module package
`taut`. Foundation imports are `taut.wire`, `taut.descriptors`, `taut.validation`.
The existing `taut-proto` distribution supplies that package; the shape library's
`taut_shape.foundation` re-exports its actual types/errors/modules and imports no
delivery engine. Its validation aliases load only when requested. Generated shape
types and wire calls use emitted static facts; normal use never loads `.taut.py`.

Allocated internal contracts:

| Identifier | Value |
| --- | --- |
| Generator build | `python-oneof-reference.1` |
| Local package verification version | `0.10.0+python.oneof.reference.1` (unpublished build override) |
| Descriptor contract | 1 |
| Codec contract | 1 (existing dense CBOR semantics) |
| Constraint IR version | 3; unconstrained schemas retain v2 output; readers accept 1, 2, 3 |
| Rule | `taut.oneof.v1` |
| Required capabilities | `descriptors.v1`, `codec.v1`, `oneof.v1` |
| Corpus | `python-oneof-conformance.1` |

Repository release metadata remains dynamic under Gearu/setuptools-scm; these are
internal reference identifiers, not a release, tag or publication. Contract checks
accept unequal patch/build labels and reject incompatible owners/contracts/rules.

Source mode copies exactly the canonical files below, byte for byte:

```text
taut/__init__.py
taut/_runtime_version.py
taut/contracts.py
taut/facts.py
taut/rules.py
taut/descriptors.py
taut/wire/__init__.py
taut/wire/cbor.py
taut/wire/codec.py
taut/wire/jsoncodec.py
taut/ext.py
taut/validation.py       # only if at least one recorded user requires validation
```

The compiler's `taut.ir.model` is a facade over the same canonical fact types.
No CLI, generator, authoring loader, compiler dependency or delivery engine is in
the source closure. Installed `taut-proto` may contain compiler tools, but its
foundation import/runtime graph does not require them.

`--runtime source` emits/reuses this owner; `--with-runtime` aliases source;
`--runtime package` imports the compatible package owner without installation.
Omission remains application-supplied runtime, recorded as `supplied`, with no
discovery or fallback. Validation selection is independent. Repeated agreeing
CLI values work; conflicting/unknown modes fail before output writes.

To share source across generation runs, use `--runtime-bindings binding.json`:

```json
{"python":{"owner":"taut.python.foundation","module":"taut","source_root":"D:/projects/limbo/my-application/foundation","descriptor_contract":1,"codec_contract":1,"capabilities":["descriptors.v1","codec.v1","oneof.v1"]}}
```

The application places that root on its import path once. A package/supplied
generation run may explicitly consume the same source owner; it does not install
missing files. An explicit source-root consumer requires the owner to have been
generated first; an unavailable owner is rejected before consumer output writes.
Every accepted consumer is recorded so producer changes preserve its requirements.
Python external types are a separate `--python-external-types`
JSON mapping such as `{"Content":"child.python.api.Content"}`. The full dependency
schema is required; map referenced dependency enums as well. Publication rejects
old/mismatched children before validation, and never regenerates them.

`.taut-python-outputs.json` records per-schema output hashes, mode and provenance;
`.taut-runtime.json` records runtime hashes/contracts and shared users. A stable
owner lock serializes preflight and writes. Unknown, modified, handwritten or
incompatible files fail before replacing outputs. Cleanup only removes recorded,
unmodified, unused files. A shared validation engine survives while another user
needs it. Interrupted multi-file writes fail closed on the next hash preflight;
there is no automatic crash-recovery/adoption protocol. Use a fresh output root
or explicit user-managed migration after inspecting such a failure.

## Package artifact verification

A local wheel was built without installing dependencies or publishing. Its 12
foundation files match the canonical source bytes, and the isolated application
examples ran directly from the wheel on `sys.path`.

```powershell
$env:PYTHONPATH += ';C:\Users\gianni\AppData\Local\Programs\Python\Python311\Lib\site-packages'
$env:SETUPTOOLS_SCM_PRETEND_VERSION_FOR_TAUT_PROTO = '0.10.0+python.oneof.reference.1'
# This checkout is owned by Administrators. The build's SCM file finder strips
# command-local Git config; this flag permits its ordinary package-file discovery.
$env:SETUPTOOLS_SCM_IGNORE_DUBIOUS_OWNER = '1'
python -m build --wheel --no-isolation --outdir "$examples\package-artifacts" D:\projects\limbo\taut-dev\taut
python -I -S -B "$examples\inspect_examples.py" --mode package --runtime-root "$examples\package-artifacts\taut_proto-0.10.0+python.oneof.reference.1-py3-none-any.whl"
```

## Migration and remaining boundaries

[goldens/off.py](goldens/off.py) and [goldens/on.py](goldens/on.py) deliberately
record mandatory metadata/import/provenance changes and optional method changes.
The same code golden is asserted across source, package and supplied modes, whose
different file inventories are checked separately. The previous generator and
unchanged committed codec goldens remain available at baseline HEAD. Shape-library
vendored Python files were regenerated through its checked-in
`tools/regenerate_python_facts.py`; engines and wire policies were preserved.

New Case payloads have nullable, keyword-only defaults; ordinary dataclass fields
retain their construction order/requirements. Descriptor/helper names are reserved;
`validate` and `is_valid` fields remain allowed only with validation disabled.
Python keyword fields use an explicit trailing underscore (for example schema
`from` binds to `from_`); descriptors and report paths retain the original name,
and escaping collisions such as `from` plus `from_` are rejected before writes.
Fields beginning with double underscores are rejected before generation because
Python private-name mangling is not a supported field projection. The referenceable
Enum DSL reserves `name`, `members` and `options` for definition metadata, and
rejects those member declarations early with a migration diagnostic. Ordinary
qualified member syntax remains `ContentKind.text`.
There is no common message base, arbitrary-object validator, constructor/setter/
codec semantic check, automatic repair, or implicit child regeneration.

Virtual selection/mutual exclusion is deliberately deferred and incomplete.
Other rule families, application ID-reference semantics and other language backend
implementation are outside this checkpoint. Unsupported oneof/validation generation
for the remaining backends fails explicitly. Python completion is not all-language
feature completion, release readiness or permission to publish.
