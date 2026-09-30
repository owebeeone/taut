// GENERATED native C++ types by taut/src/taut/gen/cpp.py — do not edit.
#pragma once
#include <cstddef>
#include <map>
#include <optional>
#include <string_view>
#include <utility>
#include <vector>
#include "taut/cbor.hpp"

namespace taut {

enum class TaskState : long long {
  Open = 0,
  Doing = 1,
  Done = 2,
};
inline constexpr long long wire(TaskState v) { return static_cast<long long>(v); }
inline constexpr DecodeResult<TaskState> try_TaskState_from_wire(long long v) {
  switch (v) {
    case 0: return DecodeResult<TaskState>::success(TaskState::Open);
    case 1: return DecodeResult<TaskState>::success(TaskState::Doing);
    case 2: return DecodeResult<TaskState>::success(TaskState::Done);
    default: return DecodeResult<TaskState>::fail(DecodeError::unknown_enum("TaskState", v));
  }
}

struct User {
  long long id;
  std::string_view name;
  static constexpr std::size_t max_depth = 32;
  static constexpr std::optional<std::size_t> max_encoded_len = std::nullopt;
  constexpr void to_cbor(::taut::Buf& __b) const {
    __b.map(2);
    __b.uint(1);
    __b.integer(id);
    __b.uint(2);
    __b.text(name);
  }
  static constexpr ::taut::DecodeResult<::taut::User> try_from_cbor(const ::taut::Cbor& __c) {
    ::taut::User __v{};
    auto __map = __c.try_map();  // a message is a map, even one with no fields
    if (!__map) { return ::taut::DecodeResult<::taut::User>::fail(__map.error); }
    auto __field_1 = __c.try_get(1);
    if (!__field_1) { return ::taut::DecodeResult<::taut::User>::fail(__field_1.error); }
    auto __decoded_1 = (*__field_1.value).try_int();
    if (!__decoded_1) { return ::taut::DecodeResult<::taut::User>::fail(__decoded_1.error); }
    __v.id = __decoded_1.value;
    auto __field_2 = __c.try_get(2);
    if (!__field_2) { return ::taut::DecodeResult<::taut::User>::fail(__field_2.error); }
    auto __decoded_2 = (*__field_2.value).try_text();
    if (!__decoded_2) { return ::taut::DecodeResult<::taut::User>::fail(__decoded_2.error); }
    __v.name = __decoded_2.value;
    return ::taut::DecodeResult<::taut::User>::success(__v);
  }
  static constexpr ::taut::DecodeResult<::taut::User> try_decode(std::string_view __data) {
    auto __tree = ::taut::try_decode(__data, ::taut::User::max_depth, ::taut::User::max_encoded_len);
    if (!__tree) { return ::taut::DecodeResult<::taut::User>::fail(__tree.error); }
    return ::taut::User::try_from_cbor(__tree.value);
  }
};

struct Comment {
  ::taut::User author;
  std::string_view text;
  static constexpr std::size_t max_depth = 32;
  static constexpr std::optional<std::size_t> max_encoded_len = std::nullopt;
  constexpr void to_cbor(::taut::Buf& __b) const {
    __b.map(2);
    __b.uint(1);
    author.to_cbor(__b);
    __b.uint(2);
    __b.text(text);
  }
  static constexpr ::taut::DecodeResult<::taut::Comment> try_from_cbor(const ::taut::Cbor& __c) {
    ::taut::Comment __v{};
    auto __map = __c.try_map();  // a message is a map, even one with no fields
    if (!__map) { return ::taut::DecodeResult<::taut::Comment>::fail(__map.error); }
    auto __field_1 = __c.try_get(1);
    if (!__field_1) { return ::taut::DecodeResult<::taut::Comment>::fail(__field_1.error); }
    auto __decoded_1_msg = ::taut::User::try_from_cbor(*__field_1.value);
    if (!__decoded_1_msg) { return ::taut::DecodeResult<::taut::Comment>::fail(__decoded_1_msg.error); }
    __v.author = __decoded_1_msg.value;
    auto __field_2 = __c.try_get(2);
    if (!__field_2) { return ::taut::DecodeResult<::taut::Comment>::fail(__field_2.error); }
    auto __decoded_2 = (*__field_2.value).try_text();
    if (!__decoded_2) { return ::taut::DecodeResult<::taut::Comment>::fail(__decoded_2.error); }
    __v.text = __decoded_2.value;
    return ::taut::DecodeResult<::taut::Comment>::success(__v);
  }
  static constexpr ::taut::DecodeResult<::taut::Comment> try_decode(std::string_view __data) {
    auto __tree = ::taut::try_decode(__data, ::taut::Comment::max_depth, ::taut::Comment::max_encoded_len);
    if (!__tree) { return ::taut::DecodeResult<::taut::Comment>::fail(__tree.error); }
    return ::taut::Comment::try_from_cbor(__tree.value);
  }
};

struct Task {
  long long id;
  std::string_view title;
  ::taut::TaskState state;
  std::optional<::taut::User> assignee;
  std::vector<::taut::Comment> comments;
  std::map<std::string_view, std::string_view> labels;
  static constexpr std::size_t max_depth = 32;
  static constexpr std::optional<std::size_t> max_encoded_len = std::nullopt;
  void to_cbor(::taut::Buf& __b) const {
    __b.map(6);
    __b.uint(1);
    __b.integer(id);
    __b.uint(2);
    __b.text(title);
    __b.uint(3);
    __b.integer(static_cast<long long>(state));
    __b.uint(4);
    if (assignee.has_value()) { (*assignee).to_cbor(__b); } else { __b.null_(); }
    __b.uint(5);
    __b.array(comments.size());
    for (const auto& __x : comments) { __x.to_cbor(__b); }
    __b.uint(7);
    __b.array(labels.size());
    for (const auto& [__k, __v] : labels) { __b.map(2); __b.uint(1); __b.text(__k); __b.uint(2); __b.text(__v); }
  }
  static ::taut::DecodeResult<::taut::Task> try_from_cbor(const ::taut::Cbor& __c) {
    ::taut::Task __v{};
    auto __map = __c.try_map();  // a message is a map, even one with no fields
    if (!__map) { return ::taut::DecodeResult<::taut::Task>::fail(__map.error); }
    auto __field_1 = __c.try_get(1);
    if (!__field_1) { return ::taut::DecodeResult<::taut::Task>::fail(__field_1.error); }
    auto __decoded_1 = (*__field_1.value).try_int();
    if (!__decoded_1) { return ::taut::DecodeResult<::taut::Task>::fail(__decoded_1.error); }
    __v.id = __decoded_1.value;
    auto __field_2 = __c.try_get(2);
    if (!__field_2) { return ::taut::DecodeResult<::taut::Task>::fail(__field_2.error); }
    auto __decoded_2 = (*__field_2.value).try_text();
    if (!__decoded_2) { return ::taut::DecodeResult<::taut::Task>::fail(__decoded_2.error); }
    __v.title = __decoded_2.value;
    auto __field_3 = __c.try_get(3);
    if (!__field_3) { return ::taut::DecodeResult<::taut::Task>::fail(__field_3.error); }
    auto __decoded_3_wire = (*__field_3.value).try_int();
    if (!__decoded_3_wire) { return ::taut::DecodeResult<::taut::Task>::fail(__decoded_3_wire.error); }
    auto __decoded_3_enum = ::taut::try_TaskState_from_wire(__decoded_3_wire.value);
    if (!__decoded_3_enum) { return ::taut::DecodeResult<::taut::Task>::fail(__decoded_3_enum.error); }
    __v.state = __decoded_3_enum.value;
    auto __field_4 = __c.try_get(4);
    if (!__field_4) { return ::taut::DecodeResult<::taut::Task>::fail(__field_4.error); }
    if (__field_4.value->is_null()) {
      __v.assignee = std::nullopt;
    } else {
      ::taut::User __value_4{};
      auto __decoded_4_msg = ::taut::User::try_from_cbor(*__field_4.value);
      if (!__decoded_4_msg) { return ::taut::DecodeResult<::taut::Task>::fail(__decoded_4_msg.error); }
      __value_4 = __decoded_4_msg.value;
      __v.assignee = __value_4;
    }
    auto __field_5 = __c.try_get(5);
    if (!__field_5) { return ::taut::DecodeResult<::taut::Task>::fail(__field_5.error); }
    auto __decoded_5_arr = (*__field_5.value).try_array();
    if (!__decoded_5_arr) { return ::taut::DecodeResult<::taut::Task>::fail(__decoded_5_arr.error); }
    __v.comments.clear();
    for (const auto& __x : *__decoded_5_arr.value) {
      ::taut::Comment __decoded_5_item{};
      auto __decoded_5_elem_msg = ::taut::Comment::try_from_cbor(__x);
      if (!__decoded_5_elem_msg) { return ::taut::DecodeResult<::taut::Task>::fail(__decoded_5_elem_msg.error); }
      __decoded_5_item = __decoded_5_elem_msg.value;
      __v.comments.push_back(__decoded_5_item);
    }
    auto __field_7 = __c.try_get(7);
    if (!__field_7) { return ::taut::DecodeResult<::taut::Task>::fail(__field_7.error); }
    auto __decoded_7_arr = (*__field_7.value).try_array();
    if (!__decoded_7_arr) { return ::taut::DecodeResult<::taut::Task>::fail(__decoded_7_arr.error); }
    __v.labels.clear();
    for (const auto& __e : *__decoded_7_arr.value) {
      auto __decoded_7_key_cbor = __e.try_get(1);
      if (!__decoded_7_key_cbor) { return ::taut::DecodeResult<::taut::Task>::fail(__decoded_7_key_cbor.error); }
      auto __decoded_7_val_cbor = __e.try_get(2);
      if (!__decoded_7_val_cbor) { return ::taut::DecodeResult<::taut::Task>::fail(__decoded_7_val_cbor.error); }
      std::string_view __decoded_7_key{};
      std::string_view __decoded_7_val{};
      auto __decoded_7_k = (*__decoded_7_key_cbor.value).try_text();
      if (!__decoded_7_k) { return ::taut::DecodeResult<::taut::Task>::fail(__decoded_7_k.error); }
      __decoded_7_key = __decoded_7_k.value;
      if (__v.labels.count(__decoded_7_key) != 0) {
        return ::taut::DecodeResult<::taut::Task>::fail(::taut::DecodeError::duplicate_map_text_key(__decoded_7_key));
      }
      auto __decoded_7_v = (*__decoded_7_val_cbor.value).try_text();
      if (!__decoded_7_v) { return ::taut::DecodeResult<::taut::Task>::fail(__decoded_7_v.error); }
      __decoded_7_val = __decoded_7_v.value;
      __v.labels[__decoded_7_key] = __decoded_7_val;
    }
    return ::taut::DecodeResult<::taut::Task>::success(__v);
  }
  static ::taut::DecodeResult<::taut::Task> try_decode(std::string_view __data) {
    auto __tree = ::taut::try_decode(__data, ::taut::Task::max_depth, ::taut::Task::max_encoded_len);
    if (!__tree) { return ::taut::DecodeResult<::taut::Task>::fail(__tree.error); }
    return ::taut::Task::try_from_cbor(__tree.value);
  }
};

struct Event {
  long long ts;
  std::string_view text;
  static constexpr std::size_t max_depth = 32;
  static constexpr std::optional<std::size_t> max_encoded_len = std::nullopt;
  constexpr void to_cbor(::taut::Buf& __b) const {
    __b.map(2);
    __b.uint(1);
    __b.integer(ts);
    __b.uint(2);
    __b.text(text);
  }
  static constexpr ::taut::DecodeResult<::taut::Event> try_from_cbor(const ::taut::Cbor& __c) {
    ::taut::Event __v{};
    auto __map = __c.try_map();  // a message is a map, even one with no fields
    if (!__map) { return ::taut::DecodeResult<::taut::Event>::fail(__map.error); }
    auto __field_1 = __c.try_get(1);
    if (!__field_1) { return ::taut::DecodeResult<::taut::Event>::fail(__field_1.error); }
    auto __decoded_1 = (*__field_1.value).try_int();
    if (!__decoded_1) { return ::taut::DecodeResult<::taut::Event>::fail(__decoded_1.error); }
    __v.ts = __decoded_1.value;
    auto __field_2 = __c.try_get(2);
    if (!__field_2) { return ::taut::DecodeResult<::taut::Event>::fail(__field_2.error); }
    auto __decoded_2 = (*__field_2.value).try_text();
    if (!__decoded_2) { return ::taut::DecodeResult<::taut::Event>::fail(__decoded_2.error); }
    __v.text = __decoded_2.value;
    return ::taut::DecodeResult<::taut::Event>::success(__v);
  }
  static constexpr ::taut::DecodeResult<::taut::Event> try_decode(std::string_view __data) {
    auto __tree = ::taut::try_decode(__data, ::taut::Event::max_depth, ::taut::Event::max_encoded_len);
    if (!__tree) { return ::taut::DecodeResult<::taut::Event>::fail(__tree.error); }
    return ::taut::Event::try_from_cbor(__tree.value);
  }
};

} // namespace taut
