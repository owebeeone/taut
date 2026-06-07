"""The closed delivery-shape set — built into taut, referenced by name in the IR.

Each shape is a validated point in the axes (payload / history / initiation /
writers). `events` is the derived streaming-kind: the only event names a
server_stream of that shape may emit. The validator rejects anything outside the
set and any event not in the shape's `events`. Extension = deliberately adding a
new *implemented* shape here, never exposing raw axis combinations.

`snapshot_delta` and `crdt` are registered (contract surfaces) but unused by the
GripLab service — GripLab has no multi-writer feed. CRDT is wire/contract only;
no convergence engine is implied (build prompt §4).
"""

from __future__ import annotations

SHAPES: dict[str, dict] = {
    "atom": {
        "payload": "whole-state", "history": "latest", "initiation": "pull|push",
        "writers": "single", "events": {"replace"},
    },
    "log": {
        "payload": "whole", "history": "append-only", "initiation": "pull|push",
        "writers": "source", "events": {"append"},
    },
    "stream": {
        "payload": "whole-or-delta", "history": "none", "initiation": "push",
        "writers": "source", "events": {"event"},
    },
    "swmr": {
        "payload": "delta", "history": "reconstructible", "initiation": "push",
        "writers": "single", "events": {"snapshot", "delta", "reset"},
    },
    "snapshot_delta": {
        "payload": "delta", "history": "reconstructible", "initiation": "push",
        "writers": "single", "events": {"snapshot", "delta"},
    },
    "crdt": {
        "payload": "ops", "history": "reconstructible", "initiation": "push-bidi",
        "writers": "multi-merge", "events": {"op", "sync"},
    },
}

ROLES: set[str] = {"out", "in", "ctl", "td", "hdl", "query", "dx"}
KINDS: set[str] = {"unary", "server_stream"}

# Tag-space partition: app fields use tags below the band; infrastructure
# extensions (side-channels) use tags at/above it. Keeps app evolution and infra
# piggybacking from ever colliding.
BAND_START: int = 1 << 20  # 1048576
