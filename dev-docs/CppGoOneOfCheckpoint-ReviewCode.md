# CppGoOneOfCheckpoint — Code+Surface-AXIS REVIEW

**Review object:** Combined Taut diff `b9f99ac88ec585616ffac8bf4fbc2aaf4535fc16..4222822320cbb22e376f8b387a963e86aad10ff2`, its controlling DRAFT, and workspace receipt `3a5d103ab09561459ce61c85707b22fd4139f60c..bd455ef9174fb13679d0ec6814e43ec1345505fc`. Frozen checkpoint; acceptance pending.

**Baseline:**

| Repository | Reviewed HEAD |
| --- | --- |
| Workspace | `bd455ef9174fb13679d0ec6814e43ec1345505fc` |
| Taut | `4222822320cbb22e376f8b387a963e86aad10ff2` |
| taut-shape-py | `c08c2a1b5197f761c5b0b835c588da512130ceda` |
| taut-shape-rs | `8e92b89ed3a4f218a5a4e018fbfee6301fcc14b4` |
| taut-shape-ts | `1aaeab65e4564a462044d2f5d824cd2f375aae97` |

Sources were inspected in the assigned isolated clone at `D:/projects/limbo/cpp-go-oneof-scratch/review-r0/code/taut-dev`, with committed blobs used to verify source association.

**Date:** 3 November 2026, Australia/Sydney.

**Axis:** Code+Surface — architecture, interfaces, call graphs, compatibility and the public generation workflow. Independent, adversarial, read-only. The other axis runs in parallel; nothing here relies on it. Filed verbatim by the lane owner.

**Verdict: NO-GO** — three P2 findings block acceptance; three additional P3 test integration defects require correction. I pre-commit to GO on a revision that resolves P2-1 through P2-3 as specified, passes their closure checks, and reconciles the new integration failures without introducing another blocking defect.

---

## 0. Evidence base

### Source and authority inspection

The mandatory cold pass preceded source/design inspection:

- Executed `python -B -m taut.cli --help` and `gen --help`.
- Read both native example READMEs.
- Subsequently compared the existing `corpus`, `json` and `parity` help.
- Read the full build proposal, Authority, DRAFT and Preparation; workspace AGENTS/AGENTS_GWZ, Taut AGENTS and the review-loop skill.
- Inspected the 59-path checkpoint inventory, production changes, tests, examples, goldens and associated drafting receipts. Inspected the workspace receipt: it changes the managed Taut revision and corresponding integrity digest.

Principal implementation inspection covered:

| Source | Inspected scope |
| --- | --- |
| [cpp.py](D:/projects/limbo/cpp-go-oneof-scratch/review-r0/code/taut-dev/taut/src/taut/gen/cpp.py) | Native projection, codecs, recursion, publication and wrappers |
| [cpp_metadata.py](D:/projects/limbo/cpp-go-oneof-scratch/review-r0/code/taut-dev/taut/src/taut/gen/cpp_metadata.py) | Lines 1–161 |
| [cpp_runtime.py](D:/projects/limbo/cpp-go-oneof-scratch/review-r0/code/taut-dev/taut/src/taut/gen/cpp_runtime.py) | Lines 1–227 |
| [descriptors.hpp](D:/projects/limbo/cpp-go-oneof-scratch/review-r0/code/taut-dev/taut/src/taut/gen/runtime/descriptors.hpp) | Lines 1–364 |
| [reports.hpp](D:/projects/limbo/cpp-go-oneof-scratch/review-r0/code/taut-dev/taut/src/taut/gen/runtime/reports.hpp) | Lines 1–128 |
| [validation.hpp](D:/projects/limbo/cpp-go-oneof-scratch/review-r0/code/taut-dev/taut/src/taut/gen/runtime/validation.hpp) | Lines 1–116 |
| [go.py](D:/projects/limbo/cpp-go-oneof-scratch/review-r0/code/taut-dev/taut/src/taut/gen/go.py) | Native declarations, naming and structural codecs |
| [go_metadata.py](D:/projects/limbo/cpp-go-oneof-scratch/review-r0/code/taut-dev/taut/src/taut/gen/go_metadata.py) | Lines 1–287 |
| [go_runtime.py](D:/projects/limbo/cpp-go-oneof-scratch/review-r0/code/taut-dev/taut/src/taut/gen/go_runtime.py) | Lines 1–286 |
| [Go descriptors](D:/projects/limbo/cpp-go-oneof-scratch/review-r0/code/taut-dev/taut/src/taut/gen/runtime/go/descriptors.go) | Lines 1–649 |
| [Go paths](D:/projects/limbo/cpp-go-oneof-scratch/review-r0/code/taut-dev/taut/src/taut/gen/runtime/go/paths.go) | Lines 1–63 |
| [Go reports](D:/projects/limbo/cpp-go-oneof-scratch/review-r0/code/taut-dev/taut/src/taut/gen/runtime/go/reports.go) | Lines 1–69 |
| [Go validation](D:/projects/limbo/cpp-go-oneof-scratch/review-r0/code/taut-dev/taut/src/taut/gen/runtime/go/validation.go) | Lines 1–121 |
| [scaffold.py](D:/projects/limbo/cpp-go-oneof-scratch/review-r0/code/taut-dev/taut/src/taut/gen/scaffold.py) | Target adapters, forwarding, planning, locking and application |
| [cli.py](D:/projects/limbo/cpp-go-oneof-scratch/review-r0/code/taut-dev/taut/src/taut/cli.py) | Arguments, defaults and forwarding |

