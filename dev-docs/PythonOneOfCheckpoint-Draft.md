# Python OneOf reference checkpoint draft brief

Authority: the operator explicitly authorized the Python reference batch and
necessary shared compiler/IR changes, plus taut-shape-py integration, directly in
Limbo without a worktree. This supersedes documentation-only scope in
OneOf-ExplicitValidation-BuildProposal.md. No other backend implementation,
release, commit, push or tag is authorized.

Controlling design: OneOf-ExplicitValidation-BuildProposal.md, all Python-relevant
sections, especially runtime distribution section 7 and conformance section 8.
Original observed gaps were missing native authoring/rule IR, missing Python source
runtime, no mandatory metadata/engine and application-time DSL loading in the shape
library. The batch addresses those through the existing compiler route.

Review tier: dual (Code + Surface and State), because this changes public APIs,
CLI flags, descriptors and JSON projection. The source object is frozen by a
SHA-256 file inventory plus the two unchanged repository HEADs; the user forbids
commits, so a hash-identified working tree replaces a committed review tuple.
No source mutation is permitted during each review round.

Scope: all source files in taut/src/taut, tests in taut/src/tests, Python example
scripts/schema/goldens and taut-shape-py/src plus its regeneration script, as listed
in the review snapshot. Other-target sources are included only as regression
reference and must remain unchanged. Evidence/results/review documents are outside
the code digest; reviewers should read the examples README and actual logs too.

Validation: latest feature and shape-suite results are in
dev-docs/examples/python-oneof/results. The broad run reported 1,339 passes including
94 then-current feature cases, five failures, four skips and eight gate deselections.
All five failures have concrete unchanged-HEAD/environment evidence, not inferred
baseline status: the isolated HEAD archive reproduces missing documentation, both
Go newline checks and Java stdout encoding; read-only Git reproduces ownership
failure. Java/Git corrected rerun has two passes. Three original baseline tests
remain failing and are disclosed. Codec parity ran all 16 variants GREEN, separate
from new-feature conformance. No all-suite-green or release claim is made.

Expected review focus: semantic/traversal completeness, actual runtime nominal
identity and contract publication, immutable reports/descriptors, source closure,
library normal-wire import graph, Python schema/name safety, flags/forwarding and
safe filesystem ownership/transitions. Virtual checks remain deliberately deferred;
other language implementations and the unrelated baseline defects are out of scope.
Deferrals do not exempt the shape/defaults/diagnostics of the Python public surface.
