# Phase 0 — Discovery notes

Status: captured from the working `trial/py/` slice (no codegen).
Purpose: record the shapes that actually emerged, ready to extract into the IR in
Phase 1. Build-prompt §8.0 / PrismPlan §9 DoD item 5.

The slice runs and is green: `cd trial/py && python3 -m pytest tests/` → 14 passed.

## What got built

A hand-wired GripLab terminal slice over an in-process JSON `ServiceEnvelope`:

| Endpoint | Shape | Engine |
| --- | --- | --- |
| `presence.subscribe` | **Atom** | `shapes.Atom` — current value, then replacements |
| `terminal.output.subscribe` | **Stream** | `shapes.Stream` — live, no replay |
| `file.subscribe` | **SWMR** | `shapes.Swmr` — snapshot(+resume_seq) then deltas |
| `cmd.run` | unary **fan-out DAG** | `scheduler.run_dag` — waves + per-task error isolation |

## Findings that should shape the IR (P1)

1. **The wire is a projection of the *tagged* subset.** One generic dataclass↔JSON
   codec (`wire.py`) replaces GripLab's per-type `parse*` wall. Fields carrying
   `metadata={"transient": True}` (e.g. `FileSnapshot.preview`,
   `CmdSession.started_monotonic`) exist in memory but never on the wire. **IR
   implication:** a message field needs a `transient` flag and a `tag`; the codec
   is fully type-directed (enum→value, bytes→base64, nested dataclass→map). This
   generic codec *is* the spec the P1 Python generator specializes.

2. **Subscription registration must be eager and separate from iteration.**
   First cut modelled each subscription as an async generator; a `Stream` event
   emitted before the consumer's first pull was silently lost and the pull then
   blocked forever. Fix: `open()` registers the listener synchronously and
   returns a `Subscription` handle; iteration is a separate concern. **IR/shape
   implication:** every streaming shape's contract has two steps — *establish*
   (server-side registration / snapshot capture) then *consume*. This is also the
   "stable source handle" Glade requires (`GladeSurfacePrecis.md:79`). The
   streaming-kind derivation in P2 must encode the establish step, not just the
   event stream.

3. **The SWMR snapshot must carry the resume offset, and readers must check
   contiguity.** `FileSnapshot.resume_seq` is the offset deltas resume after;
   `open()` captures snapshot + registers atomically (single-writer, no await
   between) so the first queued delta's `base_seq == snapshot.resume_seq`. The
   reader (`FileView`) asserts `delta.base_seq == applied_seq` on every delta —
   no gap, no double-apply. **IR implication:** the SWMR/Snapshot+Delta shape
   needs the resume-offset field as a first-class part of the snapshot message,
   and the conformance corpus (P1) must include a canonical
   snapshot→delta→delta sequence to pin the handoff across languages.

4. **Fan-out + error policy is declarative, isolated per task.** `cmd.run` builds
   a task DAG: one independent task per repo (single wave) + a gather task
   depending on all. A repo task that raises becomes a failed `TaskOutcome` and
   does **not** abort siblings; the gather turns it into a per-target `RepoRun`
   with an error. **P4 implication:** the portable orchestration spec needs at
   minimum: task key, deps, and a per-task error policy (here: isolate-and-report).
   Retry/timeout/fallback are the next knobs to add — surfaced in PrismPlan §10.3.

5. **Envelope shape (lifted from GripLab `protocol.ts:16`).** `Envelope{message_id,
   kind, method?, stream_id?, seq, event?, payload, error?}` with
   `kind ∈ {request, response, stream-event, error}`. Phase 0 added explicit
   `seq` + `event` to the envelope (GripLab nests these in a `ServiceStreamEvent`
   payload) — P1 should decide whether `seq`/`event` live on the envelope or in a
   typed stream-event payload. **Decision noted, not yet made.**

## P0.5 — modeling the full surface (the verb-cluster finding)

