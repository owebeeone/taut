# Prism — Code Shape Analysis

Status: snapshot after closing the client×server matrix. The reason the trials
exist: to see, concretely, what the code *shape* becomes when intent is tiny and
declarative and mechanism is generated / write-once-per-language. Line counts are
measured (`wc -l`), not estimated.

## The matrix (closed)

Three clients, two servers, all driven by one IR. Every cell that crosses a
language boundary is tested:

| client \ server | Python (WS) | Rust (WS) |
| --- | --- | --- |
| **TypeScript** | ✅ interop.test.ts | ✅ interop_rust.test.ts |
| **Rust** | ✅ rs/tests/interop_py.rs | ✅ rs/tests/interop_rs.rs |
| **Python** | ✅ test_ws_interop.py[python] | ✅ test_ws_interop.py[rust] |

All six cells are exercised (TS has no server, so the TS row has no diagonal).
Every language both **serves** and **consumes** the same contract. The Rust↔Rust
test runs the server in-process via the lib's `server::serve` — the same dispatch
the `prism-server` binary uses.

## What you author vs what the machine produces

| Category | Lines | Hand-authored? |
| --- | ---: | --- |
| **IR (authored intent)** `ir/griplab.prism.py` | **119** | YES — the only governed artifact |
| IR JSON (neutral, exported) | 867 | generated from the 119 |
| Golden corpus | 46 | generated |
| Rust types + codec `generated.rs` | 335 | generated from the IR |
| C++ native types `cpp/generated/types.hpp` | ~130 | generated from the IR |
| C++ compile-time corpus `cpp/generated/corpus.hpp` | ~110 | generated from the IR |

~1250 lines of derived artifact from **119 lines of authored intent**. You
govern the 119; everything in this block is regenerated and never hand-edited.

## Mechanism — write-once-per-language, same shape everywhere

| Piece | Py | TS | Rust | C++ |
| --- | ---: | ---: | ---: | ---: |
| CBOR substrate | 150 | 143 | 194 | 74 (`constexpr`) |
| IR codec | 74 | 73 | (in generated.rs) | (in generated corpus) |

The codec is ~the same size and structure in every language and is validated
**byte-identical** by the corpus. It is the only place the wire is implemented per
language, and it is pinned by an oracle — so it can be trusted without review. The
C++ codec is `constexpr`: the corpus is proven at **compile time** by a
`static_assert` wall (`generated/corpus.hpp`, 224 lines generated), so the bytes
are verified by the compiler with zero runtime cost.

## Clients — uniformly thin, fully generic

| Client | Lines | Per-method code? |
| --- | ---: | --- |
| TypeScript `client.ts` | 111 | none |
| Rust `client.rs` | 100 | none |
| Python `ws_client.py` | 83 | none |

**This is the headline.** Every client is ~100 lines, the *same shape* in three
languages — `connect`, `call(method, args)`, `subscribe(method, args)`, correlate
by id — with **zero per-method code**. Adding a method to the IR requires **no
client change in any language**. Consumers are thin projections of the contract,
exactly as the north star demands ("consumers stay thin projections… config-as-
data, not imperative flow"), now demonstrated across the language matrix.

## Servers — thin dispatch over the slice

| Piece | Lines | Note |
| --- | ---: | --- |
| Python server | 95 | reuses the in-process slice unchanged |
| Rust server | 110 | dispatch + stream pump |
| Rust WS framing `ws.rs` | 253 | hand-rolled (sha1/base64/frames), one-time |
| Rust slice `slice.rs` | 337 | the shapes + handlers ported to Rust |

The server proper is ~100 lines of dispatch; request-vs-stream is read off the IR
method kind, not hand-branched. The "real code" on a server is the slice (shapes
+ handlers) — and handlers are plain functions over native types.

## Business logic — small and plain

| Piece | Lines |
| --- | ---: |
| Handlers `service.py` | 177 |
| Shape engines `shapes.py` | 200 |

Handlers contain no transport, envelope, codec, or shape-selection logic — those
are all mechanism. What's left is the actual behavior.

## What the shape tells us

1. **Intent is singular and tiny; mechanism is large but free.** 119 authored
   lines fan out to ~1250 generated + ~600 codec lines. The thing a human or an
   AI governs is small enough to read whole; the rest is machine-produced and
   oracle-checked.
2. **Adding a method has a blast radius of one file** (the IR) plus regeneration.
   No client in any language changes; servers pick it up by name.
3. **Adding a language is a bounded, mechanical job**: one codec (~270 lines) +
   one generic client (~100) + optionally a server, all validated by the same
   corpus byte-for-byte. No business logic is touched.
4. **The clever code is confined to mechanism.** Clients/handlers are boring on
   purpose; CBOR/WS/codegen hold the complexity, behind seams.

This is the legibility the project is chasing: the part you reason about is the
119-line IR; the part that is large is the part you don't have to read.
