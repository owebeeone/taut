# C++/Go checkpoint — merged remediation plan 1

Date: 3 November 2026 (Australia/Sydney). Status: **ROOT AUTHORIZED; merged
remediation window 1 implemented; corrected production frozen for the exact seven
paths below and scoped evidence**.
The coordinator approved M1–M6, the bounded retirement/remap mutation boundary,
one later corrected local GWZ checkpoint and original-two-reviewer closure. This
is one merged patch for both original axes, not per-target rounds. No finding is
closed by this authorization or by implementer tests.

The focused implementation receipts are filed in
`CppGoOneOfCheckpoint-FocusedResults-1.json`, each target's `RESULTS-R1.md`,
and distinct `results-r1` inventories. The first Go correction attempt exposed
three persisted-retirement cutoff failures; its original 59-pass/3-fail receipt
is retained. The same bounded planner now also scans unknown leftover runtime
files in explicit imported supplied mode. The corrected retirement checks and
final feature checks pass. This is still one merged remediation patch, with no
new public API, descriptor/codec ABI, shared mutation machinery or dependency.
The same two original reviewers must independently judge closure on the new
committed tuple; these implementation results close no finding by themselves.

## Exact initial object and evidence

Taut `4222822320cbb22e376f8b387a963e86aad10ff2`, workspace
`bd455ef9174fb13679d0ec6814e43ec1345505fc`; unchanged reference shapes are the
exact revisions in Tuple.json. Full [Code+Surface](CppGoOneOfCheckpoint-ReviewCode.md)
and [State](CppGoOneOfCheckpoint-ReviewState.md) reports are unedited testimony.
The [initial verdict merge](CppGoOneOfCheckpoint-Verdict.md) is NO-GO.

The ONE root-assigned r0 gate has coherently finished. Its complete evidence is
`D:/projects/limbo/cpp-go-oneof-scratch/global-gate-r0`: RESULTS.md,
global-results.json, broad log/XML, six failure extracts, parity JSON/log, commands,
selection/deselection/skips, source/protection/raw-blob/tuple before-after proofs
and the top-level evidence inventory. Preserve all original failed receipts.

Result: **2060 pass / six fail / five skip / 11 authorized deselections**, 2071
selected. All 16 require-all codec variants GREEN, zero violations. Three failures
are the exact historical baseline; three new failures are separately classified
below. The new LF-format test failed at Python import BEFORE formatter execution.
All 678 selected source hashes, additional 679-file raw audit, five protected
sources, 35 excluded artifacts, five indices, 46 locks/manifests and five HEADs
were unchanged. No blanket baseline suppression or premature corrective run.

## One disposition and closure test for every finding

| Merged disposition | Finding IDs | Owned implementation/test scope | Acceptance counterexample / closure |
| --- | --- | --- | --- |
| M1: Correct C++ message identity | Code P2-1 | C++: runtime/validation.hpp and test_cpp_oneof.py | Parent's first required/optional value Child may have same address yet is not an ancestor cycle; valid report empty/complete and Boolean true. Invalid oneof child reports its real child path, with no invented cycle. Retain real recursive-pointer cycles and repeated shared paths. |
| M2: Correct Go slice-view identity | Code P2-2; State P2-1 | Go: runtime/go/paths.go and test_go_oneof.py | Outer two-element slice containing a node whose children are outer[:1] is finite. Valid leaf yields empty/complete report and true; invalid shared leaf yields BOTH paths and no cycle. Retain genuine slice/map cycles, copied map-value behavior, shared paths and local mode. |
| M3: Retire, rather than remap, unused old Go owner | Code P2-3 | Go: go_runtime.py and test_go_oneof.py | Default same-package source owner with one known user and matching hashes can withdraw for explicit verified package/imported-supplied owner, validation off/on; owned stale files/old registry retire, handwritten files survive, external artifact stays unchanged, new API builds/runs. Package→source returns correctly. Actual surviving/consumed source-owner import remaps still reject before mutation; other users/needed engine survive. |
| M4: Portable LF-format fixture import | Both P3-1 | Go: test_go_oneof.py | Exact formatting node runs from required integration scratch cwd with source-only PYTHONPATH, and from repo root, without adding an incidental repository-parent dependency. Confirm actual generated/canonical LF/gofmt comparisons execute and pass. Historical two CRLF tests remain unchanged. |
| M5: Preserve conditional sorting assertion under alias imports | Both P3-2 | Shared/C++: test_map_gen.py | Verify map output imports AND uses actual sort binding; plain schema has no sorting import/use or unused dependency. Keep native compilation/runtime evidence for map/plain output. Do not merely delete the old assertion. |
| M6: Attribute ownership receipt migration | Both P3-3 | Shared/C++: test_scaffold.py | Expected output includes api.go plus .taut-go-outputs.json; receipt owns the emitted API. Undeclared defaults remain accepted and explicit unsupported declarations at every existing level still fail before any output. |

No finding is disputed or silently omitted. Both axes raised M2 independently.
M4–M6 are test integration defects, not demonstrated formatter/codec/default-option
product failures. Their original failed receipts remain historical r0 evidence.

## Bounded implementation choices and mutation boundary

M1 changes only the private active-ancestor key from an untyped address to address
plus stable actual native binding/type identity. This keeps generated native data
layouts and public ABI, one traversal/predicate implementation, static metadata,
no-RTTI and const-noexcept/resource fallback. It introduces no live-instance capture,
per-field wrapper, global visited set or resource-success fallback.

