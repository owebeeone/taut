# Taut Float — Phase 2: Swift  (easiest narrowing — native Float16)

Read [TautFloatP2-Base.md](TautFloatP2-Base.md) first.

**Files you own:** `src/taut/gen/runtime/cbor.swift` · `src/taut/gen/swift.py` · the Swift test.

**Value model — enum.** `enum Cbor { case int(Int64) … }` → add `case float(Double)`, plus
`var floatVal: Double { if case let .float(x) = self { return x }; fatalError("not a float") }`.

**Runtime (`cbor.swift`):**
- `enc`: add `case let .float(x):` shortest-form.
- `dec` major 7: add `25` / `26` / `27`, reading raw payload bytes.
- **Narrowing is native** — Swift has `Float16` and `Float`. Half: `let h = Float16(v); if
  Double(h) == v { … h.bitPattern … }` (NaN handled first, so `==` is safe). Single:
  `let f = Float(v); if Double(f) == v { … f.bitPattern … }`. Double: `v.bitPattern`.
  (Confirm `Float16` is available on the build platform; it is on Apple platforms and recent
  Swift on Linux.)

**Codegen (`swift.py`):** `_swift_ty` (→ `"Double"`), `_default` (→ `"0.0"`), `_encode`
(→ `Cbor.float({expr})`), `_decode` (→ `{expr}.floatVal`).

**Verify:** if the Swift toolchain is present, run a parity harness over
`corpus/float_vectors.json`; else mirror `wire/cbor.py`.
