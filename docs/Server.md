# taut — Building a Server

This shows how to stand up a server for a taut service: write handlers, back the
streaming endpoints with delivery-shape engines, **register them against the IR**
(so `shape`/params come from the contract, not by hand), and serve.

> The snippets below use the **Tasks** API from [GettingStarted.md](GettingStarted.md)
> and show the generic binding shape: handlers, delivery-shape engines, IR-driven
> transport, and WebSocket framing.

## The handler contract

A handler is a **plain function over native values** — no envelope, transport,
codec, or shape logic inside it. Its form follows the method's `shape`:

| method `shape` | handler signature |
| --- | --- |
| `unary` (delivered once) | `async def(**params) -> value` (returns the `out` value) |
| any streaming shape | `def(**params) -> Subscription` (returns a shape's open subscription) |

`params` are exactly the IR method's params, by name. The value types are the
native types for your IR messages (the reference binding gives you typed
objects; at the codec level a "value" is a dict keyed by field name).

## 1. Back streaming endpoints with shape engines

Each streaming endpoint is fed by a delivery-shape engine
(`griplab_slice.shapes`): `Atom`, `Log`, `Stream`, `Swmr`. They register
subscribers and emit events; `.open()` returns a `Subscription` (the snapshot/
replay/registration is handled for you).

```python
from griplab_slice.shapes import Atom, Log, Subscription

tasks = Atom([])     # atom: the whole task list (latest-wins, pushed on change)
activity = Log()     # log: an append-only feed (replay then tail)
```

## 2. Write the handlers

```python
_seq = {"n": 0}

async def create(title):                       # unary -> Task
    _seq["n"] += 1
    task = {"id": _seq["n"], "title": title, "state": "open", "assignee": None, "comments": []}
    tasks.set(tasks.get() + [task])            # atom: replace whole-state -> 'replace' event
    activity.append({"ts": _seq["n"], "text": f"created {title}"})  # log: 'append' event
    return task

async def set_state(id, state):                # unary -> bool
    tasks.set([{**t, "state": state} if t["id"] == id else t for t in tasks.get()])
    return True

async def comment(task_id, author, text):      # unary -> Comment (a message param + return)
    c = {"author": author, "text": text}       # author is a nested User value
    tasks.set([{**t, "comments": t["comments"] + [c]} if t["id"] == task_id else t
               for t in tasks.get()])
    activity.append({"ts": _seq["n"], "text": f"comment on #{task_id}"})
    return c

def tasks_subscribe() -> Subscription:         # shape=atom -> Subscription
    return tasks.open()

def activity_subscribe() -> Subscription:      # shape=log -> Subscription
    return activity.open()
```

Note what's *not* here: nothing about CBOR, WebSocket, the envelope, or which
events a shape emits. `tasks.set(...)` triggers the `replace` event; `.open()`
delivers the current state then live updates. That's the shape doing its job.

## 3. Register against the IR

The transport binds each IR `MethodDef` to a handler. **The kind (unary vs
stream) and the param decoding come from the IR**, so the only thing you hand-write
is the name→handler map — and a drift check fails fast if it disagrees with the
contract:

```python
from griplab_slice.transport import InProcessTransport

handlers = {
    "create": create,
    "set_state": set_state,
    "comment": comment,
    "tasks.subscribe": tasks_subscribe,
    "activity.subscribe": activity_subscribe,
}

svc = SCHEMA.services["Tasks"]
declared = {m.name for m in svc.methods}
missing, extra = declared - handlers.keys(), handlers.keys() - declared
if missing or extra:
    raise RuntimeError(f"handler/contract drift: missing={missing} extra={extra}")

transport = InProcessTransport()
for m in svc.methods:                 # registration derived from the contract
    transport.register_method(m, handlers[m.name])
```

This is the same loop shape used by the reference composition. Add a method to the IR and the server
picks it up by name; the drift check ensures you didn't forget a handler.

## 4. Serve

The WebSocket loop dispatches purely from the contract — it reads the bound method's `shape`:

- **unary** → `await transport.request(method, payload)` → send one response;
- **streaming shape** → `transport.open(method, payload)` → pump the shape's
  events as `stream-event` frames until the client disconnects.

The envelope is JSON, message payloads are CBOR (the wire from
[Reference.md](Reference.md) §8). Sketch:

```python
import asyncio
from griplab_slice import ws            # hand-rolled WebSocket (sha1 + frames)
from griplab_slice.jsonwire import envelope_from_json, envelope_to_json

async def handle(conn, transport):
    async for raw in conn:              # each text frame is a JSON envelope
        env = envelope_from_json(raw)
        bound = transport._methods[env.method]
        if bound.mdef.streams():
            sub = transport.open(env.method, env.payload)
            async for ev in sub:        # snapshot/replace/append/delta… per the shape
                await conn.send(envelope_to_json(ev_with_stream_id(ev, env.stream_id)))
        else:
            resp = await transport.request(env.method, env.payload)
            resp.message_id = env.message_id          # echo for client correlation
            await conn.send(envelope_to_json(resp))
```

(See `server.py` for the complete loop with subscription teardown and stream-id
tagging.)

## 5. Consume it

Any client — [Reference.md](Reference.md) §12 — talks to it generically:

```python
client = await WsClient.connect(f"ws://127.0.0.1:{port}")
task = await client.call("create", Task, title="ship taut")   # unary
async for event, value in await client.subscribe("tasks.subscribe"):
    ...                                                          # 'replace' -> the task list
```

A TypeScript or Rust client talks to the same server unchanged when driven by the same IR.

## What's generic vs per-IR today

Generic and reusable: the shape engines, the IR-driven transport/registration,
the WebSocket server loop, the wire. Currently bound to one IR: the codec's
**native-type binding** (`griplab_slice/wire.py` loads a specific schema and maps
its messages to dataclasses). To serve *your* API today you point that binding at
your schema and types; turning it into a point-at-any-IR `taut.serve(schema,
handlers)` library is a noted next step.

The generated server stubs and runtime client helpers show the target-specific wiring shape.
