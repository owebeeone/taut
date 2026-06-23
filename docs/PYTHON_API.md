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
value = codec.decode(schema, "Task", raw)            # deserialize -> dict
```

`encode_struct` / `decode_struct` are the same step stopping one level short of
bytes (an int-tag-keyed structure), for composing into a larger CBOR document.

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
def dumps(value) -> bytes        # native Python value -> deterministic CBOR bytes
def loads(data: bytes)           # bytes -> native Python value
```

The vocabulary is exactly: int, bytes, text, array, **integer-keyed** map, bool,
null, float — no tags, no indefinite lengths, no big-nums. Non-`int` (or negative)
map keys and out-of-vocabulary types raise. **Consumers use `codec`, not raw
`cbor`** — `cbor` is the substrate the codec sits on; reach for it directly only to
hand-inspect bytes.

## 5. Forward-compatibility (unknown-field preservation)

**Default-on — no flag.** On `decode`, tags the schema doesn't name are captured
under the message dict's `__unknown__` key (a raw `{tag: value}` map); on `encode`,
they are re-emitted **merged with the known fields in one ascending-tag order**. So
a node that *decodes → edits → re-encodes* a newer message never drops fields it
doesn't understand, and a message with no unknowns is byte-identical either way.

(`--forward-compat` only affects *codegen* targets that emit a residual field, e.g.
Rust. The Python runtime codec always preserves — and a schema that declares an
extension still requires `--forward-compat` when generating a typed target,
because extensions ride this residual space.)

## 6. Extensions (side-channels) — `taut.ext`

Attach / read / clear a declared extension on *any* host message's wire bytes,
knowing only the extension's schema (never the host's). Tags live in the band
≥ `2^20` (`BAND_START = 1048576`); a below-band tag raises.

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

The host app decodes its own message obliviously — the extension rides in the
`__unknown__` residual (§5) and survives a decode/re-encode round-trip untouched.

## 7. Consuming the runtime

Python is the **reference impl**: `pip install taut-proto`, then `import taut`. The
codec (`taut.wire.codec`), the CBOR substrate (`taut.wire.cbor`), and the extension
accessors (`taut.ext`) all ship in that package and are driven by the IR — nothing
to vendor. Generated `api.py` is pure data types with no runtime imports; you hand
the schema and a value dict to `codec`. The bytes match every other taut target.
