# Generated code + runnable examples — Tasks API

Generated from [`../tasks.taut.py`](../tasks.taut.py) by
[`../generate.py`](../generate.py) (regenerate with `python generate.py`). One
directory per language, each **self-contained and runnable**:

```
generated/<lang>/api.<ext>       — native types (structs / classes / enums) + codec
generated/<lang>/client.<ext>    — a typed client stub over the generic transport
generated/<lang>/server.<ext>    — a handler interface stub
generated/<lang>/cbor.<ext>      — the vendored deterministic-CBOR runtime (compiled targets)
generated/<lang>/ext.<ext>       — the vendored extension accessors (compiled targets)
generated/<lang>/example.<ext>   — a runnable round-trip: build a Task, encode, decode, verify
```

Every `example.*` builds the same `Task` (id, title, an enum `state`, an optional
nested `User` assignee, a list of `Comment`, and a `map<str,str>` of labels), encodes
it, decodes it back through the message's typed decode from bytes, and checks the
re-encoding is byte-identical. It then checks that the bytes cut short by one are
refused with the language's decode error, tag `Truncated`, rather than a crash. **Every
example produces the same 72 bytes** (cross-language parity, live), and exits non-zero
on a mismatch.

## Run each example (from `generated/<lang>/`)

| lang | run |
| --- | --- |
| **python** | `python ../../run.py` (the IR-driven codec) |
| **typescript** | `node --experimental-strip-types example.ts` |
| **javascript** | `node example.js` |
| **rust** | `rustc --edition 2021 example.rs -o example && ./example` |
| **c++** | `clang++ -std=c++20 -I. example.cpp -o example && ./example` |
| **swift** | `swiftc *.swift -o example && ./example` |
| **go** | `go test -v` |
| **kotlin** | `kotlinc *.kt -include-runtime -d example.jar && java -cp example.jar taut.ExampleKt` |
| **java** | `javac *.java -d out && java -cp out taut.Example` |

## Two models

- **Generated types + codec** — Rust, C++, Swift, Go, Kotlin, Java, and JS get
  native types with `to_cbor`/`from_cbor` (naming per language) and a typed decode
  from bytes per message (`Task::decode`, `TryTaskFromBytes`, `Task::try_decode`, …),
  paired with the vendored `cbor.*` runtime. Decode is fail-closed: it returns a value
  or the language's decode error, under the message's `max_depth` and
  `max_encoded_len` (see [CodecContract.md](../../../CodecContract.md)).
- **IR-driven runtime codec** — Python and TypeScript instantiate from the IR JSON
  and encode/decode with **zero per-type code**; the TS example loads
  `../../tasks.ir.json` directly. (JS here uses the generated-class form.)

## client / server stubs

The **client**/**server** files are *typed convenience stubs*. In taut's design the
client and server runtimes are **generic** — one small client and server loop per
language that read the IR with zero per-method code (see
[dev-docs/CodeShape.md](../../../../dev-docs/CodeShape.md)); these stubs are
the thin typed layer over that runtime.
