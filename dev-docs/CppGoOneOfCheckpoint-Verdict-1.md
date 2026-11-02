# C++/Go checkpoint — accepted merged remediation 1

Status: **accepted at the exact reviewed tuple below after the same original
Code+Surface and State reviewers both reported GO; this accepts the C++/Go pair
and authorized shared integration only**. One merged remediation round was used.
No P0/P1/P2/P3 finding remains open on either axis, and neither reviewer identified
a new architectural root cause. The original NO-GO and failed receipts remain
historical evidence of their original revisions.

| Repository | Accepted reviewed revision |
| --- | --- |
| Taut | `c9c5bb0764bbc5a58c65e649468ed5aa67920ded` |
| Workspace receipt | `1a4d66e05221a1a85e5b4f0fbb10b80befe2b378` |
| Python shape | `c08c2a1b5197f761c5b0b835c588da512130ceda` |
| Rust shape | `8e92b89ed3a4f218a5a4e018fbfee6301fcc14b4` |
| TypeScript shape | `1aaeab65e4564a462044d2f5d824cd2f375aae97` |

The unedited [Code+Surface closure](CppGoOneOfCheckpoint-ReviewCode-1.md) and
[State closure](CppGoOneOfCheckpoint-ReviewState-1.md) are the authority for
finding closure. [ReportFiling-1](CppGoOneOfCheckpoint-ReportFiling-1.json) records
their original exported byte lengths and SHA256 values and the verified byte
copies. The lane owner merges those verdicts here; implementation tests alone
did not close findings.

| Merged correction | Original finding IDs | Originating closure |
| --- | --- | --- |
| Native binding plus address distinguishes C++ parent/first child | Code P2-1 | CLOSED by Code; State also attacked identity/fault/child behavior |
| Typed start plus traversed length distinguishes Go finite slice views | Code P2-2; State P2-1 | CLOSED independently by both original reviewers; original blind convergence retained |
| Retire unused old Go source owner without remapping it | Code P2-3 | CLOSED by Code; State also exercised 40 persisted cutoffs and four forced owner-receipt-first states |
| Portable formatter fixture import | Code P3-1; State P3-1 | CLOSED independently by both, including actual scratch/root formatting execution |
| Assert actual conditional sorting binding and native use | Code P3-2; State P3-2 | CLOSED independently by both, including map/plain native round trips |
| Attribute generated API ownership receipt | Code P3-3; State P3-3 | CLOSED independently by both, including API hash and neighboring option refusals |

The single corrective checkpoint contains exactly seven authorized source/test
paths and 44 scoped evidence paths. Both isolated full-history clones were set to
exact newline behavior before checkout; all 1,067 tracked files matched raw
committed blobs before dispatch and at each final boundary. All five revisions,
tracked/index cleanliness, historical fixtures, oracle assets, current source
hashes and historical/current receipt associations were independently verified.

Corrected implementer checks passed: C++ 109 (one duplicate parity wrapper
deselected), Go 145, shared assertions 16, and pair distribution/current wheel
plus exact formatting 11. Smaller C++ 18 and Go 56 runs overlap these totals.
Fresh Go examples passed six native executions. Code independently passed 89
focused cases and the repository-root formatter; State independently passed 107
native/state cases, three exact integration cases, root formatting and four
additional forced interruption states. These totals overlap and are not added.

The original complete global gate remains associated with Taut `42228223…` and
workspace `bd455ef9…`: 2,060 passed, six failed, five skipped and 11 authorized
deselections, with all 16 require-all codec variants GREEN and zero violations.
Three new integration-test failures are repaired and independently closed at the
corrected tuple. The three exact historical baseline failures remain visible.
The initial failed Go remediation cutoff attempt is also retained, followed by
passing corrected cutoff and final feature receipts. No corrected-source global
suite, full-16 rerun or standalone reference-library rerun is claimed.

The five user-owned authoring files, 35 excluded old Python artifacts, reference
libraries and dependency declarations remain preserved. The current wheel's
13 canonical runtime resources were independently matched to the corrected
source. Scope and evidence details are in
[FocusedResults-1](CppGoOneOfCheckpoint-FocusedResults-1.json),
[Preparation-R1](CppGoOneOfCheckpoint-Preparation-R1.json) and both target
`RESULTS-R1.md` records. Their pre-review HOLD labels describe that historical
checkpoint; this verdict records its acceptance.

The coordinator authorized a final local evidence-only landing after GO/GO.
It adds the exact named review/acceptance documents and a GWZ-managed workspace
receipt, preserving every file at the reviewed source revision byte for byte.
The actual resulting landing tuple is reported after those commits; no future
SHA is invented here. No additional implementation, push, tag, release, registry
publication or Swift work belongs to this lane. The coordinator owns the next
Swift checkpoint and eventual final push under the user's separate authorization.
