"""GripLab surface — the authored taut IR (the only governed artifact).

Extracted backward from the working Phase-0 slice (../trial/py) and the GripLab
surface catalog (../dev-docs/GripLabSurfaceCatalog.md). Declarative only: enums +
messages with tags, types, and transient flags. No services yet — that is P2.

Read whole: 2 enums, 9 messages. Enums carry integer wire values (the wire is a
projection distinct from the native string-valued enums). Transient fields are
native-only (M3 richness) and never cross the wire.
"""

import sys
from pathlib import Path

# Make the taut builder importable when this file is loaded by path.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from taut.ir.dsl import BOOL, BYTES, F, INT, STR, Enum, List, Msg, Ref, method, schema, service

SCHEMA = schema(
    # --- enums (integer wire values) ---
    Enum("PresenceStatus", configured=0, offline=1, starting=2, online=3, error=4),
    Enum("OpKind", insert=0, delete=1, replace=2),

    # --- Atom: presence ---
    Msg("PeerPresence",
        F("id", 1, STR),
        F("name", 2, STR),
        F("status", 3, Ref("PresenceStatus")),
        F("online", 4, BOOL),
        F("location", 5, STR)),

    # --- SWMR: file ---
    Msg("ByteOp",
        F("op", 1, Ref("OpKind")),
        F("offset", 2, INT),
        F("length", 3, INT),
        F("data", 4, BYTES)),
    Msg("FileSnapshot",
        F("resource_id", 1, STR),
        F("resume_seq", 2, INT),         # the load-bearing resume offset
        F("content", 3, BYTES),
        F("window_start", 4, INT),
        F("window_end", 5, INT),
        F("preview", 6, STR, transient=True)),   # native-only cache
    Msg("FileDelta",
        F("resource_id", 1, STR),
        F("base_seq", 2, INT),
        F("seq", 3, INT),
        F("ops", 4, List(Ref("ByteOp"))),
        F("result_size", 5, INT)),

    # --- Log: chat ---
    Msg("ChatMessage",
        F("id", 1, INT),
        F("sender_id", 2, STR),
        F("text", 3, STR)),

    # --- Stream + handle: terminal ---
    Msg("TerminalChunk",
        F("session_id", 1, STR),
        F("data", 2, BYTES)),
    Msg("TerminalOpened",
        F("session_id", 1, STR),
        F("repo", 2, STR),
        F("cols", 3, INT),
        F("rows", 4, INT)),

    # --- fan-out DAG: cmd.run ---
    Msg("RepoTarget",
        F("repo", 1, STR),
        F("fail_with", 2, INT)),
    Msg("RepoRun",
        F("repo", 1, STR),
        F("exit_code", 2, INT),
        F("output", 3, STR),
        F("error", 4, STR, optional=True)),
    Msg("CmdSession",
        F("session_id", 1, STR),
        F("argv", 2, List(STR)),
        F("targets", 3, List(Ref("RepoRun"))),
        F("started_monotonic", 4, INT, transient=True)),   # native-only

    # --- service: the GripLab surface (source × shape × role-typed verbs) ---
    service("GripLab",
        # presence — Atom: subscribe (push) + get (pull, unary)
        method("presence.subscribe", role="out", shape="atom",
               out=List(Ref("PeerPresence"))),
        method("presence.get", role="out",
               out=List(Ref("PeerPresence"))),
        # chat — Log: subscribe (replay+tail) + post (append, unary)
        method("chat.subscribe", role="out", shape="log",
               out=Ref("ChatMessage")),
        method("chat.post", role="in",
               params=[("sender_id", STR), ("text", STR)], out=Ref("ChatMessage")),
        # file — SWMR: subscribe (snapshot+delta) + window.update (input plane)
        method("file.subscribe", role="out", shape="swmr",
               out={"snapshot": Ref("FileSnapshot"), "delta": Ref("FileDelta")}),
        method("file.window.update", role="ctl",
               params=[("start", INT), ("end", INT)], out=BOOL),
        # terminal — Stream + handle: open (hdl), output (out), input/resize (ctl), close (td)
        method("term.open", role="hdl",
               params=[("repo", STR), ("cols", INT), ("rows", INT)], out=Ref("TerminalOpened")),
        method("session.output.subscribe", role="out", shape="stream",
               params=[("session_id", STR)], out=Ref("TerminalChunk")),
        method("term.input", role="ctl",
               params=[("session_id", STR), ("data", BYTES)], out=BOOL),
        method("term.resize", role="ctl",
               params=[("session_id", STR), ("cols", INT), ("rows", INT)], out=BOOL),
        method("term.close", role="td",
               params=[("session_id", STR)], out=BOOL),
        # cmd.run — fan-out DAG + sessions.query (pull)
        method("cmd.run", role="in",
               params=[("argv", List(STR)), ("targets", List(Ref("RepoTarget")))],
               out=Ref("CmdSession")),
        method("sessions.query", role="out",
               params=[("peer_id", STR)], out=List(Ref("CmdSession"))),
    ),

    # --- CRDT surface (contract from day one; engine is a pluggable slot) ---
    # Wire: ops + state are representable. CrdtOp.value is the opaque encoded
    # field value; CrdtState is the reconstructible op log + version vector.
    Msg("CrdtOp",
        F("doc", 1, STR),
        F("actor", 2, STR),
        F("seq", 3, INT),
        F("field", 4, INT),          # field tag within the CRDT doc
        F("value", 5, BYTES)),       # CBOR of the field value (set for lww / delta for counter)
    Msg("VersionEntry",
        F("actor", 1, STR),
        F("seq", 2, INT)),
    Msg("CrdtState",
        F("doc", 1, STR),
        F("ops", 2, List(Ref("CrdtOp"))),
        F("version", 3, List(Ref("VersionEntry")))),
    # A CRDT document: each field declares its merge type (captured in the IR;
    # merge is not implemented per platform). lww register + PN counter (v1).
    Msg("Board",
        F("title", 1, STR, merge="lww"),
        F("votes", 2, INT, merge="counter")),

    # The CRDT API surface: local-apply / merge-remote / sync (build prompt §4).
    service("Collab",
        method("board.snapshot", role="out", out=Ref("CrdtState")),
        method("board.local_apply", role="in",
               params=[("actor", STR), ("field", INT), ("value", BYTES)], out=Ref("CrdtOp")),
        method("board.merge", role="ctl",
               params=[("op", Ref("CrdtOp"))], out=BOOL),
        method("board.sync", role="out", shape="crdt",
               out={"op": Ref("CrdtOp")}),
    ),
)
