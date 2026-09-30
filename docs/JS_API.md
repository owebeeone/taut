# taut — JavaScript API

> Using taut-generated **JavaScript** code: native types, the deterministic-CBOR wire,
> forward-compatibility, and side-channel extensions. Authoring an IR is in
> [Reference.md](Reference.md); serving a service is in [Server.md](Server.md).

Generated JavaScript is plain ES classes over a vendored, dependency-free CBOR runtime
(CommonJS, Node only). Every language reproduces the *same bytes* — the conformance
corpus proves it.

## 1. Generate

```sh
tautc gen <ir> --lang js --with-runtime -o <out>
```

Writes, into `<out>/js/`:

| file | what |
| --- | --- |
| `api.js` | native types (class/enum) + `toCbor`/`fromCbor`, and per message its bounds and `decode` |
| `cbor.js` | the deterministic-CBOR runtime (`Cbor`, `encode`, `decode`, `DecodeError`) |
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

Messages are ES classes with an **instance** `toCbor()`, a static `fromCbor()`, and a
static decode from bytes, `decode()`, under the message's bounds:

```js
class User {
  static get MAX_DEPTH() { return 32; }          // User's effective max_depth
  static get MAX_ENCODED_LEN() { return null; }  // its effective max_encoded_len; null for none
  constructor(o = {}) { this.id = o.id; this.name = o.name; }
  toCbor() { ... }                  // CMap([[1, ..], [2, ..]])
  static fromCbor(c) { ... }        // expectInt(cget(c, 1)), expectText(cget(c, 2))
  static decode(bytes) { ... }      // bytes -> User, under both bounds
}
new User({ id: 1n, name: "ada" });  // construct from a plain object
```

Field mapping: `INT → bigint` (decode reads every int as a `bigint`, exact over the
whole `i64` range; encode also takes a safe-integer `number`), `STR → string`,
`BYTES → Uint8Array`, `BOOL → boolean`, `FLOAT → number`, `List(T) → Array<T>`,
`Map(K,V) → Map<K,V>`. **Optional** fields are nullable (encoded as CBOR `null` when
`null`/`undefined`). **Transient** fields live on the instance but never on the wire.

## 3. Encode / decode

A message ↔ CBOR bytes goes through the generated `toCbor` plus the runtime `encode`,
and back through the generated `decode`:

```js
const { encode } = require("./cbor.js");
const { Task } = require("./api.js");

const bytes = encode(task.toCbor());  // Uint8Array — serialize
const task = Task.decode(bytes);      // deserialize, under Task's bounds
```

`Task.decode(bytes)` applies the message's bounds, the read-only `Task.MAX_DEPTH` (32
unless the schema declares `max_depth`) and `Task.MAX_ENCODED_LEN` (`null` unless it
declares `max_encoded_len`). Input longer than the length bound throws a `DecodeError`
tagged `TooLarge` (`len`, `limit`) before a byte is read; an array or map nested deeper
than the depth bound, `TooDeep` (`limit`). `Task.fromCbor(decode(bytes))` still reads a
message, but under the raw decode's defaults, not the message's bounds.

Every decode entry point returns a value or throws `DecodeError`, nothing else, whatever
the bytes. Its `name` is `"DecodeError"`, its `tag` the tag, and its payload is in the
fields that tag names: `info`, `major`, `key`, `value`, `expected`, `enum`, `len` and
`limit`. The full table of tags and payloads is in [CodecContract.md](CodecContract.md).

## 4. The `Cbor` runtime (`cbor.js`)

A tiny frozen subset of RFC 8949 in core deterministic encoding (definite lengths,
shortest-form ints, ascending map keys, shortest-form floats). Hand-rolled, zero deps.
Integers decode as `bigint`, exact over the whole `i64` range (like the TS codec);
`CInt` also takes a safe-integer `number`. Bytes are `Uint8Array`.

A `Cbor` is a tagged plain object `{ kind, ... }`, built by the exported constructors:

```js
CInt(n)    // { kind, i }      CBytes(b)  // { kind, b }   (Uint8Array)
CText(s)   // { kind, s }      CBool(x)   // { kind, i }
CFloat(x)  // { kind, f }      CArr(a)    // { kind, arr }
CMap(m)    // { kind, map }    (m: array of [intKey, Cbor])   CNull()

encode(c) // -> Uint8Array
decode(data, { maxDepth, maxEncodedLen }) // -> Cbor   (data: Uint8Array; options optional)
```

`decode` knows no schema. It applies depth bound `maxDepth`, `DEFAULT_MAX_DEPTH` (32)
when absent and at most `MAX_DEPTH_CEILING` (128), and no length bound unless
`maxEncodedLen` is given; a top-level array or map has depth 1. A depth below 1 or a
negative length throws `RangeError`, and a bound that is not an integer, `TypeError`.
Malformed input throws only `DecodeError`.

Accessors, each throwing `DecodeError` (`WrongType`) on the wrong kind: `expectInt(c)`,
`expectFloat(c)`, `expectText(c)`, `expectBytes(c)`, `expectBool(c)`, `expectArray(c)`,
`expectMap(c)` and `cmapEntries(c)` (a map's `[key, Cbor]` array); `cget(c, key)` (map
value by int tag, `MissingKey` if absent), `cgetOrNull(c, key)` (a null `Cbor` if
absent); and `isNull(c)`.

## 5. Forward-compatibility (unknown-field preservation)

Generate with `--forward-compat` and each class gains a `wireResidual` field
(`Array<[number, Cbor]>`, defaulting to `[]`). On `fromCbor`, tags the class doesn't
name are captured there; on `toCbor`, they're pushed back and re-emitted **merged with
the known fields in one ascending-tag order** (`encode` sorts map keys) — so a node that
*decodes → edits → re-encodes* a newer message never drops fields it doesn't understand.
A message with no unknowns is byte-identical with or without the flag. Without it,
`fromCbor` accepts unknown fields and drops them; the parity gate runs both builds (`js`
and `js/fc`).

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

They fail closed: for any host bytes each returns or throws `DecodeError`, and a host
that is not a map is `WrongType` (`map`). Not knowing the host's schema, the helpers read
it at the depth ceiling (128) with no length bound, the only bounds every valid host
meets; the host's own reader applies the host's. A below-band `tag` is the caller's
error, a `RangeError` thrown before the host is read. The host app decodes its own
message obliviously — the extension rides in `wireResidual` and survives.

## 7. Consuming the runtime

`cbor.js` / `ext.js` are vendored, dependency-free CommonJS source — drop them next to
`api.js` and `require` them; `api.js` does `require("./cbor.js")`. Node is the only
toolchain. The bytes match every other taut target.

## 8. Changed in v0.10.0

Nothing is removed. What changes:
- `decode` takes `{ maxDepth, maxEncodedLen }`. Input nested deeper than its bound, into
  which v0.9 recursed without limit, is `TooDeep`.
- `DecodeError` gains the tags `TooDeep` and `TooLarge`, with `len` and `limit`; a
  `map<K,V>` field refuses a repeated key, where v0.9 kept the last.
- The extension helpers throw `RangeError` for a below-band tag and `DecodeError`
  (`WrongType`) for a host that is not a map, where v0.9 threw a plain `Error`.
- New: each class's `MAX_DEPTH`, `MAX_ENCODED_LEN` and `decode`; `DEFAULT_MAX_DEPTH`,
  `MAX_DEPTH_CEILING` and `cgetOrNull`.
