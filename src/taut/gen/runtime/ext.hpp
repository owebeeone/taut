// Runtime residual-extension helpers for C++.
//
// These operate on host CBOR bytes without knowing the host schema. Returned
// Cbor values hold string_view slices into the caller's host byte buffer; keep
// that buffer alive until the returned value has been consumed, or immediately
// decode the result into an owning/typed value.
#pragma once

#include "taut/cbor.hpp"

#include <algorithm>
#include <cstddef>
#include <cstdint>
#include <limits>
#include <optional>
#include <stdexcept>
#include <string_view>
#include <vector>

namespace taut {

inline constexpr long long EXT_BAND_START = 1LL << 20;

inline void ext_check_tag(long long tag) {
    if (tag < EXT_BAND_START) {
        throw std::invalid_argument("extension tag is below the reserved band");
    }
}

inline void ext_head(std::vector<unsigned char>& out, unsigned major, unsigned long long v) {
    const unsigned mt = major << 5;
    if (v < 24) {
        out.push_back(static_cast<unsigned char>(mt | v));
    } else if (v < 0x100ULL) {
        out.push_back(static_cast<unsigned char>(mt | 24));
        out.push_back(static_cast<unsigned char>(v));
    } else if (v < 0x10000ULL) {
        out.push_back(static_cast<unsigned char>(mt | 25));
        out.push_back(static_cast<unsigned char>(v >> 8));
        out.push_back(static_cast<unsigned char>(v));
    } else if (v < 0x100000000ULL) {
        out.push_back(static_cast<unsigned char>(mt | 26));
        for (int i = 3; i >= 0; --i) out.push_back(static_cast<unsigned char>(v >> (i * 8)));
    } else {
        out.push_back(static_cast<unsigned char>(mt | 27));
        for (int i = 7; i >= 0; --i) out.push_back(static_cast<unsigned char>(v >> (i * 8)));
    }
}

inline void ext_append_bytes(std::vector<unsigned char>& out, std::string_view s) {
    for (unsigned char b : s) out.push_back(b);
}

inline void ext_append_float(std::vector<unsigned char>& out, double v) {
    const std::uint64_t bits = f64_bits(v);
    if (f64_is_nan_bits(bits)) {
        out.push_back(0xf9);
        out.push_back(0x7e);
        out.push_back(0x00);
        return;
    }
    std::uint16_t h = 0;
    if (half_exact(v, h)) {
        out.push_back(0xf9);
        out.push_back(static_cast<unsigned char>(h >> 8));
        out.push_back(static_cast<unsigned char>(h));
        return;
    }
    if (single_exact(v)) {
        const std::uint32_t f = f32_bits(static_cast<float>(v));
        out.push_back(0xfa);
        for (int i = 3; i >= 0; --i) out.push_back(static_cast<unsigned char>(f >> (i * 8)));
        return;
    }
    out.push_back(0xfb);
    for (int i = 7; i >= 0; --i) out.push_back(static_cast<unsigned char>(bits >> (i * 8)));
}

inline void encode_value(std::vector<unsigned char>& out, const Cbor& c) {
    switch (c.k) {
        case Cbor::K::Int:
            if (c.i >= 0) ext_head(out, 0, static_cast<unsigned long long>(c.i));
            else ext_head(out, 1, static_cast<unsigned long long>(-1 - c.i));
            break;
        case Cbor::K::Bytes:
            ext_head(out, 2, c.s.size());
            ext_append_bytes(out, c.s);
            break;
        case Cbor::K::Text:
            ext_head(out, 3, c.s.size());
            ext_append_bytes(out, c.s);
            break;
        case Cbor::K::Bool:
            out.push_back(c.i != 0 ? 0xf5 : 0xf4);
            break;
        case Cbor::K::Null:
            out.push_back(0xf6);
            break;
        case Cbor::K::Float:
            ext_append_float(out, c.f);
            break;
        case Cbor::K::Arr:
            ext_head(out, 4, c.arr.size());
            for (const auto& e : c.arr) encode_value(out, e);
            break;
        case Cbor::K::Map: {
            auto m = c.map;
            std::sort(m.begin(), m.end(), [](const auto& a, const auto& b) {
                return a.first < b.first;
            });
            ext_head(out, 5, m.size());
            for (const auto& kv : m) {
                if (kv.first < 0) {
                    throw std::invalid_argument("frozen subset allows only non-negative integer map keys");
                }
                ext_head(out, 0, static_cast<unsigned long long>(kv.first));
                encode_value(out, kv.second);
            }
            break;
        }
    }
}

namespace detail {

inline void ext_require(bool ok, const char* message) {
    if (!ok) throw std::invalid_argument(message);
}

inline unsigned char ext_byte_at(std::string_view d, std::size_t off) {
    ext_require(off < d.size(), "truncated CBOR input");
    return static_cast<unsigned char>(d[off]);
}

inline unsigned long long ext_read_arg(std::string_view d, std::size_t& off, unsigned info) {
    if (info < 24) return info;
    if (info == 24) {
        ext_require(off + 1 <= d.size(), "truncated CBOR argument");
        return ext_byte_at(d, off++);
    }
    if (info == 25) {
        ext_require(off + 2 <= d.size(), "truncated CBOR argument");
        unsigned long long v = (static_cast<unsigned long long>(ext_byte_at(d, off)) << 8)
            | ext_byte_at(d, off + 1);
        off += 2;
        return v;
    }
    if (info == 26) {
        ext_require(off + 4 <= d.size(), "truncated CBOR argument");
        unsigned long long v = 0;
        for (int j = 0; j < 4; ++j) v = (v << 8) | ext_byte_at(d, off + j);
        off += 4;
        return v;
    }
    if (info == 27) {
        ext_require(off + 8 <= d.size(), "truncated CBOR argument");
        unsigned long long v = 0;
        for (int j = 0; j < 8; ++j) v = (v << 8) | ext_byte_at(d, off + j);
        off += 8;
        return v;
    }
    throw std::invalid_argument("unsupported additional-info in frozen CBOR subset");
}

inline std::size_t ext_size_arg(unsigned long long v) {
    ext_require(v <= static_cast<unsigned long long>(std::numeric_limits<std::size_t>::max()),
        "CBOR length is too large");
    return static_cast<std::size_t>(v);
}

inline long long ext_int_arg(unsigned long long v) {
    ext_require(v <= static_cast<unsigned long long>(std::numeric_limits<long long>::max()),
        "CBOR integer is too large");
    return static_cast<long long>(v);
}

inline Cbor ext_decode_at(std::string_view d, std::size_t& off, bool key_position) {
    const unsigned init = ext_byte_at(d, off++);
    const unsigned major = init >> 5;
    const unsigned info = init & 0x1f;
    Cbor c;

    if (major == 0) {
        c.k = Cbor::K::Int;
        c.i = ext_int_arg(ext_read_arg(d, off, info));
        return c;
    }
    if (major == 1) {
        ext_require(!key_position, "frozen subset allows only non-negative integer map keys");
        const unsigned long long n = ext_read_arg(d, off, info);
        ext_require(n < static_cast<unsigned long long>(std::numeric_limits<long long>::max()),
            "CBOR negative integer is too large");
        c.k = Cbor::K::Int;
        c.i = -1 - static_cast<long long>(n);
        return c;
    }
    if (major == 2 || major == 3) {
        ext_require(!key_position, "frozen subset allows only non-negative integer map keys");
        const std::size_t n = ext_size_arg(ext_read_arg(d, off, info));
        ext_require(off + n <= d.size(), "truncated CBOR string");
        c.k = major == 2 ? Cbor::K::Bytes : Cbor::K::Text;
        c.s = d.substr(off, n);
        off += n;
        return c;
    }
    if (major == 4) {
        ext_require(!key_position, "frozen subset allows only non-negative integer map keys");
        const std::size_t n = ext_size_arg(ext_read_arg(d, off, info));
        c.k = Cbor::K::Arr;
        c.arr.reserve(n);
        for (std::size_t j = 0; j < n; ++j) c.arr.push_back(ext_decode_at(d, off, false));
        return c;
    }
    if (major == 5) {
        ext_require(!key_position, "frozen subset allows only non-negative integer map keys");
        const std::size_t n = ext_size_arg(ext_read_arg(d, off, info));
        c.k = Cbor::K::Map;
        c.map.reserve(n);
        for (std::size_t j = 0; j < n; ++j) {
            Cbor key = ext_decode_at(d, off, true);
            Cbor val = ext_decode_at(d, off, false);
            c.map.push_back({key.i, val});
        }
        return c;
    }
    if (major == 7) {
        ext_require(!key_position, "frozen subset allows only non-negative integer map keys");
        if (info == 20 || info == 21) {
            c.k = Cbor::K::Bool;
            c.i = info == 21 ? 1 : 0;
            return c;
        }
        if (info == 22) {
            c.k = Cbor::K::Null;
            return c;
        }
        if (info == 25) {
            ext_require(off + 2 <= d.size(), "truncated half-float");
            c.k = Cbor::K::Float;
            c.f = half_to_double(static_cast<std::uint16_t>((ext_byte_at(d, off) << 8) | ext_byte_at(d, off + 1)));
            off += 2;
            return c;
        }
        if (info == 26) {
            ext_require(off + 4 <= d.size(), "truncated single-float");
            std::uint32_t bits = 0;
            for (int j = 0; j < 4; ++j) bits = (bits << 8) | ext_byte_at(d, off + j);
            c.k = Cbor::K::Float;
            c.f = static_cast<double>(f32_from_bits(bits));
            off += 4;
            return c;
        }
        if (info == 27) {
            ext_require(off + 8 <= d.size(), "truncated double-float");
            std::uint64_t bits = 0;
            for (int j = 0; j < 8; ++j) bits = (bits << 8) | ext_byte_at(d, off + j);
            c.k = Cbor::K::Float;
            c.f = f64_from_bits(bits);
            off += 8;
            return c;
        }
        throw std::invalid_argument("unsupported simple value in frozen CBOR subset");
    }

    throw std::invalid_argument("unsupported major type in frozen CBOR subset");
}

} // namespace detail

inline Cbor checked_parse_map(std::string_view data) {
    std::size_t off = 0;
    Cbor value = detail::ext_decode_at(data, off, false);
    if (off != data.size()) {
        throw std::invalid_argument("trailing bytes after top-level CBOR item");
    }
    if (value.k != Cbor::K::Map) {
        throw std::invalid_argument("extension host must be a top-level CBOR map");
    }
    return value;
}

inline std::vector<unsigned char> ext_set(std::string_view host, long long tag, const Cbor& value) {
    ext_check_tag(tag);
    Cbor root = checked_parse_map(host);
    std::vector<std::pair<long long, Cbor>> entries;
    entries.reserve(root.map.size() + 1);
    for (const auto& kv : root.map) {
        if (kv.first != tag) entries.push_back(kv);
    }
    entries.push_back({tag, value});
    root.map = std::move(entries);

    std::vector<unsigned char> out;
    encode_value(out, root);
    return out;
}

inline std::optional<Cbor> ext_get(std::string_view host, long long tag) {
    ext_check_tag(tag);
    Cbor root = checked_parse_map(host);
    for (const auto& kv : root.map) {
        if (kv.first == tag) return kv.second;
    }
    return std::nullopt;
}

inline std::vector<unsigned char> ext_clear(std::string_view host, long long tag) {
    ext_check_tag(tag);
    Cbor root = checked_parse_map(host);
    std::vector<std::pair<long long, Cbor>> entries;
    entries.reserve(root.map.size());
    for (const auto& kv : root.map) {
        if (kv.first != tag) entries.push_back(kv);
    }
    root.map = std::move(entries);

    std::vector<unsigned char> out;
    encode_value(out, root);
    return out;
}

} // namespace taut
