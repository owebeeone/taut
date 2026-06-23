# Taut ResExt Phase 2 Go Prompt Review 55-3

## Findings

No blocking findings. I do not see any remaining prompt/state issue that prevents a Go Phase 2 agent from implementing the requested residual proof and `ext.go` work as written.

The current brief is implementable because the base prompt is explicitly part of the Go prompt (`dev-docs/TautResExtP2-Go.md:3`) and now supplies the contract details that were missing in earlier passes: the shared fixture/corpus oracle (`dev-docs/TautResExtP2-Base.md:15` through `dev-docs/TautResExtP2-Base.md:29`), top-level-map and band-check error semantics (`dev-docs/TautResExtP2-Base.md:52` through `dev-docs/TautResExtP2-Base.md:70`), generated-type exercise requirements for the extension path (`dev-docs/TautResExtP2-Base.md:74` through `dev-docs/TautResExtP2-Base.md:83`), and deterministic fuzz/harness expectations (`dev-docs/TautResExtP2-Base.md:100` through `dev-docs/TautResExtP2-Base.md:113`). The Go prompt then gives the Go-specific surface and corpus handling, including the important `value`-hex-as-nested-`Cbor` rule (`dev-docs/TautResExtP2-Go.md:15` through `dev-docs/TautResExtP2-Go.md:24`).

## Proposed Resolutions

No prompt change is required before Go implementation. Dispatch can proceed with the current Go and base briefs.

Implementation should still use these gates so the no-issue verdict stays enforceable:

1. **Residual parity gate:** generate the ResExt fixture with `--forward-compat`, run all four `corpus/residual_vectors.json` rows through generated `Host` decode/re-encode, and compare exact bytes.
2. **Extension parity gate:** add `src/taut/gen/runtime/ext.go`, decode `value` hex as nested CBOR for `Decision`, run all five `corpus/ext_vectors.json` rows, and compare exact bytes or returned nested CBOR bytes as appropriate.
3. **Negative behavior gate:** assert below-band tags error before host decode and non-map hosts error rather than becoming empty maps.
4. **Fuzz support gate:** run the fixed-seed, pytest-owned differential fuzz loop described by the base brief without adding dependencies.

## Prior Issue Status

- Resolved: prior Review55 P1 missing corpus/fixture blocker. Phase 1 is now documented as landed (`dev-docs/TautResExtPlan.md:51` through `dev-docs/TautResExtPlan.md:55`); `ir/resext.taut.py:16` through `ir/resext.taut.py:24` defines `Host`, `Decision`, and the band-tag extension; `corpus/residual_vectors.json:1` through `corpus/residual_vectors.json:22` contains the four residual rows; `corpus/ext_vectors.json:1` through `corpus/ext_vectors.json:43` contains the five extension rows; and `src/tests/test_resext_vectors.py:21` through `src/tests/test_resext_vectors.py:66` lock the committed corpora to the Python oracle.
- Resolved: prior Review55 P1 missing `ext.go` runtime slot. `_RUNTIMES["go"]` now includes both `cbor.go` and `ext.go` (`src/taut/gen/scaffold.py:32` through `src/taut/gen/scaffold.py:39`), `emit(..., runtime=True)` skips not-yet-landed extension runtime files until each Phase 2 port adds them (`src/taut/gen/scaffold.py:600` through `src/taut/gen/scaffold.py:607`), and package data already includes `*.go` runtime resources (`pyproject.toml:38` through `pyproject.toml:40`). The absence of `src/taut/gen/runtime/ext.go` is expected pre-implementation, not a blocker.
- Resolved: prior Review55 P2 API-shape ambiguity. The base brief permits idiomatic typed or generic surfaces while requiring byte parity and generated `to_cbor`/`from_cbor` exercise (`dev-docs/TautResExtP2-Base.md:74` through `dev-docs/TautResExtP2-Base.md:83`), and the Go prompt explicitly chooses generic `Cbor` helpers with `ExtMsg.ToCbor()` / `ExtMsg.FromCbor` at the boundary (`dev-docs/TautResExtP2-Go.md:15` through `dev-docs/TautResExtP2-Go.md:21`).
- Resolved: prior Review55 and Review55-2 fuzz-repeatability concern. The base brief now makes corpus parity the hard checked-in gate, defines the deterministic fixed-seed fuzz as supporting evidence, gives minimum iteration count/value domain/mismatch output, and specifies that pytest owns corpus/fuzz I/O and emits a temporary Go harness (`dev-docs/TautResExtP2-Base.md:100` through `dev-docs/TautResExtP2-Base.md:113`).
- Resolved: prior Review55 and Review55-2 non-map-host concern. The base brief now requires band check before host decode and requires non-map top-level hosts to error rather than be coerced (`dev-docs/TautResExtP2-Base.md:52` through `dev-docs/TautResExtP2-Base.md:70`). The Go runtime still has the nil-map footgun if an implementer omits the `Kind == KMap` check (`src/taut/gen/runtime/cbor.go:32` through `src/taut/gen/runtime/cbor.go:40`), but the prompt now tells the implementer not to omit it.
- Resolved: prior Review55-2 `ext_vectors.json` value-translation concern. The Go prompt now says `value` is nested Decision-CBOR hex and must be decoded to `Cbor`, not wrapped as a CBOR byte string (`dev-docs/TautResExtP2-Go.md:18` through `dev-docs/TautResExtP2-Go.md:21`).

Unresolved prior issues: none.

New issues: none found.

## Non-Findings

- The residual merge-order premise still matches Go code. `src/taut/gen/go.py:104` through `src/taut/gen/go.py:106` appends `WireResidual`, and `src/taut/gen/runtime/cbor.go:117` through `src/taut/gen/runtime/cbor.go:124` sorts all map entries by ascending key during encode. The interleaved residual corpus row is therefore the right proof target rather than an obvious prompt/code mismatch.
- The Go fixture generated from `ir/resext.taut.py` with `forward_compat=True` emits the expected `Host`, `Decision`, `WireResidual []KV`, `ToCbor`, and `DecisionFromCbor` surface, matching the Go prompt's harness assumptions.
- The deferred `kit.py` per-language harness emission remains acceptable. `dev-docs/TautResExtPlan.md:51` through `dev-docs/TautResExtPlan.md:55` explicitly says agents hand-write their harnesses, and the base prompt defines the pytest-owned temporary harness shape.
- The forward-compat flag gate includes Go. `src/taut/gen/scaffold.py:580` through `src/taut/gen/scaffold.py:586` rejects extension-bearing generated targets, including Go, unless `forward_compat=True`.

## Verification Notes

- Inspected: `dev-docs/TautResExtPlan.md`, `dev-docs/TautResExtP2-Base.md`, `dev-docs/TautResExtP2-Go.md`, both prior Go reviews, `ir/resext.taut.py`, both ResExt corpora, `src/taut/corpus/resext_build.py`, `src/tests/test_resext_vectors.py`, `src/tests/test_go.py`, `src/taut/gen/scaffold.py`, `src/taut/gen/go.py`, `src/taut/gen/runtime/cbor.go`, `src/taut/ext.py`, `src/taut/corpus/kit.py`, `src/taut/cli.py`, `run_tests.py`, and `pyproject.toml`.
- Generated the Go fixture API in memory from the current `ir/resext.taut.py`; no files were written.
- Ran `PYTHONPATH=src python -m pytest src/tests/test_resext_vectors.py src/tests/test_go.py -q`: 12 passed.
- `go version` reports `go1.26.4 darwin/arm64`.
