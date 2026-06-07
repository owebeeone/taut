# Generated code — Tasks API

Generated from [`../tasks.taut.py`](../tasks.taut.py) by
[`../generate.py`](../generate.py) (regenerate with `python generate.py`). One
directory per language, each with three files:

```
generated/<lang>/api.<ext>     — native types (structs / interfaces / enums)
generated/<lang>/client.<ext>  — a typed client over the generic transport
generated/<lang>/server.<ext>  — a handler interface + IR-driven registration
```

| lang | api | client / server |
| --- | --- | --- |
| `python` | dataclasses + `Enum` (a package: `from .api import *`) | `TasksClient`, `TasksHandlers` Protocol + `register()` |
| `typescript` | `interface` + string-union enums | `TasksClient`, `TasksHandlers` interface + `register()` |
| `rust` | `struct` + `enum` with `to_cbor`/`from_cbor` | `TasksClient`, `TasksHandlers` trait |
| `cpp` | `struct` + `enum class` with `constexpr to_cbor`/`from_cbor` | `TasksClient`, virtual `TasksHandlers` |

## What's actually generated, and what isn't

The **api** is the real per-API artifact — and the Rust/C++ type emitters are the
same ones whose output is proven byte-for-byte by the conformance corpus
(`trial/rs`, `trial/cpp`). The Python `api.py` imports and constructs cleanly
(incl. nested/optional/list-of-message composition).

The **client** and **server** are *typed convenience stubs*. In taut's design
the client and server runtimes are **generic** — one ~100-line client and one
server loop per language that read the IR and need **zero per-method code** (see
[../../../dev-docs/CodeShape.md](../../../dev-docs/CodeShape.md)). These stubs are
the thin typed layer on top:

- the **client** wraps the generic transport's `call(method, …)` / `subscribe(method, …)`;
- the **server** declares one handler per method and a `register()` that binds
  names→handlers, with `kind`/params coming from the IR contract.

So they reference the per-language runtime that lives in the `trial/` slices
(`trial/<lang>/.../client.*`, `server.*`). The Python stubs are import-verified;
the Rust/C++/TS client/server are mechanically generated against that runtime
(the api portions compile/typecheck as proven in the trials).
