# Taut ResExt Phase 2 Go Prompt Review 55-4

## Findings

No actionable findings. The designer edits have preserved the Review55-3 ready-to-dispatch state and made the Go brief more implementation-ready by narrowing default ownership to `ext.go` and `test_go.py` while explicitly allowing `cbor.go` / `go.py` edits only if the residual corpus proves a real divergence.

The prompt now carries the concrete implementation traps that matter for Go:

- `dev-docs/TautResExtP2-Go.md:6` through `dev-docs/TautResExtP2-Go.md:13` scopes the Go agent to the new extension runtime and tests, and protects the existing CBOR/FLOAT path unless a ResExt vector fails.
- `dev-docs/TautResExtP2-Go.md:15` through `dev-docs/TautResExtP2-Go.md:18` requires residual decode -> re-encode parity over the interleaved and band-tag rows.
- `dev-docs/TautResExtP2-Go.md:20` through `dev-docs/TautResExtP2-Go.md:27` specifies the Go extension surface, band-check-before-decode behavior, non-map rejection, and the nested `Decision` CBOR value rule.
- `dev-docs/TautResExtP2-Go.md:29` through `dev-docs/TautResExtP2-Go.md:37` requires all corpus rows, generated `Decision.ToCbor()` / `DecisionFromCbor`, invalid-case assertions, fixed-seed differential fuzz, and the evidence command.

This lines up with the base contract at `dev-docs/TautResExtP2-Base.md:52` through `dev-docs/TautResExtP2-Base.md:83` and `dev-docs/TautResExtP2-Base.md:100` through `dev-docs/TautResExtP2-Base.md:113`.

## Proposed Resolutions

No prompt/doc changes are required before dispatch.

For the implementation agent, keep the following as execution gates rather than prompt changes:

1. Residual parity: generate `ir/resext.taut.py` with `--forward-compat` and byte-match all four `corpus/residual_vectors.json` rows.
2. Extension parity: implement `src/taut/gen/runtime/ext.go` and byte-match all five `corpus/ext_vectors.json` rows, with `value` decoded as nested `Decision` CBOR.
3. Typed path proof: drive set/get through generated `Decision.ToCbor()` and `DecisionFromCbor`, not only generic map surgery.
4. Negative behavior: below-band tag must panic before host decode; non-map hosts must panic rather than becoming empty maps.
5. Fuzz support: run the base-brief fixed-seed, pytest-owned Go harness with at least 1000 iterations and report seed plus mismatch count.

## Prior Resolution Check

- Review55-3 residual parity gate: folded in. The Go prompt requires generated fixture residual decode -> re-encode over all four rows, including interleaved and band-tag unknowns (`dev-docs/TautResExtP2-Go.md:15` through `dev-docs/TautResExtP2-Go.md:18`; corpus rows at `corpus/residual_vectors.json:1` through `corpus/residual_vectors.json:22`).
- Review55-3 extension parity gate: folded in. The Go prompt names `ext.go`, the generic `Cbor` helpers, all five ext corpus rows, and the nested `Decision` CBOR handling (`dev-docs/TautResExtP2-Go.md:20` through `dev-docs/TautResExtP2-Go.md:31`; corpus rows at `corpus/ext_vectors.json:1` through `corpus/ext_vectors.json:43`).
- Review55-3 negative behavior gate: folded in. The Go prompt explicitly requires band check before host decode and non-map host rejection (`dev-docs/TautResExtP2-Go.md:23` through `dev-docs/TautResExtP2-Go.md:24`), matching the base brief (`dev-docs/TautResExtP2-Base.md:52` through `dev-docs/TautResExtP2-Base.md:70`).
- Review55-3 fuzz support gate: folded in. The Go prompt requires the fixed-seed differential fuzz described by the base brief and asks the implementer to report seed and mismatch count (`dev-docs/TautResExtP2-Go.md:31` through `dev-docs/TautResExtP2-Go.md:36`).
- Prior runtime-slot concern remains resolved. `_RUNTIMES["go"]` includes `ext.go` (`src/taut/gen/scaffold.py:32` through `src/taut/gen/scaffold.py:39`), and `emit()` skips not-yet-present extension runtimes until the Phase 2 file lands (`src/taut/gen/scaffold.py:600` through `src/taut/gen/scaffold.py:607`).
- Prior fixture/API ambiguity remains resolved. `ir/resext.taut.py:16` through `ir/resext.taut.py:24` defines `Host`, `Decision`, and the band-tag extension. In-memory Go generation from that schema with `forward_compat=True` exposes `Host`, `Decision`, `WireResidual []KV`, `ToCbor`, and `DecisionFromCbor`, matching the Go prompt.

Unresolved prior issues: none.

New issues: none found.

## Dispatch Verdict

Dispatch Go Phase 2. The current Go and base briefs are implementation-ready.

Residual risk is limited to implementation quality, not prompt ambiguity: the Go agent still needs to prove the actual corpus/fuzz harness after `ext.go` exists, and the checked-in Go tests do not yet cover ResExt because that is the Phase 2 implementation work.

## Verification Notes

- Read and reviewed: `dev-docs/TautResExtPlan.md`, `dev-docs/TautResExtP2-Base.md`, `dev-docs/TautResExtP2-Go.md`, `dev-docs/TautResExtP2-Go-Review55-3.md`, `ir/resext.taut.py`, `corpus/residual_vectors.json`, `corpus/ext_vectors.json`, `src/tests/test_resext_vectors.py`, `src/tests/test_go.py`, `src/taut/gen/scaffold.py`, `src/taut/gen/go.py`, `src/taut/gen/runtime/cbor.go`, and `src/taut/ext.py`.
- Confirmed `src/taut/gen/runtime/ext.go` is still absent, which is expected before Go Phase 2 implementation.
- Confirmed in memory that Go generation for `ir/resext.taut.py` with `forward_compat=True` emits the expected ResExt fixture API; no files were written by that check.
- Ran `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m pytest -q -p no:cacheprovider src/tests/test_resext_vectors.py src/tests/test_go.py`: 12 passed.
- `go version`: `go1.26.4 darwin/arm64`.
- Existing workspace state noted but not changed: `dev-docs/TautResExtP2-Go.md` is modified, and previous review files are untracked. This review edited only `dev-docs/TautResExtP2-Go-Review55-4.md`.
