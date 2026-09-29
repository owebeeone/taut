"""Load an authored `.taut.py` IR module by path and return its SCHEMA.

The authored IR uses an unusual double extension (`griplab.taut.py`) and is not
a normal import target, so it is loaded explicitly here — appropriate, since the
loader is exactly the thing that consumes authored intent.

`schema_from_json` reads the exported IR, versions 1 and 2 only (TautOptions.md
OPT-I1, OPT-L5). Version 1 declares no options, so its effective values are the
defaults. From version 2 it reads the options declared at the file and at each
message, field and enum. It refuses what this taut cannot honour:
- an unknown option (OPT-F1);
- any option at a reserved level, a service, a method or an enum value (OPT-I2);
- a value its option cannot take;
- an `effective` other than what the options resolve to, the mark of a stale or
  hand-edited export (OPT-I3);
- an `effective` naming a wire option Python's runtime does not implement (OPT-F4).
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

from .model import (
    EnumDef,
    EnumRef,
    ExtensionDef,
    FieldDef,
    ListOf,
    MapOf,
    MessageDef,
    MethodDef,
    MsgRef,
    Scalar,
    Schema,
    ServiceDef,
    TypeRef,
)
from .options import OPTIONS, check_value, effective_map

# The IR versions this taut reads (OPT-I1).
IR_VERSIONS = (1, 2)

# The wire options that Python's runtime codec, `taut.wire`, implements (OPT-F4): both bound its
# decode (TautCheckedDecode.md). An IR whose `effective` names any other wire option is refused.
PYTHON_WIRE_OPTIONS = frozenset({"max_depth", "max_encoded_len"})

# The keys version 2 added. A version-1 IR carries none of them.
_V2_KEYS = ("options", "effective", "member_options")


def load_schema(path: str | Path) -> Schema:
    path = Path(path)
    spec = importlib.util.spec_from_file_location("_taut_ir_module", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load IR module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    schema = getattr(module, "SCHEMA", None)
    if not isinstance(schema, Schema):
        raise ValueError(f"{path} must define SCHEMA: Schema")
    return schema


def _typeref_from_json(d: dict) -> TypeRef:
    k = d["k"]
    if k == "scalar":
        return Scalar(d["scalar"])
    if k == "enum":
        return EnumRef(d["name"])
    if k == "msg":
        return MsgRef(d["name"])
    if k == "list":
        return ListOf(_typeref_from_json(d["elem"]))
    if k == "map":
        return MapOf(_typeref_from_json(d["key"]), _typeref_from_json(d["value"]))
    raise ValueError(f"unknown type ref {d!r}")


def _version(data: dict) -> int:
    version = data.get("version")
    if type(version) is not int or version not in IR_VERSIONS:   # true and 2.0 are not versions
        raise ValueError(f"unsupported IR version {version!r}: this taut reads versions "
                         f"{' and '.join(map(str, IR_VERSIONS))}; a newer taut wrote this IR, "
                         "or it is not one")
    return version


def _unknown(name: str) -> str:
    return (f"unknown option {name!r}; known options: {', '.join(OPTIONS)}; a newer taut wrote "
            "this IR")


def _refuse_v2_keys(level: dict, where: str) -> None:
    for key in _V2_KEYS:
        if key in level:
            raise ValueError(f"{where}: a version 1 IR declares no options, yet carries {key!r}; "
                             "re-export the schema, which writes version 2")


def _declared(level: dict, where: str, v2: bool) -> dict[str, object]:
    """The options declared at a level that takes them: the file, a message, a field or an enum.
    Each name must be registered (OPT-F1) and each value one its option can take. A wrong level
    is validate's to refuse (OPT-L4), as for a schema the DSL built."""
    if not v2:
        _refuse_v2_keys(level, where)
        return {}
    options = level.get("options", {})
    if not isinstance(options, dict):
        raise ValueError(f"{where}: options must be an object, not {options!r}")
    for name, value in options.items():
        if name not in OPTIONS:
            raise ValueError(f"{where}: {_unknown(name)}")
        try:
            check_value(name, value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{where}: {exc}") from exc
    return dict(options)


def _reserved(options: object, where: str) -> None:
    """The options of a reserved level (OPT-I2): no option is defined there yet, so any name
    is refused."""
    if not isinstance(options, dict):
        raise ValueError(f"{where}: options must be an object, not {options!r}")
    if options:
        name = next(iter(options))
        raise ValueError(f"{where}: option {name!r} at a reserved level; this taut defines no "
                         "options there, so a newer taut wrote this IR")


def _reserved_level(level: dict, where: str, v2: bool) -> None:
    """A service or a method: its `options` are reserved."""
    if not v2:
        _refuse_v2_keys(level, where)
        return
    _reserved(level.get("options", {}), where)


def _member_options(enum: dict, where: str) -> None:
    """Each enum value's options, through its enum's `member_options`: reserved (OPT-I2)."""
    member_options = enum.get("member_options", {})
    if not isinstance(member_options, dict):
        raise ValueError(f"{where}: member_options must be an object, not {member_options!r}")
    for member, options in member_options.items():
        if member not in enum["members"]:
            raise ValueError(f"{where}: member_options names {member!r}, not a member")
        _reserved(options, f"enum value {enum['name']}.{member}")


def _exactly(written: dict, resolved: dict) -> bool:
    """Equal name for name and value for value, types included: JSON's true is not 1, nor is 1.0."""
    return written.keys() == resolved.keys() and all(
        type(written[name]) is type(value) and written[name] == value
        for name, value in resolved.items()
    )


def _check_effective(level: dict, schema: Schema, message: str | None, where: str) -> None:
    """The `effective` of the file (`message` None) or of a message: registered names only
    (OPT-F1), no wire option Python's runtime lacks (OPT-F4), and exactly the values the declared
    options resolve to (OPT-I3)."""
    if "effective" not in level:
        raise ValueError(f"{where}: a version 2 IR carries effective values at the file and at "
                         "each message; re-export the schema")
    written = level["effective"]
    if not isinstance(written, dict):
        raise ValueError(f"{where}: effective must be an object, not {written!r}")
    for name in written:
        defn = OPTIONS.get(name)
        if defn is None:
            raise ValueError(f"{where}: effective names {_unknown(name)}")
        if defn.klass == "wire" and name not in PYTHON_WIRE_OPTIONS:
            raise ValueError(f"{where}: effective names wire option {name!r}, which this taut's "
                             "Python runtime does not implement, so it cannot decode as the IR "
                             "requires")
    resolved = effective_map(schema, message=message)
    if not _exactly(written, resolved):
        raise ValueError(f"{where}: effective {json.dumps(written, default=repr)} is not "
                         f"{json.dumps(resolved)}, what its options resolve to; the IR is stale "
                         "or hand-edited: re-export it")


def schema_from_json(data: dict) -> Schema:
    """Inverse of export.schema_json — load a Schema from the neutral IR JSON."""
    if not isinstance(data, dict):
        raise ValueError(f"a taut IR is a JSON object, not {type(data).__name__}")
    v2 = _version(data) == 2
    enums = {}
    for e in data["enums"]:
        where = f"enum {e['name']}"
        options = _declared(e, where, v2)
        if v2:
            _member_options(e, where)
        enums[e["name"]] = EnumDef(e["name"], dict(e["members"]), options)
    messages = {}
    for m in data["messages"]:
        for f in m["fields"]:
            if "missing_ok" in f:
                raise ValueError(
                    f"{m['name']}.{f['name']}: the IR key 'missing_ok' is retired; re-export the "
                    "schema, which writes \"optional\": \"missing_ok\" instead")
        fields = tuple(
            FieldDef(f["name"], f["tag"], _typeref_from_json(f["type"]), f["optional"],
                     f["transient"], f.get("merge"),
                     _declared(f, f"field {m['name']}.{f['name']}", v2))
            for f in m["fields"]
        )
        messages[m["name"]] = MessageDef(
            m["name"], fields,
            tuple(m.get("reserved_tags", [])),
            tuple(m.get("reserved_names", [])),
            m.get("next_id"),
            _declared(m, f"message {m['name']}", v2),
        )
    services = {}
    for s in data.get("services", []):
        _reserved_level(s, f"service {s['name']}", v2)
        for m in s["methods"]:
            _reserved_level(m, f"method {s['name']}.{m['name']}", v2)
        methods = tuple(
            MethodDef(
                name=m["name"],
                role=m["role"],
                shape=m["shape"],
                out=tuple((o["slot"], _typeref_from_json(o["type"])) for o in m["out"]),
                params=tuple((p["name"], _typeref_from_json(p["type"])) for p in m["params"]),
            )
            for m in s["methods"]
        )
        services[s["name"]] = ServiceDef(s["name"], methods)
    extensions = tuple(ExtensionDef(e["message"], e["tag"]) for e in data.get("extensions", []))
    schema = Schema(enums=enums, messages=messages, services=services, extensions=extensions,
                    options=_declared(data, "the file", v2))
    if v2:
        _check_effective(data, schema, None, "the file")
        for m in data["messages"]:
            _check_effective(m, schema, m["name"], f"message {m['name']}")
    return schema
