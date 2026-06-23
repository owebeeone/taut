# Taut Res+Ext Parity — Phase 2: Go

Read [TautResExtP2-Base.md](TautResExtP2-Base.md) first; reuse
[history/TautFloatP2-Go.md](history/TautFloatP2-Go.md) for the struct-`Cbor` idiom.

**Files you own:** `src/taut/gen/runtime/cbor.go` (residual accessor present; map is `[]KV`) ·
`src/taut/gen/go.py` (emits `WireResidual []KV`, `append(m, x.WireResidual...)` then `Encode` sorts) ·
**NEW** `src/taut/gen/runtime/ext.go` · `src/tests/test_go.py` + a Go harness.

**Residual (verify+fix).** `go.py` appends `WireResidual` to the map and relies on `Encode`'s
ascending-key sort — so interleave *should* be correct. **Prove it:** generate the fixture
`--forward-compat`, run `residual_vectors.json` decode→re-encode (incl. interleaved + band-tag
unknowns), byte-diff vs the oracle.

**Extensions (implement) — `ext.go`.** Over `Cbor{Map []KV}`:
`ExtSet(host []byte, tag int64, value Cbor) []byte` → `Decode` host, rebuild `[]KV` without `tag`,
append `KV{tag, value}`, `Encode` (sorts). `ExtGet(host []byte, tag int64) (Cbor, bool)`.
`ExtClear(host []byte, tag int64) []byte`. Band-check `tag >= 1<<20` (panic below band). `value` is
`ExtMsg.ToCbor()`; `ExtGet` returns the nested `Cbor` for `ExtMsg.FromCbor`.

**Verify:** go available — a tiny module in /tmp over both corpora + a differential fuzz. Stdlib only
(`math`, `sort`). Extend `test_go.py` for the new shape.
