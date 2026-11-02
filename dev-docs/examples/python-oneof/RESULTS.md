# Python checkpoint results — 2 November 2026

**Python reference implementation complete; Code/Surface GO and State GO at
`3dd141a8433aaef152a285327d8091870a2eb3865eba7f8cb3cc78c70f901bd2`.**
See the [filed verdict](../../PythonOneOfCheckpoint-Verdict.md) and the
[runnable example guide](README.md). All six review findings were closed by their
originating reviewers after two bounded remediation rounds.
The subsequently requested README authorization correction is approved by both
axes at commit inventory `f72b5bcf607a108a45706dcab42f28f7da8e8a823937a051b98970ddb37a0298`;
production and test bytes are unchanged from the implementation digest above.

## Reproduce and inspect

From PowerShell in `D:\projects\limbo`:

```powershell
$examples = 'D:\projects\limbo\taut-dev\taut\dev-docs\examples\python-oneof'
& "$examples\Verify-PythonCheckpoint.ps1"
& "$examples\Verify-PythonCheckpoint.ps1" -Parity
# Intentionally reports the three independently proven baseline failures below:
& "$examples\Verify-PythonCheckpoint.ps1" -AllRegression
```

The first command regenerates source/package/disabled examples and runs their
isolated applications. The guide also lists the individual `python -I -S -B`
commands, native schema, full source inventory, CLI/programmatic bindings, and
local wheel build/consumption commands. No toolchain or dependency installation
is performed. Generated example bundles, scratch trees and the local wheel are
reproducible local artifacts; the commit includes their input scripts and the
validation-on/off goldens rather than absolute-path ownership receipts.

Observed behavior includes `{"kind":"number","number":"42"}`, distinct missing
and extra payload issues, preserved zero/false/empty values, payload-free `empty`,
invalid draft serialization followed by mutable repair, local/recursive nested
failures, valid-but-incomplete virtual groups, and mandatory descriptors with no
validation engine present. Source/package application imports need no compiler,
CLI, authoring loader, build tooling or shape engine.

## Final results and count boundaries

| Gate | Observed final result | Evidence |
| --- | --- | --- |
| New Python conformance corpus | **128 passed**, no skips | [feature-tests.log](results/feature-tests.log) |
| Selected core/compiler/codec regression cases | **809 passed** | [core-regression-tests.log](results/core-regression-tests.log) |
| Actual taut-shape-py suite | **190 passed** | [shape-tests.log](results/shape-tests.log) |
| Final broad taut suite, environment corrections enabled | **1,375 passed, 3 failed, 4 skipped, 8 deselected** in 324.53 s | [regression-tests.log](results/regression-tests.log) |
| Existing codec parity | **16 variants GREEN**, clean governance; every target ran | [codec-parity.log](results/codec-parity.log) |
| Local wheel/foundation | **12 canonical files byte-identical; 16 behavior/scope rows passed**, including actual library type identity | [wheel-verification.json](results/wheel-verification.json), [wheel-conformance.json](results/wheel-conformance.json) |

**Do not add these overlapping counts.** The final broad 1,375 passes already
include all 128 new feature cases and the selected core cases. The shape-library
suite is a separate repository. Parity rows are codec regression evidence, not
new-feature conformance. The earlier exploratory broad run's 1,339 passes
included the then-current 94 feature cases; its five failures became the three
below after correcting Java stdout encoding and command-local Git ownership.
It is superseded by the final broad run, not an additional pass total.

The final local wheel is
`taut_proto-0.10.0+python.oneof.reference.1-py3-none-any.whl`, with SHA-256
`7ff8c48266ec3814a4fea75c4afe94f1ffb1e1193c0a9134706ee99ad4f7fd44`.
It is an unpublished verification build, not a release. Normal package runtime
imports use the same canonical files as source mode.

## Remaining baseline failures are established, not inferred

