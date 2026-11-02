# Rust OneOf checkpoint — CODE + SURFACE-AXIS REVIEW

**Review object:** Taut `020f7b08d379e2a27720eda102c2782dfcc55e3e` and taut-shape-rs `b55cd89e76830e61f8580c5f5e0b38519e7cef95`, including committed `dev-docs/RustOneOfCheckpoint-Draft.md`. Status: frozen implementation checkpoint, not accepted or released.

**Baseline:** Taut `7182764c4a3da372557deb6fc6f8f4b7d5f90a05`; taut-shape-rs `959f0f048a671347c0940962c5299ae117d92f8a`; reference-only Python shape `c08c2a1b5197f761c5b0b835c588da512130ceda`. Workspace reference `2183e4bc89f08837bc2a497e9f2680292ed8ba85`. Sources were inspected through working-tree reads and committed Git diffs/show; scoped GWZ status showed no tracked production modifications.

**Date:** 2 November 2026, Australia/Sydney.

**Axis:** Code architecture, interfaces, typed ownership/lifetimes, compatibility, and public Surface. Independent, adversarial, read-only. The other axis runs in parallel; nothing here relies on it. Filed verbatim by the lane owner.

**Verdict: NO-GO** — one P2 finding blocks. I pre-commit to GO on a revision that resolves P2-1 as specified, subject to the originating counterexample and relevant regression checks passing.

---

## 0. Evidence base

Read before design/code:

- Live top-level CLI help and `python -m taut.cli gen --help`.
- `dev-docs/examples/rust-oneof/README.md`, in full.

Read afterward:

- Installed `review-loop/SKILL.md`, workspace `AGENTS.md`/`AGENTS_GWZ.md`, Taut `AGENTS.md`, and taut-shape-rs `AGENTS.md`.
- `RustOneOfCheckpoint-Authority.md` and `RustOneOfCheckpoint-Draft.md`, in full.
- `OneOf-ExplicitValidation-BuildProposal.md`, including metadata, publication, validation/report semantics, Rust methods, distribution, compatibility, naming and conformance requirements.
- Both scoped committed diff inventories and relevant diffs.
- `src/taut/gen/rust_metadata.py:1–265`.
- `src/taut/gen/runtime/descriptors.rs:1–392`.
- `src/taut/gen/runtime/validation.rs:1–381`.
- `src/taut/gen/rust_runtime.py`, `rust_external.py`, Rust codec generation, shared scaffold/CLI dispatch and target-filtered native name validation.
- Foundation Cargo/lib/provenance synchronization; shape Cargo dependency, foundation facade/re-exports, regeneration script and generated provenance.
- `src/tests/test_rust_oneof.py`, including independent-child distribution matrices, actual shape composition, lifetime rejection, contract/facts rejection and output ownership tests.
- Completed Rust checkpoint logs, `package-verification.json`, and Python `baseline-evidence.json`/`broad-regression-summary.json`.

Fresh checks:

| Check | Result |
| --- | --- |
| Start and end Taut/Rust shape HEAD verification | Exact requested SHAs |
| End Python shape/workspace reference verification | Exact requested SHAs |
| `python rust/sync_foundation.py --check` | Passed |
| Allowed combined pytest selection: `test_rust_oneof.py`, `test_oneof.py`, `test_python_runtime_distribution.py`, `test_scaffold.py`, isolated basetemp and no cache provider | **215 passed** |
| Fresh CLI source/package/descriptor-only generation, compilation and execution | Passed |
| Fresh source → package and validation on → off transition | Tracked runtime files and optional methods removed as expected |
| Foundation `cargo check --offline --locked --all-features`, isolated target directory | Passed |
| Exact shape process-global checker with verified Python | Passed: 42 files, one existing permanent allowlist entry, no new entries |
| Fresh `Box` schema compilation probe | **Failed**, reproduced P2-1 |

All fresh generated artifacts and compiler outputs were confined to `D:/projects/limbo/rust-oneof-scratch/review-code`.

