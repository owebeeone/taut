"""A different graph vocabulary must compile without application-aware helpers."""

from dataclasses import replace
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

from taut.gen.scaffold import emit
from taut.ir.dsl import STR, Enum, Map, Ref, schema
from taut.ir.load import load_schema
from taut_app_probe import F, Msg, annotate, app, properties, from_probe_json, to_probe_json
from graph_contract_probe import GraphIndex, GraphLink, GraphRules, ReferenceCheck, Tagged, compile_graph_contract

NS = "example.links"


def sample():
    return schema(
        Choice=Enum(typed=0, scalar=1),
        Pointer=Msg(token=F(1, STR), next_id=2),
        Empty=Msg(next_id=1),
        Cell=Msg(
            GraphRules(NS, tagged=Tagged("which", {"typed": "object_data", "scalar": "text_data"})),
            which=F(1, Ref.Choice),
            object_data=F(2, Ref.Empty, optional=True),
            text_data=F(3, Ref.Empty, optional=True),
            next_id=4,
        ),
        Registry=Msg(catalog=F(1, Map(STR, Ref.Cell), GraphIndex(NS, reference="Pointer", key="token")), next_id=2),
        Need=Msg(
            GraphRules(NS, references=ReferenceCheck("Registry", "validate_choice")),
            selected=F(1, Ref.Pointer, GraphLink(NS, index="Registry.catalog", select=["typed"], null="reject")),
            next_id=2,
        ),
    )


def transform_message(original, name, change):
    messages = dict(original.messages)
    messages[name] = change(messages[name])
    return replace(original, messages=messages)


def replace_property(definition, payload):
    # Rebuild annotations explicitly, rather than append a duplicate namespace.
    return replace(definition, app_properties=(app(NS, payload),))


class CompleteGraphContractProbeTests(unittest.TestCase):
    def test_alternate_names_emit_actual_typed_lookup_and_payload_selection(self):
        restored = from_probe_json(json.loads(json.dumps(to_probe_json(sample()))))
        code = compile_graph_contract(restored, NS)
        self.assertIn("graph.catalog.get(&reference.token)", code)
        self.assertIn("value.object_data.is_none()", code)
        self.assertIn("target0.which != r::Choice::Typed", code)
        self.assertNotIn("node_id", code)
        self.assertNotIn("GraphDocument", code)
        self.assertNotIn("check_reference(", code)

    def test_self_contained_authored_contract_generates_lookup_without_a_side_table(self):
        model = load_schema(Path(__file__).with_name("graph_contract.taut.py"))
        code = compile_graph_contract(model, "garns.graph")
        self.assertIn("graph.nodes.get(&reference.node_id)", code)
        self.assertIn("target1.view != r::DeclarationView::TypeView", code)
        self.assertNotIn("check_reference(", code)

    def test_missing_index_contract_stops_generation(self):
        original = sample()
        broken = transform_message(original, "Registry", lambda message: replace(message, fields=tuple(
            replace(field, app_properties=()) for field in message.fields)))
        with self.assertRaisesRegex(ValueError, "unknown or wrong-context index"):
            compile_graph_contract(broken, NS)

    def test_wrong_reference_key_or_target_case_stops_generation(self):
        original = sample()
        for mode in ("wrong-key", "wrong-case"):
            with self.subTest(mode=mode):
                message_name = "Registry" if mode == "wrong-key" else "Need"
                def alter(message):
                    field = message.fields[0]
                    metadata = properties(field)[NS]
                    if mode == "wrong-key":
                        metadata["index"]["key"] = "missing_key"
                    else:
                        metadata["link"]["select"] = ["unknown"]
                    return replace(message, fields=(replace_property(field, metadata),))
                broken = transform_message(original, message_name, alter)
                with self.assertRaises(ValueError):
                    compile_graph_contract(broken, NS)

    def test_missing_union_cases_and_contradictory_null_policy_are_rejected(self):
        original = sample()
        cell = original.messages["Cell"]
        metadata = properties(cell)[NS]
        del metadata["tagged"]["cases"]["typed"]
        broken = transform_message(original, "Cell", lambda _: replace_property(cell, metadata))
        with self.assertRaisesRegex(ValueError, "cover its enum exactly"):
            compile_graph_contract(broken, NS)
        need = original.messages["Need"]
        metadata = properties(need.fields[0])[NS]
        metadata["link"]["null"] = "absent"
        broken = transform_message(original, "Need", lambda _: replace(need, fields=(replace_property(need.fields[0], metadata),)))
        with self.assertRaisesRegex(ValueError, "Null policy"):
            compile_graph_contract(broken, NS)

    def test_a_link_without_a_generated_entry_cannot_be_silently_ignored(self):
        original = sample()
        broken = transform_message(original, "Need", lambda message: replace(message, app_properties=()))
        with self.assertRaisesRegex(ValueError, "no checking entry"):
            compile_graph_contract(broken, NS)

    def test_generated_rust_compiles_and_runs_with_unrelated_graph_names(self):
        original = sample()
        restored = from_probe_json(json.loads(json.dumps(to_probe_json(original))))
        with tempfile.TemporaryDirectory(prefix="taut-direct-links-") as temporary:
            root = Path(temporary)
            emit(restored, root, langs=["rust"], services=[], runtime=True)
            (root / "checks.rs").write_text(compile_graph_contract(restored, NS))
            (root / "main.rs").write_text('''
extern crate alloc;
#[path = "rust/cbor.rs"] mod cbor;
#[path = "rust/api.rs"] mod r;
include!("checks.rs");
fn main() {
    let mut graph = r::Registry::default();
    let link = r::Need { selected: r::Pointer { token: "same".to_owned() } };
    assert!(matches!(validate_choice(&graph, &link), Err(ProbeGraphError::MissingTarget(_))));
    graph.catalog.insert("same".to_owned(), r::Cell {
        which: r::Choice::Typed, object_data: None, text_data: None,
    });
    // A semantically invalid draft remains constructible and serializable.
    let encoded = cbor::encode(&graph.to_cbor());
    let decoded = r::Registry::decode(&encoded).unwrap();
    assert_eq!(decoded, graph);
    assert!(matches!(validate_choice(&graph, &link), Err(ProbeGraphError::InvalidPayload(_))));
    graph.catalog.get_mut("same").unwrap().object_data = Some(r::Empty::default());
    let repaired = graph.clone();
    validate_choice(&graph, &link).unwrap();
    assert_eq!(graph, repaired);
    let repeated = r::Need { selected: r::Pointer { token: "same".to_owned() } };
    validate_choice(&graph, &repeated).unwrap();
    assert_eq!(graph.catalog.len(), 1);
    graph.catalog.get_mut("same").unwrap().which = r::Choice::Scalar;
    assert!(matches!(validate_choice(&graph, &link), Err(ProbeGraphError::InvalidPayload(_))));
    let cell = graph.catalog.get_mut("same").unwrap();
    cell.object_data = None;
    cell.text_data = Some(r::Empty::default());
    assert!(matches!(validate_choice(&graph, &link), Err(ProbeGraphError::WrongTarget(_))));
}
''')
            binary = root / "probe"
            compiled = subprocess.run(["rustc", "--edition", "2024", "--cap-lints", "allow", str(root / "main.rs"), "-o", str(binary)], text=True, capture_output=True, timeout=60)
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            executed = subprocess.run([str(binary)], text=True, capture_output=True, timeout=10)
            self.assertEqual(executed.returncode, 0, executed.stderr)


if __name__ == "__main__":
    unittest.main()
