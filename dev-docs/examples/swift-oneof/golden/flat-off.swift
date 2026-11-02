// GENERATED Swift native codec + mandatory descriptor ABI 1; generator=swift-oneof-reference.1
// taut-foundation-module: 

public enum Choice: Int64 {
    case text = 0
    case number = 1
    case empty = 2

    public static func fromCbor(_ wire_c: Cbor) throws -> Choice {
        let wire_raw = try wire_c.tryInt()
        guard let wire_value = Choice(rawValue: wire_raw) else {
            throw CborError.unknownEnum("Choice", wire_raw)
        }
        return wire_value
    }
}

public struct Content {
    public var kind: Choice
    public var text: String?
    public var number: Int64?

    public init(kind: Choice, text: String? = nil, number: Int64? = nil) {
        self.kind = kind
        self.text = text
        self.number = number
    }
    public func toCbor() -> Cbor {
        return Cbor.map([(1, Cbor.int(kind.rawValue)), (2, (text.map { Cbor.text($0) } ?? Cbor.null)), (3, (number.map { Cbor.int($0) } ?? Cbor.null))])
    }
    public static func fromCbor(_ wire_c: Cbor) throws -> Content {
        return Content(
            kind: try Choice.fromCbor(wire_c.tryGet(1)),
            text: try { let wire_v = try wire_c.tryGet(2); if wire_v.isNull { return nil }; return try wire_v.tryText() }(),
            number: try { let wire_v = try wire_c.tryGet(3); if wire_v.isNull { return nil }; return try wire_v.tryInt() }()
        )
    }
    public static let maxDepth: Int = 32
    public static let maxEncodedLen: Int? = nil
    public static func decode(_ wire_bytes: [UInt8]) throws -> Content {
        return try Self.fromCbor(Cbor.tryDecode(wire_bytes, maxDepth: Self.maxDepth, maxEncodedLen: Self.maxEncodedLen))
    }
}

public extension Choice {
    static let descriptor: EnumDescriptor = {
        _ = TautSchema_bc49e2b6c6f48811.guardOwner
        return TautSchema_bc49e2b6c6f48811.enum0
    }()
    static var schemaDescriptor: SchemaDescriptor { TautSchema_bc49e2b6c6f48811.schema }
}
public extension Content {
    static let descriptor: MessageDescriptor = {
        _ = TautSchema_bc49e2b6c6f48811.guardOwner
        let wire_descriptor = TautSchema_bc49e2b6c6f48811.message0
        wire_descriptor.checkLinks()
        return wire_descriptor
    }()
    static var schemaDescriptor: SchemaDescriptor { TautSchema_bc49e2b6c6f48811.schema }
    static let tautBinding: MessageBinding<Content> = TautSchema_bc49e2b6c6f48811.binding0
}
private enum TautSchema_bc49e2b6c6f48811 {
    static let guardOwner: () = {
        let wire_evidence: FoundationEvidence = requireFoundation("schema_23afcf07d78159aa", "taut.swift.foundation", 1, 1, ["codec.v1", "descriptors.v1", "oneof.v1"])
        precondition(wire_evidence.owner == "taut.swift.foundation" && wire_evidence.descriptor == 1 && wire_evidence.codec == 1 && Set(["codec.v1", "descriptors.v1", "oneof.v1"]).isSubset(of: wire_evidence.capabilities) && foundationOwner == wire_evidence.owner && descriptorContract == 1 && codecContract == 1 && Set(["codec.v1", "descriptors.v1", "oneof.v1"]).isSubset(of: foundationCapabilities()), "incompatible actual selected Swift foundation; regenerate/rebind")
        confirmFoundation(wire_evidence, foundationOwner, descriptorContract, codecContract, foundationCapabilities())
    }()
    static let enum0: EnumDescriptor = EnumDescriptor("Choice", "schema_23afcf07d78159aa.Choice", ["text": 0, "number": 1, "empty": 2], [:], ["text": .object([:]), "number": .object([:]), "empty": .object([:])], "0043217158d0d3371134c0f2560a46aaebdb2789ecdbe74dd0b3dd9571b4811d")
    static let message0: MessageDescriptor = MessageDescriptor("Content", "schema_23afcf07d78159aa.Content", [FieldDescriptor("kind", "kind", 1, .enumeration("Choice", { TautSchema_bc49e2b6c6f48811.enum0 }), "required", false, false, [:]), FieldDescriptor("text", "text", 2, .str, "nullable", false, false, [:]), FieldDescriptor("number", "number", 3, .int, "nullable", false, false, [:])], [OneOfDescriptor("kind", TautSchema_bc49e2b6c6f48811.enum0, false, false, ["text": "text", "number": "number", "empty": ""])], [ConstraintDescriptor("taut.oneof.v1", ["controlling_field": .string("kind")])], [], [], nil, [:], ["max_depth": .int(32), "max_encoded_len": .null], "24402a3846ab9a648c84902bb218c9b3aa511c9376dc3a7c159669a7a84434ab", "struct", Content.self)
    static let binding0: MessageBinding<Content> = MessageBinding(Content.descriptor,
    { wire_value, wire_index in
    switch wire_index {
    case 0: return true
    case 1: return wire_value.text != nil
    case 2: return wire_value.number != nil
    default: return false
    }
    },
    { wire_value, wire_index in
    switch wire_index {
    case 0: return wire_value.kind.rawValue
    default: return nil
    }
    },
    { wire_value, wire_index in
    switch wire_index {
    case 0: return .int(wire_value.kind.rawValue)
    case 1: return wire_value.text.map { wire_item in .string(wire_item) } ?? .null
    case 2: return wire_value.number.map { wire_item in .int(wire_item) } ?? .null
    default: preconditionFailure("Swift primitive read requires stored primitive/enum field")
    }
    },
    { wire_value, wire_index, wire_visitor, wire_path in
    switch wire_index {
    default: return true
    }
    })
    static let schema: SchemaDescriptor = {
        _ = guardOwner
        return SchemaDescriptor(3, "schema_23afcf07d78159aa", ["Content": TautSchema_bc49e2b6c6f48811.message0], ["Choice": TautSchema_bc49e2b6c6f48811.enum0], [:], ["max_depth": .int(32), "max_encoded_len": .null])
    }()
}
