# taut — C++ API

> Using taut-generated **C++** code: native types, the deterministic-CBOR wire,
> forward-compatibility, and side-channel extensions. Authoring an IR is in
> [Reference.md](Reference.md); serving a service is in [Server.md](Server.md).

Generated C++ is plain types over a vendored, dependency-free CBOR runtime. Encode is
**constexpr** — a value is serialized to bytes *at compile time* — so the conformance
corpus proves the bytes with `static_assert`. Every language reproduces the *same bytes*.

## 1. Generate

```sh
tautc gen --lang cpp --with-runtime -o <out>
```

Writes, into `<out>/cpp/`:

| file | what |
| --- | --- |
| `api.hpp` | native types (`enum class`/`struct`) + `to_cbor`/`from_cbor` |
| `taut/cbor.hpp` | the deterministic-CBOR runtime (`Cbor`, `Buf`, `parse`, `encode_value`) |
| `taut/ext.hpp` | extension accessors (`ext_set`/`ext_get`/`ext_clear`) |
| `client.hpp` / `server.hpp` | typed stubs over a transport (see [Server.md](Server.md)) |

Build with `-std=c++20`, `-I<out>/cpp`; `api.hpp` does `#include "taut/cbor.hpp"`. No
third-party headers — the runtime is header-only.

## 2. Native types

Enums are `enum class : long long`; the integer is the wire value, the names a projection:

```cpp
enum class TaskState : long long { Open = 0, Doing = 1, Done = 2 };
```

Messages are structs with `to_cbor` / `from_cbor`:

```cpp
struct User {
  long long id;
  std::string_view name;
  constexpr void to_cbor(Buf& b) const;        // b.map(2); b.uint(1); … b.uint(2); …
  static constexpr User from_cbor(const Cbor& c);   // c.get(1).as_int(), c.get(2).as_text()
};
```

Field mapping: `INT → long long`, `STR/BYTES → std::string_view`, `BOOL → bool`,
`FLOAT → double`, `List(T) → std::vector<T>`, `Map(K,V) → std::map<K,V>`. **Optional**
fields are `std::optional<T>` (encoded as CBOR `null` when empty). **Transient** fields are
in the struct but never on the wire (value-initialized, left default on decode).

## 3. Encode / decode

`to_cbor(Buf&)` writes bytes into a fixed `Buf` (encode is compile-time); `parse` then
`from_cbor(const Cbor&)` reads them back (decode is runtime):

```cpp
taut::Buf b; task.to_cbor(b);                  // serialize into b.d[0..b.n)
auto c = taut::parse(std::string_view(reinterpret_cast<const char*>(b.d), b.n));
taut::Task back = taut::Task::from_cbor(c);    // deserialize
```

A `Buf` is a fixed `unsigned char d[512]` plus length `n` — sufficient for one message;
oversized payloads (e.g. extensions on a large host) use the runtime's heap path in §6.

## 4. The `Cbor` runtime (`taut/cbor.hpp`)

A tiny frozen subset of RFC 8949 in core deterministic encoding (definite lengths,
shortest-form ints, ascending map keys, shortest-form floats). Hand-rolled, zero deps.

```cpp
struct Cbor {
  enum class K { Int, Bytes, Text, Arr, Map, Bool, Null, Float };
  K k; long long i; double f; std::string_view s;
  std::vector<Cbor> arr; std::vector<std::pair<long long, Cbor>> map;
};

constexpr Cbor parse(std::string_view d);          // bytes -> tree
constexpr void encode_value(Buf& b, const Cbor& c); // tree -> bytes (canonical)
```

Accessors: `.as_int()`, `.as_text()`, `.as_bytes()`, `.as_bool()`, `.as_float()`,
`.as_array()`, `.get(key)` (map value by integer key), `.is_null()`. `Text`/`Bytes` are
`string_view` slices **into the parsed source** — keep that buffer alive while they're read.

## 5. Forward-compatibility (unknown-field preservation)

Generate with `--forward-compat` and each struct gains
`std::vector<std::pair<long long, Cbor>> wire_residual`. On `from_cbor`, keys the struct
doesn't name are captured there; on `to_cbor`, they're re-emitted **merged with the known
fields in one ascending-key order** — so a node that *decodes → edits → re-encodes* a newer
message never drops fields it doesn't understand. A message with no unknowns is
byte-identical with or without the flag.

A schema that declares an extension **requires** `--forward-compat` (build error
otherwise — extensions ride the residual space).

## 6. Extensions (side-channels) — `taut/ext.hpp`

Attach / read / clear a declared extension on *any* host message's wire bytes, knowing only
the extension's schema (never the host's). Tags live in the band ≥ `2^20`:

```cpp
std::vector<unsigned char> ext_set(std::string_view host, long long tag, const Cbor& value);
std::optional<Cbor>        ext_get(std::string_view host, long long tag);  // nullopt if absent
std::vector<unsigned char> ext_clear(std::string_view host, long long tag);
```

`value` is the extension message as a `Cbor` (encode it, then `parse`); decode `ext_get`'s
result with `ExtMsg::from_cbor()`:

```cpp
taut::Buf eb; decision.to_cbor(eb);
auto raw = taut::ext_set(host, 0x100001,
    taut::parse(std::string_view(reinterpret_cast<const char*>(eb.d), eb.n)));
std::string_view hv(reinterpret_cast<const char*>(raw.data()), raw.size());
auto decision = taut::ext_get(hv, 0x100001).transform(
    [](const taut::Cbor& c) { return taut::Decision::from_cbor(c); });
auto stripped = taut::ext_clear(hv, 0x100001);
```

A below-band `tag` throws `std::invalid_argument`; a non-map host throws. The host app
decodes its own message obliviously — the extension rides in `wire_residual` and survives.
`ext_get`'s `Cbor` holds `string_view`s into `host` — keep the host bytes alive until it's
decoded into an owning/typed value.

## 7. Consuming the runtime

`taut/cbor.hpp` / `taut/ext.hpp` are vendored, dependency-free, header-only source — drop
them under an include root and `#include "taut/cbor.hpp"`; `api.hpp` already does.
`-std=c++20` is the only toolchain requirement. The bytes match every other taut target.
