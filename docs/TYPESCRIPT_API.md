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
| `cbor.ts` | the deterministic-CBOR runtime (`CborValue`, `encode`, `decode`, `DecodeError`) |
| `schema.ts` | the IR loader (`SchemaIndex`, `loadSchema`) |
| `ext.ts` | extension accessors (`extSet`/`extGet`/`extClear`) |
| `client.ts` / `taut_client.ts` | typed stubs over a transport (see [Server.md](Server.md)) |

`--with-runtime` vendors `codec.ts` / `cbor.ts` / `schema.ts` / `ext.ts` /
`taut_client.ts` verbatim from `src/taut/gen/runtime/typescript/` — drop-in source,
**no dependencies**. Run with `node --experimental-strip-types` (the runtime is plain
`.ts`, see §7).

## 2. Native types

The emitter writes `api.ts` for the editor — `export interface` per message, a
string-union per enum. These are *shapes only*; nothing in `api.ts` touches the
wire (that's the codec, §3).

```ts
export type TaskState = "open" | "doing" | "done";

export interface Task {
  id: bigint;
  title: string;
  state: TaskState;
  assignee: User | null;
  comments: Comment[];
  labels: Map<string, string>;
}
```

A **native value** is a plain object keyed by field name. Field mapping:
`INT → bigint`, `STR → string`, `BYTES → Uint8Array`, `BOOL → boolean`,
`FLOAT → number`, `List(T) → T[]`, `Map(K,V) → Map<K,V>`, **enum → the member-name
string** (e.g. `"done"`, not its integer). Decode returns every int as a `bigint`;
encode also takes a safe-integer `number`. A `Map(K,V)` field must be a real `Map`: the
codec iterates `.entries()`. **Optional** fields are `T | null` (encoded as CBOR `null`
when absent). **Transient** fields are in the type but never on the wire.

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
  id: 1n, title: "ship taut", state: "done",
  assignee: { id: 7n, name: "ann" },
  comments: [{ author: { id: 2n, name: "bob" }, text: "lgtm" }],
  labels: new Map([["team", "infra"], ["area", "wire"]]),  // Map, not object
};

const bytes: Uint8Array = encode(schema, "Task", task);   // serialize
const back = decode(schema, "Task", bytes);               // deserialize, under Task's bounds
```

`tasks.ir.json` is the same neutral IR every language consumes — emit it with
`tautc` (or load the `.taut.py` through the Python tooling); it is *not* a
TypeScript artifact. `loadSchema` reads IR versions 1 and 2 and refuses any other.

`decode` is the typed decode from bytes. It applies the message's bounds, the schema's
`max_depth` and `max_encoded_len` options as they resolve for it: the message's own,
else the file's, else the defaults, depth 32 and no length bound. TypeScript reads them
from the IR's `effective` values, so there are no generated constants:
`schema.effective("Task")` is `{ max_depth: 32, max_encoded_len: null }` here. The
call's root decides its bounds: a message nested inside a `Task` does not change them.

For an IR-declared method's param / output / event type (a bare `TypeRef`, not a
named message), use the ref-driven pair; `decodeRef` applies a message root's bounds,
and the file's for any other root, such as a `list<Task>`:

```ts
import { encodeRef, decodeRef } from "./codec.ts";
const bytes = encodeRef(schema, tref, value);
const value = decodeRef(schema, tref, bytes);
```

Decode is fail-closed: bad input throws `DecodeError`, and nothing else escapes,
whatever the bytes. Its `tag` is a `DecodeErrorTag`, and its payload is in the fields
that tag names: `info`, `major`, `key`, `value`, `expected`, `enum`, `len` and `limit`.

```ts
import { DecodeError } from "./cbor.ts";

try {
  use(decode(schema, "Task", bytes));
} catch (e) {
  if (!(e instanceof DecodeError)) {
    throw e;
  }
  report(e.tag, e);                  // e.g. "TooDeep", with e.limit === 32
}
```

Code that sees errors from more than one vendored copy tests `e.name === "DecodeError"`
instead of `instanceof`. An absent field is `MissingKey`, an optional one too, unless it
is `optional=MISSING_OK`, which reads it as `null`. `taut_client.ts` catches the error: a
call whose result does not decode rejects with it, and a stream whose event does not
decode ends and hands it to `subscribe`'s `onError`. The full table of tags and payloads
is in [CodecContract.md](CodecContract.md).

## 4. The `Cbor` runtime (`cbor.ts`)

A tiny frozen subset of RFC 8949 in core deterministic encoding (definite lengths,
shortest-form ints, ascending **integer** map keys — keys carry field tags —,
shortest-form floats). Hand-rolled, zero deps; byte-for-byte the same subset as
the Python and Rust runtimes.

`CborValue` is a **structural** union (no tagged `enum` — the JS type *is* the
discriminant), with floats boxed so they survive the integer/float split:

```ts
export type MapKey = number | bigint;