Modeling more of `handle_protocol_message` (full inventory in
[GripLabSurfaceCatalog.md](GripLabSurfaceCatalog.md)) changed the model in one
structural way: **the IR unit is not "method" — it is (source × shape × a cluster
of role-typed verbs).** The slice now exercises all four non-CRDT shapes and the
verb roles around each (output/input/control/teardown/handle, the GripShare
taxonomy):

- **Log shape added** (`shapes.Log`) — `chat.subscribe` replays history then tails;
  `chat.post` appends. A late subscriber loses nothing (unlike Stream). Append
  offset == message id. **IR implication:** Log needs a read-cursor on subscribe
  and immutable entries; the corpus must pin replay-then-tail ordering.
- **Handle composing multiple views** (`service.TerminalManager`) — `term.open`
  mints a session_id that keys the output **Stream** (`session.output.subscribe`)
  *and* the control plane (`term.input` echoes onto that same output, `term.resize`,
  `term.close`). This is Glade's stable-handle requirement realized. **IR
  implication:** a source declaration must be able to bind N flow-typed views to
  one handle, and the streaming-subscribe op must take the handle as an argument
  (the transport now decodes args for streams, not just unary calls).
- **Control/input verbs on a read shape** — `file.window.update` is the consumer
  writing a window preference *upstream*; it re-snapshots subscribers, and the
  delta feed resumes cleanly from the new snapshot's `resume_seq` (the same
  handoff invariant, re-proven on reset). **IR implication:** a shape's verb set
  includes upstream-input ops, not just downstream reads.
- **Pull vs push is a real axis** — `presence.get` / `sessions.query` are
  pull-once (initiation=pull); `*.subscribe` is push. The IR's initiation axis
  must carry both for the same source.

What stayed **catalog-only** and why: §"What catalog means" in the catalog doc —
peripheral SSH/iroh/perf machinery (opaque payloads, no new shape) and Atom
siblings already covered (settings, tree, workspace.status). `term.ticket` is
flagged as the transport-rebind illustration for P2.

## Native types that emerged (the first IR messages)

`PeerPresence` (+ `PresenceStatus` enum) · `ByteOp` (+ `OpKind` enum) ·
`FileSnapshot` · `FileDelta` · `ChatMessage` · `TerminalChunk` · `TerminalOpened` ·
`RepoTarget` · `RepoRun` · `CmdSession`. Two carry transient fields (the M3
native-richness proof).

## Honest scope notes (what Phase 0 did NOT do)

- **No real socket.** The JSON envelope round-trips through `json.dumps/loads` in
  `transport.py`, exercising the wire shape, but no WebSocket is opened. A socket
  binding is a later, generated transport adapter (build prompt: transport binding
  is a separate concern). PrismPlan §9 DoD item 1 said "over WebSocket+JSON" — the
  faithful Phase-0 reading is "the JSON envelope, transport-seam in-process."
- **No codegen, no IR, no validator, no CRDT, no TS/Rust/C++.** All deferred to
  P1+ by design — discover first, abstract backward.

## P1 status (data layer — DONE)

Extracted backward into [../ir/griplab.prism.py](../ir/griplab.prism.py) (2 enums,
9 messages). Wire frozen as deterministic CBOR ([../src/prism/wire/cbor.py](../src/prism/wire/cbor.py),
pinned to RFC 8949 vectors). Codec is **IR-driven at runtime**, not text-emitted
(CLAUDE.md: "probably no codegen, ever") — [../src/prism/wire/codec.py](../src/prism/wire/codec.py).
Golden corpus committed at [../corpus/griplab.golden.json](../corpus/griplab.golden.json)
(11 vectors incl. the SWMR snapshot→delta→delta handoff). **P1b done:** the live
slice's reflective JSON codec was retired — `trial/py` now rides the IR/CBOR codec
via a thin dataclass⇄dict binding ([../../trial/py/griplab_slice/wire.py](../../trial/py/griplab_slice/wire.py)),
and `ByteOp` bytes match the corpus byte-for-byte. 25 tests green (18 slice + 7
builder). Still deferred to P2+: services/shape annotations in the IR, validator,
text codegen, CRDT, Rust/C++.

