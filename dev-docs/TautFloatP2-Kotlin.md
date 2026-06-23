# Taut Float — Phase 2: Kotlin

Read [TautFloatP2-Base.md](TautFloatP2-Base.md) first.

**Files you own:** `src/taut/gen/runtime/cbor.kt` · `src/taut/gen/kotlin.py` ·
`src/tests/test_kotlin.py` (shape) + a Kotlin parity harness.

**Value model — class (needs a NEW field).** `class Cbor(val kind, val i, val s, val b,
val arr, val map)` stores bool in `i`. Add (all with defaults, so existing factories are
unaffected):
- `val f: Double = 0.0` constructor param,
- `const val FLOAT = 7` in the companion,
- `fun float(x: Double) = Cbor(FLOAT, f = x)`,
- `val floatVal: Double get() = f`.

**Runtime (`cbor.kt`):** `enc` add `Cbor.FLOAT ->` shortest-form; `dec` major 7 add 25/26/27.
**Narrowing (JVM):** `Float.floatToFloat16` (JDK 20+) takes a `Float`, so double→float→half
**double-rounds** — hand-roll double→half **directly** (RNE). Single via `v.toFloat()`
round-trip. Bits: `java.lang.Double.doubleToLongBits` / `java.lang.Float.floatToIntBits`.

**Codegen (`kotlin.py`):** `_kt_ty` (→ `"Double"`), `_default` (→ `"0.0"`), `_enc`
(→ `Cbor.float({expr})`), `_dec` (→ `{expr}.floatVal`).
