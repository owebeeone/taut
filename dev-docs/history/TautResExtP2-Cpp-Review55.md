# Taut ResExt Phase 2 C++ Plan/Prompt Review 55

## Findings

1. [P0] Phase 2 C++ is not implementable in this checkout because the Phase 1 corpora and shared harness/runtime wiring it depends on are absent.

   References: `dev-docs/TautResExtPlan.md:55`-`61` makes `corpus/residual_vectors.json`, `corpus/ext_vectors.json`, per-language harnesses, and the vendored `ext.<lang>` runtime slot Phase 1 deliverables; `dev-docs/TautResExtP2-Base.md:19`-`20` and `dev-docs/TautResExtP2-Cpp.md:12`-`24` require those corpora for the C++ work; current `corpus/` contains only `float_vectors.json`, `glade.*`, and `griplab.*`; `src/taut/corpus/kit.py:89`-`92` still exposes only the Rust harness; `run_tests.py:17`-`23` has no residual/ext corpus generation gate.

   Impact: a C++ agent cannot run the required residual byte-diff, extension vector parity, or cross-language verification as written. The prompt should either be explicitly blocked on Phase 1 landing first, or it must expand the C++ task to own the missing fixture schema, corpora, harness generation, and shared runtime wiring.

2. [P0] The prompt asks C++ to add an `ext` runtime header, but the scoped file ownership forbids the current repo changes needed to ship it.

   References: `dev-docs/TautResExtP2-Cpp.md:6`-`9` allows a new `taut/ext.hpp` and says to match `_RUNTIMES` wiring from Phase 1; `dev-docs/TautResExtP2-Base.md:63`-`68` says not to edit `src/taut/gen/scaffold.py`; current `_RUNTIMES` has only one C++ runtime entry, `taut/cbor.hpp` (`src/taut/gen/scaffold.py:30`-`38`), and `emit()` vendors only that single resource (`src/taut/gen/scaffold.py:594`-`599`).

   Impact: if Phase 1 has not already changed scaffold wiring, a new `src/taut/gen/runtime/ext.hpp` would not be emitted by `tautc gen --with-runtime`. The prompt should either require Phase 1 as a prerequisite or explicitly grant ownership of the scaffold/runtime packaging changes.

3. [P1] The C++ accessor surface conflicts with the base/Python typed extension contract.

   References: the base says `ext_set` encodes the generated extension type and `ext_get` returns `ExtMsg | null` (`dev-docs/TautResExtP2-Base.md:45`-`51`); Python takes `schema`, `ext_message`, and a native value, then decodes back to a native dict (`src/taut/ext.py:24`-`38`); the C++ brief instead specifies `ext_set(host, tag, Cbor value)` and `ext_get(host, tag) -> optional<Cbor>` (`dev-docs/TautResExtP2-Cpp.md:16`-`20`).

   Impact: an implementation can satisfy generic CBOR byte surgery while still missing the cross-language API parity promised by the plan. The C++ prompt should choose and name the contract: either a generic low-level helper plus typed wrappers, or an explicitly generic C++ exception to the `ext.py` mirror.

4. [P1] The 512-byte `Buf` caveat is not strong enough for runtime extension accessors.

   References: `Buf` is fixed at 512 bytes and `push()` has no bounds check (`src/taut/gen/runtime/cbor.hpp:132`-`136`); generic re-emission only writes to `Buf` (`src/taut/gen/runtime/cbor.hpp:319`); the C++ prompt tells the agent to use `encode_value(Buf&, Cbor)` and merely "note it" if the cap is hit (`dev-docs/TautResExtP2-Cpp.md:16`-`21`).

   Impact: `ext_set` and `ext_clear` operate on arbitrary runtime host bytes, so valid messages can exceed 512 bytes. A direct `Buf` implementation can silently overflow rather than fail or grow. The prompt should require a dynamic output sink or a checked vector-backed encoder for the extension path, not leave heap output as optional.

5. [P1] The C++ `parse()` path is not equivalent to the Python oracle for extension accessors.

   References: Python `cbor.loads()` rejects trailing bytes (`src/taut/wire/cbor.py:118`-`122`) and unsupported encodings (`src/taut/wire/cbor.py:136`, `src/taut/wire/cbor.py:185`-`186`); C++ `parse()` returns only the first decoded item (`src/taut/gen/runtime/cbor.hpp:314`), treats unsupported simple values as null (`src/taut/gen/runtime/cbor.hpp:310`), and assumes map keys decoded as ints (`src/taut/gen/runtime/cbor.hpp:282`-`286`). The C++ prompt only says to use `parse()` on host bytes (`dev-docs/TautResExtP2-Cpp.md:16`-`18`).

   Impact: C++ `ext_set/get/clear` could accept or transform malformed/trailing host bytes differently from `src/taut/ext.py`, creating cross-language parity holes outside the happy-path corpus. The prompt should require an ext-specific runtime validation wrapper: consume the full input, require a top-level map, reject unsupported major/additional-info cases, and reject non-integer map keys.

