"""Options: typed properties declared with a taut schema, as in protobuf (D27, TautOptions.md).

One definition per option (OPT-D1) in the registry `OPTIONS`. The `option` namespace reaches each
option's typed constructor, which builds a declared `OptionValue` (OPT-L1). The model stores what
each level declared (OPT-L3); `effective()` computes the value an element sees (OPT-D3).
Imports only `model.py`.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from .model import Schema

# Where an option may be declared: file, message, field and enum; enum_value, service and method
# are reserved, so that their first option needs no new IR version (OPT-I2).
LEVELS = ("file", "message", "field", "enum", "enum_value", "service", "method")

# What an option's value changes (OPT-D1, OPT-D2): what decodes (wire), the generated code only
# (codegen), nothing (metadata), or what readers compute from the same bytes (semantic, question 7).
CLASSES = ("wire", "codegen", "metadata", "semantic")

DEFAULT_MAX_DEPTH = 32               # max_depth where no level declares one (OPT-D5)
MAX_DEPTH_CEILING = 128              # a runtime constant, not an option (OPT-D5)
MAX_ENCODED_LEN_CEILING = 2**31 - 1  # on declared values, not the runtimes' inputs (OPT-D6)


@dataclass(frozen=True)
class OptionDef:
    """One option's definition (OPT-D1)."""

    name: str                   # "max_depth"; custom options, later, "ns.name"
    value_type: type            # int, bool or str
    levels: frozenset[str]      # where it may be declared, among LEVELS
    default: object             # the effective value where no level declares one (None: no value)
    klass: str                  # one of CLASSES
    inherits: tuple[str, ...]   # levels consulted, most specific first; () for none
    targets: frozenset[str] | None = None   # codegen: the generators it concerns; None for all


@dataclass(frozen=True)
class OptionValue:
    """A declared option, built by its typed constructor: `option.max_depth(16)` (OPT-D1)."""

    name: str
    value: object


OPTIONS: dict[str, OptionDef] = {
    "max_depth": OptionDef("max_depth", int, frozenset({"file", "message"}),
                           default=DEFAULT_MAX_DEPTH, klass="wire", inherits=("message", "file")),
    "max_encoded_len": OptionDef("max_encoded_len", int, frozenset({"file", "message"}),
                                 default=None, klass="wire", inherits=("message", "file")),
}

# The inclusive range of an int option's declared values (OPT-D5, OPT-D6).
_RANGES: dict[str, tuple[int, int]] = {
    "max_depth": (1, MAX_DEPTH_CEILING),
    "max_encoded_len": (1, MAX_ENCODED_LEN_CEILING),
}


def _unknown(name: str) -> str:
    return f"unknown option {name!r}; known options: {', '.join(OPTIONS)}"


def _definition(name: str) -> OptionDef:
    defn = OPTIONS.get(name)
    if defn is None:
        raise KeyError(_unknown(name))
    return defn


def check_value(name: str, value: object) -> None:
    """Refuse a value that option `name` cannot take (OPT-D5, OPT-D6): another type, a bool where an
    int is due, or a value out of range. Each typed constructor runs it; so may any later check of
    values that no constructor built. An unregistered name raises `KeyError`."""
    defn = _definition(name)
    if not isinstance(value, defn.value_type) or (
        isinstance(value, bool) and defn.value_type is not bool
    ):
        raise TypeError(f"option {name} takes {defn.value_type.__name__} values, not {value!r}")
    bounds = _RANGES.get(name)
    if bounds is not None and not (isinstance(value, int) and bounds[0] <= value <= bounds[1]):
        low, high = bounds
        raise ValueError(f"option {name} takes a value from {low} to {high}, not {value!r}")


def _constructor(defn: OptionDef) -> Callable[[object], OptionValue]:
    def construct(value: object, /) -> OptionValue:
        check_value(defn.name, value)
        return OptionValue(defn.name, value)

    construct.__name__ = defn.name
    construct.__qualname__ = f"option.{defn.name}"
    return construct


class _OptionNamespace:
    """`option.<name>(value)`: each registered option's typed constructor, after `Ref`'s pattern
    (OPT-L1). An unknown name fails at import; calling `option(...)` itself is reserved for custom
    options (question 6)."""

    def __call__(self, *args: object, **kwargs: object) -> OptionValue:
        raise TypeError('custom options are reserved: option("ns.name", value) is not available; '
                        f"use option.<name>(value), one of: {', '.join(OPTIONS)}")

    def __getattr__(self, name: str) -> Callable[[object], OptionValue]:
        defn = OPTIONS.get(name)
        if defn is None:
            raise AttributeError(_unknown(name))
        return _constructor(defn)


option = _OptionNamespace()


def _enclosing(schema: Schema, message: str | None) -> dict[str, dict[str, object]]:
    """The declarations at each level that lexically encloses the element, its own included: a
    message sits in its file only (OPT-D3)."""
    if message is None:
        return {"file": schema.options}
    msg = schema.messages.get(message)
    if msg is None:
        raise KeyError(f"unknown message {message!r}")
    return {"message": msg.options, "file": schema.options}


def _resolve(defn: OptionDef, declared: dict[str, dict[str, object]]) -> object:
    for level in defn.inherits:
        values = declared.get(level, {})
        if defn.name in values:
            return values[defn.name]
    return defn.default


def effective(schema: Schema, name: str, *, message: str | None = None) -> object:
    """Option `name`'s effective value at `message`, or at file level for None (OPT-D3): the value
    declared at the first level of its `inherits` that declares one, walking out from the element,
    else its default. Enclosure is lexical: a message used by another inherits nothing from it.
    An unregistered option or an unknown message raises `KeyError`."""
    return _resolve(_definition(name), _enclosing(schema, message))


def effective_map(schema: Schema, *, message: str | None = None) -> dict[str, object]:
    """Every wire and codegen option defined for the level, message or (for None) file, resolved,
    defaults included (OPT-I2), in registry order."""
    declared = _enclosing(schema, message)
    level = "file" if message is None else "message"
    return {
        name: _resolve(defn, declared)
        for name, defn in OPTIONS.items()
        if defn.klass in ("wire", "codegen") and level in defn.levels
    }
