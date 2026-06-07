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

> Status: **pre-alpha**. The model, codec, generators, corpus, and evolution gate
> are built and tested (53 tests green); APIs may still move.

```
pip install taut-proto      # distribution name (PyPI)
import taut                 # import name
tautc gen api.taut.py -o gen/   # CLI codegen
```

The distribution is named `taut-proto` (PyPI rejects the bare `taut`); the import
package and CLI are `taut` / `tautc` — the Pillow→PIL pattern. Pure Python, no
runtime dependencies.

---

## Why

A schema language earns its keep by removing ambiguity between services in
different languages. Protobuf does that but drags in a code-gen plugin
architecture, a bespoke grammar, language runtimes, and a wire format few can
read. taut keeps the parts that matter and drops the rest:

| You want | protobuf | taut |
| --- | --- | --- |
| one governed schema | `.proto` grammar + `protoc` | a few lines of typed Python (or JSON) |
| generated native types | plugin per language | `tautc gen` / library calls |
| portable, deterministic wire | varint protobuf | a frozen deterministic-CBOR subset (RFC 8949 §4.2) |
| dynamic / zero-codegen use | limited | fully IR-driven codec in Python & TS |
| safe schema evolution | review + custom lint | a structural **breaking-change gate** |
| forward-compat | proto3 dropped then restored | opt-in unknown-field preservation |
| streaming / subscriptions | hand-rolled | first-class **delivery shapes** |

Because the IR is data — not a Turing-complete program — taut can *diff* two
versions of a contract and tell you mechanically what broke.

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

## `tautc` — codegen CLI

```
tautc gen IR --out DIR [--lang python,typescript,rust,cpp] [--service A,B] [--api-only]
```

Loads a `.taut.py` or `.ir.json`, validates it, and emits per language:
`api` (native types + encoders/decoders), plus `client`/`server` stubs per
service. `--api-only` emits just the struct defs + codec — the drop-in for a
build script on a compiled target. Example: razel (a Rust build daemon) authors
`ir/razel.taut.py` and generates its Rust wire layer with
`tautc gen ir/razel.taut.py -o razel/gen --lang rust --api-only`.

## Evolution

- **Breaking-change gate** — structural diff of two IR versions classifies each
  change `breaking` / `compatible` (remove field, retag, change a method's
  shape → breaking; add a field/method → compatible). Run it in CI.
- **Forward-compatibility** — opt-in unknown-field preservation: a decoder keeps
  unrecognized tags as raw CBOR and re-emits them in canonical order, so an old
  hop relaying a new message loses nothing.
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

taut sits at the mechanism tier beneath **Glade**, a declarative share-kernel for
distributed/server state; see [dev-docs/TautPlan.md](dev-docs/TautPlan.md).
