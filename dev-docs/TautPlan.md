# taut — Build Plan

Status: working draft (Phase 0 plan)
Owner: Gianni
Companion specs: the "taut" build prompt (north-star brief);
`../../dev-docs/glade/GladeSurfacePrecis.md` (the model);
`../../grip-lab/` (the pressure).

> **One-line thesis.** taut is the cross-language mechanism layer under Glade's
> declarative surface: author one tiny declarative IR, generate native types +
> codecs + service stubs + shape-aware sync for Py/TS/Rust/C++, and pin
> correctness with a golden conformance corpus. We **discover** the IR by
> de-noising the real GripLab protocol, not by designing in the abstract.

---

## 1. Why GripLab is the pressure, and Glade/Grip the model

These are not two unrelated inputs. They are the *consumer* and the *lens* of the
same thing.

**GripLab is the pressure** — a live app whose client/server boundary already
carries the full mix of data-flow semantics taut must serve. Today that boundary
is hand-written:

- One transport: WebSocket carrying a JSON `ServiceEnvelope`
  (`grip-lab/src/lab/serviceClient/protocol.ts:16`), kind ∈
  `request | response | stream-event | error`, with an untyped
  `payload: Record<string, unknown>` bag.
- ~290 lines of hand-written `parse*` validators *per message type* in that one
  file — `parsePeerPresence`, `parsePeerHealth`, `parseServiceStreamEvent`, … —
  re-implemented again on the Python side
  (`grip-lab/services/griplab_service/.../protocol/envelope.py`).
- Stream events already speak taut's shape vocabulary in stringly-typed form:
  `event ∈ {snapshot, delta, reset, …}` + a `seq` counter
  (`protocol.ts:236`), and the file feed carries byte-level `ByteOp[]` deltas
  with `fileVersion` / `windowVersion` resume tokens
  (`grip-lab/services/filedelta-ts/src/model.ts`).

This is precisely the "denormalized DB of code" / boilerplate-as-smell that the
north star calls out. **Every one of those `parse*` functions is mechanism taut
generates from intent.**

**Glade is the model** — `GladeSurfacePrecis.md` already states taut's design as
the three-axis declaration:

```
declare( value-type  ×  flow-type  ×  scope )  →  a tap (substrate hidden & swappable)
```

with the flow-type set **atom / log / editable-blob(CRDT) / stream**
(`GladeSurfacePrecis.md:60`). That is taut's delivery-shape closed set, minus the
codegen + cross-language + oracle machinery taut adds. The mapping is near 1:1:

| taut shape (build prompt §4) | Glade flow-type | GripLab feed (the proof) |
| --- | --- | --- |
| **Atom** (whole-state, latest, LWW) | `atom` | `peer.presence.subscribe`, `workspace.status.subscribe` |
| **Log** (append-only, replay-from-cursor) | `log` ≈ `model:AppendLog` | `chat.subscribe`, `sessions.subscribe` |
| **Stream** (live, ephemeral, no replay) | `stream` ≈ `model:TerminalPty` | `session.output.subscribe` |
| **SWMR / Snapshot+Delta** (snapshot+offset, then deltas) | `atom`+`log` composed over one source | `file.subscribe` (ByteOp deltas, window resume) |
| **CRDT** (multi-writer merge) | `editable blob` ≈ `model:CrdtText` | *not yet in GripLab* — contract-only |

Glade even pre-states taut's hardest correctness point: *"one source often
composes two flow types"* (`GladeSurfacePrecis.md:71`) — a terminal is a live
**stream** and a durable **log** over one handle. That is the Snapshot+Delta
handoff the build prompt warns is "where naive implementations silently miss or
double-apply edits."

**Conclusion that governs the plan:** taut is not a fork of Glade — it is the
**mechanism tier** Glade's surface always assumed but never built. We extract
taut's IR *backwards* from GripLab's real protocol, validate it against Glade's
flow-type taxonomy, and prove it by regenerating GripLab's boundary and passing a
byte-exact corpus across languages. `.glade` stays the thinking artifact; taut's
IR is the machine-checkable contract beneath it.

---

## 2. Repository structure

