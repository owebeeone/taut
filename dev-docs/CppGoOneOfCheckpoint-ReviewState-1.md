# CppGoOneOfCheckpoint R1 — State-AXIS REVIEW

**Review object:** One merged remediation, Taut `4222822320cbb22e376f8b387a963e86aad10ff2..c9c5bb0764bbc5a58c65e649468ed5aa67920ded`, within the combined C++/Go checkpoint. Controlling DRAFT and authorized `CppGoOneOfCheckpoint-RemPlan-1.md` were read at the corrected revision. Corrected production is frozen; this is originating State closure, remediation round 1.

**Baseline:**

| Repository | Exact corrected revision |
| --- | --- |
| Taut | `c9c5bb0764bbc5a58c65e649468ed5aa67920ded` |
| Workspace | `1a4d66e05221a1a85e5b4f0fbb10b80befe2b378` |
| Python shape | `c08c2a1b5197f761c5b0b835c588da512130ceda` |
| Rust shape | `8e92b89ed3a4f218a5a4e018fbfee6301fcc14b4` |
| TypeScript shape | `1aaeab65e4564a462044d2f5d824cd2f375aae97` |

Source inspection and executions used `D:/projects/limbo/cpp-go-oneof-scratch/review-r1/state/taut-dev/taut`. Raw committed blobs, the settled diff and checkout bytes were compared. The original failed R0 probes were preserved.

**Date:** 3 November 2026, Australia/Sydney.

**Axis:** STATE — durable-state semantics, filesystem ownership, crash/restart legality, locking, immutable publication, lifetimes and active-path traversal. Independent, adversarial, read-only. The other axis runs in parallel; nothing here relies on its current-round report. Filed verbatim by the lane owner.

**Verdict: GO** — all four original State findings are CLOSED. No open P0, P1, P2 or P3 finding, and no new architectural root cause identified. This verdict accepts the corrected C++/Go pair on this exact tuple and the stated evidence scope.

---

## 0. Evidence base

### Documents, diff and preservation

Read the complete canonical State continuation prompt, merged RemPlan-1, original State report, initial merged verdict, corrected Preparation-R1, focused results index and both targets’ RESULTS-R1 records. Revisited the pair Authority/DRAFT and original preparation. The previously read full build proposal remains controlling; Git comparison verified it unchanged from R0, together with Authority and DRAFT.

Reviewed all seven authorized source/test changes:

- `src/taut/gen/runtime/validation.hpp`: private ancestor key and `walk` comparison, approximately lines 24 and 91–102.
- `src/taut/gen/runtime/go/paths.go:9–30`: typed collection start, traversed length and unchanged map-backing identity.
- `src/taut/gen/go_runtime.py:182–293`: manifest grammar, user withdrawal, source selection versus retirement, unknown-file scan and planned cleanup.
- `src/tests/test_cpp_oneof.py:183–207`: first required/optional value-child matrix.
- `src/tests/test_go_oneof.py:362–374` and `530–690`: portable formatter import, finite-prefix/capacity cases, retirement/return, other users, remaps, malformed ownership and persisted cutoffs.
- `src/tests/test_map_gen.py:31–56` and `src/tests/test_scaffold.py:80–87`: actual sorting dependency use and exact ownership receipt assertions.

Rechecked the relevant unchanged Go descriptor/report/validation and generated traversal assumptions, C++ binding/report/fallback assumptions, and common physical identity, previous-owner pre-lock checks, locks, locked recheck and `apply_outputs` ordering. Git comparison confirmed that the shared scaffold, physical/lock/apply helper, CLI and package-data configuration did not change in this remediation.

At start, all five HEADs matched the corrected tuple and every tracked/index diff was empty. Independent binary Git batch reads verified all **1,067 tracked checkout files** against raw committed blobs: Taut 779, workspace 54, Python shape 75, Rust shape 63, TypeScript shape 96. Verified all **50 Preparation-R1 non-self hash/size records** and that exactly the authorized seven paths changed under `src/`.

Final checks again confirmed all five expected HEADs, empty tracked/index diffs and all 1,067 raw-associated hashes. Five protected user-source hashes and four unchanged canonical C++/Go codec hashes matched their original preparation records. The original State report remains SHA256 `a401ede7f0ad06ab795dc767f0e9c383975169cbac64366e250ef9e9d8a164b7`.

