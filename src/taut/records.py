"""Optional YIDL message records; no compiler or YIDL import on the stdlib path."""

from __future__ import annotations

import copy
import inspect
from functools import partial

FREEZE_METHOD = "_taut_freeze"


class FrozenDict(dict):
    """A detached dictionary whose regular mutation operations are disabled."""

    __slots__ = ()

    def __new__(cls, *args, **kwargs):
        result = dict.__new__(cls)
        dict.__init__(result, *args, **kwargs)
        return result

    def __init__(self, *args, **kwargs):
        pass

    def _blocked(self, *args, **kwargs):
        raise TypeError("frozen Taut map cannot be modified")

    __setitem__ = __delitem__ = clear = pop = popitem = setdefault = update = (
        __ior__
    ) = _blocked

    def copy(self):
        return self

    __copy__ = copy

    def __deepcopy__(self, memo):
        result = dict.__new__(type(self))
        memo[id(self)] = result
        for key, value in self.items():
            dict.__setitem__(
                result, copy.deepcopy(key, memo), copy.deepcopy(value, memo)
            )
        return result

    def __reduce__(self):
        return type(self), (dict(self),)


def _backend():
    try:
        import yidl_dataclass
    except ImportError as error:
        raise ImportError(
            "YIDL records require yidl-dataclass with configurable freeze_method support"
        ) from error
    if "freeze_method" not in inspect.signature(yidl_dataclass.dataclass).parameters:
        raise ImportError(
            "Installed yidl-dataclass lacks freeze_method support; install the compatible prototype/release"
        )
    return yidl_dataclass


def field(**options):
    """Field declaration owned by this optional Taut backend."""
    return _backend().field(**options)


def taut_dataclass(cls=None, /, *, slots=True):
    """Configure every YIDL message consistently behind Taut's decorator."""
    if slots is not True:
        raise ValueError("Taut YIDL records require slots=True")

    def decorate(declaration):
        result = _backend().dataclass(
            declaration, slots=True, freezable=True, freeze_method=FREEZE_METHOD
        )
        result.__taut_record_backend__ = "yidl"
        return result

    return decorate if cls is None else decorate(cls)


def has_record_field(cls, attribute):
    """Recognize the selected backend's real generated property/storage pair."""
    if getattr(cls, "__taut_record_backend__", None) != "yidl":
        return False
    definition = getattr(cls, "__yidl_dataclass_definition__", None)
    if (
        definition is None
        or not definition.options.freezable
        or definition.options.freeze_method != FREEZE_METHOD
    ):
        return False
    slots = {
        name for base in cls.__mro__ for name in base.__dict__.get("__slots__", ())
    }
    return any(
        item.name == attribute
        and item.kind.stored
        and item.store_name in slots
        and isinstance(inspect.getattr_static(cls, attribute, None), property)
        for item in definition.fields
    )


def is_frozen_record(value):
    # This adapter deliberately tracks the selected YIDL backend's state ABI.
    return (
        getattr(type(value), "__taut_record_backend__", None) == "yidl"
        and getattr(value, "_y_dc_frozen", False) is True
    )


def freeze_field(spec):
    """Bind a compiler-projected type shape without importing the compiler."""
    return partial(_freeze_value, spec)


def _freeze_value(spec, value):
    if value is None:
        return None
    kind = spec[0]
    if kind == "message":
        if getattr(type(value), "__taut_record_backend__", None) != "yidl":
            raise TypeError(
                "deep freeze requires a Taut YIDL child record; regenerate the dependency with --python-records yidl"
            )
        getattr(value, FREEZE_METHOD)()
    elif kind == "list":
        if type(value) not in (list, tuple):
            raise TypeError("deep freeze expects a list field")
        return tuple(_freeze_value(spec[1], child) for child in value)
    elif kind == "map":
        if type(value) not in (dict, FrozenDict):
            raise TypeError("deep freeze expects a map field")
        return FrozenDict(
            (key, _freeze_value(spec[1], child)) for key, child in value.items()
        )
    return value
