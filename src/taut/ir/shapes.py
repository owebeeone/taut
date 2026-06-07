"""The delivery-shape registry — an OPEN, first-class set referenced by name in
the IR. **Shape is the sole method discriminator** (D22): a method is
`(name, in, out, shape)`, and `unary` is the degenerate "delivered once" member.
There is no separate `kind` axis — `kind`/`output`/`events` are derived from
`shape` + `out`, so they can never disagree (illegal states are unrepresentable).

Each shape is a validated point in the axes (payload / history / initiation /
writers) plus:
  - `events`: the shape's **out-slots** — the only slot names a method of this
    shape may bind in its `out` (for `unary` that's the single return, `value`).
  - `delivery`: `"once"` (request/response) or `"stream"`.

The set is **open by design**: adding a shape *is* adding a method-kind, so the
registry — not a sealed enum — is the extension point (`register_shape`). The one
honest caveat vs. plain data: a shape carries behaviour (delivery semantics +
per-target implementation), so "open" means open to *implemented* shapes, never
to arbitrary user-declared ones. Hardcoding a closed enum here would quietly
reintroduce protobuf's closed-taxonomy problem; this avoids it.

`snapshot_delta` and `crdt` are registered (contract surfaces) but unused by the
GripLab service — GripLab has no multi-writer feed. CRDT is wire/contract only;
no convergence engine is implied (build prompt §4).
"""

from __future__ import annotations

SHAPES: dict[str, dict] = {
    "unary": {
        "payload": "whole", "history": "none", "initiation": "pull",
        "writers": "single", "events": {"value"}, "delivery": "once",
    },
    "atom": {
        "payload": "whole-state", "history": "latest", "initiation": "pull|push",
        "writers": "single", "events": {"replace"}, "delivery": "stream",
    },
    "log": {
        "payload": "whole", "history": "append-only", "initiation": "pull|push",
        "writers": "source", "events": {"append"}, "delivery": "stream",
    },
    "stream": {
        "payload": "whole-or-delta", "history": "none", "initiation": "push",
        "writers": "source", "events": {"event"}, "delivery": "stream",
    },
    "swmr": {
        "payload": "delta", "history": "reconstructible", "initiation": "push",
        "writers": "single", "events": {"snapshot", "delta", "reset"}, "delivery": "stream",
    },
    "snapshot_delta": {
        "payload": "delta", "history": "reconstructible", "initiation": "push",
        "writers": "single", "events": {"snapshot", "delta"}, "delivery": "stream",
    },
    "crdt": {
        "payload": "ops", "history": "reconstructible", "initiation": "push-bidi",
        "writers": "multi-merge", "events": {"op", "sync"}, "delivery": "stream",
    },
}

ROLES: set[str] = {"out", "in", "ctl", "td", "hdl", "query", "dx"}


def is_streaming(shape: str) -> bool:
    """Whether `shape` is delivered as a stream (vs. once). The derived
    streaming-kind: `unary` (`delivery == "once"`) is the sole once-delivered shape."""
    return SHAPES.get(shape, {}).get("delivery", "stream") != "once"


def sole_slot(shape: str) -> str:
    """The single out-slot of a single-slot shape (so `out=` may be a bare type).
    Multi-slot shapes (swmr/snapshot_delta/crdt) must bind out with a {slot: type} map."""
    slots = SHAPES.get(shape, {}).get("events", set())
    if len(slots) != 1:
        raise ValueError(
            f"shape {shape!r} has slots {sorted(slots)}; bind out as a {{slot: type}} map"
        )
    return next(iter(slots))


def register_shape(name: str, spec: dict) -> None:
    """Extend the open shape set with a new *implemented* shape. `spec` must carry
    the axes plus `events` (out-slot names) and `delivery` ("once" | "stream").
    Adding a shape = adding a method-kind; implementing it means wiring its
    delivery semantics in each target. This is the single extension point — the
    set is never a sealed enum."""
    SHAPES[name] = spec

# Tag-space partition: app fields use tags below the band; infrastructure
# extensions (side-channels) use tags at/above it. Keeps app evolution and infra
# piggybacking from ever colliding.
BAND_START: int = 1 << 20  # 1048576
