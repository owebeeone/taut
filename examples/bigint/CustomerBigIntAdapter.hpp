// Example only: replace CustomerBigInt with your application's integer type.
#pragma once
#include <cstdint>
#include <span>
#include <stdexcept>
#include <vector>

// A stand-in customer value for the adapter example, not an arithmetic library.
class CustomerBigInt {
    bool negative_ = false;
    std::vector<std::uint8_t> magnitude_;
public:
    static CustomerBigInt fromMagnitude(bool negative, std::span<const std::uint8_t> bytes) {
        if ((!bytes.empty() && bytes.front() == 0) || (negative && bytes.empty()))
            throw std::invalid_argument("noncanonical customer integer");
        CustomerBigInt value;
        value.negative_ = negative;
        value.magnitude_.assign(bytes.begin(), bytes.end());
        return value;
    }
    bool isNegative() const { return negative_; }
    const std::vector<std::uint8_t>& magnitudeBytes() const { return magnitude_; }
    friend bool operator==(const CustomerBigInt&, const CustomerBigInt&) = default;
};

struct CustomerBigIntAdapter {
    using value_type = CustomerBigInt;
    static bool is_negative(const value_type& value) { return value.isNegative(); }
    static std::vector<std::uint8_t> magnitude(const value_type& value) { return value.magnitudeBytes(); }
    static value_type from_magnitude(bool negative, std::span<const std::uint8_t> bytes) {
        return value_type::fromMagnitude(negative, bytes);
    }
};
