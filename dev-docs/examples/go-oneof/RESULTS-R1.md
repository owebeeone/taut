# Go merged-round-1 correction evidence

3 November 2026, Australia/Sydney. Status: implementation ready for the single
combined corrected checkpoint; **Go production HOLD**. Original reviewers retain
closure authority. This is not a review verdict or self-closure.

Root authorized only merged-plan M2, M3 and M4 from the frozen r0 object:
Taut `4222822320cbb22e376f8b387a963e86aad10ff2`, workspace
`bd455ef9174fb13679d0ec6814e43ec1345505fc`. The only modified Go source/test files
are `runtime/go/paths.go`, `go_runtime.py`, and `test_go_oneof.py`. C++ owns the
other four modified pair paths and combined evidence/checkpoint.

## Changes and original counterexamples

**M2:** A private collection key now contains the typed start address and traversed
slice length. List/map tags remain separate from native record pointer identities;
map backing identity remains unchanged. Capacity does not define traversal extent.
No public signature, generated native layout, descriptor/codec contract, source
inventory, engine predicate or report API changed.

Both originating finite-prefix shapes compile/run through source and actual
extracted-package consumers. An outer two-node slice with the second node's children
equal to `outer[:1]` is valid and complete. An invalid shared leaf yields both exact
paths, without a fabricated cycle. Repair restores validity while the old report
snapshot retains its diagnostics. Local scope remains complete and valid. A real
cyclic one-node view with changed capacity but the same start/length is still
rejected. Existing real map/slice cycles, copied map values and per-path sharing
remain covered.

**M3:** The pure planner now withdraws the current user and distinguishes a selected
source producer/explicit consumer from an old source owner being retired. A package
or imported supplied request without `source_root` does not relabel the old default
directory as the external package. A real selected-source import remap still fails
before writes. Remaining source users retain the recorded import identity and any
needed engine; an unused positively owned old runtime and empty registry retire.

Native tests cover default same-package source → explicit verified package/imported
supplied, with validation off/on, and return to source with the opposite validation
setting. Handwritten files and external artifacts remain unchanged. Independent
remaining users still build/run with their source engine. Missing/modified/unknown
owners, unsupported user-record keys/types, relative user identities and actual
selected-source remaps are prewrite failures. Existing previous-root locks, raw
namespace checks, obstruction/hash checks and common application code are untouched.

Forty persisted-operation cutoffs cover package/imported-supplied retirement,
validation off/on, and ten cutoff positions. Retries either reach a fully retired
known state or refuse without further byte changes. No unknown file is adopted or
deleted. The first drafting sweep found that imported supplied retry could skip the
unknown-runtime scan after the owner receipt had been deleted first. The existing
scan now also runs for an explicit runtime import, preserving package-equivalent
refusal at this same retirement boundary. Its initial failure is retained below.

**M4:** The LF-format regression imports its existing helper through pytest's sibling
test-module route, rather than an incidental importable repository parent. It now
actually compares generated and canonical bytes with `gofmt` from the integration
scratch cwd with source-only PYTHONPATH and from the repository root. The original
two Windows CRLF tests are unchanged. The failed r0 global LF node remains an import
error before formatter execution; it is not relabeled a formatter mismatch.

## Executed scoped evidence

Used activated stable CPython 3.13.5, Go 1.27.3, existing pytest packages and disabled
third-party plugin autoload. No dependency/toolchain/manifest/lock/version upgrade,
runtime discovery/installation, corpus regeneration or child regeneration occurred.

| Scoped command | Result | Receipt |
| --- | --- | --- |
| Entire Go feature file from scratch cwd, source-only PYTHONPATH | **145 passed**, no skips/deselections, 45.98 s | `results-r1/all-go.log` and XML |
| Retirement/remap/native/invalid-state/cutoff subset after final guard | **56 passed, 89 deselected**, 11.68 s | `results-r1/retirement-corrected.log` and XML |
| Exact LF-format node from repository root | **1 passed**, 0.83 s | `results-r1/format-from-root.log` |
| Fresh source/package/supplied × validation off/on example | **Six compiled native executions passed**, streams agree | `results-r1/example.log`, `native-example.json` |

The 145 include all 85 r0 feature cases plus 60 new counterexample/lifecycle cases.
The subset/root-node totals overlap and are not added. Native package probes use a
local built/zipped/extracted module from the same corrected canonical sources;
applications execute without Python/Go on PATH. Exact command argv/cwd/configuration
is recorded in `results-r1/commands.json`.

The first drafting selection passed 59 and failed three supplied-mode persisted
retirement cutoffs, with 83 deselections. That failure motivated the final explicit
import scan guard described above. Preserve `results-r1/closure.log` and XML as
failed-first evidence; only the later 56-case and 145-case receipts qualify the
final correction. No failed r0 or drafting record was overwritten.

The C++ lane separately reports shared map/scaffold **16 passed** and pair
distribution plus exact LF-node **11 passed**, including the actual compiler wheel,
canonical resource hashes, isolated `-I -S` generation and native C++/Go source/
package execution. Those shared receipts and associations are owned by
`D:/projects/limbo/cpp-go-oneof-scratch/remediation-r1` and are not added here.
No full broad/all-16 parity gate was automatically repeated.

## Preservation and exact scope

`results-r1/preservation.json` and its before/after snapshots verify unchanged
five user sources, 35 excluded Python artifacts, five indices and 46 lock/manifest/
configuration files. All five HEADs remained at the r0 tuple during these scoped
checks. The 18 original Go-owned files outside the three authorized edits still
match the original inventory; unchanged canonical `cbor.go`/`ext.go` hashes also
match. Original `RESULTS.md`, `results/owned-source.json` and all r0 receipts remain
historical and byte-identical. The C++ lane's independent full selected-source audit
reports exactly the seven authorized pair source/test changes.

The new exact allowlist and final hashes are
`results-r1/owned-source-R1.json`. It names only the three modified Go files and
distinct R1 evidence. The saved three r0 input hashes are retained in
`results-r1/owned-r0-source.json`; original source itself remains in the frozen commit.

Go is on HOLD. No shared-file edit, independent review agent, staging, commit, push,
tag, release or Swift work was performed. The C++ owner aggregates one corrected
local GWZ checkpoint; the same two original reviewers judge closure on its exact
tuple. Root coordinates any final GitHub push only after proper pair and Swift
review acceptance.