The supplied equal protection snapshots cover 678 selected source files, five protected user sources, 35 excluded old Python artifacts, five indices and 46 locks/manifests. The excluded saved-workspace artifacts were not used as reviewer inputs or modified. Reference-library production and dependency declarations remain unchanged. Accepted TypeScript association remains the corrected ECMAScript R1 inventory/results at shape revision `1aaeab65`; no original R0 manifest is substituted for it.

### Independent native counterexample and focused executions

Used activated existing toolchains and explicitly verified stable **CPython 3.13.5**. Python used the R1 clone’s `src` plus the prescribed existing site-packages, with plugin autoload and bytecode writing disabled. Pytest used `python -B -m pytest -p no:cacheprovider`, R1 scratch `--basetemp` and R1 scratch `--junitxml`. C++ compiled as C++20 with RTTI disabled. Go used `GOPROXY=off`, `GOSUMDB=off`, `GOTOOLCHAIN=local`, `GOWORK=off`; temporary files and native caches stayed in R1 scratch.

Copied the original failed native Go probe source unchanged into R1 scratch, freshly generated its schema with the corrected compiler, and ran `go run ./app`. Its source SHA256 remains `b390a4b3a979ff2eb116b865c5f6c5bcc90245ce6e3cc7f90bf1476c25a87816`. Observed:

```text
finite graph: valid=true complete=true fast=true issues=0
repaired leaf: valid=true fast=true issues=0
invalid shared leaf: issues=2
oneof.payload_missing
oneof.payload_missing
```

The replay result is under `scratch/original-slice-prefix/replay-result.json`. The original R0 source and failed result were not touched.

The independently selected native/state command passed **107 tests in 57.66 seconds**, with no skips or deselections. `scratch/focused.xml` records every selected case. The selection comprised:

- C++ first-value-child matrix, genuine mutual recursion/primitive borrows, allocation faults, independently generated disabled children, interruption and equivalent physical-root cases.
- Go finite-prefix source/package matrix, original map/slice cycles and path-local sharing, default-source retirement/return, surviving source users/engine, actual source-import remap refusal, malformed owner inventory and all 40 persisted retirement cutoffs.
- Go sealed metadata/binding overwrite rejection, lazy-link/input snapshots, general report snapshots, fast-mode diagnostic-constructor exclusion and raw namespace checks.
- Eight-target previous-owner alias-before-lock rejection and pair complete-plan preservation.
- The exact map-import and scaffold-receipt nodes, neighboring declared-option refusal cases and target-binding option checks.

The three original integration-failure nodes also passed together from **R1 scratch with source-only PYTHONPATH**: **3 passed in 2.19 seconds**, `scratch/integration-cwd.xml`. These executed the actual LF/gofmt comparisons, native map/plain round trips and receipt/hash checks. The exact LF-format node additionally passed from the clone repository root: **1 passed in 0.82 seconds**, `scratch/format-root.xml`. These runs overlap the selected checks; totals are not added.

An additional narrow retirement probe forced the owner receipt to disappear before the first stale source deletion, leaving runtime source files behind. All four package/imported-supplied × validation-off/on cases refused the next attempt as unknown/handwritten runtime, with no further tree changes. Handwritten files and the actual external artifact were unchanged. This directly attacks the failed-first retirement state rather than depending on one set-deletion order.

### Supplied corrected-source receipts

Verified focused XML hashes and parsed results against committed `CppGoOneOfCheckpoint-FocusedResults-1.json`:

| Corrected-source run | Result |
| --- | --- |
| C++ contracts | 109 passed, one duplicate parity wrapper deselected; no failures/skips |
| C++ counterexamples | 18 passed; overlaps contracts |
| Go current feature file | 145 passed; no skips/deselections |
| Corrected Go retirement subset | 56 passed, 89 deselected; overlaps 145 |
| Shared assertions | 16 passed |
| Pair wheel plus scratch-format node | 11 passed |

