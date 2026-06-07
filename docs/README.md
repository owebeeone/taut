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

## Example

- **[examples/tasks/](examples/tasks/)** — a complete, runnable Tasks API: the
  authored IR, a round-trip + breaking-change-gate driver (`run.py`), and the
  generated `api` / `client` / `server` for Python, TypeScript, Rust, and C++
  (regenerate with `tautc gen tasks.taut.py -o generated/`).

## See also

- **[../README.md](../README.md)** — project overview and install.
- **[../dev-docs/](../dev-docs/)** — design notes and the decisions log
  (`Taut*.md`).
