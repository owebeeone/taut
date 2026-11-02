# CppGoOneOfCheckpoint R1 — Code+Surface-AXIS REVIEW

**Review object:** The single merged remediation R1, Taut `4222822320cbb22e376f8b387a963e86aad10ff2..c9c5bb0764bbc5a58c65e649468ed5aa67920ded`, within the full pair diff from `b9f99ac88ec585616ffac8bf4fbc2aaf4535fc16`; workspace receipt `bd455ef9174fb13679d0ec6814e43ec1345505fc..1a4d66e05221a1a85e5b4f0fbb10b80befe2b378`. Corrected production frozen; originating Code+Surface closure completed by this report.

**Baseline:**

| Repository | Reviewed HEAD |
| --- | --- |
| Workspace | `1a4d66e05221a1a85e5b4f0fbb10b80befe2b378` |
| Taut | `c9c5bb0764bbc5a58c65e649468ed5aa67920ded` |
| taut-shape-py | `c08c2a1b5197f761c5b0b835c588da512130ceda` |
| taut-shape-rs | `8e92b89ed3a4f218a5a4e018fbfee6301fcc14b4` |
| taut-shape-ts | `1aaeab65e4564a462044d2f5d824cd2f375aae97` |

Sources were read in the isolated R1 clone at `D:/projects/limbo/cpp-go-oneof-scratch/review-r1/code/taut-dev`, using the committed diff and the raw-blob-verified checkout inventory. This is the same originating reviewer and context as the initial Code+Surface report.

**Date:** 3 November 2026, Australia/Sydney.

**Axis:** Code+Surface — architecture, interfaces, call graphs, compatibility and public generation lifecycle. Independent, adversarial, read-only. The other axis runs in parallel; nothing here relies on its current-round review. Filed verbatim by the lane owner.

**Verdict: GO** — all three original P2 findings and all three original P3 findings are CLOSED. No additional blocking finding was established. This verdict accepts the corrected C++/Go pair on this exact tuple and the focused evidence scope below; it does not claim a new global gate or completion of Swift.

---

## 0. Evidence base

### Inspection and integrity

Before reading changed implementation, I repeated the cold root/gen help and both native example READMEs. Their public options, defaults and methods are unchanged. The original comparison with the corpus/json/parity families remains applicable.

I read the complete merged RemPlan-1, the filed original Code+Surface report and initial verdict, Authority, DRAFT, Preparation-R1, focused results index and both target RESULTS-R1 documents. The unchanged full build proposal and applicable process instructions remain the controlling requirements from the original review.

The production/test diff is exactly the seven authorized paths:

- [C++ validation](D:/projects/limbo/cpp-go-oneof-scratch/review-r1/code/taut-dev/taut/src/taut/gen/runtime/validation.hpp): private ancestor identity and its use in `walk`.
- [Go paths](D:/projects/limbo/cpp-go-oneof-scratch/review-r1/code/taut-dev/taut/src/taut/gen/runtime/go/paths.go): private collection identity and list/map constructors.
- [Go ownership planner](D:/projects/limbo/cpp-go-oneof-scratch/review-r1/code/taut-dev/taut/src/taut/gen/go_runtime.py): manifest validation and source selection/retirement, particularly lines 184–294.
- [C++ regressions](D:/projects/limbo/cpp-go-oneof-scratch/review-r1/code/taut-dev/taut/src/tests/test_cpp_oneof.py): the new first-value-child matrix and existing recursion/fault/dependency checks.
- [Go regressions](D:/projects/limbo/cpp-go-oneof-scratch/review-r1/code/taut-dev/taut/src/tests/test_go_oneof.py): formatting import and lines 530–687 covering slice views, retirement, remaps, malformed ownership and persisted interruptions.
- [Map-generation regression](D:/projects/limbo/cpp-go-oneof-scratch/review-r1/code/taut-dev/taut/src/tests/test_map_gen.py): actual sort binding and native map/plain execution.
- [Scaffold regression](D:/projects/limbo/cpp-go-oneof-scratch/review-r1/code/taut-dev/taut/src/tests/test_scaffold.py): ownership receipt and declared/default option checks.

I also inspected the unchanged shared pre-lock checks, locked ownership recheck, complete planning and common output application boundary. No shared mutation machinery, public API, descriptor/codec ABI, core codec, package-data declaration or dependency changed in R1. The remaining changes in the 51-path checkpoint are scoped evidence and review documents.

All 1,067 tracked clone file hashes still matched the dispatch inventory: Taut 779, workspace 54, Python 75, Rust 63 and TypeScript 96. The inventory was associated with raw committed blobs before dispatch, with LF settings established before checkout. The five historical fixture commits were present. Preparation-R1's 50 explicitly hashed files and all seven corrected source hashes verified.

All five HEADs matched the assigned tuple at both review boundaries. Every repository's tracked and cached diff checks returned zero at start and end. No tracked source, original failed probe or Git state was changed by this reviewer.

### Independent execution

Execution used activated **CPython 3.13.5**, existing native tools, disabled pytest plugin autoload and bytecode writes, the prescribed source PYTHONPATH, C++20 with RTTI disabled, and offline/local Go settings. All generated inputs, binaries, caches and pytest outputs stayed under:

