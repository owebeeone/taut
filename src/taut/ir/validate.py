"""The IR validator — coherence checks that make the IR trustworthy as data.

Possible *because* the IR is declarative (not Turing-complete): every reference
resolves, tags are unique, and every service method is coherent with the closed
delivery-shape set. Returns a list of human-readable errors (empty == valid).

This is the gate the build prompt calls for: reject incoherent shape/axis
combinations and anything outside the closed set, before any mechanism is derived.

Options (TautOptions.md OPT-L4): every declared option is registered, sits at one of
its levels and has a value its constructor would take, and every root's effective
bounds lie between its floors and the ceilings. `lint` returns the warnings tautc
SHOULD print (OPT-D4, OPT-D5), which never make a schema invalid.
"""

from __future__ import annotations

from .model import EnumRef, ListOf, MapOf, MsgRef, Scalar, Schema, TypeRef, is_presence
from .options import (
    LEVELS,
    MAX_DEPTH_CEILING,
    OPTIONS,
    check_value,
    effective,
    nesting,
    root_effective,
    roots,
    smallest_encoding,
)
from .shapes import BAND_START, ROLES, SHAPES

# The options a decode call takes from its root (OPT-D4): lint follows one a message declares
# into the roots that embed that message.
_BOUNDS = ("max_depth", "max_encoded_len")


def validate(schema: Schema) -> list[str]:
    errors: list[str] = []

    def check_ref(t: TypeRef, ctx: str) -> None:
        if isinstance(t, Scalar):
            if t.kind not in ("int", "str", "bytes", "bool", "float"):
                errors.append(f"{ctx}: unknown scalar {t.kind!r}")
        elif isinstance(t, EnumRef):
            if t.name not in schema.enums:
                errors.append(f"{ctx}: dangling enum ref {t.name!r}")
        elif isinstance(t, MsgRef):
            if t.name not in schema.messages:
                errors.append(f"{ctx}: dangling message ref {t.name!r}")
        elif isinstance(t, ListOf):
            check_ref(t.elem, ctx)
        elif isinstance(t, MapOf):
            if not (isinstance(t.key, Scalar) and t.key.kind in ("int", "str", "bool")):
                errors.append(f"{ctx}: map key must be int/str/bool, got {t.key!r}")
            if isinstance(t.value, (ListOf, MapOf)):
                errors.append(f"{ctx}: map value cannot be a list or map ({t.value!r})")
            check_ref(t.key, ctx)
            check_ref(t.value, ctx)
        else:
            errors.append(f"{ctx}: unknown type ref {t!r}")

    # --- messages ---
    for m in schema.messages.values():
        tags: set[int] = set()
        reserved_tags = set(m.reserved_tags)
        reserved_names = set(m.reserved_names)
        for f in m.fields:
            if f.tag <= 0:
                errors.append(f"{m.name}.{f.name}: tag must be positive")
            if f.tag >= BAND_START:
                errors.append(f"{m.name}.{f.name}: tag {f.tag} is in the extension band (>= {BAND_START})")
            if f.tag in tags:
                errors.append(f"{m.name}.{f.name}: duplicate tag {f.tag}")
            tags.add(f.tag)
            if f.tag in reserved_tags:
                errors.append(f"{m.name}.{f.name}: uses reserved tag {f.tag}")
            if f.name in reserved_names:
                errors.append(f"{m.name}.{f.name}: uses reserved name {f.name!r}")
            if f.name.startswith("wire_"):
                errors.append(f"{m.name}.{f.name}: the 'wire_' prefix is reserved by taut "
                              "(forward-compat residual field)")
            check_ref(f.type, f"{m.name}.{f.name}")
            if not is_presence(f.optional):
                errors.append(f"{m.name}.{f.name}: optional must be False, True or MISSING_OK, "
                              f"not {f.optional!r}")
            if f.merge is not None:
                if f.merge not in ("lww", "counter"):
                    errors.append(f"{m.name}.{f.name}: unknown CRDT merge {f.merge!r} (v1: lww | counter)")
                elif not isinstance(f.type, Scalar):
                    errors.append(f"{m.name}.{f.name}: CRDT merge only allowed on scalar fields")
                elif f.merge == "counter" and f.type.kind != "int":
                    errors.append(f"{m.name}.{f.name}: counter merge requires an int field")
        if m.next_id is not None:
            if m.next_id <= 0:
                errors.append(f"{m.name}: next_id must be positive")
            for t in tags | reserved_tags:
                if t >= m.next_id:
                    errors.append(f"{m.name}: tag {t} >= next_id {m.next_id}")

    # --- enums ---
    for e in schema.enums.values():
        if len(set(e.members.values())) != len(e.members):
            errors.append(f"enum {e.name}: duplicate wire values")

    # --- extensions (side-channels in the band) ---
    ext_tags: set[int] = set()
    for ext in schema.extensions:
        if ext.message not in schema.messages:
            errors.append(f"extension: dangling message ref {ext.message!r}")
        if ext.tag < BAND_START:
            errors.append(f"extension {ext.message}: tag {ext.tag} below the band (< {BAND_START})")
        if ext.tag in ext_tags:
            errors.append(f"extension: duplicate tag {ext.tag}")
        ext_tags.add(ext.tag)

    # --- services ---
    for svc in schema.services.values():
        seen: set[str] = set()
        for meth in svc.methods:
            ctx = f"{svc.name}.{meth.name}"
            if meth.name in seen:
                errors.append(f"{ctx}: duplicate method")
            seen.add(meth.name)
            if meth.role not in ROLES:
                errors.append(f"{ctx}: unknown role {meth.role!r}")
            for pn, pt in meth.params:
                check_ref(pt, f"{ctx} param {pn}")

            # shape is the sole discriminator; `out` binds the shape's slots.
            if meth.shape not in SHAPES:
                errors.append(f"{ctx}: unknown delivery shape {meth.shape!r}")
            else:
                allowed = SHAPES[meth.shape].events
                if not meth.out:
                    errors.append(
                        f"{ctx}: method must bind out (slots for {meth.shape!r}: "
                        f"{sorted(allowed)})"
                    )
                bound: set[str] = set()
                for slot, t in meth.out:
                    if slot not in allowed:
                        errors.append(
                            f"{ctx}: out slot {slot!r} not allowed for shape "
                            f"{meth.shape!r} (allowed: {sorted(allowed)})"
                        )
                    if slot in bound:
                        errors.append(f"{ctx}: duplicate out slot {slot!r}")
                    bound.add(slot)
                    check_ref(t, f"{ctx} out[{slot}]")

    # --- options (OPT-L4) ---
    errors.extend(_declaration_errors(schema))
    errors.extend(_root_errors(schema))

    return errors


