# Combined JavaScript/TypeScript OneOf checkpoint — STATE-AXIS REVIEW

**Review object:** Combined JS/TS implementation, actual `taut-shape-ts` integration, shared output helpers and controlling `dev-docs/EcmaOneOfCheckpoint-Draft.md`, frozen at the tuple below. Status: source checkpoint under review, not accepted.

**Baseline:**

| Repository | Reviewed HEAD |
| --- | --- |
| Taut | `68c24a899345367f3026372d3c67737751215a0e` |
| taut-shape-py | `c08c2a1b5197f761c5b0b835c588da512130ceda` |
| taut-shape-rs | `8e92b89ed3a4f218a5a4e018fbfee6301fcc14b4` |
| taut-shape-ts | `1409634e9b1c8eea0696bf0fee560d5017f34d1f` |
| workspace | `fe244bc4915acbce58198889feae633f778fe649` |

Reviewed full Taut range `8c113e36a927cda5c50848f25ab828185080272d..68c24a899345367f3026372d3c67737751215a0e`, shape-ts range `74597e5e3a1d3845e93644866b97b68080f4bbbe..1409634e9b1c8eea0696bf0fee560d5017f34d1f`, and the two managed workspace receipt changes. Sources were read from committed blobs, original files and hash-verified isolated exports.

**Date:** 2 November 2026, Australia/Sydney.

**Axis:** State — durable ownership, filesystem identity, mutation ordering, restart legality, fail-closed behavior, immutable observation state and compatibility publication. Independent, adversarial, read-only. The other axis runs in parallel; nothing here relies on it. Filed verbatim by the lane owner.

**Verdict: NO-GO** — two P2 findings block. One additional P3 identifies the new global regression-test failure. I pre-commit to GO on a revision that resolves P2-1 and P2-2 as specified and preserves the checked boundaries.

---

## 0. Evidence base

### Authority and reviewed inventory

Read:

- The canonical generated State prompt, verified SHA256 `1500998aeb25559d6fffa5e86897270e65c11b44305a805156e7b65dfeec7814`.
- The review-loop skill, workspace `AGENTS.md`/`AGENTS_GWZ.md`, and both changed repositories’ `AGENTS.md`.
- The full `OneOf-ExplicitValidation-BuildProposal.md`.
- Committed `EcmaOneOfCheckpoint-{Authority,Draft,Preparation}`.
- Both targets’ README and RESULTS documents, plus JS INTEGRATION.
- Accepted Python, Rust and JVM State verdicts and their relevant original counterexamples.
- Both target emitters/metadata builders, canonical descriptors/reports/validation, runtime planners and package helpers.
- Shared `python_runtime.py`, scaffold planning/locking/application paths, and the actual shape-ts foundation build, facades, package exports and generated metadata.

Verified all five HEADs at review start and end. They matched the table above.

At both boundaries, independently compared the 73 Taut and 28 shape-ts frozen entries against committed blobs and original working bytes. No mismatch occurred. Initial exported review copies also matched. The exact changed-file sets matched the snapshot inventories. Preparation’s own committed blob was included.

Verified:

- Frozen snapshot SHA256 `6b3a931d8640d4e76bcb46a8004f45299d4d0cbd3b3cbe1741e94a0bc310705d`.
- All five protected user-source hashes unchanged.
- All 35 excluded Python artifact hashes unchanged.
- Unchanged shape-ts dependency declarations and lockfile, SHA256 `e110b44300bc75e28489500b7d2165b27414e2c6283853d7e4220b5fc27e06db`.
- Workspace changes limited to `gwz.conf/gwz.lock.yml` and `gwz.conf/markers/conf-integrity.yml`.

No current-round peer prompt or report was inspected. No helpers were spawned. No original reviewed file was modified.

### Independent execution

All new outputs stayed below:

`D:/projects/limbo/ecma-oneof-scratch/review-r0/state`

Test shells used the prescribed toolchain activation, isolated-source PYTHONPATH, disabled pytest plugin autoload and disabled Python bytecode.

