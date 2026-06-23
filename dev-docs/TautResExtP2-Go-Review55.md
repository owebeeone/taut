# Taut ResExt Phase 2 Go Prompt Review 55

## Findings

1. [P1] The Go prompt is not executable in this checkout because its required Phase 1 corpora and fixture surface are absent.

   References: `dev-docs/TautResExtP2-Base.md:15` through `dev-docs/TautResExtP2-Base.md:22`; `dev-docs/TautResExtP2-Go.md:10` through `dev-docs/TautResExtP2-Go.md:22`; `dev-docs/TautResExtPlan.md:55` through `dev-docs/TautResExtPlan.md:62`.

   The base brief defines `corpus/residual_vectors.json` and `corpus/ext_vectors.json` as the parse-free oracle, and the Go prompt requires both for residual proof, extension parity, and fuzz verification. Neither file exists in the repo. The planned Phase 1 fixture schema/IR and per-language residual/extension harness support are also not present; `src/taut/corpus/kit.py:89` through `src/taut/corpus/kit.py:93` still exposes only the older generic Rust corpus harness. A Phase 2 Go implementer would have to invent vector formats, fixture schemas, or verification rules, which defeats the byte-exact shared oracle the prompt depends on.

2. [P1] The prompt assigns `ext.go` to the Go agent, but the repo still lacks the scaffold/runtime wiring needed to emit that file with generated Go packages.

   References: `dev-docs/TautResExtPlan.md:59` through `dev-docs/TautResExtPlan.md:62`; `dev-docs/TautResExtP2-Base.md:63` through `dev-docs/TautResExtP2-Base.md:68`; `dev-docs/TautResExtP2-Go.md:6` through `dev-docs/TautResExtP2-Go.md:8`; `src/taut/gen/scaffold.py:30` through `src/taut/gen/scaffold.py:38`; `src/taut/gen/scaffold.py:594` through `src/taut/gen/scaffold.py:599`.

   Phase 1 was supposed to add an `ext.<lang>` runtime slot to scaffold so Phase 2 agents only drop in their language module. That has not happened: `_RUNTIMES["go"]` names only `cbor.go`, and `emit(..., runtime=True)` copies exactly one runtime resource per language. The base brief also tells Phase 2 agents not to edit `gen/scaffold.py`. As written, the Go agent can add `src/taut/gen/runtime/ext.go` and pass a hand-built `/tmp` module, but `tautc gen --lang go --with-runtime` will still emit no extension accessor, leaving the actual generated Go surface incomplete.

3. [P2] The Go extension API contract is under-specified relative to the Python oracle and the "mirror `ext.py`" requirement.

   References: `dev-docs/TautResExtP2-Base.md:42` through `dev-docs/TautResExtP2-Base.md:59`; `dev-docs/TautResExtP2-Go.md:15` through `dev-docs/TautResExtP2-Go.md:19`; `src/taut/ext.py:24` through `src/taut/ext.py:46`.

   The Python API is schema/message aware: `ext_set(schema, bytes, ext_message, tag, value)` returns wire bytes and `ext_get(...)` returns a decoded extension message or `None`. The Go prompt specifies only generic `Cbor` helpers: `ExtSet(host []byte, tag int64, value Cbor) []byte` and `ExtGet(host []byte, tag int64) (Cbor, bool)`, with the caller manually invoking `ExtMsg.ToCbor()` or `ExtMsgFromCbor(...)`. That may be the intended idiomatic surface, but the prompt should say explicitly that Go is allowed to expose only the generic nested-CBOR helpers, or it should require typed generated wrappers. Without that clarification, agents can satisfy different interpretations and create cross-language API inconsistency even if bytes match.

