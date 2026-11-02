"""Typed graph-contract probe -> direct Rust checks, with no GARNS-aware host.

All graph/index/key/discriminator/payload names come from annotated schema data.
This deliberately implements graph integrity only, not compiler evaluation.
"""

from dataclasses import asdict, dataclass
import re

from taut.ir.model import EnumRef, MapOf, MsgRef, Scalar
from taut.ir.validate import validate
from taut_app_probe import app, properties


@dataclass(frozen=True)
class Tagged:
    discriminator: str
    cases: dict[str, str | None]


@dataclass(frozen=True)
class ReferenceCheck:
    graph: str
    function: str


def GraphRules(namespace, *, tagged=None, references=None):
    value = {}
    if tagged is not None:
        value["tagged"] = asdict(tagged)
    if references is not None:
        value["references"] = asdict(references)
    return app(namespace, value)


def GraphIndex(namespace, *, reference, key):
    return app(namespace, {"index": {"reference": reference, "key": key}})


def GraphLink(namespace, *, index, select, null, missing="reject", invalid_payload="reject", wrong_target="reject"):
    return app(namespace, {"link": {
        "index": index, "select": list(select), "null": null,
        "missing": missing, "invalid_payload": invalid_payload, "wrong_target": wrong_target,
    }})


def _ident(value):
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z_][A-Za-z_0-9]*", value):
        raise ValueError(f"Invalid Rust identifier {value!r}")
    if value in {"fn", "struct", "enum", "mod", "type", "self", "Self", "crate", "use", "pub", "ref", "match", "impl", "where", "trait", "const", "static", "let", "move", "async", "await", "loop", "for", "in", "if", "else", "return", "unsafe", "extern", "super", "true", "false", "dyn"}:
        raise ValueError(f"Rust keyword not supported by this probe: {value}")
    return value


def _variant(member):
    # Taut's current Rust enum-member spelling.
    return "".join(part.capitalize() for part in member.split("_"))


def _exact(value, keys, where):
    if type(value) is not dict or set(value) != set(keys):
        raise ValueError(f"{where}: expected {keys}")


