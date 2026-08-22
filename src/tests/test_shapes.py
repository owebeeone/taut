"""Canonical shape rows are normalized and extension dispatch fails closed."""

import pytest

from taut.ir.shapes import SHAPES, ShapeSpec, is_streaming, register_shape, sole_slot


def extension_spec(name: str = "queue") -> ShapeSpec:
    return ShapeSpec(
        name=name,
        shape_class="engine",
        core=name,
        contract_version="v1",
        delivery="stream",
        events=frozenset({"item"}),
        operations=frozenset({"publish", "subscribe"}),
        payload="record",
        history="bounded",
        initiation="push",
        writers="single",
        ordering="scalar_sequence",
        retention="bounded_records",
        position="cursor",
        recovery="expire_below_floor",
        merge="none",
        lifecycle="mailbox_terminal",
    )


def test_catalogue_classifies_value_and_snapshot_delta():
    assert SHAPES["value"].shape_class == "engine"
    assert SHAPES["value"].operations == {"read", "set"}
    assert "watch" not in SHAPES["value"].operations
    profile = SHAPES["snapshot_delta"]
    assert profile.shape_class == "profile"
    assert profile.core == "swmr"
    assert profile.fixed_profile == {"recovery": "expire"}


def test_existing_export_axes_remain_additive_and_compatible():
    atom = SHAPES["atom"].to_json()
    assert atom["payload"] == "whole-state"
    assert atom["history"] == "latest"
    assert atom["initiation"] == "pull|push"
    assert atom["writers"] == "single"
    assert atom["class"] == "engine"
    assert atom["position"] == "version"


def test_unknown_shape_helpers_fail_closed():
    with pytest.raises(ValueError, match="unknown delivery shape"):
        is_streaming("message")
    with pytest.raises(ValueError, match="unknown delivery shape"):
        sole_slot("window")


def test_extension_registration_requires_validated_spec_and_capability():
    with pytest.raises(TypeError, match="ShapeSpec"):
        register_shape("queue", {"events": {"item"}}, implementation_capability="x")  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="implementation_capability"):
        register_shape("queue", extension_spec(), implementation_capability="")


def test_extension_registration_is_exact_and_non_overwriting():
    name = "test_queue_extension"
    spec = extension_spec(name)
    try:
        register_shape(name, spec, implementation_capability="tests/queue-adapter@v1")
        assert SHAPES[name] is spec
        with pytest.raises(ValueError, match="already registered"):
            register_shape(name, spec, implementation_capability="tests/queue-adapter@v1")
    finally:
        SHAPES.pop(name, None)