## P3 data-gate (cross-language — DONE)

The IR is now a neutral serialized artifact ([../corpus/griplab.ir.json](../corpus/griplab.ir.json),
exported by [../src/prism/ir/export.py](../src/prism/ir/export.py)) and the golden
corpus is self-describing (each vector carries its message name). A TypeScript
codec ([../../trial/ts](../../trial/ts)) — its own CBOR + IR codec, driven by the
*same* IR JSON, **no schema re-declared** — reproduces all 11 golden vectors
**byte-for-byte**, with semantic + SWMR-handoff + transient-elision checks. Runs
on Node ≥22.6 type-stripping (`node --experimental-strip-types --test`), zero deps.
**The data-layer IR is validated across two languages.** 28 tests green total
(18 slice + 7 builder + 3 TS). This is the build prompt's "second language before
going wide" gate, applied at the data layer before services (P2) pile on.

Note: no *text* codegen was needed — the IR-driven runtime-codec approach holds
in TS too (codec reads the IR JSON at load). Text generation of native
interfaces stays deferred until a target actually requires ahead-of-time types
(Rust/C++).

## P2 — service contract + delivery shapes + validator (contract layer DONE)

The IR gained the service layer, modeled per the discovery finding: a method is
**(source × shape × role-typed verb)**.

- **Closed delivery-shape set** as built-in data ([../src/prism/ir/shapes.py](../src/prism/ir/shapes.py)):
  atom / log / stream / swmr / snapshot_delta / crdt, each a point in the axes
  (payload/history/initiation/writers) with `events` = its derived streaming-kind.
  `snapshot_delta` + `crdt` are registered contract surfaces, unused by GripLab
  (no multi-writer feed); CRDT is wire/contract only, no engine.
- **Service decls in the IR** ([../ir/griplab.prism.py](../ir/griplab.prism.py)):
  13 GripLab methods. Lean modeling — method I/O uses TypeRefs + named params over
  *existing* messages (no synthetic args-messages), and stream outputs are an
  event-name→type map that matches the slice's `(event_name, obj)` exactly.
- **Validator** ([../src/prism/ir/validate.py](../src/prism/ir/validate.py)):
  refs resolve, tags unique, enum values unique, and every server_stream's events
  ⊆ its shape's allowed events (e.g. an `atom` stream emitting `delta` is rejected).
  `build` validates before emitting. 9 validator tests incl. rejection cases.
- **Exported** to the neutral IR JSON ([../corpus/griplab.ir.json](../corpus/griplab.ir.json)):
  services + the shape registry, ready for cross-language bindings.
- **Intent↔mechanism bridge**: a slice test asserts the hand-wired transport
  registration matches the IR service (method set, kind↔streaming, params) — a
  drift guard ([../../trial/py/tests/test_service_contract.py](../../trial/py/tests/test_service_contract.py)).

38 tests green (19 slice + 16 builder + 3 TS).

### P2b — registration derived from the IR (DONE)

The slice's transport registration is now *derived* from the IR service, not just
consistent with it (the service-layer analog of P1b retiring the hand codec):

- A bound method is an IR `MethodDef` + handler; the transport reads kind and
  params from the IR. **Argument decoding is driven by the declared param
  TypeRefs** ([../../trial/py/griplab_slice/wire.py](../../trial/py/griplab_slice/wire.py)
  `decode_payload_ref` + a name→dataclass `NATIVE_TYPES` registry) — the
  hand-written `arg_types`/`streaming` table is gone.
- [../../trial/py/griplab_slice/composition.py](../../trial/py/griplab_slice/composition.py)
  registers in a loop over `SCHEMA.services["GripLab"].methods`. The only
  hand-written table left is name→handler (handlers are code), with a drift check.
- The consistency test now verifies actual **handler signatures match the IR
  params** (code↔contract), a stronger guard than before.

39 tests green (20 slice + 16 builder + 3 TS).

### P3b + real server — cross-language client↔server interop (DONE)

