# CppGoOneOfCheckpoint — State-AXIS REVIEW

**Review object:** Combined C++/Go checkpoint, Taut `b9f99ac88ec585616ffac8bf4fbc2aaf4535fc16..4222822320cbb22e376f8b387a963e86aad10ff2`, with controlling `dev-docs/CppGoOneOfCheckpoint-Draft.md` at the latter revision. Frozen implementation; acceptance pending.

**Baseline:**

| Repository | Exact revision |
| --- | --- |
| Workspace | `bd455ef9174fb13679d0ec6814e43ec1345505fc` |
| Taut | `4222822320cbb22e376f8b387a963e86aad10ff2` |
| Python shape | `c08c2a1b5197f761c5b0b835c588da512130ceda` |
| Rust shape | `8e92b89ed3a4f218a5a4e018fbfee6301fcc14b4` |
| TypeScript shape | `1aaeab65e4564a462044d2f5d824cd2f375aae97` |

Sources were inspected in the assigned isolated full-history clone at `D:/projects/limbo/cpp-go-oneof-scratch/review-r0/state/taut-dev`. Frozen checkout bytes were compared with raw committed Git blobs.

**Date:** 3 November 2026, Australia/Sydney.

**Axis:** STATE — durable-state semantics, filesystem ownership, interruption recovery, locking, immutable publication, native lifetimes and traversal adversity. Independent, adversarial, read-only. The other axis runs in parallel; nothing here relies on it. Filed verbatim by the lane owner.

**Verdict: NO-GO** — one P2 finding blocks; three P3 test-maintenance findings are also recorded. No P0 or P1 finding. I pre-commit to GO on a revision that resolves P2-1 as specified, subject to originating-counterexample verification, appropriate focused gates and unchanged surrounding invariants.

---

## 0. Evidence base

### Authority, scope and source association

Read the assigned canonical reviewer prompt in full; the review-loop skill; workspace `AGENTS.md`/`AGENTS_GWZ.md`; Taut `AGENTS.md`; the complete build proposal, sections 1–9; and the pair Authority, DRAFT and Preparation documents.

Inspected the combined 59-path change inventory, generator/runtime changes, tests, examples, goldens and retained receipts. Detailed State inspection covered:

- `src/taut/gen/scaffold.py:588–951`, particularly complete generation planning, previous-root discovery, locks, locked recheck and application of the merged plan.
- `src/taut/gen/python_runtime.py:49–163` and `242–271`: namespace checks, aliases, physical identity, locks, preflight, replacement and deletion.
- Complete `cpp_runtime.py` and `go_runtime.py`: artifact checks, canonical roots, ownership manifests, user normalization and transitions.
- Complete C++ metadata, descriptor, report and validation resources; the changed C++ generator projection and codec paths.
- Complete Go metadata, descriptor, path, report and validation resources; the changed native generator paths.
- Complete new pair/feature test files and relevant legacy assertions; native example inputs and consumers, allocation injection, owned inventories and source-association receipts.

The starting and final five-repository tuples matched the table above. Final `git diff --exit-code` and `git diff --cached --exit-code` succeeded for all five repositories. All 59 frozen paths matched raw `HEAD` blobs at the end.

Independent inventory checks verified:

- All 58 Preparation non-self hashes and sizes.
- Five protected user-source hashes.
- Four unchanged canonical C++/Go codec resources.
- Four historical commits and the 15 tracked oracle files named in `clone-receipt.json`.
- All 29 hashes in `TypeScript-OwnedFiles-R1.json`, including its 11 corrected shape-library paths.

Accepted ECMAScript association uses the corrected verdict, `TypeScript-OwnedFiles-R1.json`, `RESULTS-R1.md` and `results-r1/`. The original r0 TypeScript manifest was not treated as the current accepted inventory.

The 35 excluded saved-workspace Python artifacts were absent from this reviewer clone. Their preservation is supported by the coordinator’s complete before/after receipt, rather than an assertion that they were tested here.

### Review setup correction

The coordinator detected newline conversion in disposable review clones despite matching HEADs and clean Git state. Native probes and byte-manifest conclusions were paused. The coordinator normalized the disposable checkout to unchanged committed bytes, retained the setup receipt and authorized resumption.

All qualifying reviewer executions occurred after resumption. No implementation source was edited. Reviewer outputs, generated modules, native caches and temporary files stayed under the assigned State scratch directory.

### Independent executions

