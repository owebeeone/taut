# Rust OneOf checkpoint, remediation 1 — STATE-AXIS REVIEW

**Review object:** Taut `ba4240778143a382be381c0f16d3659ab097ad47` and taut-shape-rs `8e92b89ed3a4f218a5a4e018fbfee6301fcc14b4`, including the controlling draft and authority documents. Status: frozen remediation 1 checkpoint; acceptance pending.

**Baseline:** Original reviewed tuple: Taut `020f7b08d379e2a27720eda102c2782dfcc55e3e`; Rust shape `b55cd89e76830e61f8580c5f5e0b38519e7cef95`. Reference-only Python shape remains `c08c2a1b5197f761c5b0b835c588da512130ceda`; workspace root remains `2183e4bc89f08837bc2a497e9f2680292ed8ba85`. Sources were read directly and through committed Git diffs. Final targeted `git diff --exit-code HEAD` checks confirmed inspected production sources and controlling documents matched HEAD.

**Date:** 2 November 2026, Australia/Sydney.

**Axis:** Durable-state semantics, filesystem identity, preflight, ownership, shared-use accounting and failure direction. Independent, adversarial, read-only. The other axis runs in parallel; nothing here relies on its current re-verdict. Filed verbatim by the lane owner.

**Verdict: NO-GO** — originating State/P2-1 is closed, but new P2-2 blocks. I pre-commit to GO on a revision resolving P2-2 as specified while retaining the verified original closure and regression protections.

---

## Prior-finding closure table

| ID | Disposition claimed | Verified on corrected tree | Status |
| --- | --- | --- | --- |
| State/P2-1 — equivalent source-root spellings delete the live runtime | Normalize current/prior roots and users after lexical safety checks; reject overlapping physical plans | Repeated the original one-producer and enabled-A/disabled-B `owner/../owner` counterexamples through production `emit`. Files, users and engine survived; generated applications compiled and ran immediately. Equivalent output-directory spelling retained one identity. Engine cleanup occurred only after the enabled user disabled validation. Existing junction and obstruction tests passed. | **Closed** |

## Changed-range analysis

Inspected Taut `020f7b08..ba424077` and Rust shape `b55cd89e..8e92b89e`.

- `rust_runtime.py` adds lexical directory/ancestor checks, canonical current/prior roots, normalized schema-user identities, equivalent-user consolidation and ambiguous-user rejection. The scaffold obtains its Rust schema directory through that helper. These changes implement State/P2-1.
- Shared `python_runtime.py` adds a physical-path helper used by lock deduplication and application preflight. Application rejects conflicting physical write/write or write/delete targets before mutation. This remains inside the existing pre-write boundary and is relevant to State/P2-1. Its unconditional Windows namespace-prefix conversion introduces P2-2.
- Rust generation removes the unqualified allocator `Box` import and qualifies recursive storage/construction. This implements the prior Code finding. Goldens and six shape-generated modules reflect that import change; shape provenance hashes were updated without schema changes.
- Thirteen added test cases cover message/enum `Box` compilation, equivalent runtime/output identities, shared engine retention, physical overlap refusal and ordinary extended-prefix equivalence.
- Draft/README updates describe the corrections. Prior prompts, reports and the merged remediation plan provide audit records.

The patch does not change the runtime ABI, descriptor/report contracts, semantic rules, distribution architecture or mutation ordering. Continued-review proofs remain applicable. P2-2 is a new localized implementation defect in path-equivalence normalization, **not a new architectural root cause** or a redesign trigger.

## 0. Evidence base

Read the complete canonical remediation prompt, committed authority, merged `RustOneOfCheckpoint-RemPlan-1.md`, both original filed reports, all production/test/document changed ranges, and the complete Rust shape remediation diff. The proposal, original draft, repository rules and review-loop instructions remain the controlling context established during the original review.

Fresh verification:

