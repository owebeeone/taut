# taut — Reference

The complete authoring surface (the `taut.ir.dsl` DSL), the delivery-shape
catalog, the wire, validation rules, and the toolchain. See
[GettingStarted.md](GettingStarted.md) for a tutorial and
[Overview.md](Overview.md) for the model.

---

## 1. An IR module

An IR module is a Python file that builds a `SCHEMA` from the declarative DSL.
It is loaded by path (the conventional extension is `*.taut.py`), so it must
define a top-level `SCHEMA: Schema`:

```python
from taut.ir.dsl import (BOOL, INT, STR, BYTES, Enum, F, List, Msg, Params, Ref,
                          method, schema, service)

SCHEMA = schema( ... declarations ... )
```

`load_schema("x.taut.py")` runs it and returns the `Schema`. The DSL is
*declarative only* — helpers compose data; no control flow or logic belongs in an
IR module.

## 2. Scalars and type refs

| DSL | Wire | Native (examples) |
| --- | --- | --- |
| `INT` | CBOR integer | `int` / `number` / `i64` / `long long` |
| `STR` | CBOR text | `str` / `string` / `String` / `string_view` |
| `BYTES` | CBOR byte string | `bytes` / `Uint8Array` / `Vec<u8>` / `string_view` |
| `BOOL` | CBOR bool | `bool` |
| `Ref.Name` | — | reference to a declared enum or message |
| `List(elem)` | CBOR array | list / array / `Vec<T>` / `std::vector<T>` |

`Ref` resolves to either an enum or a message automatically (you don't
distinguish). Attribute refs are preferred for identifier-shaped names:
`Ref.TaskState`, `List(Ref.Task)`, `List(STR)`. The callable form
`Ref("legacy-name")` remains available for names that cannot be expressed as
Python attributes.

## 3. Enums

```python
SCHEMA = schema(
    TaskState=Enum(open=0, doing=1, done=2),
)
```

Members carry **integer wire values**; native bindings use idiomatic names
(`TaskState.open`, `TaskState::Open`, …). The wire is the integer; the name is a
projection. Wire values must be unique.

`Enum("TaskState", open=0, doing=1, done=2)` remains valid for compatibility and
for names that cannot be expressed as Python identifiers.

## 4. Messages and fields

```python
SCHEMA = schema(
    Task=Msg(
        id=F(1, INT),
        title=F(2, STR),
        state=F(3, Ref.TaskState),
        assignee=F(4, STR, optional=True),
        cached_render=F(5, STR, transient=True),
        votes=F(6, INT, merge="counter")),
)
```

The preferred form names enums and messages with `schema(...)` keywords
(`TaskState=Enum(...)`, `Task=Msg(...)`), names each field with a `Msg(...)`
keyword (`title=F(2, STR)`), and uses `Ref.Name` for enum/message references.
This keeps the governed names as Python identifiers while the integer tags stay
explicit.

`F(tag, type, *, optional=False, transient=False, merge=None)`:

- **tag** — a positive integer, unique within the message. On the wire a message
  is a CBOR map keyed by tag; tags are the stable contract (rename a field freely,
  never reuse/renumber a tag).
- **optional** — may be absent; encoded as CBOR `null` when `None`.
- **transient** — present in the *native* type but **never on the wire** (caches,
  indices, handles). The wire is a projection of the tagged, non-transient subset.
- **merge** — marks a CRDT field; see §7.

`Msg(*fields, reserved=(), next_id=None, **named_fields)` declares the message.
When the message is anonymous, `schema(MessageName=Msg(...))` MUST provide the
message name.

**Evolution metadata** (protobuf-style, but first-class and validated):

- **`reserved`** — a list mixing retired **tags** (int) and retired **names**
  (str): `reserved=[6, "priority"]`. When you remove a field, reserve its tag and
  name so they can never be reused (reuse with a different type silently corrupts
  the wire). The validator rejects any field using a reserved tag or name; the
  breaking-change gate treats *un-reserving* as breaking and reserving as
  compatible.
- **`next_id`** — the next tag to allocate. Unlike protobuf (a comment), it's a
  declared, validated invariant: every field tag *and* every reserved tag must be
  `< next_id`. Bump it when you add a field; the validator guarantees `next_id` is
  always a safe fresh tag.

The explicit string forms remain available when a name is not a valid Python
identifier, is a Python keyword, or collides with `Msg(...)` control arguments
such as `reserved` or `next_id`:

```python
SCHEMA = schema(
    Subscribe=Msg(
        F("from", 1, List(Ref.Head), optional=True),
        F("next_id", 2, STR),
        alias=F(3, Ref("legacy-head")),
    ),
)
```

