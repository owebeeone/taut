// One predicate/traversal implementation, independent report and Boolean sinks.
#pragma once
#include "taut/reports.hpp"
#include <algorithm>
#include <new>
namespace taut::validation {
namespace engine_detail {
inline void key_head(std::string& out,unsigned major,std::uint64_t n) {
  if(n<24) {out.push_back(static_cast<char>((major<<5)|n));return;}
  unsigned count=n<=255?1:n<=65535?2:n<=0xffffffffULL?4:8;
  out.push_back(static_cast<char>((major<<5)|(count==1?24:count==2?25:count==4?26:27)));
  for(unsigned i=count;i>0;--i)out.push_back(static_cast<char>(n>>((i-1)*8)));
}
inline std::string key_bytes(ValueRef key) {
  std::string out;
  if(key.kind()==TypeKind::String) {auto text=key.text();key_head(out,3,text.size());out.append(text);}
  else if(key.kind()==TypeKind::Bool)out.push_back(key.boolean()?'\xf5':'\xf4');
  else {auto n=key.integer();key_head(out,n<0?1:0,n<0?static_cast<std::uint64_t>(-(n+1)):static_cast<std::uint64_t>(n));}
  return out;
}
inline bool unsigned_less(std::string_view a,std::string_view b) noexcept {
  return std::lexicographical_compare(a.begin(),a.end(),b.begin(),b.end(),[](char x,char y){return static_cast<unsigned char>(x)<static_cast<unsigned char>(y);});
}
struct Ancestor { const void* value;const SchemaBinding* binding;const Ancestor* parent; };
template<bool Report> struct Sink {
  std::vector<PathSegment> path;
  std::vector<ValidationIssue> issues;
  std::vector<DeferredCheck> deferred;
  bool event(std::string_view code,std::string_view rule,bool defer=false) {
    if constexpr(Report) {
      if(defer)deferred.emplace_back(std::string(rule),path,std::string(code),std::string(code));
      else issues.emplace_back(std::string(code),std::string(rule),path,std::string(code));
      return true;
    }
    return false;
  }
  void field(std::string_view name) {if constexpr(Report)path.push_back(PathSegment::for_field(std::string(name)));}
  void index(std::size_t n) {if constexpr(Report)path.push_back(PathSegment::for_index(n));}
  void key(TypeKind kind,std::string_view bytes) {if constexpr(Report)path.push_back(PathSegment::for_key(kind==TypeKind::String?"str":kind==TypeKind::Bool?"bool":"int",bytes));}
  void pop() noexcept {if constexpr(Report)path.pop_back();}
};
// A fast sink has no diagnostic/path containers, even empty ones.
template<> struct Sink<false> {
  bool event(std::string_view,std::string_view,bool=false) noexcept {return false;}
  void field(std::string_view) noexcept {}
  void index(std::size_t) noexcept {}
  void key(TypeKind,std::string_view) noexcept {}
  void pop() noexcept {}
};
template<bool R> bool walk(ValueRef value,Sink<R>& sink,const Ancestor* ancestors,bool recursive);
template<bool R> bool child(ValueRef value,Sink<R>& sink,const Ancestor* ancestors) {
  if(!value.present())return true;
  if(value.kind()==TypeKind::Message)return walk(value,sink,ancestors,true);
  if(value.kind()==TypeKind::Enum && !value.enumeration().find(value.integer()))return sink.event("validation.type_mismatch","validation.shape.v1");
  if(value.kind()==TypeKind::List) {
    for(std::size_t i=0;i<value.size();++i) {sink.index(i);bool keep=child(value.item(i),sink,ancestors);sink.pop();if(!keep)return false;}
  } else if(value.kind()==TypeKind::Map) {
    std::vector<std::pair<std::string,std::size_t>> entries;
    for(std::size_t i=0;i<value.size();++i)entries.emplace_back(key_bytes(value.key(i)),i);
    std::sort(entries.begin(),entries.end(),[](const auto& a,const auto& b){return unsigned_less(a.first,b.first);});
    for(const auto& entry:entries) {sink.key(value.key(entry.second).kind(),entry.first);bool keep=child(value.item(entry.second),sink,ancestors);sink.pop();if(!keep)return false;}
  }
  return true;
}
template<bool R> bool group(ValueRef value,const MessageDescriptor& descriptor,const OneOfDescriptor& group,Sink<R>& sink) {
  sink.field(group.controlling_field());
  if(group.virtual_field()) {bool keep=sink.event("oneof.virtual_deferred","taut.oneof.v1",true);sink.pop();return keep;}
  std::size_t index=0;
  for(const auto& field:descriptor.fields()) {if(field.name()==group.controlling_field())break;++index;}
  auto tag=value.field(index);
  const auto* member=tag.present()?group.enumeration().find(tag.integer()):nullptr;
  if(!member) {bool keep=sink.event("oneof.invalid_discriminator","taut.oneof.v1");sink.pop();return keep;}
  sink.pop();
  std::string_view selected;
  for(const auto& mapping:group.members())if(mapping.member==member->name)selected=mapping.payload;
  index=0;
  for(const auto& field:descriptor.fields()) {
    bool payload=false;
    for(const auto& mapping:group.members())if(mapping.payload==field.name())payload=true;
    if(payload) {
      bool present=value.field(index).present();
      std::string_view code;
      if(field.name()==selected && !present)code="oneof.payload_missing";
      if(field.name()!=selected && present)code="oneof.payload_unexpected";
      if(!code.empty()) {sink.field(field.name());bool keep=sink.event(code,"taut.oneof.v1");sink.pop();if(!keep)return false;}
    }
    ++index;
  }
  return true;
}
template<bool R> bool walk(ValueRef value,Sink<R>& sink,const Ancestor* ancestors,bool recursive) {
  const auto& binding=value.binding();
  // A complete object and its first value subobject can share an address.
  // The actual static native binding distinguishes those valid owned values,
  // while optional/shared-pointer views of one message retain the same key.
  for(auto p=ancestors;p;p=p->parent)if(p->value==value.identity() && p->binding==&binding)return sink.event("validation.ownership_cycle","validation.shape.v1");
  const Ancestor current{value.identity(),&binding,ancestors};
  const auto& descriptor=binding.descriptor();
  std::size_t index=0;
  for(const auto& field:descriptor.fields()) {
    bool control=false;
    for(const auto& g:descriptor.oneofs())if(g.controlling_field()==field.name()) {control=true;if(!group(value,descriptor,g,sink))return false;}
    if(recursive && !field.virtual_field() && !control) {sink.field(field.name());bool keep=child(value.field(index),sink,&current);sink.pop();if(!keep)return false;}
    ++index;
  }
  return true;
}
}
template<class T> ValidationReport validate_record(const T& value,bool recursive=true) noexcept {
  try {
    engine_detail::Sink<true> sink;
    engine_detail::walk(ValueRef::borrow(value),sink,nullptr,recursive);
    return {std::move(sink.issues),std::move(sink.deferred),recursive?"recursive":"local"};
  } catch(const std::bad_alloc&) {return ValidationReport::resource_exhausted(recursive);}
}
template<class T> bool is_record_valid(const T& value,bool recursive=true) noexcept {
  try {engine_detail::Sink<false> sink;return engine_detail::walk(ValueRef::borrow(value),sink,nullptr,recursive);}
  catch(const std::bad_alloc&) {return false;}
}
}
