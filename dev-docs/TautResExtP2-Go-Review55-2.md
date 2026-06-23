# Taut ResExt Phase 2 Go Prompt Review 55-2

## Findings

1. [P2] The required differential fuzz deliverable is still not reproducible enough to review or gate.

   References: `dev-docs/TautResExtP2-Base.md:76` through `dev-docs/TautResExtP2-Base.md:84`; `dev-docs/TautResExtP2-Go.md:21` through `dev-docs/TautResExtP2-Go.md:22`; `src/tests/test_go.py:61` through `src/tests/test_go.py:76`; `src/taut/corpus/kit.py:89` through `src/taut/corpus/kit.py:93`.

   Phase 1 fixed the corpus prerequisite: `corpus/residual_vectors.json`, `corpus/ext_vectors.json`, and `ir/resext.taut.py` now give the Go agent a concrete byte oracle. The remaining verification instruction still requires "a differential fuzz" but does not define the seed, iteration count, value domain, random schema/message generation rules, injected unknown-tag strategy, band-tag selection, mismatch output shape, or whether the harness must be checked in and run by pytest. Current checked-in Go coverage still only exercises generator snippets and the float runtime harness, while `kit.py` still emits only the older Rust harness. A Go implementation can satisfy the prompt with one-off `/tmp` evidence that later reviewers and CI cannot replay. This is no longer a Phase 2 blocker for implementing `ext.go`, but it is still a testability gap in the prompt.

2. [P3] `ExtSet`/`ExtGet`/`ExtClear` still need an explicit top-level map guard to match the Python oracle on invalid host bytes.

   References: `dev-docs/TautResExtP2-Base.md:47` through `dev-docs/TautResExtP2-Base.md:58`; `dev-docs/TautResExtP2-Go.md:15` through `dev-docs/TautResExtP2-Go.md:18`; `src/taut/ext.py:24` through `src/taut/ext.py:46`; `src/taut/gen/runtime/cbor.go:32` through `src/taut/gen/runtime/cbor.go:40`; `src/taut/gen/runtime/cbor.go:58` through `src/taut/gen/runtime/cbor.go:66`; `src/taut/gen/runtime/cbor.go:242` through `src/taut/gen/runtime/cbor.go:248`.

   The contract says the accessors operate on the top-level CBOR map of host message bytes, and Python fails naturally if `cbor.loads(message_bytes)` returns a scalar/list instead of a dict. In Go, `Decode` returns a `Cbor` of any kind, and a non-map value has a nil `Map` slice. If an implementer follows the prompt literally by rebuilding `host.Map` without checking `host.Kind == KMap`, `ExtSet` can turn invalid scalar host bytes into a valid map containing only the extension tag, while `ExtGet` can report absent instead of rejecting the input. The committed vectors cover only valid host maps, so this is not a corpus blocker; the prompt should still require a panic for non-map hosts or explicitly declare invalid host bytes out of scope.

3. [P3] The Go harness translation for `ext_vectors.json` should state that `value` hex must be decoded to `Cbor`, not wrapped as bytes.

   References: `dev-docs/TautResExtP2-Base.md:23` through `dev-docs/TautResExtP2-Base.md:27`; `dev-docs/TautResExtP2-Base.md:50` through `dev-docs/TautResExtP2-Base.md:64`; `dev-docs/TautResExtP2-Go.md:15` through `dev-docs/TautResExtP2-Go.md:19`; `src/taut/corpus/resext_build.py:62` through `src/taut/corpus/resext_build.py:78`; `corpus/ext_vectors.json`.

   The extension corpus stores `value` as encoded `Decision` CBOR hex, while the proposed Go API takes `value Cbor`. The correct set-path harness is therefore `ExtSet(host, tag, Decode(unhex(value)))`, or equivalently a typed `DecisionFromCbor(Decode(...)).ToCbor()` round-trip before the call. Passing `CBytes(unhex(value))` would accidentally test the known "pre-serialized bytes" parity break. The base brief says the nested value is not pre-serialized, so this is not conceptually missing, but one Go-specific sentence would prevent a false negative or an implementation that bakes byte-string behavior into `ExtSet`.

## Prior Blocker Status

- Resolved: prior P1 missing corpus/fixture blocker. `ir/resext.taut.py` now defines `Host`, `Decision`, and the band-tag extension; `corpus/residual_vectors.json` has 4 rows; `corpus/ext_vectors.json` has 5 rows; `src/taut/corpus/resext_build.py` regenerates both; and `src/tests/test_resext_vectors.py` has lockstep tests for the committed artifacts.
- Resolved: prior P1 missing runtime scaffold slot. `_RUNTIMES["go"]` now includes `("ext.go", "ext.go")`, and `emit(..., runtime=True)` skips missing runtime resources until Phase 2 lands the file. `pyproject.toml` already packages `*.go` runtime resources.
- Resolved: prior API-shape ambiguity is mostly closed. The base brief now explicitly allows an idiomatic typed or generic surface as long as bytes match `ext_vectors.json`, and the Go prompt chooses generic `Cbor` helpers with typed `ToCbor`/`FromCbor` at the caller boundary.
- Still unresolved: prior fuzz-repeatability concern, narrowed to the required differential fuzz step rather than the fixed corpus rows.
- Still unresolved: prior non-map-host behavior concern, because the Go prompt still omits the `Kind == KMap` guard.

No prior P1 blockers remain. The Go Phase 2 prompt is now implementable as written for the core corpus-backed residual verification and `ext.go` implementation.

## Non-Findings

- The Go residual merge-order premise still matches the code. `src/taut/gen/go.py` appends `WireResidual`, and `src/taut/gen/runtime/cbor.go` sorts every map by ascending key in `Encode`, so the interleaved residual row should re-encode canonically if the generated fixture is used with `--forward-compat`.
- The forward-compat flag gate includes Go. `src/taut/gen/scaffold.py` rejects extension-bearing IR for generated targets, including Go, unless `forward_compat=True`.
- The deferred `kit.py` per-language harness emission is no longer a blocker by itself. `dev-docs/TautResExtPlan.md` now says that part of Phase 1 was deferred as optional and that agents hand-write their corpus harnesses.

## Verification Notes

- Inspected: `dev-docs/TautResExtPlan.md`, `dev-docs/TautResExtP2-Base.md`, `dev-docs/TautResExtP2-Go.md`, `dev-docs/TautResExtP2-Go-Review55.md`, `ir/resext.taut.py`, `corpus/residual_vectors.json`, `corpus/ext_vectors.json`, `src/taut/corpus/resext_build.py`, `src/tests/test_resext_vectors.py`, `src/tests/test_go.py`, `src/taut/gen/scaffold.py`, `src/taut/gen/go.py`, `src/taut/gen/runtime/cbor.go`, `src/taut/ext.py`, `src/taut/corpus/kit.py`, `run_tests.py`, and `pyproject.toml`.
- Generated the Go fixture API in memory and confirmed it emits `Host`, `Decision`, `WireResidual []KV`, `ToCbor`, and `DecisionFromCbor` using the current `ir/resext.taut.py`.
- `go version` reports `go1.26.4 darwin/arm64`.
- Did not run the narrow pytest checks because this Python environment reports `No module named pytest`.