`D:/projects/limbo/cpp-go-oneof-scratch/review-r1/code/scratch`

The three original production counterexamples were independently replayed:

| Original counterexample | Replay and result |
| --- | --- |
| C++ first value child | Copied the original probe source without changing its bytes, regenerated the original schema with the corrected compiler, compiled/ran it: `same_address=1 valid=1 complete=1 fast=1 issues=0`. |
| Go finite prefix slice | Copied the original module and native probe source without changing their bytes, regenerated the original schema and ran it: `valid=true complete=true fast=true issues=0`. |
| Go default source→package | Copied the original minimal IR unchanged, built a fresh corrected local foundation, repeated the original CLI source then package generation: both exited zero; the receipt selected package mode with null source root, and the obsolete local runtime/owner receipt were removed. |

The replay directories are `original-cpp`, `original-go-slice` and `original-go-transition` beneath the R1 scratch root. The original failed R0 evidence remains untouched.

An independent targeted pytest invocation from the R1 scratch working directory used absolute test paths, `python -B -m pytest -p no:cacheprovider`, scratch basetemp and XML output. It selected:

- C++ first-value-child matrix, genuine mutual recursion/primitive borrows, allocation faults and independently generated disabled children.
- Go finite-prefix views, original map/slice cycles, default owner retirement/return, surviving users/engine, selected-source remap refusal, malformed ownership and all 40 persisted-retirement cutoffs.
- All three original integration-failure nodes and neighboring declared/default option checks.

**Result: 89 passed in 56.09 seconds**, no failures, skips or deselections. This comprises 19 C++ cases, 61 Go identity/lifecycle cases, the three exact integration nodes and six neighboring option cases.

The exact LF-format node was also independently executed from the clone repository root: **one passed in 0.86 seconds**. It executed the generated/canonical LF-to-gofmt comparisons, rather than stopping at import. This overlaps the 89-case run and is not an additive coverage total.

### Supplied focused receipts and historical global association

I verified the focused index's seven current source hashes and 17 referenced evidence-file hashes, parsed the gate XML results, and read their command/environment associations. The supplied corrected results are:

| Focused execution | Result |
| --- | --- |
| C++ contracts | 109 passed; one duplicate parity wrapper deselected; no failures/skips |
| C++ counterexamples | 18 passed; overlaps the contracts gate |
| Current Go features | 145 passed; no failures/skips/deselections |
| Corrected Go retirement subset | 56 passed, 89 deselected; overlaps the 145 |
| Shared assertions | 16 passed |
| Pair wheel plus scratch-format node | 11 passed |

The initial Go correction attempt's **59 passed, three failed, 83 deselected** receipt remains preserved. Those were imported-supplied persisted-retirement cutoffs. The final explicit-import leftover scan addresses that same authorized boundary; the later 56-case/145-case receipts and my independent cutoff execution qualify the final source. The failed initial attempt is not relabeled as passing.

The current wheel receipt covers the changed canonical runtime payload, isolated wheel-only generation and actual C++/Go source/package compilation/execution. I did not rebuild it or run another broad, full-16 or standalone reference-library gate.

I consumed the completed R0 evidence package, including RESULTS, derived counts, final preservation and raw-after checks, and verified all **43 top-level evidence hashes**. Its exact association remains Taut `42228223…`/workspace `bd455ef9…`:

- Broad: **2,060 passed, six failed, five skipped, 11 authorized deselections; 2,071 selected**.
- All 16 require-all codec variants GREEN, zero violations.
- Three new integration-test failures, now independently closed below; three retained historical baselines: the missing proto-surface document and the two exact Windows CRLF/gofmt assertions.
- Eleven deselections: three unchanged metadata-name reservation cases for the user-owned Enum.case work and eight duplicate parity wrappers.
- Five skips: JavaScript symlink privilege, three POSIX-specific tool/PATH tests and unavailable Rust wasm32 target.
- Preservation: 678 selected source hashes, 679 raw blob associations including Preparation, all 59 pair files, five protected user sources, 35 excluded Python artifacts, five indices and 46 lock/manifest entries.

Those global results are historical evidence, not a rerun on `c9c5bb07…`. Accepted TypeScript R1 library receipts retain their original 315-test/typecheck/build association; no fresh standalone library success is claimed. Current focused preservation audits report only the seven authorized source/test changes and unchanged protected/reference inputs during execution.

## Problem, requirement provenance, and scope

The original operator outcome remains mandatory immutable native metadata, optional exact instance validation, shared reports and typed traversal, preserved structural codecs, and explicit source/package/supplied ownership. The initial review found three concrete failures within that outcome and three test-integration defects.

The coordinator expressly authorized RemPlan-1 M1–M6 in exactly seven production/test paths plus scoped evidence and the corrected managed checkpoint. The corrections address the observed failures directly: distinguish native message identities at overlapping addresses, distinguish slice traversal extents, and distinguish owner retirement from source-owner rebinding. They preserve the existing data models and runtime interfaces.

