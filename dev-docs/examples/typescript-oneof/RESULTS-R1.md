# TypeScript merged round1 implementation evidence

Status: TS-owned correction REVIEW-READY; production HOLD for the lane owner's
one merged checkpoint and the two original reviewers. Implementer tests do not
self-close their findings. No independent review, staging, commit, push, tag,
release, dependency installation or upgrade was performed here.

Baseline reviewed object: Taut68c24a899345367f3026372d3c67737751215a0e,
shape-ts1409634e9b1c8eea0696bf0fee560d5017f34d1f,
workspacefe244bc4915acbce58198889feae633f778fe649. The original RESULTS.md,
results/receipts, owned manifest and settled global-r0 evidence retain their r0
association. They are not corrected-source evidence. New receipts are in results-r1/;
exploratory failed-first logs remain in the Limbo remediation-r1 scratch directory.

## Bounded changes

**R1 / Code P2-1:** generated modules supply the actual selected foundation
namespace. The canonical checker compares actual descriptor/report/CBOR exports
and codec/schema/JSON/ext API values against its owner's implementations. Namespace
objects may differ if their exported values are real aliases. A separately evaluated
codec/error/CborFloat copy or partial namespace fails before publication. Generation
does not execute the selected target module.

`requireFoundation(selected)` now returns the checked canonical Foundation identity.
Generated code requires a defined non-null owner with the expected owner/contracts/
capabilities and that exact return identity. This rejects the original r0 guard
even when compatible-looking top-level metadata lets its old checker pass; an
omitted Foundation cannot exploit undefined===undefined. Explicit library source-owner
binding uses the same defined-token/return contract. No build-label equality was
added. Genuine CJS/ESM and selected-source-owner aliases remain supported.

**R2 / State P2-1:** a shared helper catches only `MessageBinding.read` application
slot access. Ordinary exceptions become located discriminator or shape issues;
independent groups/children continue in reports. A failed payload read is not
repeated during traversal. The helper rethrows the shared ConfigurationError and
does not catch binding discovery, descriptor/link/version/options checks, ancestor
handling, predicates, report construction or the whole engine. A private sentinel
avoids allocating a wrapper/report for every field read. Fast mode still shares
the generator predicates and does not construct diagnostic/report records.

**R3 / State P2-2:** MessageDescriptor defensively reconstructs constraint records
as canonical frozen ConstraintDescriptor values with owned parameter snapshots.
Publication requires the exact known oneof parameter form, a string control and
one-to-one controls matching all groups. Duplicate/missing/unknown controls,
unsupported parameters, coercible values and future unsupported rule names fail
configuration checking. Valid independent and virtual groups still publish.

**R4 / Code P3-1:** actual TypeScript package-builder help now explains the fresh
OUTPUT directory and that validation is included by default. Runtime behavior is
unchanged. Shared CLI/JVM help R5 belongs to the JavaScript lane owner.

Base Taut remains canonical. The explicit vendor script updated the two changed
runtime resources, their provenance, and the generated library guard calls.
No delivery-engine behavior, codecs/wire projection, native schema facts, dependency
declarations/lock, other backend production or user-owned authoring file changed.

## Executed gates

**169 passed** in one final clean affected run:83new original-counterexample closure
cases +72existing TS feature cases +14legacy TypeScript cases. This final run uses
the current patch and explicit read-only origin repository setup. See
results-r1/target-tests.log/XML and commands.json. Earlier overlapping counts are
not added. The previous168pass/1fail run rejected the incompatible descriptor
artifact correctly but failed an old diagnostic-text assertion; the message was
corrected and that unchanged assertion passes in the clean run.

The new closure cases perform real strict tsc compilation and Node execution:

- Independently evaluated modern facades substitute nominal codec types, low-level
  functions, codec/schema/JSON namespaces, reports and descriptors, or omit a
  required codec export. Enabled/disabled imports reject through compiled source
  and actual-library ownership. Genuine namespace-value wrappers pass and preserve
  native float residual encoding.
- The exact original r0 sources are read from immutable committed Git blobs and
  compiled as stale artifacts. Old guard acceptance is independently demonstrated,
  then new generated module import rejects old direct/split facades and missing
  owner tokens in both validation modes. Source hashes are recorded in
  results-r1/r0-guard-source-hashes.json. An unversioned exported review tree sets
  `TAUT_R0_REPOSITORY` to its read-only origin Git repository; no current working
  source or network discovery is used for this artifact.
- Nested discriminator, selected payload and ordinary getter exceptions produce
  exact code/path pairs plus the independent missing-payload issue. Local/recursive
  behavior, false fast results, canonical ConfigurationError passthrough and
  instrumented no-report fast behavior pass through source and actual-library
  artifacts.
- Strict TypeScript mutable constraint records, without an any cast, become
  independent immutable canonical facts after publication. Caller mutations cannot
  change their rules/parameters. Duplicate, missing, extra, non-string/coercible,
  symbol-parameter and unsupported-rule configurations fail. Valid independent/
  virtual cases continue to validate through both owner routes.
- Actual package-builder `--help` output contains the default/payload/output
  guidance. Existing residual, normalized Python-report, data-projection, independent
  child, source/package/supplied and packed actual-library composition proofs pass.

The actual shape library's **pnpm typecheck and pnpm build passed**, including CLI,
using its existing frozen declared development dependencies. **315 tests passed,
zero failed/skipped**, including explicit selected CJS and ESM namespace checks.
These library tests overlap prior library receipts and are not added to target
totals. The strict runnable source/package example also passed with identical
results. All new logs are separately attributed in results-r1/.

All41protected hashes match before/after:5user sources,35old excluded Python artifacts
and the dependency lock. The dependency lock remains
e110b44300bc75e28489500b7d2165b27414e2c6283853d7e4220b5fc27e06db.
All10vendored canonical runtime files match base Taut exactly. Both repositories'
diff whitespace checks pass. Ignored builds, package artifacts, dependencies and
pytest scratch outputs remain outside the changed allowlist.

No new broad or all16 parity gate ran. The old r0 result remains1807passed,
4failed,5skipped,11deselected with all16codec variants GREEN and unchanged old tuple;
the new help failure is never relabeled baseline. The coordinator owns combined
source association and any further integration decision.

The exact TS-owned R1 changed-file list and hashes are in
TypeScript-OwnedFiles-R1.json. All original reviewer findings remain subject to
their original counterexample reruns and closure verdicts.
