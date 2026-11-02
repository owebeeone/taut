# Rust OneOf checkpoint — STATE-AXIS REVIEW

**Review object:** Taut `7182764c4a3da372557deb6fc6f8f4b7d5f90a05..020f7b08d379e2a27720eda102c2782dfcc55e3e` and taut-shape-rs `959f0f048a671347c0940962c5299ae117d92f8a..b55cd89e76830e61f8580c5f5e0b38519e7cef95`, including the committed controlling draft and authority documents. Implementation frozen for review; acceptance pending.
**Baseline:** Taut `020f7b08d379e2a27720eda102c2782dfcc55e3e`; Rust shape `b55cd89e76830e61f8580c5f5e0b38519e7cef95`; reference-only Python shape `c08c2a1b5197f761c5b0b835c588da512130ceda`; managed workspace root `2183e4bc89f08837bc2a497e9f2680292ed8ba85`. Sources were inspected with file reads and committed Git diffs. Final targeted `git diff --exit-code HEAD` checks confirmed the inspected production files and controlling documents matched HEAD.
**Date:** 2 November 2026, Australia/Sydney.
**Axis:** Durable-state semantics, ownership, preflight, shared-use accounting, failure direction and restart legality. Independent, adversarial, read-only. The other axis runs in parallel; nothing here relies on it. Filed verbatim by the lane owner.

**Verdict: NO-GO** — one P2 finding blocks. I pre-commit to GO on a revision that resolves P2-1 as specified, passes its regression and retains the verified ownership protections.

---

## 0. Evidence base

Read:

- The complete canonical State prompt, installed review-loop skill, workspace `AGENTS.md`/`AGENTS_GWZ.md`, Taut `AGENTS.md`, and Rust shape `AGENTS.md`.
- `RustOneOfCheckpoint-Authority.md` before implementation/design inspection; the complete checkpoint draft and Rust examples README.
- `OneOf-ExplicitValidation-BuildProposal.md`, particularly descriptor publication, typed access, shared ownership, distribution, compatibility, output ownership and conformance requirements.
- `src/taut/gen/rust_runtime.py:1–133`; the reused `python_runtime.py`, including locks, planning and atomic application; `scaffold.py:590–803`; the complete Rust metadata emitter.
- Canonical Rust descriptor and validation resources; foundation synchronization/provenance code; Rust shape dependency and facade changes.
- Rust ownership, obstruction, shared-user, external-owner, lifetime, configuration and composition tests, including `test_rust_oneof.py:164–209`, `358–485` and `509–737`.
- Completed Rust results logs, `package-verification.json`, and Python baseline regression/evidence records.

Fresh commands and probes:

- Verified all four tuple members at start and end. They remained exactly as listed above.
- `python rust/sync_foundation.py --check`: passed.
- The permitted four-file focused suite, with plugin autoload/cache disabled and its basetemp under the State scratch root: **215 passed in 36.07 seconds**.
- Foundation `cargo check --offline --locked --no-default-features`: passed.
- Actual Rust shape `cargo check --offline --locked -p taut-shape --no-default-features --features validation`: passed.
- Exact unchanged process-globals checker, invoked with verified Python: **42 files, one permanent allowlist item, nothing new**.
- Production-emitter probes under `D:/projects/limbo/rust-oneof-scratch/review-state/equivalent-root` and `shared-equivalent-root`: reproduced P2-1.
- Seven isolated injected `os.replace` failures during fresh source generation under `review-state/io-faults`: every exception surfaced; locks and temporary files were removed. Restart either succeeded before any published output or explicitly rejected unrecorded partial output.

Completed supplied gate evidence:

- Combined feature/regression gate: **249 passed, one existing skip**.
- Broad regression gate: **1,450 passed, three failed, four skipped, eight deselected**. Failure identities match the prior Python baseline: the missing old extensions document and two Go CRLF/gofmt cases.
- All **16 codec variants GREEN**.
- Package verification records successful execution against the extracted foundation artifact without compiler or shape-engine dependency.
- Shape tests and source/package examples completed successfully, with the disclosed Windows `python3` harness workaround verified through the unchanged checker.

