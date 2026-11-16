# Replaceable bigint bindings

Taut defines serialization, not an arithmetic implementation. Its adapter
interfaces have no knowledge of an application's bigint library. The names
`CustomerBigInt` and `CustomerBigIntAdapter` below are examples: replace them
with your own type and binding.

Declare `BIGINT` fields in the schema. Python, JavaScript/TypeScript, Go and
Java use native arbitrary-precision types. C++, Rust, Swift and Kotlin use
`BigIntValue`, a serialization carrier with no arithmetic operations.

## C++ adapter API

Include the generated `taut/cbor.hpp` and your own adapter header. The adapter
must provide these static operations:

```cpp
struct CustomerBigIntAdapter {
    using value_type = CustomerBigInt;
    static bool is_negative(const value_type& value);
    static std::vector<std::uint8_t> magnitude(const value_type& value);
    static value_type from_magnitude(
        bool negative, std::span<const std::uint8_t> magnitude);
};

auto wire_value = taut::BigIntValue::from<CustomerBigIntAdapter>(integer);
auto integer_again = wire_value.to<CustomerBigIntAdapter>();
```

`magnitude` exports unsigned big-endian bytes with no leading zero; zero is an
empty sequence and is never negative. `from_magnitude` constructs your native
value from that same convention. Taut handles tag 3's subtract-one adjustment;
your adapter must not apply that adjustment itself. Conversion is by value:
input values must not be mutated, and adapters must not retain the borrowed
input span after the call.

The compilable `CustomerBigIntAdapter.hpp` demonstrates the interface using a
small sign-and-magnitude stand-in. That stand-in is not an arithmetic library
and is not a recommendation for representing your application's integers.
Replace its calls with your chosen library's import/export operations.
`Buf::encoded_bytes()` returns complete output, including data beyond its
512-byte inline region.

## Rust

Implement `cbor::BigIntAdapter`, with associated `Value` and operations
`is_negative(&Value)`, `magnitude(&Value) -> Vec<u8>` and
`from_magnitude(bool, &[u8]) -> Value`. Use
`BigIntValue::from_adapter::<CustomerBigIntAdapter>(&integer)` and
`value.to_adapter::<CustomerBigIntAdapter>()`. Import the same canonical
sign-and-magnitude format described above; do not retain the borrowed bytes.

The optional foundation Cargo feature `num-bigint` provides
`NumBigIntAdapter` for `num_bigint::BigInt`. Default features remain empty.

## Kotlin

Implement `BigIntAdapter<T>`: `isNegative(value)`, `magnitude(value)` and
`fromMagnitude(negative, magnitude)`. Use `BigIntValue.from(integer, adapter)`
and `value.to(adapter)`. Byte arrays use the same unsigned byte convention;
their Kotlin `Byte` elements are signed carriers of those octets.

`JvmBigIntAdapter` binds `java.math.BigInteger`. The interface and carrier do
not name Java types; the separately named JVM adapter does. A Native binding
can replace it, but no Kotlin Native generator is added.

## Swift

Implement `BigIntAdapter` with associated `Value` and static operations
`isNegative(_:)`, `magnitude(_:) -> [UInt8]` and
`fromMagnitude(negative:bytes:) -> Value`. Use:

```swift
let wireValue = try BigIntValue.from(integer, using: CustomerBigIntAdapter.self)
let integerAgain = wireValue.value(using: CustomerBigIntAdapter.self)
```

The example `CustomerBigIntAdapter.swift`, `CustomerBigIntBridge.hpp` and
module map demonstrate a replaceable C++ binding. Compile with
`-cxx-interoperability-mode=default -Xcc -std=c++23`, the example include path
and Taut's `cbor.swift`. The example accepts canonical magnitudes; C++ exceptions
must not cross a Swift call boundary. A real binding should implement its
factory with the error behavior appropriate to its native library.

## Tests

```sh
PYTHONPATH=src pytest src/tests/test_bigint_adapters.py -q
```

The C++ and Swift examples require their compilers and no external customer
library. The Rust optional binding proof requires Cargo and access to its
crate dependency. Missing toolchains are reported as skips. Ordinary schemas
add no external bigint dependency.
