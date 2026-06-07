# taut

**One tiny declarative contract → native types, a deterministic wire codec, and
service stubs across Python, TypeScript, Rust, and C++ — verified byte-for-byte
by a shared golden corpus.**

taut is a cross-language data + service protocol mechanism: protobuf's essential
value (a single governed schema, generated types, a portable wire format, an
evolution gate) with roughly 90% less of its weight (no plugin toolchain, no
`.proto` grammar, no required runtime, a wire you can read in an afternoon). The
schema is authored as a small, restricted Python DSL — or any `.ir.json` — and
everything else is *projected* from it.

> Status: **alpha**. The model, codec, generators, corpus, and evolution gate are
> built and tested end-to-end across four languages (57 tests green); APIs may
> still move.

```
pip install taut-proto      # distribution name (PyPI)
import taut                 # import name
tautc gen api.taut.py -o gen/   # CLI codegen
```

The distribution is named `taut-proto` (PyPI rejects the bare `taut`); the import
package and CLI are `taut` / `tautc` — the Pillow→PIL pattern. Pure Python, no
runtime dependencies.

---

## taut vs proto3

A schema language earns its keep by removing ambiguity between services in
different languages. proto3 (with gRPC) does that but drags in a code-gen plugin
architecture, a bespoke grammar, per-language runtimes, an HTTP/2 RPC stack, and
a wire format few can read by hand. taut keeps the parts that matter and drops
the rest:

| Dimension | proto3 / gRPC | taut |
| --- | --- | --- |
| **Schema source** | `.proto` DSL + `protoc` + a plugin per language | a few lines of typed Python, or `.ir.json` |
| **Toolchain** | `protoc` compiler + language plugins | one `pip install`; `tautc` for compiled targets |
| **Wire format** | varint tag-length-value; **not guaranteed canonical** across implementations (maps are explicitly unordered) | frozen **deterministic** CBOR (RFC 8949 §4.2) — byte-identical everywhere, corpus-pinned |
| **Codegen required?** | yes for most languages (or descriptor-based reflection) | **no** for Python/TS (IR-driven runtime codec); generated for Rust/C++ |
| **Runtime dependency** | a protobuf runtime per language | **none** (stdlib; hand-rolled codec per target) |
| **Field presence** | scalars had none; `optional` presence re-added in **3.15** | `optional` → null; presence is clean (fields always emitted) |
| **`required`** | removed in proto3 | kept as a *governance assertion*, enforced by the evolution gate (never a decode error) |
| **Forward-compat (unknown fields)** | dropped in 3.0, restored in **3.5** — and **binary only** (the JSON mapping drops them) | opt-in unknown-field preservation (raw tags re-emitted in canonical order) |
| **Services / RPC** | `service`/`rpc`, but the transport *is* gRPC: HTTP/2 + codegen + runtime | `(name, in, out, shape)`; transport-agnostic (reference: JSON envelope + CBOR payload) |
| **Streaming** | gRPC client/server/bidi streams | first-class **delivery shapes**: `atom` / `log` / `stream` / `swmr` / `snapshot_delta` / `crdt` |
| **Schema evolution** | field-number rules + `reserved`; breaking-change detection is **external** (buf, protolock) | a **built-in structural breaking-change gate**, runnable in CI |
| **Extensions** | proto2 had them; proto3 dropped them (use `Any`) | declared, typed **side-channels** at a reserved tag band |
| **Read the whole spec** | large surface | the IR fits on a screen |

Because the IR is data — not a Turing-complete program — taut can *diff* two
versions of a contract and tell you mechanically what broke.

**What taut deliberately doesn't have (yet):** `map` and `oneof` types,
well-known types (`Timestamp`/`Any`/`Duration`), a canonical JSON profile
(deferred), descriptor/reflection services, and — above all — proto's ecosystem
maturity, scale hardening, and gRPC's battle-tested multi-language RPC runtime.
taut is a focused mechanism, not a drop-in protobuf replacement for every use
case. If you need proto's breadth, use proto; taut is the lighter contract when
you want ~10% of the load for the parts that actually bite.

## The contract

A schema is **enums + messages + services**, authored declaratively:

```python
from taut.ir.dsl import INT, STR, BYTES, Enum, F, Msg, Ref, List, method, service, schema

SCHEMA = schema(
    Enum("BuildStatus", cached=0, built=1, failed=2),

    Msg("OutputArtifact",
        F("path", 1, STR),
        F("digest", 2, BYTES),
        next_id=3),

    Msg("BuildResult",
        F("target", 1, STR),
        F("status", 2, Ref("BuildStatus")),
        F("outputs", 3, List(Ref("OutputArtifact"))),
        F("message", 4, STR, optional=True),
        next_id=5),

    service("Razel",
        method("build", role="in", params=[("target", STR)], out=Ref("BuildResult")),
        method("build.subscribe", role="out", shape="atom", out=Ref("BuildState"))),
)
```

- **Fields** carry an explicit integer `tag`, a type, and flags (`optional`,
  `transient`, CRDT `merge`). Types are a closed set: scalars (`int/str/bytes/
  bool`), enum/message refs, and `List`.
- **`reserved` + `next_id`** are first-class, validated message features (not
  comments) — retired tags/names can never be reused, and `next_id` is checked.
