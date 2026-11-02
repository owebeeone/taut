"""Same explicit-validation fixtures through generated Rust and Python APIs."""

import copy
from dataclasses import fields, is_dataclass, FrozenInstanceError
from enum import Enum as PythonEnum
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from taut.gen.scaffold import emit
from taut.ir import dsl
from taut.ir.load import load_schema
from taut.ir.model import EnumRef, MsgRef, Scalar
from taut.wire.codec import encode, decode
from oneof_fields_probe import Case, Enum, F, Msg, OneOf
from oneof_reports_probe import compile_report_validators

DIRECTORY = Path(__file__).parent


def load_generated_package(directory):
    name = "_taut_validation_probe_generated"
    (directory / "__init__.py").write_text("")
    spec = importlib.util.spec_from_file_location(name, directory / "__init__.py", submodule_search_locations=[str(directory)])
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    api = __import__(name + ".api", fromlist=["api"])
    validation = __import__(name + ".validation", fromlist=["validation"])
    return name, api, validation


def wire_value(value):
    if isinstance(value, PythonEnum):
        # The existing Taut reference codec takes symbolic enum names.
        return value.name
    if is_dataclass(value):
        return {field.name: wire_value(getattr(value, field.name)) for field in fields(value)}
    return value


class ExplicitValidatorReportProbeTests(unittest.TestCase):
    def setUp(self):
        self.schema, sources = compile_report_validators(load_schema(DIRECTORY / "validation_fixture.taut.py"))
        self.temporary = tempfile.TemporaryDirectory(prefix="taut-validation-report-")
        self.root = Path(self.temporary.name)
        emit(self.schema, self.root, langs=["rust", "python"], services=[], runtime=True)
        self.ordinary_files = {p.relative_to(self.root): p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        self.rust = sources[0]
        (self.root / "validation.rs").write_text(sources[0])
        (self.root / "python/validation.py").write_text(sources[1])
        self.package_name, self.api, self.validation = load_generated_package(self.root / "python")
        self.cases = json.loads((DIRECTORY / "oneof_report_cases.json").read_text())

    def tearDown(self):
        for name in list(sys.modules):
            if name == self.package_name or name.startswith(self.package_name + "."):
                del sys.modules[name]
        self.temporary.cleanup()

    def construct(self, name, value):
        arguments = {}
        for field in self.schema.messages[name].fields:
            actual = value.get(field.name)
            if actual is None:
                arguments[field.name] = None
            elif isinstance(field.type, EnumRef):
                enum = getattr(self.api, field.type.name)
                arguments[field.name] = enum[actual] if isinstance(actual, str) else enum(actual)
            elif isinstance(field.type, MsgRef):
                arguments[field.name] = self.construct(field.type.name, actual)
            else:
                arguments[field.name] = actual
        return getattr(self.api, name)(**arguments)

    def report(self, name, value):
        return getattr(self.validation, "validate_" + name.lower())(value)

    @staticmethod
    def issue_data(report):
        return [{"code": issue.code, "path": [{"kind": part.kind, "value": part.value} for part in issue.path]} for issue in report.issues]

    def test_python_generated_reports_match_all_shared_cases_and_preserve_input(self):
        for case in self.cases:
            with self.subTest(case=case["name"]):
                value = self.construct(case["record"], case["value"])
                before = copy.deepcopy(value)
                report = self.report(case["record"], value)
                self.assertEqual(self.issue_data(report), case["issues"])
                self.assertEqual(report.is_valid(), not case["issues"])
                self.assertTrue(all(issue.message for issue in report.issues))
                self.assertEqual(value, before)

    def test_mutable_drafts_codec_calls_and_validation_reports_are_separate(self):
        with patch.object(self.validation, "validate_content", side_effect=AssertionError("implicit validation")) as validator:
            draft = self.construct("Content", {"kind": "text", "text": None, "number": None, "flag": None})
            encoded = encode(self.schema, "Content", wire_value(draft))
            self.assertEqual(decode(self.schema, "Content", encoded), wire_value(draft))
            draft.text = "ready"
            validator.assert_not_called()
        draft.text = None
        old = self.validation.validate_content(draft)
        self.assertFalse(old.is_valid())
        draft.text = "repaired"
        current = self.validation.validate_content(draft)
        self.assertTrue(current.is_valid())
        self.assertFalse(old.is_valid())
        with self.assertRaises(FrozenInstanceError):
            current.issues = ()
        draft.number = 0
        self.assertFalse(self.validation.validate_content(draft).is_valid())

    def test_virtual_group_has_no_runtime_tag_and_no_generated_validator(self):
        value = self.api.VirtualContent(text="unchecked", number=0, flag=False)
        self.assertNotIn("kind", [field.name for field in fields(value)])
        self.assertFalse(hasattr(self.validation, "validate_virtual_content"))
        self.assertNotIn("pub fn validate_virtual_content", self.rust)
        self.assertEqual(decode(self.schema, "VirtualContent", encode(self.schema, "VirtualContent", wire_value(value))), wire_value(value))

    def test_invalid_python_discriminator_and_wrong_record_return_reports(self):
        wrong = self.validation.validate_content(object())
        self.assertEqual(wrong.issues[0].code, "validation.type_mismatch")
        draft = self.construct("Content", {"kind": "text", "text": "ok"})
        draft.kind = None
        self.assertEqual(self.validation.validate_content(draft).issues[0].code, "oneof.discriminator_invalid")
        replacement = PythonEnum("ContentKind", {"text": 0, "number": 1, "flag": 2, "empty": 3, "later": 4})
        with patch.object(self.api, "ContentKind", replacement):
            draft.kind = replacement.later
            self.assertEqual(self.validation.validate_content(draft).issues[0].code, "oneof.discriminator_invalid")

    def test_generating_validation_does_not_change_ordinary_data_or_codec_sources(self):
        for path, content in self.ordinary_files.items():
            self.assertEqual((self.root / path).read_bytes(), content, str(path))

    def rust_record(self, name, data):
        assignments = []
        for field in self.schema.messages[name].fields:
            value = data.get(field.name)
            if value is None:
                rendered = "None"
            else:
                if isinstance(field.type, EnumRef):
                    variant = "".join(part.capitalize() for part in value.split("_"))
                    rendered = f"api::{field.type.name}::{variant}"
                elif isinstance(field.type, MsgRef):
                    rendered = self.rust_record(field.type.name, value)
                elif field.type == Scalar("str"):
                    rendered = json.dumps(value) + ".to_owned()"
                elif field.type == Scalar("bool"):
                    rendered = "true" if value else "false"
                else:
                    rendered = str(value)
                if field.optional:
                    rendered = "Some(" + rendered + ")"
            assignments.append(field.name + ": " + rendered)
        return f"api::{name} {{ " + ", ".join(assignments) + f", ..api::{name}::default() }}"

    def test_rust_generated_reports_match_the_same_fixtures_and_python_results(self):
        lines = ['extern crate alloc;', '#[path = "rust/cbor.rs"] mod cbor;', '#[path = "rust/api.rs"] mod api;',
                 '#[path = "validation.rs"] mod validation;', 'fn main() {']
        expected_trace = []
        for index, case in enumerate(self.cases):
            name = case["record"]
            function = "validate_" + name.lower()
            lines.extend([f"    let value{index} = {self.rust_record(name, case['value'])};",
                          f"    let before{index} = value{index}.clone();",
                          f"    let report = validation::{function}(&value{index});",
                          f"    assert_eq!(value{index}, before{index});",
                          f"    println!(\"{{}}|{{}}\", {json.dumps(case['name'])}, report.is_valid());",
                          '    for issue in report.issues() {',
                          '        let path = issue.path.iter().map(|part| match part {',
                          '            validation::PathSegment::Field(name) => format!("field:{name}"),',
                          '            validation::PathSegment::Index(index) => format!("index:{index}"),',
                          '            validation::PathSegment::Key(key) => format!("key:{key}"),',
                          '        }).collect::<Vec<_>>().join("/");',
                          '        println!("{}|{}|{}", issue.code, path, issue.message);', '    }'])
            python_report = self.report(name, self.construct(name, case["value"]))
            self.assertEqual(self.issue_data(python_report), case["issues"])
            expected_trace.append(case["name"] + "|" + str(python_report.is_valid()).lower())
            expected_trace.extend(issue.code + "|" + "/".join(f"{part.kind}:{part.value}" for part in issue.path) + "|" + issue.message for issue in python_report.issues)
        lines.extend(['    let mut draft = api::Content::default();',
                      '    let bytes = cbor::encode(&draft.to_cbor());',
                      '    assert_eq!(api::Content::decode(&bytes).unwrap(), draft);',
                      '    let old = validation::validate_content(&draft);',
                      '    assert!(!old.is_valid());',
                      '    draft.text = Some("repaired".to_owned());',
                      '    assert!(validation::validate_content(&draft).is_valid());',
                      '    assert!(!old.is_valid());', '}'])
        (self.root / "main.rs").write_text("\n".join(lines))
        binary = self.root / "probe"
        compiled = subprocess.run(["rustc", "--edition", "2024", "--cap-lints", "allow", str(self.root / "main.rs"), "-o", str(binary)], capture_output=True, text=True, timeout=60)
        self.assertEqual(compiled.returncode, 0, compiled.stderr)
        executed = subprocess.run([str(binary)], capture_output=True, text=True, timeout=10)
        self.assertEqual(executed.returncode, 0, executed.stderr)
        self.assertEqual(executed.stdout.splitlines(), expected_trace)

    def test_virtual_only_schema_emits_no_successful_noop_validator(self):
        _, source = compile_report_validators(load_schema(DIRECTORY / "oneof_virtual_fields.taut.py"))
        self.assertNotIn("pub fn validate_content", source[0])
        self.assertNotIn("def validate_content", source[1])

    def test_invalid_generated_names_and_empty_oneofs_fail_generation(self):
        kind = Enum("ExampleVariantChoice", value=0)
        alternatives = lambda: Msg(kind=F(1, OneOf(kind)), value=F(2, dsl.STR, Case(kind=kind.value)))
        source = dsl.schema(kind, TestEntry=alternatives(), testEntry=alternatives())
        with self.assertRaisesRegex(ValueError, "function-name collision"):
            compile_report_validators(source)
        empty = Enum("Empty")
        source = dsl.schema(empty, Entry=Msg(kind=F(1, OneOf(empty))))
        with self.assertRaisesRegex(ValueError, "at least one alternative"):
            compile_report_validators(source)

    def test_container_constraints_are_rejected_instead_of_silently_skipped(self):
        child = load_schema(DIRECTORY / "oneof_fields.taut.py")
        kind = Enum("OuterKind", items=0)
        wrapper = Msg(kind=F(1, OneOf(kind)), items=F(2, dsl.List(dsl.Ref.Content), Case(kind=kind.items)))
        source = dsl.schema(*child.enums.values(), *child.messages.values(), kind, Outer=wrapper)
        with self.assertRaisesRegex(ValueError, "outside this report probe"):
            compile_report_validators(source)


if __name__ == "__main__":
    unittest.main()
