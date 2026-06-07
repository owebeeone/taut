// GENERATED native C++ types by taut/src/taut/gen/cpp.py — do not edit.
#pragma once
#include <optional>
#include <string_view>
#include <vector>
#include "taut/cbor.hpp"

namespace taut {

enum class TaskState : long long {
  Open = 0,
  Doing = 1,
  Done = 2,
};

struct User {
  long long id;
  std::string_view name;
  constexpr void to_cbor(Buf& b) const {
    b.map(2);
    b.uint(1);
    b.integer(id);
    b.uint(2);
    b.text(name);
  }
  static constexpr User from_cbor(const Cbor& c) {
    User v{};
    v.id = c.get(1).as_int();
    v.name = c.get(2).as_text();
    return v;
  }
};

struct Comment {
  User author;
  std::string_view text;
  constexpr void to_cbor(Buf& b) const {
    b.map(2);
    b.uint(1);
    author.to_cbor(b);
    b.uint(2);
    b.text(text);
  }
  static constexpr Comment from_cbor(const Cbor& c) {
    Comment v{};
    v.author = taut::User::from_cbor(c.get(1));
    v.text = c.get(2).as_text();
    return v;
  }
};

struct Task {
  long long id;
  std::string_view title;
  TaskState state;
  std::optional<User> assignee;
  std::vector<Comment> comments;
  constexpr void to_cbor(Buf& b) const {
    b.map(5);
    b.uint(1);
    b.integer(id);
    b.uint(2);
    b.text(title);
    b.uint(3);
    b.integer(static_cast<long long>(state));
    b.uint(4);
    if (assignee.has_value()) { *assignee.to_cbor(b); } else { b.null_(); }
    b.uint(5);
    b.array(comments.size());
    for (const auto& x : comments) { x.to_cbor(b); }
  }
  static constexpr Task from_cbor(const Cbor& c) {
    Task v{};
    v.id = c.get(1).as_int();
    v.title = c.get(2).as_text();
    v.state = static_cast<TaskState>(c.get(3).as_int());
    { const auto& f = c.get(4); if (!f.is_null()) v.assignee = taut::User::from_cbor(f); }
    for (const auto& x : c.get(5).as_array()) v.comments.push_back(taut::Comment::from_cbor(x));
    return v;
  }
};

struct Event {
  long long ts;
  std::string_view text;
  constexpr void to_cbor(Buf& b) const {
    b.map(2);
    b.uint(1);
    b.integer(ts);
    b.uint(2);
    b.text(text);
  }
  static constexpr Event from_cbor(const Cbor& c) {
    Event v{};
    v.ts = c.get(1).as_int();
    v.text = c.get(2).as_text();
    return v;
  }
};

} // namespace taut