Activated the prescribed existing toolchains. Reviewer Python was explicitly verified as stable **CPython 3.13.5**. Used the assigned clone source and existing site-packages through `PYTHONPATH`, disabled pytest plugin autoload and bytecode writing, and used `python -B -m pytest -p no:cacheprovider`. Go execution disabled proxy, checksum-service, automatic toolchain and workspace resolution.

The following focused pytest selection passed **40 tests in 14.16 seconds**, with no skips or deselections:

- C++: modified/handwritten preservation; shared users; unavailable old owner; interrupted writes; obstruction/existing lock preservation; raw namespace rejection; junction/equivalent physical roots; allocation-fault noexcept behavior.
- Pair: all eight previous-owner alias-before-lock cases and all-target planning before mutation.
- Go: shared-owner transitions; source consumer engine preservation; sealed descriptor/binding overwrite rejection; constructor/lazy-link snapshots; map/slice cycles and shared paths; interrupted output; generation without target execution and actual forged stale exports.

The exact pytest command selected those named node IDs from `test_cpp_oneof.py`, `test_cpp_go_distribution.py` and `test_go_oneof.py`, using:

```text
--basetemp D:/projects/limbo/cpp-go-oneof-scratch/review-r0/state/scratch/pytest-state
```

The independent native finite-prefix-slice probe under `scratch/slice-prefix` reproduced P2-1 against unchanged generated Go source.

A separate narrow interruption sweep covered C++/Go × disable/move/package transitions × 22 output-operation cutoffs: **132 attempts**, with an independent disabled schema and handwritten file present. It injected failures immediately after persisted replacements/deletions. There were **52 actual interruptions**: 37 retries refused without further byte changes and 15 recovered successfully. The other 80 attempts completed before their selected cutoff. The independent schema API, handwritten file and old owner’s descriptor survived every case. These are probe outcomes, not additional broad-suite passes.

### Complete coordinator integration receipt

Consumed the complete settled receipt under `D:/projects/limbo/cpp-go-oneof-scratch/global-gate-r0`, including:

- `global-results.json`, commands and exact deselections.
- Broad raw log, XML and every retained failure text.
- Codec parity JSON/log.
- Source, protection and tuple before/after snapshots.
- Raw blob association, pair freeze checks, skip classification and actual-library receipt scope.

The settled broad result was **2,060 passed, six failed, five skipped, 11 deselected**, exit 1, with **2,071 selected tests**. The raw pytest duration was 892.49 seconds. All 85 Go feature cases were selected: 84 passed and one failed. All 76 C++ feature cases and ten pair cases were selected.

The six failures consist of:

1. Historical missing `TautProtoApiSurfaceExtensions.md`.
2. Historical Windows Go parity-runner CRLF/gofmt assertion.
3. Historical Windows generated-Go CRLF/gofmt assertion.
4. New Go LF-format test import failure, recorded as P3-1.
5. Stale Go import-spelling assertion, recorded as P3-2.
6. Stale scaffold output-list assertion, recorded as P3-3.

The new LF-format failure occurred at import, before invoking `gofmt`. It supplies no evidence of a formatter mismatch.

All **16 require-all codec variants were GREEN**, with zero governance violations. Python, TypeScript, JS and JS/fc each recorded 88 passes. Each remaining variant recorded 85 passes and three type-satisfied cases. The latter are representability proofs, not unavailable-tool skips.

The exact 11 deselections were three unchanged old Enum metadata-reservation assertions for `name`, `members`, `options`, plus the eight duplicated parity-gate tests in C++, Go, Java, JS, Kotlin, parity governance, Rust and Swift. No deselection was unclassified.

The five skips were the existing JS symlink-privilege case, three POSIX-only parity tool/path tests and the unavailable Rust wasm32 target. Real junction coverage ran.

The 678 selected source hashes, five protected sources, 35 excluded artifacts, five indices, 46 locks/manifests and five HEADs were unchanged. The additional raw audit covered 679 files including Preparation itself; no blob mismatch was recorded. The pair freeze audit had no mismatch.

The actual TypeScript library’s accepted R1 315-test/typecheck/build receipts were reused with verified source association. No fresh standalone library gate is claimed. The earlier old-manifest setup abort ran zero tests and remains historical setup evidence.

## Problem, requirement provenance, and scope