def validate_or_raise(schema: Schema) -> None:
    errors = validate(schema)
    if errors:
        raise ValueError("invalid IR:\n  " + "\n  ".join(errors))


def _declared(schema: Schema) -> list[tuple[str, str, dict[str, object]]]:
    """Each level's declared options (OPT-L3): where they sit, the level, and the values."""
    found = [("file", "file", schema.options)]
    for m in schema.messages.values():
        found.append((m.name, "message", m.options))
        found.extend((f"{m.name}.{f.name}", "field", f.options) for f in m.fields)
    found.extend((f"enum {e.name}", "enum", e.options) for e in schema.enums.values())
    return found


def _declaration_errors(schema: Schema) -> list[str]:
    """Every declared option is registered (OPT-F1), sits at one of its definition's levels, and
    has a value its constructor would take: a model loaded from JSON or built by hand never ran
    one. Each check stands alone."""
    errors: list[str] = []
    for where, level, options in _declared(schema):
        for name, value in options.items():
            defn = OPTIONS.get(name)
            if defn is None:
                errors.append(f"{where}: unknown option {name!r} (known: {', '.join(OPTIONS)})")
                continue
            if level not in defn.levels:
                allowed = ", ".join(lv for lv in LEVELS if lv in defn.levels)
                errors.append(f"{where}: option {name} is not allowed at {level} level "
                              f"(allowed: {allowed})")
            try:
                check_value(name, value)
            except (TypeError, ValueError) as exc:
                errors.append(f"{where}: {exc}")
    return errors


def _valid(name: str, value: object) -> bool:
    try:
        check_value(name, value)
    except (TypeError, ValueError):
        return False
    return True


def _source(schema: Schema, name: str, root: TypeRef) -> str:
    """Where a root's effective value of option `name` comes from (OPT-D3, OPT-D4)."""
    if isinstance(root, MsgRef) and name in schema.messages[root.name].options:
        return "declared here"
    if name in schema.options:
        return "the file's"
    return "the default"