The first Go correction attempt remains **59 passed, three failed, 83 deselected**. Its three persisted imported-supplied retirement failures are retained. The later explicit-runtime-import unknown-file scan, 56-case corrected receipt and final 145-case receipt apply to the final source. The failed-first record is not overwritten or counted as a pass.

Inspected the supplied current compiler-wheel evidence without rebuilding it. Independently opened the retained wheel and compared all **13 C++/Go canonical runtime resources** with the corrected clone; every byte matched. Wheel SHA256: `68e70df9bc7c2583a335f6387538ba816a4a65dfa6a3b2fe864663d0ec905e0b`. Its supplied native source/package execution proof is therefore associated with the actual corrected resources. No duplicate wheel build was run by this reviewer.

### Historical complete global receipt — retained scope

The complete global gate remains evidence of **Taut `4222822320cbb22e376f8b387a963e86aad10ff2` / workspace `bd455ef9174fb13679d0ec6814e43ec1345505fc`**, not a new global run on the corrected tuple.

Its result was **2,060 passed, six failed, five skipped, 11 authorized deselections**, 2,071 selected, exit 1; all 16 require-all codec variants were GREEN with zero violations. The six failures were the three established baselines plus the three integration-test defects now independently closed below. The LF test’s original failure was an import error before formatter execution.

The exact 11 deselections remain three pending-user Enum metadata-reservation assertions (`name`, `members`, `options`) plus eight duplicate parity wrappers. The five skips remain the JS symlink-privilege case, three POSIX-only parity tool/path cases and unavailable Rust wasm32 target. No new baseline category or suppression is introduced.

During this continuation, consumed the completed global RESULTS and supplemental final packaging, and verified all **43 top-level evidence hashes**. Final derived counts, source preservation, raw-source-after and raw-pair-after confirm 678 selected source hashes, 679 raw blob associations including Preparation, all 59 pair files, five protected sources, 35 exclusions, five indices, 46 locks/manifests and five HEADs unchanged in that historical run. The older-manifest setup abort still represents zero executed tests.

The accepted TypeScript library’s R1 315-test/typecheck/build receipts remain reused exact-source evidence. No new broad, all-16 parity or standalone reference-library gate ran during this closure. No current full-suite-green claim is made.

## Problem, requirement provenance, and scope

The operator’s requested C++/Go outcome remains mandatory immutable metadata, exact optional instance validation, shared owned reports, typed traversal, explicit canonical source/package/supplied ownership and safe output transitions, while preserving mutable drafts and structural codecs.

R0 demonstrated a State defect in slice identity and three integration-test defects. The merged original-round inputs additionally demonstrated C++ first-subobject address overlap and Go local-source retirement refusal. The coordinator explicitly authorized M1–M6 and the exact seven source/test paths plus scoped evidence, including the bounded retirement classification correction. The generated plan is not treated as independent product authority.

The patch repairs those observations inside the existing implementations. Typed address/binding and slice extent correct identity without a global visited set or native-layout change. Go retirement is distinguished from consuming/remapping a surviving source owner inside the existing pure planner. The shared write/lock mechanism, public descriptor/codec ABI, compiler route, dependencies and target scope remain unchanged.

Existing supported native routes demonstrate feasibility; no infrastructure or dependency prerequisite was added. The localized fixes address the observations without a new transaction API, runtime discovery, parser, library repository or application-time compiler. Reference shapes, user-owned Enum.case work, old excluded artifacts, Swift, publication and toolchain changes remain outside the editable scope.

I found no unsupported prerequisite, unauthorized component expansion or authority gap. The remediation restores existing invariants; it introduces no new architectural root requiring redesign or another review round.

## 1. Findings and prior-finding closure

No new finding is raised. Every original State ID has been independently replayed and is CLOSED:

