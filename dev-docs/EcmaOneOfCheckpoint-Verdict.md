# JavaScript/TypeScript checkpoint — initial verdict merge

Status: **NO-GO at the initial settled tuple** after both original peer-blind
Code+Surface and State reviewers reported NO-GO. No acceptance or publication.

Taut68c24a899345367f3026372d3c67737751215a0e,
shape-ts1409634e9b1c8eea0696bf0fee560d5017f34d1f,
workspacefe244bc4915acbce58198889feae633f778fe649.
Python/Rust reference heads remain c08c2a1b/8e92b89e. Both reviewers independently
verified all101 frozen files, tuple at both boundaries, protected five user files,
35 excluded artifacts and unchanged frozen dependency lock/declarations.

Verbatim reports: [Code+Surface](EcmaOneOfCheckpoint-ReviewCode.md) and
[State](EcmaOneOfCheckpoint-ReviewState.md).

| Axis | Verdict | Open findings |
| --- | --- | --- |
| Code+Surface | NO-GO | P2-1 selected-facade ownership; P3-1 package-builder defaults; P3-2 shared JVM help regression |
| State | NO-GO | P2-1 unreadable generated slots; P2-2 mutable/malformed constraints; P3-1 same shared JVM help regression |

The [one merged plan](EcmaOneOfCheckpoint-RemPlan-1.md) maps all findings to five
distinct roots, three P2 and two P3, with exact owner/originating closure. It
records the Code/State accessor-boundary interpretation difference. Shared-input
agreement on the global help failure is not labeled blind convergence. Exactly
two reviewers were used; no per-target or supplemental reviewer was launched.

The sole root-assigned settled r0 gate reports all16 codec variants GREEN and
broad1807passed/4failed/5skipped/11explicitdeselections. Baseline3 are unchanged;
the new help failure remains visible with exit1. Tuple/source/protected checks
were unchanged. The complete original receipts remain under
`D:/projects/limbo/ecma-oneof-scratch/global-gate-r0`; do not relabel them as R1
evidence or full-suite green. Independent/implementer run totals overlap.

Production remains frozen until the coordinator's merged correction assignment.
Remediation rounds used:0; proposed next is1 of2. All P2 findings remain open
until the appropriate originating reviewer verifies its original reproduction
on the revised settled tuple. No source correction, self-closure, release,
publication, push, tag or next backend is authorized by this initial merge.
