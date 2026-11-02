# Java/Kotlin OneOf checkpoint — remediation plan 1

Status: **one merged localized correction authorized after both original reports
returned NO-GO**. No finding is self-closed. This is remediation round1 of at
most2 under the controlling review-loop. Original reports are filed verbatim as
JvmOneOfCheckpoint-ReviewCode.md and -ReviewState.md against Taut92c6894d /
workspace07b5853c / shape-Pythonc08c2a1b / shape-Rust8e92b89e.

The two axes independently converged on the same Java fingerprint root cause
without seeing each other's current-round findings. Code additionally proved a
Java i64 enum literal blocker and a nonblocking CLI documentation defect.
There are two correctness roots, not three architecture roots. The correction
keeps descriptor/adapter/report/engine APIs, contract versions, owner identities,
mutation boundaries and runtime rules fixed. It normalizes already equivalent
portable facts, spells existing long-valued enum numbers correctly, and documents
existing flags/defaults. Same-origin reviewers will re-run their original
counterexamples and may challenge this localized classification.

| Finding | Disposition | Correction | Closure test / verifying axis |
| --- | --- | --- | --- |
| Code P2-1 | Accept; shared root R1 | Normalize per-message fields by numeric tag and Case nominations by controlling-field/enum/member before computing Java expected/published fingerprints. Retain every other compatibility fact. | Independently compile disabled child and parent with reversed field and Case declarations; descriptor-only and enabled parent, source/package combinations, successful recursive validation+codec composition; child API unchanged. Both originating axes re-run their independent original probes. |
| State P2-1 | Accept; same R1, one correction | Same normalization as Code P2-1; no second patch or weakened mismatch checks. | Include genuine field/rule/reservation/effective-option mismatches that still fail actual publication, then originating State verification. |
| Code P2-2 | Accept; root R2 | Emit signed long literals for Java enum constructor arguments, including min/max i64, retaining numeric values and descriptor/wire facts. Baseline-origin spelling blocks required new native OneOf inputs; localized fix is in scope. | Compile/run source and package, validation on/off; cover immediately outside signed-int bounds and both i64 extrema; enum encode/decode, descriptor values, selected/payload-free semantics and fast/report equality. Originating Code re-runs its original extreme-value probe. |
| Code P3-1 | Accept; nonblocking documentation correction | Shared CLI help identifies all four supported validation targets/JVM camelCase methods, JSON FILE inputs, mapping omissions and relevant owner/binding defaults. Kotlin executor adds package helper default/flag descriptions. No option names/default behavior change. | Help-output assertions plus fresh generated source/package programs in existing target/wheel/CLI gates; originating Code verifies its cold-help counterexample. |

Java executor owns java.py, java_metadata.py, Java regression additions,
attributed Java goldens and shared cli.py/help assertions. Kotlin retains
ownership of the small kotlin_package.py help-only correction; root coordinates
that contribution into this ONE patch. No Kotlin runtime/emitter/engine change
is required by the findings. User Enum.case sources/tests stay excluded, as do
other backends, scratch/build/jar/wheel files and unrelated local artifacts.

Before changes, both reports consumed the completed sole global gate at the
original tuple: all16 codec variants GREEN; broad1620 passes/3 established
baseline failures/4 skips/8 deselected; new_failures empty and source/tuple
unchanged. Preserve that evidence at its actual tuple. It does not close the
new counterexamples and must not be relabeled as running on the revision1
correction. Root explicitly directs against automatically duplicating the
expensive global matrix for this Java-only implementation correction.

Required focused gates after the merged patch: all Java feature tests and
existing Java regressions including both codec parity variants; shared CLI and
scaffold checks; the actual local compiler-wheel/resource/generate/compile/run
gate for both targets; relevant core/Python/Rust/reserved-name preservation;
Kotlin package-help assertion. Regenerate/run Java examples/goldens through the
existing verifier and attribute only the expected long-literal spelling/fact
normalization differences. Broaden only for a concrete new shared change,
failure or reviewer concern.

Then verify user-source hashes and the precise changed-file allowlist; commit
one local scoped GWZ remediation checkpoint with evidence and managed receipt,
refreeze the exact tuple, and generate focused re-verdict prompts from the same
canonical template/record. Continue the same two reviewers with this merged plan,
original reports, full source range and changed range. Each report must include
its prior-finding closure table, original reproduction retrace, common necessity/
scope check and changed-range analysis. Implementer pass claims remain pending
until originating/same-axis reviewers verify. A new material architecture,
interface, mutation boundary, compatibility-rule or platform change would
trigger the skill's replacement-reviewer rule; none is planned here.

No push, tag, release, registry publication/installation, another backend or
unrelated project follows from remediation or an eventual GO.
