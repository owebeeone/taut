# Swift OneOf checkpoint - initial verdict merge

Date: 3 November 2026 (Australia/Sydney). Status: **NO-GO at Taut
`c02765930f06cfcb19a522843aa54582db514706` / workspace
`a8f37984471654902149d136b7a13a588346b58f`; two open P2 findings.**

The unchanged shape revisions are Python
`c08c2a1b5197f761c5b0b835c588da512130ceda`, Rust
`8e92b89ed3a4f218a5a4e018fbfee6301fcc14b4`, TypeScript
`1aaeab65e4564a462044d2f5d824cd2f375aae97`.

The original two peer-blind reviewers consumed the SAME completed exact-tuple
global receipt before issuing their full final reports. Both independently
verified all 37 global evidence files, all five isolated-clone HEADs, clean
tracked/index diffs and all 1,114 raw-associated setup file hashes. Their reports
were filed verbatim, without lane-owner editing:

| Axis | Report | SHA256 | Verdict |
| --- | --- | --- | --- |
| Code + Surface | SwiftOneOfCheckpoint-ReviewCode.md | `954df90865cd1fb81e4768a827688f3b9a4c87d20a2888bd3eb75099c9583994` | NO-GO: Code P2-1 |
| State | SwiftOneOfCheckpoint-ReviewState.md | `95a98398843436d165e5e32a471076c172f84529115e605cf3079a66be8e1131` | NO-GO: State P2-1 |

The State author corrected only its UTF8 export before filing and attested that
the corrected bytes match the full emitted testimony; its initial mojibake export
is retained in reviewer scratch. No finding, evidence or verdict changed.

Code found one bounded namespace-hygiene root: newly introduced ambient helper
types break five accepted message names. State found one bounded recovery root:
default flat supplied mode can report successful retry after owner-receipt-first
retirement leaves orphan runtime sources. These are independent findings; no
blind convergence is claimed. No P0, P1 or P3 finding was filed by either axis.

The root/Go-assigned SINGLE r0 global gate completed: all 16 require-all codec
variants GREEN, zero governance violations; broad 2,260 pass / three exact known
baseline failures / five classified skips / eight duplicate-marker deselections,
2,268 selected. There were zero new test failures. All updated user enum.case
tests remained enabled. Source, all 45 owned files, protected five, excluded 35,
indices and locks/manifests were unchanged. Pytest exit 1 remains visible; this
is not an all-green broad suite or acceptance of the additional counterexamples.

Complete r0 evidence is retained at
`D:/projects/limbo/swift-oneof-scratch/global-gate-r0`; evidence-inventory SHA256
`93b84b7cca6fa4bf502e45a819b1babc837716335ba225ba35da33ec2650beca`,
global-results SHA256
`bad810019879df69ac807a2c8037453c8f116b9aba4da1863c1a3d444c2b75a9`.
Its source association remains the tuple above, never a future corrected tuple.

The next action is the ONE merged
[remediation plan](SwiftOneOfCheckpoint-RemPlan-1.md). Production remains frozen
until root authorizes its exact shared-state boundary and owned paths. No finding
has been self-closed; no corrective gate, extra reviewer or push is authorized.