The historical fixture commits were verified as present:

- `b9f99ac88ec585616ffac8bf4fbc2aaf4535fc16`
- `68c24a899345367f3026372d3c67737751215a0e`
- `57c56d5f7d727eb483ac9fd89c482f6a44f7913e`
- `1607b6e0b000f607153b2ec20fc244aeb5952744`

All 15 tracked oracle files matched their committed blobs.

### Clone setup and independent execution

The initial clone had checkout newline conversion despite matching HEADs and clean Git diffs. The parent paused execution, corrected local checkout configuration and restored unchanged committed bytes. Pre-pause native evidence was discarded and the counterexample was regenerated and rerun afterward. I independently verified all 59 checkpoint files against raw HEAD blobs after that correction.

Execution used activated **CPython 3.13.5**, existing native tools, disabled pytest plugin autoload and bytecode writes, and the prescribed PYTHONPATH. TEMP/TMP, native caches, generated sources and binaries remained under:

`D:/projects/limbo/cpp-go-oneof-scratch/review-r0/code/scratch`

Go execution disabled proxy, checksum service, toolchain substitution and workspace resolution.

The permitted targeted command used `python -B -m pytest -p no:cacheprovider`, a scratch `--basetemp`, and these nodes:

- C++: `test_reference_behavior`, `test_allocation_fault_noexcept`, `test_independent_disabled_child_shared_owner`, `test_mutual_recursion_and_primitive_borrows`, `test_actual_external_facts_guard`, `test_malformed_known_constraint_is_configuration_error`.
- Go: `test_python_normalized_conformance`, `test_mandatory_metadata_owned_snapshots_engine_free`, `test_reports_are_general_owned_snapshots_and_bad_rules_are_configuration`, `test_actual_stale_artifact_is_rejected`.

**Result: 28 passed in 57.22 seconds.**

Additional narrowly scoped native probes established P2-1 and P2-2. A CLI generation/use/transition walkthrough established P2-3. These were necessary adversarial checks of identity and lifecycle contracts, not duplicate broad/parity gates.

### Complete root-assigned integration receipt

I consumed the complete receipt under `D:/projects/limbo/cpp-go-oneof-scratch/global-gate-r0`, including:

- `global-results.json`, `commands.json`, `broad-regression-tests.log` and `broad-results.xml`;
- `codec-parity.json` and its log;
- exact deselection and skip classifications;
- source/protected/tuple before-and-after snapshots;
- raw source/blob association and pair-freeze checks;
- actual-library receipt scope.

The settled broad result was **2,060 passed, six failed, five skipped, 11 deselected; 2,071 selected**. All 85 Go feature cases were selected: **84 passed, one failed**. All 76 C++ feature and ten combined-pair cases were selected.

Three failures are the explicitly retained historical baselines:

1. Missing `TautProtoApiSurfaceExtensions.md`.
2. `test_go_runtime_and_parity_runner_are_gofmt_clean`: existing Windows temporary-file newline behavior.
3. `test_generated_go_is_gofmt_clean`: existing Windows temporary-file newline behavior.

The other three failures are new and are assessed individually as P3-1 through P3-3 below. The new LF formatting test failed during Python import; the receipt does **not** demonstrate a formatter mismatch.

The exact 11 deselections were:

- The three unchanged `test_enum_authoring_metadata_namespace_is_reserved_early` cases: `[name]`, `[members]`, `[options]`, excluded for the user-owned pending Enum.case work.
- Eight redundant parity wrappers: C++, Go, Java, JavaScript, Kotlin, Rust and Swift target wrappers, plus `test_full_gate_governance_clean`. Their work was covered by the separate all-16 gate.