Completed supplied evidence:

- Combined feature/regression gate: **249 passed, one existing skip**.
- Broad gate: **1,450 passed, three failed, four skipped, eight deselected**. The three failures match the separately evidenced missing old document and two Windows Go newline/gofmt baseline cases.
- All **16 codec parity variants GREEN**.
- Local packaged/extracted foundation application passed; recorded package payload contains the lightweight runtime and no compiler or shape dependency.
- Shape workspace/no_std/Clippy evidence and the disclosed unchanged Windows `python3` harness limitation were inspected.

## Problem, requirement provenance, and scope

The concrete requested outcome is Rust OneOf metadata and explicit validation against the accepted Python behavior, with safe typed access, independent structural codecs, lightweight canonical runtime distribution and actual Rust shape-library composition.

The committed authority records the operator’s implementation authorization, shared Limbo checkout constraint, Python acceptance prerequisite, committed/pushed checkpoint requirement and explicit no-release boundary. It also records supersession of the proposal’s earlier documentation-only and stop-at-Python clauses. The other seven feature backends remain deferred.

The observed Rust gaps are supported by the baseline and diff: generated messages lacked the new mandatory descriptor/access contract and validation methods; source distribution lacked the new ownership lifecycle; shape compiled its own nominal CBOR owner.

The foundation extraction is justified by the single-owner and no-shape-engine requirements. The existing shape CBOR implementation was a separately compiled nominal owner; matching labels could not unify it with an independently compiled application runtime. The implemented route uses a dependency-free `no_std + alloc` foundation and genuine shape re-exports. Fresh package/source executions and the actual shape composition tests provide feasibility evidence. Registry publication or installation is not needed.

The shared scaffold, CLI forwarding, native target name filter and Rust corpus closure changes are within the authorized integration scope. Python remains the behavioral reference, and its shared regression selection passed. No unrelated feature backend implementation was found in the reviewed diffs.

A localized correction is sufficient for P2-1: complete Rust’s generated-name preflight or eliminate the conflicting unqualified helper import. No additional infrastructure or broader redesign is required.

## 1. Findings

### [P2-1] `Box` is imported unconditionally but omitted from generated type-name reservations

**Location:** `src/taut/gen/rust_metadata.py:229–251`, particularly the reservation condition at lines 229–231 and unconditional `boxed::Box` import at line 251; related reservation inventory in `src/taut/gen/rust.py`.

**Violated invariant:** Actual generated symbol collisions must be detected explicitly before writing outputs. Newly accepted generated Rust must compile in both validation modes and distributions.

The emitter imports `alloc::boxed::Box` into every generated API module, including schemas without recursive fields. Neither `METADATA_NAMES` nor `rust.RESERVED_TYPE_NAMES` reserves `Box`. A schema message or enum named `Box` therefore passes generation and collides with that import.

**Reproduction:** The following production-emitter probe was run in the isolated scratch root:

```python
from taut.ir.dsl import schema, Msg, F, INT
from taut.gen.scaffold import emit

emit(
    schema(Box=Msg(value=F(1, INT), next_id=2)),
    scratch,
    langs=["rust"],
    services=[],
    runtime_mode="source",
)
```

Generation succeeds and writes `rust/api.rs` and the runtime closure. A root containing:

```rust
extern crate alloc;
pub mod cbor;
mod api;
fn main() {}
```

then fails under `rustc --edition=2021`:

```text
error[E0255]: the name `Box` is defined multiple times
  api.rs:12:1
5  | use alloc::{boxed::Box, string::String, vec, vec::Vec};
   |             ---------- previous import
12 | pub struct Box {
   | ^^^^^^^^^^^^^^ `Box` redefined here
```

Further errors resolve generated `impl Box` and binding references to the allocation type, including missing generic arguments and foreign inherent-implementation errors.