- Start and end verification of all four tuple members: unchanged at the SHAs above.
- `python rust/sync_foundation.py --check`: passed.
- Permitted four-file focused suite with isolated basetemp and cache/plugin autoload disabled: **228 passed in 40.96 seconds**.
- Independent production-emitter repetitions of the original single/shared-user counterexamples, immediate `rustc` builds and executable assertions: passed.
- Independent equivalent-output-directory regeneration and shared-engine disable transitions: passed.
- Filesystem identity probe and production-emitter probe under `D:/projects/limbo/rust-oneof-scratch/review-state-r1`: reproduced P2-2.

Completed gate evidence inspected:

- Combined feature/regression gate: **262 passed, one existing skip**.
- Final broad gate: **1,463 passed, three failed, four skipped, eight deselected**. The failures remain the disclosed missing old document and two Go CRLF/gofmt baseline cases.
- All **16 codec variants GREEN**.
- Foundation/shape no_std and Clippy logs completed successfully.
- Unchanged process-global checker: **42 files, one permanent allowlist item, nothing new**.
- Extracted-package verification passed and records no compiler or shape-engine dependency.

No source, checker, allowlist or configuration was modified. Fresh artifacts remained within the permitted remediation State scratch root.

## Problem, requirement provenance, and scope

The operator’s requested outcome remains working Rust metadata, safe typed access and optional explicit validation against accepted Python behavior, with a lightweight canonical foundation, actual shape-library composition and executable conformance. The committed authority supersedes the proposal’s older documentation-only restrictions and authorizes the checkpoint without release operations.

The original Rust gaps and foundation-route necessity remain supported by the baseline, independent source/package applications and actual library composition. No registry publication, package installation or additional infrastructure is needed.

This remediation addresses two demonstrated implementation defects through localized emitter and ownership-boundary changes. Shared application/lock changes are relevant to the authorized requirement to preserve safe output ownership and Python protections. The shape diff is generated import/provenance maintenance. No unrelated feature backend or project expansion was found.

The added Windows-prefix normalization is an implementation choice intended to unify equivalent spellings. That objective is appropriate, but stripping the namespace prefix is not always meaning-preserving. P2-2 supplies direct counterevidence; it does not require additional infrastructure or expanded scope to correct.

## 1. Findings

### [P2-2] Windows namespace-prefix stripping redirects generation into a distinct output owner

**Location:** [python_runtime.py:60](D:/projects/limbo/taut-dev/taut/src/taut/gen/python_runtime.py:60), particularly lines 67–73. Used by Rust `canonical_path()` and therefore runtime-root/schema-directory selection, user identities, locks and physical-target checks.

**Violated invariant:** Canonicalization may unify equivalent filesystem paths; it must not conflate physically distinct directories or redirect a successful generation into another owner.

The helper resolves a path and then removes its Windows extended namespace prefix. Windows extended paths can preserve trailing dots in directory names, whereas ordinary paths interpret those names differently. Removing the prefix therefore changes the addressed directory.

The isolated host probe created both:

```text
D:\...\namespace-probe\owner
\\?\D:\...\namespace-probe\owner.
```

They are distinct directories: `os.path.samefile(ordinary, extended)` returned `False`. The extended directory contained `extended.txt`; the ordinary directory contained `ordinary.txt`. `canonical_path(extended)` returned an ordinary spelling whose directory listing contained `ordinary.txt`.

The production-emitter probe then demonstrated mutation of the wrong owner.

**Reproduction:** In a fresh permitted scratch directory:

