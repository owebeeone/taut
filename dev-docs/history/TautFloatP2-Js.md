# Taut Float — Phase 2: JavaScript

Read [TautFloatP2-Base.md](TautFloatP2-Base.md) first.

**Files you own:** `src/taut/gen/runtime/cbor.js` · `src/taut/gen/js.py` ·
`src/tests/test_js.py` (shape) + a JS parity harness.

**Value model — tagged object.** Kinds run `INT=0 … NULL=6`, so add `const FLOAT = 7;`
plus `const CFloat = (x) => ({ kind: FLOAT, f: x });`. **Add `CFloat` to `module.exports`**
at the bottom of the file.

**Runtime (`cbor.js`):** `enc` add `case FLOAT:` shortest-form; `dec` major 7 add 25/26/27
→ `CFloat(...)`. **Narrowing:** no portable native f16 — hand-roll double→half RNE. Use a
`DataView` for bits (`setFloat64`/`getFloat64`, `setFloat32`/`getFloat32`); single round-trip
via `Math.fround(v) === v`.

**Codegen (`js.py`):** `_enc` (→ `CFloat({expr})`), `_dec` (→ `{expr}.f`).

**Verify:** if Node is present, run a parity harness over the corpus; extend `test_js.py`
for the emitted shape.