The requested outcome is the current C++/Go pair of the operator’s nine-language implementation: mandatory immutable descriptors, optional exact instance validation methods, general shared immutable reports, typed traversal, preserved structural codecs, explicit source/package/supplied delivery, one actual foundation owner and safe generator-owned transitions.

The observed gap was that these two targets lacked that descriptor/validation foundation and their prior runtime-copy route lacked the required ownership/user lifecycle. The proposal supplies product requirements; the later Authority amendments authorize implementation, the exact 59-path freeze, one local checkpoint and this combined two-axis review. The DRAFT supplies implementation intent without expanding authority.

The modified components fit the assigned boundary: C++/Go target production, tests/examples, shared scaffold/CLI and package-data integration. Python/Rust/TypeScript shape revisions are reference-only. User-owned Enum.case work, excluded old Python artifacts, Swift, releases and registry/toolchain changes remain outside this object.

No unsupported infrastructure prerequisite was identified. Existing native compilers and canonical resources demonstrably support source and local-package consumers; native artifact and allocation checks run through that route. No new library repository, JSON parser, compiler or dependency installation is necessary.

The remedy addresses the requested gap. P2-1 needs a localized correction to the existing Go ancestry identity, with no new ownership model or global visited set. The three integration-test failures need bounded test corrections or explicit dispositions; they do not justify changing the authorized runtime behavior to satisfy obsolete literals.

No blocking authority or necessity gap was found.

## 1. Findings

### [P2-1] Go slice ancestry conflates finite prefixes with their containing slice

**Location:** `src/taut/gen/runtime/go/paths.go:9–18`; used by `go_metadata.py:223–232` and `runtime/go/validation.go:11–20`.

**Violated invariant:** Only an object already on the active ownership path is a cycle. Finite shared children must be traversed at every path.

`ListIdentity` identifies a nonempty slice using only its first element’s typed address. Two slices beginning at the same element but having different lengths therefore have equal identities. Generated traversal enters the whole outer slice before visiting its elements, so a nested finite prefix is rejected before its children are visited.

**Reproduction:** Generate enabled source output for:

```python
k = Enum("Choice", text=0, empty=1)
s = schema(
    k,
    Node=Msg(
        tag=F(1, OneOf(k)),
        text=F(2, STR, Case(tag=k.text)),
        children=F(3, List(Ref("Node"))),
    ),
)
emit(s, root, langs=["go"], services=[], runtime=True, validation=True)
```

Use a local module, import its generated package as `a`, and execute:

```go
list := make([]a.Node, 2)
list[0] = a.Node{Tag: a.ChoiceEmpty}
list[1] = a.Node{Tag: a.ChoiceEmpty, Children: list[:1]}
root := a.Node{Tag: a.ChoiceEmpty, Children: list}

report := root.Validate()
```

The graph is finite: root → two elements; element 1 → element 0; element 0 has no descendants. Executed with `go run ./app` under the prescribed offline environment, the probe observed:

```text
finite graph: valid=false complete=true fast=false issues=1
code=validation.ownership_cycle path=/children/[1]/children
```

Giving element 0 a valid selected text payload still leaves the false cycle. Making that payload absent produces the first-path missing-payload issue plus the spurious cycle; traversal omits the required missing-payload diagnostic at `/children/[1]/children/[0]/text`.

**Impact:** Valid supported native values are rejected, and repeated-path diagnostics are replaced by an invented cycle. Boolean/report agreement alone does not catch the defect because both share the incorrect identity.

**Required correction:** Distinguish observable slice ranges, including their length alongside the typed start identity, or use an equivalent identity that preserves finite overlapping-range traversal. Retain active-path tracking and actual map/slice-cycle detection.

**Closure test:** Compile and run the exact finite-prefix case, requiring an empty complete report and Boolean true. Repeat with an invalid shared leaf, requiring two correctly located payload diagnostics and no cycle. Retain genuine cyclic slices/maps, ordinary shared paths and local-mode checks.

### [P3-1] The new LF-format test depends on the repository root being importable

**Location:** `src/tests/test_go_oneof.py:365`.

**Violated invariant:** The required native formatting check must run under the settled gate’s supported source-path configuration.

The complete gate failed on:

```python
from src.tests.test_go import _generated_go
```

with `ModuleNotFoundError: No module named 'src'`. Its configured source path makes `taut` available, but does not promise the repository parent as a Python package root.

**Impact:** This invocation never checks generated or canonical bytes with `gofmt`; the broad gate remains red. This is a test-import defect, not a formatting failure.

