# Taut Float — Phase 2: TypeScript  (SEPARATE REPO — not a taut worktree)

> **⚠ This task runs in the `trial` repo, NOT in `taut`.** The TS CBOR codec's source of
> truth is `trial/ts/src/cbor.ts` + `codec.ts` — a standalone TS package in its **own git
> repo**, sibling to `taut`. A `taut` worktree does **not** contain it. (The
> `taut/docs/examples/.../typescript/*.ts` files are *generated* copies under `generated/` —
> do **not** edit them; they get regenerated.) Run this agent against a worktree of
> **`trial`**, not taut.

The shared wire profile, encode algorithm, and corpus contract in **TautFloatP2-Base.md**
(in the taut repo) still govern — read it for the full spec. Only the **file scope** and the
**cross-repo oracle** below differ. Recap of the locked rules:

- Shortest-form: the smallest of half `F9` (2B) / single `FA` (4B) / double `FB` (8B) that
  round-trips the value exactly; payload big-endian IEEE-754.
- **NaN → canonical `F9 7E00`** (checked first). **−0.0 preserved** (`F9 8000`).
- Decode accepts `info` 25/26/27, widening to double.
- Narrow double→half **directly** (round-to-nearest-even) — never double→float→half.

## The oracle (cross-repo)
The contract is taut's **`corpus/float_vectors.json`** (22 rows of `{note, f64, cbor}`).
Because it lives in a different repo, **copy it into the `trial` repo** as your test fixture
(e.g. `trial/ts/test/float_vectors.json`) so the port verifies self-contained. For each row:
- `encode(double_from_bits(f64)) === cbor`
- `encode(decode(unhex(cbor))) === cbor`  (re-encode parity; covers NaN)
- for non-`nan*` rows: `f64_bits(decode(unhex(cbor))) === f64`

## Files you own (in the `trial` repo)
`trial/ts/src/cbor.ts` · `trial/ts/src/codec.ts` · a test under `trial/ts/test`.

## Why TS is different from the 7 compiled targets
1. **Interpreter-style, not codegen** — like Python: `cbor.ts` (substrate) + `codec.ts`
   (the `toWire`/`fromWire` mirror of `wire/codec.py`). There is **no `gen/ts.py`**.
2. **Structural `CborValue`** — a `number` already means an int, so a float cannot ride as a
   bare number (`1.0` would encode as int `01`). Add a wrapper class.

## `cbor.ts`
- Add `export class CborFloat { constructor(readonly value: number) {} }` and include it in
  the `CborValue` union.
- `enc`: add `if (value instanceof CborFloat) { … shortest-form … }`. Keep the existing
  `Number.isInteger` guard for bare-number ints. Narrowing: hand-roll double→half RNE;
  single via `Math.fround`; bits via a `DataView` (`setFloat64`/`getFloat64`, `setFloat32`).
- `dec` major 7: add `info` 25/26/27 → `new CborFloat(widened)` (so decode→re-encode parity
  preserves float-ness).

## `codec.ts`
- `toWire` `case "scalar"`: when the scalar's kind is `float`, return
  `new CborFloat(Number(value))` (rule E — an int/bool in a float field coerces). **Read
  `trial/ts/src/schema.ts`** to see how a scalar `TypeRef` carries its kind; the current
  `case "scalar": return value` doesn't inspect it.
- `fromWire` `case "scalar"`: unwrap — `if (cv instanceof CborFloat) return cv.value;`.

## Verify
Run the `trial/ts` test suite (check the package's `package.json` for the runner — Deno or
Node) against your copied `float_vectors.json`. For any ambiguity, mirror the Python
reference `wire/cbor.py` (`_float_bytes` + major-7 decode) and `wire/codec.py` exactly.

## Out of scope
Do **not** edit the generated TS fixtures under `taut/docs/examples/.../typescript/`. Once
this port lands in `trial`, those examples are refreshed by the example build, separately.
