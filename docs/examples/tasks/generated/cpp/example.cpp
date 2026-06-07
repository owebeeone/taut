// Tasks example — build a Task, round-trip it through the generated codec.
// Run: clang++ -std=c++23 -I. example.cpp -o example && ./example
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
    auto parsed = taut::parse(std::string_view(reinterpret_cast<const char*>(b.d), b.n));
    taut::Buf b2; taut::Task::from_cbor(parsed).to_cbor(b2);
    bool ok = b.n == b2.n;
    for (std::size_t i = 0; ok && i < b.n; i++) ok = b.d[i] == b2.d[i];
    std::printf("cpp: Task round-tripped in %zu bytes (%s)\n", b.n, ok ? "ok" : "MISMATCH");
    return ok ? 0 : 1;
}
