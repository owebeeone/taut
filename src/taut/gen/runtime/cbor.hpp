// Compile-time deterministic CBOR — the C++ binding of the frozen wire substrate.
// Everything is constexpr: a value is encoded to bytes *at compile time*, and the
// generated corpus static_asserts the bytes against the golden hex. Same tiny
// subset as the Python/TS/Rust codecs (int, bytes, text, array, int-keyed map,
// bool, null), core-deterministic (shortest ints; maps are emitted in ascending
// key order by the generator). Zero runtime cost; no heap; host-testable.
#pragma once

#include <bit>
#include <cstddef>
#include <cstdint>
#include <limits>
#include <string_view>
#include <utility>
#include <vector>

namespace taut {

constexpr std::uint64_t f64_bits(double v) {
    return std::bit_cast<std::uint64_t>(v);
}

constexpr double f64_from_bits(std::uint64_t bits) {
    return std::bit_cast<double>(bits);
}

constexpr std::uint32_t f32_bits(float v) {
    return std::bit_cast<std::uint32_t>(v);
}

constexpr float f32_from_bits(std::uint32_t bits) {
    return std::bit_cast<float>(bits);
}

constexpr bool f64_is_nan_bits(std::uint64_t bits) {
    return (bits & 0x7ff0000000000000ULL) == 0x7ff0000000000000ULL
        && (bits & 0x000fffffffffffffULL) != 0;
}

constexpr bool f64_is_inf_bits(std::uint64_t bits) {
    return (bits & 0x7fffffffffffffffULL) == 0x7ff0000000000000ULL;
}

constexpr unsigned long long round_shift_right(unsigned long long v, int shift) {
    if (shift <= 0) return v << -shift;
    if (shift >= 64) return 0;
    unsigned long long q = v >> shift;
    unsigned long long rem = v & ((1ULL << shift) - 1);
    unsigned long long half = 1ULL << (shift - 1);
    if (rem > half || (rem == half && (q & 1ULL) != 0)) ++q;
    return q;
}

struct HalfNarrow {
    std::uint16_t bits{0};
    bool overflow{false};
};

constexpr double half_to_double(std::uint16_t h) {
    std::uint64_t sign = static_cast<std::uint64_t>(h & 0x8000U) << 48;
    unsigned exp = (h >> 10) & 0x1fU;
    unsigned frac = h & 0x03ffU;
    if (exp == 0) {
        if (frac == 0) return f64_from_bits(sign);
        int e = -14;
        while ((frac & 0x0400U) == 0) {
            frac <<= 1;
            --e;
        }
        frac &= 0x03ffU;
        return f64_from_bits(sign
            | (static_cast<std::uint64_t>(e + 1023) << 52)
            | (static_cast<std::uint64_t>(frac) << 42));
    }
    if (exp == 0x1fU) {
        return f64_from_bits(sign
            | 0x7ff0000000000000ULL
            | (static_cast<std::uint64_t>(frac) << 42));
    }
    return f64_from_bits(sign
        | (static_cast<std::uint64_t>(exp + 1008) << 52)
        | (static_cast<std::uint64_t>(frac) << 42));
}

constexpr HalfNarrow narrow_half(double v) {
    std::uint64_t bits = f64_bits(v);
    std::uint16_t sign = static_cast<std::uint16_t>((bits >> 48) & 0x8000U);
    std::uint64_t abs = bits & 0x7fffffffffffffffULL;
    unsigned exp = static_cast<unsigned>((bits >> 52) & 0x7ffU);
    std::uint64_t frac = bits & 0x000fffffffffffffULL;

    if (f64_is_nan_bits(bits)) return {static_cast<std::uint16_t>(sign | 0x7e00U), false};
    if (f64_is_inf_bits(bits)) return {static_cast<std::uint16_t>(sign | 0x7c00U), false};
    if (abs == 0) return {sign, false};
    if (abs > 0x40effc0000000000ULL) return {static_cast<std::uint16_t>(sign | 0x7c00U), true};

    if (exp == 0) return {sign, false}; // non-zero double subnormal is below half range.

    int e = static_cast<int>(exp) - 1023;
    unsigned long long mant = (1ULL << 52) | frac;

    if (e >= -14) {
        int half_exp = e + 15;
        unsigned long long rounded = round_shift_right(mant, 42);
        if (rounded == 0x800ULL) {
            rounded = 0x400ULL;
            ++half_exp;
        }
        if (half_exp >= 31) return {static_cast<std::uint16_t>(sign | 0x7c00U), true};
        return {static_cast<std::uint16_t>(sign | (half_exp << 10) | (rounded & 0x03ffULL)), false};
    }

    unsigned long long rounded = round_shift_right(mant, 28 - e);
    if (rounded == 0) return {sign, false};
    if (rounded >= 0x400ULL) return {static_cast<std::uint16_t>(sign | 0x0400U), false};
    return {static_cast<std::uint16_t>(sign | rounded), false};
}

constexpr bool half_exact(double v, std::uint16_t& bits_out) {
    HalfNarrow h = narrow_half(v);
    bits_out = h.bits;
    return !h.overflow && f64_bits(half_to_double(h.bits)) == f64_bits(v);
}

constexpr bool single_exact(double v) {
    std::uint64_t bits = f64_bits(v);
    if (f64_is_nan_bits(bits)) return false;
    if (f64_is_inf_bits(bits)) return true;
    if ((bits & 0x7fffffffffffffffULL) > 0x47efffffe0000000ULL) return false;
    return f64_bits(static_cast<double>(static_cast<float>(v))) == bits;
}

struct Buf {
    unsigned char d[512]{};
    std::size_t n{0};

