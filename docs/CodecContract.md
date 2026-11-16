# taut's codec contract

Every language taut generates a codec for implements one contract:
rust, python, typescript, js, cpp, swift, go, kotlin and java.
A codec is taut's until it passes the shared corpus in `tautc parity`, and a codec that passes it
gives the same result as the other eight for the same bytes. This page states the contract. The
decisions behind it are D1, D2, D26 and D27 in `dev-docs/TautDecisions.md`, and the gate that
enforces it is `taut-codec-parity/i64/v1`.

## 1. Two invariants

1. **Ordinary `INT` values are exactly `i64`.** Every value in `[-2^63, 2^63 - 1]` round-trips unchanged.
   - A received CBOR int outside that range is `IntOverflow`.
   - A native value outside it is `IntOutOfSubset` on encode. That applies only where a native
     integer can hold it: Python's `int`, and TypeScript's and JavaScript's `bigint`.
2. **Decode is fail-closed.** Every decode entry point returns a value or a `DecodeError`. It
   never panics, aborts, overflows its stack or throws anything else, whatever the input.

## 2. The error

Each runtime has one error type, `DecodeError`, in its own idiom:
- Rust returns `Result<_, DecodeError>`.
- Python raises `DecodeError(ValueError)`.
- TypeScript and JavaScript throw it.
- Go returns `*DecodeError`.
- Swift throws `CborError`.
- Kotlin and Java throw it.
- C++ returns a `DecodeResult`.

The tag and its payload are the contract. Display text is not. The gate compares payload values
as text:

