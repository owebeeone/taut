# taut — Overview

taut lets you define **data shapes**, **service endpoints (web APIs)**, and
**data-delivery shapes** once, in one tiny declarative source, and derive native
types, codecs, service stubs, and shape-aware sync for **Python, TypeScript,
Rust, and C++** — verified against a golden conformance corpus.

> One thesis governs everything: **the only artifact you hand-author is a small
> declarative IR; all mechanism (codecs, transport, sync, stubs) is generated from
> it and checked byte-for-byte against the corpus.** No protoc, no heavy IDL.

## What you write vs what you get

```
  one .taut.py  ──►  neutral IR (JSON)  ──►  native types · codec · service stubs
   (you author)        (generated)              shape clients · docs · corpus
                                                  for Py / TS / Rust / C++
```

You govern the IR (small enough to read whole). Everything downstream is
regenerated and never hand-edited; a regeneration gate fails CI if generated
files drift, and a breaking-change gate rejects incompatible IR edits.

## A "web API" in taut

A web API is a **`service`** — a set of **methods**. Each method is either:

- **unary** — request → response (`create`, `set_state`, a query…), or
- **server_stream** — a subscription whose behavior is a **delivery shape**.

You don't hand-roll request/response plumbing or streaming semantics. You pick a
delivery shape per streaming endpoint and taut gives you the idiomatic API +
sync for it. The closed set:

| Shape | Use it for | Reader sees |
| --- | --- | --- |
| **atom** | whole-state, latest-wins (presence, status, a list) | replacements |
| **log** | append-only history (chat, an event feed) | replay then tail |
| **stream** | live, ephemeral (terminal output, ticks) | live events, no replay |
| **swmr** | single-writer snapshot + deltas (a file, a doc view) | snapshot(+offset) then deltas |
| **snapshot_delta** | snapshot carrying a resume offset, then deltas | same handoff, generalized |
| **crdt** | multi-writer convergent (collaborative fields) | ops; merge via a bound engine |

The shape is the contract; the transport binding (WebSocket+JSON today, others
later) and the sync machinery are derived, not written per endpoint. Building a
server is then just writing handlers (plain functions) and registering them
against the contract — see [Server.md](Server.md).

## What taut decouples (and never fuses)

Wire format · in-memory representation · access/mutation API · service contract ·
transport binding · delivery shape. Each is a separate concern. A field's native
type can be *richer* than the wire (untagged transient caches are fine); the wire
is a derived projection of the tagged subset.

## The pieces

| Piece | Where |
| --- | --- |
| IR authoring DSL | `taut.ir.dsl` (Python-as-DSL) |
| Validator + breaking-change gate | `taut.ir.validate`, `taut.ir.compat` |
| Wire codec (deterministic CBOR) | `taut.wire.codec` / `taut.wire.cbor` |
| Per-language generators | `taut.gen.rust`, `taut.gen.cpp` |
| Golden corpus | `taut/corpus/` |
| Reference slices + clients/servers | the `trial/` repo (`py/ ts/ rs/ cpp/`) |
| CRDT reference engine + slot | `taut.crdt` |

## Status

This is a working spike, not a packaged product. The library API (author →
validate → export → encode/decode) is general; the per-language generators and
the WebSocket client/server bindings currently target the `trial/` slices as
worked examples. See [GettingStarted.md](GettingStarted.md) to define your own
API, [Server.md](Server.md) to serve it, and [Reference.md](Reference.md) for the
complete authoring surface.
