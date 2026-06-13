"""Glade wire golden corpus (GLP-0005, P0.S3).

The conformance oracle for the glade framing protocol (`ir/glade.taut.py`):
each reference value encoded by taut's canonical (Python) codec to exact CBOR
bytes. Rust + TS codecs conform iff they reproduce these bytes (P0.S4).

Values = synth coverage (one per message, every field type) + curated edge
cases the plan calls out: empty causal refs, null key, zero-length payload,
per-origin chain hashes, multi-origin heads, unicode, equivocation error,
large chunk, and the security seams (principal/capability) both set and unset.

Run: `PYTHONPATH=src python -m taut.corpus.glade_build`.
"""

from __future__ import annotations

from pathlib import Path

from . import kit, synth
from ..ir.export import export_to
from ..ir.load import load_schema
from ..ir.model import Schema
from ..ir.validate import validate_or_raise

_TAUT = Path(__file__).resolve().parents[3]
IR_PATH = _TAUT / "ir" / "glade.taut.py"
GOLDEN_PATH = _TAUT / "corpus" / "glade.golden.json"
IR_JSON_PATH = _TAUT / "corpus" / "glade.ir.json"


def _head(origin: str, seq: int, h: bytes | None) -> dict:
    return {"origin": origin, "seq": seq, "hash": h}


def _op(*, share="sh", glade_id="g", key=b"", origin="o", seq=0, prev=None,
        lamport=0, refs=None, shape="value", payload=b"") -> dict:
    return {"share": share, "glade_id": glade_id, "key": key, "origin": origin,
            "seq": seq, "prev": prev, "lamport": lamport,
            "refs": refs if refs is not None else [], "shape": shape, "payload": payload}


def curated_values() -> dict[str, tuple[str, dict]]:
    """name -> (message, native dict). Every wire field present; None for absent
    optionals (the griplab convention). Hand-authored edge cases."""
    sh32 = b"\xab" * 32
    op_min = _op(payload=b"")                                   # null key, empty refs, no prev
    op_chain = _op(key=b"\x01\x02", origin="o", seq=5, prev=sh32, lamport=9,
                   refs=[_head("o2", 3, b""), _head("o3", 1, None)],
                   shape="log", payload=b"hello")
    sh_multi = {"share": "sh", "glade_id": "g", "key": b"",
                "heads": [_head("a", 7, b"\x01" * 32), _head("b", 0, b"\x02" * 32)]}
    return {
        # --- op envelope edge cases ---
        "edge/op-min": ("Op", op_min),
        "edge/op-chain": ("Op", op_chain),
        # --- resume / heads ---
        "edge/streamheads-multi": ("StreamHeads", sh_multi),
        "edge/heads-frame": ("Heads", {"streams": [sh_multi]}),
        # --- hello: security seams set and unset (the punt) ---
        "edge/hello-resume": ("Hello", {"session": "sess-1", "protocol": 1,
            "principal": "user:ann", "capability": b"\x00\x01", "heads": [sh_multi]}),
        "edge/hello-anon": ("Hello", {"session": "sess-2", "protocol": 1,
            "principal": None, "capability": None, "heads": []}),
        "edge/welcome": ("Welcome", {"session": "sess-1", "protocol": 1, "heads": [sh_multi]}),
        # --- interest ---
        "edge/subscribe-key": ("Subscribe", {"share": "sh", "glade_id": "g",
            "key": b"\x01\x02", "from": [_head("a", 7, None)]}),
        "edge/subscribe-allkeys": ("Subscribe", {"share": "sh", "glade_id": "g",
            "key": None, "from": None}),
        "edge/unsubscribe": ("Unsubscribe", {"share": "sh", "glade_id": "g", "key": None}),
        # --- ops batch + priority ---
        "edge/ops-bulk": ("Ops", {"ops": [op_min, op_chain], "pri": "bulk"}),
        "edge/ops-nopri": ("Ops", {"ops": [op_min], "pri": None}),
        # --- exchange (directed) ---
        "edge/exchange-req": ("ExchangeReq", {"share": "sh", "glade_id": "run",
            "corr": "x1", "payload": b"argv"}),
        "edge/exchange-ok": ("ExchangeRes", {"corr": "x1", "ok": True,
            "payload": b"out", "error": None}),
        "edge/exchange-err": ("ExchangeRes", {"corr": "x2", "ok": False,
            "payload": None, "error": "boom"}),
        # --- channel (directed, ephemeral) ---
        "edge/channel-open": ("ChannelOpen", {"share": "sh", "glade_id": "pty",
            "channel": "ch1", "key": b""}),
        "edge/channel-data": ("ChannelData", {"channel": "ch1", "data": b"keystroke"}),
        "edge/channel-close": ("ChannelClose", {"channel": "ch1", "reason": None}),
        # --- chunk (large-ish, reassembled by corr) ---
        "edge/chunk": ("Chunk", {"corr": "c1", "index": 0, "total": 4,
            "data": bytes(range(256))}),
        # --- error: equivocation + unicode ---
        "edge/error-equivocation": ("Error", {"code": "equivocation",
            "message": "forked chain at (o,5)", "share": "sh", "glade_id": "g", "corr": None}),
        "edge/error-unicode": ("Error", {"code": "protocol",
            "message": "é—中—\U0001f600 bad frame", "share": "shär",
            "glade_id": "glⓐde", "corr": None}),
    }


def glade_values(schema: Schema) -> dict[str, tuple[str, dict]]:
    """Synth coverage (every message) + curated edge cases. Synth keys are
    message names; curated keys are `edge/*` — no collision."""
    values = dict(synth.synth_values(schema))
    values.update(curated_values())
    return values


def main() -> None:
    schema = load_schema(IR_PATH)
    validate_or_raise(schema)
    export_to(schema, IR_JSON_PATH)
    corpus = kit.build_corpus(schema, glade_values(schema))
    GOLDEN_PATH.write_text(kit.golden_json(corpus))
    print(f"wrote IR to {IR_JSON_PATH} and {len(corpus)} vectors to {GOLDEN_PATH}")


if __name__ == "__main__":
    main()
