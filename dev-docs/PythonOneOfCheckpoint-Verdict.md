# Python reference checkpoint — final verdict

Status: **accepted at source inventory
`3dd141a8433aaef152a285327d8091870a2eb3865eba7f8cb3cc78c70f901bd2`
after [Code/Surface](PythonOneOfCheckpoint-ReviewCode-2.md) and
[State](PythonOneOfCheckpoint-ReviewState-2.md) independently reported GO. This
accepts the Python reference batch only.** Both repository HEADs remained at their
recorded baselines during review. The exact 165-file inventory is
[Snapshot-2](PythonOneOfCheckpoint-Snapshot-2.json).

The operator then required one authorization-only correction to the README
opening. Both axes approved the amended commit inventory
`f72b5bcf607a108a45706dcab42f28f7da8e8a823937a051b98970ddb37a0298`
in their [Code](PythonOneOfCheckpoint-ApprovalCode-Authorization.md) and
[State](PythonOneOfCheckpoint-ApprovalState-Authorization.md) addenda.
[CommitSnapshot](PythonOneOfCheckpoint-CommitSnapshot.json) records that tuple;
all production and test bytes are identical to the independently reviewed code.

Authorized commit title: **Implement Python oneof descriptors and explicit validation**.
Only the explicit Python/core/IR/runtime, shape-Python integration, intended
packaging proposal, example inputs/goldens/evidence and filed review documents are
included. Local generated bundles with absolute ownership receipts, wheel/build
outputs, scratch/probe trees and unrelated work are excluded.

All six P2 findings are reviewer-closed after two bounded remediation rounds.
There are no open findings in this checkpoint. The second round completed the
same filesystem preflight root cause for deletions as well as writes; neither
reviewer identified a new architecture requiring replacement reviewers.

The operator subsequently authorized committing the working Python milestone via
GWZ and starting Rust in a separate chat. That supersedes the earlier no-commit
task constraint; pushes, tags and releases remain unauthorized. Rust production
integration must wait until this reviewed Python milestone is committed. The
other seven backends are deferred. This agent implements no Rust changes.

The operator explicitly confirmed both naming decisions: leading double
underscores are out for Python schema fields (internal substrings remain valid),
and the Enum design and early `name`/`members`/`options` reservation remedy stay.

Final verification is recorded in [the examples results report](examples/python-oneof/RESULTS.md):
128 feature tests passed; 190 shape-library tests passed; the final broad suite
reported 1,375 passed, three unchanged baseline failures, four skipped and eight
gate deselections. The 128 feature cases are included in those 1,375 passes and
must not be added again. All 16 existing codec parity variants ran GREEN. The
final local wheel matches all 12 canonical foundation files and passes isolated
application/library identity checks with compiler imports blocked.

This is not a full-suite-green, all-language-complete or release-ready claim.
The missing baseline document and two original Windows Go newline checks remain
disclosed, with concrete isolated-HEAD evidence. Virtual selection is deliberately
deferred/incomplete. Interrupted multi-file output updates remain fail-closed and
can require a fresh root or explicit user-managed migration.
