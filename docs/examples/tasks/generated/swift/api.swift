// GENERATED native Swift types + codec — do not edit.
// Pairs with the vendored cbor.swift runtime (same module).

public enum TaskState: Int64 {
    case `open` = 0
    case doing = 1
    case done = 2

    public static func fromCbor(_ wire_c: Cbor) throws -> TaskState {
        let wire_raw = try wire_c.tryInt()
        guard let wire_value = TaskState(rawValue: wire_raw) else {
            throw CborError.unknownEnum("TaskState", wire_raw)
        }
        return wire_value
    }
}

public struct User {
    public var id: Int64
    public var name: String

    public init(id: Int64, name: String) {
        self.id = id
        self.name = name
    }
    public func toCbor() -> Cbor {
        return Cbor.map([(1, Cbor.int(id)), (2, Cbor.text(name))])
    }
    public static func fromCbor(_ wire_c: Cbor) throws -> User {
        return User(
            id: try wire_c.tryGet(1).tryInt(),
            name: try wire_c.tryGet(2).tryText()
        )
    }
    public static let maxDepth: Int = 32
    public static let maxEncodedLen: Int? = nil
    public static func decode(_ wire_bytes: [UInt8]) throws -> User {
        return try Self.fromCbor(Cbor.tryDecode(wire_bytes, maxDepth: Self.maxDepth, maxEncodedLen: Self.maxEncodedLen))
    }
}

public struct Comment {
    public var author: User
    public var text: String

    public init(author: User, text: String) {
        self.author = author
        self.text = text
    }
    public func toCbor() -> Cbor {
        return Cbor.map([(1, author.toCbor()), (2, Cbor.text(text))])
    }
    public static func fromCbor(_ wire_c: Cbor) throws -> Comment {
        return Comment(
            author: try User.fromCbor(wire_c.tryGet(1)),
            text: try wire_c.tryGet(2).tryText()
        )
    }
    public static let maxDepth: Int = 32
    public static let maxEncodedLen: Int? = nil
    public static func decode(_ wire_bytes: [UInt8]) throws -> Comment {
        return try Self.fromCbor(Cbor.tryDecode(wire_bytes, maxDepth: Self.maxDepth, maxEncodedLen: Self.maxEncodedLen))
    }
}

public struct Task {
    public var id: Int64
    public var title: String
    public var state: TaskState
    public var assignee: User?
    public var comments: [Comment]
    public var labels: [String: String]

    public init(id: Int64, title: String, state: TaskState, assignee: User? = nil, comments: [Comment], labels: [String: String]) {
        self.id = id
        self.title = title
        self.state = state
        self.assignee = assignee
        self.comments = comments
        self.labels = labels
    }
    public func toCbor() -> Cbor {
        return Cbor.map([(1, Cbor.int(id)), (2, Cbor.text(title)), (3, Cbor.int(state.rawValue)), (4, (assignee.map { $0.toCbor() } ?? Cbor.null)), (5, Cbor.array(comments.map { $0.toCbor() })), (7, Cbor.array(labels.sorted { $0.key < $1.key }.map { Cbor.map([(1, Cbor.text($0.key)), (2, Cbor.text($0.value))]) }))])
    }
    public static func fromCbor(_ wire_c: Cbor) throws -> Task {
        return Task(
            id: try wire_c.tryGet(1).tryInt(),
            title: try wire_c.tryGet(2).tryText(),
            state: try TaskState.fromCbor(wire_c.tryGet(3)),
            assignee: try { let wire_v = try wire_c.tryGet(4); if wire_v.isNull { return nil }; return try User.fromCbor(wire_v) }(),
            comments: try wire_c.tryGet(5).tryArray().map { try Comment.fromCbor($0) },
            labels: try wire_c.tryGet(7).tryDictionary(key: { try $0.tryText() }, value: { try $0.tryText() })
        )
    }
    public static let maxDepth: Int = 32
    public static let maxEncodedLen: Int? = nil
    public static func decode(_ wire_bytes: [UInt8]) throws -> Task {
        return try Self.fromCbor(Cbor.tryDecode(wire_bytes, maxDepth: Self.maxDepth, maxEncodedLen: Self.maxEncodedLen))
    }
}

public struct Event {
    public var ts: Int64
    public var text: String

    public init(ts: Int64, text: String) {
        self.ts = ts
        self.text = text
    }
    public func toCbor() -> Cbor {
        return Cbor.map([(1, Cbor.int(ts)), (2, Cbor.text(text))])
    }
    public static func fromCbor(_ wire_c: Cbor) throws -> Event {
        return Event(
            ts: try wire_c.tryGet(1).tryInt(),
            text: try wire_c.tryGet(2).tryText()
        )
    }
    public static let maxDepth: Int = 32
    public static let maxEncodedLen: Int? = nil
    public static func decode(_ wire_bytes: [UInt8]) throws -> Event {
        return try Self.fromCbor(Cbor.tryDecode(wire_bytes, maxDepth: Self.maxDepth, maxEncodedLen: Self.maxEncodedLen))
    }
}