| Check | Result |
| --- | --- |
| Prescribed seven-file durable/artifact selection | **86 passed, 1 skipped, 387 deselected** |
| Fourteen selected semantic/artifact test nodes, including parameterizations | **32 passed** |
| Actual shape-ts `pnpm typecheck` | Passed |
| Actual shape-ts `pnpm build` | Passed |
| Actual shape-ts `pnpm test`, after completing isolated corpus fixtures | **315 passed, zero failed/skipped** |
| Generated TS field-read adversary, strict compilation and Node execution | Reproduced P2-1 |
| Generated JS counterpart to the field-read adversary | Located `child.kind` issue; fast result false |
| TS duplicate/extra-parameter constraint publication probes | Reproduced P2-2 |
| Strict TS mutable-constraint probe, without an `any` cast | Compiled; reproduced P2-2 |
| Same mutable-constraint attack against built actual-library CJS foundation | Reproduced P2-2 |
| Fault injection across enabled→disabled output transitions | Correct retry or explicit fail-closed refusal |

The 32-case selection exercised both Python-normalized targets, source/package/supplied behavior, immutable metadata/reports, independent disabled children, i64 key paths, cycles, JS fast-path allocation checks, existing malformed-metadata negatives, TS residual roundtrip, actual packed library compositions and recursive service-data proofs.

The initial library test attempt lacked the exported sibling oracle corpus: 155 tests passed and seven modules failed with ENOENT. This was an isolated-fixture setup failure. The subsequently supplied corpus was verified against committed `taut-shape` reference `89916c4d017123d7c16f094eb2fba6ece98facc0`, all 190 files. Its reference-manifest SHA256 is `3d0df94c2ae067ff1e513a1f7ee24c903ee4016ba0969e73ee2c54c972fc0e23`. The completed 315-pass rerun used that verified data.

Independent reproduction artifacts include:

- `state-adversary-probe.py` and `independent-probes/probe.ts`.
- `independent-probes/mutable-strict.ts`.
- `mutable-constraint.cjs`.
- `crash-probe.py`.
- `js-getter-control/`.

These are review probes, not edits to implementation or existing test source.

### Completed settled global evidence

Consumed the completed root-assigned evidence under:

`D:/projects/limbo/ecma-oneof-scratch/global-gate-r0`

Read global results, commands, parity results, broad failure traces, baseline-source proof, skip/deselection classification, actual-library receipt scope, and before/after tuple/source/protected inventories.

Independently compared the before/after JSON inventories: tuple, source and protected state were equal.

Results:

- **All 16 codec parity variants GREEN**, no governance violations.
- Broad suite: **1,807 passed, 4 failed, 5 skipped, 11 deselected**.
- Three failures match the established baseline: missing historical API-surface document and two Windows Go formatting checks.
- One new failure is the stale JVM help assertion described in P3-1.
- No unclassified deselections. Eight exclude already-executed parity gates; three preserve the user-owned Enum.case policy boundary.
- Skips are explicitly attributed to unavailable Windows symlink privilege, three POSIX-oriented toolchain tests, and the unavailable wasm32 target.
- Exact tuple, production hashes and protected hashes remained unchanged.

The historical JVM all16/1,620-pass evidence remains attributed to its original `92c6894d…`/`07b5853c…` tuple. It is not relabeled as this checkpoint’s evidence. Overlapping test counts are not added.

## Problem, requirement provenance, and scope

The operator-authorized outcome is working JS and TS support through the existing compiler route: mandatory complete immutable descriptors, optional exact instance validation, shared reports and engines, explicit source/package/supplied distribution, independent dependency composition, actual TS library ownership and safe output transitions.

The concrete prior deficiencies were missing JS/TS metadata and instance validation, unconditional runtime copying without the required ownership lifecycle, and an actual TS library lacking a foundation-only shared owner. The Authority record traces the all-nine implementation directive, Python/Rust milestone, two-at-a-time continuation, service-data/residual amendments and explicit combined freeze/review authorization. Those directions supersede the proposal’s historical documentation-only/Python-stop clauses.

The implementation uses the supported emit/emit_all, native IR and codec routes. Fresh source/package applications, independent-child tests, actual library typecheck/build and packed compositions establish feasibility without a second compiler, runtime installation, dependency upgrade or fabricated JS library. Localized emitters, canonical resources, shared output helpers and actual shape-ts foundation integration are authorized components.

The shared raw-namespace correction addresses a demonstrated path-conversion problem at the existing identity boundary. It does not require a new interpreter baseline. The declared frozen library development dependencies support the existing build route; they are not application-time prerequisites. Dependency declarations and lock bytes remained unchanged.

The prefreeze service correction is necessary because decoded values are recursive plain data. Its actual exported Fields imports and strict negative/runtime proofs passed. The residual correction preserves native unknown tags without adding them to portable descriptors.

No unauthorized component expansion or unsupported blocking infrastructure prerequisite was established. Python/Rust/JVM remain reference/preservation boundaries, apart from the authorized common helper. User Enum.case changes, virtual selection implementation, new backends, JS JSON APIs, cross-target codec unification and release/publication remain outside this checkpoint.

