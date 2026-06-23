# Taut Res+Ext Parity — Phase 2: C++

Read [TautResExtP2-Base.md](TautResExtP2-Base.md) first; reuse
[history/TautFloatP2-Cpp.md](history/TautFloatP2-Cpp.md) for the `Buf` + `Cbor`-tree idiom.

**Files you own:** `src/taut/gen/runtime/cbor.hpp` (residual `encode_value` merge already there) ·
`src/taut/gen/cpp.py` (emits `std::vector<std::pair<long long, Cbor>> wire_residual`) · **NEW**
`src/taut/gen/runtime/ext.hpp` (Phase 1 wired the `("taut/ext.hpp","ext.hpp")` slot — put the
accessors HERE, **not** in `cbor.hpp`) · the C++ harness/tests.

**Residual (verify+fix).** `cpp.py` already merge-emits residual interleaved with known fields in
ascending order (the `to_cbor` `__ri` while-loop). Generate the fixture `--forward-compat`, compile,
and run `residual_vectors.json` decode→re-encode; byte-diff. Confirm the interleave handles an
unknown tag *between* known tags and a band-tag unknown.

**Extensions (implement) — `ext.hpp`.** `ext_*` is a **runtime** (non-constexpr) path. `cbor.hpp` gives
you none of the three pieces below — add them in your owned `ext.hpp`:
1. **A heap-output encoder** `void encode_value(std::vector<unsigned char>& out, const Cbor&)`. `cbor.hpp`
   only has the fixed-512-byte `Buf` overload — the WRONG abstraction here (a host + extension can exceed
   512). `ext_set`/`ext_clear` re-emit through THIS heap encoder, never the fixed `Buf`.
2. **A checked parse** wrapper over `parse()` mirroring `cbor.loads`: consume the ENTIRE input (error on
   trailing bytes), require a **top-level map**, reject unsupported additional-info / simple / major types
   (incl. major 6) and non-negative-integer map keys. `ext_*` decode host bytes with THIS — raw `parse()`
   returns only the first item, coerces unknown simples to null, and skips key checks.
3. **The typed `Decision` ↔ `Cbor` bridge.** Generated C++ messages expose only `constexpr void
   to_cbor(Buf&)` (emits BYTES) + `from_cbor(const Cbor&)` — there is no `Cbor`-tree builder. So
   encode the `Decision` with your heap encoder, **checked-parse** those bytes into a `Cbor`, and pass
   THAT nested `Cbor` to `ext_set`; on `ext_get`, hand the nested `Cbor` to `Decision::from_cbor`
   (encode→parse — never hand-build a `Cbor::Map`, never store pre-serialized bytes at the tag).

Surface: `ext_set(host, tag, const Cbor& value) -> std::vector<unsigned char>`, `ext_get(host, tag) ->
std::optional<Cbor>`, `ext_clear(host, tag) -> std::vector<unsigned char>`. **Band-check FIRST**: `tag >=
(1<<20)`, else throw (a negative test, no corpus row). ⚠ **Lifetime:** a decoded `Cbor` holds text/bytes
as `std::string_view` into the source buffer, so **the host byte buffer must outlive any `Cbor` returned
by `ext_get`** (or decode to `Decision` before returning). If you touch the forward-compat gate test, add
a `cpp`-named assertion (extension-bearing generation fails without `--forward-compat`, succeeds with it).

**Verify:** clang++/g++ `-std=c++20` available — compile a harness over both corpora + a differential
fuzz. Stdlib-only includes; no third-party header.