| Original test | Evidence |
| --- | --- |
| `test_dev_docs.py::test_proto_api_surface_extensions_doc_exists_and_covers_contract` | The required document is absent in original HEAD `2cfee5d6156b0179066dc4eed70f60cde489a422`; `git cat-file` and an isolated archive reproduce it. |
| `test_go.py::test_go_runtime_and_parity_runner_are_gofmt_clean` | Original test, generator, runner and runtime sources match HEAD. The isolated original test fails because default Windows `Path.write_text` emits CRLF. The exact same source written with LF is gofmt-clean. |
| `test_go.py::test_generated_go_is_gofmt_clean` | The same unchanged-HEAD reproduction and LF-only probe applies to every generated file. No Go source or fixture was changed. |

[baseline-evidence.json](results/baseline-evidence.json) records 12 source
comparisons and exact command outcomes. The corresponding logs are
[baseline-head-tests.log](results/baseline-head-tests.log) and
[baseline-java-encoding.log](results/baseline-java-encoding.log). The unchanged
Java encoding and Rust Git-tag tests pass with environment fixes, recorded in
[corrected-environment-tests.log](results/corrected-environment-tests.log).
No global Git trust setting was changed. GWZ uses a process-local XDG Git config
for this Administrators-owned workspace.

`baseline_evidence.py` captures the checkout HEAD at invocation; the committed
evidence above was captured before this milestone's commit against original HEAD
`2cfee5d…`. Its archived probes remain under the local scratch directory. Do not
reinterpret a later HEAD capture as the original baseline.

There is no full-suite-green claim and no outstanding new Python feature failure.
The four existing broad-suite skips are retained as skips, not counted as passes.

## Frozen contract handed to Rust

- Native constraint IR **v3** when OneOf/Case is present; unconstrained exports
  remain v2, and readers accept v1/v2/v3. `FieldDef.oneof` stores enum, virtual and
  exhaustive; `FieldDef.cases` retains typed controller/enum/member nominations.
- Descriptor contract **1**, codec contract **1**, generator build
  `python-oneof-reference.1`, corpus `python-oneof-conformance.1`.
- Rule **`taut.oneof.v1`**. Known constraint parameters are exactly
  `{"controlling_field": <schema field name>}` and must match normalized groups
  one-to-one. Unsupported rules/parameters/links are configuration failures.
- Codes: `oneof.invalid_discriminator`, `oneof.payload_missing`,
  `oneof.payload_unexpected`, `validation.type_mismatch`,
  `validation.ownership_cycle`; virtual reason `oneof.virtual_deferred`.
- Report scope local/recursive; recursive defaults true; Boolean success equals
  valid **and** complete. Wrong tags do not hide independent children; populated
  nonselected children are traversed. Maps use unsigned lexicographic canonical
  CBOR key bytes and typed, padded-base64 path snapshots. Shared objects report
  per path; only active ancestors detect cycles.
- Presence is non-null. Sparse oneof JSON preserves every populated payload and
  existing i64 string semantics; dense CBOR remains unchanged. Constructors,
  setters and codecs do not call semantic validation.
- Shared CLI/programmatic selection is explicit source/package/supplied, with
  `--with-runtime` aliasing source and `--with-validation` independent. Explicit
  source-root consumers require an existing owner and retain their use requirement.
- Remediation changed no shared wire shape, IR allocation or runtime-owner model.
  It added strict known-rule configuration checks, normalized compatibility
  comparison and safe preflight of **both writes and deletions**. Rust must
  preserve these invariants rather than reproduce the fixed counterexamples.

Representative implementation:
[facts.py](../../../src/taut/facts.py),
[descriptors.py](../../../src/taut/descriptors.py),
[validation.py](../../../src/taut/validation.py),
[Python emission](../../../src/taut/gen/python.py),
[runtime ownership](../../../src/taut/gen/python_runtime.py),
[native DSL](../../../src/taut/ir/dsl.py), and
[sparse JSON](../../../src/taut/wire/jsoncodec.py).
Tests: [behavior/metadata](../../../src/tests/test_oneof.py) and
[distribution/identity/ownership](../../../src/tests/test_python_runtime_distribution.py).

Python's actual runtime binding is `taut.python.foundation` under module `taut`;
`taut_shape.foundation` re-exports that actual owner. Rust may use its separately
selected lightweight foundation crate, but must freeze and test its own owner and
typed-access binding before claiming Rust completion. The other seven languages
remain deferred. No push, tag or release was performed.
