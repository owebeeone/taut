# Taut Res+Ext Parity — Phase 2: TypeScript  (SEPARATE REPO — `trial`, not the taut worktree)

> **⚠ Runs in the `trial` repo**, like FLOAT — `trial/ts/src/*`, a standalone package, NOT the
> `taut` worktree (whose only TS is generated examples). See
> [history/TautFloatP2-Ts.md](history/TautFloatP2-Ts.md) for the cross-repo setup and the
> structural-`CborValue` background.

> **⚠⚠ BLOCKER — resolve before dispatching this task: the `trial/ts` package is NOT in the
> `taut-dev-cross` checkout.** `taut-dev-cross/trial` has only `cpp/` (no `ts/`), and `taut-ts` holds
> only generated TS examples. This task cannot run until the `trial` repo is provided as its own
> checkout/worktree alongside taut. (Owner decision — see the chat note.)

Read [TautResExtP2-Base.md](TautResExtP2-Base.md) first. The wire profile + parity parameters there
govern; only the file scope + cross-repo oracle differ.

**Files you own (in `trial`):** `trial/ts/src/cbor.ts` · `trial/ts/src/codec.ts`
(residual `__unknown__` lives here) · **NEW** `trial/ts/src/ext.ts` · `trial/ts/test/`.

**Cross-repo oracle:** copy taut's `corpus/residual_vectors.json` + `corpus/ext_vectors.json` into
`trial/ts/test/` as fixtures (as FLOAT did with `float_vectors.json`).

**Residual (verify+fix).** TS is interpreter-style: `codec.ts` `toWire`/`fromWire` already capture
unknown tags in `__unknown__` (a `Map<number, CborValue>`) and re-emit them; `cbor.ts` `enc` sorts
the map keys ascending. Run the residual vectors decode→re-encode; byte-diff. Verify an interleaved
unknown tag and a band-tag unknown round-trip byte-identical.

**Extensions (implement) — `ext.ts`.** Over the structural `CborValue` (`Map<number, CborValue>`):
`extSet(host, tag, value: CborValue): Uint8Array` → `decode` host to a `Map`, `map.set(tag, value)`,
`encode(map)` (sorts). `extGet(host, tag): CborValue | null`. `extClear(host, tag): Uint8Array`.
Band-check FIRST: `Number.isSafeInteger(tag) && tag >= 2 ** 20`. The ext `value` is a nested `Map`; to
satisfy the base's typed-path requirement, build it via the schema-aware codec and read it back —
**but `toWire`/`fromWire` are file-LOCAL `function`s in `codec.ts` (not exported)**, so either export
them or use the already-exported `encodeRef`/`decodeRef`. That typed path needs a `SchemaIndex`, so bring
the fixture across too: export `ir/resext.taut.py` → IR JSON and `loadSchema` it (corpora hex alone is
not enough for the typed codec). (No `CborFloat`-style wrapper — the ext value is a map, not a number.)

**Verify:** `node --experimental-strip-types` (or `npx tsx`) — run the `trial/ts` tests + a
differential fuzz over both corpora vs the Python reference. No package deps.
