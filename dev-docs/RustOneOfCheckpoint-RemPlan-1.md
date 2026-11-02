# Rust OneOf checkpoint — remediation 1

Object: Taut `020f7b08d379e2a27720eda102c2782dfcc55e3e` and Rust shape
`b55cd89e76830e61f8580c5f5e0b38519e7cef95`. Both independent reports are NO-GO.
There are two distinct blocking roots, identified by axis-qualified IDs because
both reports use P2-1. No blocking finding is self-closed by this plan.

| Finding | Disposition | Correction and closure evidence |
| --- | --- | --- |
| Code/P2-1 — unconditional unqualified Box import | Fix | Remove that import; qualify allocator Box storage/construction where recursive layout needs it. Preserve valid schema types named Box. Compile message and enum Box with validation on/off in source/package modes, plus existing recursive-layout cases; originating Code reviewer repeats its counterexample. |
| State/P2-1 — equivalent roots delete live source owner | Fix | Validate lexical root/ancestor safety before resolving filesystem identity. Normalize current/prior runtime roots, schema directories and user identities before deduplication/accounting. Reject conflicting physical write/delete plans before application. Keep junction/reparse/obstruction protection. Reproduce one-producer, shared enabled/disabled users and equivalent schema output-directory cases through emit; immediately build/run generated output; originating State reviewer repeats its exact one/two-user counterexamples. |

One merged patch implements both corrections. It does not change public runtime
ABI, descriptor/report contracts, native rule semantics, release numbering or
the selected foundation route. The common output application preflight may gain
the physical-target contradiction guard required by State/P2-1; this remains
inside its existing pre-write mutation boundary and is covered by shared/Python
regressions. Alias checks must happen before canonicalization so unsafe directory
links are not silently made acceptable.

Implementation/probe note: normalization also folds Windows extended drive/UNC
prefix spellings. A direct host probe showed Path.resolve preserves the prefix,
so resolve alone is insufficient for that equivalent spelling. The same identity
helper is used for lock deduplication and physical-target contradiction checks;
Rust root/user planning still checks the original lexical ancestors first. A
source/output-prefix regression builds/runs immediately and retains one user.

Both reports describe localized corrections without broader redesign. Continue
the same two reviewers with the revised committed tuple and this merged plan;
ask each for its originating closure and changed-range analysis. If a reviewer
determines the patch changes an architectural boundary requiring fresh reviewers,
follow the skill's replacement rule rather than adding a third reviewer.

Run Rust/shared/Python feature and existing Rust regressions, canonical inventory,
source/package examples/package proof, foundation/shape no_std and Clippy checks,
unchanged process-global checker and codec parity after the patch. Preserve the
three demonstrated broad baseline failures and environment limitations. No push
until both blocking findings are closed with GO reports on the corrected object.
This is remediation round 1 of the maximum two allowed for this object.
