# Taut Res+Ext Parity — Phase 2: Swift

Read [TautResExtP2-Base.md](TautResExtP2-Base.md) first; reuse
[history/TautFloatP2-Swift.md](history/TautFloatP2-Swift.md) for the `Cbor` enum idiom.

**Files you own:** `src/taut/gen/runtime/cbor.swift` (residual accessor present) · `src/taut/gen/swift.py`
(emits the `wireResidual` field) · **NEW** `src/taut/gen/runtime/ext.swift` · the Swift harness/tests.

**Residual (verify+fix).** Generate the fixture `--forward-compat`, run `residual_vectors.json`
decode→re-encode, byte-diff. Verify the generated `encode`/`toCbor` emits known + residual in one
ascending order (interleaved unknown tag + band-tag unknown).

**Extensions (implement) — `ext.swift`.** Over the `Cbor` enum (`case map([(Int64, Cbor)])`):
`extSet(_ host: [UInt8], tag: Int64, value: Cbor) -> [UInt8]` → `decode` to `.map(m)`, filter out `tag`,
append `(tag, value)`, `encode(.map(m))` (sorts). `extGet(_ host, tag) -> Cbor?` (nil if absent).
`extClear(_ host, tag) -> [UInt8]`. Band-check `tag >= 1 << 20`. `value` is the caller's
`ExtMsg.toCbor()`; `extGet` returns the nested `Cbor` for `ExtMsg.fromCbor`.

**Verify:** swiftc available — build a harness over both corpora + a differential fuzz vs Python.