    constexpr void push(unsigned char b) { d[n++] = b; }

    constexpr void head(unsigned major, unsigned long long v) {
        unsigned mt = major << 5;
        if (v < 24) {
            push(static_cast<unsigned char>(mt | v));
        } else if (v < 0x100ULL) {
            push(static_cast<unsigned char>(mt | 24));
            push(static_cast<unsigned char>(v));
        } else if (v < 0x10000ULL) {
            push(static_cast<unsigned char>(mt | 25));
            push(static_cast<unsigned char>(v >> 8));
            push(static_cast<unsigned char>(v));
        } else if (v < 0x100000000ULL) {
            push(static_cast<unsigned char>(mt | 26));
            for (int i = 3; i >= 0; --i) push(static_cast<unsigned char>(v >> (i * 8)));
        } else {
            push(static_cast<unsigned char>(mt | 27));
            for (int i = 7; i >= 0; --i) push(static_cast<unsigned char>(v >> (i * 8)));
        }
    }

    constexpr void uint(unsigned long long v) { head(0, v); }
    constexpr void integer(long long v) {
        if (v >= 0) head(0, static_cast<unsigned long long>(v));
        else head(1, static_cast<unsigned long long>(-1 - v));
    }
    constexpr void text(std::string_view s) {
        head(3, s.size());
        for (char c : s) push(static_cast<unsigned char>(c));
    }
    constexpr void bytes(std::string_view s) {
        head(2, s.size());
        for (char c : s) push(static_cast<unsigned char>(c));
    }
    constexpr void float_(double v) {
        std::uint64_t bits = f64_bits(v);
        if (f64_is_nan_bits(bits)) {
            push(0xf9);
            push(0x7e);
            push(0x00);
            return;
        }
        std::uint16_t h = 0;
        if (half_exact(v, h)) {
            push(0xf9);
            push(static_cast<unsigned char>(h >> 8));
            push(static_cast<unsigned char>(h));
            return;
        }
        if (single_exact(v)) {
            std::uint32_t f = f32_bits(static_cast<float>(v));
            push(0xfa);
            for (int i = 3; i >= 0; --i) push(static_cast<unsigned char>(f >> (i * 8)));
            return;
        }
        push(0xfb);
        for (int i = 7; i >= 0; --i) push(static_cast<unsigned char>(bits >> (i * 8)));
    }
    constexpr void boolean(bool b) { push(b ? 0xf5 : 0xf4); }
    constexpr void null_() { push(0xf6); }
    constexpr void array(std::size_t k) { head(4, k); }
    constexpr void map(std::size_t k) { head(5, k); }
};

constexpr unsigned char hex_nibble(char c) {
    return c <= '9' ? static_cast<unsigned char>(c - '0')
                    : static_cast<unsigned char>((c | 0x20) - 'a' + 10);
}

// Compile-time equality of an encoded buffer against a hex string.
constexpr bool eq_hex(const Buf& b, std::string_view hex) {
    if (b.n != hex.size() / 2) return false;
    for (std::size_t i = 0; i < b.n; ++i) {
        unsigned char want = static_cast<unsigned char>((hex_nibble(hex[i * 2]) << 4) | hex_nibble(hex[i * 2 + 1]));
        if (b.d[i] != want) return false;
    }
    return true;
}

constexpr bool eq(const Buf& b, std::string_view bytes) {
    if (b.n != bytes.size()) return false;
    for (std::size_t i = 0; i < b.n; ++i)
        if (b.d[i] != static_cast<unsigned char>(bytes[i])) return false;
    return true;
}

// --- decode: a constexpr CBOR value tree + parser (mirrors cbor.rs) ----------

enum class DecodeErrorTag {
    Truncated,
    TrailingBytes,
    InvalidUtf8,
    UnsupportedInfo,
    UnsupportedMajor,
    NonIntegerMapKey,
    IntOverflow,
    DuplicateMapKey,
    MissingKey,
    WrongType,
    UnknownEnum,
};

struct DecodeError {
    DecodeErrorTag tag{DecodeErrorTag::Truncated};
    long long key{0};
    unsigned info{0};
    unsigned major{0};
    const char* expected{nullptr};
    const char* enum_name{nullptr};
    long long value{0};
    std::uint64_t unsigned_value{0};
    bool negative_overflow{false};

