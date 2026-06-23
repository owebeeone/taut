# taut documentation

Start here, then dig in:

- **[Overview](Overview.md)** — the mental model: what a taut "web API" is, the
  `(name, in, out, shape)` method contract, and the delivery-shape catalog.
- **[Getting Started](GettingStarted.md)** — author an IR → validate → encode/
  decode → generate code, end to end.
- **[Reference](Reference.md)** — every DSL helper, the type system, the shape
  registry, and the validator rules.
- **[Building a Server](Server.md)** — handlers, shape engines, and the
  WebSocket dispatch loop.

## Per-language APIs

How to *use* taut-generated code in each target — native types, encode/decode, the
deterministic-CBOR runtime, forward-compatibility, and side-channel extensions:

[Python](PYTHON_API.md) · [TypeScript](TYPESCRIPT_API.md) · [Rust](RUST_API.md) ·
[C++](CPP_API.md) · [Go](GO_API.md) · [Java](JAVA_API.md) · [Kotlin](KOTLIN_API.md) ·
[JavaScript](JS_API.md) · [Swift](SWIFT_API.md)

## Example

- **[examples/tasks/](examples/tasks/)** — a complete, runnable Tasks API: the
  authored IR, a round-trip + breaking-change-gate driver (`run.py`), and the
  generated `api` / `client` / `server` for all nine targets
  (regenerate with `tautc gen tasks.taut.py -o generated/`).

## See also

- **[../README.md](../README.md)** — project overview and install.
- **[../dev-docs/](../dev-docs/)** — design notes and the decisions log
  (`Taut*.md`).