The two P2 findings concern required publication/diagnostic guarantees. Neither requires changing the requested architecture.

## 1. Findings

### [P2-1] TypeScript typed field reads leak input-access exceptions instead of producing located diagnostics

**Location:** Taut `src/taut/gen/runtime/typescript/validation.ts:53`, `:58` and `:66`; identical canonical copy in shape-ts `foundation-src/validation.ts`. Generated direct readers originate in `typescript_metadata.py`.

**Violated invariant:** Dynamic misuse encountered through a known generated binding must yield a located issue. A bad discriminator suppresses only its dependent selection checks; report mode continues independent checks. Fast validation must return false for such invalid input.

**Reproduction:** Generate enabled `Child` with a stored OneOf discriminator and `Parent` containing `Child`, then:

```typescript
const child = new Child({kind: "yes", value: "ok"});
const parent = new Parent({child});

Object.defineProperty(child, "kind", {
  get() { throw new Error("unreadable tag"); },
  configurable: true
});

parent.validate();
parent.isValid();
```

Both operations throw `Error: unreadable tag`. The strict-compiled reproduction is retained in `independent-probes/probe.ts`.

The same attack against generated JS returns `oneof.invalid_discriminator` at `child.kind` and Boolean false. Thus the established target route demonstrates the required bounded behavior.

**Root cause:** The TS engine directly invokes `b.read` without a field-read error boundary. The outer `finally` only removes ancestor state; it does not convert an unreadable generated slot into a diagnostic.

**Impact:** A mutable draft with an unreadable slot aborts validation, loses its diagnostic path and prevents collection of independent issues. Callers cannot rely on the promised report/Boolean failure behavior.

**Required correction:** Add a shared safe-read path around generated field access. Convert discriminator failures to the located discriminator issue and ordinary/payload read failures to located shape issues. Preserve independent traversal and keep actual metadata/configuration failures distinct.

**Closure test:** Exercise throwing getters at a nested discriminator, payload and ordinary child field. Assert exact paths, false fast results, continued independent report issues, correct local/recursive behavior and no report allocation in fast mode. Repeat through canonical source and actual-library package ownership.

### [P2-2] TypeScript publication admits mutable and malformed constraint records

**Location:** Taut `src/taut/gen/runtime/typescript/descriptors.ts:82–86` retains constraint elements; `:169` incompletely validates them. Identical canonical copy exists in shape-ts `foundation-src/descriptors.ts`.

**Violated invariant:** Published descriptors are immutable snapshots. Known rules require complete, valid normalized declarations; unsupported rule metadata must fail configuration checking rather than become successful validation.

**Reproduction A — mutable accepted record:** A strict TypeScript program, without `any`, supplies:

```typescript
const supplied = {
  rule: ONEOF_RULE,
  parameters: {controlling_field: "kind"}
};
```

Pass `[supplied]` to `MessageDescriptor`, construct the matching binding and successfully call `publish`. Then:

```typescript
supplied.rule = "future.unsupported.rule";
```

Observed result:

```json
{
  "constraintFrozen": false,
  "publishedRule": "future.unsupported.rule",
  "valid": true,
  "complete": true,
  "fast": true
}
```

The descriptor retains the caller’s mutable object. The same attack reproduced against the newly built actual library.

**Reproduction B — invalid normalized grammar:** For a descriptor with independent `left` and `right` groups, publication accepts two constraints both naming `left`, omitting `right`. It also accepts additional unsupported parameters. Both cases are retained in `independent-probes/probe.ts`.

**Root cause:** Publication checks only array length, rule spelling and whether a coercible controlling-field value names some group. It does not require the shared immutable `ConstraintDescriptor`, exact parameter grammar or a one-to-one set of controls. The descriptor constructor copies the array but retains its elements.

**Impact:** Successfully published metadata can change afterward, and malformed known-rule declarations are admitted. The engine walks groups rather than the changed constraint list, so unsupported published rule metadata can coexist with valid, complete, true results. This defeats the required immutable and fail-closed publication boundary.

**Required correction:** Require canonical immutable constraint records or defensively construct equivalent immutable snapshots. Validate the exact known-rule parameter grammar and require exactly one constraint for every group, rejecting duplicate, missing, extra and incorrectly typed controls. Preserve canonical synchronization into actual shape-ts.

