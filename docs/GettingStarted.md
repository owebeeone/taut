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
from taut.ir.dsl import BOOL, INT, STR, Enum, F, List, Map, Msg, Params, Ref, method, schema, service

SCHEMA = schema(
    # the web API: a service of methods. Each method is (name, in, out, shape);
    # `shape` is the sole discriminator and defaults to `unary` (delivered once).
    service("Tasks",
        # unary (default shape): request -> response. params can be messages.
        method("create", role="in",
               params=Params(title=STR), out=Ref.Task),
        method("comment", role="in",
               params=Params(task_id=INT, author=Ref.User, text=STR),
               out=Ref.Comment),
        method("set_state", role="ctl",
               params=Params(id=INT, state=Ref.TaskState), out=BOOL),

        # Atom: the whole task list, latest-wins, pushed on every change
        method("tasks.subscribe", role="out", shape="atom",
               out=List(Ref.Task)),

        # Log: an append-only activity feed (replay then tail)
        method("activity.subscribe", role="out", shape="log",
               out=Ref.Event),
    ),

    # an enum — integer wire values, idiomatic native names per language
    TaskState=Enum(open=0, doing=1, done=2),

    # messages compose: a field can reference another message, an optional
    # message, or a list of messages — nesting is automatic on the wire.
    User=Msg(
        id=F(1, INT),
        name=F(2, STR)),

    Comment=Msg(
        author=F(1, Ref.User),          # a message field — composition
        text=F(2, STR)),

    Task=Msg(
        id=F(1, INT),
        title=F(2, STR),
        state=F(3, Ref.TaskState),       # enum field
        assignee=F(4, Ref.User, optional=True),  # nested message, optional
        comments=F(5, List(Ref.Comment)),        # list of messages
        labels=F(7, Map(STR, STR)),                 # map<str,str> — a keyed collection
        reserved=[6, "priority"],   # tag 6 / "priority" retired (see §5) — never reusable
        next_id=8),

    Event=Msg(
        ts=F(1, INT),
        text=F(2, STR)),
)
```

That file *is* the governed artifact — four messages (composed: `Task` embeds an
optional `User`, a list of `Comment`, and a `map<str,str>` of `labels`; each
`Comment` embeds a `User`), one enum, and a service of three unary calls and two
streaming endpoints, read whole in a screen. (`out=` is a bare type for
single-slot shapes — bound to the shape's slot; multi-slot shapes like `swmr` take
`out={"snapshot": …, "delta": …}`.)

Keyword-named enums, messages, fields, `Ref.Name` references, and `Params(...)`
method params are the preferred style. The positional `service(...)` declaration
appears before keyword declarations because Python requires positional call
arguments first; references resolve after the whole schema is built.

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
messages are dicts, lists of messages are lists of dicts, and **maps are dicts**
(emitted key-sorted on the wire, so the bytes are deterministic):

```python
task = {
    "id": 1, "title": "ship taut", "state": "doing",
    "assignee": {"id": 7, "name": "ann"},                 # nested message
    "comments": [                                          # list of messages
        {"author": {"id": 7, "name": "ann"}, "text": "started"},
        {"author": {"id": 9, "name": "bo"},  "text": "lgtm"},
    ],
    "labels": {"team": "infra", "area": "wire"},          # map<str, str>
}
blob = codec.encode(schema, "Task", task)      # deterministic CBOR bytes
assert codec.decode(schema, "Task", blob) == task

# an optional nested message that's absent decodes as None; an empty map is just {}
later = {"id": 2, "title": "later", "state": "open",
         "assignee": None, "comments": [], "labels": {}}
assert codec.decode(schema, "Task", codec.encode(schema, "Task", later)) == later
```

The codec recurses through the composition automatically; the bytes are the same
in every language — that's what the golden corpus pins.

## 4. Talk to it across languages

The contract is enough to generate/derive the rest:

- **Nine targets** — Python, TypeScript, Rust, C++, Swift, Go, Kotlin, JS, Java —
  projected from the same `tasks.ir.json`. The compiled targets (Rust, C++, Swift,
  Go, Kotlin, Java, JS) get native types **with a generated codec** plus the
  vendored CBOR runtime; Python and TypeScript use the **IR-driven runtime codec**
  (no per-type code). See [`examples/tasks/generated/`](examples/tasks/generated/)
  for the **api / client / server** + a runnable `example.*` emitted for *this* API
  in all nine — `tautc gen tasks.taut.py -o generated/ --with-runtime` (the codegen
  CLI; add `--api-only` for just struct defs + encoders/decoders, `--lang` to narrow).
- **Clients are generic** — one ~100-line client per language exposes
  `call(method, args)` and `subscribe(method, args)`; there is **no per-method
  code**. Adding a method to the IR needs no client change.
- **Servers** dispatch by reading the IR: a method's `shape` decides
  request-vs-stream (`unary` = once), and the handler is a plain function over
  native types.

**[Server.md](Server.md)** walks through building a server for this exact Tasks
API: write handlers (plain functions), back the streaming endpoints with shape
engines, register them against the IR, and serve. See `src/taut/gen/runtime/typescript/taut_client.ts`,
and the generated client/server stubs for the client/server shape.

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
Task=Msg(
    id=F(1, INT), title=F(2, STR), state=F(3, Ref.TaskState),
    assignee=F(4, Ref.User, optional=True), comments=F(5, List(Ref.Comment)),
    labels=F(7, Map(STR, STR)),  # added at tag 7 — tag 6 was retired, so it's skipped
    reserved=[6, "priority"],   # retired tag 6 + name "priority" — never reusable
    next_id=8)                  # next tag to allocate (validated > every used/reserved tag)
```

See [Reference.md](Reference.md) §4 for the rules.

## Where to go next

- [Server.md](Server.md) — build a server for this API: handlers, shape engines,
  registration from the IR, serving.
- [Reference.md](Reference.md) — every DSL primitive, the delivery-shape catalog,
  CRDT fields, and the toolchain.
- [Overview.md](Overview.md) — the model and what taut decouples.
