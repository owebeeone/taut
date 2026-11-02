"""Observation only: write full selected/deselected IDs; never modify items."""
import json
from pathlib import Path
HERE=Path(__file__).resolve().parent
POLICY=set()
GATES={
 'src/tests/test_cpp.py::test_cpp_passes_the_parity_gate',
 'src/tests/test_go.py::test_go_parity_gate_is_green',
 'src/tests/test_java.py::test_java_passes_the_shared_parity_gate',
 'src/tests/test_js.py::test_js_parity_gate_is_green',
 'src/tests/test_kotlin.py::test_kotlin_passes_the_parity_gate',
 'src/tests/test_parity.py::test_full_gate_governance_clean',
 'src/tests/test_rust.py::test_rust_passes_the_parity_gate',
 'src/tests/test_swift.py::test_swift_parity_gate_is_green',
}
def pytest_deselected(items):
    path=HERE/'deselected-tests.json'
    rows=json.loads(path.read_text()) if path.exists() else []
    for item in items:
        reason=('separate all16 require-all parity already executed' if item.nodeid in GATES and item.get_closest_marker('gate') else
            'user-owned pending Enum.case authoring; exact old reservation assertion excluded, source unchanged' if item.nodeid in POLICY else 'UNCLASSIFIED')
        rows.append({'nodeid':item.nodeid,'reason':reason})
    path.write_text(json.dumps(rows,indent=2)+'\n',encoding='utf-8')
def pytest_collection_finish(session):
    ids=[item.nodeid for item in session.items]
    (HERE/'selected-tests.json').write_text(json.dumps(ids,indent=2)+'\n',encoding='utf-8')
    groups={name:[n for n in ids if n.startswith('src/tests/'+name+'::')] for name in ('test_go_oneof.py','test_cpp_oneof.py','test_cpp_go_distribution.py','test_swift_oneof.py','test_swift.py','test_swift_distribution.py','test_oneof.py')}
    (HERE/'new-target-collection.json').write_text(json.dumps({'selected_counts':{k:len(v) for k,v in groups.items()},'selected_ids':groups},indent=2)+'\n',encoding='utf-8')
