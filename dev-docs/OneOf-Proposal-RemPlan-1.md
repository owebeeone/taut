# OneOf proposal — remediation plan 1

Baseline: isolated snapshot 8d7a8bff959a5711362a0aba107a62aaeee4a94a.
Merged verdict: NO-GO; Safety GO, Consistency one P2. No blind convergence on a defect.

| Finding | Disposition | Correction | Closure test |
| --- | --- | --- | --- |
| Consistency P2-1 | Fix | Define validator eligibility by all owned schema-reachable non-virtual checks, not just local groups; clarify both omission clauses and add root traversal acceptance case. | Original Root virtual -> Child nonvirtual missing payload must have root entry point, root-relative error and deferred parent group; after repair valid true / complete false; pure virtual scalar-only root still has no entry point. Consistency reviewer must verify. |

One merged proposal-only patch. No new public API, discriminator behavior, mutation boundary or compatibility rule is introduced; this clarifies which entry points realize the already-required traversal. Same two reviewers receive focused re-verdicts on the same revised tuple. Safety confirms continued GO on the changed range; Consistency closes its own counterexample. No implementation/test builds, workspace commit or push.