def _root_errors(schema: Schema) -> list[str]:
    """Every root's effective bounds lie between its floors and the ceilings (OPT-D5, OPT-D6).

    A root's `max_depth` covers its non-recursive nesting, and no root nests past the ceiling.
    A declared `max_encoded_len` holds the root's smallest encoding. A root with no finite value
    (a required field recursing without end) admits no declared length; with none declared, no
    length floor applies to any root. A value refused where it is declared is not compared, nor is
    a root whose types do not resolve: both are errors already."""
    errors: list[str] = []
    for label, root in roots(schema):
        try:
            floor = nesting(schema, root)
            shortest = smallest_encoding(schema, root)
            depth = root_effective(schema, "max_depth", root)
            limit = root_effective(schema, "max_encoded_len", root)
        except (KeyError, TypeError):   # a dangling ref, an unknown type or scalar: refused above
            continue
        if floor > MAX_DEPTH_CEILING:
            errors.append(f"{label}: nests {floor} deep, above the max_depth ceiling "
                          f"{MAX_DEPTH_CEILING}")
        elif isinstance(depth, int) and _valid("max_depth", depth) and depth < floor:
            errors.append(f"{label}: max_depth {depth} ({_source(schema, 'max_depth', root)}) "
                          f"is below its non-recursive nesting {floor}")
        if not (isinstance(limit, int) and _valid("max_encoded_len", limit)):
            continue   # none declared: no length floor
        source = _source(schema, "max_encoded_len", root)
        if shortest is None:
            errors.append(f"{label}: max_encoded_len {limit} ({source}) admits no value: none has "
                          "a finite encoding (a required field recurses without end or is an "
                          "enum without members)")
        elif limit < shortest:
            errors.append(f"{label}: max_encoded_len {limit} ({source}) is below its smallest "
                          f"encoding, {shortest} bytes")
    return errors


def _held(schema: Schema, tref: TypeRef) -> tuple[TypeRef, ...]:
    """The types directly inside a value of `tref`, through wire fields, lists and maps."""
    if isinstance(tref, ListOf):
        return (tref.elem,)
    if isinstance(tref, MapOf):
        return (tref.key, tref.value)
    if isinstance(tref, MsgRef) and tref.name in schema.messages:
        return tuple(f.type for f in schema.messages[tref.name].wire_fields())
    return ()


def _embedded(schema: Schema, root: TypeRef) -> set[str]:
    """The messages a value of `root` may hold at any depth: a message root's own name only if
    it recurs. Extensions ride messages at run time, not through the schema's fields, and are
    not followed."""
    found: set[str] = set()
    pending = list(_held(schema, root))
    while pending:
        tref = pending.pop()
        if isinstance(tref, MsgRef):
            if tref.name in found:
                continue
            found.add(tref.name)
        pending.extend(_held(schema, tref))
    return found


def lint(schema: Schema) -> list[str]:
    """The warnings tautc SHOULD print, which never make a schema invalid (OPT-L4):

    - a recursive message, one whose wire fields reach it again, that declares no `max_depth`:
      the file's value or the default limits it, and its data may outgrow that (OPT-D5);
    - a bound a message declares that cannot take effect inside another root that embeds it at
      any depth, a message or a method's slot, because that root's effective value differs and
      bounds the whole call (OPT-D4).

    What validate refuses, an invalid value or a dangling reference, adds no warning here."""
    warnings: list[str] = []
    for m in schema.messages.values():
        if "max_depth" not in m.options and m.name in _embedded(schema, MsgRef(m.name)):
            value = effective(schema, "max_depth", message=m.name)
            warnings.append(f"{m.name}: recursive but declares no max_depth; a decode rooted at "
                            f"it applies {_source(schema, 'max_depth', MsgRef(m.name))} {value}, "
                            "which its data may outgrow")
    embedders = [(label, root, _embedded(schema, root)) for label, root in roots(schema)]
    for m in schema.messages.values():
        for name in _BOUNDS:
            if name not in m.options or not _valid(name, m.options[name]):
                continue
            declared = m.options[name]
            for label, root, inside in embedders:
                if root == MsgRef(m.name) or m.name not in inside:
                    continue
                outer = root_effective(schema, name, root)
                if outer == declared or not (outer is None or _valid(name, outer)):
                    continue
                shown = "no bound" if outer is None else outer
                warnings.append(f"{m.name}: its {name} {declared} cannot take effect inside "
                                f"{label}, which embeds it; a decode rooted there applies {shown}")
    return warnings
