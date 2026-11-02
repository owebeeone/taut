# Combined ECMA remediation1 — affected checks

Status: implementer evidence for the single authorized merged remediation1;
not reviewer closure or acceptance. The original settled r0 global gate remains
historical and retains its exit1 and four failures.

The shared affected gate passed **503 tests, with one skip**, in28.00seconds.
It ran JS oneof, shared JS/TS distribution/service/package/wheel checks, legacy
JS, scaffold, CLI, reserved names, and the complete original JVM help-contract
test. The skip is the existing Windows symlink-privilege case. The two earlier
focused help cases also passed; their overlapping count is not added.

Receipts are filed under `examples/js-oneof/results/remediation-1-*`: exact
command/environment/exit receipt, full log and JUnit XML, before/after source
inventories, and the runner. Both inventories are identical. They include
tracked feature source/tests plus changed/new source/tests, all five protected
authoring files, all35 excluded old Python artifacts, both member refs and
indices, and the frozen actual-library lock. Both indices remained empty and
the lock retained SHA256
`e110b44300bc75e28489500b7d2165b27414e2c6283853d7e4220b5fc27e06db`.

The shared correction retains substantive targets, method names, JSON inputs,
defaults and JVM artifact guidance. CLI help now distinguishes optional Java
jar and JS/TS tgz artifacts. The complete previously failing JVM assertion
sequence passes, with a separate expanded ECMA/JVM help regression.

The TypeScript worker separately records169 affected passes and actual-library
typecheck/build plus315 Node test passes in
[RESULTS-R1](examples/typescript-oneof/RESULTS-R1.md) and its results-r1 receipts.
The final169-pass run uses the explicit read-only historical-origin fixture.
Its owned manifest and source associations are reconciled in the combined
inventory before refreeze. These independent/overlapping totals must not be summed.

No broad or all16 parity gate was repeated. The r0 record remains1807 passed,
4failed,5skipped,11explicitdeselections; three proven baselines and one new
help failure. R1 focused help success does not rewrite that failed receipt.
All three P2 findings remain open until the originating reviewers replay their
original counterexamples on the corrected exact tuple.
