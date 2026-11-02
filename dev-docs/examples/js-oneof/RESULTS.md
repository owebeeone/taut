# JavaScript implementation evidence — 2 November 2026

Status: implementation complete and REVIEW-READY; production HOLD for the combined
JS/TS pair freeze and review. No staging, commit, push, tag, release, registry
installation/publication or independent target review was performed here.

The authorized prefreeze service type-soundness correction is complete. The
updated same focused command reports **500 passed,1 skipped** in
[prefreeze-service-gate.log](results/prefreeze-service-gate.log). The original
496-pass receipt below remains historical. Four added nested service cases cover
enabled/disabled parents and local/separately generated enabled children. Positive
strict compilation accepts plain recursive data and generated class inputs;
negative strict compilation rejects validate/isValid on decoded roots and every
nested child/list/map path. Runtime transport results come from actual generic
codec decoding and remain plain objects. Shared service helpers delegate to the
TS emitter's `data_type`; external message data imports default to actual exported
`ExportFields` and optional `data_export` selects another explicit data export.
No constructor/factory or implicit semantic validation was added. Counts overlap;
500 is the updated focused run, not 500 plus496.

One subsequently added test-only unsupported-artifact case passes separately:
`python -m pytest src/tests/test_js_ts_distribution.py::test_external_service_child_without_exported_data_shape_fails_typecheck -q --tb=short`
reported **1 passed in0.47s**. It proves a facade exporting a real child class,
descriptor and binding but omitting ChildFields fails strict tsc with the named
missing data export. No production bytes changed for this added test; it is not
represented as a single501-case full run. The TS executor's subsequent native
unknown-tag preservation correction and final pair integration have their own
source-associated evidence.

The initial focused gate reports **496 passed, 1 skipped** in
[target-gate.log](results/target-gate.log). It runs `test_js_oneof.py`,
`test_js_ts_distribution.py`, existing `test_js.py`, `test_scaffold.py`,
`test_cli.py` and `test_reserved_names.py`. The skip requires Windows symlink
privilege; actual junction refusal is tested and passing. This covers Node
execution, exact Python-normalized reports, all runtime distributions, immutable
metadata/reports, dynamic misuse, source closure, local package/subpath identity,
independent disabled children, compatible build labels, artifact substitution,
real strict TypeScript compilation/transpilation/execution of shared service
wiring, CLI/programmatic forwarding and an isolated built compiler wheel.

The final common-helper preservation gate reports **40 passed, 281 deselected**
in [shared-path-preservation.log](results/shared-path-preservation.log). It selects
namespace, physical overlap, equivalent ownership roots, shared users, junction,
obstruction and transition cases from Python/Rust/JVM suites plus the shared
JS/TS tests. Counts overlap the focused gate and are not added.

[native-preservation.log](results/native-preservation.log) records the separate
Python reference and real Rust/Java/Kotlin source/package/supplied behavior gate.
It reports **95 passed, 3 deselected** on the final shared-helper source.
The three old Python enum metadata-reservation tests are explicitly deselected:
the user's parallel Enum.case policy and authoring patch remain coordinator-owned.
No Python authoring source or authoring test was edited.

All gates use the activated stable CPython **3.13.5**, reusing the existing pure
pytest/build packages from the Python311 site-packages path with plugin autoload
disabled. No dependency installation or upgrade was needed. Actual Node and tsc
come from the verified readiness activation. The raw `\\?\D:\...\x:y` and
`x:stream` path issue was first observed through the older 3.11.0b4 pytest
launcher; the shared `validate_namespace_path(value)` now checks `os.fspath`
before Path conversion. JS/TS canonical-path callers use that single helper;
`_physical_path` also invokes it. Stable and beta direct regression routes were
checked without imposing a beta-specific product prerequisite.

Repeat the focused gate from `taut-dev/taut`:

```powershell
. D:\projects\limbo\toolchain-readiness-2026-11-02\Activate-TautToolchains.ps1
$env:PYTHONPATH += ';C:\Users\gianni\AppData\Local\Programs\Python\Python311\Lib\site-packages'
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = '1'
python -m pytest src/tests/test_js_oneof.py src/tests/test_js_ts_distribution.py src/tests/test_js.py src/tests/test_scaffold.py src/tests/test_cli.py src/tests/test_reserved_names.py -q
python dev-docs/examples/js-oneof/verify_examples.py
```

[examples.log](results/examples.log), source/package report TSVs and example logs
record identical reports and successful invalid-draft serialization/repair.
[canonical-inventory.json](results/canonical-inventory.json) and
[package-provenance.json](results/package-provenance.json) record exact canonical
foundation hashes; extracted local `npm pack --ignore-scripts` payload bytes are
compared to the source bundles. The enabled/disabled goldens contain no absolute
owner receipts. Temporary generated outputs and local tarballs are excluded.

No new global nine-language gate was run or claimed. The previously disclosed
missing historical document and two Windows Go CRLF/gofmt baseline failures are
unchanged and are not represented as green. Root coordinates the pair's full
integration matrix and combined two-axis review.

Limits: virtual selection is intentionally deferred/incomplete; JS retains its
existing dense structural CBOR route and has no native JSON codec. The actual
TypeScript library owns a separate codec projection; no JS library repository or
unrequested cross-target native interoperability is claimed. Multi-file output
interruption can require a fresh root or explicit migration. See
[INTEGRATION.md](INTEGRATION.md) for exact contracts and bindings.
