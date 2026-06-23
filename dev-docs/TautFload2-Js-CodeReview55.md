# Taut Float Phase 2 JS Code Review 55

## Findings

No correctness findings found.

I did not find any blocking or non-blocking implementation defects in the uncommitted JavaScript float changes. The runtime paths in `src/taut/gen/runtime/cbor.js:66`, `src/taut/gen/runtime/cbor.js:118`, and `src/taut/gen/runtime/cbor.js:196` match the Phase 2 wire profile: NaN canonicalization happens before width selection, `-0.0` is preserved through bit-sensitive equality, half narrowing is direct round-to-nearest-even, single narrowing uses `Math.fround`, and decode accepts CBOR float additional-info 25/26/27. The generator changes in `src/taut/gen/js.py:13`, `src/taut/gen/js.py:30`, and `src/taut/gen/js.py:95` also align with the required `CFloat(...)` encode shape and `.f` decode shape.

## Residual Risks / Test Gaps

- The runtime parity coverage is currently a standalone Node harness at `src/tests/js_float_parity.js:31`. I ran it manually and it passes, but `run_tests.py:23` only invokes pytest, and the Python-side coverage in `src/tests/test_js.py:36` is a shape test rather than a runtime byte-parity test. If the project expects normal CI to be only `PYTHONPATH=src pytest src/tests -q`, JS float runtime regressions would not be caught unless the Node harness is wired into CI or documented as a separate required gate.
- The additional broad JS/Python parity sweeps I ran during review were ad hoc, not checked in. They increase confidence in half rounding and decode widening, but future protection still depends on the checked-in corpus harness.

## Scope Inspected

- `dev-docs/TautFloatP2-Base.md`
- `dev-docs/TautFloatP2-Js.md`
- Current `git diff`
- `src/taut/gen/runtime/cbor.js`
- `src/taut/gen/js.py`
- `src/tests/test_js.py`
- `src/tests/js_float_parity.js`
- `corpus/float_vectors.json`
- Python reference float behavior in `src/taut/wire/cbor.py`

## Commands Run

- `node src/tests/js_float_parity.js`  
  Result: `js float parity: 22 vectors ok`
- `PYTHONPATH=src python3 -m pytest src/tests/test_js.py -q`  
  Result: failed because `/opt/homebrew/opt/python@3.14/bin/python3.14` does not have `pytest` installed.
- `PYTHONPATH=src python3 -m pytest src/tests -q`  
  Result: failed for the same missing-`pytest` Python 3.14 environment.
- `PYTHONPATH=src pytest src/tests/test_js.py -q`  
  Result: `4 passed in 0.02s`
- `PYTHONPATH=src pytest src/tests -q`  
  Result: `166 passed in 0.16s`
- Ad hoc JS/Python encode parity sweep over 20,027 f64 bit patterns, including NaNs, infinities, half/single boundaries, and random payloads.  
  Result: all matched the Python reference.
- Ad hoc JS/Python half decode sweep over all 65,536 half payloads.  
  Result: all non-NaNs widened to the same f64 bits as Python; all NaNs re-encoded to `f97e00`.
- Ad hoc JS/Python f32 decode sweep over 20,011 single payloads.  
  Result: all non-NaNs widened to the same f64 bits as Python; all NaNs re-encoded to `f97e00`.
