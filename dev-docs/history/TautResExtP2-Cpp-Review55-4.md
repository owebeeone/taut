# Taut ResExt Phase 2 C++ Prompt Review 55-4

## Findings

No actionable prompt issues remain.

The designer-edited C++ Phase 2 prompt folds the Review55-3 proposed resolutions into the dispatch brief closely enough for implementation. The prompt now gives the C++ implementer explicit direction for the dynamic vector-backed encoder, checked extension parser, typed `Decision` <-> `Cbor` path, `ext_get` lifetime contract, and C++-named D14 gate.

Residual implementation risk remains, but it is now covered by the prompt's required tests/gates rather than by missing design text:

- The typed bridge is still the highest-risk implementation detail because the current generated C++ `to_cbor` surface is `Buf`-based today (`src/taut/gen/cpp.py:137`-`160`), while the prompt requires the checked ResExt harness to use a heap-backed typed encode path (`dev-docs/TautResExtP2-Cpp.md:36`-`40`). The prompt correctly allows `src/taut/gen/cpp.py` changes if a generated typed bridge is needed (`dev-docs/TautResExtP2-Cpp.md:6`-`10`).
- The checked parser is net-new runtime behavior. Current `parse()` still returns the first decoded item without full-consumption validation and accepts several unsupported shapes permissively (`src/taut/gen/runtime/cbor.hpp:252`-`314`), but the prompt now explicitly requires an ext-specific checked wrapper and negative tests (`dev-docs/TautResExtP2-Cpp.md:27`-`31`, `dev-docs/TautResExtP2-Cpp.md:42`-`47`).
- The C++-named D14 assertion is not in the current test suite yet; the existing target-specific extension gate test still names Rust (`src/tests/test_forward_compat.py:77`-`81`). This is not a prompt blocker because the C++ brief now explicitly requires the C++ assertion, and the shared scaffold guard already covers C++ (`src/taut/gen/scaffold.py:580`-`586`).

## Proposed Resolutions

None for the prompt/docs. Dispatch as written.

Implementation follow-through should make the required tests fail first where practical, especially for trailing bytes, non-map host roots, invalid map keys, below-band-before-decode behavior, the large dynamic-output row, and the C++-named D14 assertion.

## Prior Resolution Check

- Dynamic vector-backed encoder: resolved. The prompt now requires a heap-backed encoder, preferably `void encode_value(std::vector<unsigned char>& out, const Cbor& value)`, and requires `ext_set` / `ext_clear` to avoid the fixed 512-byte `Buf` path (`dev-docs/TautResExtP2-Cpp.md:22`-`26`). The current runtime still only has fixed `Buf` encoding (`src/taut/gen/runtime/cbor.hpp:132`-`199`, `src/taut/gen/runtime/cbor.hpp:319`-`342`), so the instruction is real implementation work, not stale documentation.
- Typed `Decision` <-> `Cbor` bridge: resolved. The base requires generated type `to_cbor`/`from_cbor` coverage and bans hand-built `Cbor` maps as the checked proof path (`dev-docs/TautResExtP2-Base.md:74`-`83`). The C++ prompt now tells the implementer to pick a typed bridge, names dynamic encode-then-checked-parse as the preferred bridge, and explicitly bans hand-built equivalent `Cbor::Map` values in the checked ResExt harness (`dev-docs/TautResExtP2-Cpp.md:36`-`40`).
- Checked parse wrapper: resolved. The prompt now requires full consumption, rejection of unsupported additional-info/simple values, major type 6, unsupported majors, non-map host roots, and non-non-negative-integer map keys, with band check before parsing and `std::invalid_argument` for misuse/parse-contract failures (`dev-docs/TautResExtP2-Cpp.md:27`-`31`). This matches the Python oracle behavior called out in `cbor.loads()` / `cbor.dumps()` (`src/taut/wire/cbor.py:103`-`121`, `src/taut/wire/cbor.py:125`-`186`) and `ext._check()` (`src/taut/ext.py:19`-`46`).
- `ext_get` lifetime wording: resolved. The prompt now says the host byte buffer passed by the caller must outlive any returned view-backed `Cbor`, and it forbids returning views into a local decoded buffer (`dev-docs/TautResExtP2-Cpp.md:32`-`35`). That is the correct direction for the current `Cbor` view model (`src/taut/gen/runtime/cbor.hpp:225`-`232`, `src/taut/gen/runtime/cbor.hpp:274`-`275`).
- C++-named D14 gate: resolved in prompt. The prompt now requires a C++-named assertion that extension-bearing C++ generation fails without `--forward-compat` and succeeds with it (`dev-docs/TautResExtP2-Cpp.md:42`-`47`). The shared scaffold guard already enforces the invariant for compiled targets including C++ (`src/taut/gen/scaffold.py:580`-`586`).

## Dispatch Verdict

Dispatch-ready.

The C++ prompt is now implementation-ready for ResExt Phase 2. It preserves the "verify residual first" shape, keeps the proven fixed-`Buf` FLOAT path intact, names only the C++-owned files, and gives enough concrete acceptance criteria for an implementation agent to produce the runtime, harness, negative cases, and C++ target gate without changing shared Phase 1 inputs.

## Verification Notes

- Read `dev-docs/TautResExtPlan.md`, `dev-docs/TautResExtP2-Base.md`, `dev-docs/TautResExtP2-Cpp.md`, and `dev-docs/TautResExtP2-Cpp-Review55-3.md`.
- Inspected relevant source/tests: `ir/resext.taut.py`, `corpus/residual_vectors.json`, `corpus/ext_vectors.json`, `src/taut/ext.py`, `src/taut/wire/cbor.py`, `src/taut/gen/scaffold.py`, `src/taut/gen/cpp.py`, `src/taut/gen/runtime/cbor.hpp`, `src/tests/test_forward_compat.py`, and `src/tests/test_cpp.py`.
- Ran `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m pytest -q -p no:cacheprovider src/tests/test_resext_vectors.py src/tests/test_forward_compat.py src/tests/test_cpp.py`: 21 passed.
- Did not implement runtime code, commit, push, or edit any file other than this review output.
