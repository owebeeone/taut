# taut — TypeScript API

> Using taut-generated **TypeScript** code: native types, the deterministic-CBOR
> wire, forward-compatibility, and side-channel extensions. Authoring an IR is in
> [Reference.md](Reference.md); serving a service is in [Server.md](Server.md).

TypeScript is **interpreter-style, not per-message codegen**: one IR-driven codec
walks the schema at run time, so there is no generated encoder per message. The
emitter writes `export interface` types for editor ergonomics; the bytes come from
the runtime. Every language reproduces the *same bytes* — the conformance corpus
proves it (all targets agree, live).

## 1. Generate

```sh
tautc gen <ir> --lang typescript --with-runtime -o <out>
```

Writes, into `<out>/typescript/`:

| file | what |
| --- | --- |
| `api.ts` | native types — `export interface` / enum-as-union (types only, no codec) |
| `codec.ts` | the IR-driven codec (`encode`/`decode`, `encodeRef`/`decodeRef`) |
| `cbor.ts` | the deterministic-CBOR runtime (`CborValue`, `encode`, `decode`) |
| `schema.ts` | the IR loader (`SchemaIndex`, `loadSchema`) |
| `ext.ts` | extension accessors (`extSet`/`extGet`/`extClear`) |
| `client.ts` / `taut_client.ts` | typed stubs over a transport (see [Server.md](Server.md)) |

`--with-runtime` vendors `codec.ts` / `cbor.ts` / `schema.ts` / `ext.ts` verbatim
from `src/taut/gen/runtime/typescript/` — drop-in source, **no dependencies**. Run
with `node --experimental-strip-types` (the runtime is plain `.ts`, see §7).

## 2. Native types

The emitter writes `api.ts` for the editor — `export interface` per message, a
string-union per enum. These are *shapes only*; nothing in `api.ts` touches the
wire (that's the codec, §3).

```ts
export type TaskState = "open" | "doing" | "done";

export interface Task {
  id: number;
  title: string;
  state: TaskState;
  assignee: User | null;
  comments: Comment[];
  labels: Record<string, string>;
}
```

A **native value** is a plain object keyed by field name. Field mapping:
`INT → number`, `STR → string`, `BYTES → Uint8Array`, `BOOL → boolean`,
`FLOAT → number`, `List(T) → T[]`, **enum → the member-name string** (e.g.
`"done"`, not its integer). **Optional** fields are `T | null` (encoded as CBOR
`null` when absent). **Transient** fields are in the type but never on the wire.

One run-time caveat the `interface` glosses over: a **`Map(K,V)` field is a real
`Map`** at the codec boundary, not the `Record` the type advertises — build it as
`new Map([["team", "infra"]])`. (The `Record` is an editor convenience; the codec
iterates `.entries()`.)

## 3. Encode / decode

Load the neutral IR JSON once into a `SchemaIndex`, then drive `encode`/`decode`
by **message name** — no per-message generated function:

```ts
import { readFileSync } from "node:fs";
import { loadSchema } from "./schema.ts";
import { encode, decode } from "./codec.ts";

const ir = JSON.parse(readFileSync("tasks.ir.json", "utf8"));
const schema = loadSchema(ir);                 // build the SchemaIndex once

const task = {
  id: 1, title: "ship taut", state: "done",
  assignee: { id: 7, name: "ann" },
  comments: [{ author: { id: 2, name: "bob" }, text: "lgtm" }],
  labels: new Map([["team", "infra"], ["area", "wire"]]),  // Map, not object
};

const bytes: Uint8Array = encode(schema, "Task", task);   // serialize
const back = decode(schema, "Task", bytes);               // deserialize
```

`tasks.ir.json` is the same neutral IR every language consumes — emit it with
`tautc` (or load the `.taut.py` through the Python tooling); it is *not* a
TypeScript artifact.

For an IR-declared method's param / output / event type (a bare `TypeRef`, not a
named message), use the ref-driven pair:

```ts
import { encodeRef, decodeRef } from "./codec.ts";
const bytes = encodeRef(schema, tref, value);
const value = decodeRef(schema, tref, bytes);
```

## 4. The `Cbor` runtime (`cbor.ts`)

A tiny frozen subset of RFC 8949 in core deterministic encoding (definite lengths,
shortest-form ints, ascending **integer** map keys — keys carry field tags —,
shortest-form floats). Hand-rolled, zero deps; byte-for-byte the same subset as
the Python and Rust runtimes.

`CborValue` is a **structural** union (no tagged `enum` — the JS type *is* the
discriminant), with floats boxed so they survive the integer/float split:

```ts
export type CborValue =
  | number | CborFloat | string | boolean | null
  | Uint8Array | CborValue[] | Map<number, CborValue>;

export function encode(value: CborValue): Uint8Array;
export function decode(data: Uint8Array): CborValue;
```

A bare `number` must be an integer (a non-integer throws "no floats"); reals go
through `new CborFloat(x)` and decode back as a `CborFloat` (read `.value`).
`decode` throws on trailing bytes.

## 5. Forward-compatibility (unknown-field preservation)

Default-on — there is no flag to set in TypeScript. On `decode`, any map tags the
schema doesn't name are captured on the native object under a **`__unknown__`**
`Map<number, CborValue>`; on `encode`, they're re-emitted **merged with the known
fields in one ascending-tag order** (CBOR sorts the keys). So a node that
*decodes → edits → re-encodes* a newer message never drops fields it doesn't
understand, and a message with no unknowns is byte-identical either way.

Extensions (§6) ride this same residual space — the host decodes its own message
obliviously and the extension survives the round-trip under `__unknown__`.

## 6. Extensions (side-channels) — `ext.ts`

Attach / read / clear a declared extension on *any* host message's wire bytes,
knowing only the extension's schema (never the host's). Tags live in the band ≥
`2**20` (`BAND_START`):

```ts
export function extSet(host: Uint8Array, tag: number, value: CborValue): Uint8Array;
export function extGet(host: Uint8Array, tag: number): CborValue | null;
export function extClear(host: Uint8Array, tag: number): Uint8Array;
```

The `value` is the extension message's **structural `CborValue` `Map`** — *not* a
serialized byte string. Produce it with the codec's `toWire` path by encoding then
decoding back through `cbor.ts`, or build the `Map<number, CborValue>` directly:

```ts
import { extSet, extGet, extClear } from "./ext.ts";
import { encode as cborEncode, decode as cborDecode } from "./cbor.ts";

const TAG = 0x100001;                                 // ≥ 2**20

// the extension message as a structural CBOR Map (tag 1 = an int field):
const decision: CborValue = new Map<number, CborValue>([[1, 2]]);

const raw  = extSet(host, TAG, decision);             // attach / replace
const got  = extGet(raw, TAG);                        // CborValue | null
const bare = extClear(raw, TAG);                      // strip it back out
```

A below-band `tag` throws; a host that doesn't decode to a top-level CBOR `Map`
throws. The host app decodes its own message unchanged — the extension rides in
its `__unknown__` residual (§5) and survives.

## 7. Consuming the runtime

`codec.ts` / `cbor.ts` / `schema.ts` / `ext.ts` are vendored, **dependency-free**
source — drop them in next to your `api.ts` and import; the imports between them
are relative (`./cbor.ts`, `./schema.ts`). The only toolchain is `node
--experimental-strip-types` (it strips the types and runs the `.ts` directly — no
build step, no `tsc`, no `package.json`). The bytes match every other taut target.

```sh
node --experimental-strip-types example.ts
# typescript: Task round-tripped in 43 bytes (ok)
```
