"""IR breaking-change gate (P7).

Diff a new IR against the prior version and classify each change as breaking or
compatible. Under the same major version, breaking changes are rejected. This is
*possible because the IR is declarative* (not Turing-complete) — a structural
diff is well-defined.

Compatibility model for the frozen wire (messages = CBOR maps keyed by field tag,
decoders read declared wire-fields by tag):

  Compatible: add message/enum/method; add enum member; add a field that is
              optional=MISSING_OK; add a stream event; move a field's presence up
              the ladder required -> optional -> missing_ok.
  Breaking:   add a required or optional=True field (a decoder refuses a message
              without its key, MissingKey, so a new reader refuses every message
              written before it: TautCheckedDecode.md question 4); remove or
              rename(at-tag) a field; change a field's tag or wire-type; move its
              presence down the ladder; remove/renumber an enum member; remove
              message/enum/method; change a method's kind/shape/param types/output/
              event types; remove a method param or add one.

Transient fields are off the wire and ignored by the diff.

Options (D27, TautOptions.md OPT-K1-K4). A wire or semantic option is compared by its effective
value at every root present in both schemas: each message, and each method slot not typed as a
message, which takes the file's values. Any change is breaking, raised or lowered; an undeclared
max_encoded_len is none, unbounded, so a first declaration lowers it. A move that changes no root's
value is no change, and a new message is "message added" whatever it declares. Codegen and metadata
declarations are listed as written, compatible, a codegen change with a note; a change of an option
the registry does not know is breaking, since its class is unknown. Defaults and ceilings are taut's
own: both schemas resolve under this taut's, so changing one is a taut release (OPT-K4).
"""

from __future__ import annotations

import json
import sys
from collections.abc import Iterator
from dataclasses import dataclass

from .load import schema_from_json
from .model import MISSING_OK, EnumRef, ListOf, MapOf, MsgRef, Scalar, Schema, TypeRef
from .options import OPTIONS, effective

# Presence is a ladder: each value reads every message the one before it reads, so a move up is
# compatible and a move down breaking.
_PRESENCE_RANK = {False: 0, True: 1, MISSING_OK: 2}
_PRESENCE_NAME = {False: "required", True: "optional", MISSING_OK: "missing_ok"}

# Option classes graded at roots, breaking when an effective value changes: wire options change
# what decodes (OPT-K1), semantic ones what readers compute from the same bytes (question 7).
_AT_ROOTS = ("wire", "semantic")
# The classes that leave the wire alone, listed as declared (OPT-K2), with each one's note.
_LISTED = {"codegen": " (wire-compatible; the generated API may change)", "metadata": ""}


@dataclass(frozen=True)
class Change:
    level: str   # "breaking" | "compatible"
    detail: str


def _wire(t: TypeRef) -> tuple:
    if isinstance(t, Scalar):
        return ("scalar", t.kind)
    if isinstance(t, EnumRef):
        return ("enum", t.name)
    if isinstance(t, MsgRef):
        return ("msg", t.name)
    if isinstance(t, ListOf):
        return ("list", _wire(t.elem))
    if isinstance(t, MapOf):
        return ("map", _wire(t.key), _wire(t.value))
    raise TypeError(t)


def _diff_enums(old: Schema, new: Schema, out: list[Change]) -> None:
    for name, oe in old.enums.items():
        ne = new.enums.get(name)
        if ne is None:
            out.append(Change("breaking", f"enum {name} removed"))
            continue
        for m, v in oe.members.items():
            if m not in ne.members:
                out.append(Change("breaking", f"enum {name} member {m} removed"))
            elif ne.members[m] != v:
                out.append(Change("breaking", f"enum {name} member {m} wire value {v}->{ne.members[m]}"))
        for m in ne.members:
            if m not in oe.members:
                out.append(Change("compatible", f"enum {name} member {m} added"))
    for name in new.enums:
        if name not in old.enums:
            out.append(Change("compatible", f"enum {name} added"))


