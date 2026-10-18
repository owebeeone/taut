# Taut ResExt Phase 2 C++ Plan/Prompt Review 55-3

## Findings

1. [P1] The heap-output fix is stated, but the concrete encoder instruction still points at the fixed `Buf` API.

   References: `dev-docs/TautResExtP2-Cpp.md:16`-`22` says to re-emit with `encode_value(Buf&, Cbor)`, then says the runtime ext path MUST output to `std::vector<unsigned char>` and must not re-emit through the fixed `Buf`; current C++ runtime only exposes `encode_value(Buf&, const Cbor&)` (`src/taut/gen/runtime/cbor.hpp:319`-`342`), and `Buf::push` still writes into a 512-byte array with no bounds check (`src/taut/gen/runtime/cbor.hpp:132`-`136`).

   Impact: the prior unsafe-output issue is only partially resolved. A careful implementer can infer that they should add a vector-backed sink or `encode_value` overload in owned C++ files, but the prompt as written gives two conflicting instructions: use the only existing fixed-buffer encoder, and do not use that fixed buffer. Tighten it to require a specific dynamic encoder shape, e.g. a shared sink abstraction or `encode_value(std::vector<unsigned char>&, const Cbor&)`, and require ext accessors to use only that runtime path.

2. [P1] The prompt still does not define how the generated C++ extension type becomes the `Cbor` value accepted by `ext_set`.

   References: the base now requires the harness to exercise the generated extension type's `to_cbor`/`from_cbor` path, not a hand-rolled Cbor map (`dev-docs/TautResExtP2-Base.md:74`-`83`); the C++ brief specifies a generic `ext_set(host, tag, Cbor value)` and `ext_get(host, tag) -> optional<Cbor>` surface (`dev-docs/TautResExtP2-Cpp.md:16`-`20`); generated C++ messages only expose `constexpr void to_cbor(Buf&) const` plus `from_cbor(const Cbor&)` (`src/taut/gen/cpp.py:137`-`160`, `src/taut/gen/cpp.py:115`-`134`), not a Cbor-tree builder or typed extension wrapper.

   Impact: an agent can pass bytes by manually constructing `Cbor::Map`, or by serializing `Decision` through `Buf` and parsing it back, while still missing the intent of the base contract or reintroducing the 512-byte limit. The C++ prompt should explicitly require one bridge: typed wrappers/templates in `ext.hpp`, a generated `to_cbor_value()` helper, or a dynamic encode-then-parse helper that avoids fixed `Buf` and is used by the checked harness.

3. [P1] The `parse()` instruction still does not require Python-oracle validation behavior.

   References: Python `cbor.loads()` rejects trailing bytes, unsupported additional-info values, unsupported simple values, and unsupported major types (`src/taut/wire/cbor.py:118`-`136`, `src/taut/wire/cbor.py:172`-`186`); Python `cbor.dumps()` also rejects non-integer or negative map keys (`src/taut/wire/cbor.py:103`-`111`). C++ `parse()` returns only the first decoded item (`src/taut/gen/runtime/cbor.hpp:314`), `read_arg` treats unsupported info values as the 64-bit case (`src/taut/gen/runtime/cbor.hpp:252`-`263`), major type 6 falls through to the simple/null handling (`src/taut/gen/runtime/cbor.hpp:288`-`310`), unsupported simple values become null (`src/taut/gen/runtime/cbor.hpp:310`), and map keys are accepted via `key.i` without checking key kind or non-negativity (`src/taut/gen/runtime/cbor.hpp:282`-`286`).

   Impact: the base now says to mirror `ext.py`, band-check first, and reject non-map hosts (`dev-docs/TautResExtP2-Base.md:52`-`70`), but the C++ brief still says only to use `parse()` on host bytes. A happy-path corpus implementation can therefore accept malformed/trailing host bytes or re-encode invalid map keys differently from the Python oracle. Require an ext-specific checked parse wrapper: full consumption, top-level map, supported major/additional-info/simple values only, and non-negative integer map keys.

