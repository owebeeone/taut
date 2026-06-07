# Prism — Getting Started

We'll define a small web API — a shared **task board** — from scratch: composed
data shapes, a service with unary calls and two streaming endpoints (an Atom list
and a Log feed), then validate it, export the neutral IR, and encode a value.

Prerequisite: the `prism` package importable (the repo's `prism/src` on
`PYTHONPATH`, or run from there). Python ≥ 3.10.

> **Runnable version:** everything below is a working example at
> [`examples/tasks/`](examples/tasks/) — `cd docs/examples/tasks && python3 run.py`.

## 1. Author the API (`tasks.prism.py`)

The IR is authored in a restricted, declarative Python DSL — no logic, just
declarations:

```python
from prism.ir.dsl import BOOL, INT, STR, Enum, F, List, Msg, Ref, method, schema, service

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

    # the web API: a service of methods
    service("Tasks",
        # unary: request -> response. params can themselves be messages.
        method("create", kind="unary", role="in",
               params=[("title", STR)], output=Ref("Task")),
        method("comment", kind="unary", role="in",
               params=[("task_id", INT), ("author", Ref("User")), ("text", STR)],
               output=Ref("Comment")),
        method("set_state", kind="unary", role="ctl",
               params=[("id", INT), ("state", Ref("TaskState"))], output=BOOL),

        # Atom: the whole task list, latest-wins, pushed on every change
        method("tasks.subscribe", kind="server_stream", role="out", shape="atom",
               events={"replace": List(Ref("Task"))}),

        # Log: an append-only activity feed (replay then tail)
        method("activity.subscribe", kind="server_stream", role="out", shape="log",
               events={"append": Ref("Event")}),
    ),
)
```

That file *is* the governed artifact — four messages (composed: `Task` embeds an
optional `User` and a list of `Comment`, each `Comment` embeds a `User`), one
enum, and a service of three unary calls and two streaming endpoints, read whole
in a screen.

## 2. Load, validate, export

```python
from prism.ir.load import load_schema
from prism.ir.validate import validate_or_raise
from prism.ir.export import export_to
from prism.wire import codec

schema = load_schema("tasks.prism.py")     # run the DSL, get a Schema
validate_or_raise(schema)                  # reject incoherent IR (see below)
export_to(schema, "tasks.ir.json")         # the neutral artifact every language reads
```

The validator enforces coherence: refs resolve, tags are unique, and a
streaming method's `events` must be allowed for its shape (an `atom` emitting a
`delta` is rejected — try it and see the error).

## 3. Encode / decode a value

The codec is driven by the IR. A "value" is a plain dict keyed by field name
(enums as their member-name string); **composed messages just nest** — embedded
messages are dicts, lists of messages are lists of dicts:

```python
task = {
    "id": 1, "title": "ship prism", "state": "doing",
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
  (`python generate.py`).
- **Clients are generic** — one ~100-line client per language exposes
  `call(method, args)` and `subscribe(method, args)`; there is **no per-method
  code**. Adding a method to the IR needs no client change.
- **Servers** dispatch by reading the IR: a method's `kind` decides
  request-vs-stream, and the handler is a plain function over native types.

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
python3 -m prism.ir.compat tasks.ir.json.prev tasks.ir.json
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
- [Overview.md](Overview.md) — the model and what Prism decouples.