**Required correction:** Import the helper through the established pytest test-module route or extract it to an appropriately importable test helper.

**Closure test:** Run this exact node from the integration gate’s working directory/configuration and from the repository root, verifying that formatting checks execute and pass without adding an accidental root-path prerequisite.

### [P3-2] The map test still requires the previous literal import spelling

**Location:** `src/tests/test_map_gen.py:28–29`.

**Violated invariant:** Migration assertions must continue checking the intended property after authorized generation changes.

The test requires the substring `import "sort"`. Current output uses a grouped import with alias `tautsort`, and codec statements use that alias. The settled native/parity evidence does not show a missing sorting dependency.

**Impact:** A stale textual assertion fails the broad suite and no longer accurately tests conditional sorting imports.

**Required correction:** Update the assertion to recognize the current import binding while retaining both map-positive and plain-schema-negative checks.

**Closure test:** The exact node passes and still fails if sorting is omitted for maps or unnecessarily imported for the plain schema.

### [P3-3] The scaffold test excludes the newly required ownership receipt

**Location:** `src/tests/test_scaffold.py:81`.

**Violated invariant:** Tests of declared-versus-effective options must accommodate authorized ownership output.

The test expects `emit` to return only `go/api.go`; the current result additionally names `go/.taut-go-outputs.json`. The receipt is required for safe output ownership. The underlying assertion that defaulted, undeclared options should not be rejected succeeds far enough to generate both files.

**Impact:** The broad suite fails on an obsolete output inventory, obscuring the actual option behavior being tested.

**Required correction:** Attribute the receipt as the intended migration and update this test without removing its declared/default option distinction.

**Closure test:** This exact node and the neighboring declared-option refusal tests pass; ownership receipt emission remains intact.

## 2. Invariant analysis

**Complete preflight and physical ownership:** C++ and Go collect target text before the common application step. The pair handwritten-conflict test passed without leaving C++ files behind. Raw namespace checks precede Path conversion. Alias/non-file previous manifests and raw previous-root ancestors are rejected before lock attempts in the eight-target junction regression.

**Lock scope and owner changes:** Discovery includes current schema, selected source and recorded old source roots. The locked recheck refuses a concurrently changed owner outside the acquired set. Equivalent physical roots and normalized schema-user identities avoid treating a spelling change as a second user. Go import-path remapping of an existing physical owner is refused. No supported transition counterexample was found that deletes another recorded user’s engine.

**Interrupted durable states:** Replacement is atomic per file, rather than transactional across the complete plan. The permitted recovery grammar includes the previous generation, a completed generation and inconsistent ownership/content requiring explicit migration or a fresh root. Tests and the interruption sweep showed refusals on inconsistent state without subsequent adoption, cleanup or handwritten-file loss. I found no basis to demand stronger transactional success than the proposal requires.

**C++ publication and lifetime:** Generated tables use static immutable storage and captureless typed readers. Recursive metadata links do not eagerly expand the graph. Primitive and map-key operations borrow existing native storage; reports own diagnostic data. The allocation-fault test passed first fallback construction, copying/moving and getters under fail-all allocation, plus successive report failures. Boolean mode constructs no report/diagnostic containers. Existing borrowed codec input lifetimes and fixed-buffer policy remain the stated boundary.

**Go immutable publication:** Sealed readers prevent external whole-value overwrite of shared backing structs. Constructors and container/options getters snapshot data. Lazy links resolve once; schema publication checks category/owner links and prevents validation against unpublished descriptors. Actual-artifact guards, disabled children and source-consumer engine preservation passed their focused checks. P2-1 is a traversal identity defect within that otherwise functioning boundary.

**Semantics and codecs:** General report snapshots, invalid mutable drafts, explicit validation and structural codec separation are supported by native tests and source-associated receipts. Virtual selection remains explicitly incomplete while supported child traversal continues. The all-16 codec gate is green. The three new broad failures do not establish a codec regression, but their test defects must remain disclosed and dispositioned.

## 3. Risks and next action

The combined object remains blocked by P2-1. The passing existing cycle tests cover genuine cycles and ordinary sharing, but miss overlapping slice ranges; the native counterexample demonstrates that gap.

The sole next action is one root-authorized merged remediation patch, including the bounded slice-identity correction and explicit dispositions for the three new integration-test failures, followed by originating State replay and appropriate focused gates. No source correction, commit, push, release, Swift work or duplicate global gate was performed by this reviewer.