4. [P2] The verification instructions require a differential fuzz gate, but do not define enough for a repeatable checked-in Go test.

   References: `dev-docs/TautResExtP2-Base.md:71` through `dev-docs/TautResExtP2-Base.md:79`; `dev-docs/TautResExtP2-Go.md:21` through `dev-docs/TautResExtP2-Go.md:22`; `src/tests/test_go.py:61` through `src/tests/test_go.py:76`; `src/taut/corpus/kit.py:17` through `src/taut/corpus/kit.py:27`.

   The prompt asks for "a tiny module in /tmp over both corpora + a differential fuzz" and to show mismatch counts, but it does not define corpus JSON shape, fuzz seed, iteration count, generated fixture schema, host/ext message names, or whether the fuzz harness must be committed and run by pytest. Current Go tests only compile the vendored runtime float harness; they do not compile generated Go API types or drive language-neutral residual/ext vectors. This leaves too much room for an ad hoc local proof that cannot be reproduced by CI or later reviewers.

5. [P3] Naive `ext.go` implementations can silently accept non-map host bytes unless the prompt requires a top-level map check.

   References: `dev-docs/TautResExtP2-Base.md:43` through `dev-docs/TautResExtP2-Base.md:52`; `dev-docs/TautResExtP2-Go.md:15` through `dev-docs/TautResExtP2-Go.md:18`; `src/taut/gen/runtime/cbor.go:32` through `src/taut/gen/runtime/cbor.go:40`; `src/taut/gen/runtime/cbor.go:242` through `src/taut/gen/runtime/cbor.go:248`; `src/taut/ext.py:27` through `src/taut/ext.py:29`.

   The contract says extension accessors operate on the top-level CBOR map of host message bytes. In Go, `Decode` returns a `Cbor` of any kind, and a non-map value has a nil `Map` slice. If an implementer follows the prompt literally by rebuilding `host.Map` without first checking `host.Kind == KMap`, `ExtSet` can turn invalid non-map host bytes into a valid map containing only the extension tag. Python's oracle operates on a decoded dict and would not silently coerce a scalar host this way. Host messages should normally be maps, so this is not a core parity blocker, but the prompt should require a panic/error for non-map top-level input or state that vectors never cover invalid hosts.

## Non-Findings

- The residual merge-order premise in the Go prompt matches the current code. `src/taut/gen/go.py:104` through `src/taut/gen/go.py:106` appends `WireResidual`, and `src/taut/gen/runtime/cbor.go:117` through `src/taut/gen/runtime/cbor.go:124` sorts all map entries by key during encode, so an interleaved unknown tag should be emitted in canonical order once real residual vectors exist.
- The forward-compat flag gate is already broad enough for Go in scaffold. `src/taut/gen/scaffold.py:574` through `src/taut/gen/scaffold.py:580` includes Go in the generated-target set that errors on extension IR without `forward_compat`.
- `go` is available in this environment (`go version go1.26.4 darwin/arm64`), so tool availability is not a blocker for the planned Go compile/run checks.

## Recommended Prompt Changes

- Make Phase 2 conditional on Phase 1 artifacts being present, or include exact checked-in locations and JSON schemas for `corpus/residual_vectors.json`, `corpus/ext_vectors.json`, and the fixture IR.
- Move scaffold/runtime-copy wiring for `ext.go` into Phase 1 before fan-out, or explicitly add `src/taut/gen/scaffold.py` and packaging updates to the Go-owned files.
- State whether Go's public extension surface is intentionally generic `Cbor` helpers only, or require typed wrappers generated beside `ToCbor`/`FromCbor`.
- Define the Go verification harness as either checked-in pytest-driven coverage or explicitly disposable local evidence, with deterministic fuzz parameters and expected command lines.
- Require `ExtSet`/`ExtGet`/`ExtClear` to reject non-map top-level host bytes unless invalid hosts are out of scope for the oracle.

## Scope Inspected

- `dev-docs/TautResExtPlan.md`
- `dev-docs/TautResExtP2-Base.md`
- `dev-docs/TautResExtP2-Go.md`
- `dev-docs/history/TautFloatP2-Go.md`
- `src/taut/gen/runtime/cbor.go`
- `src/taut/gen/go.py`
- `src/taut/gen/scaffold.py`
- `src/taut/corpus/kit.py`
- `src/taut/ext.py`
- `src/taut/wire/codec.py`
- `src/tests/test_go.py`
- `src/tests/test_forward_compat.py`
- `corpus/`

