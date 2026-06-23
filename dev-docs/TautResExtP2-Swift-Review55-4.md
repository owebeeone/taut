# Taut Res+Ext Phase 2 Swift Prompt Review 55-4

## Findings

No actionable issues remain. The designer-edited Swift prompt has folded in the Review55-3 proposed resolutions and is implementation-ready for Phase 2 dispatch.

Residual risk / test gaps are implementation risks rather than prompt blockers:

- The Swift agent still has to write the actual corpus harness, invalid-case subprocess harnesses, and fixed-seed fuzz. The prompt now names these deliverables explicitly.
- The existing Swift residual path is only verify-first until the Phase 2 harness runs the four residual corpus rows through generated `Host` code. That is the intended Phase 2 gate, not a remaining docs gap.

## Proposed Resolutions

None. Keep the current Swift prompt wording.

## Prior Resolution Check

- **Resolved: Swift failure style is now explicit.** Review55-3 asked the Swift prompt to pin the language failure surface. The current prompt now says to use the existing trap-style convention: `precondition(tag >= 1 << 20)` before host decode and `fatalError` or `preconditionFailure` for a decoded non-map host (`dev-docs/TautResExtP2-Swift.md:22-24`). It also warns not to introduce `throws` unless all three accessors and tests use that style consistently (`dev-docs/TautResExtP2-Swift.md:24-25`). This matches the current Swift runtime's trap-style accessors and decode checks (`src/taut/gen/runtime/cbor.swift:18-31`, `src/taut/gen/runtime/cbor.swift:109-112`).

- **Resolved: invalid-case testing is now required.** Review55-3 asked for below-band and non-map assertions because the corpus only covers valid above-band rows. The Swift prompt now requires both invalid cases and allows Python to compile/run tiny Swift subprocess harnesses and assert non-zero exit for trap assertions (`dev-docs/TautResExtP2-Swift.md:28-32`). This lines up with the base brief's band-check-before-host-decode and non-map-host error contract (`dev-docs/TautResExtP2-Base.md:52-70`).

- **Resolved: generated extension type path is now explicit.** The Swift prompt states that `value` is the caller's `Decision.toCbor()` and that `extGet` returns nested `Cbor` for `Decision.fromCbor` (`dev-docs/TautResExtP2-Swift.md:25-26`). The test/gate section also requires all five extension rows to go through generated `Decision.toCbor()` / `Decision.fromCbor` (`dev-docs/TautResExtP2-Swift.md:28-30`). This satisfies the base brief's requirement that the harness prove typed extension parity, not just generic map surgery (`dev-docs/TautResExtP2-Base.md:74-83`).

- **Still resolved: residual field spelling and ownership.** The prompt keeps the `wire_residual` spelling and warns that `cbor.swift` / `swift.py` are verify-first only (`dev-docs/TautResExtP2-Swift.md:6-9`). The generator emits `wire_residual` and re-emits it through `toCbor()` when forward compatibility is enabled (`src/taut/gen/swift.py:109-155`), and existing Swift tests cover the spelling and off-by-default behavior (`src/tests/test_swift.py:46-50`).

- **Still resolved: shared prerequisites are present.** The base brief names `ir/resext.taut.py`, `residual_vectors.json`, `ext_vectors.json`, and the `ext.<lang>` vendoring slot (`dev-docs/TautResExtP2-Base.md:15-29`). The fixture defines `Host`, `Decision`, and the band-tag extension (`ir/resext.taut.py:16-24`). The residual corpus has four rows including interleaved and band cases (`corpus/residual_vectors.json:1-22`), and the extension corpus has five set/get/clear rows (`corpus/ext_vectors.json:1-43`). Scaffold registers Swift `ext.swift` and skips missing runtime files until Phase 2 lands them (`src/taut/gen/scaffold.py:32-40`, `src/taut/gen/scaffold.py:600-607`).

## Dispatch Verdict

**Dispatchable.** The Swift Phase 2 prompt is now clear enough for an implementation agent to proceed without further prompt edits. It identifies owned files, keeps shared files out of scope, preserves the verify-first posture for residual support, pins Swift's invalid-case failure style, and requires both valid corpus parity and invalid-case tests.

## Verification Notes

Reviewed:

- `dev-docs/TautResExtPlan.md`
- `dev-docs/TautResExtP2-Base.md`
- `dev-docs/TautResExtP2-Swift.md`
- `dev-docs/TautResExtP2-Swift-Review55-3.md`
- `ir/resext.taut.py`
- `corpus/residual_vectors.json`
- `corpus/ext_vectors.json`
- `src/taut/gen/runtime/cbor.swift`
- `src/taut/gen/swift.py`
- `src/taut/gen/scaffold.py`
- `src/tests/test_resext_vectors.py`
- `src/tests/test_swift.py`

Verification run:

- `swiftc --version` -> `swift-driver version: 1.148.6 Apple Swift version 6.3.1 (swiftlang-6.3.1.1.2 clang-2100.0.123.102)`, target `arm64-apple-macosx26.0`.
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m pytest -q -p no:cacheprovider src/tests/test_resext_vectors.py src/tests/test_swift.py` -> `14 passed`.

No runtime code, prompt docs, corpora, or tests were edited as part of this review; only this review file was created.
