// Canonical immutable C++ metadata and typed, borrowed access. No RTTI/engine.
#pragma once
#include "taut/foundation.hpp"
#include <cstddef>
#include <concepts>
#include <cstdint>
#include <map>
#include <memory>
#include <optional>
#include <string>
#include <string_view>
#include <type_traits>
#include <vector>
namespace taut {
template<class T> class ReadOnlyRange {
  const T* data_ = nullptr;
  std::size_t size_ = 0;
public:
  constexpr ReadOnlyRange() noexcept = default;
  constexpr ReadOnlyRange(const T* data, std::size_t size) noexcept : data_(data), size_(size) {}
  template<std::size_t N> constexpr ReadOnlyRange(const T (&data)[N]) noexcept : data_(data), size_(N) {}
  constexpr const T* begin() const noexcept { return data_; }
  constexpr const T* end() const noexcept { return size_ ? data_ + size_ : data_; }
  constexpr std::size_t size() const noexcept { return size_; }
  constexpr bool empty() const noexcept { return size_ == 0; }
  constexpr const T& operator[](std::size_t i) const noexcept { return data_[i]; }
};
// Static metadata is compiler-authored, const-owned storage. No public mutable
// metadata containers or runtime graph registration are part of this ABI.
enum class TypeKind { Int, String, Bool, Bytes, Float, Enum, Message, List, Map };
struct Fact;
struct FactEntry;
struct Fact {
  enum class Tag { Null, Bool, Int, Float, String, Bytes, List, Map };
  const Tag tag;
  const bool boolean = false;
  const long long integer = 0;
  const double floating = 0;
  const std::string_view text = {};
  const ReadOnlyRange<Fact> list = {};
  const ReadOnlyRange<FactEntry> map = {};
};
struct FactEntry { const std::string_view name; const Fact value; };
using Options = ReadOnlyRange<FactEntry>;
namespace descriptor_detail {
// An immediate publication constructor may only borrow fully constant storage.
// Reading every byte/node rejects a mutable caller-owned backing graph at build
// time. Published metadata therefore has static immutable ownership, without a
// heap snapshot or a dangling view into caller data.
consteval std::uint64_t frozen_text(std::string_view text) {
  std::uint64_t sum=0;for(unsigned char c:text)sum=sum*131+c;return sum;
}
consteval std::uint64_t frozen_fact(const Fact& value) {
  auto sum=static_cast<std::uint64_t>(value.tag);
  sum+=value.boolean;sum+=static_cast<std::uint64_t>(value.integer);
  if(value.floating!=0)sum+=1;
  sum+=frozen_text(value.text);
  for(const auto& item:value.list)sum+=frozen_fact(item);
  for(const auto& item:value.map)sum+=frozen_text(item.name)+frozen_fact(item.value);
  return sum;
}
consteval std::uint64_t frozen_options(Options options) {
  std::uint64_t sum=0;for(const auto& item:options)sum+=frozen_text(item.name)+frozen_fact(item.value);return sum;
}
}
class MessageDescriptor;
class EnumDescriptor;
struct SchemaBinding;
struct TypeDescriptor {
  const TypeKind kind;
  const TypeDescriptor* const element = nullptr;
  const TypeDescriptor* const key = nullptr;
  const TypeDescriptor* const value = nullptr;
  const MessageDescriptor& (*const message)() noexcept = nullptr;
  const EnumDescriptor& (*const enumeration)() noexcept = nullptr;
};
class FieldDescriptor {
  std::string_view name_, access_, presence_;
  long long number_;
  const TypeDescriptor* type_;
  bool transient_, virtual_;
  Options options_;
  std::uint64_t frozen_;
public:
  consteval FieldDescriptor(std::string_view name,std::string_view access,long long number,
      const TypeDescriptor& type,std::string_view presence,bool transient,bool virtual_field,Options options) noexcept
      : name_(name),access_(access),presence_(presence),number_(number),type_(&type),transient_(transient),virtual_(virtual_field),options_(options),
        frozen_(descriptor_detail::frozen_text(name)+descriptor_detail::frozen_text(access)+descriptor_detail::frozen_text(presence)+descriptor_detail::frozen_options(options)+static_cast<unsigned>(type.kind)) {}
  constexpr std::string_view name() const noexcept { return name_; }
  constexpr std::string_view access_identity() const noexcept { return access_; }
  constexpr long long number() const noexcept { return number_; }
  constexpr const TypeDescriptor& type() const noexcept { return *type_; }
  constexpr std::string_view presence() const noexcept { return presence_; }
  constexpr bool transient() const noexcept { return transient_; }
  constexpr bool virtual_field() const noexcept { return virtual_; }
  constexpr Options options() const noexcept { return options_; }
};
struct EnumMemberDescriptor {
  const std::string_view name;
  const long long number;
  const Options options;
};
class EnumDescriptor {
  std::string_view name_,qualified_,fingerprint_;
  ReadOnlyRange<EnumMemberDescriptor> members_;
  Options options_;
  std::uint64_t frozen_;
public:
  consteval EnumDescriptor(std::string_view name,std::string_view qualified,ReadOnlyRange<EnumMemberDescriptor> members,Options options,std::string_view fingerprint) noexcept
    : name_(name),qualified_(qualified),fingerprint_(fingerprint),members_(members),options_(options),frozen_(descriptor_detail::frozen_text(name)+descriptor_detail::frozen_text(qualified)+descriptor_detail::frozen_text(fingerprint)+descriptor_detail::frozen_options(options)) {
      for(const auto& m:members)frozen_+=descriptor_detail::frozen_text(m.name)+static_cast<std::uint64_t>(m.number)+descriptor_detail::frozen_options(m.options);
    }
  constexpr std::string_view name() const noexcept { return name_; }
  constexpr std::string_view qualified_name() const noexcept { return qualified_; }
  constexpr unsigned descriptor_contract_version() const noexcept { return 1; }
  constexpr ReadOnlyRange<EnumMemberDescriptor> members() const noexcept { return members_; }
  constexpr Options options() const noexcept { return options_; }
  constexpr std::string_view fingerprint() const noexcept { return fingerprint_; }
  constexpr const EnumMemberDescriptor* find(long long number) const noexcept {
    for (const auto& m:members_) if(m.number==number) return &m;
    return nullptr;
  }
};
struct OneOfMemberDescriptor { const std::string_view member; const std::string_view payload; };
class OneOfDescriptor {
  std::string_view controlling_;
  const EnumDescriptor& (*enum_)() noexcept;
  bool virtual_,exhaustive_;
  ReadOnlyRange<OneOfMemberDescriptor> members_;
  std::uint64_t frozen_;
public:
  consteval OneOfDescriptor(std::string_view control,const EnumDescriptor& (*enumeration)() noexcept,bool virtual_field,bool exhaustive,ReadOnlyRange<OneOfMemberDescriptor> members) noexcept
    : controlling_(control),enum_(enumeration),virtual_(virtual_field),exhaustive_(exhaustive),members_(members),frozen_(descriptor_detail::frozen_text(control)) {
      for(const auto& m:members)frozen_+=descriptor_detail::frozen_text(m.member)+descriptor_detail::frozen_text(m.payload);
    }
  constexpr std::string_view controlling_field() const noexcept { return controlling_; }
  const EnumDescriptor& enumeration() const noexcept { return enum_(); }
  constexpr bool virtual_field() const noexcept { return virtual_; }
  constexpr bool exhaustive() const noexcept { return exhaustive_; }
  constexpr ReadOnlyRange<OneOfMemberDescriptor> members() const noexcept { return members_; }
};
struct ConstraintDescriptor { const std::string_view rule; const Options parameters; };
class MessageDescriptor {
  std::string_view name_,qualified_,fingerprint_;
  ReadOnlyRange<FieldDescriptor> fields_;
  ReadOnlyRange<OneOfDescriptor> groups_;
  ReadOnlyRange<ConstraintDescriptor> constraints_;
  ReadOnlyRange<long long> reserved_numbers_;
  ReadOnlyRange<std::string_view> reserved_names_;
  std::optional<long long> next_id_;
  Options options_,effective_;
  std::uint64_t frozen_;
public:
  consteval MessageDescriptor(std::string_view name,std::string_view qualified,ReadOnlyRange<FieldDescriptor> fields,
    ReadOnlyRange<OneOfDescriptor> groups,ReadOnlyRange<ConstraintDescriptor> constraints,
    ReadOnlyRange<long long> numbers,ReadOnlyRange<std::string_view> names,std::optional<long long> next,
    Options options,Options effective,std::string_view fingerprint) noexcept
    : name_(name),qualified_(qualified),fingerprint_(fingerprint),fields_(fields),groups_(groups),constraints_(constraints),
      reserved_numbers_(numbers),reserved_names_(names),next_id_(next),options_(options),effective_(effective),
      frozen_(descriptor_detail::frozen_text(name)+descriptor_detail::frozen_text(qualified)+descriptor_detail::frozen_text(fingerprint)+descriptor_detail::frozen_options(options)+descriptor_detail::frozen_options(effective)) {
      for(const auto& field:fields)frozen_+=descriptor_detail::frozen_text(field.name())+static_cast<std::uint64_t>(field.number());
      for(const auto& group:groups)frozen_+=descriptor_detail::frozen_text(group.controlling_field());
      for(const auto& rule:constraints)frozen_+=descriptor_detail::frozen_text(rule.rule)+descriptor_detail::frozen_options(rule.parameters);
      for(auto number:numbers)frozen_+=static_cast<std::uint64_t>(number);
      for(auto reserved:names)frozen_+=descriptor_detail::frozen_text(reserved);
    }
  constexpr std::string_view name() const noexcept { return name_; }
  constexpr std::string_view qualified_name() const noexcept { return qualified_; }
  constexpr std::string_view fingerprint() const noexcept { return fingerprint_; }
  constexpr unsigned descriptor_contract_version() const noexcept { return 1; }
  constexpr auto fields() const noexcept { return fields_; }
  constexpr auto oneofs() const noexcept { return groups_; }
  constexpr auto constraints() const noexcept { return constraints_; }
  constexpr auto reserved_numbers() const noexcept { return reserved_numbers_; }
  constexpr auto reserved_names() const noexcept { return reserved_names_; }
  constexpr auto next_id() const noexcept { return next_id_; }
  constexpr auto options() const noexcept { return options_; }
  constexpr auto effective_options() const noexcept { return effective_; }
};
struct SchemaDescriptor {
  const unsigned descriptor_contract_version, ir_version;
  const std::string_view identity;
  const ReadOnlyRange<const MessageDescriptor& (*)() noexcept> messages;
  const ReadOnlyRange<const EnumDescriptor& (*)() noexcept> enums;
  const Options options, effective_options;
  consteval SchemaDescriptor(unsigned descriptor,unsigned ir,std::string_view name,
      ReadOnlyRange<const MessageDescriptor& (*)() noexcept> message_values,
      ReadOnlyRange<const EnumDescriptor& (*)() noexcept> enum_values,Options declared,Options effective)
    : descriptor_contract_version(descriptor),ir_version(ir),identity(name),messages(message_values),enums(enum_values),options(declared),effective_options(effective),
      frozen_(descriptor_detail::frozen_text(name)+descriptor_detail::frozen_options(declared)+descriptor_detail::frozen_options(effective)) {
      for(auto accessor:message_values)if(accessor)++frozen_;
      for(auto accessor:enum_values)if(accessor)++frozen_;
    }
private:
  std::uint64_t frozen_;
};
namespace descriptor_detail {
struct ValueOps;
template<class T> const ValueOps& operations() noexcept;
}
class ValueRef {
  const void* value_;
  const descriptor_detail::ValueOps* ops_;
  ValueRef(const void* value,const descriptor_detail::ValueOps& ops) noexcept : value_(value),ops_(&ops) {}
public:
  template<class T> static ValueRef borrow(const T& value) noexcept { return {&value,descriptor_detail::operations<T>()}; }
  bool present() const noexcept;
  TypeKind kind() const noexcept;
  long long integer() const noexcept;
  double floating() const noexcept;
  bool boolean() const noexcept;
  std::string_view text() const noexcept;
  const SchemaBinding& binding() const noexcept;
  const EnumDescriptor& enumeration() const noexcept;
  std::size_t size() const noexcept;
  ValueRef item(std::size_t i) const noexcept;
  ValueRef key(std::size_t i) const noexcept;
  const void* identity() const noexcept;
  ValueRef field(std::size_t i) const noexcept;
};
struct FieldBinding { const ValueRef (*const read)(const void*) noexcept; };
struct SchemaBinding {
  const MessageDescriptor& (*const descriptor)() noexcept;
  const ReadOnlyRange<FieldBinding> fields;
  const SchemaDescriptor& (*const schema)() noexcept;
  consteval SchemaBinding(const MessageDescriptor& (*description)() noexcept,ReadOnlyRange<FieldBinding> accessors,const SchemaDescriptor& (*registry)() noexcept)
    : descriptor(description),fields(accessors),schema(registry),count_(0) {for(const auto& field:accessors)if(field.read)++count_;}
private:
  std::size_t count_;
};
template<class T> struct EnumTraits; // Generated enum owner provides specialization.
template<class T> concept CompatibleMessage = requires {
  { T::descriptor() } noexcept -> std::same_as<const MessageDescriptor&>;
  { T::taut_binding() } noexcept -> std::same_as<const SchemaBinding&>;
};
template<class T> concept CompatibleEnum = requires {
  { EnumTraits<T>::descriptor() } noexcept -> std::same_as<const EnumDescriptor&>;
};
namespace descriptor_detail {
struct ValueOps {
  bool (*present)(const void*) noexcept;
  TypeKind kind;
  long long (*integer)(const void*) noexcept;
  double (*floating)(const void*) noexcept;
  bool (*boolean)(const void*) noexcept;
  std::string_view (*text)(const void*) noexcept;
  const SchemaBinding& (*binding)() noexcept;
  const EnumDescriptor& (*enumeration)() noexcept;
  std::size_t (*size)(const void*) noexcept;
  ValueRef (*item)(const void*,std::size_t) noexcept;
  ValueRef (*key)(const void*,std::size_t) noexcept;
  const void* (*unwrap)(const void*) noexcept;
};
template<class T> struct Unwrap { using type=T; static const T* get(const T& value) noexcept { return &value; } };
template<class T> struct Unwrap<std::optional<T>> { using type=typename Unwrap<T>::type; static const type* get(const std::optional<T>& v) noexcept { return v ? Unwrap<T>::get(*v) : nullptr; } };
template<class T> struct Unwrap<std::shared_ptr<T>> { using type=T; static const T* get(const std::shared_ptr<T>& v) noexcept { return v.get(); } };
template<class T> struct Collection { static constexpr bool list=false,map=false; };
template<class T,class A> struct Collection<std::vector<T,A>> { static constexpr bool list=true,map=false; };
template<class K,class V,class C,class A> struct Collection<std::map<K,V,C,A>> { static constexpr bool list=false,map=true; };
template<class T> const ValueOps& operations() noexcept {
  using U=typename Unwrap<T>::type;
  static const ValueOps ops=[] {
    ValueOps o{};
    o.unwrap=[](const void* p) noexcept -> const void* { return Unwrap<T>::get(*static_cast<const T*>(p)); };
    o.present=[](const void* p) noexcept { return Unwrap<T>::get(*static_cast<const T*>(p))!=nullptr; };
    if constexpr (std::is_enum_v<U>) {
      o.kind=TypeKind::Enum; o.enumeration=EnumTraits<U>::descriptor;
      o.integer=[](const void* p) noexcept { return static_cast<long long>(*Unwrap<T>::get(*static_cast<const T*>(p))); };
    } else if constexpr (std::is_same_v<U,bool>) {
      o.kind=TypeKind::Bool; o.boolean=[](const void* p) noexcept { return *Unwrap<T>::get(*static_cast<const T*>(p)); };
    } else if constexpr (std::is_integral_v<U>) {
      o.kind=TypeKind::Int; o.integer=[](const void* p) noexcept { return static_cast<long long>(*Unwrap<T>::get(*static_cast<const T*>(p))); };
    } else if constexpr (std::is_floating_point_v<U>) {
      o.kind=TypeKind::Float; o.floating=[](const void* p) noexcept { return static_cast<double>(*Unwrap<T>::get(*static_cast<const T*>(p))); };
    } else if constexpr (std::is_same_v<U,std::string_view> || std::is_same_v<U,std::string>) {
      o.kind=TypeKind::String; o.text=[](const void* p) noexcept -> std::string_view { return *Unwrap<T>::get(*static_cast<const T*>(p)); };
    } else if constexpr (Collection<U>::list || Collection<U>::map) {
      o.kind=Collection<U>::list?TypeKind::List:TypeKind::Map;
      o.size=[](const void* p) noexcept { return Unwrap<T>::get(*static_cast<const T*>(p))->size(); };
      if constexpr(Collection<U>::list) {
        if constexpr(std::is_same_v<typename U::value_type,bool>) {
          o.item=[](const void* p,std::size_t i) noexcept { static constexpr bool values[]{false,true};return ValueRef::borrow(values[(*Unwrap<T>::get(*static_cast<const T*>(p)))[i]?1:0]); };
        } else o.item=[](const void* p,std::size_t i) noexcept { return ValueRef::borrow((*Unwrap<T>::get(*static_cast<const T*>(p)))[i]); };
      } else {
        o.item=[](const void* p,std::size_t i) noexcept { auto it=Unwrap<T>::get(*static_cast<const T*>(p))->begin();std::advance(it,i);return ValueRef::borrow(it->second); };
        o.key=[](const void* p,std::size_t i) noexcept { auto it=Unwrap<T>::get(*static_cast<const T*>(p))->begin();std::advance(it,i);return ValueRef::borrow(it->first); };
      }
    } else { o.kind=TypeKind::Message; o.binding=U::taut_binding; }
    return o;
  }();
  return ops;
}
}
inline bool ValueRef::present() const noexcept { return ops_->present(value_); }
inline TypeKind ValueRef::kind() const noexcept { return ops_->kind; }
inline long long ValueRef::integer() const noexcept { return ops_->integer(value_); }
inline double ValueRef::floating() const noexcept { return ops_->floating(value_); }
inline bool ValueRef::boolean() const noexcept { return ops_->boolean(value_); }
inline std::string_view ValueRef::text() const noexcept { return ops_->text(value_); }
inline const SchemaBinding& ValueRef::binding() const noexcept { return ops_->binding(); }
inline const EnumDescriptor& ValueRef::enumeration() const noexcept { return ops_->enumeration(); }
inline std::size_t ValueRef::size() const noexcept { return ops_->size(value_); }
inline ValueRef ValueRef::item(std::size_t i) const noexcept { return ops_->item(value_,i); }
inline ValueRef ValueRef::key(std::size_t i) const noexcept { return ops_->key(value_,i); }
inline const void* ValueRef::identity() const noexcept { return ops_->unwrap(value_); }
inline ValueRef ValueRef::field(std::size_t i) const noexcept { return binding().fields[i].read(identity()); }
namespace descriptor_detail {
struct TypeAncestor {const TypeDescriptor* value;const TypeAncestor* parent;};
inline void check_type(const TypeDescriptor& type,const TypeAncestor* ancestors=nullptr) {
  for(auto p=ancestors;p;p=p->parent)if(p->value==&type)throw std::logic_error("cyclic C++ collection descriptor configuration; regenerate");
  const TypeAncestor current{&type,ancestors};
  const bool primitive=type.kind==TypeKind::Int||type.kind==TypeKind::String||type.kind==TypeKind::Bool||type.kind==TypeKind::Bytes||type.kind==TypeKind::Float;
  bool valid=false;
  if(primitive)valid=!type.element&&!type.key&&!type.value&&!type.message&&!type.enumeration;
  if(type.kind==TypeKind::Message)valid=type.message&&!type.enumeration&&!type.element&&!type.key&&!type.value&&type.message().descriptor_contract_version()==1;
  if(type.kind==TypeKind::Enum)valid=type.enumeration&&!type.message&&!type.element&&!type.key&&!type.value&&type.enumeration().descriptor_contract_version()==1;
  if(type.kind==TypeKind::List) {valid=type.element&&!type.key&&!type.value&&!type.message&&!type.enumeration;if(valid)check_type(*type.element,&current);}
  if(type.kind==TypeKind::Map) {valid=type.key&&type.value&&!type.element&&!type.message&&!type.enumeration;
    if(valid) {check_type(*type.key,&current);check_type(*type.value,&current);valid=type.key->kind==TypeKind::Int||type.key->kind==TypeKind::String||type.key->kind==TypeKind::Bool;}}
  if(!valid)throw std::logic_error("incompatible C++ descriptor kind/link/version; regenerate dependency");
}
inline const FieldDescriptor* find_field(const MessageDescriptor& descriptor,std::string_view name) noexcept {
  for(const auto& field:descriptor.fields())if(field.name()==name)return &field;return nullptr;
}
inline void check_message(const MessageDescriptor& descriptor) {
  if(descriptor.descriptor_contract_version()!=1)throw std::logic_error("incompatible C++ message descriptor contract; regenerate");
  long long previous=0;
  for(const auto& field:descriptor.fields()) {
    if(field.number()<=previous || (field.presence()!="required"&&field.presence()!="nullable"&&field.presence()!="missing_ok"))throw std::logic_error("malformed C++ field descriptor order/presence; regenerate");
    previous=field.number();check_type(field.type());
  }
  if(descriptor.constraints().size()!=descriptor.oneofs().size())throw std::logic_error("incomplete C++ constraint grammar; regenerate");
  for(const auto& constraint:descriptor.constraints()) {
    if(constraint.rule!="taut.oneof.v1" || constraint.parameters.size()!=1 || constraint.parameters[0].name!="controlling_field" || constraint.parameters[0].value.tag!=Fact::Tag::String)
      throw std::logic_error("unsupported/malformed C++ constraint grammar; require taut.oneof.v1 controlling_field string; regenerate");
    std::size_t matches=0;
    for(const auto& group:descriptor.oneofs())if(group.controlling_field()==constraint.parameters[0].value.text)++matches;
    if(matches!=1)throw std::logic_error("malformed C++ constraint/group association; regenerate");
  }
  for(const auto& group:descriptor.oneofs()) {
    const auto* control=find_field(descriptor,group.controlling_field());
    if(!control || control->type().kind!=TypeKind::Enum || &control->type().enumeration()!=&group.enumeration() || control->presence()!="required" || control->virtual_field()!=group.virtual_field() || control->transient())
      throw std::logic_error("malformed C++ oneof controlling field; regenerate");
    if(group.members().size()!=group.enumeration().members().size())throw std::logic_error("incomplete C++ oneof enum mapping; regenerate");
    for(const auto& member:group.enumeration().members()) {
      std::size_t count=0;
      for(const auto& mapping:group.members())if(mapping.member==member.name) {
        ++count;
        if(mapping.payload.empty()) {if(group.exhaustive())throw std::logic_error("incomplete exhaustive C++ oneof; regenerate");}
        else {auto* payload=find_field(descriptor,mapping.payload);if(!payload||payload->presence()=="required"||payload->virtual_field())throw std::logic_error("malformed C++ oneof payload; regenerate");}
      }
      if(count!=1)throw std::logic_error("malformed C++ oneof nomination; regenerate");
    }
  }
}
inline void check_binding(const SchemaBinding& binding) {
  const auto& schema=binding.schema();
  if(schema.descriptor_contract_version!=1 || schema.ir_version<1 || schema.ir_version>3)throw std::logic_error("unsupported C++ schema descriptor/IR version; regenerate");
  const auto& message=binding.descriptor();check_message(message);
  if(binding.fields.size()!=message.fields().size())throw std::logic_error("incomplete C++ typed field binding; regenerate");
  for(std::size_t i=0;i<binding.fields.size();++i)if(bool(binding.fields[i].read)==message.fields()[i].virtual_field())throw std::logic_error("incompatible C++ virtual/value accessor; regenerate");
}
}
}
