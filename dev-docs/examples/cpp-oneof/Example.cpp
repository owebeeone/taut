#include "api.hpp"
#include <cassert>
#include <iostream>
int main() {
  taut::Content draft{};
  draft.kind=taut::Kind::Number;
  draft.text="extra";
  const auto before=draft.validate();
  assert(before.issues().size()==2 && !draft.is_valid());
  taut::Buf wire;
  draft.to_cbor(wire); // All populated fields survive; no semantic validation.
  auto decoded=taut::Content::try_decode(std::string_view(reinterpret_cast<const char*>(wire.d),wire.n));
  assert(decoded && decoded.value.text=="extra" && !decoded.value.number);
  draft.text.reset();
  draft.number=42;
  assert(draft.is_valid() && before.issues().size()==2); // Owned earlier report.
  auto child=std::make_shared<taut::Content>();
  child->kind=taut::Kind::Text;
  taut::Virtual root{};root.child=child;
  assert(!root.validate().is_valid());
  child->text="";
  auto incomplete=root.validate();
  assert(incomplete.is_valid() && !incomplete.is_complete() && !root.is_valid());
  std::cout<<"draft issues="<<before.issues().size()<<"; repaired="<<draft.is_valid()
           <<"; virtual valid="<<incomplete.is_valid()<<" complete="<<incomplete.is_complete()<<"\n";
}
