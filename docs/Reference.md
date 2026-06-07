# Prism — Reference

The complete authoring surface (the `prism.ir.dsl` DSL), the delivery-shape
catalog, the wire, validation rules, and the toolchain. See
[GettingStarted.md](GettingStarted.md) for a tutorial and
[Overview.md](Overview.md) for the model.

---

## 1. An IR module

An IR module is a Python file that builds a `SCHEMA` from the declarative DSL.
It is loaded by path (the conventional extension is `*.prism.py`), so it must
define a top-level `SCHEMA: Schema`:

```python
from prism.ir.dsl import (BOOL, INT, STR, BYTES, Enum, F, List, Msg, Ref,
                          method, schema, service)

SCHEMA = schema( ... declarations ... )
```

`load_schema("x.prism.py")` runs it and returns the `Schema`. The DSL is
*declarative only* — helpers compose data; no control flow or logic belongs in an
IR module.

## 2. Scalars and type refs

| DSL | Wire | Native (examples) |
| --- | --- | --- |
| `INT` | CBOR integer | `int` / `number` / `i64` / `long long` |
| `STR` | CBOR text | `str` / `string` / `String` / `string_view` |
| `BYTES` | CBOR byte string | `bytes` / `Uint8Array` / `Vec<u8>` / `string_view` |
| `BOOL` | CBOR bool | `bool` |
| `Ref("Name")` | — | reference to a declared enum or message |
| `List(elem)` | CBOR array | list / array / `Vec<T>` / `std::vector<T>` |

`Ref` resolves to either an enum or a message automatically (you don't
distinguish). `List` nests: `List(Ref("Task"))`, `List(STR)`.

## 3. Enums

```python
Enum("TaskState", open=0, doing=1, done=2)
```

Members carry **integer wire values**; native bindings use idiomatic names
(`TaskState.open`, `TaskState::Open`, …). The wire is the integer; the name is a
projection. Wire values must be unique.

## 4. Messages and fields

```python
Msg("Task",
    F("id", 1, INT),
    F("title", 2, STR),
    F("state", 3, Ref("TaskState")),
    F("assignee", 4, STR, optional=True),
    F("cached_render", 5, STR, transient=True),
    F("votes", 6, INT, merge="counter"))
```

`F(name, tag, type, *, optional=False, transient=False, merge=None)`:

- **tag** — a positive integer, unique within the message. On the wire a message
  is a CBOR map keyed by tag; tags are the stable contract (rename a field freely,
  never reuse/renumber a tag).
- **optional** — may be absent; encoded as CBOR `null` when `None`.
- **transient** — present in the *native* type but **never on the wire** (caches,
  indices, handles). The wire is a projection of the tagged, non-transient subset.
- **merge** — marks a CRDT field; see §7.

`Msg(name, *fields, reserved=(), next_id=None)` declares the message.

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

## 5. Services and methods (web APIs)

```python
service("Tasks",
    method("create", kind="unary", role="in",
           params=[("title", STR)], output=Ref("Task")),
    method("tasks.subscribe", kind="server_stream", role="out", shape="atom",
           events={"replace": List(Ref("Task"))}),
)
```

`method(name, *, kind, role, params=(), output=None, shape=None, events=None)`:

| arg | meaning |
| --- | --- |
| `kind` | `"unary"` (request→response) or `"server_stream"` (subscription) |
| `role` | semantic verb role (see legend) |
| `params` | ordered `[(name, TypeRef), …]` — the inputs; map 1:1 to a handler's args |
| `output` | the response `TypeRef` — **unary only** |
| `shape` | the delivery shape (§6) — **server_stream only** |
| `events` | `{event_name: TypeRef}` for the stream — **server_stream only** |

`service(name, *methods)` groups them. A schema may declare several services.

**Role legend** (`role=`): `out` produce/consume · `in` write/append · `ctl`
control · `td` teardown · `hdl` handle (create a stable source handle) · `query`
pull query · `dx` diagnostic.

The IR unit is **(source × shape × role-typed verb)**: a source (a terminal, a
file, a doc) is one handle that may expose several flow-typed views (a live
`stream` *and* a durable `log`, say), each a method with its role.

To **implement** a service (handlers + serving), see [Server.md](Server.md).

## 6. Delivery-shape catalog

A streaming method's `shape` selects behavior + sync; its `events` must be a
subset of the shape's allowed events (the derived streaming-kind). The closed set
(`prism.ir.shapes.SHAPES`):

| shape | payload · history · initiation · writers | allowed events | intended API |
| --- | --- | --- | --- |
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

A CRDT document is a message whose fields declare a `merge` type (PrismPlan §10.4
vocabulary):