No source, checker, allowlist or configuration was modified. New generated/build artifacts remained inside the permitted State scratch root.

## Problem, requirement provenance, and scope

The operator requested a working Rust implementation against the accepted Python behavior: mandatory metadata and safe typed access, optional explicit validation, lightweight source/package delivery, actual `taut-shape-rs` composition, executable conformance and a committed/pushed checkpoint without release operations. The authority document expressly supersedes the proposal’s older documentation-only and stop-at-Python restrictions.

The concrete Rust gaps were missing metadata/adapters/validation, insufficient runtime-output ownership lifecycle, and a separately compiled private CBOR implementation in the shape library. The implementation addresses those gaps through the existing compiler and native IR.

The new foundation crate and shape facade are authorized by the explicit requirement for one nominal owner while preserving a basic `no_std + alloc` route without shape engines. Existing-route feasibility is demonstrated by the source-only applications, standalone foundation checks, independently generated dependency builds and actual shape-library builds. Registry publication and additional tool installation are unnecessary prerequisites and were not introduced.

The shared scaffold and dispatch changes are connected to complete output preflight and Rust generation forwarding. Python production implementation remains reference-only apart from the authorized shared boundary and regression coverage. Other feature backends and release operations remain deferred.

No unsupported infrastructure prerequisite or unauthorized component expansion was established. P2-1 is a localized defect in the authorized Rust ownership implementation; correcting it does not require broader architecture or scope.

## 1. Findings

### [P2-1] Equivalent source-root spellings are planned as separate owners and delete the live runtime

**Location:** [rust_runtime.py:31](D:/projects/limbo/taut-dev/taut/src/taut/gen/rust_runtime.py:31), lines 69–84, 95–129 and 130–132. The resulting conflicting plan reaches the shared [write-then-delete application](D:/projects/limbo/taut-dev/taut/src/taut/gen/python_runtime.py:214).

**Violated invariant:** Current and prior ownership roots referring to the same filesystem directory must represent one owner. A successful regeneration must retain the runtime and validation engine required by its recorded live users.

`binding()` and `plan_outputs()` use `Path.absolute()`, which preserves `..` in an already absolute path. The previous root is inserted into a set without canonicalization. Consequently, `owner` and `owner/../owner` compare unequal and receive independent plans, although they identify the same directory. The lock implementation resolves and deduplicates those roots, so generation acquires its lock successfully rather than rejecting the discrepancy.

The old-root plan removes the current schema’s user and schedules stale deletion. The new-root plan writes the runtime and adds that same user. Both plans are based on the original manifest. Application writes the replacement files and then executes the stale deletions against those same physical files.

**Reproduction:** Using the committed production emitter and a fresh permitted scratch directory:

```python
from pathlib import Path
from taut.gen.scaffold import emit
from taut.ir.dsl import schema, Msg, F, INT

base = Path(
    "D:/projects/limbo/rust-oneof-scratch/review-state/equivalent-root"
)
owner = base / "owner"
app = base / "app"
s = schema(M=Msg(n=F(1, INT)))

def generate(root):
    emit(
        s, app, langs=["rust"], services=[],
        runtime_mode="source", validation=True,
        runtime_bindings={"rust": {"source_root": str(root)}},
    )

generate(owner)
generate(owner / ".." / "owner")
```

Observed during the review:

```text
before: ['.taut-rust-runtime.json', 'cbor.rs',
         'descriptors.rs', 'ext.rs', 'validation.rs']
equivalent same resolved? True Path equality? False
emit returned success
after: []
```

The schema manifest nevertheless recorded `mode: source`, `validation: true` and the new source-root spelling. A further identical regeneration recreated the files, demonstrating recoverability but also confirming that the preceding successful call had delivered an incomplete configuration.

