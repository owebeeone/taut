# TypeScript implementation results

Status: REVIEW-READY; production HOLD for the coordinator's combined JavaScript /
TypeScript pair freeze and review. No independent review, staging, commit, push,
tag, release or registry publication was performed by this worker.

Final target gate: **86 passed** in `results/target-tests.log` and XML: 72 feature
cases in `src/tests/test_typescript_oneof.py` and 14 preserved TypeScript codec /
runtime cases in `src/tests/test_ts.py`. This is one clean final run on the current
production/test source. Repeated or earlier gates are not added to that total.

The gate used stable CPython 3.13.5 with the existing pure pytest 9.1.1 distribution
on PYTHONPATH; unrelated third-party plugin autoload was disabled. It ran real
strict `tsc` 7.0.2 typechecking/transpilation and Node 24.22.0 execution. Earlier
exploratory runs through the installed pytest launcher used the old Python
interpreter and are not substituted for this stable final evidence.

The actual `taut-shape-ts` library passed its standard **`pnpm typecheck` and
`pnpm build`**, including CLI, using its already declared frozen development
dependencies: TypeScript 5.9.2, @types/node 24.3.0, undici-types 7.10.0. They were
installed with `--frozen-lockfile --ignore-scripts` for verification only. No
dependency declaration or lockfile version changed; lock SHA256 before/after is
`e110b44300bc75e28489500b7d2165b27414e2c6283853d7e4220b5fc27e06db`.
Ignored node_modules/build outputs and the local store remain outside the allowlist.
The actual library's final Node suite reports **315 passed, zero failed/skipped**
(313 existing cases plus two new foundation identity checks). See the three
`results/library-*.log` receipts. These counts overlap other coordinator gates
and must not be added to their totals.

## Contract and actual-artifact evidence

- Normal `emit`/CLI uses mandatory immutable descriptors and typed bindings in
  both modes. Enabled class wrappers call one shared engine. Disabled interfaces
  and independently compiled disabled/enabled children use actual exported Fields
  data projections without constructor/method assumptions. Strict negative service
  proofs reject calling validation methods on decoded nested data.
- Exact Python-normalized code/rule/path/deferred/scope/valid/complete/fast results
  match for local/recursive reports, virtual groups, shared children, canonical
  int/bool/str map paths, i64 extrema and active-ancestor cycles. Presence, drafts,
  repair, sparse oneof JSON and dense CBOR execute in source/package/supplied modes.
- Unknown CBOR tags survive actual decode -> enabled constructor/plain disabled
  data -> re-encode. The native optional residual Map is retained by reference,
  excluded from descriptors/validation, and only its exact schema field collision
  is rejected. Other valid double-underscore names remain supported.
- Local foundation artifacts compile from exact canonical source bytes and carry
  content provenance. An actual library package is built with `pnpm build`, packed
  locally with `npm pack --ignore-scripts`, extracted and executed. Two application
  schemas and library-generated descriptors/engines share actual descriptor,
  report, error and codec identities in source/source, source/package and
  package/package combinations. CJS/ESM facades return the same actual classes/state.
- Separate compiled child artifacts are used without source regeneration. Actual
  substituted changed-field, changed-effective-option, old and split-owner children
  fail; actual old codec/schema/JSON/descriptor/engine artifacts fail independently
  of binding claims. Compatible unequal build labels work. Fields/Case/enum-map
  ordering is normalized while genuine imported codec facts remain checked.
- Descriptor-only source runs without validation-engine source or imports,
  compiler/authoring modules, shape engines or transports. Recursive links terminate
  publication; missing/wrong-category/version/unknown-rule/options metadata fails
  before usable validation. Reports, paths and metadata are frozen/copied snapshots.
- Recorded shared users survive the tested mode/validation changes. Target tests
  cover modified/unrecorded output and manifests, shared users/equivalent roots,
  and ambiguous Windows namespace components. Other physical-root safety delegates
  to the accepted common guards, locks and mutation preflight, with the wider
  shared integration matrix owned by the coordinator. The namespace guard receives
  raw spelling before Path coercion; all four final target cases pass on stable Python.

The runnable source/package example passed strict compilation and execution and
produced identical results (`results/example-results.json`). It demonstrates a
plain Fields object, explicit class construction, invalid serialization, repair,
descriptor identity and explicit validation. No generic factory is used.

## Evidence boundaries

Historical `target-tests-failed-first.*` records 78 passes plus one old API-only
transport fixture failure. The fixture now explicitly selects its service, keeping
all call/stream malformed-decode assertions intact. `target-tests-before-data-projection.*`
and `target-tests-before-residual.*` retain earlier clean 79- and 84-case gates.
They are labeled historical and are not current-source totals.

No new global all-language matrix was run by this worker. The coordinator owns
that combined gate and preservation of the accepted Python/Rust/JVM checkpoint.
The known missing historical document and two Windows Go formatting baseline
failures are not changed or relabeled as successful. No full-suite-green or
all-nine-language-complete claim is made.

Virtual selection remains intentionally deferred/incomplete. TypeScript and
JavaScript retain separate native codec projections and owners. The class named
Object collides with tsc's CommonJS intrinsic and fails clearly when enabled;
disabled structural Object interfaces remain possible. New Fields/data symbols
are checked for actual collisions in both modes. Source/library composition
requires an explicit chosen owner and build-time facades; no owner is discovered
or silently copied at application runtime. See README for the concrete binding ABI.

Both repositories' final `git diff --check` passed. The exact target-owned allowlist
is `TypeScript-OwnedFiles.json`; shared scaffold/CLI/pyproject/common physical-path
changes belong to the JavaScript/shared worker. User-owned Python authoring files
were not edited by this worker.
