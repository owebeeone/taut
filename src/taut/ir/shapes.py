"""Canonical Taut interaction/delivery-shape registry.

``shape`` remains the sole method discriminator in IR v1. Each active name is a
validated semantic row classified as an interaction, engine, or fixed engine
profile. Registry recognition is not runtime support: every generated client or
adapter must advertise and check its own exact capabilities.

The catalogue is closed to schema authors. Compiler extensions may add a row
only with complete semantic metadata and an implementation-capability identity;
an arbitrary string can therefore never acquire implicit streaming behaviour.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Iterable, Literal, Mapping

ShapeClass = Literal["interaction", "engine", "profile"]
Delivery = Literal["once", "stream"]


@dataclass(frozen=True)
class ShapeSpec:
    """One normalized, exportable semantic catalogue row."""

    name: str
    shape_class: ShapeClass
    core: str | None
    contract_version: str
    delivery: Delivery
    events: frozenset[str]
    operations: frozenset[str]
    payload: str
    history: str
    initiation: str
    writers: str
    ordering: str
    retention: str
    position: str
    recovery: str
    merge: str
    lifecycle: str
    fixed_profile: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "events", frozenset(self.events))
        object.__setattr__(self, "operations", frozenset(self.operations))
        object.__setattr__(self, "fixed_profile", MappingProxyType(dict(self.fixed_profile)))
        _validate_spec(self)

    def to_json(self) -> dict:
        """Return the stable JSON form embedded in exported IR."""
        return {
            "name": self.name,
            "class": self.shape_class,
            "core": self.core,
            "contract_version": self.contract_version,
            "fixed_profile": dict(self.fixed_profile),
            "delivery": self.delivery,
            "events": sorted(self.events),
            "operations": sorted(self.operations),
            "payload": self.payload,
            "history": self.history,
            "initiation": self.initiation,
            "writers": self.writers,
            "ordering": self.ordering,
            "retention": self.retention,
            "position": self.position,
            "recovery": self.recovery,
            "merge": self.merge,
            "lifecycle": self.lifecycle,
        }


def _validate_spec(spec: ShapeSpec) -> None:
    if not spec.name or not spec.name.replace("_", "").isalnum():
        raise ValueError(f"invalid shape name {spec.name!r}")
    if spec.shape_class not in ("interaction", "engine", "profile"):
        raise ValueError(f"shape {spec.name!r}: invalid class {spec.shape_class!r}")
    if spec.delivery not in ("once", "stream"):
        raise ValueError(f"shape {spec.name!r}: invalid delivery {spec.delivery!r}")
    if not spec.events or any(not isinstance(e, str) or not e for e in spec.events):
        raise ValueError(f"shape {spec.name!r}: events must be non-empty names")
    if not spec.operations or any(not isinstance(o, str) or not o for o in spec.operations):
        raise ValueError(f"shape {spec.name!r}: operations must be non-empty names")

    semantic = {
        "contract_version": spec.contract_version,
        "payload": spec.payload,
        "history": spec.history,
        "initiation": spec.initiation,
        "writers": spec.writers,
        "ordering": spec.ordering,
        "retention": spec.retention,
        "position": spec.position,
        "recovery": spec.recovery,
        "merge": spec.merge,
        "lifecycle": spec.lifecycle,
    }
    missing = [name for name, value in semantic.items() if not isinstance(value, str) or not value]
    if missing:
        raise ValueError(f"shape {spec.name!r}: missing semantic metadata {missing}")

    if spec.shape_class == "interaction":
        if spec.core is not None:
            raise ValueError(f"interaction {spec.name!r}: core must be None")
        if spec.fixed_profile:
            raise ValueError(f"interaction {spec.name!r}: fixed_profile is not applicable")
    elif spec.shape_class == "engine":
        if spec.core != spec.name:
            raise ValueError(f"engine {spec.name!r}: core must equal its public name")
        if spec.fixed_profile:
            raise ValueError(f"engine {spec.name!r}: fixed_profile is only valid on profiles")
    else:
        if not spec.core or spec.core == spec.name:
            raise ValueError(f"profile {spec.name!r}: core must name a distinct engine")
        if not spec.fixed_profile:
            raise ValueError(f"profile {spec.name!r}: fixed_profile must not be empty")


def _spec(
    name: str,
    shape_class: ShapeClass,
    core: str | None,
    contract_version: str,
    delivery: Delivery,
    events: Iterable[str],
    operations: Iterable[str],
    *,
    payload: str,
    history: str,
    initiation: str,
    writers: str,
    ordering: str,
    retention: str,
    position: str,
    recovery: str,
    merge: str,
    lifecycle: str,
    fixed_profile: Mapping[str, str] | None = None,
) -> ShapeSpec:
    return ShapeSpec(
        name=name,
        shape_class=shape_class,
        core=core,
        contract_version=contract_version,
        delivery=delivery,
        events=frozenset(events),
        operations=frozenset(operations),
        payload=payload,
        history=history,
        initiation=initiation,
        writers=writers,
        ordering=ordering,
        retention=retention,
        position=position,
        recovery=recovery,
        merge=merge,
        lifecycle=lifecycle,
        fixed_profile=fixed_profile or {},
    )


SHAPES: dict[str, ShapeSpec] = {
    "unary": _spec(
        "unary", "interaction", None, "v1", "once", {"value"}, {"call"},
        payload="whole", history="none", initiation="pull", writers="single",
        ordering="none", retention="none",
        position="none", recovery="not_applicable", merge="none",
        lifecycle="request_response",
    ),
    "value": _spec(
        "value", "engine", "value", "v0", "once", {"value"}, {"read", "set"},
        payload="whole-state", history="materialized", initiation="pull|push",
        writers="multi-attributed", ordering="lww_lamport_origin",
        retention="materialized_winner", position="op_identity", recovery="materialized_read",
        merge="attributed_lww", lifecycle="persistent_register",
    ),
    "atom": _spec(
        "atom", "engine", "atom", "v1", "stream", {"replace"},
        {"read", "replace", "subscribe"}, payload="whole-state", history="latest",
        initiation="pull|push", writers="single",
        ordering="scalar_version", retention="latest", position="version",
        recovery="latest_refresh", merge="sequential_overwrite", lifecycle="mailbox_terminal",
    ),
    "log": _spec(
        "log", "engine", "log", "v1", "stream", {"append"},
        {"append", "read", "subscribe"}, payload="whole", history="append-only",
        initiation="pull|push", writers="source",
        ordering="scalar_sequence", retention="bounded_records", position="cursor",
        recovery="expire_below_floor", merge="none", lifecycle="mailbox_terminal",
    ),
    "stream": _spec(
        "stream", "engine", "stream", "v1", "stream", {"event"},
        {"publish", "subscribe"}, payload="whole-or-delta", history="none",
        initiation="push", writers="source",
        ordering="live_session", retention="none", position="none",
        recovery="none", merge="none", lifecycle="live_terminal",
    ),
    "swmr": _spec(
        "swmr", "engine", "swmr", "v1", "stream", {"snapshot", "delta", "reset"},
        {"publish_snapshot", "publish_delta", "read", "reset", "subscribe"},
        payload="delta", history="reconstructible", initiation="push", writers="single",
        ordering="scalar_epoch_sequence",
        retention="snapshot_bounded_deltas", position="epoch_cursor",
        recovery="in_band_reset_repair", merge="sequential_single_writer",
        lifecycle="mailbox_terminal",
    ),
    "snapshot_delta": _spec(
        "snapshot_delta", "profile", "swmr", "v1", "stream",
        {"snapshot", "delta"}, {"publish_snapshot", "publish_delta", "read", "subscribe"},
        payload="delta", history="reconstructible", initiation="push", writers="single",
        ordering="scalar_epoch_sequence",
        retention="snapshot_bounded_deltas", position="epoch_cursor",
        recovery="expire", merge="sequential_single_writer", lifecycle="mailbox_terminal",
        fixed_profile={"recovery": "expire"},
    ),
    "crdt": _spec(
        "crdt", "engine", "crdt", "v1", "stream", {"op", "sync"},
        {"apply", "bootstrap", "read", "sync"}, payload="opaque-ops", history="reconstructible",
        initiation="push-bidi", writers="multi-merge", ordering="causal_per_origin",
        retention="convergence_safe",
        position="causal_vector", recovery="anti_entropy", merge="profile_defined_convergent",
        lifecycle="replica_sync",
    ),
    "text_crdt": _spec(
        "text_crdt", "profile", "crdt", "v1", "stream", {"op", "sync"},
        {"insert", "delete", "bootstrap", "read", "sync"}, payload="text-ops",
        history="reconstructible", initiation="push-bidi", writers="multi-merge",
        ordering="causal_per_origin", retention="convergence_safe",
        position="causal_vector", recovery="anti_entropy",
        merge="stable_item_text", lifecycle="replica_sync",
        fixed_profile={"payload": "text_crdt.profile/v1"},
    ),
}

# A capability identity records which compiler/adapter extension supplied a
# semantic row. It is intentionally not exported as semantic shape metadata and
# never means that every generated target can execute the shape.
_REGISTRATION_CAPABILITIES: dict[str, str] = {
    name: f"taut.ir/catalog/{name}@{spec.contract_version}" for name, spec in SHAPES.items()
}

ROLES: set[str] = {"out", "in", "ctl", "td", "hdl", "query", "dx"}


def shape_spec(shape: str) -> ShapeSpec:
    """Resolve an active shape or fail closed."""
    try:
        return SHAPES[shape]
    except KeyError as exc:
        raise ValueError(f"unknown delivery shape {shape!r}") from exc


def is_streaming(shape: str) -> bool:
    """Whether ``shape`` is streamed. Unknown names are errors, never streams."""
    return shape_spec(shape).delivery == "stream"


def sole_slot(shape: str) -> str:
    """Return the single out-slot, rejecting unknown and multi-slot shapes."""
    slots = shape_spec(shape).events
    if len(slots) != 1:
        raise ValueError(
            f"shape {shape!r} has slots {sorted(slots)}; bind out as a {{slot: type}} map"
        )
    return next(iter(slots))


def register_shape(name: str, spec: ShapeSpec, *, implementation_capability: str) -> None:
    """Register a compiler extension with explicit semantics and capability.

    Runtime adapters must still perform their own exact capability check. The
    registration is rejected when the name is already active, the row/name do
    not agree, its profile core is unavailable, or capability identity is absent.
    """
    if name in SHAPES:
        raise ValueError(f"shape {name!r} is already registered")
    if not isinstance(spec, ShapeSpec):
        raise TypeError("spec must be a validated ShapeSpec")
    if spec.name != name:
        raise ValueError(f"shape registry key {name!r} does not match spec name {spec.name!r}")
    if not isinstance(implementation_capability, str) or not implementation_capability.strip():
        raise ValueError(f"shape {name!r}: implementation_capability must be a non-empty identity")
    if spec.shape_class == "profile":
        core = SHAPES.get(spec.core or "")
        if core is None or core.shape_class != "engine":
            raise ValueError(f"profile {name!r}: unknown engine core {spec.core!r}")
    SHAPES[name] = spec
    _REGISTRATION_CAPABILITIES[name] = implementation_capability


# Tag-space partition: app fields use tags below the band; infrastructure
# extensions (side-channels) use tags at/above it. Keeps app evolution and infra
# piggybacking from ever colliding.
BAND_START: int = 1 << 20  # 1048576
