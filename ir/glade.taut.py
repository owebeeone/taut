"""Glade wire surface — the substrate framing protocol (GLP-0005, P0.S2).

Authored against `glade/dev-docs/GladeSubstrateV1.md` (§2 model, §6 server,
GQ-9 hybrid causal-ref encoding). This is the *transport* layer, not an app
service: it carries opaque app payloads (already taut-encoded) so the glade
server stays payload-agnostic (§6). Therefore it is modeled as messages +
codecs, NOT a `service` — taut generates the frame codecs; the session state
machine (HELLO/resume/route/fold) is hand-written in node + client.

Read whole. Three layers:
  1. addressing + ordering — Head, StreamHeads, Op (the op envelope, GQ-9)
  2. frames — Hello/Welcome, Subscribe/Unsubscribe, Ops, Heads, Exchange*,
     Channel*, Chunk, Error
  3. enums — FrameType (the transport type-tag registry), Priority, ErrorCode

Payloads are opaque BYTES at this layer: an app value/delta is its own taut
message, CBOR-encoded, carried in Op.payload / Exchange*.payload. The fold
that turns ops into materialized state is taut's crdt engine (Decisions D5),
selected by Op.shape; it is not re-specified here.

Identity carried from day one (brutal to retrofit, GladeSubstrateV1 §2):
share/glade/op identity, per-origin monotonic seq, prev-hash chain, causal
refs, lamport clock. Security seams present but unenforced: Hello.principal
and Hello.capability (the punt, see GladeGrythSecurityModelAnalysisPrompt.md).
"""

import sys
from pathlib import Path

# Make the taut builder importable when this file is loaded by path.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from taut.ir.dsl import BOOL, BYTES, INT, STR, Enum, F, List, Msg, Ref, schema