**Closure test:** Add strict-TS and runtime cases for caller-owned mutable records, post-publication mutation, duplicate controls, extra parameters and invalid control types. Publication must reject malformed input or retain an immutable independent snapshot. Valid independent/virtual groups must continue to publish and validate through source and actual-library package routes.

### [P3-1] Shared help wording leaves the accepted JVM regression assertion stale

**Location:** Taut `src/taut/cli.py` shared `--with-validation` help; `src/tests/test_java_oneof.py:564`.

**Violated invariant:** Required regression checks must reflect the supported interface while preserving their substantive assertions.

**Reproduction:** The completed settled broad gate fails `test_jvm_help_describes_supported_targets_json_files_and_defaults`. It expects the exact substring:

`Java/Kotlin methods: validate/isValid`

Current help correctly says:

`JS/TS/JVM methods: validate/isValid`

**Impact:** The current broad suite has a new failure beyond the three established baseline failures. It cannot be described as baseline-only or green.

**Required correction:** Update the stale expectation to verify the expanded target set and retained JVM method names/defaults without depending on the obsolete sentence fragment. Do not remove the substantive JVM help/default checks.

**Closure test:** Run the named help test against the revised shared help and retain passing JS/TS help/default coverage.

## 2. Invariant analysis

**Complete planning and mutation preflight held under the tested attacks.** Both targets construct text plans before application. Locks cover schema directories, selected owner roots and recorded prior roots; the locked prior-root recheck detects a changed ownership reference. Physical write/delete overlap, obstructions and alias checks run before replacement.

**Historical filesystem roots were retraced.** The allowed selection repeated Rust equivalent-root/shared-user/extended-prefix cases, distinct namespace directories, physical overlap and common identity-boundary checks. JS/TS equivalent owner spellings, actual junction refusal and raw `x:y`/`x:stream` namespace tests passed. These attacks did not redirect output or delete another user’s engine.

**Shared-use lifecycle held.** Recorded enabled and disabled users survived the tested transitions. Consumers could not adopt an unavailable source owner or add missing source capabilities. Disabling or detaching one user retained components needed by another. Unknown, handwritten, modified, incompatible and obstructed target files were refused before output replacement.

**Crash direction held within the documented contract.** Independent fault injection interrupted enabled→disabled transitions before every planned replacement/deletion: nine mutation steps for JS and thirteen for TS. Failure before the first mutation allowed a normal retry. Interrupted intermediate states explicitly refused regeneration; completed transitions retried successfully. No partial transition was accepted as complete. This is exception-based ordering evidence, not a claim of filesystem crash rollback or power-loss atomicity. Real process death can also leave the inspection-required stale lock.

**Native validation behavior largely held.** Independent executed tests confirmed non-null presence, payload-free choices, wrong-tag suppression, independent groups, local/recursive scope, virtual incompleteness, populated nonselected-child traversal, shared paths, active cycles and canonical typed map paths including exact i64 values. Fast/report equivalence held on those inputs. P2-1 identifies the uncovered unreadable-slot boundary.

**Observation snapshots held for generated canonical records and reports.** Tests confirmed protected descriptor inventories/options, immutable report/path copies and snapshots retained after draft mutation. P2-2 identifies publication’s admission of caller-owned mutable constraint records and malformed declarations.

**Actual ownership and distribution held on exercised compositions.** Independently built disabled children, source/package/supplied consumers, actual substituted artifacts and packed actual-library compositions passed their positive and negative checks. CJS/ESM facades shared actual descriptor/report/codec identities. Foundation-only metadata operated without the validation engine, compiler, authoring loader, delivery engines or transports.

**Native data and residual state held.** Constructors retained children directly; decoded service values remained recursive plain Fields data. Strict negative proofs rejected instance-method claims on decoded children. Native TS unknown-tag Maps survived decode/construct/reencode and stayed outside portable descriptors.

**Global attribution is complete.** Current all16 parity is green, but the current broad suite is not. Three failures retain established baseline attribution; P3-1 accounts for the fourth. Protected user work and excluded artifacts remained untouched.

## 3. Risks and next action

Whole-generation crash rollback remains intentionally unsupported; interrupted output may require a fresh root or explicit migration. Cooperative locks do not protect against arbitrary external filesystem mutation. Virtual selection remains deliberately incomplete. Windows symlink and wasm32 coverage retain the recorded environment limits.

The next action is one merged bounded remediation addressing P2-1 and P2-2, with P3-1’s stale regression assertion corrected and all evidence kept accurately attributed. The originating State counterexamples must then be rerun against the revised settled tuple. This report authorizes no release, publication, push or next backend.
