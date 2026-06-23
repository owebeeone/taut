# Taut Float — Phase 2: Java

Read [TautFloatP2-Base.md](TautFloatP2-Base.md) first.

**Files you own:** `src/taut/gen/runtime/Cbor.java` · `src/taut/gen/java.py` ·
`src/tests/test_java.py` (shape) + a Java parity harness.

**Value model — class (needs a NEW field + constructor ripple).** `Cbor` stores bool in
`long i`. Add:
- a `FLOAT` constant (kinds run `INT=0 … NULL=6`, so `FLOAT = 7`),
- a `public final double d;` field,
- a factory whose name avoids the `float` keyword — mirror the existing `int_`, e.g.
  `public static Cbor float_(double v)`,
- extend the **private constructor** to take `double d` — and update the existing factories
  (`int_`, `text`, `bytes`, `bool`, `arr`, `map`, `NUL`) to pass `0` for it (positional
  constructor, so every call site ripples).

**Runtime (`Cbor.java`):** `enc` add `case FLOAT ->` shortest-form; `dec` major 7 add
25/26/27 → the float factory. **Narrowing (JVM):** same double-rounding caveat as Kotlin —
hand-roll double→half **directly**. Bits: `Double.doubleToLongBits`, `Float.floatToIntBits`;
single via `(float)v` round-trip.

**Codegen (`java.py`):** `_java_ty` prim/boxed (→ `"double"` / `"Double"`), `_enc`
(→ `Cbor.float_({expr})`, matching your factory name), `_dec` (→ `{expr}.d`).
