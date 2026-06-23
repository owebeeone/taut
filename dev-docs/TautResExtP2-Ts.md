# Taut Res+Ext Parity — Phase 2: TypeScript

Read [TautResExtP2-Base.md](TautResExtP2-Base.md) first. TypeScript is now a taut-owned
runtime-resource target. The implementation source of truth is in this repo.

**Files you own:** `src/taut/gen/runtime/typescript/cbor.ts` and
`src/taut/gen/runtime/typescript/codec.ts` only for verify-first residual/structural-CBOR fixes;
`src/taut/gen/runtime/typescript/schema.ts` only if `loadSchema(resext.ir.json)` demonstrably fails;
**NEW** `src/taut/gen/runtime/typescript/ext.ts`; `src/tests/test_ts.py`; and any temporary
TypeScript harness source emitted by the Python test. The TypeScript runtime is already registered
in `scaffold._RUNTIMES`; do not edit scaffold unless this prompt is stale.

**Do not change:** external scratch workspaces, taut's generated examples under `docs/examples/**`,
`ir/*`, committed corpora/generators, Python `ext.py`, another language, package dependencies, or
unrelated FLOAT work.

**Runtime handoff:** use `tautc gen ir/resext.taut.py --lang typescript --api-only --with-runtime`
into a temp directory from `src/tests/test_ts.py`. The emitted temp TypeScript directory should
contain `api.ts`, `cbor.ts`, `codec.ts`, `schema.ts`, `taut_client.ts`, and after this phase
`ext.ts`. Export neutral IR JSON for `loadSchema(json)` into the same temp test directory; the TS
test must not import `ir/resext.taut.py` directly.

Example Python-side setup shape:

```py
from pathlib import Path
from taut.ir.load import load_schema
from taut.ir.export import export_to
from taut import cli

gen_dir = tmp_path / "gen"
cli.main([
    "gen", "ir/resext.taut.py", "-o", str(gen_dir),
    "--lang", "typescript", "--api-only", "--with-runtime", "--forward-compat",
])
export_to(load_schema("ir/resext.taut.py"), gen_dir / "typescript" / "resext.ir.json")
```

**Residual (verify+fix).** TS is interpreter-style: `codec.ts` `toWire`/`fromWire` capture unknown
tags in `__unknown__` (`Map<number, CborValue>`) and re-emit them; `cbor.ts` sorts map keys
ascending. Run `corpus/residual_vectors.json` decode -> re-encode through the emitted runtime and
byte-diff. Verify the interleaved unknown tag and band-tag unknown round-trip byte-identical. If
green, do not edit `cbor.ts` or `codec.ts`.

**Extensions (implement) — `ext.ts`.** Over structural `CborValue` (`Map<number, CborValue>`):
`extSet(host, tag, value: CborValue): Uint8Array` decodes host to a map, sets/replaces `tag`, and
encodes the whole host once; `extGet(host, tag): CborValue | null`; `extClear(host, tag):
Uint8Array`. Band-check FIRST: `Number.isSafeInteger(tag) && tag >= 2 ** 20`. Reject non-map hosts;
do not coerce scalars/arrays into empty maps.

The typed extension bridge must be structural, not byte-string storage. For set/replace rows, build
or decode a native `Decision`, then do:

```ts
const decisionRef = { k: "msg", name: "Decision" } as const;
const nested = cborDecode(encodeRef(schema, decisionRef, decision));
const wire = extSet(host, tag, nested);
```

For get rows, do the reverse:

```ts
const got = extGet(host, tag);
const decision = got === null ? null : decodeRef(schema, decisionRef, cborEncode(got));
```

The test must fail if `extSet` stores a `Uint8Array` CBOR byte string at the band tag instead of the
nested `Decision` map. Do not pass raw `encodeRef(...)` bytes directly to `extSet`. No
`CborFloat`-style wrapper — the extension value is a map, not a number.

**Tests/gates to add:** residual decode -> re-encode parity over all residual rows; extension
set/replace/get/absent/clear parity over all ext rows; below-band tag before host decode; non-map
host rejection; a structural assertion that the decoded band-tag value is a `Map`, not `Uint8Array`;
and the fixed-seed differential fuzz described by the base brief.

**Required evidence:** run the new in-repo pytest, e.g.
`PYTHONPATH=src python -m pytest src/tests/test_ts.py src/tests/test_resext_vectors.py -q`. The
pytest should run Node with `node --experimental-strip-types --test <temp>/resext.test.ts`. If a
TypeScript checker is already available without adding dependencies, also run it; otherwise state
that no `tsc` gate is available. No package deps.