```python
from pathlib import Path
import os
from taut.gen.scaffold import emit
from taut.ir.dsl import schema, Msg, F, INT

base = Path(
    "D:/projects/limbo/rust-oneof-scratch/review-state-r1/namespace-emitter"
)
base.mkdir(parents=True)

ordinary = base / "app"
ordinary.mkdir()

prefix = chr(92) * 2 + "?" + chr(92)
extended = Path(prefix + str(base / "app."))
extended.mkdir()

assert not os.path.samefile(ordinary, extended)

emit(
    schema(First=Msg(n=F(1, INT))),
    ordinary, langs=["rust"], services=[], runtime_mode="source",
)
before = (ordinary / "rust/api.rs").read_bytes()

emit(
    schema(Second=Msg(n=F(1, INT))),
    extended, langs=["rust"], services=[], runtime_mode="source",
)

after = (ordinary / "rust/api.rs").read_bytes()
```

Observed:

```text
distinct namespace directory samefile? False
second emit returned success; ordinary API changed? True
ordinary API has Second? True
extended directory entries: []
```

The second request replaced the first directory’s generated API and ownership state while leaving its intended, physically distinct destination empty. No symlink, junction, malformed manifest or concurrent process was involved.

**Impact:** A supported Windows path spelling can cause successful generation to overwrite a different schema owner’s tracked output. Runtime roots and shared-user accounting use the same helper, so they also lack a reliable physical identity for these paths. Existing unknown-file protections do not prevent this case because the wrong destination already contains positively inventoried generator output.

**Required correction:** Preserve filesystem meaning during namespace normalization. Either use a canonical representation that retains extended-path semantics or reject paths whose conversion cannot be established as equivalent, before output mutation. Apply the same identity rule consistently to roots, users, locks and physical-target checks. Preserve ordinary extended-prefix equivalence and lexical alias rejection.

**Closure/regression test:** Create physically distinct ordinary and extended trailing-dot directories. Generate different schemas into them and require either:

- independent outputs, manifests and users, with the first destination unchanged; or
- an explicit preflight refusal leaving both destinations unchanged.

Cover the equivalent runtime-root case and trailing-space namespace behavior. Retain the existing ordinary extended-prefix, `..`, shared-user, output-user, overlap and junction regressions, then run the focused Rust/shared/Python gates.

## 2. Invariant analysis

- **Original cleanup failure:** The original single-producer and shared enabled/disabled-user attacks now fail to reproduce. Both immediate applications built and ran without requiring another regeneration.
- **User identity:** Equivalent `..` output-directory spelling replaces the existing user rather than adding a phantom user. Shared validation remains until the final enabled user disables it.
- **Lexical safety:** Original lexical ancestors are checked before Rust canonicalization. Existing junction cleanup and obstruction tests passed in the fresh suite; normalization did not silently accept those aliases.
- **Application preflight:** The new physical-overlap regression refuses a `..` write/delete contradiction before replacing content. The guard is correctly placed before the first write. P2-2 concerns incorrect identity computation rather than guard ordering.
- **Locking:** Current/prior canonical roots remain locked through planning and application. Ordinary extended-prefix spelling is deduplicated. The new namespace counterexample shows that deduplication must preserve distinctions as well as remove equivalent spellings.
- **Rust helper correction:** Qualified allocator paths preserve valid schema types named `Box`; the fresh suite compiled message/enum cases in source/package modes with validation on/off and retained recursive-layout coverage.
- **Unchanged engine and ownership contracts:** Descriptor/report ABI, lifetime boundaries, shared predicates, owned snapshots, foreign-owner checks and source/package closure were not changed by remediation. Their focused regressions passed.
- **Failure/durability boundary:** Per-file atomic replacement and explicit refusal of unverifiable ownership remain intact. No whole-tree transaction or arbitrary external-filesystem-race guarantee is claimed.
- **Baseline limits:** The final broad check completed with only the three established baseline failures. Those failures do not explain or excuse P2-2.

## 3. Risks and next action

The fresh tests establish closure for the original equivalent-root deletion defect, but the namespace probe prevents accepting the replacement physical-identity helper.

The next action is a second bounded remediation for P2-2, followed by the distinct-namespace counterexample, retained original closure tests and focused gates, then an originating State re-verdict on the revised committed tuple.
