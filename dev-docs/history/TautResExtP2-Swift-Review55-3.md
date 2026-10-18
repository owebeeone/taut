# Taut Res+Ext Phase 2 Swift Prompt Review 55-3

## Findings

1. **[P2] Swift failure semantics are narrowed by the base brief, but the Swift brief still does not pin the exact Swift error style.**  
   This is the only prior issue that remains partially unresolved. The base brief now requires a below-band tag to be a hard error before host decode and says each port should use its language-idiomatic equivalent while stating that convention in the per-language brief (`dev-docs/TautResExtP2-Base.md:52-59`). It also specifies that a non-map host is an error, not an empty-map coercion (`dev-docs/TautResExtP2-Base.md:68-70`). The Swift brief only says "Band-check `tag >= 1 << 20`" and does not name `precondition`, `fatalError`, or `throws` (`dev-docs/TautResExtP2-Swift.md:13-17`). Current Swift runtime convention is trap-style (`fatalError` for wrong accessors, `precondition` for trailing data: `src/taut/gen/runtime/cbor.swift:18-31`, `src/taut/gen/runtime/cbor.swift:109-112`), and the corpus has only valid above-band rows (`corpus/ext_vectors.json:1-43`). A Swift implementer can still complete byte parity, but the prompt should say which trap style to use and require one below-band and one non-map assertion so incompatible failure surfaces do not both pass the corpus.

## Proposed Resolutions

1. **Pin Swift extension failure style**
   - **Resolution:** Update the Swift prompt to choose one runtime convention explicitly. Based on current Swift runtime style, use trap-style validation: `precondition` for below-band tags before host decode and `fatalError` or `preconditionFailure` for decoded hosts whose root is not a map. If the project prefers `throws`, state that instead and require all three accessors to use it consistently.
   - **Verification:** Add Swift harness assertions for below-band tag and non-map host behavior in addition to the valid corpus rows. Because trap assertions are awkward in plain Swift, the Python test can compile/run a tiny subprocess harness and assert non-zero exit for invalid cases.

2. **Keep generated-type exercise explicit**
   - **Resolution:** Retain the generic `Cbor?` extension surface, but state that set/get tests must use `Decision.toCbor()` and `Decision.fromCbor(...)` rather than hand-built `Cbor.map` values.
   - **Verification:** The Swift ResExt harness should build `Decision` values for extension `value` rows and decode returned `Cbor` values through generated `Decision` before byte comparison.

## Prior Issue Status

- **Resolved: Phase 1 corpora and fixture prerequisites.** `ir/resext.taut.py` now defines the shared `Host`, `Decision`, and `BAND_START + 1` extension fixture (`ir/resext.taut.py:16-24`). `corpus/residual_vectors.json` has the four residual rows, including interleaved and band-tag cases (`corpus/residual_vectors.json:1-22`), and `corpus/ext_vectors.json` has the five set/get/clear rows (`corpus/ext_vectors.json:1-43`). The committed corpora are lockstepped by `src/tests/test_resext_vectors.py:21-28`, and `run_tests.py` regenerates `taut.corpus.resext_build` (`run_tests.py:17-24`).

- **Resolved: `ext.swift` vendoring slot.** `_RUNTIMES` now registers `("ext.swift", "ext.swift")` for Swift (`src/taut/gen/scaffold.py:32-40`), and `emit()` vendors every registered runtime resource that exists while skipping missing Phase 2 files (`src/taut/gen/scaffold.py:600-607`). Package data already includes `*.swift` runtime resources (`pyproject.toml:38-40`). `src/taut/gen/runtime/ext.swift` is still absent, but that is the expected Phase 2 Swift deliverable, not a prompt blocker.

- **Resolved: residual field spelling.** The Swift prompt now explicitly says `wire_residual`, not `wireResidual` (`dev-docs/TautResExtP2-Swift.md:6-7`). The generator emits that field and initializer/codec plumbing (`src/taut/gen/swift.py:109-155`), and the current Swift tests assert the same spelling (`src/tests/test_swift.py:46-50`).

- **Resolved: fixture dispatch contract.** The base brief names the shared fixture path and message names (`dev-docs/TautResExtP2-Base.md:19-25`), and the vector rows carry the needed `message`, `ext_message`, `op`, `tag`, `host`, `value`, and `expect` metadata (`corpus/residual_vectors.json:1-22`, `corpus/ext_vectors.json:1-43`). The Swift brief's shorter "Generate the fixture `--forward-compat`" instruction is acceptable because it explicitly requires reading the base brief first (`dev-docs/TautResExtP2-Swift.md:3-10`).

- **Resolved: generic Swift `Cbor?` surface.** The base brief now allows an idiomatic per-language surface while requiring the harness to exercise the generated extension type's `to_cbor`/`from_cbor` path (`dev-docs/TautResExtP2-Base.md:74-83`). The Swift brief's generic `extGet(_ host, tag) -> Cbor?` is therefore implementable as long as tests call `Decision.toCbor()` for set and `Decision.fromCbor(...)` for get (`dev-docs/TautResExtP2-Swift.md:13-17`).

- **Resolved: test tooling prerequisite.** The base brief now tells agents to use whichever `python` or `python3` has pytest (`dev-docs/TautResExtP2-Base.md:114-115`). In this checkout, `python3` still lacks pytest, but `PYTHONPATH=src python -m pytest src/tests/test_resext_vectors.py src/tests/test_swift.py -q` passes, so this is no longer an implementability problem.

- **Partially unresolved: Swift error semantics.** See finding 1. This is no longer a P1/P2 corpus blocker because the base contract defines the required behavior, but the per-language brief still leaves avoidable implementation variance.

- **New issues: none found.** I did not find a new blocker, ownership conflict, missing shared prerequisite, or cross-language parity risk beyond the remaining Swift error-style wording above.

## Overall Assessment

The Swift Phase 2 prompt is now implementable as written for the core work: generate `ir/resext.taut.py` with `--forward-compat`, verify the four residual vectors, add `src/taut/gen/runtime/ext.swift`, compile a Swift harness over the five extension vectors, and run the supporting fixed-seed fuzz described by the base brief. The previous P0 blockers are gone, and the prior `wireResidual` typo is fixed.

Verification run in this environment:

- `swiftc --version` -> Apple Swift 6.3.1 available.
- `PYTHONPATH=src python -m pytest src/tests/test_resext_vectors.py src/tests/test_swift.py -q` -> `14 passed`.
- `PYTHONPATH=src python3 -m pytest ...` -> not runnable because that interpreter has no pytest; the base brief already accounts for this by allowing whichever Python has pytest.
