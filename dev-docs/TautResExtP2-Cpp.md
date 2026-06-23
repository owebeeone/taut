# Taut Res+Ext Parity — Phase 2: C++

Read [TautResExtP2-Base.md](TautResExtP2-Base.md) first; reuse
[history/TautFloatP2-Cpp.md](history/TautFloatP2-Cpp.md) for the `Buf` + `Cbor`-tree idiom.

**Files you own:** `src/taut/gen/runtime/cbor.hpp` only for the runtime support needed by ResExt
(`std::vector<unsigned char>` encoding and checked parse support; keep the existing fixed `Buf`
path intact) · `src/taut/gen/cpp.py` only if a generated typed bridge is needed · **NEW**
`src/taut/gen/runtime/ext.hpp` (Phase 1 wired the `("taut/ext.hpp","ext.hpp")` slot — put the
accessors HERE, **not** in `cbor.hpp`) · `src/tests/test_cpp.py` · `src/tests/test_forward_compat.py`
only for the C++-named D14 assertion.

**Do not change:** `ir/*`, the corpora/generators, `src/taut/ext.py`, `gen/scaffold.py`, another
language, or the proven FLOAT/fixed-`Buf` byte-exact encode path. Residual runtime/generator edits
are verify-first only: no churn unless a residual vector fails.

**Residual (verify+fix).** `cpp.py` already merge-emits residual interleaved with known fields in
ascending order (the `to_cbor` `__ri` while-loop). Generate the fixture `--forward-compat`, compile,
and run `residual_vectors.json` decode→re-encode; byte-diff. Confirm the interleave handles an
unknown tag *between* known tags and a band-tag unknown.

**Extensions (implement) — `ext.hpp`.** Unlike the codec, `ext_*` is a **runtime** path (not
constexpr). `cbor.hpp` gives you none of the pieces below — add them in your owned `ext.hpp`:
1. **A heap-output encoder** `void encode_value(std::vector<unsigned char>& out, const Cbor& value)`.
   `cbor.hpp` only has the fixed-512-byte `Buf` overload — the WRONG abstraction here (a host +
   extension can exceed 512). Make `ext_set` / `ext_clear` use only this path for host re-emission;
   never the fixed `Buf`.
2. **A checked parse** wrapper over `parse()` mirroring `cbor.loads`: consume the ENTIRE input (error
   on trailing bytes), require a **top-level map**, reject unsupported additional-info / simple /
   major types (incl. major 6) and non-negative-integer map keys. `ext_*` decode host bytes with
   THIS — raw `parse()` returns only the first item, coerces unknown simples to null, and skips key
   checks. Band-check `tag >= (1LL << 20)` before calling this parser; use `std::invalid_argument`
   for ext misuse / parse-contract failures.
3. **The raw runtime surface.** `ext_set(host, tag, const Cbor& value) -> std::vector<unsigned char>`,
   `ext_get(host, tag) -> std::optional<Cbor>`, `ext_clear(host, tag) -> std::vector<unsigned char>`.
   ⚠ **Lifetime:** a decoded `Cbor` holds text/bytes as `std::string_view` into the source buffer, so
   **the host byte buffer must outlive any `Cbor` returned by `ext_get`** (or decode to `Decision`
   before returning). State that in the API and in the harness; do not return views into a local
   decoded buffer.
4. **The typed `Decision` ↔ `Cbor` bridge.** Generated C++ messages expose only `constexpr void
   to_cbor(Buf&)` (emits BYTES) + `from_cbor(const Cbor&)` — there is no `Cbor`-tree builder. Use
   dynamic encode-then-checked-parse: serialize generated `Decision` through the heap-backed encoder
   path, **checked-parse** those bytes into a nested `Cbor`, pass that to `ext_set`; on `ext_get`, hand
   the nested `Cbor` to `Decision::from_cbor` (encode→parse — never hand-build a `Cbor::Map`, never
   store pre-serialized bytes at the tag).

**Tests/gates to add:** residual byte parity for all four `residual_vectors.json` rows; extension
byte parity for all five `ext_vectors.json` rows through `ext_set`/`ext_get`/`ext_clear`; negative
C++ tests for below-band tag before host decode, scalar/non-map host bytes, trailing host bytes, and
one invalid map-key shape; a fuzz row large enough that a fixed 512-byte output buffer would be the
wrong abstraction; and a C++-named D14 assertion that extension-bearing C++ generation fails without
`--forward-compat` and succeeds with it.

**Required evidence:** run
`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m pytest -q -p no:cacheprovider src/tests/test_resext_vectors.py src/tests/test_forward_compat.py src/tests/test_cpp.py`.
Report the compiler used (`clang++`/`g++`, `-std=c++20`), corpus parity result, invalid-case result,
fuzz seed, and mismatch count. Stdlib-only includes; no third-party header.