There were no unclassified deselections.

The five skips were the existing JavaScript symlink-privilege case; two POSIX shell-script tool-selection tests; one POSIX PATH-isolation test; and the Rust wasm32 target test because that target was unavailable.

The separate `require_all=True` codec gate ran **all 16 variants, all GREEN, zero governance violations**:

- Python, TypeScript, JavaScript and JavaScript/fc: 88 passes each.
- Rust, C++, Swift, Go, Kotlin and Java, each ordinary/fc: 85 passes plus three type-satisfied cases each.

The accepted TypeScript R1 inventory associates the unchanged 28 library production files with its prior **315-test/typecheck/build** receipts at `1aaeab65…`. This was receipt reuse, not a fresh standalone library gate. The older r0 manifest was not used as current proof.

The 678 selected source hashes, five protected user sources, 35 excluded Python artifacts, five indices and 46 lock/manifest entries were unchanged. The raw blob audit covered 679 files, including Preparation itself, with no mismatches. Before/after tuples matched.

Final reviewer checks independently reconfirmed all five assigned HEADs. Both `git diff --exit-code` and `git diff --cached --exit-code` returned zero in every repository.

## Problem, requirement provenance, and scope

The operator requested native OneOf support across all nine languages, with mandatory immutable descriptors, optional exact instance validation methods, shared general reports, typed traversal, preserved structural codecs and explicit runtime distribution. Later instructions selected the current C++/Go pair and authorized this exact local checkpoint and one combined two-axis review.

The observed gap was concrete: the prior C++/Go route lacked the required descriptors, shared validation/report machinery and safe runtime ownership lifecycle. Extending the existing emit/CLI/native codec route addresses that gap. The source/package builders exercise existing C++20 and Go toolchains; no dependency or infrastructure upgrade was established as necessary or introduced as a prerequisite.

Authorized components comprise the frozen C++/Go production, tests and examples, shared scaffold/CLI/package resources, and managed workspace receipt. Python/Rust/TypeScript libraries remain reference-only. The user-owned Enum.case patch, excluded old Python artifacts, Swift implementation and publication remain outside this review.

The design’s static C++ adapters and sealed Go readers are implementation choices. Their necessity is not assumed from the DRAFT; they were checked against the required immutability, native access and shared-owner behavior. No unauthorized component expansion was established.

Localized corrections suffice for the findings below. In particular, preserving native value ownership and valid slice sharing is preferable to changing the generated data model to accommodate incorrect cycle identities. Likewise, retiring a verified source owner should be corrected in the existing planner rather than requiring a new migration subsystem.

## 1. Findings

### [P2-1] C++ cycle detection mistakes a first value subobject for its parent

**Location:** [validation.hpp:24](D:/projects/limbo/cpp-go-oneof-scratch/review-r0/code/taut-dev/taut/src/taut/gen/runtime/validation.hpp:24), and [validation.hpp:92](D:/projects/limbo/cpp-go-oneof-scratch/review-r0/code/taut-dev/taut/src/taut/gen/runtime/validation.hpp:92).

**Violated invariant:** Recursive validation traverses ordinary owned children and reports a cycle only when the same message object is already an active ancestor.

`Ancestor` stores only `const void*`. `walk()` compares that address against the child’s unwrapped address without considering native type or binding identity. An enclosing object and its first value subobject can have the same address.

**Reproduction:** Generate source/on C++ from:

```python
schema(
    Child=Msg(n=F(1, INT)),
    Parent=Msg(child=F(1, Ref("Child"))),
)
```

Compile the generated output and this probe with `clang++ -std=c++20 -fno-rtti`, the generated include root and `foundation.cpp`:

```cpp
taut::Parent p{};
auto report = p.validate();
```

The exact-checkout probe at `D:/projects/limbo/cpp-go-oneof-scratch/review-r0/code/scratch/first-member-exact` compiled successfully and printed:

```text
same_address=1 valid=0 complete=1 fast=0 issues=1
validation.ownership_cycle
```

There is no cycle, no rule violation and no invalid primitive. Expected results are an empty complete report and Boolean true.

**Impact:** Ordinary acyclic wrappers can fail recursive validation. The child’s actual rules are skipped and replaced by a false cycle diagnostic.

**Required correction:** Identify active message objects using both their address and stable native type/binding identity, or an equivalent identity that distinguishes overlapping enclosing/subobject addresses. Preserve genuine same-object cycle rejection.

**Closure test:** Compile/run required and optional acyclic first-child wrappers, including a child with a real oneof error. Require successful valid wrappers and the real child diagnostic for invalid wrappers. Retain true recursive-pointer cycle and repeated-shared-child tests, in both report and Boolean modes.

