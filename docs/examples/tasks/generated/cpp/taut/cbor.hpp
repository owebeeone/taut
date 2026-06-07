// Compile-time deterministic CBOR — the C++ binding of the frozen wire substrate.
// Everything is constexpr: a value is encoded to bytes *at compile time*, and the
// generated corpus static_asserts the bytes against the golden hex. Same tiny
// subset as the Python/TS/Rust codecs (int, bytes, text, array, int-keyed map,
// bool, null), core-deterministic (shortest ints; maps are emitted in ascending
// key order by the generator). Zero runtime cost; no heap; host-testable.
#pragma once

#include <cstddef>
#include <string_view>
#include <utility>
#include <vector>

namespace taut {

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

struct Cbor {
    enum class K { Int, Bytes, Text, Arr, Map, Bool, Null };
    K k{K::Null};
    long long i{0};
    std::string_view s{};                          // Text / Bytes (view into source)
    std::vector<Cbor> arr{};                        // Array
    std::vector<std::pair<long long, Cbor>> map{};  // Map (integer keys)

    constexpr long long as_int() const { return i; }
    constexpr bool as_bool() const { return i != 0; }
    constexpr std::string_view as_text() const { return s; }
    constexpr std::string_view as_bytes() const { return s; }
    constexpr const std::vector<Cbor>& as_array() const { return arr; }
    constexpr bool is_null() const { return k == K::Null; }
    constexpr const Cbor& get(long long key) const {
        for (const auto& kv : map)
            if (kv.first == key) return kv.second;
        return *this; // unreachable for well-formed canonical input
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
    else { c.k = Cbor::K::Null; }
    return {c, off};
}

constexpr Cbor parse(std::string_view d) { return decode_at(d, 0).first; }

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
