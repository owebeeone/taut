// Tasks example — build a Task, round-trip it through the generated codec.
// Run: swiftc *.swift -o example && ./example
@main struct Example {
    static func main() {
        let task = Task(
            id: 1, title: "ship taut", state: .done,
            assignee: User(id: 7, name: "ann"),
            comments: [Comment(author: User(id: 2, name: "bob"), text: "lgtm")]
        )
        let bytes = encode(task.toCbor())
        let back = Task.fromCbor(decode(bytes))
        let ok = encode(back.toCbor()) == bytes
        print("swift: Task round-tripped in \(bytes.count) bytes (\(ok ? "ok" : "MISMATCH"))")
    }
}