M2 distinguishes the typed start and traversed length of a slice, rather than only
its first-element address. Capacity alone is not traversal extent. Preserve actual
map backing identity and active-path enter/leave, including Boolean short circuits.
No reflect/unsafe requirement, data coercion, generic factory or public API change.

M3 is a correction inside the existing pure Go planner, not a new lifecycle or
mutation mechanism. The current guard sees `source_root == output_directory` even
when package/supplied mode selects no source owner. Its before-state is:

- Old local `.taut-go-runtime.json`: import_path empty, fully hashed owned files,
  one current schema user A, validation requirement off/on.
- Old schema receipt points to that local physical source owner; all hashes match.
- New request selects explicit usable package/imported-supplied module and artifact,
  with no explicit source_root consumption. The default path variable still equals
  the old local directory; this alone must not classify it as a selected source.

The corrected plan must withdraw A from its old owner, determine remaining users,
and classify actual source production/consumption separately from retirement. A
surviving or explicitly consumed physical source owner must retain its recorded
import identity; requests to rebind it incompatibly still fail. A completely unused
verified old owner can retire without relabeling it as the new package owner.

After legitimate sole-user retirement:

- Generated API and schema receipt select package/supplied mode; source_root is null.
- Only recorded unmodified stale runtime files and empty owner receipt are removed.
- Handwritten files, other schemas/owners and the actual external artifact are unchanged.
- If another valid user needs the old owner/engine, those components and old import
  identity remain. The new package choice does not remap that source root.
- Unknown/malformed user records, missing previous owners, modified/handwritten
  runtime files, alias/obstruction/overlap and unsupported remaps remain prewrite errors.

Existing raw namespace checks, complete multi-target planning, previous-root/current
root locks, locked recheck, positive file hashes and common apply_outputs stay in
place. Exercise actual default-directory retirement, explicit shared-owner retention,
genuine remap rejection and cutoffs during retirement; retries must either succeed
from a valid state or refuse durably without further writes/adoption/deletion.

This narrowly changes a source-use classification at a mutation boundary. Root must
review/authorize that exact window before patching. The original reviewers called
the remedies bounded; their originating closure judges any new architectural root.
No implementer claims self-closure or exemption from the bounded review process.

## Ownership and expected patch allowlist

C++ lane owns M1, M5, M6, combined evidence/docs and staging aggregation. Go lane
owns M2, M3, M4 and its target receipts. Go does not edit shared files or commit.
Do not independently commit either half: merge both owned changes into ONE scoped
corrective checkpoint after their focused gates and final byte inventories settle.

Expected production/test paths (no others without root reconciliation):

- `src/taut/gen/runtime/validation.hpp`
- `src/taut/gen/runtime/go/paths.go`
- `src/taut/gen/go_runtime.py`
- `src/tests/test_cpp_oneof.py`
- `src/tests/test_go_oneof.py`
- `src/tests/test_map_gen.py` — newly attributed shared regression-test path.
- `src/tests/test_scaffold.py` — newly attributed shared regression-test path.

Update owned source manifests and corrected example/test receipts deliberately;
retain initial owned-source/gate associations as historical r0 records. Pair
Authority/DRAFT, RemPlan, Inventory-1, corrected tuple, prompts, original reports,
closure reports and merged verdict are authorized review evidence. The unchanged
canonical cbor/ext resources, user DSL/authoring tests, 35 excluded Python artifacts,
dependency declarations/locks/versions and reference libraries remain protected.
No manual gwz.conf edit, toolchain upgrade, publication, push, tag or Swift work.

## Focused acceptance gates and original-axis closure

1. Replay all exact originating native counterexamples, including all valid/invalid
   path variants above. Keep the original failed counterexample files/results.
2. C++ meaningful native engine/codec/source/package/supplied/disabled-child/fault
   gates, and Go meaningful conformance/identity/immutability/package/artifact/
   child/fingerprint/source-owner transition/interruption gates. Run in scratch
   using stable CPython 3.13.5 and activated existing native compilers; source hashes
   and protected/indices/locks before/after are explicit.
3. Run all three new integration assertion nodes in the actual original gate cwd/
   PYTHONPATH configuration, plus neighboring map and declared-option tests. Verify
   map/plain native use, not only textual spelling. Keep old baseline tests intact.
4. Regenerate/compile/run corrected native examples and complete actual compiler-wheel
   source/package proof where changed canonical source affects the payload. No
   automatic dependencies, corpus regeneration or actual-library production edits.
5. Focus Go shared-user/retirement/remap/unknown-owner/interruptions and common
   preflight preservation. No global all16/full-broad rerun by default: canonical
   core codecs and shared mutation mechanism are unchanged. If focused evidence
   reveals genuine shared impact, report it to root before widening gates.
6. Reconcile exact combined R1 file hashes, baseline/protected/excluded/locks, then
   root-authorized scoped local GWZ correction/receipt and full tuple. Production
   freezes again. Send the SAME TWO original reviewer contexts the merged plan,
   diff and complete receipts; each verifies its own original counterexamples and
   every finding/disposition on its axis. No third/supplementary reviewer.

Acceptance is only two GO verdicts on that same corrected tuple with no open
P0/P1/P2 and the three new integration failures explicitly repaired. Until then the
initial checkpoint is NO-GO. This is remediation round 1 of at most two; reviewers
classify any new architectural root and the cap remains operative. Root coordinates
the later final push only after C++/Go and Swift acceptance; no individual push now.
