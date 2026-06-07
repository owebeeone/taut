"""GripLab surface — the authored Prism IR (the only governed artifact).

Extracted backward from the working Phase-0 slice (../trial/py) and the GripLab
surface catalog (../dev-docs/GripLabSurfaceCatalog.md). Declarative only: enums +
messages with tags, types, and transient flags. No services yet — that is P2.

Read whole: 2 enums, 9 messages. Enums carry integer wire values (the wire is a
projection distinct from the native string-valued enums). Transient fields are
native-only (M3 richness) and never cross the wire.
"""

import sys
from pathlib import Path

# Make the prism builder importable when this file is loaded by path.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from prism.ir.dsl import BOOL, BYTES, F, INT, STR, Enum, List, Msg, Ref, method, schema, service

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
        # presence — Atom: subscribe (push) + get (pull)
        method("presence.subscribe", kind="server_stream", role="out", shape="atom",
               events={"replace": List(Ref("PeerPresence"))}),
        method("presence.get", kind="unary", role="out",
               output=List(Ref("PeerPresence"))),
        # chat — Log: subscribe (replay+tail) + post (append)
        method("chat.subscribe", kind="server_stream", role="out", shape="log",
               events={"append": Ref("ChatMessage")}),
        method("chat.post", kind="unary", role="in",
               params=[("sender_id", STR), ("text", STR)], output=Ref("ChatMessage")),
        # file — SWMR: subscribe (snapshot+delta) + window.update (input plane)
        method("file.subscribe", kind="server_stream", role="out", shape="swmr",
               events={"snapshot": Ref("FileSnapshot"), "delta": Ref("FileDelta")}),
        method("file.window.update", kind="unary", role="ctl",
               params=[("start", INT), ("end", INT)], output=BOOL),
        # terminal — Stream + handle: open (hdl), output (out), input/resize (ctl), close (td)
        method("term.open", kind="unary", role="hdl",
               params=[("repo", STR), ("cols", INT), ("rows", INT)], output=Ref("TerminalOpened")),
        method("session.output.subscribe", kind="server_stream", role="out", shape="stream",
               params=[("session_id", STR)], events={"event": Ref("TerminalChunk")}),
        method("term.input", kind="unary", role="ctl",
               params=[("session_id", STR), ("data", BYTES)], output=BOOL),
        method("term.resize", kind="unary", role="ctl",
               params=[("session_id", STR), ("cols", INT), ("rows", INT)], output=BOOL),
        method("term.close", kind="unary", role="td",
               params=[("session_id", STR)], output=BOOL),
        # cmd.run — fan-out DAG + sessions.query (pull)
        method("cmd.run", kind="unary", role="in",
               params=[("argv", List(STR)), ("targets", List(Ref("RepoTarget")))],
               output=Ref("CmdSession")),
        method("sessions.query", kind="unary", role="out",
               params=[("peer_id", STR)], output=List(Ref("CmdSession"))),
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
        method("board.snapshot", kind="unary", role="out", output=Ref("CrdtState")),
        method("board.local_apply", kind="unary", role="in",
               params=[("actor", STR), ("field", INT), ("value", BYTES)], output=Ref("CrdtOp")),
        method("board.merge", kind="unary", role="ctl",
               params=[("op", Ref("CrdtOp"))], output=BOOL),
        method("board.sync", kind="server_stream", role="out", shape="crdt",
               events={"op": Ref("CrdtOp")}),
    ),
)
