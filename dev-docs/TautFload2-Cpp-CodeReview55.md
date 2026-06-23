# Taut Float Phase 2 C++ Code Review 55

## Findings

1. [P2] `src/tests/test_cpp.py` is untracked, so the required Phase 2 C++ test coverage is not in the tracked diff.

   References: `src/tests/test_cpp.py:1`; `git status --short` reports `?? src/tests/test_cpp.py`, while `git diff --name-only` lists only `src/taut/gen/cpp.py` and `src/taut/gen/runtime/cbor.hpp`.

   The Phase 2 base brief requires extending `src/tests/test_<lang>.py` and compiling a float `static_assert` harness when a C++20 compiler is present. With the current tracked diff, those tests can be omitted from the final commit and CI/review would see only the implementation files.

2. [P2] The new float map codegen path is only string-checked, and the exact schema used by the test does not compile as C++20 in the constexpr generated path on this toolchain.

   References: `src/tests/test_cpp.py:15` defines a `Map(INT, FLOAT)` field; `src/tests/test_cpp.py:29` only inspects emitted text; `src/taut/gen/cpp.py:108` emits a `std::map` range-for in generated `to_cbor`; `src/taut/gen/cpp.py:139` declares that generated `to_cbor` as `constexpr`.

   I compiled `_emit_types(S)` for the test schema with `c++ -std=c++20` in a temp directory. It failed before the float runtime was reached because `std::map` iterators are non-literal under Apple clang/libc++ C++20: "variable of non-literal type 'const_iterator' ... cannot be defined in a constexpr function before C++23". The scalar/list float generated header compiled and static-asserted successfully. This may be a pre-existing C++ map/constexpr limitation, but the new test advertises `Map(INT, FLOAT)` coverage without compiling that path.

## Runtime Parity Notes

I did not find correctness issues in the changed float runtime paths in `src/taut/gen/runtime/cbor.hpp`: `Buf::float_`, half/single/double width selection, NaN canonicalization, `-0.0` preservation, major-7 decode for info 25/26/27, or `encode_value` re-emission all matched the Phase 2 brief in the probes below.

Residual risks: I only had Apple clang 21 available, not a compiler matrix; the shared generated C++ corpus does not yet include Phase 3 float-bearing GripLab rows; and the map/constexpr issue above remains outside the scalar/list float path.

## Commands Inspected Or Run

- `sed -n '1,260p' dev-docs/TautFloatP2-Base.md`
- `sed -n '1,320p' dev-docs/TautFloatP2-Cpp.md`
- `git diff -- src/taut/gen/runtime/cbor.hpp`
- `git diff -- src/taut/gen/cpp.py`
- `sed -n '1,260p' src/tests/test_cpp.py`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m pytest -q src/tests/test_cpp.py -p no:cacheprovider` failed because the default Python has no `pytest` module.
- Manual Python assertion plus C++20 compile of the float corpus static-assert harness: passed.
- C++ runtime probe comparing `Buf::float_` against Python `_float_bytes` for 20,018 raw double bit patterns: passed.
- C++ decode probe comparing half/f32 widening against Python for all non-NaN half values and 20,003 f32 probes: passed.
- C++20 compile-time re-emit probes for half, single, and double signaling NaNs: passed.
- C++20 compile of generated scalar/list float header with static asserts: passed.
- C++20 compile of generated `Map(INT, FLOAT)` header from the new test schema: failed as described in finding 2.