export type CborValue =
  | bigint | number | CborFloat | string | boolean | null
  | Uint8Array | CborValue[] | Map<MapKey, CborValue>;

export const DEFAULT_MAX_DEPTH = 32;    // the depth bound where none is given
export const MAX_DEPTH_CEILING = 128;   // no decode applies a deeper bound

export interface DecodeLimits { maxDepth?: number; maxEncodedLen?: number | null }

export function encode(value: CborValue): Uint8Array;
export function decode(data: Uint8Array, limits: DecodeLimits = {}): CborValue;
```

`decode` returns every int as a `bigint`, exact over the whole `i64` range; `encode`
also takes a `number`, which must be an integer (a non-integer throws "no floats").
Reals go through `new CborFloat(x)` and decode back as a `CborFloat` (read `.value`).
A map key is a `number` up to 2^53 − 1 and an exact `bigint` above it, so a map
re-encodes as it was read.

This `decode` is the raw decode and knows no schema: it applies depth 32 and no length
bound unless its caller passes limits. An array or map has depth one more than the
arrays and maps around it, so a top-level one has depth 1; one deeper than `maxDepth` is
`TooDeep` (`limit`), refused once its head is read. A `maxDepth` above the ceiling
applies the ceiling, and `limit` names the bound applied; with a `maxEncodedLen`, longer
input is `TooLarge` (`len`, `limit`) before a byte is read. A bad limit is the caller's
error, a `TypeError` or `RangeError`, never a `DecodeError`.

## 5. Forward-compatibility (unknown-field preservation)

Default-on — there is no flag to set in TypeScript. On `decode`, any map tags the
schema doesn't name are captured on the native object under a **`__unknown__`**
`Map<MapKey, CborValue>`; on `encode`, they're re-emitted **merged with the known
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
serialized byte string. Produce it by encoding the message with the codec and decoding
those bytes back through `cbor.ts`, or build the `Map<number, CborValue>` directly:

```ts
import { extSet, extGet, extClear } from "./ext.ts";
import { type CborValue } from "./cbor.ts";

const TAG = 0x100001;                                 // ≥ 2**20

// the extension message as a structural CBOR Map (tag 1 = an int field):
const decision: CborValue = new Map<number, CborValue>([[1, 2n]]);

const raw  = extSet(host, TAG, decision);             // attach / replace
const got  = extGet(raw, TAG);                        // CborValue | null
const bare = extClear(raw, TAG);                      // strip it back out
```

They fail closed: for any host bytes each returns or throws `DecodeError`, and a host
that is not a map is `WrongType` (`map`). Not knowing the host's schema, they read a
host at the depth ceiling, 128, with no length bound, the only bounds every valid host
meets; the host's own reader applies the host's. A below-band `tag` is the caller's
error, a `RangeError` thrown before the host is read. The host app decodes its own
message unchanged — the extension rides in its `__unknown__` residual (§5) and survives.

## 7. Consuming the runtime

`codec.ts` / `cbor.ts` / `schema.ts` / `ext.ts` are vendored, **dependency-free**
source — drop them in next to your `api.ts` and import; the imports between them
are relative (`./cbor.ts`, `./schema.ts`). The only toolchain is `node
--experimental-strip-types` (it strips the types and runs the `.ts` directly — no
build step, no `tsc`, no `package.json`). The bytes match every other taut target.

```sh
node --experimental-strip-types example.ts
# typescript: Task round-tripped in 72 bytes (ok)
```

## 8. Changed in v0.10.0

- `cbor.ts`'s `decode` takes `{ maxDepth, maxEncodedLen }`, and `codec.ts`'s `decode`
  and `decodeRef` apply the root's bounds from the IR. Input nested deeper than its
  bound, into which v0.9 recursed until a `RangeError` escaped, is `TooDeep`.
- `DecodeErrorTag` gains `TooDeep` and `TooLarge`, with `len` and `limit`.
  `WrongType.expected` is `text` or `array` where v0.9 said `str` or `list`.
- An absent optional field is `MissingKey` unless it is `optional=MISSING_OK`; v0.9 read
  it as `null`.
- `loadSchema` refuses an IR version other than 1 or 2, and an `effective` naming an
  option it does not know. The extension helpers throw `RangeError` and `DecodeError`
  where v0.9 threw a plain `Error`. `taut_client.ts` rejects a call, or ends a stream,
  on a `DecodeError`.
- New: `DEFAULT_MAX_DEPTH`, `MAX_DEPTH_CEILING`, `DecodeLimits`, `MISSING_OK`, and
  `SchemaIndex`'s `effective` and `rootEffective`.
