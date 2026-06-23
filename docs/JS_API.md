# taut — JavaScript API

> Using taut-generated **JavaScript** code: native types, the deterministic-CBOR wire,
> forward-compatibility, and side-channel extensions. Authoring an IR is in
> [Reference.md](Reference.md); serving a service is in [Server.md](Server.md).

Generated JavaScript is plain ES classes over a vendored, dependency-free CBOR runtime
(CommonJS, Node only). Every language reproduces the *same bytes* — the conformance
corpus proves it.

## 1. Generate

```sh
tautc gen --lang js --with-runtime -o <out>
```

Writes, into `<out>/js/`:

| file | what |
| --- | --- |
| `api.js` | native types (class/enum) + `toCbor`/`fromCbor` |
| `cbor.js` | the deterministic-CBOR runtime (`Cbor`, `encode`, `decode`) |
| `ext.js` | extension accessors (`extSet`/`extGet`/`extClear`) |
| `client.js` / `server.js` | typed stubs over a transport (see [Server.md](Server.md)) |

Generated code resolves the runtime by relative `require("./cbor.js")` — keep the files
side by side. No npm dependencies; Node is the whole toolchain.

## 2. Native types

Enums are frozen `name → wire` objects; a field holds the wire int directly:

```js
const TaskState = Object.freeze({ open: 0, doing: 1, done: 2 });
// task.state = TaskState.doing;   // 1 on the wire
```

Messages are ES classes with an **instance** `toCbor()` and a static `fromCbor()`:

```js
class User {
  constructor(o = {}) { this.id = o.id; this.name = o.name; }
  toCbor() { ... }                  // CMap([[1, ..], [2, ..]])
  static fromCbor(c) { ... }        // cget(c, 1).i, cget(c, 2).s
}
new User({ id: 1, name: "ada" });   // construct from a plain object
```

Field mapping: `INT → number`, `STR → string`, `BYTES → Uint8Array`, `BOOL → boolean`,
`FLOAT → number` (number carries both int and float), `List(T) → Array<T>`,
`Map(K,V) → Map<K,V>`. **Optional** fields are nullable (encoded as CBOR `null` when
`null`/`undefined`). **Transient** fields live on the instance but never on the wire.

## 3. Encode / decode

A message ↔ CBOR bytes goes through the generated `toCbor`/`fromCbor` plus the
runtime `encode`/`decode`:

```js
const { encode, decode } = require("./cbor.js");
const { Task } = require("./api.js");

const bytes = encode(task.toCbor());      // Uint8Array — serialize
const task = Task.fromCbor(decode(bytes)); // deserialize
```

## 4. The `Cbor` runtime (`cbor.js`)

A tiny frozen subset of RFC 8949 in core deterministic encoding (definite lengths,
shortest-form ints, ascending map keys, shortest-form floats). Hand-rolled, zero deps.
Integers are JS numbers (safe to 2^53, like the TS codec); bytes are `Uint8Array`.

A `Cbor` is a tagged plain object `{ kind, ... }`, built by the exported constructors:

```js
CInt(n)    // { kind, i }      CBytes(b)  // { kind, b }   (Uint8Array)
CText(s)   // { kind, s }      CBool(x)   // { kind, i }
CFloat(x)  // { kind, f }      CArr(a)    // { kind, arr }
CMap(m)    // { kind, map }    (m: array of [intKey, Cbor])   CNull()

encode(c) // -> Uint8Array
decode(data) // -> Cbor   (data: Uint8Array)
```

Accessors (read the tagged shape): `cget(c, key)` (map value by int tag — throws if
absent), `cmapEntries(c)` (the `[key, Cbor]` array, or `[]` if not a map), `isNull(c)`.
Scalar fields are read off the tag directly: `.i`, `.s`, `.b`, `.f`.

## 5. Forward-compatibility (unknown-field preservation)

Generate with `--forward-compat` and each class gains a `wireResidual` field
(`Array<[number, Cbor]>`, defaulting to `[]`). On `fromCbor`, tags the class doesn't
name are captured there; on `toCbor`, they're pushed back and re-emitted **merged with
the known fields in one ascending-tag order** (`encode` sorts map keys) — so a node that
*decodes → edits → re-encodes* a newer message never drops fields it doesn't understand.
A message with no unknowns is byte-identical with or without the flag.

A schema that declares an extension **requires** `--forward-compat` (build error
otherwise — extensions ride the residual space).

## 6. Extensions (side-channels) — `ext.js`

Attach / read / clear a declared extension on *any* host message's wire bytes, knowing
only the extension's schema (never the host's). Tags live in the band ≥ `2**20`:

```js
const { extSet, extGet, extClear } = require("./ext.js");

extSet(hostBytes, tag, value)   // -> Uint8Array   attach / replace
extGet(hostBytes, tag)          // -> Cbor | null  (null if absent)
extClear(hostBytes, tag)        // -> Uint8Array   strip
```

`value` is the generated extension message's instance `toCbor()`; decode `extGet`'s
result with `ExtMsg.fromCbor()`:

```js
const raw = extSet(host, 0x100001, decision.toCbor());
const got = extGet(raw, 0x100001);
const decision = got ? Decision.fromCbor(got) : null;
const stripped = extClear(raw, 0x100001);
```

A below-band `tag` throws; a non-map host throws. The host app decodes its own message
obliviously — the extension rides in `wireResidual` and survives.

## 7. Consuming the runtime

`cbor.js` / `ext.js` are vendored, dependency-free CommonJS source — drop them next to
`api.js` and `require` them; `api.js` does `require("./cbor.js")`. Node is the only
toolchain. The bytes match every other taut target.
