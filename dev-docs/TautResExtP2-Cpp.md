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

**Extensions (implement).** Unlike the codec, `ext_*` is a **runtime** path (not constexpr): use
`parse()` to decode host bytes to a `Cbor` tree, surgery the `map` (`std::vector<std::pair<long long,
Cbor>>`) — drop existing `tag`, push the ext value — then `encode_value(Buf&, Cbor)` to re-emit (it
sorts). `ext_set(host, tag, Cbor value) -> bytes`, `ext_get(host, tag) -> optional<Cbor>`,
`ext_clear(host, tag) -> bytes`. Band-check `tag >= (1<<20)`. ⚠ The constexpr codec's `Buf` is a fixed
**512-byte** stack buffer — the **runtime ext path MUST output to a heap buffer** (`std::vector<unsigned
char>`); a host + extension can exceed 512, so do NOT re-emit through the fixed `Buf`. Also `Cbor` holds
text/bytes as `std::string_view` into the decoded source — whatever `ext_get` returns must outlive its
backing buffer (state that lifetime in the API).

**Verify:** clang++/g++ `-std=c++20` available — compile a harness over both corpora + a differential
fuzz. Stdlib-only includes; no third-party header.
