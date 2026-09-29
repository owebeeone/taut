"""C++ runner for the parity gate (see `parity_rust.py` for the shape).

C++ keeps its constexpr corpus for the encode goldens (`gen/cpp.py`); constexpr
cannot host a fallible decode, so the gate replays the rows through a small
runtime binary instead: the generated `api.hpp` over the vendored `taut/cbor.hpp`,
built with the compiler and flags `src/tests/test_cpp.py` uses. A build failure is
RED; a runner that dies before reporting every row fails its target.

The runner prints `name<TAB>outcome<TAB>detail` per row. It checks int rows itself;
for a malformed row it reports `ok`, `err` with the tag and payload, or `untyped`
when a C++ exception escapes, and the gate judges it.
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
struct Mal { const char* name; const char* stage; const char* schema; const char* bytes; };

const std::vector<IntRow> ROUND_TRIP = {
@ROUND_TRIP@
};
const std::vector<EncFail> ENCODE_FAIL = {
@ENCODE_FAIL@
};
const std::vector<Mal> MALFORMED = {
@MALFORMED@
};

using Outcome = std::optional<taut::DecodeError>;  // nullopt: decoded

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

void emit(std::string_view name, std::string_view outcome, std::string detail) {
    for (char& ch : detail) {
        if (ch == '\t' || ch == '\n' || ch == '\r') {
            ch = ' ';
        }
    }
    std::cout << name << '\t' << outcome << '\t' << detail << '\n';
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
    }
    throw std::logic_error("a DecodeError tag this runner does not report");
}

template <class Result>
Outcome outcome(const Result& r) {
    if (!r) {
        return r.error;
    }
    return std::nullopt;
}

// A from_cbor row's typed entry point, by message name (from the fixture schema).
Outcome from_cbor(std::string_view message, const taut::Cbor& c) {
@FROM_CBOR@
    throw std::invalid_argument("no from_cbor entry point for " + std::string(message));
}

// A from_wire row's typed entry point, by enum name (from the fixture schema).
Outcome from_wire(std::string_view name, long long v) {
@FROM_WIRE@
    throw std::invalid_argument("no from_wire entry point for " + std::string(name));
}

Outcome decode_row(const Mal& row) {
    std::string bytes = unhex(row.bytes);
    auto c = taut::try_decode(std::string_view(bytes));
    if (!c) {
        return c.error;
    }
    std::string_view stage(row.stage);
    if (stage == "raw_decode") {
        return std::nullopt;
    }
    if (stage == "from_cbor") {
        return from_cbor(row.schema, c.value);
    }
    if (stage == "from_wire") {
        auto v = c.value.try_int();
        if (!v) {
            return v.error;
        }
        return from_wire(row.schema, v.value);
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
    auto c = taut::try_decode(std::string_view(wire));
    if (!c) {
        emit(row.name, "fail", "decode " + describe(c.error));
        return;
    }
    auto d = taut::IntBox::try_from_cbor(c.value);
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
    for (const auto& row : MALFORMED) {
        try {
            Outcome error = decode_row(row);
            if (error) {
                emit(row.name, "err", describe(*error));
            } else {
                emit(row.name, "ok", "");
            }
        } catch (const std::exception& e) {
            emit(row.name, "untyped", std::string("exception: ") + e.what());
        } catch (...) {
            emit(row.name, "untyped", "a non-standard exception");
        }
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


def _tables() -> tuple[str, str, str]:
    round_trip, encode_fail, malformed = [], [], []
    for row in parity.int_rows():
        if row["kind"] == "round_trip":
            pairs = ", ".join(f"{{{_cxx(k)}, {_cxx(v)}}}" for k, v in row["value"]["by_id"])
            round_trip.append(f"    {{{_cxx(row['name'])}, {_cxx(row['cbor'])}, "
                              f"{_cxx(row['value']['n'])}, {{{pairs}}}}},")
        else:
            encode_fail.append(f"    {{{_cxx(row['name'])}, {_cxx(row['value']['n'])}}},")
    for row in parity.malformed_rows():
        malformed.append(f"    {{{_cxx(row['name'])}, {_cxx(row['stage'])}, "
                         f"{_cxx(row.get('schema', ''))}, {_cxx(row['bytes'])}}},")
    return "\n".join(round_trip), "\n".join(encode_fail), "\n".join(malformed)


def _dispatch() -> tuple[str, str]:
    """The arms for every message (`from_cbor`) and enum (`from_wire`) in the fixture."""
    dispatch = parity.fixture_dispatch()
    from_cbor = [f"    if (message == {_cxx(name)}) {{\n"
                 f"        return outcome(taut::{name}::try_from_cbor(c));\n"
                 f"    }}"
                 for name in dispatch.messages]
    from_wire = [f"    if (name == {_cxx(name)}) {{\n"
                 f"        return outcome(taut::{_try_enum_fn(name)}(v));\n"
                 f"    }}"
                 for name in dispatch.enums]
    return "\n".join(from_cbor), "\n".join(from_wire)


def _source() -> str:
    round_trip, encode_fail, malformed = _tables()
    from_cbor, from_wire = _dispatch()
    return (_MAIN
            .replace("@ROUND_TRIP@", round_trip)
            .replace("@ENCODE_FAIL@", encode_fail)
            .replace("@MALFORMED@", malformed)
            .replace("@FROM_CBOR@", from_cbor)
            .replace("@FROM_WIRE@", from_wire))


def run() -> parity.TargetReport:
    cxx = toolchains.find_cxx()
    if cxx is None:
        return parity.skipped(TARGET, "no C++ compiler (c++, clang++ or g++) found")
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        failed = parity.generate(TARGET, work, runtime=True)
        if failed is not None:
            return failed
        runner = work / "parity_runner.cpp"
        runner.write_text(_source())
        binary = work / "parity_runner"
        failed = parity.build(TARGET, [cxx, "-std=c++20", "-I", str(work / TARGET), str(runner),
                                       "-o", str(binary)], cwd=work)
        if failed is not None:
            return failed
        return parity.run_runner(TARGET, [str(binary)], cwd=work)
