# Taut ResExt Phase 2 C++ Plan/Prompt Review 55-2

## Findings

1. [P1] The C++ brief still permits the extension accessors to be implemented in `cbor.hpp`, but Phase 1 wired a concrete `ext.hpp` runtime slot.

   References: `dev-docs/TautResExtP2-Cpp.md:6`-`9` allows "a small `taut/ext.hpp`, or a section of `cbor.hpp`"; `dev-docs/TautResExtP2-Base.md:24`-`25` says `ext.<lang>` is already wired and agents should drop the file into `gen/runtime/`; `src/taut/gen/scaffold.py:32`-`35` maps C++ specifically to `taut/ext.hpp` backed by `ext.hpp`; `src/taut/gen/scaffold.py:600`-`606` vendors resources only when the named runtime file exists.

   Impact: an agent can follow the C++ prompt, put the API only in `cbor.hpp`, and leave the Phase 1 `ext.hpp` slot empty. That would compile local tests that include `cbor.hpp` directly, but it would not deliver the promised extension runtime module through `tautc gen --with-runtime`. Tighten the prompt to require `src/taut/gen/runtime/ext.hpp` for the public accessors, with `cbor.hpp` edits only for narrowly required shared primitives such as a checked/dynamic encoder sink.

2. [P1] The extension output path is still unsafe as written because the prompt points at fixed `Buf`.

   References: `dev-docs/TautResExtP2-Cpp.md:16`-`21` tells the agent to re-emit via `encode_value(Buf&, Cbor)` and only "note it" if the 512-byte cap is hit; `src/taut/gen/runtime/cbor.hpp:132`-`136` defines `Buf` as a 512-byte array with unchecked `push`; `src/taut/gen/runtime/cbor.hpp:319`-`338` only exposes `encode_value` for `Buf`.

   Impact: `ext_set` and `ext_clear` operate on runtime host bytes, not compile-time corpus values. Valid host messages can exceed 512 bytes, and the current instruction can silently overflow instead of returning correct bytes or a controlled error. The C++ prompt should require either a vector-backed runtime encoder or a bounds-checked sink abstraction reused by `encode_value`; treating heap output as optional is not sufficient.

3. [P1] The `parse()` instruction still does not match the Python oracle's validation behavior.

   References: Python `cbor.loads()` rejects trailing bytes and unsupported encodings (`src/taut/wire/cbor.py:118`-`136`, `src/taut/wire/cbor.py:172`-`186`); C++ `parse()` returns only the first item (`src/taut/gen/runtime/cbor.hpp:314`), treats unsupported simple values as null (`src/taut/gen/runtime/cbor.hpp:288`-`310`), and accepts map keys by reading `key.i` without checking that the key is an integer (`src/taut/gen/runtime/cbor.hpp:282`-`286`); the C++ prompt says only to use `parse()` on host bytes (`dev-docs/TautResExtP2-Cpp.md:16`-`18`).

   Impact: a C++ implementation can pass the happy-path corpus while accepting or transforming malformed host bytes differently from `src/taut/ext.py`. The prompt should require an ext-specific validation wrapper: consume the full input, require a top-level map, reject unsupported additional-info/simple/major cases, and reject non-integer map keys.

4. [P1] The public accessor contract remains ambiguous between generic CBOR helpers and typed extension parity.

   References: the base says extension accessors mirror `ext.py`, with `ext_set` encoding the generated extension message and `ext_get` returning the generated extension type (`dev-docs/TautResExtP2-Base.md:47`-`57`), while also allowing an idiomatic per-language surface (`dev-docs/TautResExtP2-Base.md:61`-`64`); the C++ prompt specifies only `ext_set(host, tag, Cbor value)`, `ext_get(host, tag) -> optional<Cbor>`, and `ext_clear(host, tag)` (`dev-docs/TautResExtP2-Cpp.md:16`-`20`).

   Impact: byte tests can pass with a low-level CBOR surgery API that never proves the generated `Decision::to_cbor` / `Decision::from_cbor` path promised by the plan. The prompt should explicitly choose one contract: either generic `Cbor` helpers plus typed wrappers used by the harness, or an explicitly generic C++ exception with tests that still exercise the generated extension type before/after the helper.

5. [P2] Differential fuzz remains underspecified relative to C++'s constexpr and schema limitations.

   References: the base asks for differential fuzz over random schemas/values and random extension messages (`dev-docs/TautResExtP2-Base.md:81`-`83`); the C++ prompt only says "compile a harness over both corpora + a differential fuzz" (`dev-docs/TautResExtP2-Cpp.md:23`-`24`); the existing C++ tests document that generated `std::map` iteration is not portable under C++20 constexpr code (`src/tests/test_cpp.py:50`-`52`), and `_render()` still has no `MapOf` branch for generated compile-time corpus values (`src/taut/gen/cpp.py:200`-`218`).

   Impact: the fixed ResExt fixture is map-free and a temporary `-std=c++20` residual harness compiled successfully, so this is no longer a fixture blocker. But a literal "random schemas" fuzz can fail for C++ generator/toolchain reasons unrelated to ResExt. The prompt should constrain C++ fuzz schemas to the currently supported compile path or define the fuzz as runtime-CBOR-only when map-bearing schemas are included.

