# Java execution results — 2 November 2026

## Remediation1 — awaiting originating review

Both initial reviewers returned NO-GO at Taut92c6894d/root07b5853c. The
verbatim reports and one merged disposition are filed in the pair checkpoint
review records. Remediation1 fixes Java field/Case-order fingerprint
normalization and signed-i64 enum literal spelling, plus shared CLI/helper help.
No descriptor/adapter/report/engine API, runtime contract/owner, wire semantics
or filesystem mutation boundary changed. The user Enum.case work is excluded.

All17 new regression cases passed: eight independent reordered child/parent
field+Case composition combinations across validation modes/distributions,
four real field/rule/reservation/effective-option mismatch rejections, four
source/package/validation signed-i64 enum compile/run/codec/metadata matrices,
and one shared help test including Kotlin's helper default.

The affected full target command (Java feature+existing Java regressions,
both Java codec-parity variants, CLI/scaffold and real compiler-wheel generation/
Java+Kotlin compilation/execution) reported141 passed and one stale source-shape
assertion in123.70s. That assertion alone expected BUILT(1), the exact literal
spelling intentionally corrected by the review; it now expects BUILT(1L).
Its isolated rerun passed in0.12s with production unchanged. Thus all142
distinct targeted cases have passing evidence across the141+1 runs. The raw
failed-first log remains preserved; no clean142-pass single run is claimed.
Relevant Python/Rust/core/options/IR/reserved-name preservation:865 passed in
46.66s. See ../jvm-oneof/remediation-r1/ for exact logs. Java example source/
package and engine-free adapter runs pass; golden deltas are enum long suffixes.

The sole broad/all16global gate remains honestly tied to the ORIGINAL frozen
Taut92c6894d/root07b5853c tuple:16 codec variants GREEN, broad1620 passed,
3 established baseline failures,4 skipped,8 deselected, no new failure and
unchanged source/tuple. Original receipts are preserved verbatim under
../jvm-oneof/global-r0/. It is not relabeled as running on remediation1, and
root explicitly directed against an automatic duplicate global run for these
localized corrections. Originating reviewers must re-run the counterexamples
against the newly settled R1 tuple before any finding closes.

## Original implementation evidence (historical source92c6894d)

Implementation is REVIEW-READY, pending the coordinator's settled Java/Kotlin
pair freeze and independent reviews. This document does not claim acceptance,
publication, a registry release, or a Git commit/push.

The final main command ran test_java_oneof.py, test_java.py (including its shared
Java/plain and Java/fc codec gate), test_jvm_compiler_distribution.py,
test_scaffold.py and test_cli.py: **117 passed** in 119.72 seconds. See
results/final-target-gate.log. Eight subsequently added contract cases passed:
seven native invalid-rule preflights and one actual compatible unequal runtime
build-label substitution; see results/contract-supplement.log. No production
code changed after the main gate. The current Java feature file has 88 cases.

Reference regression: test_oneof.py, test_python_runtime_distribution.py,
test_rust_oneof.py and test_reserved_names.py: **591 passed** in 63.18 seconds.
See results/reference-regression.log. This is a selected preservation gate,
not a claim that the full repository suite was run by this executor.

The main gate includes a local compiler-wheel build without isolation or
installation. Every canonical Java/Kotlin runtime resource is compared byte
for byte with the wheel payload. An isolated Python process imports that
unpacked wheel, generates both targets, then compiles/runs Java with
javac --release8 and Kotlin with JVM target1.8. No SDK, Gradle, compiler plugin,
registry package, or shape engine is part of either application runtime.

verify_examples.py generated fresh source/package consumers from the same
canonical Java closure, built a local foundation-only jar, compiled/reran the
same report corpus and found identical results. Its disabled route compiled
and ran descriptor/codec queries without ValidationEngine.class. AdapterProbe
also compiled/ran against that engine-free closure, proving direct typed
primitive reads/presence and defensive static descriptors without a message
base/interface. Canonical runtime hashes, actual package source/class hashes,
normalized source/package reports and logs are filed in results/.

Behavior checks compare actual Java results to Python's reference engine for
code/rule/path/deferred/validity/completeness/scope. They exercise missing and
extra payloads, false/zero/empty/list presence, payload-free choices, independent
groups, invalid discriminator plus children, nonselected children, local and
recursive scope, virtual deferral plus child repair, lists, string/int/bool maps,
canonical key ordering, shared-child paths, active-ancestor cycles, snapshots,
open non-oneof diagnostics and invalid-draft dense-CBOR roundtrips.

Separate child and parent compilation proves enabled-parent/disabled-child
traversal and actual shared descriptor/report/codec nominal identity in
source/source, package/package, and both mixed generation combinations.
The selected source owner is built once; dependency API bytes are unchanged.
Partial external graphs fail rather than duplicate dependent native types.
Old missing accessors/codecs fail real compilation. Inconsistent facts and
substituted actual child/runtime/codec artifacts fail publication/execution
with named regeneration/rebinding errors; an unequal compatible build passes.
There is no reliance on found-value public-constant inlining: checks call
runtime methods and immutable descriptor getters.

Mode/ownership checks cover supplied omission, source/package, agreeing and
conflicting CLI flags, Boolean programmatic flags, emit_all forwarding,
source/package and enabled/disabled transitions, shared users, equivalent '..'
roots, modified/unknown/handwritten files, incompatible contracts and ambiguous
Windows namespace/obstructed roots. Failures leave file bytes unchanged.

Migration goldens deliberately add mandatory static descriptor/adapters and
provenance in both modes, and thin instance validation wrappers only when
selected. The Java8 source projection preserves prior read-only codec collection
behavior; construction/setters/codecs still do not run semantic validation.
Contextual type keywords and ordinary Java keywords are escaped with recorded
field access identities; actual collisions fail. Java fields named descriptor,
validate and isValid are accepted because fields and methods can share names.
Metadata-like enum members are tested through native facts independently of
the user's concurrent authoring-accessor change.

Exact limitations: generated messages retain package-private visibility and
package taut; the supported external mapping route names same-package types.
There is no native Java JSON serializer in this checkout, and no Java shape
library repository exists here. No public multi-file schema projection, new
serializer, fabricated library integration, publication or install is claimed.
Java and Kotlin are independent runtime owners despite similar package names.
