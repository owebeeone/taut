# Rust OneOf checkpoint — execution evidence

Source object: Taut `99b3dcf7c1f34985098a5b13add14088b86fe57c`, Rust shape
`8e92b89ed3a4f218a5a4e018fbfee6301fcc14b4`. Accepted Python reference:
Taut `7182764c4a3da372557deb6fc6f8f4b7d5f90a05`, Python shape
`c08c2a1b5197f761c5b0b835c588da512130ceda`.
The separate final verdict records review acceptance; this file records execution.

On 2 November 2026, the verified Python 3.13.5 / Rust 1.96 MSVC environment ran
`dev-docs/examples/rust-oneof/Verify-RustCheckpoint.ps1 -Parity -AllRegression`.
The script intentionally exits nonzero on the disclosed broad baseline failures;
all preceding checkpoint gates completed successfully. Logs and example outputs
are filed in [examples/rust-oneof/results](examples/rust-oneof/results).

| Gate | Completed result |
| --- | --- |
| Combined Rust feature/existing Rust/external types/Python OneOf/runtime distribution/scaffold | 272 passed, one existing wasm32 skip |
| Broad suite, `-m 'not gate'` | 1473 passed, three established baseline failures, four skipped, eight deselected; 411.51 seconds |
| Canonical foundation byte/provenance inventory | Matches |
| Foundation no_std and all-feature Clippy, warnings denied | Passed |
| Actual shape no_std, all-target/all-feature Clippy | Passed |
| Shape workspace executable tests | 107 passed; only the environment-broken python3 wrapper filtered |
| Exact unchanged process-global checker with verified Python | 42 files, one permanent allowlist entry, nothing new |
| Source, package and descriptor-only examples | Built and ran; invalid drafts round-trip, reports retain snapshots, local/recursive/virtual cases behave as required |
| Extracted local `.crate` application | Built and ran offline, no compiler or shape-engine dependency |
| All existing codec parity variants | All 16 GREEN, governance clean |
| Independent final reviewer suites | Each 238 passed; see originating reports for probes and closure |

The broad baseline failures are:

- `test_dev_docs.py::test_proto_api_surface_extensions_doc_exists_and_covers_contract`
  (the old `TautProtoApiSurfaceExtensions.md` is absent).
- `test_go.py::test_go_runtime_and_parity_runner_are_gofmt_clean`.
- `test_go.py::test_generated_go_is_gofmt_clean`.

The two Go failures reproduce Windows CRLF/gofmt behavior established before this
Rust checkpoint. No new broad failure identity appeared. The wasm32 target is not
installed. The unchanged Rust process-global wrapper invokes `python3`, which is
a Windows Store alias here; its initial environment failure is preserved in
`shape-tests-environment-baseline.log`, while `shape-process-globals.log` records
the exact checker succeeding with verified Python. Neither checker nor allowlist
was modified. Nonfatal incremental-cache access notes appear in the foundation
logs; the commands exit successfully.

The final local package artifact is
`examples/rust-oneof/package-artifacts/taut-foundation-0.10.0.crate`, SHA-256
`4abc323a490a745c673c71c0982a3e2aab88baf915278a6e4e21824ebe2a7007`.
It is a reproducible local consumption proof, not a registry publication.
The checked-in crate source, canonical resources, provenance, generation scripts,
four goldens and executable examples reproduce the supported source/package routes.

The final path correction explicitly refuses extended Windows drive/UNC namespace
components with trailing dots/spaces, reserved DOS device names or reserved
filename characters before normalization/locking/mutation. This documented
supported-path limit avoids redirecting generation into another physical owner.
Safe ordinary extended-prefix and `..` spellings remain supported. The new
counterexamples include both dot/space suffixes and both schema/runtime roots;
failed generation leaves ordinary and namespace trees unchanged.

The earlier initial/round-1 reports, plans and prompts remain audit history.
Only final round-2 reports determine acceptance at the source object above.
Existing excluded Python generated bundles/wheel and isolated scratch/package
build outputs remain outside staging. No release, tag or registry operation was run.
