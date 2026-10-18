# Taut Res+Ext Parity — Phase 2: Go

Read [TautResExtP2-Base.md](TautResExtP2-Base.md) first; reuse
[history/TautFloatP2-Go.md](history/TautFloatP2-Go.md) for the struct-`Cbor` idiom.

**Files you own:** **NEW** `src/taut/gen/runtime/ext.go` · `src/tests/test_go.py`.
`src/taut/gen/runtime/cbor.go` and `src/taut/gen/go.py` are verify-first only: residual support
appears present (`WireResidual []KV`, `append(m, x.WireResidual...)`, then `Encode` sorts), so edit
them only if `residual_vectors.json` demonstrates a real Go divergence.

**Do not change:** `ir/*`, the corpora/generators, Python `ext.py`, `gen/scaffold.py`, another
language, package dependencies, or proven FLOAT/CBOR encode paths unless tied to a failing ResExt
vector.

**Residual (verify+fix).** `go.py` appends `WireResidual` to the map and relies on `Encode`'s
ascending-key sort — so interleave *should* be correct. **Prove it:** generate the fixture
`--forward-compat`, run `residual_vectors.json` decode→re-encode (incl. interleaved + band-tag
unknowns), byte-diff vs the oracle.

**Extensions (implement) — `ext.go`.** Over `Cbor{Map []KV}`:
`ExtSet(host []byte, tag int64, value Cbor) []byte` → `Decode` host, rebuild `[]KV` without `tag`,
append `KV{tag, value}`, `Encode` (sorts). `ExtGet(host []byte, tag int64) (Cbor, bool)`.
`ExtClear(host []byte, tag int64) []byte`. Band-check `tag >= 1<<20` before host decode (panic below
band). Reject non-map hosts; do not coerce a nil/scalar map to empty. `value` is the ext message as a
`Cbor` map (`Decision.ToCbor()`). **Harness note:** `ext_vectors.json`'s `value` is the
nested Decision-CBOR **hex** — `Decode` it to a `Cbor` and pass that; do NOT wrap the raw hex bytes as a
CBOR byte string. `ExtGet` returns the nested `Cbor` for `DecisionFromCbor`.

**Tests/gates to add:** residual byte parity over all four residual rows; extension byte parity over
all five ext rows through generated `Decision.ToCbor()` / `DecisionFromCbor`; below-band tag before
host decode; non-map host rejection; and the fixed-seed differential fuzz described by the base
brief.

**Required evidence:** run
`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m pytest -q -p no:cacheprovider src/tests/test_resext_vectors.py src/tests/test_go.py`.
Report `go version`, corpus parity result, invalid-case result, fuzz seed, and mismatch count.
Stdlib only (`math`, `sort`). Extend `test_go.py` for the new shape.
