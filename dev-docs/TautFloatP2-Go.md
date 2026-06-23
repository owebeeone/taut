# Taut Float — Phase 2: Go

Read [TautFloatP2-Base.md](TautFloatP2-Base.md) first.

**Files you own:** `src/taut/gen/runtime/cbor.go` · `src/taut/gen/go.py` ·
`src/tests/test_go.py` (Python shape test) + a Go parity harness.

**Value model — struct (needs a NEW field).** `type Cbor struct { Kind; I int64; S; B;
Arr; Map }` stores bool in `I`. Add:
- a `F float64` field on the struct,
- a `KFloat` kind constant (extend the `iota` block — it becomes 7),
- `func CFloat(n float64) Cbor { return Cbor{Kind: KFloat, F: n} }`,
- `func (c Cbor) Float() float64 { return c.F }`.

**Runtime (`cbor.go`):** `enc` add `case KFloat:` shortest-form (`math.Float64bits`,
`math.Float32bits`); `dec` major 7 add 25/26/27 (`math.Float64frombits`, `math.Float32frombits`).
**Narrowing:** no native f16 — hand-roll double→half RNE. Single: `f := float32(v); if
float64(f) == v { … }`.

**Codegen (`go.py`):** `_go_ty` (→ `"float64"`), `_enc` (→ `CFloat({expr})`),
`_dec` (→ `{expr}.Float()`).

**Verify:** if `go` is present, run a parity harness over the corpus; extend `test_go.py`
to assert the emitted float type + `CFloat`/`.Float()` calls.
