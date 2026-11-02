#include "api.hpp"
#include <cassert>
#include <cstdlib>
#include <new>
#include <utility>
static long allocation_budget=-1;
static std::size_t allocations=0;
void* operator new(std::size_t n) {
  if(allocation_budget==0)throw std::bad_alloc();
  if(allocation_budget>0)--allocation_budget;
  ++allocations;
  if(auto p=std::malloc(n?n:1))return p;
  throw std::bad_alloc();
}
void* operator new[](std::size_t n) {return ::operator new(n);}
void operator delete(void* p) noexcept {std::free(p);}
void operator delete[](void* p) noexcept {std::free(p);}
void operator delete(void* p,std::size_t) noexcept {std::free(p);}
void operator delete[](void* p,std::size_t) noexcept {std::free(p);}
int main() {
  taut::Content bad{};bad.kind=taut::Kind::Text;
  allocation_budget=0;
  // First ever fallback construction/getters happen with every allocation failing.
  auto fallback=bad.validate(false);
  auto moved=std::move(fallback);
  auto copied=moved;
  assert(!copied.is_valid()&&!copied.is_complete()&&copied.scope()=="local");
  assert(copied.issues().size()==1&&copied.deferred_checks().size()==1);
  assert(copied.issues()[0].code()=="validation.resource_exhausted");
  assert(copied.deferred_checks()[0].reason_code()=="validation.resource_exhausted");
  assert(copied.issues()[0].path().empty()&&copied.deferred_checks()[0].path().empty());
  for(const auto& issue:copied.issues())assert(issue.message()=="validation allocation failed");
  const auto baseline=allocations;
  assert(!bad.is_valid());assert(allocations==baseline);
  allocation_budget=-1;
  bad.text="";
  auto child=std::make_shared<taut::Content>(bad);
  taut::Wrapper wrapper{child,{},{{"z",child},{"aa",child}},{{-1,child},{24,child}},{{false,child}}};
  allocation_budget=0;
  assert(bad.is_valid()); // No diagnostics or per-field heap wrapper.
  assert(!wrapper.is_valid()); // Map ordering allocation is recoverable.
  allocation_budget=-1;
  bad.text.reset();
  bool reached_success=false;
  for(long budget=0;budget<100;++budget) {
    allocation_budget=budget;
    auto r=bad.validate();
    allocation_budget=0;
    if(r.issues()[0].code()=="validation.resource_exhausted") {
      assert(r.issues().size()==1&&!r.is_complete()&&r.issues()[0].path().empty());
      assert(r.deferred_checks().size()==1&&r.deferred_checks()[0].path().empty());
    } else {
      assert(r.issues().size()==1&&r.is_complete());
      assert(r.issues()[0].code()=="oneof.payload_missing");
      assert(r.issues()[0].path().size()==1&&r.issues()[0].path()[0].field_name()=="text");
      reached_success=true;break;
    }
    allocation_budget=-1;
  }
  allocation_budget=-1;
  assert(reached_success);
}
