# Rust OneOf checkpoint — remediation 2 (final)

Object: Taut `ba4240778143a382be381c0f16d3659ab097ad47` and Rust shape
`8e92b89ed3a4f218a5a4e018fbfee6301fcc14b4`. Code reports GO; State closes
State/P2-1 and reports new State/P2-2, explicitly classified as a bounded
implementation defect rather than a new architectural root cause.

| Finding | Disposition | Correction and originating closure test |
| --- | --- | --- |
| Code/P2-1 — Box collision | Retain closed correction | Keep qualified allocator paths and all eight compile cases; Code reviewer checks retained closure. |
| State/P2-1 — equivalent owner/user spellings | Retain closed correction | Keep lexical alias checks, canonical roots/users, shared-user accounting and physical write/delete contradiction preflight; repeat original immediate-build counterexamples. |
| State/P2-2 — Windows namespace-prefix conversion changes identity | Fix by conservative rejection | Inspect original namespace components before resolving or removing drive/UNC prefixes. Reject trailing dots/spaces, reserved DOS device names and reserved filename characters. Use the same identity helper for roots, users, locks and application targets. Reproduce physically distinct ordinary and extended trailing-dot AND trailing-space schema-output/runtime-owner directories; refusal must leave both trees byte-identical and create no new output/lock. Preserve safe ordinary extended-prefix equivalence. State reviewer repeats its originating counterexample and verifies closure. |

This is one localized patch inside the existing identity/preflight boundary.
The operator coordinator explicitly selected the fail-closed rejection permitted
by the State report; support for exotic Windows namespace filenames is not a
checkpoint requirement. Document the rejected class in the public example guide.
No runtime ABI, architecture, semantic validation, release or registry changes.

Run retained focused/shared/Python regressions, inventory, foundation/shape checks,
working examples, package proof and codec parity. Both original reviewers receive
the revised committed tuple and perform final changed-range/closure reviews.
No implementation self-closure; no push before both GO. If a blocking finding
remains after this final round, report the concrete blocker and stop for decision.