The older all-explicit form is still valid for compatibility:

```python
Msg("Task", F("id", 1, INT), F("title", 2, STR))
```

## 5. Services and methods (web APIs)

```python
service("Tasks",
    method("create", role="in",
           params=Params(title=STR), out=Ref.Task),
    method("tasks.subscribe", role="out", shape="atom",
           out=List(Ref.Task)),
)
```

`method(name, *, role, shape="unary", params=(), out=None)` — the minimal contract
`(name, in, out, shape)`. **`shape` is the sole discriminator** (`unary` is the
degenerate "delivered once" member); `kind`/`output`/`events` are derived from
`shape`+`out`, so they can never disagree:

| arg | meaning |
| --- | --- |
| `role` | semantic verb role (see legend) |
| `shape` | the delivery shape (§6); defaults to `unary` (request→response) |
| `params` | `in` — `Params(name=TypeRef, ...)`; map 1:1 to a handler's args |
| `out` | a bare `TypeRef` (bound to the shape's sole slot) **or** `{slot: TypeRef}` for multi-slot shapes (`swmr`/`crdt`) |

`Params(...)` preserves keyword order and returns the same tuple shape accepted
by `method(...)`. The tuple form remains available for names that cannot be
expressed as Python keywords:

```python
method("tail", role="out", params=[("from", Ref.Head)], out=Ref.Event)
```

`service(name, *methods)` groups them. A schema may declare several services.

**Role legend** (`role=`): `out` produce/consume · `in` write/append · `ctl`
control · `td` teardown · `hdl` handle (create a stable source handle) · `query`
pull query · `dx` diagnostic.

The IR unit is **(source × shape × role-typed verb)**: a source (a terminal, a
file, a doc) is one handle that may expose several flow-typed views (a live
`stream` *and* a durable `log`, say), each a method with its role.

To **implement** a service (handlers + serving), see [Server.md](Server.md).

## 6. Delivery-shape catalog

A method's `shape` selects behavior + sync; its `out` slots must be a subset of
the shape's slots (`events`). The shape set is an **open registry**
(`taut.ir.shapes.SHAPES` + `register_shape`) — since shape is the discriminator,
adding a shape *is* adding a method-kind, so it is deliberately not a sealed enum:

| shape | payload · history · initiation · writers | out slots | intended API |
| --- | --- | --- | --- |
| `unary` | whole · none · pull · single | `value` | request → response (the default) |
| `atom` | whole-state · latest · pull\|push · single | `replace` | get / set / subscribe-replace |
| `log` | whole · append-only · pull\|push · source | `append` | append / read-from-offset / tail |
| `stream` | whole-or-delta · none · push · source | `event` | subscribe (live only) |
| `swmr` | delta · reconstructible · push · single | `snapshot`,`delta`,`reset` | snapshot(+offset) / subscribe-deltas |
| `snapshot_delta` | delta · reconstructible · push · single | `snapshot`,`delta` | snapshot carrying resume offset, then deltas |
| `crdt` | ops · reconstructible · push-bidi · multi-merge | `op`,`sync` | local-apply / merge-remote / sync |

Rules:
- Use a shape by name; you cannot expose raw axis combinations. Extension = adding
  a new *implemented* shape to the registry.
- **SWMR / snapshot_delta invariant:** the snapshot MUST carry the offset the
  delta feed resumes from (`resume_seq`), and readers must apply deltas
  contiguously — no gap, no double-apply. This handoff is corpus-pinned.

## 7. CRDT fields

A CRDT document is a message whose fields declare a `merge` type (tautPlan §10.4
vocabulary):

| merge | meaning | reference merge |
| --- | --- | --- |
| `lww` | last-writer-wins register (any scalar) | max by `(seq, actor)` |
| `counter` | PN counter (int only) | sum of distinct per-`(actor,seq)` deltas |

```python
SCHEMA = schema(
    Board=Msg(
        title=F(1, STR, merge="lww"),
        votes=F(2, INT, merge="counter")),
)
```

The wire carries CRDT from day one via built-in messages `CrdtOp`,
`VersionEntry`, `CrdtState` (representable in every language). The API surface is
the `crdt` shape (`local-apply` / `merge-remote` / `sync`). The **convergence
engine is a pluggable slot** (`taut.crdt.CrdtEngine`): `ReferenceDoc` implements
lww+counter; `text`/sequence/set bind an external engine (Automerge/Yjs) and raise
`EngineNotBound` until bound. See [../dev-docs/TautCrdt.md](../dev-docs/TautCrdt.md).

## 8. The wire

Deterministic **CBOR**, a deliberately tiny frozen subset (`taut.wire.cbor`):
int, bytes, text, array, integer-keyed map, bool, null. Core deterministic
encoding — definite lengths, shortest-form ints, ascending map keys. Messages are
maps keyed by field tag; enums are their integer value; transient fields are
absent. The same bytes are produced by every language (the corpus proves it).

### Forward compatibility (unknown-field preservation, default-on)

A decoder captures tags it doesn't recognize as raw CBOR (under `__unknown__`) and
re-emits them on encode (canonical order). So a node that **decodes → modifies →
re-encodes** a *newer* message doesn't drop the fields it doesn't understand —
critical for proxies and store-and-forward. Nested unknowns are preserved too. A
message with no unknown tags encodes/decodes identically (corpus-safe).

### Extensions (side-channels)

Infrastructure can piggyback metadata (load-balancing, tracing, routing) on any
message without the app's schema knowing. The tag space is partitioned: app field
tags are `< BAND_START` (2^20); extensions sit at/above it.

```python
extension("Decision", tag=0x100001)   # bind a message to a band tag
```
Generic accessors (`taut.ext`) operate on a host message's *wire bytes* knowing
only the extension's schema, never the host's:
```python
raw = ext_set(schema, raw, "Decision", tag, {"backend": "b7", "hops": 1})
d   = ext_get(schema, raw, "Decision", tag)    # -> dict | None
raw = ext_clear(raw, tag)
```
The host decodes/handles/re-encodes obliviously; the extension rides in
`__unknown__` and survives. Almost free given forward-compat. Full design:
[../dev-docs/TautModules.md](../dev-docs/TautModules.md).

## 9. Validation rules

`validate(schema) -> list[str]` (errors; empty == valid); `validate_or_raise`
raises on any error. It enforces:

- every type ref resolves (enum/message exists);
- field tags positive and unique within a message;
- enum wire values unique;
- `merge` ∈ {lww, counter}, on scalar fields only, counter ⇒ int;
- app field tags stay below the extension band (`2^20`); extension tags sit at/
  above it and are unique; an extension's message exists;
- every method has a known `shape` and a non-empty `out` whose slots ⊆ the
  shape's slots (no duplicate slots); `unary` is the default once-delivered shape;
- known `role` and `kind`.

## 10. Toolchain / library API

```python
from taut.ir.load import load_schema, schema_from_json
from taut.ir.validate import validate, validate_or_raise
from taut.ir.export import export_to, schema_json
from taut.wire import codec
from taut.ir import compat
```

| call | does |
| --- | --- |
| `load_schema(path)` | run a `*.taut.py`, return `Schema` |
| `schema_json(schema)` / `export_to(schema, path)` | the neutral IR JSON (dict / file) |
| `schema_from_json(data)` | inverse — load `Schema` from IR JSON (lossless round-trip) |
| `validate(schema)` / `validate_or_raise(schema)` | coherence check |
| `codec.encode(schema, msg, value)` → `bytes` | native dict → CBOR |
| `codec.decode(schema, msg, bytes)` → `dict` | CBOR → native dict |
| `codec.encode_struct` / `decode_struct` | composable int-keyed form (for nesting) |
| `compat.diff(old, new)` / `breaking(...)` / `check_or_raise(...)` | the version diff |

**Breaking-change gate (CLI):**
```sh
python3 -m taut.ir.compat <baseline.ir.json> <new.ir.json>   # exit 1 on breaking
```

**Per-language generators** (`taut.gen.rust`, `taut.gen.cpp`) emit native types
+ codec for compiled targets. They currently write into the `trial/` slices
(`trial/rs/src/generated.rs`, `trial/cpp/generated/{types,corpus}.hpp`); point
them at your own tree to target your API.

**The project's own build** (worked example): `python3 -m taut.corpus.build`
validates the GripLab IR (`taut/ir/griplab.taut.py`), exports
`corpus/griplab.ir.json`, and writes the golden corpus + Rust + C++ artifacts.

## 11. Conformance corpus & gates

- `taut/corpus/griplab.golden.json` — value→exact-bytes vectors. Every language
  reproduces them byte-for-byte (Python/TS/Rust at runtime; C++ via `static_assert`
  at compile time).
- **Regeneration gate** (`taut/src/tests/test_regen.py`): generated files must
  byte-match fresh generator output — hand-edits fail CI.
- **Breaking-change gate** (§10) — governs API evolution.

## 12. Reference implementations

The `trial/` repo (sibling checkout) is the worked end-to-end example: native
types + codec + WebSocket clients and servers in Python, TypeScript, Rust, and a
C++ compile-time oracle, all driven by this IR. See the per-target READMEs and
[../dev-docs/CodeShape.md](../dev-docs/CodeShape.md).
