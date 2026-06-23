# Taut Float — Phase 2: TypeScript  (special: interpreter + structural type)

Read [TautFloatP2-Base.md](TautFloatP2-Base.md) first.

**Files you own:** `trial/ts/src/cbor.ts` · `trial/ts/src/codec.ts` · the TS tests under
`trial/ts`. (Path is under the repo root's `trial/`, not `taut/`.)

**Two things make TS different from the compiled targets:**

1. **Interpreter-style, not codegen.** Like Python, TS is IR-driven: `cbor.ts` (substrate)
   + `codec.ts` (the `toWire`/`fromWire` mirror of `wire/codec.py`). There is **no
   `gen/ts.py` codec** to edit, and `scaffold.py`'s `_ts_ty` is already done.
2. **Structural `CborValue`** — a `number` already means an int, so a float cannot ride as a
   bare number (`1.0` would encode as an int `01`). Add a wrapper class.

**`cbor.ts`:**
- Add `export class CborFloat { constructor(readonly value: number) {} }` and include it in
  the `CborValue` union.
- `enc`: add `if (value instanceof CborFloat) { … shortest-form … }`. Keep the existing
  `Number.isInteger` guard for bare-number ints. Narrowing: hand-roll double→half RNE;
  single via `Math.fround`; bits via a `DataView`.
- `dec` major 7: add `info` 25/26/27 → `new CborFloat(widened)` (so decode→re-encode parity
  preserves float-ness).

**`codec.ts`:**
- `toWire` `case "scalar"`: when the scalar's kind is `float`, return
  `new CborFloat(Number(value))` (rule E). **Read `trial/ts/src/schema.ts`** to see how a
  scalar `TypeRef` carries its kind (the current `case "scalar": return value` doesn't
  inspect it).
- `fromWire` `case "scalar"`: unwrap — `if (cv instanceof CborFloat) return cv.value;`.

**Verify:** if Deno/Node is present, run the `trial/ts` tests + a parity harness over
`corpus/float_vectors.json`; else mirror `wire/cbor.py` + `wire/codec.py` exactly.