```
taut/
  dev-docs/
    TautPlan.md              # this file
    TautIR.md                # (P1) the IR meta-schema, frozen append-only
    TautWire.md              # (P1) wire substrate decision + frozen vocabulary
    TautShapes.md            # (P2) the closed delivery-shape set + validator rules
  src/                        # the BUILDER infrastructure — Python (intent → mechanism)
    taut/
      ir/                     # IR model (pydantic), loader, validator (declarative-only gate)
      wire/                   # codec strategy + canonical-bytes reference
      shapes/                 # delivery-shape definitions, axis validator
      gen/                    # generators: per-language emitters (py, ts, rs, cpp)
        python/
        typescript/
        rust/
        cpp/
      corpus/                 # golden-vector generator (value→bytes, request→frame)
      cli.py                  # `taut gen <lang>`, `taut corpus`, `taut check`
    pyproject.toml
    tests/
  ir/                         # AUTHORED IR modules (the only governed artifact)
    griplab.taut.py          # GripLab surface as Python-as-DSL declarations
  corpus/                     # generated golden vectors (committed; the oracle)
  trial/                      # GENERATED + hand-wired target slices (one per language)
    py/                       # reference implementation (defines truth)
    ts/                       # generalization gate (P3): TS client ↔ Py server
    rs/                       # P5
    cpp/                      # P6 — the showcase target (compile-time + static_assert)
```

Notes:
- **`src/` is Python** — the build prompt names Python as the authoring front-end
  *and* the reference that defines corpus truth (§5). Generators are Python that
  emit each target language's source.
- **`ir/` vs `src/`**: `ir/` holds *authored intent* (governed, tiny, read whole);
  `src/` holds the *machine* that consumes it. Never fuse them.
- **`trial/<lang>/`** holds generated mechanism + a thin hand-written composition
  root (DI, handlers) per language. Generated files are never hand-edited;
  regeneration reproduces the tree (DoD §9).
- Python is both a builder (`src/`) and a target (`trial/py/`). The reference
  implementation lives in `trial/py/`; the corpus is generated from it.

---

## 3. The IR — discovered from GripLab (not designed up front)

The IR is **flat, content-addressed, versioned**, declarative-only, and small
enough to read whole. For Phase 0 we do **not** freeze it — we hand-wire the slice
first (build prompt §8.0) and let the real shapes fall out, then extract the IR
backward in Phase 1. What the GripLab surface already tells us the IR must carry:

- **enums** — e.g. `PeerPresenceStatus` (`protocol.ts:25`), `ProtocolKind`.
- **messages** — fields: name, tag, wire-type, repeated/optional/map, **transient
  flag** (in-memory-only; ignored by codec), optional closed-form derivation rule.
  GripLab's `PeerPresence`, `FileWindowSnapshot`, `TextWindowDelta`, `ByteOp`,
  `DiffHunk` are the first messages.
- **services** — methods with `name`, `input`, `output`, **streaming-kind**.
  GripLab gives both unary (`cmd.run`, `term.input`) and streaming
  (`*.subscribe`) directly.
- **per-stream delivery shape** — the axis/preset annotation (Atom / Log / Stream
  / SWMR …). This is the centerpiece; §5 below.

It carries **no imperative logic and no representation specifics** — a front-end
validator must *reject* non-declarative constructs (the Python-as-DSL is a
restricted subset). The transient/untagged richness (caches, line indices,
handles) lives in the native type, never on the wire (M3 native types).

---

## 4. Wire substrate — recommendation, surfaced for decision

This is a build-prompt §10 decision; I will not guess it silently. Recommendation
with rationale, **your call to ratify:**

- **Phase 0:** stay on **canonical JSON**, byte-for-byte mirroring GripLab's
  current envelope. Zero new codec; lets the slice prove the *shapes and IR*, and
  lets a taut-generated client talk to the *real, unmodified* GripLab server as
  an interop check.
- **Phase 1 (freeze here):** ride **CBOR** (RFC 8949 deterministic encoding) as
  the frozen substrate. Rationale: (a) no N hand-written codecs — "reuse over
  build"; (b) deterministic ordering + canonical form gives byte-exact corpus
  for free; (c) integer-keyed maps preserve unknown fields and stay compact;
  (d) CRDT ops/state are representable from day one (build prompt §6 requires it).
  The own-TLV alternative buys tighter control of scalar widths at the cost of
  hand-writing/maintaining four codecs — not worth it for this project's
  AI-built, blast-radius-small posture.

**DECIDED (2026-06-06): CBOR.** Frozen at P1. No `cbor2` dep — a hand-rolled
deterministic CBOR codec (RFC 8949 §4.2 core deterministic: definite-length,
shortest-form ints, ascending map keys) over the frozen vocabulary {int, bytes,
text, array, map-with-int-keys, bool, null}. Messages encode as CBOR **maps with
integer keys = field tags**; enums encode as their integer wire value; bytes are
native byte strings (no base64). This *is* the tiny wire vocabulary.

