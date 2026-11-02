"""Closed, versioned schema rule checks shared by compiler and publication."""
from .facts import EnumRef, OneOfRule, CaseRule

ONEOF_RULE = "taut.oneof.v1"


def check_rules(schema):
    errors = []
    for msg in schema.messages.values():
        fields = {f.name: f for f in msg.fields}
        owned = {}
        for f in msg.fields:
            where = f"{msg.name}.{f.name}"
            if f.oneof is not None:
                r = f.oneof
                if not isinstance(r, OneOfRule):
                    errors.append(f"{where}: unsupported oneof rule")
                    continue
                if type(r.virtual) is not bool or type(r.exhaustive) is not bool:
                    errors.append(f"{where}: virtual/exhaustive must be Boolean")
                if not isinstance(f.type, EnumRef) or f.type.name != r.enum:
                    errors.append(f"{where}: OneOf must use its declared enum type")
                enum = schema.enums.get(r.enum)
                if enum is None or not enum.members:
                    errors.append(f"{where}: OneOf requires an existing nonempty enum")
                if f.optional is not False or f.transient or f.cases:
                    errors.append(f"{where}: discriminator must be required, stored, and not a payload")
            controls = set()
            for c in f.cases:
                if not isinstance(c, CaseRule):
                    errors.append(f"{where}: unsupported Case rule")
                    continue
                controls.add(c.controlling_field)
                control = fields.get(c.controlling_field)
                if control is None or control.oneof is None:
                    errors.append(f"{where}: Case names unknown/non-OneOf controlling field {c.controlling_field}")
                    continue
                enum = schema.enums.get(control.oneof.enum)
                if enum is None or c.enum != enum.name or c.member not in enum.members:
                    errors.append(f"{where}: wrong enum ownership or unknown member {c.enum}.{c.member}")
                key = (c.controlling_field, c.member)
                if key in owned:
                    errors.append(f"{where}: duplicate member ownership {c.member}")
                owned[key] = f.name
            if len(controls) > 1:
                errors.append(f"{where}: payload cannot depend on multiple discriminators")
            if f.cases and f.optional is False:
                errors.append(f"{where}: Case payload must be nullable")
        for f in msg.fields:
            if isinstance(f.oneof, OneOfRule) and f.oneof.exhaustive:
                enum = schema.enums.get(f.oneof.enum)
                if enum:
                    missing = set(enum.members) - {m for (ctrl, m) in owned if ctrl == f.name}
                    if missing:
                        errors.append(f"{msg.name}.{f.name}: exhaustive OneOf missing {sorted(missing)}")
    return errors
