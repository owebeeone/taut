#include "api.hpp"
#include <cassert>
#include <iostream>
#include <memory>
#include <string>
#include <type_traits>
using taut::Content;
using taut::Kind;
using taut::validation::ValidationReport;
std::string path(taut::ReadOnlyRange<taut::validation::PathSegment> segments) {
  std::string out;
  for(const auto& s:segments) {
    if(!out.empty())out+='/';
    if(s.kind()=="field")out+="f="+std::string(*s.field_name());
    else if(s.kind()=="index")out+="i="+std::to_string(*s.index());
    else out+="k="+std::string(*s.key_type())+","+std::string(*s.key_cbor_base64());
  }
  return out;
}
template<class T> void report(std::string_view name,const T& value,bool recursive=true) {
  auto r=value.validate(recursive);
  assert(value.is_valid(recursive)==(r.is_valid()&&r.is_complete()));
  std::cout<<name<<'\t'<<r.scope()<<'\t'<<(r.is_valid()?"true":"false")<<'\t'<<(r.is_complete()?"true":"false");
  for(const auto& i:r.issues())std::cout<<"\tI:"<<i.code()<<":"<<i.rule()<<":"<<path(i.path());
  for(const auto& d:r.deferred_checks())std::cout<<"\tD:"<<d.reason_code()<<":"<<d.rule()<<":"<<path(d.path());
  std::cout<<'\n';
}
Content content(Kind kind) {Content c{};c.kind=kind;return c;}
int main() {
  static_assert(noexcept(Content::descriptor()));
  static_assert(noexcept(std::declval<const Content&>().validate()));
  static_assert(noexcept(std::declval<const Content&>().is_valid()));
  auto c=content(Kind::Text);report("missing",c);c.text="";report("empty",c);c.number=0;report("extra",c);
  taut::Buf wire;c.to_cbor(wire);
  auto decoded=Content::try_decode(std::string_view(reinterpret_cast<const char*>(wire.d),wire.n));assert(decoded);
  report("roundtrip",decoded.value);
  c.kind=Kind::Number;c.text.reset();report("zero",c);
  c.kind=Kind::Flag;c.number.reset();c.flag=false;report("false",c);
  c.flag.reset();c.kind=Kind::Items;c.items=std::vector<long long>{};report("empty-list",c);
  c.items.reset();c.kind=Kind::Empty;report("payload-free",c);
  c.kind=static_cast<Kind>(99);c.child=std::make_shared<Content>(content(Kind::Text));report("bad-tag-child",c);
  c.kind=Kind::Empty;report("nonselected-child",c);
  auto cycle=std::make_shared<Content>(content(Kind::Child));cycle->child=cycle;report("cycle",*cycle);cycle->child.reset();
  auto bad=std::make_shared<Content>(content(Kind::Text));
  taut::Wrapper w{bad,{bad,bad},{{"z",bad},{"",bad},{"aa",bad}},{{-1,bad},{24,bad},{0,bad}},{{true,bad},{false,bad}}};
  report("wrapper",w);report("local",w,false);
  taut::Virtual v{};v.child=bad;report("virtual-child",v);bad->text="";report("virtual-repaired",v);report("virtual-local",v,false);
  taut::Multi m{};m.left=static_cast<Kind>(99);m.right=Kind::Number;report("independent",m);
  report("plain",taut::Plain{0,std::nullopt,std::nullopt});
  const auto snapshot=c.validate();c.child.reset();assert(snapshot.issues().size()==2);
  auto issue=taut::validation::ValidationIssue("app.custom","app.rule.v1",{},"owned diagnostic");
  ValidationReport synthetic({issue},{});assert(!synthetic.is_valid()&&synthetic.is_complete());
  assert(Content::descriptor().fields().size()==6);
  assert(Content::descriptor().reserved_numbers()[0]==7);
  assert(Content::descriptor().next_id()==9);
  assert(taut::Virtual::descriptor().fields()[0].virtual_field());
}
