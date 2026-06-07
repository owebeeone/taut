# taut — Getting Started

We'll define a small web API — a shared **task board** — from scratch: composed
data shapes, a service with unary calls and two streaming endpoints (an Atom list
and a Log feed), then validate it, export the neutral IR, and encode a value.

Prerequisite: the `taut` package importable (the repo's `taut/src` on
`PYTHONPATH`, or run from there). Python ≥ 3.10.

> **Runnable version:** everything below is a working example at
> [`examples/tasks/`](examples/tasks/) — `cd docs/examples/tasks && python3 run.py`.

## 1. Author the API (`tasks.taut.py`)

The IR is authored in a restricted, declarative Python DSL — no logic, just
declarations:

```python
from taut.ir.dsl import BOOL, INT, STR, Enum, F, List, Msg, Ref, method, schema, service

SCHEMA = schema(
    # an enum — integer wire values, idiomatic native names per language
    Enum("TaskState", open=0, doing=1, done=2),

    # messages compose: a field can reference another message, an optional
    # message, or a list of messages — nesting is automatic on the wire.
    Msg("User",
        F("id", 1, INT),
        F("name", 2, STR)),

    Msg("Comment",
        F("author", 1, Ref("User")),          # a message field — composition
        F("text", 2, STR)),

    Msg("Task",
        F("id", 1, INT),
        F("title", 2, STR),
        F("state", 3, Ref("TaskState")),       # enum field
        F("assignee", 4, Ref("User"), optional=True),  # nested message, optional
        F("comments", 5, List(Ref("Comment")))),       # list of messages

    Msg("Event",
        F("ts", 1, INT),
        F("text", 2, STR)),

    # the web API: a service of methods. Each method is (name, in, out, shape);
    # `shape` is the sole discriminator and defaults to `unary` (delivered once).
    service("Tasks",
        # unary (default shape): request -> response. params can be messages.
        method("create", role="in",
               params=[("title", STR)], out=Ref("Task")),
        method("comment", role="in",
               params=[("task_id", INT), ("author", Ref("User")), ("text", STR)],
               out=Ref("Comment")),
        method("set_state", role="ctl",
               params=[("id", INT), ("state", Ref("TaskState"))], out=BOOL),

        # Atom: the whole task list, latest-wins, pushed on every change
        method("tasks.subscribe", role="out", shape="atom",
               out=List(Ref("Task"))),

        # Log: an append-only activity feed (replay then tail)
        method("activity.subscribe", role="out", shape="log",
               out=Ref("Event")),
    ),
)
```

That file *is* the governed artifact — four messages (composed: `Task` embeds an
optional `User` and a list of `Comment`, each `Comment` embeds a `User`), one
enum, and a service of three unary calls and two streaming endpoints, read whole
in a screen. (`out=` is a bare type for single-slot shapes — bound to the shape's
slot; multi-slot shapes like `swmr` take `out={"snapshot": …, "delta": …}`.)

## 2. Load, validate, export

```python
from taut.ir.load import load_schema
from taut.ir.validate import validate_or_raise
from taut.ir.export import export_to
from taut.wire import codec

schema = load_schema("tasks.taut.py")     # run the DSL, get a Schema
validate_or_raise(schema)                  # reject incoherent IR (see below)
export_to(schema, "tasks.ir.json")         # the neutral artifact every language reads
```

The validator enforces coherence: refs resolve, tags are unique, and a method's
`out` slots must be allowed for its shape (an `atom` binding a `delta` slot is
rejected — try it and see the error).

## 3. Encode / decode a value

The codec is driven by the IR. A "value" is a plain dict keyed by field name
(enums as their member-name string); **composed messages just nest** — embedded
messages are dicts, lists of messages are lists of dicts:

```python
task = {
    "id": 1, "title": "ship taut", "state": "doing",
    "assignee": {"id": 7, "name": "ann"},                 # nested message
    "comments": [                                          # list of messages
        {"author": {"id": 7, "name": "ann"}, "text": "started"},
        {"author": {"id": 9, "name": "bo"},  "text": "lgtm"},
    ],
}
blob = codec.encode(schema, "Task", task)      # deterministic CBOR bytes
assert codec.decode(schema, "Task", blob) == task

# an optional nested message that's absent decodes as None
later = {"id": 2, "title": "later", "state": "open", "assignee": None, "comments": []}
assert codec.decode(schema, "Task", codec.encode(schema, "Task", later)) == later
```

The codec recurses through the composition automatically; the bytes are the same
in every language — that's what the golden corpus pins.

## 4. Talk to it across languages

The contract is enough to generate/derive the rest:

- **TypeScript / Rust / C++** get native types + a codec from the same
  `tasks.ir.json`. The compiled targets generate structs; the runtime targets
  read the IR JSON directly. See [`examples/tasks/generated/`](examples/tasks/generated/)
  for the **api / client / server** emitted for *this* API in all four languages
  — generated by `tautc gen tasks.taut.py -o generated/` (the codegen CLI; add
  `--api-only` for just struct defs + encoders/decoders, drop-in for build scripts).
- **Clients are generic** — one ~100-line client per language exposes
  `call(method, args)` and `subscribe(method, args)`; there is **no per-method
  code**. Adding a method to the IR needs no client change.
- **Servers** dispatch by reading the IR: a method's `shape` decides
  request-vs-stream (`unary` = once), and the handler is a plain function over
  native types.

**[Server.md](Server.md)** walks through building a server for this exact Tasks
API: write handlers (plain functions), back the streaming endpoints with shape
engines, register them against the IR, and serve. See `trial/ts/src/client.ts`,
`trial/rs/src/client.rs`, `trial/py/griplab_slice/ws_client.py` for the client
shape, and `trial/py/griplab_slice/server.py` / `trial/rs/src/server.rs` for the
runnable reference servers.

## 5. Evolve it safely

When you change the API, the breaking-change gate diffs the new IR against the
prior version and rejects incompatible edits under the same major:

```sh
python3 -m taut.ir.compat tasks.ir.json.prev tasks.ir.json
# [compatible] Task.due (tag 5) added        → exit 0
# [breaking]  Task.title wire-type changed    → exit 1
```

Adding a message / enum / method / **optional** field / stream event is
compatible; removing or renaming fields, changing tags or wire-types, or
tightening optional→required is breaking.

When you *do* remove a field, **reserve** its tag and name so they can never be
reused, and keep **`next_id`** ahead of every tag — both are first-class,
validated message features (the example uses them on `Task`):

```python
Msg("Task",
    F("id", 1, INT), F("title", 2, STR), F("state", 3, Ref("TaskState")),
    F("assignee", 4, Ref("User"), optional=True), F("comments", 5, List(Ref("Comment"))),
    reserved=[6, "priority"],   # retired tag 6 + name "priority" — never reusable
    next_id=7)                  # next tag to allocate (validated > every used/reserved tag)
```

See [Reference.md](Reference.md) §4 for the rules.

## Where to go next

- [Server.md](Server.md) — build a server for this API: handlers, shape engines,
  registration from the IR, serving.
- [Reference.md](Reference.md) — every DSL primitive, the delivery-shape catalog,
  CRDT fields, and the toolchain.
- [Overview.md](Overview.md) — the model and what taut decouples.
