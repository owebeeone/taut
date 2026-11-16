// Example thin C++ wrapper exposing Swift-importable operations.
#pragma once
#include "CustomerBigIntAdapter.hpp"
class CustomerBigIntBridge {
    CustomerBigInt value_;
public:
    bool negative() const { return value_.isNegative(); }
    std::size_t byteCount() const { return value_.magnitudeBytes().size(); }
    std::uint8_t byteAt(std::size_t index) const { return value_.magnitudeBytes().at(index); }
    static CustomerBigIntBridge fromBytes(bool negative, const std::uint8_t* data, std::size_t count) {
        CustomerBigIntBridge result;
        result.value_ = CustomerBigIntAdapter::from_magnitude(negative, std::span(data, count));
        return result;
    }
};
