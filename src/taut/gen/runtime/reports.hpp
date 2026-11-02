// Shared, owned reports. Fallback has no dynamic text/path storage.
#pragma once
#include "taut/descriptors.hpp"
#include <optional>
#include <string>
#include <utility>
#include <vector>
namespace taut::validation {
namespace report_detail {
class Text {
  std::optional<std::string> owned_;
  std::string_view static_;
public:
  explicit Text(std::string value) : owned_(std::move(value)) {}
  struct Static {};
  constexpr Text(Static,std::string_view value) noexcept : static_(value) {}
  std::string_view get() const noexcept { return owned_ ? std::string_view(*owned_) : static_; }
};
}
class PathSegment {
  std::string kind_;
  std::optional<std::string> field_,key_type_,key_;
  std::optional<std::size_t> index_;
  explicit PathSegment(std::string kind) : kind_(std::move(kind)) {}
public:
  static PathSegment for_field(std::string name) { PathSegment p("field");p.field_=std::move(name);return p; }
  static PathSegment for_index(std::size_t index) { PathSegment p("index");p.index_=index;return p; }
  static PathSegment for_key(std::string type,std::string_view canonical_bytes);
  std::string_view kind() const noexcept { return kind_; }
  std::optional<std::string_view> field_name() const noexcept { return field_ ? std::optional<std::string_view>(*field_) : std::nullopt; }
  std::optional<std::size_t> index() const noexcept { return index_; }
  std::optional<std::string_view> key_type() const noexcept { return key_type_ ? std::optional<std::string_view>(*key_type_) : std::nullopt; }
  std::optional<std::string_view> key_cbor_base64() const noexcept { return key_ ? std::optional<std::string_view>(*key_) : std::nullopt; }
};
class ValidationIssue {
  report_detail::Text code_,rule_,message_;
  std::vector<PathSegment> path_;
  struct Fallback {};
  explicit ValidationIssue(Fallback) noexcept :
    code_(report_detail::Text::Static{},"validation.resource_exhausted"),
    rule_(report_detail::Text::Static{},"validation.resource.v1"),
    message_(report_detail::Text::Static{},"validation allocation failed") {}
public:
  ValidationIssue(std::string code,std::string rule,std::vector<PathSegment> path,std::string message)
    : code_(std::move(code)),rule_(std::move(rule)),message_(std::move(message)),path_(std::move(path)) {}
  static const ValidationIssue& resource_exhausted() noexcept { static const ValidationIssue value(Fallback{});return value; }
  std::string_view code() const noexcept { return code_.get(); }
  std::string_view rule() const noexcept { return rule_.get(); }
  ReadOnlyRange<PathSegment> path() const noexcept { return {path_.data(),path_.size()}; }
  std::string_view message() const noexcept { return message_.get(); }
};
class DeferredCheck {
  report_detail::Text rule_,reason_,message_;
  std::vector<PathSegment> path_;
  struct Fallback {};
  explicit DeferredCheck(Fallback) noexcept :
    rule_(report_detail::Text::Static{},"validation.resource.v1"),
    reason_(report_detail::Text::Static{},"validation.resource_exhausted"),
    message_(report_detail::Text::Static{},"validation allocation failed") {}
public:
  DeferredCheck(std::string rule,std::vector<PathSegment> path,std::string reason,std::string message)
    : rule_(std::move(rule)),reason_(std::move(reason)),message_(std::move(message)),path_(std::move(path)) {}
  static const DeferredCheck& resource_exhausted() noexcept { static const DeferredCheck value(Fallback{});return value; }
  std::string_view rule() const noexcept { return rule_.get(); }
  ReadOnlyRange<PathSegment> path() const noexcept { return {path_.data(),path_.size()}; }
  std::string_view reason_code() const noexcept { return reason_.get(); }
  std::string_view message() const noexcept { return message_.get(); }
};
class ValidationReport {
  std::vector<ValidationIssue> issues_;
  std::vector<DeferredCheck> deferred_;
  bool recursive_ = true, fallback_ = false;
public:
  ValidationReport(std::vector<ValidationIssue> issues={},std::vector<DeferredCheck> deferred={},std::string_view scope="recursive")
    : issues_(std::move(issues)),deferred_(std::move(deferred)),recursive_(scope=="recursive") {
      if(scope!="recursive" && scope!="local") throw std::invalid_argument("validation scope must be local or recursive");
    }
  ValidationReport(ValidationReport&&) noexcept = default;
  ValidationReport& operator=(ValidationReport&&) noexcept = default;
  ValidationReport(const ValidationReport&) = default;
  ValidationReport& operator=(const ValidationReport&) = default;
  static ValidationReport resource_exhausted(bool recursive) noexcept {
    // Empty vectors, disengaged optional<string> and static text; no SSO premise.
    ValidationReport r;r.recursive_=recursive;r.fallback_=true;return r;
  }
  ReadOnlyRange<ValidationIssue> issues() const noexcept {
    return fallback_ ? ReadOnlyRange<ValidationIssue>{&ValidationIssue::resource_exhausted(),1} : ReadOnlyRange<ValidationIssue>{issues_.data(),issues_.size()};
  }
  ReadOnlyRange<DeferredCheck> deferred_checks() const noexcept {
    return fallback_ ? ReadOnlyRange<DeferredCheck>{&DeferredCheck::resource_exhausted(),1} : ReadOnlyRange<DeferredCheck>{deferred_.data(),deferred_.size()};
  }
  std::string_view scope() const noexcept { return recursive_?"recursive":"local"; }
  bool is_valid() const noexcept { return issues().empty(); }
  bool is_complete() const noexcept { return deferred_checks().empty(); }
};
namespace report_detail {
inline std::string base64(std::string_view data) {
  constexpr char alphabet[]="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
  std::string out;
  for(std::size_t i=0;i<data.size();i+=3) {
    unsigned n=static_cast<unsigned char>(data[i])<<16;
    if(i+1<data.size())n|=static_cast<unsigned char>(data[i+1])<<8;
    if(i+2<data.size())n|=static_cast<unsigned char>(data[i+2]);
    out.push_back(alphabet[n>>18]);out.push_back(alphabet[(n>>12)&63]);
    out.push_back(i+1<data.size()?alphabet[(n>>6)&63]:'=');out.push_back(i+2<data.size()?alphabet[n&63]:'=');
  }
  return out;
}
// Validate the whole canonical primitive key, without the codec's fixed Buf limit.
inline bool canonical_key(std::string_view type,std::string_view bytes) noexcept {
  if(bytes.empty())return false;
  unsigned first=static_cast<unsigned char>(bytes[0]),major=first>>5,ai=first&31;
  if(type=="bool")return bytes.size()==1 && (first==0xf4 || first==0xf5);
  if((type=="str" && major!=3) || (type=="int" && major>1) || (type!="str" && type!="int"))return false;
  std::size_t count=ai<24?0:ai==24?1:ai==25?2:ai==26?4:ai==27?8:99;
  if(count==99 || bytes.size()<1+count)return false;
  std::uint64_t n=ai<24?ai:0;
  for(std::size_t i=0;i<count;++i)n=(n<<8)|static_cast<unsigned char>(bytes[1+i]);
  if((count==1 && n<24)||(count==2 && n<=255)||(count==4 && n<=65535)||(count==8 && n<=0xffffffffULL))return false;
  if(type=="int")return bytes.size()==1+count && n<=0x7fffffffffffffffULL;
  return n==bytes.size()-1-count;
}
}
inline PathSegment PathSegment::for_key(std::string type,std::string_view bytes) {
  if(!report_detail::canonical_key(type,bytes))throw std::invalid_argument("invalid canonical Taut CBOR key/type");
  PathSegment p("key");p.key_type_=std::move(type);p.key_=report_detail::base64(bytes);return p;
}
}