class Contract:
    def __init__(self, schema, namespace):
        errors = validate(schema)
        if errors:
            raise ValueError("\n".join(errors))
        self.schema = schema
        self.namespace = namespace
        self.unions = {}
        self.indices = {}
        self.checks = []
        for record in schema.messages.values():
            _ident(record.name)
            metadata = properties(record).get(namespace, {})
            if type(metadata) is not dict or set(metadata) - {"tagged", "references"}:
                raise ValueError(f"Unknown graph record property on {record.name}")
            if "tagged" in metadata:
                self.unions[record.name] = self.union(record, metadata["tagged"])
            for field in record.fields:
                field_metadata = properties(field).get(namespace, {})
                if type(field_metadata) is not dict or set(field_metadata) - {"index", "link"} or len(field_metadata) > 1:
                    raise ValueError(f"Unknown or conflicting graph field property on {record.name}.{field.name}")
                if "index" in field_metadata:
                    self.index(record, field, field_metadata["index"])
            if "references" in metadata:
                spec = metadata["references"]
                _exact(spec, ("graph", "function"), "reference check")
                _ident(spec["graph"])
                _ident(spec["function"])
                self.checks.append((record, spec, namespace))
        names = [spec["function"] for _, spec, _ in self.checks]
        generated = {self.union_name(name) for name in self.unions}
        if len(names) != len(set(names)) or generated.intersection(names) or "ProbeGraphError" in names:
            raise ValueError("Generated Rust function name collision")
        self._union_cycles()

    def fields(self, record):
        return {field.name: field for field in record.fields}

    def union(self, record, spec):
        _exact(spec, ("discriminator", "cases"), f"union {record.name}")
        fields = self.fields(record)
        tag = fields.get(spec["discriminator"])
        if tag is None or tag.optional or not isinstance(tag.type, EnumRef):
            raise ValueError(f"{record.name}: discriminator must be a required enum field")
        _ident(tag.name)
        _ident(tag.type.name)
        enum = self.schema.enums[tag.type.name]
        cases = spec["cases"]
        if type(cases) is not dict or set(cases) != set(enum.members):
            raise ValueError(f"{record.name}: explicit payload cases must cover its enum exactly")
        for payload in cases.values():
            if payload is None:
                continue
            _ident(payload)
            field = fields.get(payload)
            if field is None or not field.optional:
                raise ValueError(f"{record.name}.{payload}: payload must be nullable")
        return tag, cases

    def index(self, record, field, spec):
        _exact(spec, ("reference", "key"), f"index {record.name}.{field.name}")
        _ident(field.name)
        if field.optional or not isinstance(field.type, MapOf) or field.type.key != Scalar("str") or not isinstance(field.type.value, MsgRef):
            raise ValueError("Graph index must be a required text-keyed map of records")
        reference = self.schema.messages.get(spec["reference"])
        if reference is None:
            raise ValueError("Unknown graph reference record")
        key = self.fields(reference).get(spec["key"])
        if key is None or key.optional or key.type != field.type.key:
            raise ValueError("Reference key must be required and match the graph map's key type")
        _ident(key.name)
        self.indices[f"{record.name}.{field.name}"] = (record, field, reference, key)

    @staticmethod
    def union_name(name):
        return "probe_payload_" + re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()

    def _union_cycles(self):
        done = set()
        active = set()

        def visit(name):
            if name in active:
                raise ValueError("Recursive inline union validation is outside this probe")
            if name in done:
                return
            active.add(name)
            _, cases = self.unions[name]
            fields = self.fields(self.schema.messages[name])
            for payload in set(cases.values()) - {None}:
                payload_type = fields[payload].type
                if isinstance(payload_type, MsgRef) and payload_type.name in self.unions:
                    visit(payload_type.name)
            active.remove(name)
            done.add(name)

        for name in self.unions:
            visit(name)

    def emit_union(self, name):
        record = self.schema.messages[name]
        tag, cases = self.unions[name]
        payloads = sorted(set(cases.values()) - {None})
        count = "0" + "".join(f" + usize::from(value.{field}.is_some())" for field in payloads)
        lines = [f"fn {self.union_name(name)}(value: &r::{name}) -> Result<(), ProbeGraphError> {{",
                 f"    let active = {count};", f"    match value.{tag.name} {{"]
        for member, payload in cases.items():
            variant = _variant(member)
            lines.append(f"        r::{tag.type.name}::{variant} => {{")
            expected = 0 if payload is None else 1
            condition = f"active != {expected}" + (f" || value.{payload}.is_none()" if payload else "")
            lines.extend([f"            if {condition} {{", f'                return Err(ProbeGraphError::InvalidPayload("{name}"));', "            }"])
            if payload:
                field = self.fields(record)[payload]
                if isinstance(field.type, MsgRef) and field.type.name in self.unions:
                    lines.extend([f"            let selected = value.{payload}.as_ref().ok_or(ProbeGraphError::InvalidPayload(\"{name}\"))?;",
                                  f"            {self.union_name(field.type.name)}(selected)?;"])
            lines.append("        }")
        lines.extend(["    }", "    Ok(())", "}", ""])
        return lines

    def link(self, record, field, spec, graph):
        _exact(spec, ("index", "select", "null", "missing", "invalid_payload", "wrong_target"), "graph link")
        if spec["missing"] != "reject" or spec["invalid_payload"] != "reject" or spec["wrong_target"] != "reject":
            raise ValueError("This probe requires explicit rejection of invalid links")
        if spec["null"] not in ("reject", "absent") or (not field.optional and spec["null"] != "reject"):
            raise ValueError("Null policy conflicts with reference field presence")
        index = self.indices.get(spec["index"])
        if index is None or index[0].name != graph:
            raise ValueError("Graph link names an unknown or wrong-context index")
        _, index_field, reference, key = index
        if field.type != MsgRef(reference.name):
            raise ValueError("Link's reference record does not match its index")
        _ident(field.name)
        if type(spec["select"]) is not list or any(type(case) is not str for case in spec["select"]):
            raise ValueError("Target selection must be a list of explicit union case names")
        target_name = index_field.type.value.name
        if target_name not in self.unions:
            raise ValueError("Index target needs an explicit payload-selection contract")
        origin = f'"{record.name}.{field.name}"'
        lines = [f"let target0 = graph.{index_field.name}.get(&reference.{key.name}).ok_or(ProbeGraphError::MissingTarget({origin}))?;",
                 f"{self.union_name(target_name)}(target0)?;"]
        for level, member in enumerate(spec["select"]):
            if target_name not in self.unions:
                raise ValueError("Target selection continues beyond a declared union")
            tag, cases = self.unions[target_name]
            if member not in cases:
                raise ValueError("Target selection names an unknown union case")
            lines.extend([f"if target{level}.{tag.name} != r::{tag.type.name}::{_variant(member)} {{",
                          f"    return Err(ProbeGraphError::WrongTarget({origin}));", "}"])
            payload = cases[member]
            if level + 1 < len(spec["select"]):
                if payload is None:
                    raise ValueError("Target selection descends through an absent payload")
                lines.append(f"let target{level + 1} = target{level}.{payload}.as_ref().ok_or(ProbeGraphError::InvalidPayload(\"{target_name}\"))?;")
                payload_type = self.fields(self.schema.messages[target_name])[payload].type
                if not isinstance(payload_type, MsgRef):
                    raise ValueError("Target selection descends through a non-record payload")
                target_name = payload_type.name
        if field.optional and spec["null"] == "absent":
            return [f"if let Some(reference) = &value.{field.name} {{", *("    " + line for line in lines), "}"]
        if field.optional:
            prefix = f"let reference = value.{field.name}.as_ref().ok_or(ProbeGraphError::NullReference({origin}))?;"
        else:
            prefix = f"let reference = &value.{field.name};"
        return ["{", "    " + prefix, *("    " + line for line in lines), "}"]

    def emit_check(self, record, spec, namespace):
        if spec["graph"] not in self.schema.messages:
            raise ValueError("Unknown graph context record")
        lines = [f"pub fn {spec['function']}(graph: &r::{spec['graph']}, value: &r::{record.name}) -> Result<(), ProbeGraphError> {{"]
        count = 0
        for field in record.fields:
            metadata = properties(field).get(namespace, {})
            if "link" in metadata:
                count += 1
                lines.extend("    " + line for line in self.link(record, field, metadata["link"], spec["graph"]))
        if count == 0:
            raise ValueError("Reference check does not declare any links")
        lines.extend(["    Ok(())", "}", ""])
        return lines

    def emit(self):
        # Reject annotated links with no declared checking entry rather than
        # silently failing to generate a check for them.
        checked = {record.name for record, _, _ in self.checks}
        for record in self.schema.messages.values():
            for field in record.fields:
                if "link" in properties(field).get(self.namespace, {}) and record.name not in checked:
                    raise ValueError("A linked field has no checking entry")
        lines = ["// Generated from the explicit graph-contract probe. Do not edit.",
                 "// No application-specific runtime helper is called.",
                 "#[derive(Debug, PartialEq, Eq)]",
                 "pub enum ProbeGraphError {",
                 "    MissingTarget(&'static str),",
                 "    WrongTarget(&'static str),",
                 "    NullReference(&'static str),",
                 "    InvalidPayload(&'static str),", "}", ""]
        for name in sorted(self.unions):
            lines.extend(self.emit_union(name))
        for record, spec, namespace in sorted(self.checks, key=lambda item: item[1]["function"]):
            lines.extend(self.emit_check(record, spec, namespace))
        return "\n".join(lines)


def compile_graph_contract(schema, namespace):
    return Contract(schema, namespace).emit()
