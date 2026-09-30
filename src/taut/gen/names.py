"""The names a generator's code declares where a schema's names are declared too (TautV010Plan.md,
step E1a).

Each generator keeps its reservations beside it, and `ir/validate.py` refuses a schema that meets
one, naming the target:
  - `RESERVED_FIELD_NAMES` and `RESERVED_TYPE_NAMES` map a name to why the target cannot take it:
    a member, runtime or standard name, or a local, that the name would redeclare, hide or be
    hidden by;
  - `name_clashes(schema)` finds what no fixed set holds: a clash between two of the schema's
    names, or a family of names. A clash is `(where, kind, why)`: `where` names the field
    (`Msg.f`), message (`Msg`) or enum (`enum E`) that `kind` says it is.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping

Clash = tuple[str, str, str]


def scope_clashes(generated: Iterable[tuple[str, str, str]], reserved: Mapping[str, str]) -> list[Clash]:
    """Where the names a generator declares in one scope for a schema's messages and enums meet.

    `generated` is each such name with the declaration it is made for, `(name, where, kind)`:
    its own name and the names derived from it. A name made twice is reported on its second
    maker, and a name in `reserved` (the scope's runtime and standard names) on its maker."""
    makers: dict[str, str] = {}
    clashes: list[Clash] = []
    for name, where, kind in generated:
        if name in makers:
            clashes.append((where, kind, f"the generated {name} is also {makers[name]}'s"))
        elif name in reserved:
            clashes.append((where, kind, f"the generated {name} is {reserved[name]}"))
        else:
            makers[name] = where
    return clashes