4. [P2] The `ext_get` lifetime warning is present but worded backwards.

   References: `Cbor` stores text/bytes as `std::string_view` into the decoded input (`src/taut/gen/runtime/cbor.hpp:225`-`232`, `src/taut/gen/runtime/cbor.hpp:274`-`275`); the C++ prompt says whatever `ext_get` returns "must outlive its backing buffer" (`dev-docs/TautResExtP2-Cpp.md:22`-`24`).

   Impact: the backing buffer must outlive the returned `Cbor`, not the other way around. As written, the sentence describes the dangling-view bug it is trying to prevent. Change it to require either an explicit "host bytes must outlive returned Cbor" contract, an owning `Cbor` representation for `ext_get`, or typed decode before return.

5. [P3] The extension/forward-compat gate is still not asserted through the C++ target path.

   References: `scaffold.emit()` enforces the extension/forward-compat gate for every compiled target including C++ (`src/taut/gen/scaffold.py:580`-`586`), but the current named test still exercises only Rust for the extension gate (`src/tests/test_forward_compat.py:77`-`81`). The C++ test covers residual field emission, not extension-gated generation (`src/tests/test_forward_compat.py:84`-`88`).

   Impact: this is not an implementation blocker because the shared guard covers C++ today, but the Phase 2 C++ harness should add a C++-named assertion if it touches C++ tests. That keeps the D14 invariant visible in the target being ported.

## Proposed Resolutions

1. **Dynamic encoder API**
   - **Resolution:** Change the C++ Phase 2 prompt to require one concrete heap-backed encoder path, preferably `encode_value(std::vector<unsigned char>& out, const Cbor& value)` in the owned C++ runtime files. `ext_set` and `ext_clear` must use that path for host re-emission and must not route extension output through fixed `Buf`.
   - **Verification:** Add an extension vector/harness case that re-emits through `ext_set`/`ext_clear`, compare bytes against `corpus/ext_vectors.json`, and include at least one fuzz row large enough that a fixed 512-byte buffer would be the wrong abstraction even if it does not overflow in the committed corpus.

2. **Typed `Decision` to `Cbor` bridge**
   - **Resolution:** Pick one explicit bridge in the prompt before dispatch. The least invasive option is a dynamic encode-then-parse helper in the C++ harness/runtime: serialize the generated `Decision` with a heap-backed encoder, checked-parse that byte vector into a `Cbor`, pass that nested `Cbor` to `ext_set`, and decode `ext_get` output with `Decision::from_cbor`. Do not allow hand-built `Cbor::Map` values in the checked corpus path.
   - **Verification:** The C++ extension harness must call the generated `Decision` encode/decode path for every `value` and `get` row, not construct equivalent CBOR trees manually.

3. **Checked parse behavior**
   - **Resolution:** Add an ext-specific checked parse wrapper and require the extension helpers to use it. The wrapper should reject trailing bytes, unsupported additional-info values, unsupported simple values, tag major type 6, unsupported majors, non-map host roots, and map keys that are not non-negative integers.
   - **Verification:** Add negative C++ tests for below-band tag before host decode, scalar host bytes, trailing host bytes, and at least one invalid map-key shape. These are language-runtime tests, not corpus rows.

4. **`ext_get` lifetime contract**
   - **Resolution:** Fix the wording to say the backing host byte buffer must outlive any returned view-backed `Cbor`, or avoid the contract by returning an owning value / decoding to the generated typed value before exposing it. The current phrase "returned Cbor must outlive its backing buffer" should be removed.
   - **Verification:** The harness should either keep host bytes alive while inspecting `ext_get`, or test the chosen owning/typed return shape directly.

5. **C++ extension gate visibility**
   - **Resolution:** Add a C++-named assertion if Phase 2 touches forward-compat tests: extension-bearing generation fails without `--forward-compat` and succeeds for C++ with it.
   - **Verification:** Extend `src/tests/test_forward_compat.py` or the C++ test module with a target-specific assertion that names `cpp` in the test.

