# Taut Res+Ext Parity — Phase 2: Swift

Read [TautResExtP2-Base.md](TautResExtP2-Base.md) first; reuse
[history/TautFloatP2-Swift.md](history/TautFloatP2-Swift.md) for the `Cbor` enum idiom.

**Files you own:** **NEW** `src/taut/gen/runtime/ext.swift` · `src/tests/test_swift.py`.
`src/taut/gen/runtime/cbor.swift` and `src/taut/gen/swift.py` are verify-first only: residual support
appears present, and the generator emits `wire_residual` (single underscore per D10, **not**
`wireResidual`), so edit them only if `residual_vectors.json` demonstrates a real Swift divergence.

**Do not change:** `ir/*`, the corpora/generators, Python `ext.py`, `gen/scaffold.py`, another
language, package dependencies, or proven FLOAT/CBOR encode paths unless tied to a failing ResExt
vector.

**Residual (verify+fix).** Generate the fixture `--forward-compat`, run `residual_vectors.json`
decode→re-encode, byte-diff. Verify the generated `encode`/`toCbor` emits known + residual in one
ascending order (interleaved unknown tag + band-tag unknown).

**Extensions (implement) — `ext.swift`.** Over the `Cbor` enum (`case map([(Int64, Cbor)])`):
`extSet(_ host: [UInt8], tag: Int64, value: Cbor) -> [UInt8]` → `decode` to `.map(m)`, filter out `tag`,
append `(tag, value)`, `encode(.map(m))` (sorts). `extGet(_ host, tag) -> Cbor?` (nil if absent).
`extClear(_ host, tag) -> [UInt8]`. Use the existing Swift runtime's trap-style convention:
`precondition(tag >= 1 << 20)` before host decode, and `fatalError` or `preconditionFailure` for a
decoded host whose root is not `.map`. Do not introduce a throwing API unless all three accessors
use that style consistently and the tests assert it. `value` is the caller's `Decision.toCbor()`;
`extGet` returns the nested `Cbor` for `Decision.fromCbor`.

**Tests/gates to add:** residual byte parity over all four residual rows; extension byte parity over
all five ext rows through generated `Decision.toCbor()` / `Decision.fromCbor`; below-band tag before
host decode; non-map host rejection; and the fixed-seed differential fuzz described by the base
brief. Because trap assertions are awkward in plain Swift, the Python test may compile/run tiny
subprocess harnesses and assert non-zero exit for invalid cases.

**Required evidence:** run
`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m pytest -q -p no:cacheprovider src/tests/test_resext_vectors.py src/tests/test_swift.py`.
Report `swiftc --version`, corpus parity result, invalid-case subprocess results, fuzz seed, and
mismatch count.