**Impact:** An ordinary nonrecursive schema is accepted, emitted and inventoried as current generated output but cannot compile. The same unconditional import affects source, package and supplied-runtime generation, with validation enabled or disabled. This is a concrete generated-code correctness and name-preflight defect.

**Required correction:** Either reserve `Box` consistently with the other imported helper types and reject it before any write, or remove the unqualified collision by using an appropriate qualified helper spelling. Keep the public migration documentation consistent with the chosen behavior.

**Closure/regression test:** Add message and enum `Box` cases covering validation on/off and source/package output. If rejected, assert a named preflight error and unchanged output; if supported, compile the generated cases. Re-run the counterexample above and relevant Rust/shared feature checks.

## 2. Invariant analysis

The following attacks did not establish additional defects:

- **Typed pairing and lifetimes:** Generated `SchemaBinding<T>` callbacks receive the correct concrete type; `Bound` keeps its value and binding private. Borrowed primitive access remains tied to the input lifetime. Fresh regression checks include wrong-live-type and escaping-borrow compile failures.
- **Static recursive metadata:** Recursive links use descriptor accessors rather than eagerly expanded graphs. Inline owned recursive edges use `Box`; container recursion uses existing collection storage. No mutable publication cache or process-global initialization was introduced.
- **Optional methods and mandatory metadata:** Validation-disabled generation retains descriptor/binding access without report-engine files or instance validation methods. Enabled messages expose exactly the four specified methods, with recursive default options.
- **Shared predicates and full/fast behavior:** Both sinks use the same traversal and payload predicate. Boolean failure short-circuits on issues or virtual deferrals without constructing diagnostic objects. Report mode continues independent children and records owned snapshots.
- **Paths and ordering:** Field-number group placement, payload ordering, list indices and canonical CBOR map-key ordering are implemented explicitly and exercised against the Python reference. Original schema names survive raw-identifier field projection.
- **Invalid drafts and codecs:** Fresh source and package executions preserved populated invalid payloads through dense CBOR, repaired the draft and retained the earlier report’s two issues. Structural decode remains separate from semantic validation.
- **Actual nominal owner:** Shape’s codec facade and optional validation export alias the foundation. Independent child/parent and actual shape tests exercise shared descriptor/report/issue/Cbor/error identities. Disabled children supply metadata without foreign inherent methods.
- **Compatibility failure direction:** Old children, altered facts/contracts/capabilities and deliberately split nominal owners fail at generation, compilation or publication rather than yielding empty successful reports.
- **Distribution and provenance:** Source/package/supplied mode selection remains independent of validation. Foundation synchronization passed, and actual extracted-package evidence supports the lightweight package route.
- **Authorized scope:** Shared dispatch/preflight changes support Rust integration while preserving accepted Python regression behavior. No other feature backend or release action was introduced.

### Surface

The added switches belong under the existing `gen` family. The public help distinguishes source, package and application-supplied defaults; `--with-runtime` is explicitly a source alias; validation defaults off. The README documents the four methods, recursive defaults, read-only report getters and the distinction between validity and completeness.

The first-day walkthrough succeeded for source, package and descriptor-only applications. Source required the documented root modules; package used the documented local foundation owner. No install or registry-release assumption was necessary. Regeneration with package mode and validation disabled provided the documented lifecycle transition and removed the tracked source closure and optional methods.

The actual shape route documents the necessary Cargo patch and single-owner constraint. It does not imply that equal version labels repair separately compiled owners.

P2-1 is also a Surface defect: the promised named rejection for actual helper-symbol collisions is incomplete, leaving users with an avoidable downstream compiler failure.

## 3. Risks and next action

The wasm target remains unverified on this host, and the three established broad-suite baseline failures remain outside this checkpoint. The existing Windows shape harness’s `python3` invocation was handled by running its unchanged checker with verified Python; its rules and allowlist were not loosened.

The next action is one bounded correction for **P2-1**, followed by its message/enum collision regressions and the originating reviewer’s focused re-verdict on the revised exact tuple.
