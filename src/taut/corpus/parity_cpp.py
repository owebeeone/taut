"""C++ runner for the parity gate (see `parity_rust.py` for the shape).

C++ keeps its constexpr corpus for the golden vectors (`gen/cpp.py`); a static_assert
cannot report a row's outcome, so the gate replays the rows through a small
runtime binary instead: the generated `api.hpp` over the vendored `taut/cbor.hpp`,
built with the compiler and flags `src/tests/test_cpp.py` uses. A build failure is
RED; a runner that dies before reporting every row fails its target.

The runner prints `name<TAB>outcome<TAB>detail` per row. It checks int rows itself;
for a malformed or bounds row it reports `ok` with the hex of the re-encoding
(`encode_value` of the tree for a raw row, the typed value's `to_cbor` for a from_cbor
row), `err` with the tag and payload, or `untyped` when a C++ exception escapes, and the
gate judges it.

It speaks C3's bounds protocol (`parity.py`'s docstring): one `#constants` line from the
runtime's `taut::default_max_depth` and `taut::max_depth_ceiling`; a raw row's call
passes its `limits`; every from_cbor row decodes through its message's `try_decode` from
bytes, which applies the message's bounds, and adds the fourth column from the message's
`max_depth` and `max_encoded_len`; and the runner expands a row's segments itself,
reporting an expansion whose length is not the row's `len` as `untyped`.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from ..gen.cpp import _try_enum_fn
from . import parity, toolchains

TARGET = "cpp"

_MAIN = r'''
#include "api.hpp"

#include <charconv>
#include <cstdint>
#include <exception>
#include <iostream>
#include <limits>
#include <map>
#include <optional>
#include <stdexcept>
#include <string>
#include <string_view>
#include <system_error>
#include <utility>
#include <vector>

namespace {

struct IntRow {
    const char* name;
    const char* cbor;
    const char* n;
    std::vector<std::pair<const char*, const char*>> by_id;
};
struct EncFail { const char* name; const char* value; };
// A row's bytes, `count` times `hex` per segment (the bounds protocol, item 5).
struct Segment { const char* hex; std::size_t count; };
// A malformed or bounds row: its expanded length when it states one, and a raw row's limits,
// what its call passes.
struct Row {
    const char* name;
    const char* stage;
    const char* schema;
    std::vector<Segment> bytes;
    std::optional<std::size_t> len;
    std::optional<std::size_t> max_depth;
    std::optional<std::size_t> max_encoded_len;
};

const std::vector<IntRow> ROUND_TRIP = {
@ROUND_TRIP@
};
const std::vector<EncFail> ENCODE_FAIL = {
@ENCODE_FAIL@
};
const std::vector<Row> DECODE_ROWS = {
@DECODE_ROWS@
};

// A decode row's outcome: `ok` with the hex of the re-encoding (empty for a from_wire row:
// an enum row never accepts), `err` with its DecodeError described, or `untyped`; and a
// from_cbor row's fourth column, the bounds its typed entry point resolved.
struct Outcome {
    std::string outcome;
    std::string detail;
    std::optional<std::string> bounds;
};

int nibble(char c) {
    if (c >= '0' && c <= '9') {
        return c - '0';
    }
    if (c >= 'a' && c <= 'f') {
        return c - 'a' + 10;
    }
    if (c >= 'A' && c <= 'F') {
        return c - 'A' + 10;
    }
    throw std::invalid_argument("bad hex digit");
}

std::string unhex(std::string_view hex) {
    std::string out;
    for (std::size_t i = 0; i + 1 < hex.size(); i += 2) {
        out.push_back(static_cast<char>((nibble(hex[i]) << 4) | nibble(hex[i + 1])));
    }
    return out;
}

std::string hexof(const taut::Buf& b) {
    static constexpr char digits[] = "0123456789abcdef";
    std::string out;
    for (std::size_t i = 0; i < b.n; ++i) {
        out.push_back(digits[b.d[i] >> 4]);
        out.push_back(digits[b.d[i] & 0x0f]);
    }
    return out;
}

// A decimal integer: its value, or nullopt when it does not fit long long.
std::optional<long long> parse_i64(std::string_view s) {
    long long v = 0;
    auto [end, ec] = std::from_chars(s.data(), s.data() + s.size(), v);
    if (ec == std::errc::result_out_of_range) {
        return std::nullopt;
    }
    if (ec != std::errc() || end != s.data() + s.size()) {
        throw std::invalid_argument("not a decimal integer: " + std::string(s));
    }
    return v;
}

long long pi(std::string_view s) {
    auto v = parse_i64(s);
    if (!v) {
        throw std::invalid_argument("outside long long: " + std::string(s));
    }
    return *v;
}

std::string flat(std::string column) {
    for (char& ch : column) {
        if (ch == '\t' || ch == '\n' || ch == '\r') {
            ch = ' ';
        }
    }
    return column;
}

void emit(std::string_view name, std::string_view outcome, std::string detail) {
    std::cout << name << '\t' << outcome << '\t' << flat(std::move(detail)) << '\n';
}

void emit(std::string_view name, const Outcome& seen) {
    std::cout << name << '\t' << seen.outcome << '\t' << flat(seen.detail);
    if (seen.bounds) {
        std::cout << '\t' << *seen.bounds;
    }
    std::cout << '\n';
}

// IntOverflow's value: the decimal integer the bytes denote, `-1 - raw` for major 1.
std::string overflow_value(const taut::DecodeError& e) {
    if (!e.negative_overflow) {
        return std::to_string(e.unsigned_value);
    }
    if (e.unsigned_value == std::numeric_limits<std::uint64_t>::max()) {
        return "-18446744073709551616";  // raw + 1 does not fit uint64_t
    }
    return "-" + std::to_string(e.unsigned_value + 1);
}

std::string text(const char* s) {
    return s == nullptr ? std::string() : std::string(s);
}

// An `err` detail: the tag, then `;field=value` for each payload field it carries.
std::string describe(const taut::DecodeError& e) {
    using T = taut::DecodeErrorTag;
    switch (e.tag) {
        case T::Truncated:
            return "Truncated";
        case T::TrailingBytes:
            return "TrailingBytes";
        case T::InvalidUtf8:
            return "InvalidUtf8";
        case T::UnsupportedInfo:
            return "UnsupportedInfo;info=" + std::to_string(e.info);
        case T::UnsupportedMajor:
            return "UnsupportedMajor;major=" + std::to_string(e.major);
        case T::NonIntegerMapKey:
            return "NonIntegerMapKey";
        case T::IntOverflow:
            return "IntOverflow;value=" + overflow_value(e);
        case T::DuplicateMapKey:
            return "DuplicateMapKey;key=" + (e.key_is_text ? std::string(e.key_text) : std::to_string(e.key));
        case T::MissingKey:
            return "MissingKey;key=" + std::to_string(e.key);
        case T::WrongType:
            return "WrongType;expected=" + text(e.expected);
        case T::UnknownEnum:
            return "UnknownEnum;enum=" + text(e.enum_name) + ";value=" + std::to_string(e.value);
        case T::NonCanonicalInt:
            return "NonCanonicalInt;value=" + std::to_string(e.unsigned_value);
        case T::NegativeMapKey:
            return "NegativeMapKey;key=" + std::to_string(e.key);
        case T::TooDeep:
            return "TooDeep;limit=" + std::to_string(e.limit);
        case T::TooLarge:
            return "TooLarge;len=" + std::to_string(e.len) + ";limit=" + std::to_string(e.limit);
    }
    throw std::logic_error("a DecodeError tag this runner does not report");
}

// The bounds column: `max_depth=<n>;max_encoded_len=<n>`, the length empty where none applies.
std::string bounds_column(std::size_t max_depth, std::optional<std::size_t> max_encoded_len) {
    return "max_depth=" + std::to_string(max_depth) + ";max_encoded_len="
        + (max_encoded_len ? std::to_string(*max_encoded_len) : std::string());
}

// taut::Buf holds 512 bytes and does not check its bound. A re-encoding is never much
// longer than its input (an absent MISSING_OK key adds its null), so an input longer
// than half a Buf is not re-encoded.
constexpr std::size_t REENCODE_INPUT_MAX = sizeof(taut::Buf::d) / 2;

// Described here, while the row's input is alive: a DuplicateMapKey's text key views it.
Outcome failed(const taut::DecodeError& e) {
    return Outcome{"err", describe(e), std::nullopt};
}

Outcome untyped(std::string what) {
    return Outcome{"untyped", std::move(what), std::nullopt};
}

// A decoded input: the hex of its re-encoding, which `encode` writes, unless the input is
// longer than a taut::Buf allows.
template <class Encode>
Outcome decoded(std::size_t input_size, Encode encode) {
    if (input_size > REENCODE_INPUT_MAX) {
        return Outcome{"ok", "not re-encoded: input longer than a taut::Buf allows", std::nullopt};
    }
    taut::Buf again;
    encode(again);
    return Outcome{"ok", hexof(again), std::nullopt};
}

// A typed value: its error, or its own to_cbor.
template <class Result>
Outcome reencoded(const Result& r, std::size_t input_size) {
    if (!r) {
        return failed(r.error);
    }
    return decoded(input_size, [&](taut::Buf& again) { r.value.to_cbor(again); });
}

// An enum: its error, or decoded with no re-encoding.
template <class Result>
Outcome checked(const Result& r) {
    if (!r) {
        return failed(r.error);
    }
    return Outcome{"ok", "", std::nullopt};
}

// One decode: anything but a DecodeError that escapes it is `untyped`.
template <class Decode>
Outcome guarded(Decode decode) {
    try {
        return decode();
    } catch (const std::exception& e) {
        return untyped(std::string("exception: ") + e.what());
    } catch (...) {
        return untyped("a non-standard exception");
    }
}

// A from_cbor row's typed entry point from bytes, which applies M's bounds, and the fourth
// column: the bounds it resolved, M's constants.
template <class M>
Outcome typed(std::string_view bytes, const std::optional<std::string>& misexpanded) {
    Outcome seen = misexpanded ? untyped(*misexpanded)
                               : guarded([&] { return reencoded(M::try_decode(bytes), bytes.size()); });
    seen.bounds = bounds_column(M::max_depth, M::max_encoded_len);
    return seen;
}

// A from_cbor row's typed entry point, by message name (from the fixture schema).
Outcome from_cbor(std::string_view message, std::string_view bytes, const std::optional<std::string>& misexpanded) {
@FROM_CBOR@
    throw std::invalid_argument("no from_cbor entry point for " + std::string(message));
}

// A from_wire row's typed entry point, by enum name (from the fixture schema).
Outcome from_wire(std::string_view name, long long v) {
@FROM_WIRE@
    throw std::invalid_argument("no from_wire entry point for " + std::string(name));
}

// A row's input, its segments expanded by the runner (the bounds protocol, item 5).
std::string expand(const Row& row) {
    std::string out;
    for (const auto& segment : row.bytes) {
        const std::string once = unhex(segment.hex);
        for (std::size_t i = 0; i < segment.count; ++i) {
            out += once;
        }
    }
    return out;
}

Outcome decode_row(const Row& row) {
    const std::string bytes = expand(row);  // outlives the decoded value, whose text views it
    std::optional<std::string> misexpanded;
    if (row.len && bytes.size() != *row.len) {
        misexpanded = "bytes expand to " + std::to_string(bytes.size()) + " bytes, len is "
            + std::to_string(*row.len);
    }
    std::string_view stage(row.stage);
    if (stage == "from_cbor") {
        return from_cbor(row.schema, bytes, misexpanded);
    }
    if (misexpanded) {
        return untyped(*misexpanded);
    }
    if (stage == "raw_decode") {
        return guarded([&] {
            auto c = taut::try_decode(bytes, row.max_depth.value_or(taut::default_max_depth), row.max_encoded_len);
            if (!c) {
                return failed(c.error);
            }
            return decoded(bytes.size(), [&](taut::Buf& again) { taut::encode_value(again, c.value); });
        });
    }
    if (stage == "from_wire") {
        return guarded([&] {
            auto c = taut::try_decode(bytes);
            if (!c) {
                return failed(c.error);
            }
            auto v = c.value.try_int();
            if (!v) {
                return failed(v.error);
            }
            return from_wire(row.schema, v.value);
        });
    }
    throw std::invalid_argument("unknown stage " + std::string(stage));
}

void round_trip(const IntRow& row) {
    std::map<long long, long long> by_id;
    for (const auto& [k, v] : row.by_id) {
        by_id[pi(k)] = pi(v);
    }
    taut::IntBox built{};
    built.n = pi(row.n);
    built.by_id = by_id;
    taut::Buf enc;
    built.to_cbor(enc);
    std::string got = hexof(enc);
    if (got != row.cbor) {
        emit(row.name, "fail", "encode " + got + " != " + row.cbor);
        return;
    }
    std::string wire = unhex(row.cbor);
    auto d = taut::IntBox::try_decode(wire);
    if (!d) {
        emit(row.name, "fail", "decode " + describe(d.error));
        return;
    }
    taut::Buf re;
    d.value.to_cbor(re);
    std::string again = hexof(re);
    if (d.value.n == built.n && d.value.by_id == by_id && again == row.cbor) {
        emit(row.name, "pass", "");
    } else {
        emit(row.name, "fail", "reencode " + again);
    }
}

}  // namespace

int main() {
    std::cout << "#constants\tdefault_max_depth=" << taut::default_max_depth
              << ";max_depth_ceiling=" << taut::max_depth_ceiling << '\n';
    for (const auto& row : ROUND_TRIP) {
        try {
            round_trip(row);
        } catch (const std::exception& e) {
            emit(row.name, "fail", std::string("threw: ") + e.what());
        } catch (...) {
            emit(row.name, "fail", "threw a non-standard exception");
        }
    }
    for (const auto& row : ENCODE_FAIL) {
        // long long is the encode-side subset guard: an out-of-subset value is
        // unrepresentable, so this is satisfied by the type system.
        try {
            if (parse_i64(row.value)) {
                emit(row.name, "fail", "value fits long long but expected out-of-subset");
            } else {
                emit(row.name, "type-satisfied", "unrepresentable in long long");
            }
        } catch (const std::exception& e) {
            emit(row.name, "fail", std::string("threw: ") + e.what());
        }
    }
    for (const auto& row : DECODE_ROWS) {
        emit(row.name, guarded([&] { return decode_row(row); }));
    }
    return 0;
}
'''


def _cxx(value: str) -> str:
    """A C++ string literal; octal escapes (at most three digits) for anything unsafe."""
    out = []
    for byte in value.encode("utf-8"):
        if 0x20 <= byte < 0x7F and chr(byte) not in '"\\?':
            out.append(chr(byte))
        else:
            out.append(f"\\{byte:03o}")
    return '"' + "".join(out) + '"'


def _optional(value: int | None) -> str:
    return "std::nullopt" if value is None else f"std::size_t{{{value}}}"


def _decode_row(row: dict) -> str:
    """A malformed or bounds row as the runner's `Row`: its segments, to expand itself, and
    the `len` and `limits` it states."""
    segments = ", ".join(f"{{{_cxx(hexed)}, {count}}}" for hexed, count in parity.segments(row))
    limits = row.get("limits", {})
    return (f"    {{{_cxx(row['name'])}, {_cxx(row['stage'])}, {_cxx(row.get('schema', ''))}, "
            f"{{{segments}}}, {_optional(row.get('len'))}, {_optional(limits.get('max_depth'))}, "
            f"{_optional(limits.get('max_encoded_len'))}}},")


def _tables() -> tuple[str, str, str]:
    round_trip, encode_fail = [], []
    for row in parity.int_rows():
        if row["kind"] == "round_trip":
            pairs = ", ".join(f"{{{_cxx(k)}, {_cxx(v)}}}" for k, v in row["value"]["by_id"])
            round_trip.append(f"    {{{_cxx(row['name'])}, {_cxx(row['cbor'])}, "
                              f"{_cxx(row['value']['n'])}, {{{pairs}}}}},")
        else:
            encode_fail.append(f"    {{{_cxx(row['name'])}, {_cxx(row['value']['n'])}}},")
    decode = [_decode_row(row) for row in parity.decode_rows()]
    return "\n".join(round_trip), "\n".join(encode_fail), "\n".join(decode)


def _dispatch() -> tuple[str, str]:
    """The arms for every message (`from_cbor`) and enum (`from_wire`) in the fixture."""
    dispatch = parity.fixture_dispatch()
    from_cbor = [f"    if (message == {_cxx(name)}) {{\n"
                 f"        return typed<taut::{name}>(bytes, misexpanded);\n"
                 f"    }}"
                 for name in dispatch.messages]
    from_wire = [f"    if (name == {_cxx(name)}) {{\n"
                 f"        return checked(taut::{_try_enum_fn(name)}(v));\n"
                 f"    }}"
                 for name in dispatch.enums]
    return "\n".join(from_cbor), "\n".join(from_wire)


def _source() -> str:
    round_trip, encode_fail, decode = _tables()
    from_cbor, from_wire = _dispatch()
    return (_MAIN
            .replace("@ROUND_TRIP@", round_trip)
            .replace("@ENCODE_FAIL@", encode_fail)
            .replace("@DECODE_ROWS@", decode)
            .replace("@FROM_CBOR@", from_cbor)
            .replace("@FROM_WIRE@", from_wire))


def run(forward_compat: bool = False) -> parity.TargetReport:
    """The cpp gate, or with `forward_compat` its `cpp/fc` variant (`parity_rust.py`)."""
    name = parity.variant(TARGET, forward_compat)
    cxx = toolchains.find_cxx()
    if cxx is None:
        return parity.skipped(name, "no C++ compiler (c++, clang++ or g++) found")
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        failed = parity.generate(name, work, runtime=True)
        if failed is not None:
            return failed
        runner = work / "parity_runner.cpp"
        runner.write_text(_source())
        binary = work / "parity_runner"
        failed = parity.build(name, [cxx, "-std=c++20", "-I", str(work / TARGET), str(runner),
                                     "-o", str(binary)], cwd=work)
        if failed is not None:
            return failed
        return parity.run_runner(name, [str(binary)], cwd=work)