    static constexpr DecodeError truncated() { return {DecodeErrorTag::Truncated}; }
    static constexpr DecodeError trailing_bytes() { return {DecodeErrorTag::TrailingBytes}; }
    static constexpr DecodeError invalid_utf8() { return {DecodeErrorTag::InvalidUtf8}; }
    static constexpr DecodeError unsupported_info(unsigned info) {
        DecodeError e{DecodeErrorTag::UnsupportedInfo};
        e.info = info;
        return e;
    }
    static constexpr DecodeError unsupported_major(unsigned major) {
        DecodeError e{DecodeErrorTag::UnsupportedMajor};
        e.major = major;
        return e;
    }
    static constexpr DecodeError non_integer_map_key() { return {DecodeErrorTag::NonIntegerMapKey}; }
    static constexpr DecodeError int_overflow(std::uint64_t raw, bool negative) {
        DecodeError e{DecodeErrorTag::IntOverflow};
        e.unsigned_value = raw;
        e.negative_overflow = negative;
        return e;
    }
    static constexpr DecodeError duplicate_map_key(long long key) {
        DecodeError e{DecodeErrorTag::DuplicateMapKey};
        e.key = key;
        return e;
    }
    static constexpr DecodeError missing_key(long long key) {
        DecodeError e{DecodeErrorTag::MissingKey};
        e.key = key;
        return e;
    }
    static constexpr DecodeError wrong_type(const char* expected) {
        DecodeError e{DecodeErrorTag::WrongType};
        e.expected = expected;
        return e;
    }
    static constexpr DecodeError unknown_enum(const char* enum_name, long long value) {
        DecodeError e{DecodeErrorTag::UnknownEnum};
        e.enum_name = enum_name;
        e.value = value;
        return e;
    }
};

template <class T>
struct DecodeResult {
    T value{};
    DecodeError error{};
    bool ok{false};

    constexpr explicit operator bool() const { return ok; }
    static constexpr DecodeResult success(T v) { return DecodeResult{v, {}, true}; }
    static constexpr DecodeResult fail(DecodeError e) { return DecodeResult{{}, e, false}; }
};

struct Cbor {
    enum class K { Int, Bytes, Text, Arr, Map, Bool, Null, Float };
    K k{K::Null};
    long long i{0};
    double f{0.0};
    std::string_view s{};                          // Text / Bytes (view into source)
    std::vector<Cbor> arr{};                        // Array
    std::vector<std::pair<long long, Cbor>> map{};  // Map (integer keys)

