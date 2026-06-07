// GENERATED native Swift types + codec — do not edit.
// Pairs with the vendored cbor.swift runtime (same module).

public enum TaskState: Int64 {
    case `open` = 0
    case doing = 1
    case done = 2
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
    public static func fromCbor(_ c: Cbor) -> User {
        return User(
            id: c.get(1).intVal,
            name: c.get(2).textVal
        )
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
    public static func fromCbor(_ c: Cbor) -> Comment {
        return Comment(
            author: User.fromCbor(c.get(1)),
            text: c.get(2).textVal
        )
    }
}

public struct Task {
    public var id: Int64
    public var title: String
    public var state: TaskState
    public var assignee: User?
    public var comments: [Comment]

    public init(id: Int64, title: String, state: TaskState, assignee: User? = nil, comments: [Comment]) {
        self.id = id
        self.title = title
        self.state = state
        self.assignee = assignee
        self.comments = comments
    }
    public func toCbor() -> Cbor {
        return Cbor.map([(1, Cbor.int(id)), (2, Cbor.text(title)), (3, Cbor.int(state.rawValue)), (4, (assignee.map { $0.toCbor() } ?? Cbor.null)), (5, Cbor.array(comments.map { $0.toCbor() }))])
    }
    public static func fromCbor(_ c: Cbor) -> Task {
        return Task(
            id: c.get(1).intVal,
            title: c.get(2).textVal,
            state: TaskState(rawValue: c.get(3).intVal)!,
            assignee: { let v = c.get(4); return v.isNull ? nil : User.fromCbor(v) }(),
            comments: c.get(5).arrayVal.map { Comment.fromCbor($0) }
        )
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
    public static func fromCbor(_ c: Cbor) -> Event {
        return Event(
            ts: c.get(1).intVal,
            text: c.get(2).textVal
        )
    }
}

