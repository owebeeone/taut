"""Golden conformance corpus — generated from the Python reference.

Reference values (native dicts) per message, plus the canonical SWMR
snapshot->delta->delta frame sequence that pins the resume-offset handoff. The
golden file maps each entry name to the exact CBOR hex. Every other language must
reproduce these bytes; this is the oracle that lets us trust generated code.
"""

from __future__ import annotations

import json
from pathlib import Path

from ..gen import rust as rust_gen
from ..ir.export import export_to
from ..ir.load import load_schema
from ..ir.model import Schema
from ..ir.validate import validate_or_raise
from ..wire import codec

# Repo-relative paths.
_PRISM = Path(__file__).resolve().parents[3]
IR_PATH = _PRISM / "ir" / "griplab.prism.py"
GOLDEN_PATH = _PRISM / "corpus" / "griplab.golden.json"
IR_JSON_PATH = _PRISM / "corpus" / "griplab.ir.json"


# Reference values: name -> (message, native-dict). Enums as member-name strings;
# transient fields omitted (they never reach the wire).
def reference_values() -> dict[str, tuple[str, dict]]:
    repo_ok = {"repo": "alpha", "exit_code": 0, "output": "git status @ alpha", "error": None}
    repo_err = {"repo": "beta", "exit_code": 2, "output": "", "error": "beta: exited 2"}
    snapshot = {"resource_id": "file:notes.txt", "resume_seq": 1,
                "content": b"hello world", "window_start": 0, "window_end": -1}
    delta1 = {"resource_id": "file:notes.txt", "base_seq": 1, "seq": 2,
              "ops": [{"op": "insert", "offset": 11, "length": 0, "data": b"!"}],
              "result_size": 12}
    delta2 = {"resource_id": "file:notes.txt", "base_seq": 2, "seq": 3,
              "ops": [{"op": "delete", "offset": 0, "length": 5, "data": b""}],
              "result_size": 7}
    return {
        "PeerPresence/online": ("PeerPresence",
            {"id": "p1", "name": "Ann", "status": "online", "online": True, "location": "NYC"}),
        "ByteOp/replace": ("ByteOp",
            {"op": "replace", "offset": 3, "length": 2, "data": b"\x00xy"}),
        "ChatMessage/first": ("ChatMessage", {"id": 0, "sender_id": "ann", "text": "hi"}),
        "TerminalChunk/ls": ("TerminalChunk", {"session_id": "term-1", "data": b"$ ls\n"}),
        "TerminalOpened/alpha": ("TerminalOpened",
            {"session_id": "term-1", "repo": "alpha", "cols": 120, "rows": 40}),
        "RepoRun/ok": ("RepoRun", repo_ok),
        "RepoRun/err": ("RepoRun", repo_err),
        "CmdSession/mixed": ("CmdSession",
            {"session_id": "sess-0001", "argv": ["git", "status"], "targets": [repo_ok, repo_err]}),
        # The SWMR handoff sequence — base_seq of each delta == prior seq.
        "swmr/snapshot": ("FileSnapshot", snapshot),
        "swmr/delta-1": ("FileDelta", delta1),
        "swmr/delta-2": ("FileDelta", delta2),
    }


def generate_golden(schema: Schema) -> dict[str, dict]:
    """name -> {message, cbor-hex}; self-describing so any language can replay."""
    return {
        name: {"message": message, "cbor": codec.encode(schema, message, value).hex()}
        for name, (message, value) in reference_values().items()
    }


def main() -> None:
    schema = load_schema(IR_PATH)
    validate_or_raise(schema)
    export_to(schema, IR_JSON_PATH)
    golden = generate_golden(schema)
    GOLDEN_PATH.write_text(json.dumps(golden, indent=2, sort_keys=True) + "\n")
    rust_gen.emit()
    print(f"wrote IR to {IR_JSON_PATH}, {len(golden)} vectors to {GOLDEN_PATH}, and the Rust corpus")


if __name__ == "__main__":
    main()
