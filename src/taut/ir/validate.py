"""The IR validator — coherence checks that make the IR trustworthy as data.

Possible *because* the IR is declarative (not Turing-complete): every reference
resolves, tags are unique, and every service method is coherent with the closed
delivery-shape set. Returns a list of human-readable errors (empty == valid).

This is the gate the build prompt calls for: reject incoherent shape/axis
combinations and anything outside the closed set, before any mechanism is derived.
"""

from __future__ import annotations

from .model import EnumRef, ListOf, MsgRef, Scalar, Schema, TypeRef
from .shapes import BAND_START, ROLES, SHAPES


def validate(schema: Schema) -> list[str]:
    errors: list[str] = []

    def check_ref(t: TypeRef, ctx: str) -> None:
        if isinstance(t, Scalar):
            if t.kind not in ("int", "str", "bytes", "bool"):
                errors.append(f"{ctx}: unknown scalar {t.kind!r}")
        elif isinstance(t, EnumRef):
            if t.name not in schema.enums:
                errors.append(f"{ctx}: dangling enum ref {t.name!r}")
        elif isinstance(t, MsgRef):
            if t.name not in schema.messages:
                errors.append(f"{ctx}: dangling message ref {t.name!r}")
        elif isinstance(t, ListOf):
            check_ref(t.elem, ctx)
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
                allowed = SHAPES[meth.shape]["events"]
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

    return errors


def validate_or_raise(schema: Schema) -> None:
    errors = validate(schema)
    if errors:
        raise ValueError("invalid IR:\n  " + "\n  ".join(errors))
