# taut — Python API

> Using taut-generated **Python** code: native types, the deterministic-CBOR wire,
> forward-compatibility, and side-channel extensions. Authoring an IR is in
> [Reference.md](Reference.md); serving a service is in [Server.md](Server.md).

Python is the **reference implementation, and it is interpreter-style**: the codec
is a runtime that *walks the IR* (`taut.wire.codec`), not emitted source. Generated
Python is therefore only the native `@dataclass` types — there is no per-message
`to_cbor`. The same IR drives the *same bytes* as every other target — the
conformance corpus proves it.

## 1. Generate

```sh
tautc gen <ir> --lang python -o <out>
```

Writes, into `<out>/python/`:

| file | what |
| --- | --- |
| `api.py` | native types — `@dataclass(slots=True)` structs + `Enum`s (no codec) |
| `client.py` / `server.py` | typed stubs over a transport (see [Server.md](Server.md)) |
| `__init__.py` | re-exports `api` so the output is an importable package |

The codec, the CBOR substrate, and the extension accessors are **not generated** —
they live in the installed `taut` package (`taut.wire.codec`, `taut.wire.cbor`,
`taut.ext`) and are driven by the IR at runtime. `--with-runtime` is a no-op for
Python (nothing to vendor); just `pip install taut-proto`. No other third-party deps.

## 2. Native types

Enums are Python `Enum`s; the member is a projection of an integer wire value:

```python
class TaskState(Enum):
    open = 0
    doing = 1
    done = 2
```

Messages are `@dataclass(slots=True)` — no codec methods, because encoding is the
runtime's job (§3), not the type's:

```python
@dataclass(slots=True)
class Task:
    id: int
    title: str
    state: TaskState
    assignee: User | None
    comments: list[Comment]
    labels: dict[str, str]
```

Field mapping: `INT → int`, `STR → str`, `BYTES → bytes`, `BOOL → bool`,
`FLOAT → float`, `List(T) → list[T]`, `Map(K,V) → dict[K,V]`. **Optional** fields
are `T | None` (encoded as CBOR `null` when `None` — always emitted, never omitted).
**Transient** fields are in the dataclass but never on the wire.

## 3. Encode / decode

The codec is IR-driven: it takes the **schema**, the **message name**, and a plain
**value dict keyed by field name** (enums as their member-name string). The
dataclass is a thin adapter over that dict — the wire contract is the dict.

```python
from taut.wire import codec

value = {
    "id": 1, "title": "ship it", "state": "doing",
    "assignee": None, "comments": [], "labels": {"area": "wire"},
}

raw: bytes = codec.encode(schema, "Task", value)   # serialize
value = codec.decode(schema, "Task", raw)            # deserialize -> dict, under Task's bounds
```

`codec.decode` is the typed decode from bytes. It applies the message's bounds, the
schema's `max_depth` and `max_encoded_len` options as they resolve for it: the message's
own, else the file's, else the defaults, depth 32 and no length bound. Python reads them
from the schema, so there are no generated constants: `codec.bounds(schema,
MsgRef("Task"))` (`MsgRef` from `taut.ir.model`) is the pair, `(32, None)` here. The
call's root decides its bounds: a message nested inside a `Task` does not change them.
`codec.decode_ref(schema, tref, raw)` decodes a root that is not a message, such as a
method's `list<Task>` output, under the file's bounds. Declare bounds in the schema, at
file or message level, with `option` from `taut.ir.dsl`:
`schema(option.max_depth(16), Tree=Msg(option.max_encoded_len(4096), ...))`.

Decode is fail-closed: bad input raises `DecodeError`, and nothing else escapes,
whatever the bytes. `DecodeError` is a `ValueError` whose `.tag` is the tag and whose
payload is in attributes and in the dict `.payload`:

```python
from taut.wire.cbor import DecodeError   # also codec.DecodeError

try:
    value = codec.decode(schema, "Task", raw)
except DecodeError as e:
    print(e.tag, e.payload)              # e.g. TooDeep {'limit': 32}
```

An absent field is `MissingKey`, an optional one too, unless it is `optional=MISSING_OK`,
which reads it as `None`. The full table of tags and payloads is in
[CodecContract.md](CodecContract.md).

`encode_struct` / `decode_struct` are the same step stopping one level short of
bytes (an int-tag-keyed structure), for composing into a larger CBOR document.
`decode_struct` reads a tree its caller decoded, so it applies no bounds, and it reads
an absent field as `None` unless it is passed `strict=True`.

To go through the generated `@dataclass`, bind it yourself — `dataclasses.asdict`
out, the constructor in (enum members become their `.name` on the wire side):

```python
import dataclasses
raw  = codec.encode(schema, "Task", dataclasses.asdict(task))
task = Task(**codec.decode(schema, "Task", raw))
```

## 4. The Cbor runtime (`taut.wire.cbor`)

A tiny frozen subset of RFC 8949 in core deterministic encoding (definite lengths,
shortest-form int arguments, ascending integer map keys, shortest-form floats —
NaN canonical to `F9 7E00`, `-0.0` preserved). Hand-rolled, zero deps, pinned by
the RFC vectors in the tests.