| Original State ID | Original counterexample replay | Regression and relevant evidence | Status |
| --- | --- | --- | --- |
| P2-1 — finite slice prefixes falsely cycle | Unchanged original native probe now returns valid/complete/fast true; invalid shared leaf yields two payload diagnostics and no cycle | Source/package × constrained/unconstrained prefix matrix verifies both locations, capped prefix, genuine capped-view cycle, local mode, repair and immutable prior report; original map-copy/slice-cycle test also passes | **CLOSED** |
| P3-1 — formatter fixture requires repository root importability | Exact original node passes from scratch with only the prescribed source path and from repository root | Actual generated and canonical LF/gofmt equality checks execute; 3-case scratch replay and separate root replay pass | **CLOSED** |
| P3-2 — literal sort import expectation is stale | Exact original node passes with the actual grouped alias import | It requires the actual binding’s `Slice` use, rejects sorting dependency/use for the plain schema, and compiles/runs both native codec round trips | **CLOSED** |
| P3-3 — ownership receipt omitted from expected outputs | Exact original node passes with API plus ownership receipt | Receipt owns the exact API SHA256 and records supplied/off/null-source state; neighboring explicit unsupported declaration refusals and target-specific option checks pass | **CLOSED** |

These closures are the originating State reviewer’s judgments, not adoption of implementer assertions or current-round peer conclusions. M1 and M3 were also attacked for State effects below; the other originating reviewer retains responsibility for its own IDs.

## 2. Invariant analysis

**Active-path identity and cleanup.** Go collection identity now combines the typed first-element pointer with traversed length. Different finite prefixes can be traversed; capacity changes alone do not disguise an actual cycle. Existing map-backing identity still catches cycles through copied map values. Shared children remain checked at each path, fast/report results agree, and early returns preserve active-path cleanup. The original counterexample, expanded regression and original real-cycle tests all pass.

**C++ address overlap and lifetime.** The private key combines native binding identity and object address. A parent and its first required/optional value child can share an address without sharing a binding. Independently generated engine-free children traverse correctly in all three distributions, valid input passes, and invalid children report the actual child/text path. Real recursive pointer cycles still fail. The added key does not allocate, capture instances or change borrowed primitive/key storage; allocation-fault fallback construction, move/copy and getters remain verified.

**Retirement versus remapping.** The Go planner withdraws the current normalized user before calculating remaining ownership, but changes `import_path` only for actual source production or explicit source consumption. Verified sole-user local source can retire for an external package/imported supplied owner and later return to source. Existing users retain their import identity and required engine. Actual selected-source remaps still reject in source/package/supplied modes. Missing, modified, unknown and malformed ownership refuses before output mutation; stricter user-record checks reject unsupported keys/types and relative identities.

**Crash recovery remains fail closed.** All 40 persisted retirement cutoffs and the four forced owner-receipt-first states behaved legally: either retry completed a known retirement or refused without additional changes. The explicit imported-supplied scan closes the retained failed-first leftover state. No source content was adopted or deleted as unowned data; handwritten content and external artifacts survived. Inconsistent multi-file generations may still need inspection/migration or a fresh root, as the original contract permits.

**Physical roots and mutation boundaries.** Shared raw namespace checks, physical identity, previous-root discovery, old/current owner locks, locked recheck, complete-plan preflight and per-file application remain unchanged. Fresh namespace, junction/equivalent-root, all-eight-target pre-lock alias and cross-target no-partial-plan tests pass. M3 changes source-use classification inside the planner, not lock scope or the common mutation mechanism.

**Immutable state and validation boundaries.** Fresh sealed-metadata, constructor/lazy-link snapshot, general report snapshot and fast-path constructor-exclusion tests pass. Supported child traversal and local/recursive behavior remain intact. Invalid drafts and structural codecs are exercised independently of validation. Virtual selection remains deliberately incomplete. The original borrowed C++ codec lifetime and fixed-buffer contract are retained.

**Test corrections retain their purpose.** The three integration repairs now execute the intended checks rather than deleting assertions: formatting is actually compared, conditional sort imports are paired with native use, and receipt migration is tied to exact API ownership while declaration refusal remains tested. Historical baseline tests were not weakened or relabeled.

## 3. Risks and next action

No open State defect remains on the corrected tuple. Evidence is focused corrected-source native/state/package verification plus the unchanged historical complete R0 global receipt; there is no corrected-source broad/full-16 or standalone library rerun.

The next action is the lane owner’s merge of the two original reviewers’ verdicts on this exact corrected tuple and filing of the unedited closure testimony. This State GO authorizes no release, tag, registry publication, individual push or Swift implementation. No source edit, Git mutation or duplicate global/wheel build was performed by this reviewer.