A **real Python WebSocket server** ([../../trial/py/griplab_slice/server.py](../../trial/py/griplab_slice/server.py))
serves the slice over a socket, reusing the *same* IR-driven dispatch (it picks
request-vs-stream from the IR method kind and runs `transport.request`/`.open`).
The envelope rides as JSON ([../../trial/py/griplab_slice/jsonwire.py](../../trial/py/griplab_slice/jsonwire.py));
message payloads stay CBOR.

An **IR-driven TypeScript WebSocket client** ([../../trial/ts/src/client.ts](../../trial/ts/src/client.ts))
reads the service contract from the shared `griplab.ir.json` — per method it knows
the param/output/event TypeRefs, encodes args and decodes results via the CBOR/IR
codec. No per-method code on either side beyond the generic call/subscribe + the
handlers.

[../../trial/ts/test/interop.test.ts](../../trial/ts/test/interop.test.ts) spawns
the Python server and drives it from the TS client across **all five shapes**:
cmd.run (fan-out DAG + per-target error isolation), presence (Atom), chat (Log),
file (**SWMR snapshot+delta, with the resume-offset handoff proven across the
wire**), terminal (Stream + handle, input echoes to the handle's output). All pass.

Bug found en route: the in-process transport generated a fresh response
`messageId`; over the wire the response must **echo the request id** for
correlation (in-process the client awaited the return value directly, so it never
surfaced). Fixed in the server.

44 tests green: 20 slice + 16 builder + 8 TS (3 corpus + 5 interop). **The whole
thesis now runs as a two-language system: one IR → byte-exact CBOR → a live TS
client talking to a live Python server across every implemented shape.**

Deferred (honest scope): CRDT engine; a binary-CBOR-envelope transport profile
(today JSON envelope + CBOR payload); Rust/C++ targets (P5/P6); an AST-level
declarative-only check of `.prism.py` (today the DSL helpers enforce
non-executability and the validator checks the resulting data).

## P4 — orchestration formalization (DONE)

The task-DAG scheduler is now a formalized execution spec with a declarative
per-task error policy ([../../trial/py/griplab_slice/scheduler.py](../../trial/py/griplab_slice/scheduler.py),
normative semantics in [PrismOrchestration.md](PrismOrchestration.md)):

- **Error-policy vocabulary (v1, resolves PrismPlan §10.3):** `retries`, `timeout`
  (per-attempt), `on_error` ∈ {isolate, fail, fallback}, `fallback`, `teardown`.
- **Structured cancellation:** `on_error="fail"` cancels in-flight siblings *and*
  all downstream waves; `cmd.run` uses `on_error="isolate"` so one repo's failure
  is isolated by **policy**, not hand-coded control flow.
- **Teardown** runs for every started task in reverse start order.
- 5 new scheduler tests (retry, timeout, fallback, hard-fail cancellation,
  teardown). Slice suite: 25 green.

Deferred: cross-language portable serialization of the task graph + a Rust tokio
binding to the same spec; sagas/compensation.

## Rust gate (third-language wire validation — DONE)

A hand-written deterministic CBOR codec in Rust ([../../trial/rs](../../trial/rs))
reproduces the golden corpus **byte-for-byte** — the third language (after Python
and TypeScript) to validate the frozen wire. Zero dependencies: Rust has no std
JSON parser, so the corpus is **generated as Rust data** by
[../src/prism/gen/rust.py](../src/prism/gen/rust.py) (the first place Prism's text
codegen earns its keep — ahead-of-time data for a compiled target, exactly as
planned). `cargo test --offline`: 2 green.

### P5 Rust — finished (IR-aware codec + tokio scheduler)

- **Generated native types + codec** ([../src/prism/gen/rust.py](../src/prism/gen/rust.py)
  → [../../trial/rs/src/generated.rs](../../trial/rs/src/generated.rs)): one Rust
  enum per IR enum (wire()/from_wire()), one struct per message (to_cbor/from_cbor),
  transient fields present-but-off-the-wire, a `roundtrip` dispatcher. The IR-aware
  codec reproduces the golden corpus **byte-for-byte** over native structs (not
  just the CBOR substrate). This is Prism's text codegen finally earning its place
  — a compiled target wants ahead-of-time types.
- **Tokio scheduler binding** ([../../trial/rs/src/scheduler.rs](../../trial/rs/src/scheduler.rs)):
  the Rust mirror of the Python sdax scheduler — waves, per-task error policy
  (retries / timeout / isolate|fail|fallback / teardown), structured cancellation
  via `JoinSet::abort_all`. Same orchestration spec, second runtime.
- tokio built **offline** from the cargo cache (no network). 9 Rust tests green
  (codec corpus + native-struct semantics + 6 scheduler-semantics tests).

**58 tests across three languages:** 16 builder + 25 slice + 8 TS + 9 Rust. The
wire + codec are proven in Python, TypeScript, and Rust over native types; the IR
drives a live TS↔Python system; orchestration is a formal spec with two runtime
bindings (Python sdax, Rust tokio).

### Rust server — TS client ↔ Rust server (DONE)

The GripLab slice is now also served by Rust ([../../trial/rs/src/slice.rs](../../trial/rs/src/slice.rs)
+ [../../trial/rs/src/bin/server.rs](../../trial/rs/src/bin/server.rs)): the shapes
(Atom/Log/Stream/SWMR), handlers, and the `cmd.run` fan-out (on the tokio
scheduler) ported to Rust over the generated native structs, behind a
**hand-rolled WebSocket** ([../../trial/rs/src/ws.rs](../../trial/rs/src/ws.rs):
sha1 + base64 + RFC 6455 frames, zero crates beyond tokio + serde_json). Same
protocol as the Python server (JSON envelope + CBOR payload).

[../../trial/ts/test/interop_rust.test.ts](../../trial/ts/test/interop_rust.test.ts)
runs the *same* IR-driven TS client against the Rust server across all five
shapes — TS↔Rust interop, peer to the TS↔Python test. All pass.

Two bugs found en route: the WS accept-key needed case-insensitive header
matching (Node's `WebSocket` sends a different header case than the canonical
one); and `Vec::splice` arms had incompatible types (used `drain` for delete).

**64 tests:** 16 builder + 25 slice + 13 TS (3 corpus + 5 TS↔Python + 5 TS↔Rust)
+ 10 Rust. Prism now has **two interoperable servers (Python, Rust)** and a TS
client that talks to both, all from one IR; the wire is proven in three languages;
orchestration is a formal spec with two runtime bindings.

### Client×server matrix closed

Added the two missing clients so every language both serves and consumes:
- **Rust client** ([../../trial/rs/src/client.rs](../../trial/rs/src/client.rs) +
  client-side WS framing in [ws.rs](../../trial/rs/src/ws.rs)) — tested against the
  Python server ([../../trial/rs/tests/interop_py.rs](../../trial/rs/tests/interop_py.rs)).
- **Python WS client** ([../../trial/py/griplab_slice/ws_client.py](../../trial/py/griplab_slice/ws_client.py))
  — tested against the Rust server ([../../trial/py/tests/test_ws_interop.py](../../trial/py/tests/test_ws_interop.py)).

All six client×server cells tested: TS→Py, TS→Rust, Rust→Py, **Rust→Rust**,
Py→Rust, **Py→Py**. (The Rust↔Rust test runs the server in-process via the lib's
`server::serve`; the server logic was lifted out of the binary so both share it.
The Python client test is parametrized over both servers.) **68 tests.**

The point of this was the **code shape** — see [CodeShape.md](CodeShape.md): 119
lines of authored IR fan out to ~1250 generated lines; every client is ~100 lines
of *identical, fully generic* code in three languages with zero per-method logic;
adding a method changes one file and no client; adding a language is one codec +
one generic client, corpus-verified.

Remaining: C++ (P6 — the compile-time showcase, `static_assert` corpus), OCI
distribution + breaking-change gate (P7), the CRDT engine, and a binary-CBOR
envelope profile.
