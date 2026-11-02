"""Explicit discriminator syntax and opt-in generated validator feasibility."""

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from taut.gen.scaffold import emit
from taut.ir import dsl
from taut.ir.export import schema_json
from taut.ir.load import load_schema
from taut.ir.model import EnumRef
from taut_app_probe import properties
from taut_app_probe import from_probe_json, to_probe_json
from oneof_fields_probe import Case, Enum, EnumMember, F, Msg, OneOf, compile_validators, normalize_oneofs, NAMESPACE
from graph_contract_probe import Contract


DIRECTORY = Path(__file__).parent


def lifecycle_schema():
    kind = Enum("ContentKind", text=0, number=1, flag=2, empty=3)
    return dsl.schema(
        kind,
        Content=Msg(
            kind=F(1, OneOf(kind)),
            text=F(2, dsl.STR, Case(kind=kind.text)),
            number=F(3, dsl.INT, Case(kind=kind.number)),
            flag=F(4, dsl.BOOL, Case(kind=kind.flag)),
            next_id=5,
        ),
    )


class FieldLocalOneOfProbeTests(unittest.TestCase):
    def test_authored_example_has_explicit_enum_discriminator_and_nominated_cases(self):
        source = load_schema(DIRECTORY / "oneof_fields.taut.py")
        record = source.messages["Content"]
        self.assertTrue(record.fields[0].oneof)
        self.assertIsInstance(record.fields[0].type, EnumRef)
        self.assertEqual(record.fields[0].type.name, "ContentKind")
        self.assertFalse(record.fields[0].optional)
        nomination = record.fields[1].cases[0]
        self.assertEqual(nomination.tag, "kind")
        self.assertIsInstance(nomination.member, EnumMember)
        self.assertEqual(nomination.member.enum.name, "ContentKind")
        self.assertEqual(nomination.member.name, "text")
        self.assertEqual(nomination.member.value, 0)
        self.assertTrue(record.fields[1].optional)
        normalized, code = compile_validators(source)
        self.assertIn("pub fn validate_content", code)
        self.assertEqual(normalize_oneofs(normalized), normalized)

    def test_normalized_constraints_survive_the_explicit_probe_json_round_trip(self):
        normalized, code = compile_validators(lifecycle_schema())
        restored = from_probe_json(json.loads(json.dumps(to_probe_json(normalized))))
        self.assertEqual(restored, normalized)
        # All validator mechanics remain recoverable from portable normalized data.
        self.assertEqual(Contract(restored, NAMESPACE).emit(), Contract(normalized, NAMESPACE).emit())
        self.assertIn("pub fn validate_content", code)

    def test_existing_enum_and_nullable_payload_layout_is_unchanged(self):
        source = load_schema(DIRECTORY / "oneof_fields.taut.py")
        plain = dsl.schema(
            ContentKind=dsl.Enum(text=0, number=1, empty=2),
            Content=dsl.Msg(kind=dsl.F(1, dsl.Ref.ContentKind),
                            text=dsl.F(2, dsl.STR, optional=True),
                            number=dsl.F(3, dsl.INT, optional=True), next_id=4),
        )
        self.assertEqual(schema_json(source), schema_json(plain))
        # Unannotated calls keep exactly the original constructors.
        self.assertEqual(F(1, dsl.STR), dsl.F(1, dsl.STR))
        self.assertEqual(Msg(label=F(1, dsl.STR)), dsl.Msg(label=dsl.F(1, dsl.STR)))

    def test_virtual_flag_defaults_false_and_requires_a_boolean(self):
        kind = Enum("Kind", text=0)
        self.assertEqual(OneOf(kind), OneOf(kind, virtual=False))
        for flag in ("true", 1, None):
            with self.subTest(flag=flag), self.assertRaises(TypeError):
                OneOf(kind, virtual=flag)

    def test_exhaustive_flag_defaults_false_and_requires_a_boolean(self):
        kind = Enum("Kind", text=0)
        self.assertEqual(OneOf(kind), OneOf(kind, exhaustive=False))
        for flag in ("false", 0, None):
            with self.subTest(flag=flag), self.assertRaises(TypeError):
                OneOf(kind, exhaustive=flag)

    def test_implicit_unit_cases_normalize_and_survive_transport(self):
        kind = Enum("Kind", text=0, empty=1, absent=2)
        source = dsl.schema(kind, Entry=Msg(
            kind=F(1, OneOf(kind)), text=F(2, dsl.STR, Case(kind=kind.text))))
        normalized = normalize_oneofs(source)
        self.assertEqual(properties(normalized.messages["Entry"])[NAMESPACE]["tagged"]["cases"],
                         {"text": "text", "empty": None, "absent": None})
        coverage = properties(normalized.messages["Entry"])[NAMESPACE + ".coverage"]
        self.assertEqual(coverage, {"discriminator": "kind", "exhaustive": False,
                                    "implicit_units": ["empty", "absent"]})
        restored = from_probe_json(json.loads(json.dumps(to_probe_json(normalized))))
        self.assertEqual(restored, normalized)
        self.assertEqual(normalize_oneofs(restored), restored)

    def test_exhaustive_coverage_is_independent_of_virtual_storage(self):
        kind = Enum("EntryKind", text=0, empty=1)
        for virtual in (False, True):
            with self.subTest(virtual=virtual):
                partial = dsl.schema(kind, Entry=Msg(
                    kind=F(1, OneOf(kind, virtual=virtual, exhaustive=True)),
                    text=F(2, dsl.STR, Case(kind=kind.text))))
                with self.assertRaisesRegex(ValueError, "cover every enum member"):
                    normalize_oneofs(partial)
                complete = dsl.schema(kind, Entry=Msg(
                    kind=F(1, OneOf(kind, virtual=virtual, exhaustive=True)),
                    text=F(2, dsl.STR, Case(kind=kind.text)),
                    other=F(3, dsl.INT, Case(kind=kind.empty))))
                normalized, code = compile_validators(complete)
                coverage = properties(normalized.messages["Entry"])[NAMESPACE + ".coverage"]
                self.assertTrue(coverage["exhaustive"])
                self.assertEqual(coverage["implicit_units"], [])
                self.assertEqual("pub fn validate_entry" in code, not virtual)

    def test_non_exhaustive_enum_with_no_payload_fields_is_accepted(self):
        kind = Enum("EntryKind", empty=0)
        source = dsl.schema(kind, Entry=Msg(kind=F(1, OneOf(kind))))
        normalized, code = compile_validators(source)
        self.assertEqual(properties(normalized.messages["Entry"])[NAMESPACE]["tagged"]["cases"],
                         {"empty": None})
        self.assertIn("pub fn validate_entry", code)

    def test_standalone_cases_are_rejected(self):
        kind = Enum("EntryKind", text=0, empty=1)
        with self.assertRaisesRegex(ValueError, "Case belongs on a payload field"):
            Msg(Case(kind=kind.empty), kind=F(1, OneOf(kind)))

    def test_virtual_discriminator_has_no_storage_wire_field_or_validator(self):
        source = load_schema(DIRECTORY / "oneof_virtual_fields.taut.py")
        normalized, code = compile_validators(source)
        record = normalized.messages["Content"]
        self.assertEqual([field.name for field in record.fields], ["text", "number"])
        self.assertEqual([field.tag for field in record.fields], [2, 3])
        metadata = properties(record)[NAMESPACE + ".virtual"]
        self.assertEqual(metadata["validation"], "deferred")
        self.assertFalse(metadata["runtime_field"])
        self.assertFalse(metadata["wire_field"])
        self.assertNotIn("pub fn validate_content", code)
        self.assertEqual(from_probe_json(json.loads(json.dumps(to_probe_json(normalized)))), normalized)
        with tempfile.TemporaryDirectory(prefix="taut-virtual-oneof-") as temporary:
            root = Path(temporary)
            emit(normalized, root, langs=["rust"], services=[], runtime=True)
            self.assertNotIn("pub kind:", (root / "rust/api.rs").read_text())
            (root / "main.rs").write_text('''extern crate alloc;
#[path = "rust/cbor.rs"] mod cbor;
#[path = "rust/api.rs"] mod api;
fn main() {
    let mut draft = api::Content::default();
    draft.text = Some("not validated in this cut".to_owned());
    draft.number = Some(0);
    let bytes = cbor::encode(&draft.to_cbor());
    assert_eq!(api::Content::decode(&bytes).unwrap(), draft);
}
''')
            binary = root / "probe"
            compiled = subprocess.run(["rustc", "--edition", "2024", "--cap-lints", "allow", str(root / "main.rs"), "-o", str(binary)], capture_output=True, text=True, timeout=60)
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            executed = subprocess.run([str(binary)], capture_output=True, text=True, timeout=10)
            self.assertEqual(executed.returncode, 0, executed.stderr)
            source_text = (root / "main.rs").read_text().replace("let bytes =", "let _ = draft.kind;\n    let bytes =")
            (root / "main.rs").write_text(source_text)
            unavailable = subprocess.run(["rustc", "--edition", "2024", "--cap-lints", "allow", str(root / "main.rs"), "-o", str(binary)], capture_output=True, text=True, timeout=60)
            self.assertNotEqual(unavailable.returncode, 0)
            self.assertIn("no field `kind`", unavailable.stderr)

    def test_virtual_group_schema_still_requires_correct_case_nominations(self):
        kind = Enum("Kind", text=0)
        wrong = Enum("Wrong", text=0)
        source = dsl.schema(kind, wrong, Content=Msg(
            kind=F(1, OneOf(kind, virtual=True)),
            text=F(2, dsl.STR, Case(kind=wrong.text))))
        with self.assertRaisesRegex(ValueError, "different enum"):
            normalize_oneofs(source)

    def test_qualified_members_reject_a_different_enum_with_the_same_member_name(self):
        kind = Enum("Kind", text=0)
        other = Enum("OtherKind", text=0)
        source = dsl.schema(kind, other, Entry=Msg(
            kind=F(1, OneOf(kind)), payload=F(2, dsl.STR, Case(kind=other.text))))
        with self.assertRaisesRegex(ValueError, "different enum"):
            normalize_oneofs(source)
        with self.assertRaises(AttributeError):
            _ = kind.missing
        with self.assertRaises(ValueError):
            Enum("Collision", members=0)

    def test_script_entry_regenerates_qualified_member_schema_in_a_fresh_process(self):
        checked = subprocess.run([sys.executable, str(DIRECTORY / "oneof_fields_probe.py"), "--check"],
                                 capture_output=True, text=True, timeout=30)
        self.assertEqual(checked.returncode, 0, checked.stderr)

    def test_keyword_case_requires_one_typed_nomination(self):
        kind = Enum("Kind", text=0)
        self.assertEqual(Case(kind=kind.text), Case("kind", kind.text))
        for arguments in ({}, {"kind": "text"}, {"kind": kind.text, "other": kind.text}):
            with self.subTest(arguments=arguments), self.assertRaises(TypeError):
                Case(**arguments)

    def test_case_must_nominate_a_marked_field_and_known_enum_member(self):
        for kind, case in ((dsl.Ref.Kind, Case("kind", "text")),
                           (OneOf(dsl.Ref.Kind), Case("other", "text")),
                           (OneOf(dsl.Ref.Kind), Case("kind", "missing"))):
            with self.subTest(kind=repr(kind), case=case), self.assertRaises(ValueError):
                source = dsl.schema(Kind=dsl.Enum(text=0), Entry=Msg(kind=F(1, kind), payload=F(2, dsl.STR, case)))
                normalize_oneofs(source)

    def test_empty_duplicate_or_non_enum_discriminators_are_rejected(self):
        examples = (
            lambda: dsl.schema(Kind=dsl.Enum(text=0), Entry=Msg(kind=F(1, OneOf(dsl.Ref.Kind, exhaustive=True)))),
            lambda: dsl.schema(Kind=dsl.Enum(text=0), Entry=Msg(kind=F(1, OneOf(dsl.Ref.Kind)),
                left=F(2, dsl.STR, Case("kind", "text")), right=F(3, dsl.STR, Case("kind", "text")))),
            lambda: dsl.schema(Entry=Msg(kind=F(1, OneOf(dsl.STR)))),
        )
        for example in examples:
            with self.subTest(example=example), self.assertRaises(ValueError):
                normalize_oneofs(example())
        with self.assertRaises(ValueError):
            F(1, OneOf(dsl.Ref.Kind), optional=True)
        with self.assertRaises(ValueError):
            F(1, dsl.STR, Case("kind", "text"), optional=False)

    def test_generated_validator_is_explicit_and_preserves_zero_false_empty_and_unit_cases(self):
        normalized, code = compile_validators(lifecycle_schema())
        with tempfile.TemporaryDirectory(prefix="taut-field-oneof-") as temporary:
            root = Path(temporary)
            emit(normalized, root, langs=["rust"], services=[], runtime=True)
            (root / "validation.rs").write_text(code)
            (root / "main.rs").write_text('''
extern crate alloc;
#[path = "rust/cbor.rs"] mod cbor;
#[path = "rust/api.rs"] mod api;
mod validation {
    use super::api as r;
    include!("validation.rs");
}
fn main() {
    let mut draft = api::Content::default();
    // A selected-but-missing payload is constructible and serializable.
    let bytes = cbor::encode(&draft.to_cbor());
    let decoded = api::Content::decode(&bytes).unwrap();
    assert_eq!(decoded, draft);
    assert!(validation::validate_content(&draft).is_err());
    draft.kind = api::ContentKind::Number;
    draft.number = Some(0);
    let before = draft.clone();
    validation::validate_content(&draft).unwrap();
    assert_eq!(before, draft);
    draft.number = None;
    draft.kind = api::ContentKind::Flag;
    draft.flag = Some(false);
    validation::validate_content(&draft).unwrap();
    draft.flag = None;
    draft.kind = api::ContentKind::Text;
    draft.text = Some(String::new());
    validation::validate_content(&draft).unwrap();
    draft.text = None;
    draft.kind = api::ContentKind::Empty;
    validation::validate_content(&draft).unwrap();
    draft.text = Some("unexpected".to_owned());
    assert!(validation::validate_content(&draft).is_err());
}
''')
            binary = root / "probe"
            compiled = subprocess.run(["rustc", "--edition", "2024", "--cap-lints", "allow", str(root / "main.rs"), "-o", str(binary)], capture_output=True, text=True, timeout=60)
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            executed = subprocess.run([str(binary)], capture_output=True, text=True, timeout=10)
            self.assertEqual(executed.returncode, 0, executed.stderr)


if __name__ == "__main__":
    unittest.main()