```python
DEFAULT_MAX_DEPTH = 32           # the depth bound where none is given
MAX_DEPTH_CEILING = 128          # no decode applies a deeper bound

def dumps(value) -> bytes        # native Python value -> deterministic CBOR bytes
def loads(data: bytes, *, max_depth: int = 32, max_encoded_len: int | None = None)
                                 # bytes -> native Python value
```

The vocabulary is exactly: int, bytes, text, array, **integer-keyed** map, bool,
null, float — no tags, no indefinite lengths, no big-nums. Non-`int` (or negative)
map keys and out-of-vocabulary types raise. **Consumers use `codec`, not raw
`cbor`** — `cbor` is the substrate the codec sits on; reach for it directly only to
hand-inspect bytes.

`loads` is the raw decode and knows no schema: it applies depth 32 and no length bound
unless its caller passes bounds. An array or map has depth one more than the arrays and
maps around it, so a top-level one has depth 1; one deeper than `max_depth` is `TooDeep`
(`limit`), refused once its head is read. A `max_depth` above the ceiling applies the
ceiling, and `limit` names the bound applied; with `max_encoded_len`, longer input is
`TooLarge` (`len`, `limit`) before a byte is read. A `max_depth` below 1 or a negative
`max_encoded_len` is the caller's error, a plain `ValueError` (or `TypeError` for a
non-int), not a `DecodeError`.

## 5. Forward-compatibility (unknown-field preservation)

**Default-on — no flag.** On `decode`, tags the schema doesn't name are captured
under the message dict's `__unknown__` key (a raw `{tag: value}` map); on `encode`,
they are re-emitted **merged with the known fields in one ascending-tag order**. So
a node that *decodes → edits → re-encodes* a newer message never drops fields it
doesn't understand, and a message with no unknowns is byte-identical either way.

(`--forward-compat` only affects *codegen* targets that emit a residual field — the
seven generated targets, Rust to Java. The Python runtime codec always preserves — and
a schema that declares an extension still requires `--forward-compat` when generating
a typed target, because extensions ride this residual space.)

## 6. Extensions (side-channels) — `taut.ext`

Attach / read / clear a declared extension on *any* host message's wire bytes,
knowing only the extension's schema (never the host's). Tags live in the band
≥ `2^20` (`BAND_START = 1048576`).

```python
from taut import ext

def ext_set(schema, message_bytes: bytes, ext_message: str, tag: int, value: dict) -> bytes
def ext_get(schema, message_bytes: bytes, ext_message: str, tag: int) -> dict | None
def ext_clear(message_bytes: bytes, tag: int) -> bytes
```

`value` / the return are the *native value dict* for `ext_message` (the same shape
`codec` takes — `ext` encodes/decodes it for you). Worked example, strapping a
`Decision` onto an opaque host:

```python
TAG = 0x100001   # 1048577, in-band

raw      = ext.ext_set(schema, host_bytes, "Decision", TAG, {"approved": True})
decision = ext.ext_get(schema, raw, "Decision", TAG)   # {"approved": True}  (None if absent)
raw      = ext.ext_clear(raw, TAG)                       # strip before delivery
```

They fail closed: for any host bytes each returns or raises `DecodeError`, and a host
that is not a map is `WrongType` (`map`). Not knowing the host's schema, they read a
host at the depth ceiling, 128, with no length bound, the only bounds every valid host
meets; the host's own reader applies the host's. `ext_get` reads the extension as
strictly as `codec.decode` reads a message. A below-band `tag` is the caller's error, a
plain `ValueError`, raised before the host is read. The host app decodes its own message
obliviously — the extension rides in the `__unknown__` residual (§5) and survives a
decode/re-encode round-trip untouched.

## 7. Consuming the runtime

Python is the **reference impl**: `pip install taut-proto`, then `import taut`. The
codec (`taut.wire.codec`), the CBOR substrate (`taut.wire.cbor`), and the extension
accessors (`taut.ext`) all ship in that package and are driven by the IR — nothing
to vendor. Generated `api.py` is pure data types with no runtime imports; you hand
the schema and a value dict to `codec`. The bytes match every other taut target.

## 8. Changed in v0.10.0

- `cbor.loads` takes `max_depth` and `max_encoded_len`, and `codec.decode` applies the
  message's. Input nested deeper than its bound, which v0.9 decoded until a
  `RecursionError` escaped, is `TooDeep`.
- `DecodeError` gains the tags `TooDeep` (`limit`) and `TooLarge` (`len`, `limit`). A
  repeated key of a `map<bool,V>` field is reported as `true` or `false`.
- `codec.decode` refuses an absent optional field as `MissingKey` unless it is
  `optional=MISSING_OK`; v0.9 read it as `None`.
- The extension helpers raise `DecodeError` for a host that is not a map, where v0.9
  leaked `TypeError` or `ValueError`, and `ext_get` reads the extension strictly.
- New: `codec.decode_ref`, `codec.bounds`, the `option` namespace in the DSL, and IR
  version 2, which `export_to` writes (options and their effective values) and the
  loader reads beside version 1.
