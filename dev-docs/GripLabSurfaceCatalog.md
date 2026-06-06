# GripLab Surface Catalog — the full pressure source

Status: lifted from `grip-lab/services/griplab_service/src/griplab_service/
local_client/app.py:438` (`handle_protocol_message`) + the stream dataclasses
below it. This is the authoritative inventory Prism's IR must be able to express.

## The finding the full surface reveals

The 4-endpoint Phase-0 slice saw shapes in isolation. The full dispatcher shows
the real structure: **each shape is a *source* surrounded by a cluster of
role-typed verbs** — the GripShare role taxonomy (input / output / control /
diagnostic / handle / private, per `GripShareAdvertisement.md`) made concrete.

- A **terminal** is not an endpoint — it is a **handle** (`term.open` → sessionId)
  that keys several views: the live output **Stream** (`session.output.subscribe`),
  the interactive control plane (`term.input`, `term.resize`), teardown
  (`term.close`), and a transport handoff (`term.ticket` → iroh). This is exactly
  Glade's "one source composes multiple flow types bound by a stable handle"
  (`GladeSurfacePrecis.md:79`).
- A **file** (SWMR) carries an **input plane**: `file.window.update` is the
  consumer writing a window preference *upstream*, plus `file.unsubscribe`
  teardown.
- A **chat** (Log) pairs `chat.subscribe` (replay+tail) with `chat.post` (append).
- **Atoms** pair `*.subscribe` (push) with `*.refresh` (control) and `*.get`
  (pull). Pull-vs-push is a real initiation-axis distinction the slice must model.

So the IR unit is not "method" — it is **(source × shape × {role-typed verbs})**.
That is the structural lesson for Phase 1.

## Full method inventory

Roles: **out**=output/consume, **in**=input/write, **ctl**=control,
**td**=teardown, **hdl**=handle, **dx**=diagnostic. Kind: U=unary, S=stream.

| Method | Kind | Shape | Role | Args | P0.5 status |
| --- | --- | --- | --- | --- | --- |
| `peer.presence.subscribe` | S | Atom | out | — | **modeled** (P0) |
| `presence.get` *(derived)* | U | Atom | out | — | **modeled** (pull) |
| `file.subscribe` | S | SWMR | out | window | **modeled** (P0) |
| `file.window.update` | U | SWMR | in/ctl | streamId, window | **modeled** |
| `file.unsubscribe` | U | SWMR | td | streamId | covered by handle aclose |
| `session.output.subscribe` | S | Stream | out | sessionId | **modeled** (per-handle) |
| `term.open` | U | handle | hdl | repo, cols, rows | **modeled** |
| `term.input` | U | Stream | in/ctl | sessionId, data | **modeled** |
| `term.resize` | U | — | ctl | sessionId, cols, rows | **modeled** |
| `term.close` | U | handle | td | sessionId | **modeled** |
| `chat.subscribe` | S | Log | out | — | **modeled** (new shape) |
| `chat.post` | U | Log | in | senderId, text | **modeled** |
| `cmd.run` | U | fan-out DAG | in | argv, repos | **modeled** (P0) |
| `sessions.query` | U | query | out | filter | **modeled** (pull) |
| `sessions.subscribe` | S | Atom/Log | out | — | catalog (Atom+refresh, ≈presence) |
| `workspace.status.subscribe` | S | Atom | out | — | catalog (≈presence) |
| `workspace.status.refresh` | U | — | ctl | — | catalog (refresh verb ≈ tree) |
| `tree.subscribe` | S | Atom+invalidation | out | — | catalog (≈presence) |
| `tree.refresh` | U | — | ctl | — | catalog |
| `tree.unsubscribe` | U | — | td | streamId | catalog (≈ file.unsubscribe) |
| `settings.get` | U | Atom | out | — | catalog (≈presence.get) |
| `settings.update` | U | Atom | in | payload | catalog (≈ Atom set) |
| `deps.get` | U | Atom-snapshot | out | — | catalog (pull config) |
| `peer.health.get` | U | query | dx | peerId | catalog (parameterized pull) |
| `peer.probe` | U | query (threaded) | dx | ssh, location | catalog (SSH, opaque) |
| `peer.bootstrap` | U | action (threaded) | ctl | payload | catalog (SSH, opaque) |
| `peer.bootstrap.stop` | U | — | td | bootstrapId | catalog |
| `term.ticket` | U | transport handoff | hdl | sessionId | catalog (iroh rebind) |
| `debug.perf.get` | U | Log-snapshot | dx | limit | catalog |
| `debug.perf.clear` | U | — | ctl | — | catalog |
| `admin.restart` | U | — | ctl | — | catalog |

## What "catalog" means here

"Catalog" = shape/role already covered by a modeled sibling, **or** peripheral
out-of-band machinery (SSH bootstrap, perf, process restart) whose payloads are
opaque and add no new shape. Phase 0 deliberately does not hand-build SSH/iroh
internals — they are transport/ops concerns, not delivery-shape structure.

`term.ticket` is catalog-but-important: it rebinds one source's view to a
*different transport profile* (iroh instead of the websocket output stream).
That is a direct illustration of Prism's "transport binding is a separate concern"
thesis — the same source, a different generated adapter. Flagged for P2.

## Shapes exercised (the closed set, now fully evidenced)

Atom · Log · Stream · SWMR are all present and now modeled. CRDT is the only
build-prompt shape GripLab does **not** exercise — it stays contract-only (P2),
exactly as planned.
