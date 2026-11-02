"""Isolated application-property experiment; not a production Taut extension.

The original F, Msg, schema, generators and wire codecs remain unchanged.
Field/message subclasses retain annotations through dataclasses.replace, which
Taut already uses for assigning names and resolving enum refs.
"""

from dataclasses import dataclass, field, fields, replace
import json
import re

from taut.ir import dsl
from taut.ir.export import schema_json
from taut.ir.load import schema_from_json
from taut.ir.model import FieldDef, MessageDef


@dataclass(frozen=True)
class Property:
    namespace: str
    encoded: str

    @property
    def value(self):
        # Each observer gets a copy; callers cannot mutate the retained value.
        return json.loads(self.encoded)


def _json_value(value):
    if value is None or type(value) in (str, bool, int, float):
        return
    if type(value) is list:
        for item in value:
            _json_value(item)
        return
    if type(value) is dict and all(type(key) is str for key in value):
        for item in value.values():
            _json_value(item)
        return
    raise TypeError("Application properties require JSON values with text object keys")


def app(namespace, value):
    if not isinstance(namespace, str) or not re.fullmatch(r"[a-z][a-z0-9_-]*(?:\.[a-z][a-z0-9_-]*)+", namespace):
        raise ValueError("Application properties need a dotted namespace")
    _json_value(value)
    encoded = json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True)
    encoded.encode("utf-8")
    return Property(namespace, encoded)


@dataclass(frozen=True)
class AnnotatedField(FieldDef):
    app_properties: tuple[Property, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class AnnotatedMessage(MessageDef):
    app_properties: tuple[Property, ...] = field(default_factory=tuple)


def annotate(definition, *properties):
    if not properties:
        return definition
    if isinstance(definition, FieldDef):
        base, result = FieldDef, AnnotatedField
    elif isinstance(definition, MessageDef):
        base, result = MessageDef, AnnotatedMessage
    else:
        raise TypeError("This probe annotates fields and messages only")
    combined = list(getattr(definition, "app_properties", ()))
    seen = {value.namespace for value in combined}
    for value in properties:
        if not isinstance(value, Property):
            raise TypeError("Properties must be constructed with app(namespace, value)")
        if value.namespace in seen:
            raise ValueError(f"Duplicate application namespace {value.namespace}")
        seen.add(value.namespace)
        # Revalidate even explicitly constructed Property values.
        combined.append(app(value.namespace, value.value))
    data = {item.name: getattr(definition, item.name) for item in fields(base)}
    return result(**data, app_properties=tuple(combined))


def properties(definition):
    return {value.namespace: value.value for value in getattr(definition, "app_properties", ())}


def _split(args):
    return tuple(arg for arg in args if not isinstance(arg, Property)), tuple(
        arg for arg in args if isinstance(arg, Property))


def F(*args, **kwargs):
    arguments, metadata = _split(args)
    return annotate(dsl.F(*arguments, **kwargs), *metadata)


def Msg(*args, **kwargs):
    arguments, metadata = _split(args)
    return annotate(dsl.Msg(*arguments, **kwargs), *metadata)


def to_probe_json(schema):
    """Explicit probe envelope; the normal version-2 exporter is not modified."""
    document = schema_json(schema)
    for message in document["messages"]:
        definition = schema.messages[message["name"]]
        message["app_properties"] = properties(definition)
        by_name = {item.name: item for item in definition.fields}
        for item in message["fields"]:
            item["app_properties"] = properties(by_name[item["name"]])
    return {"format": "taut.application-properties.probe", "version": 1, "schema": document}


def from_probe_json(value):
    if type(value) is not dict or set(value) != {"format", "version", "schema"}:
        raise ValueError("Expected the application-property probe envelope")
    if value["format"] != "taut.application-properties.probe" or type(value["version"]) is not int or value["version"] != 1:
        raise ValueError("Unsupported application-property probe")
    # Private copy before stripping properties for the unchanged Taut IR loader.
    document = json.loads(json.dumps(value["schema"], allow_nan=False))
    metadata = {}
    for message in document["messages"]:
        message_properties = message.pop("app_properties")
        field_properties = {item["name"]: item.pop("app_properties") for item in message["fields"]}
        if message["name"] in metadata:
            raise ValueError("Duplicate annotated message name")
        metadata[message["name"]] = (message_properties, field_properties)
    schema = schema_from_json(document)
    messages = {}
    for name, message in schema.messages.items():
        message_properties, field_properties = metadata[name]
        new_fields = tuple(annotate(item, *_read_properties(field_properties[item.name])) for item in message.fields)
        messages[name] = annotate(replace(message, fields=new_fields), *_read_properties(message_properties))
    return replace(schema, messages=messages)


def _read_properties(value):
    if type(value) is not dict:
        raise ValueError("Application properties must be a namespace map")
    return tuple(app(namespace, payload) for namespace, payload in value.items())