### [P2-2] Go slice identity conflates different views of one backing array

**Location:** [paths.go:14](D:/projects/limbo/cpp-go-oneof-scratch/review-r0/code/taut-dev/taut/src/taut/gen/runtime/go/paths.go:14).

**Violated invariant:** Active-ancestor tracking detects traversal cycles without hiding valid shared-child paths.

`ListIdentity` uses only `&value[0]`. Distinct slice views starting at the same element therefore receive the same identity even when their traversable extents differ.

**Reproduction:** Generate source/on Go for:

```python
schema(
    Node=Msg(children=F(1, List(Ref("Node")))),
    Root=Msg(nodes=F(1, List(Ref("Node")))),
)
```

In a module declaring `module review.local/probe`, run:

```go
nodes := make([]a.Node, 2)
nodes[1].Children = nodes[:1]
root := a.Root{Nodes: nodes}
report := root.Validate()
```

`nodes[0]` has no children. Traversal is finite: the second node refers to the first node through a shorter view. The probe at `D:/projects/limbo/cpp-go-oneof-scratch/review-r0/code/scratch/go-slice-identity`, executed with `go run ./app`, returned:

```text
valid=false complete=true fast=false issues=1
validation.ownership_cycle
```

The issue is located at `nodes[1].children`.

**Impact:** Valid native slice sharing is rejected, and supported child checks beneath that view are skipped.

**Required correction:** Include the slice’s traversable view in its identity—at least distinguishing differing lengths at the same starting address—or use equivalent tracking that preserves correct traversal semantics. Keep map-value-copy and genuine slice-cycle detection.

**Closure test:** Add this finite shared-prefix example, require empty complete reports and Boolean true, and add an invalid first node to prove both reachable paths are checked. Retain actual self-referential slice/map cycles and repeated shared collections.

### [P2-3] Go’s default source owner cannot transition to package mode

**Location:** [go_runtime.py:235](D:/projects/limbo/cpp-go-oneof-scratch/review-r0/code/taut-dev/taut/src/taut/gen/go_runtime.py:235).

**Violated invariant:** Source/package changes retire positively owned unused source components while preserving other users. An owner being retired is distinct from a source owner being rebound to a different import path.

The remapping guard runs before withdrawing the current source user. With default same-package source output, the existing runtime manifest records an empty import path. Package generation introduces the package’s explicit import path, but `source_root` still defaults to the output directory. The planner rejects the transition as a physical source-owner remap even though that source owner is being retired.

**Reproduction:** Using the verified local package already compiled/run in the walkthrough:

1. Generate a minimal `Record(n: int)` to a fresh output using CLI `--lang go --api-only --runtime source`.
2. Repeat generation to the same output using `--runtime package --runtime-bindings bindings.json`, with an explicit valid import path and artifact directory.

The isolated minimal reproduction at `D:/projects/limbo/cpp-go-oneof-scratch/review-r0/code/scratch/go-transition-minimal` produced:

```text
source exit 0
package exit 1 unchanged True
ValueError: ... cannot remap a Go physical source owner to another import_path; use explicit migration
```

All prior output ownership and content hashes matched. No other user required that local owner. The same package worked in a fresh package-mode consumer.

**Impact:** A user following the advertised default source route cannot perform the normal package transition in place. Fresh-output generation works, but it does not fulfill the owned transition lifecycle.

**Required correction:** Separate withdrawal/retirement of the old owner from selection of the new package owner. Retain rejection when an actual surviving source owner is rebound incompatibly.

**Closure test:** Exercise default local-source→package and imported supplied-runtime transitions with validation off/on, then package→source. Check native build/run, removal of only owned obsolete files, preservation of handwritten files and other users, and continued rejection of genuine source-owner import remapping.

### [P3-1] The new LF formatting regression cannot import its fixture in the settled gate

**Location:** [test_go_oneof.py:365](D:/projects/limbo/cpp-go-oneof-scratch/review-r0/code/taut-dev/taut/src/tests/test_go_oneof.py:365).

**Violated invariant:** The new independent formatting check must execute under the supported broad test invocation.

The test imports `_generated_go` from `src.tests.test_go`. With the prescribed source PYTHONPATH and absolute test-directory invocation, there is no importable `src` package. The complete integration receipt records `ModuleNotFoundError: No module named 'src'` before any `gofmt` comparison.

**Impact:** The settled gate is red and the claimed additional LF formatting coverage does not execute in that environment. This is not evidence that generated Go formatting differs.

