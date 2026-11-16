# Arbitrary-precision integer support

Owner direction, 16 November 2026: add bigint support to taut, keeping the
arithmetic implementation replaceable. This is implementation work, not a
release request. Existing signed-64-bit INT schemas keep their meaning.

## Contract

- Add a distinct BIGINT scalar. It carries an arbitrary signed integer and
  never silently converts through float or the existing INT carrier.
- Encode BIGINT using CBOR tag 2 (nonnegative) or tag 3 (negative), followed
  by an unsigned big-endian byte string. For a negative value x, the encoded
  unsigned argument is -1-x, not abs(x). Empty argument bytes encode zero for
  tag 2 and minus one for tag 3; reject redundant leading zero bytes.
- The schema explicitly requires the tagged form even for small BIGINT values.
  This deterministic application profile preserves the distinction from INT.
- Decode validates the wire before a normalizing arithmetic-library factory.
  Other tags remain unsupported. Tagged values cannot become raw map field tags.
- Existing ordinary integer overflow checks, bounds and error precedence remain
  intact outside the newly supported tag-2/tag-3 inputs.
- Taut owns serialization and bindings, not an arithmetic implementation.
  Binding operations need sign and canonical magnitude import/export only.
  The codec handles the negative CBOR offset and never mutates a caller value.

## Bindings

| Target | Arithmetic binding |
| --- | --- |
| Python | built-in int |
| JavaScript, TypeScript | native bigint; never Number for BIGINT |
| Go | standard-library math/big.Int |
| Java, Kotlin/JVM | standard-library java.math.BigInteger |
| C++ | templated customer-supplied adapter |
| Rust | trait adapter; optional num-bigint binding |
| Swift | replaceable adapter; a C++ BigInt wrapper is a candidate to prove |

Kotlin's common bigint boundary must not name Java classes. A JVM implementation
can use BigInteger; a Native implementation can replace it. This does not add
a Kotlin Native generator or claim Native support. Schemas that do not use
BIGINT must not acquire a bigint dependency. C++/Rust/Swift arithmetic packages
remain optional rather than becoming unconditional taut dependencies.

## Acceptance

Use shared byte-exact vectors across bindings: zero, minus one, positive and
negative small numbers, 64-bit boundaries, powers of two and their neighbours,
large positive/negative values, nested/optional/list fields, malformed tags,
wrong tag content, nonminimal arguments, redundant zeros, truncation, bounds,
and a tagged bigint used as a raw map key. Preserve ordinary INT refusals.
Verify host encode/decode and byte re-encode, not only a raw CBOR reader.
Run the existing parity gate as a regression and add bigint parity evidence.
Missing toolchains or arithmetic bindings must be reported, never counted as
successful coverage. No release/tag/registry publication is authorized here.

## Implemented and verified

Implemented in the compiler, IR v4 reader/exporter, generated model projections,
metadata, validation and the nine CBOR runtimes. Ordinary INT remains signed
64-bit. Python/TypeScript JSON codecs use exact decimal strings; Python's
implementation also round-trips values exceeding its default decimal-digit
conversion limit without changing a process-global setting.

Generated C++, Rust, Swift and Kotlin fields use `BigIntValue` carriers. Arithmetic
conversion is explicit through the replaceable adapters described above. The
C++ example uses a generic customer value stand-in. Swift's thin C++ bridge compiled
and round-tripped on Swift 6.4.2, Linux x86_64. Kotlin Native is not implemented.
No macOS, Windows-native or ARM toolchain run is claimed by this validation.

Validation environment: WSL, Ubuntu 26.04, Linux x86_64.

- Complete test selection: 2,581 passed, 66 explicitly skipped, zero failures.
  TypeScript integration tests ran sequentially because their shared fixture
  builds the sibling shape package. Remaining tests ran with four workers.
- `tautc parity --require-all`: all nine language targets and seven generated
  forward-compatible variants GREEN, no missing toolchain. Each variant replays
  134 rows including 46 BIGINT rows. Static carriers satisfy three legacy
  out-of-range encode cases by type; these are not missing toolchain skips.
- Eight adapter checks passed, covering Java, Kotlin/JVM, Go,
  JavaScript, TypeScript, C++/customer adapter, Rust/num-bigint and Swift/C++/customer adapter.
  Values include both signs, zero and magnitudes above 8,000 bits.
- The TypeScript shape member's canonical foundation was refreshed using its
  `scripts/vendor-foundation.py`; its provenance records exact source hashes.

Tool versions: Python 3.14.4, Rust 1.95.0, Node 24.20.0, TypeScript 7.0.2,
Go 1.26.8, Swift 6.4.2, Clang 18.1.8 with libstdc++ 13, OpenJDK 25.0.5.0.3,
Kotlin/JVM 2.4.21 and pnpm 12.21.0. These versions record the tested
configuration; they do not prescribe installation locations. In WSL, select
Linux-native tools rather than inheriting Windows executables such as `npm.cmd`.
The TypeScript finder now probes a real typed file, detecting distro Node builds
that accept the stripping flag but omit the TypeScript subsystem.

Reproduce with the required language toolchains, pytest and pytest-xdist available
on PATH:

```sh
export PYTHONPATH=src
pytest src/tests -q -n 4 -m 'not gate' \
  --ignore=src/tests/test_typescript_oneof.py \
  --ignore=src/tests/test_typescript_review_closure.py \
  --ignore=src/tests/test_ts.py
pytest src/tests/test_typescript_oneof.py \
  src/tests/test_typescript_review_closure.py src/tests/test_ts.py -q
python -m taut.cli parity --require-all
python rust/sync_foundation.py --check
```

The suite's conditional/platform skips remain explicit; the required
nine-language parity run has no unavailable target.

The customer examples are deliberately application-independent. Their stand-in
value demonstrates sign/magnitude transport, not arithmetic. Taut contains no
binding, dependency or naming for an application-specific bigint library.

## Sibling package validation

The Python, Rust and TypeScript shape-package suites and live cross-language
matrix have also been exercised against this runtime. See
[BigIntSiblingValidation.md](BigIntSiblingValidation.md) for counts, packaged
consumer checks, the Rust error-formatter correction, 0.12 metadata preparation and the remaining
publication gates. Passing the functional suites does not clear the separate
coordinated release gate.
