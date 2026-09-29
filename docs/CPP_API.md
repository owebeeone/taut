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
| `api.hpp` | native types (`enum class`/`struct`) + `to_cbor`/`try_decode`/`try_from_cbor` |
| `taut/cbor.hpp` | the deterministic-CBOR runtime (`Cbor`, `Buf`, `try_decode`, `encode_value`) |
| `taut/ext.hpp` | extension accessors (`ext_set`/`ext_get`/`ext_clear`) |
| `client.hpp` / `server.hpp` | typed stubs over a transport (see [Server.md](Server.md)) |

Build with `-std=c++20`, `-I<out>/cpp`; `api.hpp` does `#include "taut/cbor.hpp"`. No
third-party headers — the runtime is header-only.

## 2. Native types

Enums are `enum class : long long`; the integer is the wire value, the names a projection:

```cpp
enum class TaskState : long long { Open = 0, Doing = 1, Done = 2 };
```

Messages are structs with `to_cbor` / `try_decode` / `try_from_cbor` and their bounds:

```cpp
struct User {
  long long id;
  std::string_view name;
  static constexpr std::size_t max_depth = 32;                                  // §3, Bounds
  static constexpr std::optional<std::size_t> max_encoded_len = std::nullopt;
  constexpr void to_cbor(::taut::Buf& __b) const;  // __b.map(2); __b.uint(1); … __b.uint(2); …
  static constexpr ::taut::DecodeResult<::taut::User> try_from_cbor(const ::taut::Cbor& __c);
  static constexpr ::taut::DecodeResult<::taut::User> try_decode(std::string_view __data);
};
```

The generated code names its own parameters and locals with `__`, which C++ reserves, and
qualifies every name it takes from outside the struct `::taut::`, so a field may have any
name but a keyword or a member's (`to_cbor`, `try_from_cbor`, `try_decode`, `max_depth`,
`max_encoded_len`); `wire_` is taut's.

Field mapping: `INT → long long`, `STR/BYTES → std::string_view`, `BOOL → bool`,
`FLOAT → double`, `List(T) → std::vector<T>`, `Map(K,V) → std::map<K,V>`. **Optional**
fields are `std::optional<T>` (encoded as CBOR `null` when empty). **Transient** fields are
in the struct but never on the wire (value-initialized, left default on decode).

## 3. Encode / decode

`to_cbor(Buf&)` writes bytes into a fixed `Buf` (encode is compile-time); the message's
`try_decode(std::string_view)` reads them back. Decode is fail-closed: it returns a
`DecodeResult<T>`, the value or a `DecodeError` with its tag and payload, and nothing else
escapes, whatever the bytes:

```cpp
taut::Buf b; task.to_cbor(b);                    // serialize into b.d[0..b.n)
auto back = taut::Task::try_decode(std::string_view(reinterpret_cast<const char*>(b.d), b.n));
if (back) { use(back.value); } else { report(back.error); }  // explicit bool
```

**Bounds.** A message's `try_decode` applies its bounds as the call's root, the schema's
`max_depth` and `max_encoded_len` options (the message's, else the file's), which the
struct carries: `max_depth` is 32 unless declared and 128 at most, `max_encoded_len`
`std::nullopt` unless declared. An array or map one deeper than `max_depth` is
`TooDeep{limit}`, even when empty, and input longer than `max_encoded_len` is
`TooLarge{len, limit}` before a byte is read; a message nested inside changes neither.
The two-step form, the raw `taut::try_decode` then `try_from_cbor(const Cbor&)`, applies
the raw decode's defaults instead (§4).

The raw `try_decode` is constexpr, and so are a message's `try_decode` and `try_from_cbor`
when it holds no `std::map`, so the corpus decodes each golden vector back at compile time
too.

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

inline constexpr std::size_t default_max_depth = 32;   // the raw decode's depth bound
inline constexpr std::size_t max_depth_ceiling = 128;  // the deepest bound any call applies

// bytes -> tree, or a DecodeError, under the bounds the caller passes
constexpr DecodeResult<Cbor> try_decode(std::string_view d, std::size_t max_depth = default_max_depth,
                                        std::optional<std::size_t> max_encoded_len = std::nullopt);
constexpr void encode_value(Buf& b, const Cbor& c);  // tree -> bytes (canonical)
```

The raw `try_decode` knows no schema, and serves schema-blind carriers and the generated
code. A `max_depth` above the ceiling applies the ceiling, and `TooDeep`'s `limit` names
the bound applied; a `max_depth` of 0 is the caller's error and throws
`std::invalid_argument`.

Accessors, each the value or a `DecodeError`: `.try_int()`, `.try_text()`, `.try_bytes()`,
`.try_bool()`, `.try_float()`, `.try_array()`, `.try_map()` (`WrongType` otherwise),
`.try_get(key)` (map value by integer key, `MissingKey` when absent), `.try_get_opt(key)`
(nullptr when absent); and `.is_null()`. `Text`/`Bytes` are `string_view` slices **into the
decoded source** — keep that buffer alive while they're read.

## 5. Forward-compatibility (unknown-field preservation)

Generate with `--forward-compat` and each struct gains
`std::vector<std::pair<long long, Cbor>> wire_residual`. On `try_from_cbor`, keys the struct
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
DecodeResult<std::vector<unsigned char>> ext_set(std::string_view host, long long tag, const Cbor& value);
DecodeResult<std::optional<Cbor>>        ext_get(std::string_view host, long long tag);  // nullopt if absent
DecodeResult<std::vector<unsigned char>> ext_clear(std::string_view host, long long tag);
```

`value` is the extension message as a `Cbor` (encode it, then `try_decode`); decode
`ext_get`'s result with `ExtMsg::try_from_cbor()`:

```cpp
taut::Buf eb; decision.to_cbor(eb);
auto value = taut::try_decode(std::string_view(reinterpret_cast<const char*>(eb.d), eb.n));
auto raw = taut::ext_set(host, 0x100001, value.value);          // check `value` and `raw`
std::string_view hv(reinterpret_cast<const char*>(raw.value.data()), raw.value.size());
auto got = taut::ext_get(hv, 0x100001);
if (got && got.value) { auto d = taut::Decision::try_from_cbor(*got.value); }
auto stripped = taut::ext_clear(hv, 0x100001);
```

They fail closed: for any host bytes each returns its result or a `DecodeError`, and a host
that is not a map is `WrongType{map}`. Not knowing the host's root, they read it at the
depth ceiling, 128, with no length bound, leaving the host's own bounds to its reader. A below-band `tag` is the caller's error: it throws
`std::invalid_argument` before the host is read. The host app decodes its own message
obliviously — the extension rides in `wire_residual` and survives.
`ext_get`'s `Cbor` holds `string_view`s into `host` — keep the host bytes alive until it's
decoded into an owning/typed value.

## 7. Consuming the runtime

`taut/cbor.hpp` / `taut/ext.hpp` are vendored, dependency-free, header-only source — drop
them under an include root and `#include "taut/cbor.hpp"`; `api.hpp` already does.
`-std=c++20` is the only toolchain requirement. The bytes match every other taut target.
