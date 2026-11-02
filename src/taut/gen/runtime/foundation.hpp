// Canonical C++ foundation ABI. One compiled owner per application.
#pragma once
#include <cstdint>
#include <string_view>
#include <stdexcept>
namespace taut {
struct FoundationContract {
  std::string_view owner;
  unsigned descriptor, codec, adapter, capabilities;
  std::uint64_t guard;
  std::string_view build;
};
const FoundationContract& foundation_contract() noexcept;
inline void require_foundation() {
  const auto& c = foundation_contract();
  if (c.owner != "taut.cpp.foundation" || c.descriptor != 1 || c.codec != 1 ||
      c.adapter != 1 || (c.capabilities & 7) != 7 || c.guard != 0x5441555443505031ULL)
    throw std::logic_error("incompatible C++ taut foundation: require owner taut.cpp.foundation, descriptor=1 codec=1 adapter=1 capabilities=7; regenerate/rebind");
}
}
