"""IR breaking-change gate (P7).

Diff a new IR against the prior version and classify each change as breaking or
compatible. Under the same major version, breaking changes are rejected. This is
*possible because the IR is declarative* (not Turing-complete) — a structural
diff is well-defined.

Compatibility model for the frozen wire (messages = CBOR maps keyed by field tag,
decoders read declared wire-fields by tag):

  Compatible: add message/enum/method; add enum member; add an *optional* field;
              add a stream event; relax a field required→optional.
  Breaking:   remove or rename(at-tag) a field; change a field's tag or wire-type;
              tighten optional→required; add a *required* field; remove/renumber an
              enum member; remove message/enum/method; change a method's kind/shape/
              param types/output/event types; remove a method param or add one.

Transient fields are off the wire and ignored by the diff.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass

from .load import schema_from_json
from .model import EnumRef, ListOf, MsgRef, Scalar, Schema, TypeRef


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
            if of.optional and not nf.optional:
                out.append(Change("breaking", f"{name}.{of.name} optional->required"))
            elif not of.optional and nf.optional:
                out.append(Change("compatible", f"{name}.{of.name} required->optional"))
            if of.merge != nf.merge:
                out.append(Change("breaking", f"{name}.{of.name} CRDT merge {of.merge}->{nf.merge}"))
            # a field kept by name but moved to a different tag
            same_name_new = new_by_name.get(of.name)
            if same_name_new is not None and same_name_new.tag != of.tag:
                out.append(Change("breaking", f"{name}.{of.name} tag {of.tag}->{same_name_new.tag}"))
        for tag, nf in new_by_tag.items():
            if tag not in old_by_tag:
                level = "compatible" if nf.optional else "breaking"
                suffix = "" if nf.optional else " (required)"
                out.append(Change(level, f"{name}.{nf.name} (tag {tag}) added{suffix}"))
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
            if nm.kind != om.kind:
                out.append(Change("breaking", f"method {sname}.{mname} kind {om.kind}->{nm.kind}"))
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


def diff(old: Schema, new: Schema) -> list[Change]:
    out: list[Change] = []
    _diff_enums(old, new, out)
    _diff_messages(old, new, out)
    _diff_services(old, new, out)
    return out


def breaking(old: Schema, new: Schema) -> list[Change]:
    return [c for c in diff(old, new) if c.level == "breaking"]


def check_or_raise(old: Schema, new: Schema) -> None:
    bad = breaking(old, new)
    if bad:
        raise ValueError("breaking IR changes under the same major:\n  " + "\n  ".join(c.detail for c in bad))


def main() -> None:
    """CLI: prism.ir.compat <baseline.ir.json> <new.ir.json> — exit 1 on breaking."""
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
