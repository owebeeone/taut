# Settled all-nine integration gate — Swift r0

Exact-source read/run gate; this is not an independent review axis. No product changes or corrective reruns were performed.

```json
{
  "shape_python": "c08c2a1b5197f761c5b0b835c588da512130ceda",
  "shape_rust": "8e92b89ed3a4f218a5a4e018fbfee6301fcc14b4",
  "shape_ts": "1aaeab65e4564a462044d2f5d824cd2f375aae97",
  "taut": "c02765930f06cfcb19a522843aa54582db514706",
  "workspace": "a8f37984471654902149d136b7a13a588346b58f"
}
```

All 16 existing codec variants ran GREEN with require_all=True/jobs=2; 0 governance violations.

Broad: 2260 passed, 3 failed, 5 skipped, 8 deselected; 2268 selected. Pytest exit 1. Total gate elapsed 1213.7 seconds.

Demonstrated baseline failures: 3. New failures: 0. All exact tracebacks are in broad-regression-tests.log and failure-*.txt; machine details in global-results.json.

Baseline failures kept enabled: missing historical proto-surface document, two Windows Go CRLF/gofmt checks. Updated enum.case authoring and metadata tests stayed enabled. Only the eight duplicate parity marker tests were deselected.

## Commands

```text
taut.corpus.parity.run_gate(require_all=True,jobs=2)
C:\Users\gianni\AppData\Roaming\uv\python\cpython-3.13.5-windows-x86_64-none\python.exe -m pytest D:\projects\limbo\taut-dev\taut\src\tests -q -m "not gate" -p no:cacheprovider -p collection_receipt --basetemp D:\projects\limbo\swift-oneof-scratch\global-gate-r0\pytest-temp --junitxml D:\projects\limbo\swift-oneof-scratch\global-gate-r0\broad-results.xml
```

Executed from the assigned scratch directory using stable CPython3.13.5, pytest9.1.1, activated toolchains, UTF8 JVM, disabled third-party pytest plugin autoload, isolated process-local Git trust, scratch caches/temp. See environment.json and run-gate.ps1.

## Integrity

All five HEADs, 718 selected source files, 736 raw committed-blob comparisons, all45 Swift owned files including Preparation self, protected5, excluded35, five indices, and 47 locks/manifests remained identical. Counts are derived from JSON. GWZ before/after records classify any permitted untracked review evidence.

Accepted unchanged ECMA library R1 receipts were associated using the original full28 inventory overridden by R1 changed11 hashes. All28 source files, dependency lock, and corrected typecheck/build/test315 log hashes matched. No new standalone library run or dependency install was performed.

## Failures

baseline_failures:
- test_dev_docs::test_proto_api_surface_extensions_doc_exists_and_covers_contract
- test_go::test_generated_go_is_gofmt_clean
- test_go::test_go_runtime_and_parity_runner_are_gofmt_clean

new_failures:

## Skips

- src.tests.test_js_oneof::test_obstructed_or_alias_owner_unchanged[symlink] — Windows symlink privilege unavailable; junction coverage is separate
- src.tests.test_parity::test_java_tools_come_from_java_home_first — fake tools are shell scripts
- src.tests.test_parity::test_kotlinc_comes_from_the_kotlinc_variable_with_the_java_it_runs_with — fake tools are shell scripts
- src.tests.test_parity::test_a_missing_toolchain_is_none — PATH isolation uses POSIX paths
- src.tests.test_rust::test_rust_runtime_keeps_long_lengths_whole_on_a_32_bit_target — the wasm32-unknown-unknown target is not installed

## Deselections

- src/tests/test_cpp.py::test_cpp_passes_the_parity_gate — separate all16 require-all parity already executed
- src/tests/test_go.py::test_go_parity_gate_is_green — separate all16 require-all parity already executed
- src/tests/test_java.py::test_java_passes_the_shared_parity_gate — separate all16 require-all parity already executed
- src/tests/test_js.py::test_js_parity_gate_is_green — separate all16 require-all parity already executed
- src/tests/test_kotlin.py::test_kotlin_passes_the_parity_gate — separate all16 require-all parity already executed
- src/tests/test_parity.py::test_full_gate_governance_clean — separate all16 require-all parity already executed
- src/tests/test_rust.py::test_rust_passes_the_parity_gate — separate all16 require-all parity already executed
- src/tests/test_swift.py::test_swift_parity_gate_is_green — separate all16 require-all parity already executed

## Feature collection and outcomes

| Module | Passed | Failed | Skipped | Selected |
|---|---:|---:|---:|---:|
| test_cpp_go_distribution | 11 | 0 | 0 | 11 |
| test_cpp_oneof | 88 | 0 | 0 | 88 |
| test_go_oneof | 145 | 0 | 0 | 145 |
| test_java_oneof | 105 | 0 | 0 | 105 |
| test_js_oneof | 75 | 0 | 1 | 76 |
| test_js_ts_distribution | 29 | 0 | 0 | 29 |
| test_jvm_compiler_distribution | 1 | 0 | 0 | 1 |
| test_kotlin_oneof | 56 | 0 | 0 | 56 |
| test_oneof | 93 | 0 | 0 | 93 |
| test_python_runtime_distribution | 47 | 0 | 0 | 47 |
| test_rust_oneof | 90 | 0 | 0 | 90 |
| test_swift | 30 | 0 | 0 | 30 |
| test_swift_distribution | 1 | 0 | 0 | 1 |
| test_swift_oneof | 116 | 0 | 0 | 116 |
| test_typescript_oneof | 72 | 0 | 0 | 72 |