- **Methods are the minimal contract `(name, in, out, shape)`.** `shape` is the
  *sole* discriminator: `unary` (request→response, the default) is just the
  degenerate member of an **open shape registry**, alongside streaming shapes
  `atom` (latest-wins state), `log` (append-only), `stream` (live), `swmr`
  (snapshot+delta), `snapshot_delta`, and `crdt`. `out` binds a type per the
  shape's delivery slots. There is no separate "kind" axis to disagree — illegal
  states are unrepresentable. (See [Reference §5–6](docs/Reference.md).)

A **validator** rejects incoherent IR (dangling refs, duplicate tags, out-slots
that don't match a shape, …), so downstream mechanism can be derived without
review.

## The wire

A hand-rolled, frozen **deterministic CBOR** subset: definite-length, shortest-
form integers, ascending integer map keys. The same value encodes to the same
bytes in every language — pinned by a **golden conformance corpus** (value →
exact hex). Python and TypeScript run a fully **IR-driven codec** (instantiate a
client or server from JSON alone, zero codegen); Rust and C++ get **generated
native types with encoders/decoders** (compiled targets need types ahead of
time). The C++ corpus is a wall of `static_assert`s — *compiling is the test*.

## Opinionated about the wire, not the API

Small-and-tight vs. bloated is only half the pitch. The other half: taut pins
*exactly* what cross-language interop requires — the deterministic wire, the
`(name, in, out, shape)` contract, and the evolution gate — and **nothing more**.
Those must be fixed, so they are.

How that contract surfaces in *your* code is your call. The IR is the governed
artifact (a tiny JSON); projecting it into types, clients, and servers is a
choice, not a mandate:

- The bundled `tautc` generators are **reference** projections. Use them, swap
  them, or write your own against the exported `.ir.json` — pydantic models, plain
  dataclasses, a transactional/ORM wrapper, different client ergonomics, whatever
  fits your app.
- Or generate nothing: Python and TypeScript drive the IR straight through the
  runtime codec.

Where `protoc` hands you *its* message classes and gRPC *its* stubs, taut hands
you the bytes and the schema and gets out of the way.

## `tautc` — the reference codegen CLI

```
tautc gen IR --out DIR [--lang python,typescript,rust,cpp] [--service A,B] [--api-only]
```

Loads a `.taut.py` or `.ir.json`, validates it, and emits per language:
`api` (native types + encoders/decoders), plus `client`/`server` stubs per
service. `--api-only` emits just the struct defs + codec — the drop-in for a
build script on a compiled target. `--with-runtime` additionally emits the
vendored CBOR runtime for compiled targets (`rust` → `cbor.rs`, `cpp` →
`taut/cbor.hpp`), so the generated output compiles **standalone** — no
hand-vendoring. Example: razel (a Rust build daemon) authors
`ir/razel.taut.py` and generates its Rust wire layer with
`tautc gen ir/razel.taut.py -o razel/gen --lang rust --api-only`.

These are the *reference* emitters; they read the exported `.ir.json`, and so can
a generator you write — `tautc` is a convenience, not a requirement.

**Conformance** — `tautc corpus IR -o DIR [--lang rust] [--check]` derives a golden
corpus from the IR (deterministic coverage values, one per message, encoded by the
canonical codec → `golden.json`) plus a per-language byte-parity harness (Rust
`vectors.rs` today). A target *conforms* iff its codec reproduces those bytes;
`--check` is the CI drift gate. No hand-authored vectors.

## Evolution

- **Breaking-change gate** — structural diff of two IR versions classifies each
  change `breaking` / `compatible` (remove field, retag, change a method's
  shape → breaking; add a field/method → compatible). Run it in CI.
- **Forward-compatibility** — unknown-field preservation: a decoder keeps
  unrecognized tags as raw CBOR and re-emits them in canonical order, so an old
  reader relaying a new message loses nothing. Default-on in the Python/TS runtime
  codec; opt-in for generated structs (Rust + C++) via `tautc gen --forward-compat`
  (a `wire_residual` field). Proven across all four languages by a cross-version
  test: a v1 struct round-trips a v2-only field **byte-for-byte** — even when the
  unknown tag interleaves between known ones.
- **Extensions** — declared, typed side-channels at a reserved tag band
  (`BAND_START = 2^20`); infrastructure reads/writes them on the wire without the
  app schema knowing.

## Layout

```
src/taut/        the builder (pure Python)
  ir/            model, DSL, validator, export/load, breaking-change gate, shapes
  wire/          deterministic CBOR + IR-driven codec
  gen/           generators: Rust, C++, and the per-language scaffold
  cli.py         the `tautc` command
ir/              authored IR modules — the only governed artifact
                 (griplab.taut.py, razel.taut.py)
corpus/          generated golden vectors (the oracle)
docs/            Overview, GettingStarted, Reference, Server + a runnable example
dev-docs/        design notes + the decisions log (Taut*.md)
.github/         the PyPI publish workflow (Trusted Publishing on release)
```

Reference target implementations and the full cross-language interop matrix
(TS/Rust/Python clients × Python/Rust servers, plus the C++ oracle) live in a
companion `trial/` repo, each validated against this repo's corpus.

## Docs

- [Overview](docs/Overview.md) — the mental model and the shape catalog.
- [Getting Started](docs/GettingStarted.md) — author → validate → encode → generate.
- [Reference](docs/Reference.md) — every DSL helper, the shapes, the validator rules.
- [Building a Server](docs/Server.md) — handlers, shape engines, the WS loop.
- [examples/tasks](docs/examples/tasks/) — a complete runnable API with generated
  code for all four languages.

## Develop

```
python run_tests.py        # regenerate the corpus, run the suite
```

Design notes and the decisions log live in [dev-docs/](dev-docs/).

## License

[MIT](LICENSE)
