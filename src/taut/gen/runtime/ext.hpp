// Runtime residual-extension helpers for C++.
//
// These operate on host CBOR bytes without knowing the host schema. They fail closed
// (TautCheckedDecode.md CD-E4): for any host bytes each returns its result or a
// DecodeError through DecodeResult, nothing else. The strict runtime decode reads the
// host, so it reserves nothing from a count the bytes declare, and a host that is not
// a map is WrongType{map}. Two things are the caller's errors, std::invalid_argument:
// a tag below the extension band, checked before the host is read, and a value that
// holds a negative map key, which the frozen subset cannot encode.
//
// Returned Cbor values hold string_view slices into the caller's host byte buffer; keep
// that buffer alive until the returned value has been consumed, or immediately decode
// the result into an owning/typed value (`ExtMsg::try_from_cbor`).
#pragma once

#include "taut/cbor.hpp"

#include <algorithm>
#include <cstddef>
#include <cstdint>
#include <optional>
#include <stdexcept>
#include <string_view>
#include <utility>
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

// The host's top-level map, read by the strict runtime: its DecodeError, or
// WrongType{map} for a host that is not a map.
// TODO(D1): read the host at the depth ceiling with no length bound (TautOptions.md G3),
// as Python's ext.py does, once D1 gives try_decode its depth parameter.
inline DecodeResult<Cbor> ext_host(std::string_view host) {
    auto top = try_decode(host);
    if (top && top.value.k != Cbor::K::Map) {
        return DecodeResult<Cbor>::fail(DecodeError::wrong_type("map"));
    }
    return top;
}

// The host re-encoded without the entry at `tag`, and with `value` there when given.
inline std::vector<unsigned char> ext_rewrite(Cbor host, long long tag, const Cbor* value) {
    std::erase_if(host.map, [tag](const auto& kv) { return kv.first == tag; });
    if (value != nullptr) {
        host.map.push_back({tag, *value});
    }
    std::vector<unsigned char> out;
    encode_value(out, host);
    return out;
}

} // namespace detail

inline DecodeResult<std::vector<unsigned char>> ext_set(std::string_view host, long long tag, const Cbor& value) {
    ext_check_tag(tag);
    auto top = detail::ext_host(host);
    if (!top) {
        return DecodeResult<std::vector<unsigned char>>::fail(top.error);
    }
    return DecodeResult<std::vector<unsigned char>>::success(detail::ext_rewrite(std::move(top.value), tag, &value));
}

// The extension at `tag`, or nullopt when the host has none.
inline DecodeResult<std::optional<Cbor>> ext_get(std::string_view host, long long tag) {
    ext_check_tag(tag);
    auto top = detail::ext_host(host);
    if (!top) {
        return DecodeResult<std::optional<Cbor>>::fail(top.error);
    }
    for (const auto& kv : top.value.map) {
        if (kv.first == tag) {
            return DecodeResult<std::optional<Cbor>>::success(kv.second);
        }
    }
    return DecodeResult<std::optional<Cbor>>::success(std::nullopt);
}

inline DecodeResult<std::vector<unsigned char>> ext_clear(std::string_view host, long long tag) {
    ext_check_tag(tag);
    auto top = detail::ext_host(host);
    if (!top) {
        return DecodeResult<std::vector<unsigned char>>::fail(top.error);
    }
    return DecodeResult<std::vector<unsigned char>>::success(detail::ext_rewrite(std::move(top.value), tag, nullptr));
}

} // namespace taut