## Prior Issue Status

- Resolved: the Review55 P0 blocker about missing Phase 1 corpora and shared surface is resolved. `ir/resext.taut.py`, `corpus/residual_vectors.json`, `corpus/ext_vectors.json`, `src/taut/corpus/resext_build.py`, `run_tests.py` regen, and `src/tests/test_resext_vectors.py` are present; the plan now says per-language `kit.py` harness emission was deferred and agents hand-write harnesses (`dev-docs/TautResExtPlan.md:51`-`55`).
- Resolved: the Review55 P0 blocker about missing C++ `ext.hpp` runtime wiring is resolved. `_RUNTIMES` has `("taut/ext.hpp", "ext.hpp")`, and `emit()` vendors registered runtime files once they exist (`src/taut/gen/scaffold.py:32`-`39`, `src/taut/gen/scaffold.py:600`-`606`).
- Resolved: the Review55-2 issue that the C++ brief allowed accessors in `cbor.hpp` is resolved. The current C++ prompt explicitly requires `src/taut/gen/runtime/ext.hpp` and says not to put accessors in `cbor.hpp` (`dev-docs/TautResExtP2-Cpp.md:6`-`9`).
- Resolved: the residual sorted-order invariant is now documented in the base brief, including the fact that verification is wire decode -> re-encode and direct residual mutation must sort first (`dev-docs/TautResExtP2-Base.md:39`-`45`).
- Resolved: the fixed ResExt fixture/C++20 map concern no longer blocks corpus parity. The fixture is map-free (`ir/resext.taut.py:16`-`24`), and the existing C++ tests still document map constexpr limits as shape-only coverage (`src/tests/test_cpp.py:50`-`57`).
- Resolved: the differential fuzz instruction is now specific enough for Phase 2. The base makes corpus parity the hard gate, describes a deterministic stdlib fuzz loop, and says the pytest side owns corpus/fuzz I/O for compiled targets (`dev-docs/TautResExtP2-Base.md:100`-`113`).
- Partially resolved / still unresolved: the prior fixed-`Buf`, parse-validation, generic-vs-typed C++ extension bridge, `optional<Cbor>` lifetime, and C++ extension-gate-test concerns remain in the findings above.

## Verdict

The prior P0 prerequisites are gone, and the C++ residual half is implementable: the corpus and scaffold inputs exist, the prompt points at the right files, and a temporary C++20 residual harness over all four ResExt residual vectors compiled and passed. I would still not call the C++ Phase 2 prompt fully implementable as written for extensions. Before handing it to an implementation agent, clarify the dynamic encoder API, the typed `Decision` <-> `Cbor` bridge, checked parse behavior, and the `ext_get` lifetime wording.

## Verification Notes

- Inspected `dev-docs/TautResExtPlan.md`, `dev-docs/TautResExtP2-Base.md`, `dev-docs/TautResExtP2-Cpp.md`, both prior reviews, `ir/resext.taut.py`, the ResExt corpora/generator/tests, `src/taut/gen/scaffold.py`, `src/taut/gen/cpp.py`, `src/taut/gen/runtime/cbor.hpp`, `src/taut/ext.py`, `src/taut/wire/cbor.py`, and relevant C++/forward-compat tests.
- Ran `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m pytest -q -p no:cacheprovider src/tests/test_resext_vectors.py src/tests/test_forward_compat.py src/tests/test_cpp.py`: 21 passed.
- Ran a temporary C++20 residual probe generated from `ir/resext.taut.py` and `corpus/residual_vectors.json` with `/usr/bin/c++ -std=c++20`: all 4 residual vectors passed.
- `python3 -m pytest` could not run because that interpreter has no `pytest`; the default `python` interpreter was used successfully.
- No code implementation was attempted.