| merge | meaning | reference merge |
| --- | --- | --- |
| `lww` | last-writer-wins register (any scalar) | max by `(seq, actor)` |
| `counter` | PN counter (int only) | sum of distinct per-`(actor,seq)` deltas |

```python
Msg("Board",
    F("title", 1, STR, merge="lww"),
    F("votes", 2, INT, merge="counter"))
```

The wire carries CRDT from day one via built-in messages `CrdtOp`,
`VersionEntry`, `CrdtState` (representable in every language). The API surface is
the `crdt` shape (`local-apply` / `merge-remote` / `sync`). The **convergence
engine is a pluggable slot** (`prism.crdt.CrdtEngine`): `ReferenceDoc` implements
lww+counter; `text`/sequence/set bind an external engine (Automerge/Yjs) and raise
`EngineNotBound` until bound. See [../dev-docs/PrismCrdt.md](../dev-docs/PrismCrdt.md).

## 8. The wire

Deterministic **CBOR**, a deliberately tiny frozen subset (`prism.wire.cbor`):
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
Generic accessors (`prism.ext`) operate on a host message's *wire bytes* knowing
only the extension's schema, never the host's:
```python
raw = ext_set(schema, raw, "Decision", tag, {"backend": "b7", "hops": 1})
d   = ext_get(schema, raw, "Decision", tag)    # -> dict | None
raw = ext_clear(raw, tag)
```
The host decodes/handles/re-encodes obliviously; the extension rides in
`__unknown__` and survives. Almost free given forward-compat. Full design:
[../dev-docs/PrismModules.md](../dev-docs/PrismModules.md).

## 9. Validation rules

`validate(schema) -> list[str]` (errors; empty == valid); `validate_or_raise`
raises on any error. It enforces:

- every type ref resolves (enum/message exists);
- field tags positive and unique within a message;
- enum wire values unique;
- `merge` ∈ {lww, counter}, on scalar fields only, counter ⇒ int;
- app field tags stay below the extension band (`2^20`); extension tags sit at/
  above it and are unique; an extension's message exists;
- unary methods have an `output` and no `shape`/`events`;
- server_stream methods have a known `shape`, non-empty `events` ⊆ the shape's
  allowed events, and no `output`;
- known `role` and `kind`.

## 10. Toolchain / library API

```python
from prism.ir.load import load_schema, schema_from_json
from prism.ir.validate import validate, validate_or_raise
from prism.ir.export import export_to, schema_json
from prism.wire import codec
from prism.ir import compat
```

| call | does |
| --- | --- |
| `load_schema(path)` | run a `*.prism.py`, return `Schema` |
| `schema_json(schema)` / `export_to(schema, path)` | the neutral IR JSON (dict / file) |
| `schema_from_json(data)` | inverse — load `Schema` from IR JSON (lossless round-trip) |
| `validate(schema)` / `validate_or_raise(schema)` | coherence check |
| `codec.encode(schema, msg, value)` → `bytes` | native dict → CBOR |
| `codec.decode(schema, msg, bytes)` → `dict` | CBOR → native dict |
| `codec.encode_struct` / `decode_struct` | composable int-keyed form (for nesting) |
| `compat.diff(old, new)` / `breaking(...)` / `check_or_raise(...)` | the version diff |

**Breaking-change gate (CLI):**
```sh
python3 -m prism.ir.compat <baseline.ir.json> <new.ir.json>   # exit 1 on breaking
```

**Per-language generators** (`prism.gen.rust`, `prism.gen.cpp`) emit native types
+ codec for compiled targets. They currently write into the `trial/` slices
(`trial/rs/src/generated.rs`, `trial/cpp/generated/{types,corpus}.hpp`); point
them at your own tree to target your API.

**The project's own build** (worked example): `python3 -m prism.corpus.build`
validates the GripLab IR (`prism/ir/griplab.prism.py`), exports
`corpus/griplab.ir.json`, and writes the golden corpus + Rust + C++ artifacts.

## 11. Conformance corpus & gates

- `prism/corpus/griplab.golden.json` — value→exact-bytes vectors. Every language
  reproduces them byte-for-byte (Python/TS/Rust at runtime; C++ via `static_assert`
  at compile time).
- **Regeneration gate** (`prism/src/tests/test_regen.py`): generated files must
  byte-match fresh generator output — hand-edits fail CI.
- **Breaking-change gate** (§10) — governs API evolution.

## 12. Reference implementations

The `trial/` repo (sibling checkout) is the worked end-to-end example: native
types + codec + WebSocket clients and servers in Python, TypeScript, Rust, and a
C++ compile-time oracle, all driven by this IR. See the per-target READMEs and
[../dev-docs/CodeShape.md](../dev-docs/CodeShape.md).