SCHEMA = schema(
    # ---- enums -------------------------------------------------------------
    # FrameType is the transport type-tag registry: the session framing writes
    # this tag + length around each frame message. Not a union message — the
    # discriminator is a transport detail, the codecs are per-message.
    Enum("FrameType",
         hello=0, welcome=1,
         subscribe=2, unsubscribe=3,
         ops=4, heads=5,
         exchange_req=6, exchange_res=7,
         channel_open=8, channel_data=9, channel_close=10,
         chunk=11, error=12,
         # node<->node handshake seam (Lane R step 2). The client HELLO
         # (Hello/Welcome) carries a session + principal/capability; the node
         # peer HELLO carries a node identity instead. Appended (13/14) so the
         # existing wire values stay frozen.
         node_hello=13, node_welcome=14),
    # QoS classes for the single-socket scheduler (§6): interactive/control
    # preempt bulk log backfill; bulk may be conflated/chunked.
    Enum("Priority", control=0, interactive=1, bulk=2),
    Enum("ErrorCode",
         ok=0, equivocation=1, unknown_share=2, unauthorized=3,
         protocol=4, retention=5, internal=6),
    # Declared shape of a stream (drives the fold). Mirrors taut shapes; carried
    # as a STR on Op.shape, enumerated here for the wire vocabulary.
    Enum("Shape", value=0, log=1, stream=2),

    # ---- addressing + ordering --------------------------------------------
    # A point in one origin's log, plus that origin's chain head hash (GQ-9).
    # In Op.refs the hash MAY be empty (causal ref only); in StreamHeads it is
    # the per-origin chain head used for resume + equivocation detection.
    Msg("Head",
        F("origin", 1, STR),
        F("seq", 2, INT),
        F("hash", 3, BYTES, optional=True)),

    # Per-stream heads: the resume/anti-entropy unit, scoped to one
    # (share, glade_id, key) stream. key empty = the null/default key.
    Msg("StreamHeads",
        F("share", 1, STR),
        F("glade_id", 2, STR),
        F("key", 3, BYTES),
        F("heads", 4, List(Ref("Head")))),

    # The op envelope (GladeSubstrateV1 §2, GQ-9 hybrid). One attributed change.
    #   addressing: share / glade_id / key   (the stream id is (share,glade_id,key))
    #   identity:   origin / seq             (per-origin monotonic)
    #   integrity:  prev                     (hash of predecessor in THIS origin's
    #                                          log — the per-origin chain)
    #   causality:  lamport / refs           (cross-origin order + causal heads)
    #   fold:       shape                    (selects the taut fold)
    #   data:       payload                  (opaque app taut bytes: value | delta)
    Msg("Op",
        F("share", 1, STR),
        F("glade_id", 2, STR),
        F("key", 3, BYTES),
        F("origin", 4, STR),
        F("seq", 5, INT),
        F("prev", 6, BYTES, optional=True),
        F("lamport", 7, INT),
        F("refs", 8, List(Ref("Head"))),
        F("shape", 9, Ref("Shape")),
        F("payload", 10, BYTES)),

    # ---- frames ------------------------------------------------------------
    # Session init + resume. principal/capability are unenforced security seams
    # (the punt). heads = what this peer already has, so the other side ships
    # only the gaps.
    Msg("Hello",
        F("session", 1, STR),
        F("protocol", 2, INT),
        F("principal", 3, STR, optional=True),
        F("capability", 4, BYTES, optional=True),
        F("heads", 5, List(Ref("StreamHeads")))),
    Msg("Welcome",
        F("session", 1, STR),
        F("protocol", 2, INT),
        F("heads", 3, List(Ref("StreamHeads")))),

    # Node<->node handshake (the s-sync DIAL gate: "node<->node HELLO seam").
    # node_id = sha256(node key) — the stubbed-but-structure-real identity
    # (GladeSystemDataSeamNotes: ed25519 swaps in behind the seam). sig is the
    # operator/origin signature seam — present, unenforced (empty when stubbed).
    # Distinct from the client Hello: peers exchange node identity, not a
    # session principal, and sync integrity NEVER trusts this handshake.
    Msg("NodeHello",
        F("node_id", 1, BYTES),
        F("protocol", 2, INT),
        F("sig", 3, BYTES, optional=True)),
    Msg("NodeWelcome",
        F("node_id", 1, BYTES),
        F("protocol", 2, INT),
        F("sig", 3, BYTES, optional=True)),

    # Interest. key absent = all keys under glade_id. from = resume cursor.
    Msg("Subscribe",
        F("share", 1, STR),
        F("glade_id", 2, STR),
        F("key", 3, BYTES, optional=True),
        F("from", 4, List(Ref("Head")), optional=True)),
    Msg("Unsubscribe",
        F("share", 1, STR),
        F("glade_id", 2, STR),
        F("key", 3, BYTES, optional=True)),

    # The main data frame: a batch of attributed ops. pri lets the sender mark
    # live (interactive) vs backfill (bulk) for the scheduler.
    Msg("Ops",
        F("ops", 1, List(Ref("Op"))),
        F("pri", 2, Ref("Priority"), optional=True)),

    # Heads exchange (resume / anti-entropy), both directions.
    Msg("Heads",
        F("streams", 1, List(Ref("StreamHeads")))),

    # Directed request/response (the exchange shape) — not replicated.
    Msg("ExchangeReq",
        F("share", 1, STR),
        F("glade_id", 2, STR),
        F("corr", 3, STR),
        F("payload", 4, BYTES)),
    Msg("ExchangeRes",
        F("corr", 1, STR),
        F("ok", 2, BOOL),
        F("payload", 3, BYTES, optional=True),
        F("error", 4, STR, optional=True)),

    # Directed live channel (keystrokes, control) — ephemeral, never replicated
    # (read/write asymmetry, GladeTerminalSliceProposal §3).
    Msg("ChannelOpen",
        F("share", 1, STR),
        F("glade_id", 2, STR),
        F("channel", 3, STR),
        F("key", 4, BYTES, optional=True)),
    Msg("ChannelData",
        F("channel", 1, STR),
        F("data", 2, BYTES)),
    Msg("ChannelClose",
        F("channel", 1, STR),
        F("reason", 2, STR, optional=True)),

    # Chunking for oversized single payloads (e.g. a log-backfill snapshot):
    # reassembled by corr before decode. Frame-size caps + this keep bulk from
    # head-of-line-blocking interactive frames on the single socket (§6).
    Msg("Chunk",
        F("corr", 1, STR),
        F("index", 2, INT),
        F("total", 3, INT),
        F("data", 4, BYTES)),

    # Diagnostic. equivocation = a forked per-origin chain (same (origin,seq),
    # different hash) was detected and rejected (P1.S4).
    Msg("Error",
        F("code", 1, Ref("ErrorCode")),
        F("message", 2, STR),
        F("share", 3, STR, optional=True),
        F("glade_id", 4, STR, optional=True),
        F("corr", 5, STR, optional=True)),
)