**Codec strategy — IR-driven at runtime for Python, NOT text codegen.** Per
CLAUDE.md ("probably no codegen, ever; build the runtime as code-as-declaration")
the Python reference codec is a generic CBOR encoder/decoder *driven by the IR
data* — no `.py` is emitted. Text codegen is introduced only at P3, where adding
TypeScript actually forces it (and where drift between decl and runtime would
first bite). This keeps taut from becoming a compiler front-end prematurely.

---

## 5. Delivery shapes — the closed set, anchored to GripLab feeds

The shapes are a **closed, validated set**; axes are the justification/derivation,
never the public surface (build prompt §4). Phase 0 implements three; the rest
land in P2.

| Shape | Public API (idiomatic, hand-designed) | Derived streaming-kind | GripLab anchor |
| --- | --- | --- | --- |
| **Atom** | `get` / `set` / `subscribe-replace` | server-stream of replacements | `peer.presence` |
| **Stream** | `subscribe` (live only) | server-stream | `session.output` |
| **SWMR / Snapshot+Delta** | `snapshot(+resume-offset)` / `subscribe-deltas` | snapshot RPC + delta stream | `file.subscribe` |
| **Log** *(P2)* | `append` / `read-from-offset` / `tail` | server-stream from offset | `chat`, `sessions` |
| **CRDT** *(P2, contract-only)* | `local-apply` / `merge-remote` / `sync` | bidi | — (engine slot empty) |

**The non-negotiable invariant** (build prompt §4, echoed by Glade's
live/replay split): the SWMR snapshot **MUST carry the offset the delta feed
resumes from**. GripLab's `file.subscribe` already does this with
`fileVersion`/`windowVersion`; the validator and corpus must pin that handoff so
no language drops or double-applies an edit. This is the single most important
correctness oracle in the slice.

A validator rejects incoherent axis combinations and anything outside the set;
extension = deliberately adding a new *implemented* shape, never exposing raw
axes.

---

## 6. Orchestration — the fan-out + error method

Build prompt §8.0 requires "one method with real fan-out + error handling on an
sdax-style DAG." GripLab hands us the natural one: **`cmd.run`** spawns a command
across N repos (and optionally peers) and returns a `sessionId`, with per-target
execution and per-target errors (`cmd.run` →
`grip-lab/services/griplab_service/.../local_client/app.py`).

Phase 0 models this as a declarative task DAG: fan-out wave (one task per repo) →
gather → publish session. Per-task error policy (timeout / failure isolation) is
declared, not coded into the handler. The handler stays a plain function over
native types; the scheduler derives the waves. Full portable orchestration spec
is deferred to Phase 4 — Phase 0 only needs the shape to fall out honestly.

---

## 7. The oracle — golden conformance corpus

Generated from the Python reference (`trial/py/`) alongside the IR:

- **value → exact bytes** per message (round-trip + canonical encoding).
- **request → exact frame** per method, and **canonical event sequences** per
  shape (esp. the SWMR snapshot+resume-offset+delta handoff).
- Committed under `taut/corpus/`. Every implemented language reproduces it
  byte-for-byte in CI. **C++ additionally compiles the vectors into
  `static_assert`s** for anything compile-time-known (build prompt §5a).

The corpus is what lets us trust generated and AI-written code without
line-by-line review — it is the contract, not the prose.

---

## 8. Phase plan (build prompt §8, re-cast onto GripLab)

The discipline: start concrete, extract the declarative layers *backward*,
validate each abstraction by adding the *second* language before going wide.
Phases 0–3 + 7 are the proven-value foundation; 4–6 are the harder cross-language
work and **must not block the foundation**.

