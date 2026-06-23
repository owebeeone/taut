# Taut Float — Phase 2: C++  (highest complexity — constexpr)

Read [TautFloatP2-Base.md](TautFloatP2-Base.md) first.

**Files you own:** `src/taut/gen/runtime/cbor.hpp` · `src/taut/gen/cpp.py` · the C++
corpus / `static_assert` test.

**⚠ Everything is `constexpr`.** The encoder runs at compile time and the corpus
`static_assert`s the bytes, so your float narrowing must be **constexpr** too. Use C++20
`std::bit_cast<unsigned long long>(double)` (constexpr) for the bits and hand-roll a
constexpr `narrow16` + round-trip. This is the hardest port — budget for it.

**Two sites in `cbor.hpp`:**
- `struct Buf` (the encoder): add `constexpr void float_(double v)` emitting shortest-form
  (`F9`/`FA`/`FB` + BE payload). Generated `to_cbor` calls this.
- `struct Cbor` (the decode tree): add `K::Float`, a `double f` field, `constexpr double
  as_float() const`, decode arms for major-7 `info` 25/26/27, and an `encode_value`
  `K::Float` case (for forward-compat residual re-emit).

**Codegen (`cpp.py`):** `_base_type` (→ `"double"`), `_encode_scalar` (→ `b.float_({expr});`),
`_decode_expr` (→ `{acc}.as_float()`).

**Narrowing:** no portable native half — hand-roll constexpr double→half RNE (avoid
double-rounding; see base). Single via a bit round-trip of `static_cast<float>(v)`.

**Verify:** if a C++20 compiler is present, compile a float `static_assert` harness against
the corpus hex; else mirror `wire/cbor.py` and hand-check rows.
