// Tasks example — build a Task, round-trip it through the generated codec.
// Run: clang++ -std=c++20 -I. example.cpp -o example && ./example
#include "api.hpp"
#include <cstdio>
#include <string_view>
int main() {
    taut::Task task;
    task.id = 1; task.title = "ship taut"; task.state = taut::TaskState::Done;
    task.assignee = taut::User{7, "ann"};
    task.comments = { taut::Comment{ taut::User{2, "bob"}, "lgtm" } };
    task.labels = { {"team", "infra"}, {"area", "wire"} };
    taut::Buf b; task.to_cbor(b);
    std::string_view bytes(reinterpret_cast<const char*>(b.d), b.n);
    // The typed decode from bytes, under Task's bounds (Task::max_depth, Task::max_encoded_len):
    // the value, or a DecodeError.
    auto back = taut::Task::try_decode(bytes);
    taut::Buf b2;
    if (back) {
        back.value.to_cbor(b2);
    }
    bool ok = back && b.n == b2.n;
    for (std::size_t i = 0; ok && i < b.n; i++) {
        ok = b.d[i] == b2.d[i];
    }
    // Decode is fail-closed: bytes cut short are a DecodeError, never undefined behaviour.
    auto cut = taut::Task::try_decode(bytes.substr(0, bytes.size() - 1));
    ok = ok && !cut && cut.error.tag == taut::DecodeErrorTag::Truncated;
    std::printf("cpp: Task round-tripped in %zu bytes (%s)\n", b.n, ok ? "ok" : "MISMATCH");
    return ok ? 0 : 1;
}
