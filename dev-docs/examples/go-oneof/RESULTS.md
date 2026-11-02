# Go lane — ready for paired review

3 November 2026. This is the Go implementation handoff, not a pair verdict,
commit authorization, full-suite success, release or publication claim.
The C++ lane owns all shared scaffold/CLI/package integration and the combined
review object. Go production is on HOLD after this handoff.

## Target evidence and source association

Activated stable CPython 3.13.5 and native Go 1.27.3 on Windows amd64.
Existing pytest packages were reused; no toolchain/dependency/manifest/lock/version
upgrade was performed. Generated local test modules explicitly disable workspace,
proxy, checksum-service and automatic toolchain resolution. No registry access,
module installation, fallback or child regeneration is part of generation.

The complete drafting target command, before the localized fingerprint correction,
was:

```powershell
python -m pytest src/tests/test_go_oneof.py src/tests/test_go.py -q --basetemp D:/projects/limbo/go-oneof-scratch/final-target-r0 --junitxml D:/projects/limbo/go-oneof-scratch/final-target-r0.xml
```

Result: **104 passed, 2 failed**, with no skips or deselections. All **80 new Go
feature cases passed**. The remaining 24 passing cases and two failures belong to
the original Go suite. The feature count is included in 104, not additional.
Verbatim receipt: [target-gate-r0.log](results/target-gate-r0.log).

The two failures are exactly the demonstrated Windows CRLF/gofmt baseline:

- `test_go_runtime_and_parity_runner_are_gofmt_clean` writes its runner with
  Windows `Path.write_text` and observes it in `gofmt -l`.
- `test_generated_go_is_gofmt_clean` uses the same Windows newline route.

The separate new `test_go_emission_and_canonical_closure_are_gofmt_clean_without_crlf`
passed. It requires exact `gofmt` equality for LF source across every established
generated schema, new validation on/off output, and all canonical runtime sources.
Additional direct import-bound and independent-child import-bound output checks
also matched `gofmt` exactly. No new formatting defect is treated as baseline.

An earlier drafting pass found an impossible-index `panic` string that violated
the old generated-code preservation assertion; its generated branch was corrected
and that original test passes in the final receipt. Intermediate totals overlap
and are not added to final results. No existing Go assertion was weakened.

The paired drafting audit then identified the separately selected
`forward_compat` codec profile as an additional imported-message fact. Per-message
fingerprints now include it. The new four-case actual child build matrix accepts
matching profiles and rejects both mismatches before application validation.
The focused correction gate passed **19 cases, 65 deselected** on that revision;
it covers actual independent children/replacements, normalized fingerprints,
source/package/supplied conformance, goldens, formatting and the new codec profile
matrix. Receipt: [fingerprint-r1.log](results/fingerprint-r1.log).

A final native Unicode check also corrected JSON surrogate-pair literal escaping,
which Go does not accept for supplementary code points. UTF-8 scalar literals now
preserve valid Go names, original report paths and qualified identities. That
focused gate passed **3 cases, 82 deselected**, including the new actual native
Unicode execution plus goldens/formatting:
[unicode-r1.log](results/unicode-r1.log). The two focused totals overlap. The final
feature file contains 85 collected cases; an all-85 run is not claimed here.
The root's settled gate owns the final broad association. `owned-source.json`
records the exact final Go-owned bytes; the earlier complete target log is not
relabeled as an unchanged final-source full run.

`run-example.py --out D:/projects/limbo/go-oneof-scratch/final-example-r1` built
and ran **six native executables**: source/package/supplied, each validation off/on.
Enabled report streams and disabled metadata results agree in all distributions.
Application execution had Python and Go removed from PATH; generation/build used
the normal compiler and native Go toolchain. The local foundation module was built,
zipped, extracted, imported and executed. All packaged/source runtime bytes were
compared with the canonical source. Retained streams:
[native-example.json](results/native-example.json).
These six fingerprint-corrected ASCII example APIs were also compared byte for
byte with fresh output after the final Unicode-only escaping correction.

The C++ lane separately reported a passing actual compiler-wheel proof: canonical
C++/Go resources in the built wheel, isolated `-I -S` wheel-only generation, local
native foundation builds, source/package application compilation and execution.
That shared gate and its exact association are owned by the C++ pair record;
its count is not added here. The root owns the single settled broad/all-16-parity
gate; no final global rerun is claimed by this Go lane.

