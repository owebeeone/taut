"""Glade per-origin chain hash + oracle (GLP-0005, P1.S4 / D10).

GQ-9 gives each origin's log a hash chain: an op's `prev` is the hash of its
predecessor in that origin's log. The hash is:

    op_hash(op) = sha256(canonical_cbor(op))

over the op's full frozen encoding (prev included — that is what links the
chain and makes it tamper-evident). Cross-language agreement is *free*: the
wire corpus already proves Python/Rust/TS produce identical CBOR for ops, so
the sha256 of those identical bytes is identical too. This module pins the
sha256 step and the chain-linking invariant; the Rust node (P1.S4) and TS
client (P2) reproduce `corpus/glade_hashes.json`.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from ..ir.load import load_schema
from ..wire import codec

_TAUT = Path(__file__).resolve().parents[3]
IR_PATH = _TAUT / "ir" / "glade.taut.py"
HASHES_PATH = _TAUT / "corpus" / "glade_hashes.json"


def op_hash(schema, op: dict) -> bytes:
    """sha256 of the op's canonical CBOR (the frozen glade codec)."""
    return hashlib.sha256(codec.encode(schema, "Op", op)).digest()


def _op(origin: str, seq: int, payload: bytes, prev: bytes | None) -> dict:
    return {"share": "sh", "glade_id": "g", "key": b"", "origin": origin, "seq": seq,
            "prev": prev, "lamport": seq, "refs": [], "shape": "value", "payload": payload}


def build_chain(schema, origin: str, n: int) -> list[dict]:
    """A linked run of `n` ops: each op's prev = hash of the previous op."""
    ops, prev = [], None
    for seq in range(n):
        op = _op(origin, seq, f"p{seq}".encode(), prev)
        ops.append(op)
        prev = op_hash(schema, op)
    return ops


def vectors(schema) -> list[dict]:
    """name -> op + expected hash. A 3-op chain (links verified) plus a fork at
    (a,0) that must hash differently (equivocation)."""
    chain = build_chain(schema, "a", 3)
    out = [{"name": f"chain/a{ i }", "op": _enc_op(op), "hash": op_hash(schema, op).hex()}
           for i, op in enumerate(chain)]
    fork = _op("a", 0, b"p0-fork", None)            # same (origin,seq) as chain/a0, different payload
    out.append({"name": "fork/a0", "op": _enc_op(fork), "hash": op_hash(schema, fork).hex()})
    return out


def _enc_op(op: dict) -> dict:
    return {"share": op["share"], "glade_id": op["glade_id"], "key": op["key"].hex(),
            "origin": op["origin"], "seq": op["seq"],
            "prev": op["prev"].hex() if op["prev"] else None,
            "lamport": op["lamport"], "shape": op["shape"], "payload": op["payload"].hex()}


def main() -> None:
    schema = load_schema(IR_PATH)
    out = vectors(schema)
    HASHES_PATH.write_text(json.dumps(out, indent=2) + "\n")
    print(f"wrote {len(out)} op-hash vectors to {HASHES_PATH}")


if __name__ == "__main__":
    main()
