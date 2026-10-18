# Taut Res+Ext Phase 2 Swift Prompt Review 55-2

## Findings

1. **[P1] The Swift prompt still names the wrong residual field.**  
   The prior P1 blocker is still unresolved. `dev-docs/TautResExtP2-Swift.md:6-7` says `src/taut/gen/swift.py` emits `wireResidual`, but the current Swift generator emits `wire_residual` (`src/taut/gen/swift.py:110`, `src/taut/gen/swift.py:123`, `src/taut/gen/swift.py:141`, `src/taut/gen/swift.py:155`) and existing Swift tests assert that spelling (`src/tests/test_swift.py:46-50`). Following the prompt literally could send the Phase 2 agent into an unnecessary Swift API rename, or cause tests/harness code to target a nonexistent property. Update the Swift brief to say `wire_residual`.

2. **[P2] Swift extension error semantics remain underspecified.**  
   The prior error-semantics concern is still unresolved. The base brief requires a band check with an error for `tag < BAND_START` (`dev-docs/TautResExtP2-Base.md:48-49`), and Python raises `ValueError` (`src/taut/ext.py:19-21`), but `dev-docs/TautResExtP2-Swift.md:13-17` does not say whether Swift `extSet`/`extGet`/`extClear` should be `throws`, `precondition`, or `fatalError`. It also does not specify behavior when `host` decodes to a non-map. The current `ext_vectors.json` has only valid positive/null cases, so two Swift implementations can both pass the corpus while exposing incompatible failure behavior. The prompt should either pin the Swift error style or state that invalid-tag/malformed-host behavior is out of the Phase 2 corpus contract.

3. **[P2] The verification path is now feasible, but the prompt still assumes missing test tooling.**  
   `swiftc` is available, and the current Swift generator/runtime can compile and byte-match all four committed residual vectors in a temporary harness. However, the base definition of done still requires `PYTHONPATH=src python3 -m pytest src/tests -q` (`dev-docs/TautResExtP2-Base.md:84`), while this checkout has no importable `pytest`. The prior testability concern is therefore only partially resolved: Swift corpus work is implementable with direct `swiftc` harnesses, but the prompt should name the Python test prerequisite or give a direct non-pytest verification ladder for agents in a minimal environment.

## Prior Blockers

- **Resolved: Phase 1 corpora/fixture prerequisites.** `ir/resext.taut.py` now exists with `Host`, `Decision`, and `BAND_START + 1` (`ir/resext.taut.py:17-24`), and both oracle files are committed: `corpus/residual_vectors.json` has four rows and `corpus/ext_vectors.json` has five rows. `run_tests.py` regenerates `taut.corpus.resext_build` (`run_tests.py:20`), and `src/tests/test_resext_vectors.py:16-64` locksteps the committed JSON against the generator and Python oracle.

- **Resolved: `ext.swift` vendoring slot.** `scaffold._RUNTIMES` now includes `("ext.swift", "ext.swift")` for Swift (`src/taut/gen/scaffold.py:32-39`), and `emit()` vendors every existing runtime resource while tolerating missing Phase 2 `ext.<lang>` files (`src/taut/gen/scaffold.py:600-604`). A Phase 2 Swift agent can now add only `src/taut/gen/runtime/ext.swift` and have `tautc gen --with-runtime` pick it up.

- **Resolved: fixture dispatch contract.** The base brief now names the shared fixture path and message names (`dev-docs/TautResExtP2-Base.md:19-24`), and the vector rows carry enough metadata for a hand-written Swift harness (`message`, `ext_message`, `op`, `tag`, `host`, `value`, `expect`). The Swift brief's "Generate the fixture" wording is acceptable because it explicitly says to read the base brief first.

- **Resolved with caveat: generic Swift `Cbor?` extension surface.** The base brief now allows an idiomatic per-language surface as long as bytes match (`dev-docs/TautResExtP2-Base.md:60-63`), so the Swift prompt's generic `extGet(_ host, tag) -> Cbor?` is implementable. The caveat is that the tests should compare `encode(got)` to the `get` vector's expected nested-map bytes and separately use `Decision.fromCbor(got)` where typed coverage is desired.

- **Unresolved: residual field spelling.** See finding 1.

- **Unresolved: Swift error semantics.** See finding 2.

- **Partially resolved: dev/test prerequisites.** See finding 3.

## Overall Assessment

Phase 1 has resolved the previous P0 blockers. The Swift Phase 2 prompt is now implementable for the core positive-path work: generate `ir/resext.taut.py` with `--forward-compat`, verify residual round-trip bytes, add `src/taut/gen/runtime/ext.swift`, and test the five extension vectors. I verified the current Swift residual path with a temporary compiled harness against all four residual vectors.

Before handing the prompt to an implementer, fix the `wireResidual` typo and decide the Swift failure contract for invalid tags and non-map host bytes. The remaining issues are prompt/test-contract risks, not missing Phase 1 infrastructure.