## ABI, distribution and publication choices

Foundation owner `taut.go.foundation`, internal build `go-oneof-reference.1`,
descriptor/codec contract 1. Native constrained IR 3, unconstrained IR 2, readers
1–3. No backend IR bump, second compiler or application-time schema loader.

The application supplies the actual `import_path`. Package mode has no invented
module default. Same-package source/supplied mode retains `package taut` and the
existing output layout. Independent schemas bind one source root/import or actual
local extracted package. The compiler preflights artifact inventory/provenance
without running Go. Generated initialization checks the selected runtime's actual
contract/capability exports using a defined guard token. Explicit package probes
compile and execute actual exports. A coherent forged stale artifact receipt is
insufficient: actual native initialization rejects the incompatible contract.
Compatible unequal build labels pass. No Go language-library repository exists
here, so no library migration or invented repository is claimed.

Mandatory `DescribeContent()` and nil-safe `(*Content).Descriptor()` return one
underlying immutable descriptor pointer through a sealed reader interface. This
prevents external whole-struct overwrite, which private fields alone cannot stop
for an exported writable pointer. Every descriptor/binding record is a shared
runtime type. Getter containers and constructor inputs are owned snapshots;
recursive links resolve once. Category, inventory, supported codec-option grammar,
constraint grammar and imported native fact fingerprints (including the explicit
forward-compat codec profile) are checked before usable
validation. Static typed adapters expose presence, native primitive/enum reads and
owned traversal, without capturing live values or building per-instance metadata.

Every enabled message has the four exact pointer-receiver methods. Default calls
recurse; explicit zero-value options select local scope. Reports own immutable paths
and diagnostics. Fast mode shares predicates and has a tested poison-constructor
proof that it constructs no report/issue/deferred records. Nil roots return a root
type-mismatch issue/false. Virtual selection is deliberately deferred/incomplete.
Independent groups, nonselected children, zero/false/empty presence, wrong tags,
ordinary/list/map traversal, shared paths and native pointer/map/slice cycles are
covered. Collection ancestry is local to each active path; copied Go map values
cannot hide a cycle. Validation maps use canonical unsigned CBOR key-byte order.

Native mutable structs/pointers/slices/maps/enums and structural CBOR codecs remain.
Constructors/mutations/codecs do not validate. Populated invalid payloads serialize
without selecting a winner. Forward-compat residual state remains native. The
existing `cbor.go` and `ext.go` bytes were verified identical to the dispatched
`b9f99ac88ec585616ffac8bf4fbc2aaf4535fc16` baseline. Go has no existing native Taut
JSON route; no new JSON projection is claimed.

Both validation modes publish complete ordinary/logical metadata. Independent
child builds cover disabled/enabled children and all three distributions. Actual
old/replaced children and split nominal owners fail native compile/initialization.
Metadata-like enum names and leading-double-underscore non-Python field names are
tested through supported native IR, without editing the user's DSL/authoring work.
Keywords/generated collisions fail before writes with original schema names kept.

The planner reuses the accepted physical identity/locking/preflight helpers and
tracks source users. Tests cover handwritten/changed files, shared-engine lifetime,
mode and owner moves, unavailable previous roots, import-path remapping,
obstructions, raw Windows namespace ambiguity, and injected interrupted writes.
Interrupted output remains durably fail closed; retry cannot adopt/delete unknown
partial files. Explicit migration or a fresh root can be necessary.

## Owned source and limits

[owned-source.json](results/owned-source.json) is the exact Go-owned source/test/
example inventory and hashes. Shared scaffold, CLI, pyproject, shared pair tests,
review documents, GWZ captures/status/staging/commits belong to the C++ lane/root.
No other target, user DSL/authoring test, dependency declaration/lock, repository
configuration or protected Python artifact was edited by this lane.

Runnable commands, binding grammar and complete source closure are in
[README.md](README.md). Local modules declare the existing Go generics floor;
execution is tested with Go 1.27.3, not an independently installed older Go release.
No independent review, staging, commit, push, tag, release or Swift implementation
was performed here. The root coordinates the next paired-review action.
