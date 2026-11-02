"""Focused feasibility checks; production Taut modules remain unchanged."""

from dataclasses import replace
import json
from pathlib import Path
import tempfile
import unittest

from taut.gen.scaffold import emit
from taut.ir import dsl
from taut.ir.export import schema_json
from taut.ir.load import load_schema
from taut.ir.validate import validate
from taut.wire.codec import encode, decode
from taut_app_probe import F, Msg, annotate, app, from_probe_json, properties, to_probe_json


def example(annotated=True):
    field = dsl.F(1, dsl.STR, optional=True)
    if annotated:
        field = annotate(field, app("example.validation", {"max_characters": 24}))
    message = dsl.Msg(dsl.option.max_depth(8), label=field, next_id=2)
    if annotated:
        message = annotate(message, app("example.validation", {"check": "check_label"}))
    return dsl.schema(Label=message)


class ApplicationPropertiesProbeTests(unittest.TestCase):
    def test_field_and_message_properties_survive_naming_and_enum_resolution(self):
        schema = dsl.schema(
            Mode=dsl.Enum(fast=0, slow=1),
            Job=Msg(app("example.docs", {"owner": "synthetic"}),
                    mode=F(1, dsl.Ref.Mode, app("example.docs", "selection")), next_id=2),
        )
        self.assertEqual(validate(schema), [])
        message = schema.messages["Job"]
        self.assertEqual(properties(message), {"example.docs": {"owner": "synthetic"}})
        self.assertEqual(properties(message.fields[0]), {"example.docs": "selection"})
        self.assertEqual(message.fields[0].type.name, "Mode")
        self.assertIsInstance(message.fields[0].type, dsl.EnumRef)

    def test_wrapper_and_convenience_apis_are_equivalent(self):
        prop = app("example.validation", {"minimum": 1})
        left = annotate(dsl.F("count", 1, dsl.INT), prop)
        right = F("count", 1, dsl.INT, prop)
        self.assertEqual(left, right)
        self.assertEqual(annotate(dsl.Msg("Counter", left), prop), Msg("Counter", right, prop))

    def test_no_properties_preserves_exact_original_definitions_and_options(self):
        self.assertEqual(F(1, dsl.STR), dsl.F(1, dsl.STR))
        message = Msg(dsl.option.max_depth(8), name=F(1, dsl.STR), next_id=2)
        self.assertEqual(message, dsl.Msg(dsl.option.max_depth(8), name=dsl.F(1, dsl.STR), next_id=2))
        self.assertEqual(schema_json(example(True)), schema_json(example(False)))

    def test_explicit_probe_json_round_trip_preserves_unknown_namespaces(self):
        original = example()
        message = original.messages["Label"]
        message = annotate(message, app("other.consumer", [True, None, {"x": 2}]))
        original = replace(original, messages={"Label": message})
        envelope = json.loads(json.dumps(to_probe_json(original)))
        restored = from_probe_json(envelope)
        self.assertEqual(restored, original)
        self.assertEqual(validate(restored), [])
        self.assertEqual(to_probe_json(restored), envelope)

    def test_metadata_does_not_change_normal_rust_or_python_generation(self):
        with tempfile.TemporaryDirectory(prefix="taut-app-properties-") as temporary:
            root = Path(temporary)
            for name, schema in (("plain", example(False)), ("annotated", example(True))):
                emit(schema, root / name, langs=["rust", "python"], services=[], runtime=True)
            plain = {p.relative_to(root / "plain"): p.read_bytes() for p in (root / "plain").rglob("*") if p.is_file()}
            annotated = {p.relative_to(root / "annotated"): p.read_bytes() for p in (root / "annotated").rglob("*") if p.is_file()}
            self.assertTrue(plain)
            self.assertEqual(annotated, plain)

    def test_properties_do_not_change_wire_bytes_or_run_application_checks(self):
        for label in (None, "hello", "longer than the annotated application limit" * 2):
            value = {"label": label}
            plain = encode(example(False), "Label", value)
            annotated = encode(example(True), "Label", value)
            self.assertEqual(annotated, plain)
            self.assertEqual(decode(example(True), "Label", annotated), value)

    def test_properties_are_copied_and_conflicting_namespaces_rejected(self):
        payload = {"items": [1]}
        prop = app("example.validation", payload)
        payload["items"].append(2)
        observer = prop.value
        observer["items"].append(3)
        self.assertEqual(prop.value, {"items": [1]})
        with self.assertRaises(ValueError):
            F(1, dsl.INT, prop, prop)
        with self.assertRaises(ValueError):
            annotate(annotate(dsl.Msg(), prop), prop)

    def test_invalid_namespaces_or_nonportable_values_are_rejected(self):
        for namespace in ("garns", "", "garns..graph", "garns. graph", None):
            with self.subTest(namespace=namespace), self.assertRaises(ValueError):
                app(namespace, {})
        for payload in (object(), {1: "x"}, (1, 2), float("nan"), float("inf"), "\ud800"):
            with self.subTest(payload=repr(payload)), self.assertRaises((TypeError, ValueError, UnicodeError)):
                app("example.validation", payload)

    def test_example_loads_through_the_existing_taut_loader(self):
        schema = load_schema(Path(__file__).with_name("example.taut.py"))
        self.assertEqual(validate(schema), [])
        field = schema.messages["FieldDetails"].fields[0]
        self.assertEqual(properties(field)["garns.graph"]["target"]["view"], "type_view")


if __name__ == "__main__":
    unittest.main()