- **P0 — Python vertical slice, hand-wired, working.** `trial/py/`. One service =
  a GripLab terminal-slice subset: **Atom** (presence), **Stream** (terminal
  output), **SWMR** (file snapshot+delta), plus the **`cmd.run` fan-out+error
  DAG**. No codegen. JSON wire mirroring GripLab. **Goal: discover the real shapes
  of types, service, orchestration, delivery.** *(This plan's immediate target.)*
- **P1 — Extract the data layer.** Types → IR (`ir/griplab.taut.py`); generate
  the Python codec; emit golden vectors; round-trip validate. **Freeze the wire
  vocabulary here**, including CRDT op/state representation (no engine).
- **P2 — Extract service contract + shape API.** IR service/stream defs +
  delivery-shape annotations + validator; generated Py stubs + clients; same
  endpoints now run the generated path. Add **Log**, **Snapshot+Delta**, and the
  **CRDT contract surface** (API present, engine slot empty).
- **P3 — Generalization gate: add TypeScript.** `trial/ts/`. Generate TS
  types+codec+stubs+shape clients; pass the *same* corpus; a TS client talks to
  the Py server across every implemented shape. **This is also the real interop
  win**: it regenerates GripLab's hand-written `protocol.ts` boundary from the IR.
  Fix the IR here while it is cheap.
- **P4 — Formalize orchestration.** Lift the `cmd.run` DAG into a portable
  declarative spec (waves; per-task retry/timeout/fallback + structured
  cancellation; teardown). Python executes on sdax. Sagas deferred.
- **P5 — Add Rust.** `trial/rs/`. Codec + stubs + shape clients; tokio scheduler
  binding. Arena/index representations allowed as transient state.
- **P6 — Add C++ (the long pole).** `trial/cpp/`. Build prompt §5a in full:
  C++23/26, compile-time selection/derivation, `static_assert` corpus,
  concepts-first errors, TMP confined to the generated mechanism.
- **P7 — Distribution / BSR.** IR modules as OCI artifacts; digest pinning;
  breaking-change gate (declarative IR diff); published corpus. No bespoke
  registry.

Cross-cutting: the CRDT wire + API surface is required from P1–P2; a CRDT
*engine* is never a per-platform deliverable (pluggable Automerge/Yjs slot).

---

## 9. Phase 0 — concrete deliverables (what we build next)

Definition of done for P0:

1. `trial/py/` runs a `GripLabSlice` service over WebSocket+JSON with four
   endpoints:
   - `presence.subscribe` — **Atom**, whole peer list, latest-wins.
   - `terminal.output.subscribe` — **Stream**, live append, ephemeral.
   - `file.subscribe` — **SWMR**, snapshot carrying resume offset + ByteOp
     deltas; resume/reset honored.
   - `cmd.run` — unary, **fan-out** across repos on a task DAG with per-target
     error isolation.
2. Native Python types are **dataclasses/pydantic**, not hand-written `__init__`
   or hand-written `parse*` (we are deliberately *not* reproducing GripLab's
   boilerplate; that boilerplate is the thing we're proving away).
3. A thin hand-written composition root wires DI + handlers; handlers are plain
   functions over native types — no transport/shape/DI logic inside them.
4. A throwaway in-process "client" exercises all four shapes and the fan-out
   error path, so the delivery semantics are observable and testable.
5. Notes captured in `TautIR.md` / `TautShapes.md` stubs: which field/service/
   shape shapes actually emerged, ready to extract in P1.

Explicitly **out of P0 scope:** any codegen, the frozen wire, the IR validator,
TS/Rust/C++, the CRDT engine, OCI distribution. Discover first, abstract backward.

---

## 10. Open decisions to surface (build prompt §10 — your call, not guessed)

1. **Wire substrate** at the P1 freeze: CBOR (recommended) vs minimal-own-TLV;
   keep JSON as a permanent debug profile? (§4)
2. **v1 transport profile(s):** GripLab uses WebSocket+JSON. Keep that as the v1
   profile, or add a binary-wire profile (HTTP/2 + CBOR) alongside a JSON debug
   profile?
3. **Error-policy vocabulary** for the orchestration spec — which knobs are v1
   (retry / timeout / fallback / cancel)? Driven by what `cmd.run` actually needs.
4. **CRDT type-modeling vocabulary** in the IR — which CRDT field types are
   wire-representable in v1 (text? counter? map?). GripLab has no CRDT feed yet,
   so this is contract-only and the least pressured — defer detail to P2.
5. **C++ toolchain target** for the P2996 reflection path vs the fallback — defer
   to P6, but name the gating compiler/std now so the corpus harness assumes it.

---

## 11. Style guardrails (from CLAUDE.md / AGENTS.md — hold the line)

- **Declarative-first, always.** System shape lives in data, not control flow.
- **Boilerplate is a smell.** If we're about to hand-write repetitive scaffolding,
  stop and generate it. GripLab's `parse*` wall is the cautionary example.
- **Clean seams.** declaration / producer / consumer stay separate; consumers
  never know producers. Mock→real with no consumer rewrite.
- **TDD per AGENTS.md.** The corpus is the test spine; shapes get tests at the
  semantic-handoff points (esp. SWMR resume offset).
- **Verify before asserting; stay in scope; don't manufacture work.**