6. [P2] The residual section still overstates the merge guarantee by omitting the sorted-residual invariant.

   References: the C++ prompt says `cpp.py` already merge-emits residuals in ascending order (`dev-docs/TautResExtP2-Cpp.md:11`-`14`); the generated merge loop only walks `wire_residual` in its existing vector order (`src/taut/gen/cpp.py:140`-`153`); `from_cbor` captures unknowns in parsed map order (`src/taut/gen/cpp.py:129`-`132`); `encode_value` sorts nested `Cbor::Map` entries but does not sort a message's `wire_residual` vector (`src/taut/gen/runtime/cbor.hpp:331`-`338`).

   Impact: decode-to-reencode of canonical corpus bytes is fine, but direct residual mutation or an unsorted test fixture can emit non-canonical bytes. The prompt should say residual verification is specifically wire decode -> re-encode, or require sorting/deduplication of `wire_residual` before message emission.

7. [P2] `optional<Cbor>` from `ext_get` has an unmentioned lifetime contract.

   References: `Cbor` stores bytes/text as `std::string_view` into the decoded source (`src/taut/gen/runtime/cbor.hpp:225`-`232`), and decoding fills those views from the input buffer (`src/taut/gen/runtime/cbor.hpp:274`-`275`); the C++ prompt returns `optional<Cbor>` from `ext_get` (`dev-docs/TautResExtP2-Cpp.md:19`).

   Impact: `ext_get(std::string_view(temp), tag)` can return a tree containing views into a destroyed buffer. The prompt should require either an explicit host-buffer lifetime contract, a deep-owned return type for extension reads, or typed decode before returning.

8. [P3] The extension/forward-compat gate is globally implemented, but still lacks a C++-named assertion.

   References: `scaffold.emit()` rejects extension schemas for all compiled targets without `forward_compat` (`src/taut/gen/scaffold.py:580`-`586`), but the current gate test only exercises `langs=["rust"]` (`src/tests/test_forward_compat.py:77`-`81`). The base definition of done requires the flag/gate invariant to remain intact (`dev-docs/TautResExtP2-Base.md:42`-`45`, `dev-docs/TautResExtP2-Base.md:86`-`89`).

   Impact: this is not an implementation blocker because the shared guard covers C++ today, but a C++ Phase 2 test should assert the C++ target path explicitly if the C++ tests are being touched.

## Prior Blocker Status

- Resolved: the prior P0 "Phase 1 corpora and shared runtime wiring are absent" blocker is resolved for implementability. `ir/resext.taut.py`, `corpus/residual_vectors.json`, `corpus/ext_vectors.json`, `src/taut/corpus/resext_build.py`, `run_tests.py` regen, and `src/tests/test_resext_vectors.py` are present. `src/taut/corpus/kit.py` still only has Rust harness emission, but `dev-docs/TautResExtPlan.md:52`-`55` now explicitly says per-language harness emission was deferred and agents hand-write harnesses.
- Resolved: the prior P0 "new `ext.hpp` cannot be vendored without scaffold ownership" blocker is resolved. `_RUNTIMES` now has the C++ `("taut/ext.hpp", "ext.hpp")` slot and `emit()` will vendor it once the Phase 2 file exists, without editing `scaffold.py`.
- Unresolved: the prior Buf, parse-validation, typed-vs-generic API, residual sorted-invariant, `optional<Cbor>` lifetime, differential fuzz, and C++ gate-test concerns remain as prompt/testability risks.
- Resolved for the fixed fixture, still a fuzz caveat: the prior C++20/map concern no longer blocks the shared ResExt fixture because `Host` and `Decision` are map-free and a temporary C++20 residual harness compiled. It still matters if "random schemas" fuzz includes map-bearing generated types.

## Verdict

Phase 1 has resolved the previous P0 prerequisites, so C++ Phase 2 is no longer blocked by missing corpora or scaffold runtime slots. The prompt is close to implementable, but not quite safe as written: require `ext.hpp`, require a checked/dynamic runtime encoder, define parse validation, and settle the generic-vs-typed C++ accessor surface before handing it to an implementation agent.

## Verification Notes

- Inspected `dev-docs/TautResExtPlan.md`, `dev-docs/TautResExtP2-Base.md`, `dev-docs/TautResExtP2-Cpp.md`, `dev-docs/TautResExtP2-Cpp-Review55.md`, `ir/resext.taut.py`, the committed ResExt corpora, `src/taut/corpus/resext_build.py`, `src/tests/test_resext_vectors.py`, `src/taut/gen/scaffold.py`, `src/taut/gen/cpp.py`, `src/taut/gen/runtime/cbor.hpp`, `src/taut/ext.py`, `src/taut/wire/cbor.py`, and relevant C++/forward-compat tests.
- Compiled a temporary C++20 residual harness generated from `ir/resext.taut.py` and `corpus/residual_vectors.json` with `/usr/bin/c++ -std=c++20`; it succeeded.
- `PYTHONPATH=src python3 -m pytest src/tests/test_resext_vectors.py src/tests/test_cpp.py src/tests/test_forward_compat.py -q` could not run because this Python environment has no `pytest` module installed.
- No code implementation was attempted.