No dependency/infrastructure prerequisite or broader component expansion was introduced. A local correction to the existing identity keys and pure planner was feasible and sufficient. Tightening accepted user-record grammar and checking imported-supplied leftovers are bounded safeguards for the authorized retirement boundary, including its observed interrupted states; they do not introduce another transaction API.

Reference libraries, protected user authoring work, excluded old Python artifacts, Swift and publication remain outside the editable scope. I found no missing authority or demonstrated necessity gap that blocks this correction.

## 1. Findings and prior-finding closure

No new finding is raised. Closure is my independent originating-axis judgment on the corrected tuple, not an adoption of implementer self-closure.

| Original Code ID | Original-counterexample result | Regression and relevant evidence | Status |
| --- | --- | --- | --- |
| **P2-1** — C++ first-child address overlap | Original unchanged probe now reports the shared address with an empty valid/complete report and true Boolean. | Twelve required/optional × scalar/constrained × source/package/supplied cases passed. Independently generated children remain validation-disabled; invalid children retain exact `child/text` diagnostics. Genuine pointer recursion, shared paths and allocation-fault checks passed. Supplied C++ 109-case gate also passed. | **CLOSED** |
| **P2-2** — Go slice-view identity | Original unchanged finite-prefix probe now reports valid/complete/true with no issues. | Four source/package × rule/no-rule cases passed, including capped prefixes, both invalid shared-leaf paths, local scope, repair/snapshot behavior and a genuine same-start/same-length cycle with differing capacity. Original copied-map-value and slice-cycle checks passed. | **CLOSED** |
| **P2-3** — Go default source-owner retirement | Original minimal CLI source→package request now succeeds and retires the sole old owner. | Four package/imported-supplied × validation off/on transitions build/run and return to source with opposite validation. Two surviving-user/engine cases, three genuine remap refusals, seven malformed/unknown-owner cases and all 40 interruption cutoffs passed independently. | **CLOSED** |
| **P3-1** — LF fixture import | The exact original failing node now executes and passes from source-only scratch cwd and repository root. | Independent scratch run and root run execute actual formatting comparisons; supplied pair-wheel/format 11 and Go 145 receipts agree. Historical CRLF tests remain unchanged. | **CLOSED** |
| **P3-2** — obsolete sort-import assertion | The exact retained test passes with the actual grouped alias. | The test preserves map-positive/plain-negative checks and compiles/runs both native codec round trips. Independently executed; shared 16-case receipt also passes. | **CLOSED** |
| **P3-3** — missing ownership receipt expectation | The exact retained test now passes with API plus ownership receipt. | The receipt's API SHA and supplied/off/null-source-root facts are checked. Neighboring explicit unsupported declarations still reject before output, while undeclared defaults remain accepted. Independently executed; shared 16-case receipt also passes. | **CLOSED** |

## 2. Invariant analysis

**C++ identity and fault behavior.** The ancestor key now pairs the unwrapped object address with the actual static `SchemaBinding`. Optional/shared-pointer views of the same native message obtain the same binding, so genuine cycles remain detectable. An enclosing message and its first child obtain distinct bindings, so address overlap no longer suppresses child traversal. The change adds no RTTI, allocation, live-instance capture or public layout change. Independent allocation-fault execution continued to satisfy the noexcept false/fallback contract.

**Go identity and active-path behavior.** The private key contains a typed starting pointer and traversed length. Capacity is correctly excluded from traversal identity. Map backing identity remains unchanged. The finite-prefix and genuine-cycle cases, copied map values, repeated shared paths and Boolean/report outcomes passed together. No global visited set, coercion or reflection was introduced.

**Retirement and recovery.** The planner withdraws the current user before computing remaining demand, but applies import remapping only to an actually selected source producer/consumer. Retirement does not relabel another user's owner. Positive file hashes, source-user identities, physical-path checks, pre-lock boundaries and common apply machinery remain in force. Unknown user keys/types reject before mutation. The explicit-runtime-import scan catches leftover runtime files even after an interrupted supplied-mode retirement has removed the owner receipt. Independently exercised retries either reached the complete intended retirement or refused with unchanged retry-state bytes; handwritten files and external artifacts survived.

**Surface and compatibility.** Public commands, options/defaults, generated method signatures, descriptor/report families and codec contracts are unchanged. The lifecycle operation that failed in the cold R0 walkthrough now succeeds through the existing CLI and native consumers. Source/package/supplied bindings remain explicit and perform no automatic installation, fallback or child regeneration. The unchanged compatibility proofs therefore remain applicable, reinforced by focused disabled-child, native transition and current-wheel evidence.

I established no new architectural root cause in this remediation round. No broader gate was necessary to resolve a demonstrated shared impact, and none was run by this reviewer.

## 3. Risks and next action

The original documented limits remain: virtual selection is deliberately incomplete; C++ decoded views retain their input-lifetime requirement and fixed-buffer boundary; neither target gains a native JSON route. The three historical broad baseline failures remain visible. There is no corrected-source global-suite or all-16 rerun claim.

The next action is the lane owner's merge of the two original reviewers' verdicts on this exact corrected tuple. This Code+Surface GO authorizes no push, release, tag, registry publication or Swift implementation by this reviewer.