def _diff_messages(old: Schema, new: Schema, out: list[Change]) -> None:
    for name, om in old.messages.items():
        nm = new.messages.get(name)
        if nm is None:
            out.append(Change("breaking", f"message {name} removed"))
            continue
        old_by_tag = {f.tag: f for f in om.wire_fields()}
        new_by_tag = {f.tag: f for f in nm.wire_fields()}
        new_by_name = {f.name: f for f in nm.wire_fields()}
        for tag, of in old_by_tag.items():
            nf = new_by_tag.get(tag)
            if nf is None:
                out.append(Change("breaking", f"{name}.{of.name} (tag {tag}) removed"))
                continue
            if nf.name != of.name:
                out.append(Change("breaking", f"{name} tag {tag} reassigned {of.name}->{nf.name}"))
            if _wire(nf.type) != _wire(of.type):
                out.append(Change("breaking", f"{name}.{of.name} wire-type changed"))
            if of.optional != nf.optional:
                up = _PRESENCE_RANK[nf.optional] > _PRESENCE_RANK[of.optional]
                out.append(Change("compatible" if up else "breaking",
                                  f"{name}.{of.name} {_PRESENCE_NAME[of.optional]}->"
                                  f"{_PRESENCE_NAME[nf.optional]}"))
            if of.merge != nf.merge:
                out.append(Change("breaking", f"{name}.{of.name} CRDT merge {of.merge}->{nf.merge}"))
            # a field kept by name but moved to a different tag
            same_name_new = new_by_name.get(of.name)
            if same_name_new is not None and same_name_new.tag != of.tag:
                out.append(Change("breaking", f"{name}.{of.name} tag {of.tag}->{same_name_new.tag}"))
        for tag, nf in new_by_tag.items():
            if tag not in old_by_tag:
                # Only MISSING_OK reads a message that lacks the key (question 4, ruled (a)).
                level = "compatible" if nf.optional == MISSING_OK else "breaking"
                out.append(Change(level, f"{name}.{nf.name} (tag {tag}) added "
                                         f"({_PRESENCE_NAME[nf.optional]})"))
        # reserved: adding is hygiene (compatible); un-reserving re-opens reuse (breaking)
        for t in set(om.reserved_tags) - set(nm.reserved_tags):
            out.append(Change("breaking", f"{name} tag {t} un-reserved"))
        for rn in set(om.reserved_names) - set(nm.reserved_names):
            out.append(Change("breaking", f"{name} name {rn!r} un-reserved"))
        for t in set(nm.reserved_tags) - set(om.reserved_tags):
            out.append(Change("compatible", f"{name} tag {t} reserved"))
    for name in new.messages:
        if name not in old.messages:
            out.append(Change("compatible", f"message {name} added"))


def _diff_services(old: Schema, new: Schema, out: list[Change]) -> None:
    for sname, osvc in old.services.items():
        nsvc = new.services.get(sname)
        if nsvc is None:
            out.append(Change("breaking", f"service {sname} removed"))
            continue
        old_m = {m.name: m for m in osvc.methods}
        new_m = {m.name: m for m in nsvc.methods}
        for mname, om in old_m.items():
            nm = new_m.get(mname)
            if nm is None:
                out.append(Change("breaking", f"method {sname}.{mname} removed"))
                continue
            # shape is the sole discriminator (D22) — it subsumes the old `kind`,
            # so a unary->stream change is just a shape change.
            if nm.shape != om.shape:
                out.append(Change("breaking", f"method {sname}.{mname} shape {om.shape}->{nm.shape}"))
            op = {pn: _wire(pt) for pn, pt in om.params}
            np = {pn: _wire(pt) for pn, pt in nm.params}
            for pn, w in op.items():
                if pn not in np:
                    out.append(Change("breaking", f"method {sname}.{mname} param {pn} removed"))
                elif np[pn] != w:
                    out.append(Change("breaking", f"method {sname}.{mname} param {pn} type changed"))
            for pn in np:
                if pn not in op:
                    out.append(Change("breaking", f"method {sname}.{mname} param {pn} added"))
            if om.output is not None and nm.output is not None and _wire(om.output) != _wire(nm.output):
                out.append(Change("breaking", f"method {sname}.{mname} output type changed"))
            oe = {en: _wire(et) for en, et in om.events}
            nev = {en: _wire(et) for en, et in nm.events}
            for en, w in oe.items():
                if en not in nev:
                    out.append(Change("breaking", f"method {sname}.{mname} event {en} removed"))
                elif nev[en] != w:
                    out.append(Change("breaking", f"method {sname}.{mname} event {en} type changed"))
            for en in nev:
                if en not in oe:
                    out.append(Change("compatible", f"method {sname}.{mname} event {en} added"))
        for mname in new_m:
            if mname not in old_m:
                out.append(Change("compatible", f"method {sname}.{mname} added"))
    for sname in new.services:
        if sname not in old.services:
            out.append(Change("compatible", f"service {sname} added"))