A separate shared-user probe generated enabled user A and disabled user B against the same owner, then rebound A through `owner/../owner`. That generation also returned success. The observed owner lost `validation.rs`, and its runtime manifest retained only B’s disabled entry. Subsequent B regeneration succeeded while A remained unaccounted for.

**Impact:** A valid configuration spelling change can remove the entire selected source runtime or remove a live user’s validation engine and ownership record. The successful generation leaves generated imports/configuration without their required source closure. This is a concrete correctness and shared-cleanup defect; it needs neither concurrency nor malformed metadata.

**Required correction:** Give the current root, prior roots and schema-user identity a consistent normalized filesystem identity before deduplication, ownership comparisons and manifest updates. Preserve rejection of directory aliases/reparse points; normalization must not make those obstructions silently acceptable. Ensure the combined plan cannot write and delete the same physical target through different path spellings.

**Closure/regression test:** Through normal `emit`, cover:

1. One enabled producer regenerated from `owner` to `owner/../owner`: runtime files and manifest remain present, with one live user, and the emitted application builds/runs immediately.
2. Enabled A plus disabled B, followed by the same equivalent-root rebind: both users remain recorded and `validation.rs` remains until no user requires it.
3. Equivalent output-directory spellings do not create duplicate user identities.
4. Existing junction/reparse and obstruction tests continue to reject unsafe paths before output mutation.

Run the focused Rust/shared/Python gates after the fix.

## 2. Invariant analysis

- **Complete preflight:** Unknown runtime/schema files, modified inventories, incompatible ownership contracts and mixed Python/Rust conflicts were exercised by the fresh suite. Those attacks failed before output replacement. P2-1 escapes because the individual plans are locally valid while their filesystem identities overlap.
- **Shared-user lifecycle:** Canonically spelled producer/consumer lifecycles preserve the engine while another recorded user needs it. Consumer-first binding to a missing owner fails explicitly. Equivalent-path rebinding breaks this accounting as documented above.
- **Lock scope:** Current and prior roots are included, resolved, sorted and locked; a changed prior owner is checked after locking. The demonstrated failure occurs inside a successfully held lock, so additional locking alone will not correct it.
- **Failure direction:** Injected replacement failures never returned generation success. Partial fresh output was subsequently rejected as unowned rather than adopted or overwritten. Per-file atomicity is present; whole-tree crash rollback is not claimed or required. Stale-lock inspection remains an explicit recovery operation.
- **Observation and reports:** The engine shares predicates between report and Boolean sinks, preserves recursive traversal through populated children, and marks virtual checks incomplete. Fresh behavior tests cover snapshot retention, local/recursive parity and canonical map paths.
- **Typed access/lifetimes:** Private bound handles and typed binding signatures reject wrong live values; borrowed primitive views cannot escape their input lifetime. Reports contain owned strings and path vectors. No retained input reference was found in reports.
- **Composition and configuration:** Independent enabled-parent/disabled-child and actual shape-library builds passed. The foundation facade preserves nominal CBOR/error/descriptor/report ownership. Old contracts, missing capabilities, incompatible facts and split owners have executable rejection coverage.
- **Source/package closure:** Canonical-source synchronization and standalone/no_std checks passed. Extracted-package evidence supports compiler-free runtime consumption. The process-global checker and allowlist remain unchanged.
- **Regression boundaries:** The broad run completed. Its three failures match established baseline evidence; they are not new Rust findings or a claim of a wholly green broad suite.

## 3. Risks and next action

The fault probes establish exception propagation and fail-closed restart behavior for bounded replacement failures; they do not establish whole-tree transactional durability or protection against arbitrary external filesystem mutation during application. Those stronger properties are outside this checkpoint’s stated requirements.

The next action is a bounded remediation for P2-1, followed by its equivalent-path/shared-user regressions and the focused gates, then State re-verdict against the new committed tuple.