6. [P1] The residual merge claim hides an invariant: current C++ generated code assumes `wire_residual` is already sorted.

   References: the C++ brief says `cpp.py` "already merge-emits residual interleaved with known fields in ascending order" (`dev-docs/TautResExtP2-Cpp.md:11`-`12`); the generated loop only advances through `wire_residual` in existing vector order (`src/taut/gen/cpp.py:140`-`153`); `from_cbor` captures unknowns in parsed map order (`src/taut/gen/cpp.py:129`-`132`); `encode_value` sorts nested `Cbor::Map` entries but does not sort a message's `wire_residual` vector (`src/taut/gen/runtime/cbor.hpp:331`-`339`).

   Impact: decode-to-reencode of canonical corpus bytes should pass because CBOR maps are already sorted, but direct residual mutation or a harness that constructs `wire_residual` unsorted will emit non-canonical bytes. The prompt should state that residual verification must decode from wire bytes, or require sorting/deduplication before the generated merge.

7. [P2] The `-std=c++20` instruction can fail for reasonable fixture schemas that include map fields.

   References: the existing C++ test suite documents that generated `std::map` iteration is not portable in C++20 constexpr code (`src/tests/test_cpp.py:50`-`52`); `cpp.py` emits `std::map` for IR maps (`src/taut/gen/cpp.py:63`-`65`) and a `constexpr` `to_cbor` (`src/taut/gen/cpp.py:137`-`139`); the C++ prompt requires `clang++/g++ -std=c++20` (`dev-docs/TautResExtP2-Cpp.md:23`-`24`) but does not constrain the residual/ext fixture schema.

   Impact: an extension fixture containing a map field can fail compilation because of the existing C++20 constexpr map limitation, not because ResExt is wrong. The prompt should either keep the C++ Phase 2 fixture schema map-free, compile map-bearing generated types under a standard/toolchain that supports the path, or make extension verification exercise the runtime CBOR helper without constexpr map field emission.

8. [P2] Returning `optional<Cbor>` from `ext_get` has an unmentioned lifetime hazard.

   References: `Cbor` stores bytes/text as `std::string_view` into the decoded source (`src/taut/gen/runtime/cbor.hpp:225`-`233`), and decode populates those views with `substr()` from the input (`src/taut/gen/runtime/cbor.hpp:274`-`275`); the C++ prompt returns `optional<Cbor>` (`dev-docs/TautResExtP2-Cpp.md:19`).

   Impact: `ext_get(std::string_view(host_temp), tag)` can return a tree containing views into a destroyed buffer. The prompt should either document the host-buffer lifetime contract, return a typed/deep-owned value, or introduce an owning runtime representation for extension reads.

9. [P2] The differential fuzz requirement is underspecified relative to the allowed scope.

   References: the base requires differential fuzz against the Python oracle (`dev-docs/TautResExtP2-Base.md:76`-`78`), while also forbidding edits to corpus generators and shared infrastructure (`dev-docs/TautResExtP2-Base.md:63`-`68`); the C++ prompt says "compile a harness over both corpora + a differential fuzz" (`dev-docs/TautResExtP2-Cpp.md:23`-`24`), but this repo has no C++ residual/ext harness generator (`src/taut/corpus/kit.py:89`-`92`).

   Impact: implementers may either skip fuzz, write one-off tests outside the repo, or edit shared files despite the prompt. The C++ prompt should define the expected in-repo test location, data flow to the Python oracle, and whether one-off C++/Python harness code is in scope.

10. [P3] The extension-without-forward-compat gate is implemented broadly but is not explicitly tested for C++.

    References: `scaffold.emit()` rejects any generated target with extensions unless `forward_compat=True` (`src/taut/gen/scaffold.py:574`-`580`), but the current test only names and exercises Rust (`src/tests/test_forward_compat.py:77`-`81`). The base definition of done requires the flag/gate invariant to stay intact (`dev-docs/TautResExtP2-Base.md:81`-`84`; `dev-docs/TautResExtPlan.md:88`-`91`).

    Impact: this is not a current implementation blocker, but a C++ Phase 2 test could regress the invariant without a C++-named assertion. Add a small C++-target gate test if C++ tests are touched.

## Summary

The C++ prompt should not be handed to an implementation agent as-is against this repository. Its central verification inputs and runtime wiring are Phase 1 prerequisites, but they are not present here. After Phase 1 lands, the most important C++-specific prompt fixes are to settle the typed-vs-generic extension API, require a heap or bounds-checked encoder for runtime extension output, and specify parse/validation behavior so C++ matches the Python oracle.

## Verification Notes

- Inspected `dev-docs/TautResExtPlan.md`, `dev-docs/TautResExtP2-Base.md`, `dev-docs/TautResExtP2-Cpp.md`, `src/taut/gen/runtime/cbor.hpp`, `src/taut/gen/cpp.py`, `src/taut/gen/scaffold.py`, `src/taut/ext.py`, `src/taut/wire/cbor.py`, `src/taut/corpus/kit.py`, and relevant tests.
- `PYTHONPATH=src python3 -m pytest src/tests/test_cpp.py src/tests/test_forward_compat.py -q` could not run because this Python environment has no `pytest` module installed.
- No code implementation was attempted.