def _slots(s: Schema) -> dict[str, TypeRef]:
    """Every method slot, each param and out slot, by the name the gate reports it under."""
    slots: dict[str, TypeRef] = {}
    for sname, svc in s.services.items():
        for m in svc.methods:
            for pn, pt in m.params:
                slots[f"method {sname}.{m.name} param {pn}"] = pt
            for slot, st in m.out:
                slots[f"method {sname}.{m.name} out {slot}"] = st
    return slots


def _roots(old: Schema, new: Schema) -> list[tuple[str, str | None]]:
    """The decode roots present in both schemas (OPT-D4, OPT-D5), each with the message whose
    effective values bound it, or None for the file's: every message, and every method slot whose
    type is not a message in either. A slot typed as a message is rooted at that message."""
    roots: list[tuple[str, str | None]] = [
        (f"message {name}", name) for name in old.messages if name in new.messages
    ]
    new_slots = _slots(new)
    for where, t in _slots(old).items():
        nt = new_slots.get(where)
        if nt is not None and not isinstance(t, MsgRef) and not isinstance(nt, MsgRef):
            roots.append((where, None))
    return roots


def _declarations(old: Schema, new: Schema) -> Iterator[tuple[str, dict, dict]]:
    """The declared options of each element present in both schemas: the file, each message and its
    fields, matched by name, and each enum."""
    yield "file", old.options, new.options
    for name, om in old.messages.items():
        nm = new.messages.get(name)
        if nm is None:
            continue
        yield f"message {name}", om.options, nm.options
        new_fields = {f.name: f for f in nm.fields}
        for of in om.fields:
            nf = new_fields.get(of.name)
            if nf is not None:
                yield f"{name}.{of.name}", of.options, nf.options
    for name, oe in old.enums.items():
        ne = new.enums.get(name)
        if ne is not None:
            yield f"enum {name}", oe.options, ne.options


def _effective_text(value: object) -> str:
    return "none" if value is None else repr(value)


def _declared_text(options: dict[str, object], name: str) -> str:
    return repr(options[name]) if name in options else "unset"


def _diff_options(old: Schema, new: Schema, out: list[Change]) -> None:
    """Options (OPT-K1, K2): effective values at roots, then the other classes as declared."""
    for where, message in _roots(old, new):
        for name, defn in OPTIONS.items():
            if defn.klass not in _AT_ROOTS:
                continue
            before = effective(old, name, message=message)
            after = effective(new, name, message=message)
            if before != after:
                out.append(Change("breaking", f"{where} {defn.klass} option {name} "
                                              f"{_effective_text(before)}->{_effective_text(after)}"))
    for where, before, after in _declarations(old, new):
        for name in dict.fromkeys((*before, *after)):
            defn = OPTIONS.get(name)
            if defn is not None and defn.klass in _AT_ROOTS:
                continue   # graded at the roots above
            if name in before and name in after and before[name] == after[name]:
                continue
            change = f"{_declared_text(before, name)}->{_declared_text(after, name)}"
            if defn is None:
                out.append(Change("breaking", f"{where} unknown option {name} {change}"))
            else:
                out.append(Change("compatible", f"{where} {defn.klass} option {name} {change}"
                                                f"{_LISTED[defn.klass]}"))


def diff(old: Schema, new: Schema) -> list[Change]:
    out: list[Change] = []
    _diff_enums(old, new, out)
    _diff_messages(old, new, out)
    _diff_services(old, new, out)
    _diff_options(old, new, out)
    return out


def breaking(old: Schema, new: Schema) -> list[Change]:
    return [c for c in diff(old, new) if c.level == "breaking"]


def check_or_raise(old: Schema, new: Schema) -> None:
    bad = breaking(old, new)
    if bad:
        raise ValueError("breaking IR changes under the same major:\n  " + "\n  ".join(c.detail for c in bad))


def main() -> None:
    """CLI: taut.ir.compat <baseline.ir.json> <new.ir.json> — exit 1 on breaking."""
    base, new = sys.argv[1], sys.argv[2]
    old_s = schema_from_json(json.loads(open(base).read()))
    new_s = schema_from_json(json.loads(open(new).read()))
    changes = diff(old_s, new_s)
    for c in changes:
        print(f"[{c.level}] {c.detail}")
    bad = [c for c in changes if c.level == "breaking"]
    print(f"{len(bad)} breaking, {len(changes) - len(bad)} compatible")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