    constexpr long long as_int() const { return i; }
    constexpr bool as_bool() const { return i != 0; }
    constexpr double as_float() const { return f; }
    constexpr std::string_view as_text() const { return s; }
    constexpr std::string_view as_bytes() const { return s; }
    constexpr const std::vector<Cbor>& as_array() const { return arr; }
    constexpr bool is_null() const { return k == K::Null; }
    constexpr const Cbor& get(long long key) const {
        for (const auto& kv : map)
            if (kv.first == key) return kv.second;
        return *this; // unreachable for well-formed canonical input
    }
    constexpr DecodeResult<const Cbor*> try_get(long long key) const {
        if (k != K::Map) return DecodeResult<const Cbor*>::fail(DecodeError::wrong_type("map"));
        for (const auto& kv : map)
            if (kv.first == key) return DecodeResult<const Cbor*>::success(&kv.second);
        return DecodeResult<const Cbor*>::fail(DecodeError::missing_key(key));
    }
    constexpr DecodeResult<long long> try_int() const {
        if (k != K::Int) return DecodeResult<long long>::fail(DecodeError::wrong_type("int"));
        return DecodeResult<long long>::success(i);
    }
    constexpr DecodeResult<bool> try_bool() const {
        if (k != K::Bool) return DecodeResult<bool>::fail(DecodeError::wrong_type("bool"));
        return DecodeResult<bool>::success(i != 0);
    }
    constexpr DecodeResult<double> try_float() const {
        if (k != K::Float) return DecodeResult<double>::fail(DecodeError::wrong_type("float"));
        return DecodeResult<double>::success(f);
    }
    constexpr DecodeResult<std::string_view> try_text() const {
        if (k != K::Text) return DecodeResult<std::string_view>::fail(DecodeError::wrong_type("text"));
        return DecodeResult<std::string_view>::success(s);
    }
    constexpr DecodeResult<std::string_view> try_bytes() const {
        if (k != K::Bytes) return DecodeResult<std::string_view>::fail(DecodeError::wrong_type("bytes"));
        return DecodeResult<std::string_view>::success(s);
    }
    constexpr DecodeResult<const std::vector<Cbor>*> try_array() const {
        if (k != K::Arr) return DecodeResult<const std::vector<Cbor>*>::fail(DecodeError::wrong_type("array"));
        return DecodeResult<const std::vector<Cbor>*>::success(&arr);
    }
    constexpr DecodeResult<const std::vector<std::pair<long long, Cbor>>*> try_map() const {
        if (k != K::Map) return DecodeResult<const std::vector<std::pair<long long, Cbor>>*>::fail(DecodeError::wrong_type("map"));
        return DecodeResult<const std::vector<std::pair<long long, Cbor>>*>::success(&map);
    }
};

constexpr unsigned char byte_at(std::string_view d, std::size_t i) {
    return static_cast<unsigned char>(d[i]);
}

constexpr std::pair<unsigned long long, std::size_t> read_arg(std::string_view d, std::size_t off, unsigned info) {
    if (info < 24) return {info, off};
    if (info == 24) return {byte_at(d, off), off + 1};
    if (info == 25) return {(static_cast<unsigned long long>(byte_at(d, off)) << 8) | byte_at(d, off + 1), off + 2};
    if (info == 26) {
        unsigned long long v = 0;
        for (int j = 0; j < 4; ++j) v = (v << 8) | byte_at(d, off + j);
        return {v, off + 4};
    }
    unsigned long long v = 0; // info == 27
    for (int j = 0; j < 8; ++j) v = (v << 8) | byte_at(d, off + j);
    return {v, off + 8};
}

constexpr std::pair<Cbor, std::size_t> decode_at(std::string_view d, std::size_t off) {
    unsigned init = byte_at(d, off);
    unsigned major = init >> 5;
    unsigned info = init & 0x1f;
    off++;
    Cbor c;
    if (major == 0) { auto [v, o] = read_arg(d, off, info); c.k = Cbor::K::Int; c.i = static_cast<long long>(v); return {c, o}; }
    if (major == 1) { auto [v, o] = read_arg(d, off, info); c.k = Cbor::K::Int; c.i = -1 - static_cast<long long>(v); return {c, o}; }
    if (major == 2) { auto [v, o] = read_arg(d, off, info); c.k = Cbor::K::Bytes; c.s = d.substr(o, static_cast<std::size_t>(v)); return {c, o + static_cast<std::size_t>(v)}; }
    if (major == 3) { auto [v, o] = read_arg(d, off, info); c.k = Cbor::K::Text; c.s = d.substr(o, static_cast<std::size_t>(v)); return {c, o + static_cast<std::size_t>(v)}; }
    if (major == 4) {
        auto [n, o] = read_arg(d, off, info);
        c.k = Cbor::K::Arr;
        for (unsigned long long j = 0; j < n; ++j) { auto [e, o2] = decode_at(d, o); c.arr.push_back(e); o = o2; }
        return {c, o};
    }
    if (major == 5) {
        auto [n, o] = read_arg(d, off, info);
        c.k = Cbor::K::Map;
        for (unsigned long long j = 0; j < n; ++j) { auto [key, o2] = decode_at(d, o); auto [val, o3] = decode_at(d, o2); c.map.push_back({key.i, val}); o = o3; }
        return {c, o};
    }
    // major == 7
    if (info == 20) { c.k = Cbor::K::Bool; c.i = 0; }
    else if (info == 21) { c.k = Cbor::K::Bool; c.i = 1; }
    else if (info == 25) {
        c.k = Cbor::K::Float;
        c.f = half_to_double(static_cast<std::uint16_t>((byte_at(d, off) << 8) | byte_at(d, off + 1)));
        off += 2;
    }
    else if (info == 26) {
        std::uint32_t bits = 0;
        for (int j = 0; j < 4; ++j) bits = (bits << 8) | byte_at(d, off + j);
        c.k = Cbor::K::Float;
        c.f = static_cast<double>(f32_from_bits(bits));
        off += 4;
    }
    else if (info == 27) {
        std::uint64_t bits = 0;
        for (int j = 0; j < 8; ++j) bits = (bits << 8) | byte_at(d, off + j);
        c.k = Cbor::K::Float;
        c.f = f64_from_bits(bits);
        off += 8;
    }
    else { c.k = Cbor::K::Null; }
    return {c, off};
}

constexpr Cbor parse(std::string_view d) { return decode_at(d, 0).first; }

namespace cbor_detail {

inline bool has(std::string_view d, std::size_t off, std::size_t len) {
    return off <= d.size() && len <= d.size() - off;
}

inline DecodeResult<unsigned char> checked_byte_at(std::string_view d, std::size_t off) {
    if (!has(d, off, 1)) return DecodeResult<unsigned char>::fail(DecodeError::truncated());
    return DecodeResult<unsigned char>::success(static_cast<unsigned char>(d[off]));
}

inline DecodeResult<unsigned long long> checked_read_arg(std::string_view d, std::size_t& off, unsigned info) {
    if (info < 24) return DecodeResult<unsigned long long>::success(info);
    if (info == 24) {
        if (!has(d, off, 1)) return DecodeResult<unsigned long long>::fail(DecodeError::truncated());
        return DecodeResult<unsigned long long>::success(static_cast<unsigned char>(d[off++]));
    }
    if (info == 25) {
        if (!has(d, off, 2)) return DecodeResult<unsigned long long>::fail(DecodeError::truncated());
        unsigned long long v = (static_cast<unsigned long long>(static_cast<unsigned char>(d[off])) << 8)
            | static_cast<unsigned char>(d[off + 1]);
        off += 2;
        return DecodeResult<unsigned long long>::success(v);
    }
    if (info == 26) {
        if (!has(d, off, 4)) return DecodeResult<unsigned long long>::fail(DecodeError::truncated());
        unsigned long long v = 0;
        for (int j = 0; j < 4; ++j) v = (v << 8) | static_cast<unsigned char>(d[off + j]);
        off += 4;
        return DecodeResult<unsigned long long>::success(v);
    }
    if (info == 27) {
        if (!has(d, off, 8)) return DecodeResult<unsigned long long>::fail(DecodeError::truncated());
        unsigned long long v = 0;
        for (int j = 0; j < 8; ++j) v = (v << 8) | static_cast<unsigned char>(d[off + j]);
        off += 8;
        return DecodeResult<unsigned long long>::success(v);
    }
    return DecodeResult<unsigned long long>::fail(DecodeError::unsupported_info(info));
}

inline DecodeResult<std::size_t> checked_size(unsigned long long v) {
    if (v > static_cast<unsigned long long>(std::numeric_limits<std::size_t>::max())) {
        return DecodeResult<std::size_t>::fail(DecodeError::int_overflow(v, false));
    }
    return DecodeResult<std::size_t>::success(static_cast<std::size_t>(v));
}

inline bool valid_utf8(std::string_view s) {
    std::size_t i = 0;
    while (i < s.size()) {
        unsigned char b0 = static_cast<unsigned char>(s[i]);
        if (b0 <= 0x7f) {
            ++i;
        } else if (b0 >= 0xc2 && b0 <= 0xdf) {
            if (i + 1 >= s.size()) return false;
            unsigned char b1 = static_cast<unsigned char>(s[i + 1]);
            if ((b1 & 0xc0) != 0x80) return false;
            i += 2;
        } else if (b0 == 0xe0) {
            if (i + 2 >= s.size()) return false;
            unsigned char b1 = static_cast<unsigned char>(s[i + 1]);
            unsigned char b2 = static_cast<unsigned char>(s[i + 2]);
            if (b1 < 0xa0 || b1 > 0xbf || (b2 & 0xc0) != 0x80) return false;
            i += 3;
        } else if (b0 >= 0xe1 && b0 <= 0xec) {
            if (i + 2 >= s.size()) return false;
            unsigned char b1 = static_cast<unsigned char>(s[i + 1]);
            unsigned char b2 = static_cast<unsigned char>(s[i + 2]);
            if ((b1 & 0xc0) != 0x80 || (b2 & 0xc0) != 0x80) return false;
            i += 3;
        } else if (b0 == 0xed) {
            if (i + 2 >= s.size()) return false;
            unsigned char b1 = static_cast<unsigned char>(s[i + 1]);
            unsigned char b2 = static_cast<unsigned char>(s[i + 2]);
            if (b1 < 0x80 || b1 > 0x9f || (b2 & 0xc0) != 0x80) return false;
            i += 3;
        } else if (b0 >= 0xee && b0 <= 0xef) {
            if (i + 2 >= s.size()) return false;
            unsigned char b1 = static_cast<unsigned char>(s[i + 1]);
            unsigned char b2 = static_cast<unsigned char>(s[i + 2]);
            if ((b1 & 0xc0) != 0x80 || (b2 & 0xc0) != 0x80) return false;
            i += 3;
        } else if (b0 == 0xf0) {
            if (i + 3 >= s.size()) return false;
            unsigned char b1 = static_cast<unsigned char>(s[i + 1]);
            unsigned char b2 = static_cast<unsigned char>(s[i + 2]);
            unsigned char b3 = static_cast<unsigned char>(s[i + 3]);
            if (b1 < 0x90 || b1 > 0xbf || (b2 & 0xc0) != 0x80 || (b3 & 0xc0) != 0x80) return false;
            i += 4;
        } else if (b0 >= 0xf1 && b0 <= 0xf3) {
            if (i + 3 >= s.size()) return false;
            unsigned char b1 = static_cast<unsigned char>(s[i + 1]);
            unsigned char b2 = static_cast<unsigned char>(s[i + 2]);
            unsigned char b3 = static_cast<unsigned char>(s[i + 3]);
            if ((b1 & 0xc0) != 0x80 || (b2 & 0xc0) != 0x80 || (b3 & 0xc0) != 0x80) return false;
            i += 4;
        } else if (b0 == 0xf4) {
            if (i + 3 >= s.size()) return false;
            unsigned char b1 = static_cast<unsigned char>(s[i + 1]);
            unsigned char b2 = static_cast<unsigned char>(s[i + 2]);
            unsigned char b3 = static_cast<unsigned char>(s[i + 3]);
            if (b1 < 0x80 || b1 > 0x8f || (b2 & 0xc0) != 0x80 || (b3 & 0xc0) != 0x80) return false;
            i += 4;
        } else {
            return false;
        }
    }
    return true;
}

inline DecodeResult<Cbor> checked_decode_at(std::string_view d, std::size_t& off, bool key_position) {
    auto init_r = checked_byte_at(d, off);
    if (!init_r) return DecodeResult<Cbor>::fail(init_r.error);
    unsigned init = init_r.value;
    unsigned major = init >> 5;
    unsigned info = init & 0x1f;
    ++off;
    Cbor c;

    if (major == 0) {
        auto v = checked_read_arg(d, off, info);
        if (!v) return DecodeResult<Cbor>::fail(v.error);
        if (v.value > static_cast<unsigned long long>(std::numeric_limits<long long>::max())) {
            return DecodeResult<Cbor>::fail(DecodeError::int_overflow(v.value, false));
        }
        c.k = Cbor::K::Int;
        c.i = static_cast<long long>(v.value);
        return DecodeResult<Cbor>::success(c);
    }
    if (major == 1) {
        auto v = checked_read_arg(d, off, info);
        if (!v) return DecodeResult<Cbor>::fail(v.error);
        if (v.value > static_cast<unsigned long long>(std::numeric_limits<long long>::max())) {
            return DecodeResult<Cbor>::fail(DecodeError::int_overflow(v.value, true));
        }
        c.k = Cbor::K::Int;
        c.i = -1 - static_cast<long long>(v.value);
        return DecodeResult<Cbor>::success(c);
    }
    if (key_position) return DecodeResult<Cbor>::fail(DecodeError::non_integer_map_key());

    if (major == 2 || major == 3) {
        auto raw_n = checked_read_arg(d, off, info);
        if (!raw_n) return DecodeResult<Cbor>::fail(raw_n.error);
        auto n = checked_size(raw_n.value);
        if (!n) return DecodeResult<Cbor>::fail(n.error);
        if (!has(d, off, n.value)) return DecodeResult<Cbor>::fail(DecodeError::truncated());
        std::string_view s = d.substr(off, n.value);
        off += n.value;
        if (major == 3 && !valid_utf8(s)) return DecodeResult<Cbor>::fail(DecodeError::invalid_utf8());
        c.k = major == 2 ? Cbor::K::Bytes : Cbor::K::Text;
        c.s = s;
        return DecodeResult<Cbor>::success(c);
    }
    if (major == 4) {
        auto raw_n = checked_read_arg(d, off, info);
        if (!raw_n) return DecodeResult<Cbor>::fail(raw_n.error);
        auto n = checked_size(raw_n.value);
        if (!n) return DecodeResult<Cbor>::fail(n.error);
        c.k = Cbor::K::Arr;
        c.arr.reserve(n.value);
        for (std::size_t j = 0; j < n.value; ++j) {
            auto e = checked_decode_at(d, off, false);
            if (!e) return DecodeResult<Cbor>::fail(e.error);
            c.arr.push_back(e.value);
        }
        return DecodeResult<Cbor>::success(c);
    }
    if (major == 5) {
        auto raw_n = checked_read_arg(d, off, info);
        if (!raw_n) return DecodeResult<Cbor>::fail(raw_n.error);
        auto n = checked_size(raw_n.value);
        if (!n) return DecodeResult<Cbor>::fail(n.error);
        c.k = Cbor::K::Map;
        c.map.reserve(n.value);
        for (std::size_t j = 0; j < n.value; ++j) {
            auto key = checked_decode_at(d, off, true);
            if (!key) return DecodeResult<Cbor>::fail(key.error);
            for (const auto& kv : c.map) {
                if (kv.first == key.value.i) {
                    return DecodeResult<Cbor>::fail(DecodeError::duplicate_map_key(key.value.i));
                }
            }
            auto val = checked_decode_at(d, off, false);
            if (!val) return DecodeResult<Cbor>::fail(val.error);
            c.map.push_back({key.value.i, val.value});
        }
        return DecodeResult<Cbor>::success(c);
    }
    if (major == 7) {
        if (info == 20 || info == 21) {
            c.k = Cbor::K::Bool;
            c.i = info == 21 ? 1 : 0;
            return DecodeResult<Cbor>::success(c);
        }
        if (info == 22) {
            c.k = Cbor::K::Null;
            return DecodeResult<Cbor>::success(c);
        }
        if (info == 25) {
            if (!has(d, off, 2)) return DecodeResult<Cbor>::fail(DecodeError::truncated());
            c.k = Cbor::K::Float;
            c.f = half_to_double(static_cast<std::uint16_t>((static_cast<unsigned char>(d[off]) << 8) | static_cast<unsigned char>(d[off + 1])));
            off += 2;
            return DecodeResult<Cbor>::success(c);
        }
        if (info == 26) {
            if (!has(d, off, 4)) return DecodeResult<Cbor>::fail(DecodeError::truncated());
            std::uint32_t bits = 0;
            for (int j = 0; j < 4; ++j) bits = (bits << 8) | static_cast<unsigned char>(d[off + j]);
            c.k = Cbor::K::Float;
            c.f = static_cast<double>(f32_from_bits(bits));
            off += 4;
            return DecodeResult<Cbor>::success(c);
        }
        if (info == 27) {
            if (!has(d, off, 8)) return DecodeResult<Cbor>::fail(DecodeError::truncated());
            std::uint64_t bits = 0;
            for (int j = 0; j < 8; ++j) bits = (bits << 8) | static_cast<unsigned char>(d[off + j]);
            c.k = Cbor::K::Float;
            c.f = f64_from_bits(bits);
            off += 8;
            return DecodeResult<Cbor>::success(c);
        }
        return DecodeResult<Cbor>::fail(DecodeError::unsupported_info(info));
    }
    return DecodeResult<Cbor>::fail(DecodeError::unsupported_major(major));
}

} // namespace cbor_detail

inline DecodeResult<Cbor> try_decode(std::string_view data) {
    std::size_t off = 0;
    auto decoded = cbor_detail::checked_decode_at(data, off, false);
    if (!decoded) return decoded;
    if (off != data.size()) return DecodeResult<Cbor>::fail(DecodeError::trailing_bytes());
    return decoded;
}

// Re-emit an arbitrary decoded value canonically (ascending map keys). Used by
// forward-compat: residual fields a schema doesn't name are carried as raw Cbor
// and written back with this.
constexpr void encode_value(Buf& b, const Cbor& c) {
    switch (c.k) {
        case Cbor::K::Int: b.integer(c.i); break;
        case Cbor::K::Bytes: b.bytes(c.s); break;
        case Cbor::K::Text: b.text(c.s); break;
        case Cbor::K::Bool: b.boolean(c.i != 0); break;
        case Cbor::K::Null: b.null_(); break;
        case Cbor::K::Float: b.float_(c.f); break;
        case Cbor::K::Arr:
            b.array(c.arr.size());
            for (const auto& e : c.arr) encode_value(b, e);
            break;
        case Cbor::K::Map: {
            auto m = c.map;  // copy to sort ascending (canonical)
            for (std::size_t i = 1; i < m.size(); ++i)
                for (std::size_t j = i; j > 0 && m[j - 1].first > m[j].first; --j) {
                    auto t = m[j - 1]; m[j - 1] = m[j]; m[j] = t;
                }
            b.map(m.size());
            for (const auto& kv : m) { b.uint(static_cast<unsigned long long>(kv.first)); encode_value(b, kv.second); }
            break;
        }
    }
}

} // namespace taut
