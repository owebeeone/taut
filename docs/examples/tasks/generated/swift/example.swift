// Tasks example — build a Task, round-trip it through the generated codec.
// Run: swiftc *.swift -o example && ./example
struct RoundTripFailed: Error {}

@main struct Example {
    static func main() throws {
        let task = Task(
            id: 1, title: "ship taut", state: .done,
            assignee: User(id: 7, name: "ann"),
            comments: [Comment(author: User(id: 2, name: "bob"), text: "lgtm")],
            labels: ["team": "infra", "area": "wire"]
        )
        let bytes = encode(task.toCbor())
        // The typed decode from bytes, under Task's bounds (Task.maxDepth, Task.maxEncodedLen).
        let back = try Task.decode(bytes)
        var ok = encode(back.toCbor()) == bytes
        // Decode is fail-closed: bytes cut short throw CborError, never trap.
        do {
            _ = try Task.decode(Array(bytes.dropLast()))
            ok = false
        } catch let error as CborError {
            ok = ok && error == .truncated
        }
        print("swift: Task round-tripped in \(bytes.count) bytes (\(ok ? "ok" : "MISMATCH"))")
        if !ok {
            throw RoundTripFailed()
        }
    }
}