**Required correction:** Use a fixture/helper import that works under the repository’s supported test invocation without requiring an incidental working-directory entry.

**Closure test:** Run this exact node from the integration runner’s working directory and PYTHONPATH, then confirm the formatter comparisons actually execute and pass.

### [P3-2] The retained map-import test assumes the obsolete Go import spelling

**Location:** [test_map_gen.py:28](D:/projects/limbo/cpp-go-oneof-scratch/review-r0/code/taut-dev/taut/src/tests/test_map_gen.py:28).

**Violated invariant:** Retained regression checks must express the supported generated contract after migration.

The assertion requires literal `import "sort"`. The current generator emits a grouped import with alias `tautsort`, and qualifies sort calls accordingly. The broad failure is the obsolete lexical assertion, not missing sorting functionality.

**Impact:** Correctly compiled current output fails the standard regression suite.

**Required correction:** Update the test to verify that map output imports and uses sorting, while plain output does not introduce an unused sorting dependency.

**Closure test:** Run the retained test against map/plain output and preserve native compilation coverage.

### [P3-3] The retained scaffold result assertion omits the new ownership receipt

**Location:** [test_scaffold.py:81](D:/projects/limbo/cpp-go-oneof-scratch/review-r0/code/taut-dev/taut/src/tests/test_scaffold.py:81).

**Violated invariant:** Existing option tests must remain executable after the mandatory output-ownership migration.

The test expects only `go/api.go` from `emit()`. The current supported route also returns `go/.taut-go-outputs.json`. The assertion fails before completing its intended check that undeclared default options do not count as unsupported declarations.

**Impact:** The suite gains a new failure despite generation correctly accepting the schema; the option regression is obscured by an outdated file inventory.

**Required correction:** Include the ownership receipt in the expected result while retaining the declared-versus-default option assertions.

**Closure test:** Run the scaffold option tests and verify acceptance of undeclared defaults and prewrite rejection of unsupported explicit declarations.

## 2. Invariant analysis

The following attacks did not establish additional defects:

- **Allocation-fault boundary:** Both source/package C++ allocation-injection cases passed. First fallback construction, copy/move and getters survived fail-all allocation; report and Boolean behavior matched the required failure direction.
- **Native semantic fixtures:** Source/package/supplied normalized conformance passed in both languages for the selected fixtures, including zero/false/empty presence, wrong tags, nonselected children, virtual incompleteness, paths, scopes and structural round trips. Those passing fixtures do not cover P2-1 or P2-2.
- **Independent ownership:** Four C++ independent disabled-child distribution combinations passed. Native metadata and shared report identity worked without regenerating child methods.
- **Compatibility facts:** The four C++ external-facts cases accepted normalized equivalent facts and rejected enum, effective-codec and forward-compat mismatches.
- **Configuration boundaries:** The targeted malformed C++ constraint and Go report/configuration checks passed. Go snapshot and descriptor-only checks passed in both validation modes.
- **Distribution:** The cold walkthrough generated and used C++ and Go source, package and supplied consumers through the CLI. All six native consumers succeeded. C++ enabled→disabled→package→source transitions succeeded. Go enabled→disabled succeeded, followed by the P2-3 package-transition failure.
- **Structural behavior:** The changes retain the existing native codec route rather than invoking semantic validation from construction, mutation or codecs. No new native JSON parser or higher-level library dependency is introduced.
- **Shared integration:** The combined wheel and ownership checks were selected in the settled broad gate. The complete receipt, rather than the earlier drafting totals, supplies final source association.

### Surface assessment

The new options belong under the existing `gen` family. Their names describe their function. Help states validation-off, mandatory-descriptor and supplied-runtime defaults, explains the source alias, and requires an explicit Go package import path. The documentation supplies concrete owner/binding examples and explains validation disablement and distribution transitions.

No additional command-placement or naming blocker was established. The first-day workflow’s concrete lifecycle failure is P2-3. No installation/removal command pair is missing: these routes generate application-owned files and explicitly avoid package installation.

## 3. Risks and next action

Virtual selection remains intentionally incomplete. Existing C++ borrowed decode lifetimes and fixed-buffer behavior remain applicable. Neither target gains a native JSON route. These are documented boundaries, not findings.

The exercised native toolchains do not independently establish every older compiler/runtime combination. That limitation does not explain the reproduced correctness defects.

The next action is one root-authorized merged correction: resolve P2-1 through P2-3, repair the three new test integration failures, and return the corrected settled tuple for originating-axis closure. Preserve the three named historical baselines and exact deselection policy; do not relabel the new failures as baseline or claim the current broad gate is green.
