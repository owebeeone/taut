"""Glade fold reference + conformance oracle (GLP-0005, P0.S5).

The fold turns a *set* of attributed ops (the glade Op envelope) into
materialized state. M-LIMP needs two folds; both are pure functions of the
op-set, so convergence is guaranteed when every replica folds the same set:

  - `value` (lww register): whole-payload last-writer-wins. Winner = max by
    `(lamport, origin)` — the faithful tiebreak (GladeSubstrateV1 §2), the
    glade analogue of taut ReferenceDoc's `(seq, actor)` lww stamp.
  - `log` (append): deterministic causal interleave. Order by
    `(lamport, origin, seq)`; trivially convergent.

Both dedup by `(origin, seq)` (idempotent delivery). A second op at an existing
`(origin, seq)` with a *different* payload/prev is **equivocation** — a forked
per-origin chain (GQ-9): detected and rejected, never folded.

This Python reference is the cross-language oracle: it emits
`corpus/glade_folds.json`, which the Rust node (P1) and TS client (P2) fold
implementations must reproduce — same discipline as the wire corpus.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_TAUT = Path(__file__).resolve().parents[3]
FOLDS_PATH = _TAUT / "corpus" / "glade_folds.json"


class Equivocation(Exception):
    """A forked per-origin chain: two ops share (origin, seq) but differ."""


def _dedup(ops: list[dict]) -> list[dict]:
    """Drop exact duplicates by (origin, seq); raise on equivocation."""
    seen: dict[tuple[str, int], dict] = {}
    for op in ops:
        k = (op["origin"], op["seq"])
        prior = seen.get(k)
        if prior is None:
            seen[k] = op
        elif prior.get("payload") != op.get("payload") or prior.get("prev") != op.get("prev"):
            raise Equivocation(f"forked chain at {k}")
        # else: exact duplicate — idempotent, ignore
    return list(seen.values())


def fold_value(ops: list[dict]) -> Any:
    """Whole-value lww. Returns the winning payload, or None for the empty set."""
    live = _dedup(ops)
    if not live:
        return None
    return max(live, key=lambda o: (o["lamport"], o["origin"]))["payload"]


def fold_log(ops: list[dict]) -> list:
    """Append log. Returns payloads in deterministic (lamport, origin, seq) order."""
    live = _dedup(ops)
    live.sort(key=lambda o: (o["lamport"], o["origin"], o["seq"]))
    return [o["payload"] for o in live]


def is_equivocation(ops: list[dict]) -> bool:
    try:
        _dedup(ops)
        return False
    except Equivocation:
        return True


# --- conformance vectors (hand-authored; expected outputs reviewed) -----------

def _op(origin: str, seq: int, lamport: int, payload: bytes, prev: bytes | None = None) -> dict:
    return {"origin": origin, "seq": seq, "lamport": lamport, "prev": prev, "payload": payload}


def vectors() -> list[dict]:
    """Each case: name, fold, ops, and the hand-reviewed expected result.
    Covers concurrent writes, lamport/origin tiebreaks, out-of-order arrival,
    duplicate delivery, and equivocation (detection, not a fold result)."""
    a1 = _op("a", 1, 1, b"A1")
    b1 = _op("b", 1, 2, b"B1")            # higher lamport than a1
    a2 = _op("a", 2, 2, b"A2")            # same lamport as b1 -> origin breaks tie
    return [
        # value (lww)
        {"name": "value/single", "fold": "value", "ops": [a1], "expect": b"A1"},
        {"name": "value/concurrent-lamport", "fold": "value",
         "ops": [a1, b1], "expect": b"B1"},                       # B1 wins on lamport
        {"name": "value/tiebreak-origin", "fold": "value",
         "ops": [a2, b1], "expect": b"B1"},                       # lamport tie -> "b" > "a"
        {"name": "value/out-of-order", "fold": "value",
         "ops": [b1, a1], "expect": b"B1"},                       # order-independent
        {"name": "value/duplicate", "fold": "value",
         "ops": [a1, b1, a1, b1], "expect": b"B1"},               # idempotent
        {"name": "value/empty", "fold": "value", "ops": [], "expect": None},
        # log (append, ordered)
        {"name": "log/order", "fold": "log",
         "ops": [a1, b1], "expect": [b"A1", b"B1"]},
        {"name": "log/tiebreak-origin", "fold": "log",
         "ops": [a2, b1], "expect": [b"A2", b"B1"]},              # lamport tie -> "a"<"b"
        {"name": "log/out-of-order", "fold": "log",
         "ops": [b1, a2, a1], "expect": [b"A1", b"A2", b"B1"]},   # (1,a,1)<(2,a,2)<(2,b,1)
        {"name": "log/duplicate", "fold": "log",
         "ops": [a1, b1, a1], "expect": [b"A1", b"B1"]},          # dup dropped
        # equivocation: same (origin,seq), different payload -> detected
        {"name": "equiv/forked", "fold": "equiv",
         "ops": [a1, _op("a", 1, 1, b"A1-fork")], "expect": True},
        {"name": "equiv/clean", "fold": "equiv",
         "ops": [a1, b1, a1], "expect": False},
    ]


def run(case: dict) -> Any:
    if case["fold"] == "value":
        return fold_value(case["ops"])
    if case["fold"] == "log":
        return fold_log(case["ops"])
    if case["fold"] == "equiv":
        return is_equivocation(case["ops"])
    raise ValueError(f"unknown fold {case['fold']!r}")


def _enc(v: Any) -> Any:
    """JSON-safe: bytes -> hex, lists recurse, None/bool pass through."""
    if isinstance(v, bytes):
        return v.hex()
    if isinstance(v, list):
        return [_enc(x) for x in v]
    return v


def _enc_op(op: dict) -> dict:
    return {"origin": op["origin"], "seq": op["seq"], "lamport": op["lamport"],
            "prev": op["prev"].hex() if op["prev"] else None,
            "payload": op["payload"].hex()}


def main() -> None:
    out = [{"name": c["name"], "fold": c["fold"],
            "ops": [_enc_op(o) for o in c["ops"]], "expect": _enc(c["expect"])}
           for c in vectors()]
    FOLDS_PATH.write_text(json.dumps(out, indent=2) + "\n")
    print(f"wrote {len(out)} fold vectors to {FOLDS_PATH}")


if __name__ == "__main__":
    main()
