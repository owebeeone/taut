#include "taut/foundation.hpp"
namespace taut {
const FoundationContract& foundation_contract() noexcept {
  static constexpr FoundationContract contract{"taut.cpp.foundation",1,1,1,7,0x5441555443505031ULL,"cpp-oneof-reference.1"};
  return contract;
}
}
