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
- **optional** — `False` (the default), `True` or `MISSING_OK`, from `taut.ir.dsl`. With `True` the
  field may be `None` in the native type. On the wire it is still always written, as CBOR `null` when
  `None`, and a decoder refuses a message whose key for the field is missing (`MissingKey`), as for a
  required field. `MISSING_OK` also reads a missing key as `None`, so a new reader accepts messages
  written before the field existed; the encoder still writes the key. Every target language
  supports `MISSING_OK`. See §8, *Missing versus null*.
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

### Options

An option is a typed property declared with the schema, as in protobuf (D27, TautOptions.md). It is
written as a positional value, `option.<name>(value)`, at file level (in `schema(...)`), at message
level (in `Msg(...)`), at field level (after `F`'s type) or at enum level (in `Enum(...)`). Enum
value, service and method levels are reserved:

```python
from taut.ir.dsl import option

SCHEMA = schema(
    option.max_depth(16),                            # file level
    Tree=Msg(option.max_depth(64),                   # message level, overrides the file's
             kids=F(1, List(Ref.Tree))),
)
```

- **One definition per option:** its value type, the levels it may sit at, its default, how it
  inherits, and its class: *wire* (changes what decodes), *codegen*, *metadata* or *semantic*.
- **An unknown name fails:** at import (`option.max_dept` raises), in IR JSON at load, and in
  `validate`. `option("ns.name", v)` is reserved for custom options.
- **Effective values** resolve from the element out: a message's own value, else the file's, else
  the default (`taut.ir.options.effective`). A message used inside another inherits nothing from it.
- **The first two options** are both wire options, at file and message level:
  - `max_depth`: default 32, 1 to 128.
  - `max_encoded_len`: no default, 1 to 2^31 − 1.

  They bound a decode call (§8).
- **Compatibility:** changing a wire option's effective value at any root is breaking, in both
  directions (§10's gate).
- **The IR** (version 2) carries each level's declared `options`, and the resolved `effective`
  values at file and message level. The loader recomputes `effective` and refuses a stale one.

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
the shape's slots (`events`). Schema authors select an active name from the
validated canonical registry (`taut.ir.shapes.SHAPES`). Compiler extensions can
register a complete `ShapeSpec` only with an implementation-capability identity;
runtime adapters still gate their own exact support.

| shape | class / core | out slots | normalized intent |
| --- | --- | --- | --- |
| `unary` | interaction / — | `value` | one request → one response (default) |
| `value` | engine / value | `value` | attributed multi-writer LWW; portable v0 operations are immediate read/set, not watch |
| `atom` | engine / atom | `replace` | single-writer latest mailbox with versioned replacement |
| `log` | engine / log | `append` | retained scalar-cursor records with explicit expiry |
| `stream` | engine / stream | `event` | live-only delivery; overflow policy still unbound |
| `swmr` | engine / swmr | `snapshot`,`delta`,`reset` | one bound writer; snapshot + deltas + in-band reset/repair |
| `snapshot_delta` | profile / swmr | `snapshot`,`delta` | SWMR core with fixed expiry/out-of-band recovery |
| `crdt` | engine / crdt | `op`,`sync` | attributed replica ops, causal position, anti-entropy |

Rules:
- Use an active shape by name; raw axis combinations and arbitrary strings are
  rejected. Registry recognition does not imply a target runtime capability.
- Unknown names fail closed. `message`, `exchange`, and `window` are not Taut
  delivery shapes; `text_crdt` is reserved but inactive.
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

### Missing versus null

An unset optional field is written as CBOR `null`; its key is never left out. A decoder therefore
reads a present `null` as `None`, and refuses a missing key with `MissingKey`, for optional and
required fields alike. The one exception is opt-in: a field declared `optional=MISSING_OK` also
reads a missing key as `None`. In the exported IR its `optional` is the string `"missing_ok"`.
(Its earlier spelling, `optional=True, missing_ok=True`, and the IR key `missing_ok` are no longer
accepted; re-export a schema that used them.)

Why it settled here. The fail-closed codec, the default since v0.8.0, accepts exactly the bytes the
canonical encoder could emit: `decode(bytes)` succeeds only if `encode(decode(bytes)) == bytes`
(decision D2 of [the codec parity plan](../dev-docs/TautCodecParityPlan.md), ratified 2026-07-07).
No conforming writer omits a field's key, and accepting a message without it would re-encode to
different bytes. This replaced an earlier, lenient model
([TautModules.md §2](../dev-docs/TautModules.md)) in which a missing field, even a required one,
decoded to null. Every language follows the rule, and the parity corpus pins it (Python's
`decode_struct`, which reads a decoded tree, is lenient unless called with `strict=True`).

What it means for evolving a schema: after an optional field is added, an old reader still reads new
messages (it keeps the new tag as an unknown field, below), but a new reader refuses a message written
before the field existed. Adding the field with `optional=MISSING_OK` avoids that: a new reader reads
the field of such a message as `None`. For that field the round trip deliberately changes bytes,
since re-encoding the message writes the key, as `null`. The breaking-change gate treats presence as
a ladder, `False` to `True` to `MISSING_OK`: a move up is compatible and a move down breaking, and
it treats adding a field as compatible only at `MISSING_OK`.
Without `MISSING_OK`, upgrade writers before readers, and re-encode stored messages before a new
reader reads them.

### Decode: one error, fail-closed, bounded

Every decode entry point, in every language, returns a value or a `DecodeError` (in the language's
idiom). It never panics, aborts, overflows its stack or throws anything else. The nine languages
give the same tag and payload for the same bytes, in one order of checks; the tags, payloads and
order are in [CodecContract.md](CodecContract.md). Decoding is strict-canonical: it accepts only
what the canonical encoder could write.

A decode call is bounded by its **root**, the message it is asked to decode:
- **Depth.** The root's effective `max_depth` (default 32, never above 128). A top-level array or
  map has depth 1; one level deeper than the bound is `TooDeep{limit}`.
- **Length.** The root's effective `max_encoded_len`, if one is declared. Longer input is
  `TooLarge{len, limit}`, before any byte is read.
- **Typed decode** (Python's `codec.decode`, TypeScript's `decode`, each generated message's
  `decode`) applies the root's bounds and takes no bounds argument, so every reader of a root
  agrees.
- **Raw decode** knows no schema. It applies depth 32 and no length bound unless the caller passes
  bounds, with the depth capped at 128. Python's form is `cbor.loads(data, *, max_depth=32,
  max_encoded_len=None)`.
- **Extension helpers** read a host at the ceiling, 128, with no length bound. A host that is not a
  map is `WrongType{map}`.

A message nested inside another does not change the bounds of a call in progress.

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
- known `role` and `kind`;
- every declared option is registered, sits at a level its definition allows, and holds a value of
  its type and range;
- at every root (each message, and each method's param and out slot types), `max_depth` is at
  least the root's non-recursive nesting and at most 128, and a declared `max_encoded_len` is at
  least the root's smallest encoding;
- no field, message or enum takes a name that some target's generated code or runtime already
  declares where the name would go, such as C++'s member `to_cbor`, Java's `MAX_DEPTH` or a
  message `Cbor`. The error names each target the name breaks and why. Each generator keeps its
  own list (`RESERVED_FIELD_NAMES`, `RESERVED_TYPE_NAMES`, `name_clashes`), and validate refuses
  their union, so a schema that validates generates in all nine targets. Language keywords are
  not covered: some generators escape them, and a keyword a generator does not escape still fails
  there, such as a Python field `from`.

`lint(schema) -> list[str]` returns warnings that never fail a build, which `tautc` prints:
- a recursive message that declares no `max_depth`;
- a message whose declared bound cannot take effect inside another message that embeds it.

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
| `codec.decode(schema, msg, bytes)` → `dict` | CBOR → native dict, bounded by `msg`'s effective options |
| `cbor.loads(data, *, max_depth=32, max_encoded_len=None)` | raw CBOR decode, no schema |
| `options.effective(schema, name, message=...)` | an option's effective value |
| `codec.encode_struct` / `decode_struct` | composable int-keyed form (for nesting) |
| `compat.diff(old, new)` / `breaking(...)` / `check_or_raise(...)` | the version diff |

**Breaking-change gate (CLI):**
```sh
python3 -m taut.ir.compat <baseline.ir.json> <new.ir.json>   # exit 1 on breaking
```

**Per-language generators** emit native types and vendored runtimes where needed.
The TypeScript generic runtime lives in `src/taut/gen/runtime/typescript/` and is
emitted by `tautc gen --lang typescript --with-runtime`; Rust/C++ can still be
pointed at whatever generated-output tree the caller chooses.

**`tautc`** runs `validate` and prints `lint`'s warnings before it generates or exports.
`--legacy-codec` is gone: every generated codec is fail-closed, and `--fail-closed` is accepted as
a no-op.

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
- **Parity gate** (`tautc parity`): replays `corpus/parity/{int,malformed,bounds}.vectors.json`
  through all nine codecs, and through the seven generated ones built with forward-compat
  (`<target>/fc`). It compares tag and payload and checks each accepted row's re-encoding. A target
  may fail only while `corpus/parity/allowlist.json` lists it with a reason. A target whose
  toolchain is missing is skipped, with the reason; `--require-all` fails the gate instead, as a
  release does (`RELEASE.md`). The contract is `taut-codec-parity/i64/v1`; see
  [CodecContract.md](CodecContract.md).

## 12. Reference implementations

TypeScript's reusable runtime source is in this repo under
`src/taut/gen/runtime/typescript/` and can be vendored into generated outputs
with `--with-runtime`. Other targets can be emitted into caller-owned generated
output trees and validated against the same corpus.
