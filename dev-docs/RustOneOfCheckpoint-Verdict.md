# Rust OneOf checkpoint — accepted

Status: **accepted at Taut `99b3dcf7c1f34985098a5b13add14088b86fe57c`
and Rust shape `8e92b89ed3a4f218a5a4e018fbfee6301fcc14b4` after
`RustOneOfCheckpoint-ReviewCode-2.md` and `RustOneOfCheckpoint-ReviewState-2.md`
reported GO; this accepts the Rust OneOf/descriptors/explicit-validation and
actual-library foundation checkpoint only**.

Both original, peer-blind reviewers completed final reviews on that same frozen
tuple and verified unchanged production sources. The lane owner merges GO/GO.
The accepted Python reference remains Taut `7182764c4a3da372557deb6fc6f8f4b7d5f90a05`
and Python shape `c08c2a1b5197f761c5b0b835c588da512130ceda`.

| Discovery phase | Blocking defect | Final disposition |
| --- | --- | --- |
| Initial Code review | Code/P2-1: unqualified allocator Box collides with schema name | Originating Code reviewer closed in remediation 1; retained and reverified in remediation 2 |
| Initial State review | State/P2-1: equivalent owner roots delete live runtime | Originating State reviewer closed in remediation 1; retained and reverified in remediation 2 |
| Remediation-1 State review | State/P2-2: Windows namespace prefix removal redirects output | Originating State reviewer closed in remediation 2 after exact counterexamples and unchanged-tree refusal checks |

Two bounded remediation rounds were used. All blocking findings are closed.
Final reviewers identified no new root cause, bounded or architectural; no escaped
defect is known at this gate. The findings were distinct rather than blind
convergence. Final reviewers independently corroborated the corrected cases.

[Results](RustOneOfCheckpoint-Results.md) records the completed gates: 272 passes
and one existing skip in the combined suite; 1473 broad passes with the same
three disclosed baseline failures, four skips and eight deselections; all 16
codec variants GREEN; actual shape tests, no_std/Clippy, unchanged process-global
checker, source/package examples and extracted local package proof passed.
Each final reviewer independently ran 238 focused tests successfully.

The accepted behavior includes mandatory immutable metadata and typed access,
optional explicit validation with owned reports and shared predicates, source /
package / supplied-runtime delivery, one canonical base-Taut foundation, actual
shape-library nominal composition, and guarded output ownership/shared lifetimes.
Invalid drafts and structural codecs remain usable independently of validation.
The documented refusal of ambiguous Windows namespace filename components is an
intentional supported-path limit. Existing wasm/python3 environment limitations
and broad baseline defects remain disclosed, not relabeled as successful checks.

The next authorized action is an audit/evidence-only Taut commit, a GWZ-managed
workspace receipt, then ordinary nonforce `main` pushes for Taut, Python shape,
Rust shape and the workspace root. Production source at the evidence commit
must remain byte-identical to the accepted tuple; record that comparison before
publication. The workspace lock records the final member HEADs. Other seven
feature languages belong to the coordinator after verified publication.

No release, release tag, GitHub Release or registry publication is authorized or
performed by this acceptance. Source `.crate` packaging is a local proof only.