| Tag | Payload | Meaning |
|---|---|---|
| `Truncated` | | the input ends inside an item, or a length or count runs past it |
| `TrailingBytes` | | bytes after the top-level item |
| `InvalidUtf8` | | text that is not UTF-8 |
| `UnsupportedInfo` | `info` | additional info 28-31, or a major-7 value other than false, true, null and the three floats |
| `UnsupportedMajor` | `major` | major type 6 except the supported one-byte bigint tags `c2` and `c3` |
| `NonCanonicalBigInt` | | redundant leading zero bytes in a tagged bigint argument |
| `NonCanonicalInt` | `value` | an argument longer than needed (the raw argument) |
| `IntOverflow` | `value` | an int outside `i64` (Rust's variant carries no value) |
| `NonIntegerMapKey` | | a raw map key that is not an int |
| `NegativeMapKey` | `key` | a raw map key below 0 |
| `DuplicateMapKey` | `key` | a repeated raw map key or `map<K,V>` key, as text: an int in decimal, a str as itself, a bool as `true` or `false` |
| `MissingKey` | `key` | an absent field, unless it is `optional=MISSING_OK` |
| `WrongType` | `expected` | one of `int`, `bigint`, `float`, `bytes`, `text`, `bool`, `array`, `map` |
| `UnknownEnum` | `enum`, `value` | a value the enum does not name |
| `TooDeep` | `limit` | an array or map one level deeper than the bound |
| `TooLarge` | `len`, `limit` | input longer than the length bound |

## 3. One order of checks

Decode reads left to right and reports the first check that fails:

1. **Length.** Where a length bound applies, input longer than it is `TooLarge`, before any byte
   is read.
2. **Each item's head.**
   - No byte left is `Truncated`.
   - Major type 6 is `UnsupportedMajor`, except `c2` and `c3` (§8).
   - Unsupported additional info is `UnsupportedInfo`.
   - Missing argument bytes are `Truncated`.
   - A non-minimal argument is `NonCanonicalInt`.
3. **Its body.**
   - An int outside `i64` is `IntOverflow`.
   - A byte or text length beyond the input is `Truncated`, whatever its size.
   - Bad UTF-8 is `InvalidUtf8`.
   - An array or map one level too deep is `TooDeep`, before any of its items.
   - Items are read in order.
   - A map entry reads its key first: the key item, then `NonIntegerMapKey`, `NegativeMapKey`
     and `DuplicateMapKey`, then the value.
4. **Trailing bytes.** Anything after the top-level item is `TrailingBytes`.
5. **The schema stage.**
   - A message must be a map, even one with no fields.
   - Fields are checked in IR order.
   - An absent field is `MissingKey`, unless it is `optional=MISSING_OK`, which reads it as null.
   - A present null is null for an optional field.
   - A wrong CBOR type is `WrongType`, and an unknown enum value is `UnknownEnum`.
   - A `map<K,V>` entry checks for keys 1 and 2 before decoding either.

## 4. Strict-canonical decode (D2)

The decoder accepts only what the canonical encoder could write: minimal integer arguments, raw
map keys that are non-negative ints, and no repeated key. Encode then decode then encode returns
the same bytes, with three known exceptions:
- A field read under `optional=MISSING_OK` without its key re-encodes with the key, as null.
- A codec that drops unknown fields re-encodes without them (§6).
- Floats wider than needed, and out-of-order map keys, are accepted and re-encoded canonically.
  This is TautCheckedDecode.md G2, whose follow-up comes after v0.10.0.

## 5. Bounds

- **Depth.** A decode call is bounded by its root's `max_depth`: the root message's option, else
  the file's, else 32. The bound is never above the ceiling of 128.
  - A top-level array or map has depth 1.
  - A container one deeper than the bound is `TooDeep{limit}`.
- **Length.** A root's `max_encoded_len` bounds the input's length. It has no default; declared
  values are at most 2^31 − 1.
- **One bound per call.** A call's bounds are its root's for the whole input. A message nested
  inside does not change them.
- **Typed decode.** It takes no bounds argument: every reader of one root applies the same bounds,
  in every language.
- **Raw decode.** It knows no schema. It applies depth 32 and no length bound, unless its caller
  passes bounds. A depth above 128 is capped.
- **Extension helpers.** They read a host at the ceiling, with no length bound.

## 6. Unknown fields

Python's and TypeScript's codecs keep a message's unknown fields and write them back. A generated
codec does the same when generated with `--forward-compat`, and otherwise drops them. The corpus
states both outcomes where they differ (`expect_dropping`). The gate runs each generated target
both ways: plain, and as `<target>/fc`.

## 7. The corpus and the gate

- `corpus/parity/int.vectors.json`: the `i64` range, round trips and encode refusals.
- `corpus/parity/malformed.vectors.json`: malformed input, the order of checks, payload words,
  `MISSING_OK`, every legal field shape (`Shapes`), repeated keys, unknown fields, and field names
  that collide with generated names (`Names`).
- `corpus/parity/bounds.vectors.json`: depth and length at their defaults, at declared values, at
  the ceiling, and the root rule. Its header carries `default_max_depth` and `max_depth_ceiling`,
  which every runtime's constants must equal.

`tautc parity` replays every row through every target, and through the seven generated targets'
forward-compat builds. It compares tag and payload. It checks that a row that decodes re-encodes
to its expected bytes, and that a typed row resolved its root's bounds.

A target is **gated** unless `corpus/parity/allowlist.json` lists it with a reason. The gate fails
when a gated target fails, or when a listed target passes. A missing toolchain skips its target,
with the reason, except under `tautc parity --require-all`: there a target that does not run fails
the gate, and a release runs it that way (`RELEASE.md`). A failed build or a runner that exits
non-zero fails its target.

## 8. What is outside

- The delivery-shape packages (`taut-shape-*`) sit above this contract and vendor its runtimes.
- The legacy codec that D1 retired, `--legacy-codec` and its panicking runtime, is gone as of
  v0.10.0.

## 8. Arbitrary-precision `BIGINT` (IR version 4)

`BIGINT` is a separate scalar; it does not widen `INT`. Its CBOR representation
is tag 2 (`c2`) for a nonnegative value n, or tag 3 (`c3`) for a negative value
-1-n, followed by a definite-length byte string containing n as minimal unsigned
big-endian bytes. Empty bytes encode zero under tag 2 and minus one under tag 3.
Leading zero bytes are `NonCanonicalBigInt`; a nonminimal byte-string length is
`NonCanonicalInt`. Missing tag content is `Truncated`; non-byte-string content
is `WrongType(expected=bytes)`. Other tag heads, including `d8 02`, retain
`UnsupportedMajor(6)` precedence. A tagged value used as a raw map key is
`NonIntegerMapKey` after its body has been checked.

This application profile always tags `BIGINT`, including small values, so an
ordinary CBOR integer is `WrongType(expected=bigint)` in a bigint field and a
tagged integer is `WrongType(expected=int)` in an `INT` field. This makes typed
decode/re-encode byte exact. It is an explicit profile over
[RFC 8949 section 3.4.3](https://www.rfc-editor.org/rfc/rfc8949.html#section-3.4.3),
whose generic preferred form uses ordinary integer heads for small numbers.

Lists, optional fields and map values support `BIGINT`; schema map keys remain
`INT`, `STR` or `BOOL`. Existing bounds apply before copying a magnitude. Tag
content is a byte string, so tags add no container nesting. The JSON profile
uses canonical decimal strings (`0` or an optional minus and nonzero first
digit), never floating-point JSON numbers.

Python uses `int`; JavaScript/TypeScript use `bigint`; Java uses `BigInteger`;
Go uses `math/big.Int`. Generated C++, Rust, Swift and Kotlin fields use a
`BigIntValue` serialization carrier with replaceable sign/magnitude adapters.
Kotlin provides the JVM `BigInteger` adapter; Rust's `num-bigint` feature is
opt-in. Taut has no arithmetic implementation dependency by default. See
[the adapter examples](../examples/bigint/README.md) for C++ and Swift.

The shared `corpus/parity/bigint.vectors.json` is replayed alongside the frozen
i64 corpus by `tautc parity --require-all`.
