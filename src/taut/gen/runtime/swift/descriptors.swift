import Foundation
// Canonical foundation facts. No compiler, schema loader or validation engine.
public let foundationOwner = "taut.swift.foundation"
public let foundationBuild = "swift-oneof-reference.1"
public let descriptorContract = 1
public let codecContract = 1
public let oneOfRule = "taut.oneof.v1"
public func foundationCapabilities() -> Set<String> { ["codec.v1", "descriptors.v1", "oneof.v1"] }
public struct FoundationEvidence {
    public let owner: String
    public let descriptor: Int
    public let codec: Int
    public let capabilities: Set<String>
    public init(_ owner: String, _ descriptor: Int, _ codec: Int, _ capabilities: Set<String>) {
        self.owner = owner; self.descriptor = descriptor; self.codec = codec; self.capabilities = capabilities
    }
}
public func requireFoundation(_ artifact: String, _ owner: String, _ descriptor: Int,
                              _ codec: Int, _ capabilities: Set<String>) -> FoundationEvidence {
    precondition(owner == foundationOwner && descriptor == descriptorContract && codec == codecContract &&
                 capabilities.isSubset(of: foundationCapabilities()), artifact + ": incompatible Swift foundation; regenerate/rebind")
    return FoundationEvidence(foundationOwner, descriptorContract, codecContract, foundationCapabilities())
}
public func confirmFoundation(_ evidence: FoundationEvidence, _ owner: String, _ descriptor: Int,
                              _ codec: Int, _ capabilities: Set<String>) {
    precondition(evidence.owner == "taut.swift.foundation" && owner == evidence.owner && descriptor == 1 && codec == 1 &&
                 evidence.descriptor == descriptor && evidence.codec == codec &&
                 Set(["codec.v1", "descriptors.v1", "oneof.v1"]).isSubset(of: capabilities) &&
                 capabilities == evidence.capabilities, "incompatible actual Swift foundation exports; regenerate/rebind")
}

/// Closed immutable fact values prevent mutable Foundation/Any reference escape.
public indirect enum MetadataValue: Equatable {
    case null, bool(Bool), int(Int64), float(Double), string(String), bytes([UInt8])
    case array([MetadataValue]), object([String: MetadataValue])
}
private func effectiveFacts(_ facts: [String: MetadataValue]) -> [String: MetadataValue] {
    precondition(Set(facts.keys) == Set(["max_depth", "max_encoded_len"]), "incomplete Swift effective codec facts")
    for key in ["max_depth", "max_encoded_len"] {
        if key == "max_encoded_len", facts[key] == .null { continue }
        guard case let .int(n)? = facts[key] else { preconditionFailure("invalid Swift effective codec option " + key) }
        precondition(n > 0 && n <= (key == "max_depth" ? 128 : 2147483647), "invalid Swift effective codec bounds")
    }
    return facts
}
private final class DescriptorLink<T> {
    let name: String
    private let load: () -> T
    private let lock = Foundation.NSLock()
    private var cached: T?
    init(_ name: String, _ load: @escaping () -> T) {
        precondition(!name.isEmpty, "missing Swift descriptor reference")
        self.name = name; self.load = load
    }
    func resolve() -> T {
        lock.lock(); defer { lock.unlock() }
        if let value = cached { return value }
        let value = load(); cached = value; return value
    }
}
public struct TypeDescriptor {
    private indirect enum Storage {
        case primitive(String), message(DescriptorLink<MessageDescriptor>), enumeration(DescriptorLink<EnumDescriptor>)
        case list(TypeDescriptor), map(TypeDescriptor, TypeDescriptor)
    }
    private let storage: Storage
    private init(_ storage: Storage) { self.storage = storage }
    public static let int = Self(.primitive("int"))
    public static let str = Self(.primitive("str"))
    public static let bool = Self(.primitive("bool"))
    public static let bytes = Self(.primitive("bytes"))
    public static let float = Self(.primitive("float"))
    public static func message(_ name: String, _ link: @escaping () -> MessageDescriptor) -> Self {
        Self(.message(DescriptorLink(name, link)))
    }
    public static func enumeration(_ name: String, _ link: @escaping () -> EnumDescriptor) -> Self {
        Self(.enumeration(DescriptorLink(name, link)))
    }
    public static func list(_ element: Self) -> Self { Self(.list(element)) }
    public static func map(_ key: Self, _ value: Self) -> Self {
        precondition(["str", "int", "bool"].contains(key.kind), "invalid Swift map key type")
        return Self(.map(key, value))
    }
    public var kind: String {
        switch storage {
        case let .primitive(kind): return kind
        case .message: return "message"; case .enumeration: return "enum"
        case .list: return "list"; case .map: return "map"
        }
    }
    public var reference: String? {
        switch storage {
        case let .message(link): return link.name
        case let .enumeration(link): return link.name
        default: return nil
        }
    }
    public var element: Self? { if case let .list(t) = storage { return t }; return nil }
    public var key: Self? { if case let .map(k, _) = storage { return k }; return nil }
    public var value: Self? { if case let .map(_, v) = storage { return v }; return nil }
    public func messageDescriptor() -> MessageDescriptor {
        guard case let .message(link) = storage else { preconditionFailure("not a Swift message link") }
        let value = link.resolve()
        precondition(value.name == link.name && value.descriptorContractVersion == 1, "incompatible Swift message link " + link.name)
        return value
    }
    public func enumDescriptor() -> EnumDescriptor {
        guard case let .enumeration(link) = storage else { preconditionFailure("not a Swift enum link") }
        let value = link.resolve()
        precondition(value.name == link.name && value.descriptorContractVersion == 1, "incompatible Swift enum link " + link.name)
        return value
    }
    // Resolve one edge once; never recursively expand another message's fields.
    public func checkLink() {
        switch storage {
        case .message: _ = messageDescriptor()
        case .enumeration: _ = enumDescriptor()
        case let .list(element): element.checkLink()
        case let .map(key, value): key.checkLink(); value.checkLink()
        default: break
        }
    }
}
public struct EnumDescriptor {
    public let name: String
    public let qualifiedName: String
    public let members: [String: Int64]
    public let options: [String: MetadataValue]
    public let memberOptions: [String: MetadataValue]
    public let fingerprint: String
    public let descriptorContractVersion = 1
    public init(_ name: String, _ qualifiedName: String, _ members: [String: Int64],
                _ options: [String: MetadataValue], _ memberOptions: [String: MetadataValue], _ fingerprint: String) {
        precondition(!name.isEmpty && !members.isEmpty && Set(members.values).count == members.count, "invalid Swift enum inventory")
        self.name = name; self.qualifiedName = qualifiedName; self.members = members
        self.options = options; self.memberOptions = memberOptions; self.fingerprint = fingerprint
    }
}
public struct FieldDescriptor {
    public let name: String
    public let access: String
    public let number: Int64
    public let type: TypeDescriptor
    public let presence: String
    public let transient: Bool
    public let virtual: Bool
    public let options: [String: MetadataValue]
    public init(_ name: String, _ access: String, _ number: Int64, _ type: TypeDescriptor,
                _ presence: String, _ transient: Bool, _ virtual: Bool, _ options: [String: MetadataValue]) {
        precondition(!name.isEmpty && number > 0 && ["required", "nullable", "missing_ok"].contains(presence) &&
                     (virtual ? access.isEmpty : !access.isEmpty), "invalid Swift field descriptor " + name)
        self.name = name; self.access = access; self.number = number; self.type = type
        self.presence = presence; self.transient = transient; self.virtual = virtual; self.options = options
    }
}
public struct OneOfDescriptor {
    public let controllingField: String
    public let enumDescriptor: EnumDescriptor
    public let virtual: Bool
    public let exhaustive: Bool
    /// Empty string denotes a normalized payload-free choice.
    public let members: [String: String]
    public init(_ controllingField: String, _ enumeration: EnumDescriptor, _ virtual: Bool,
                _ exhaustive: Bool, _ members: [String: String]) {
        precondition(Set(members.keys) == Set(enumeration.members.keys) &&
                     (!exhaustive || !members.values.contains("")), "incomplete Swift oneof inventory")
        self.controllingField = controllingField; self.enumDescriptor = enumeration
        self.virtual = virtual; self.exhaustive = exhaustive; self.members = members
    }
}
public struct ConstraintDescriptor {
    public let rule: String
    public let parameters: [String: MetadataValue]
    public init(_ rule: String, _ parameters: [String: MetadataValue]) {
        guard rule == oneOfRule, parameters.count == 1,
              case let .string(name)? = parameters["controlling_field"], !name.isEmpty else {
            preconditionFailure("unsupported Swift constraint grammar " + rule)
        }
        self.rule = rule; self.parameters = parameters
    }
}
public struct MessageDescriptor {
    public let name: String
    public let qualifiedName: String
    public let descriptorContractVersion = 1
    public let fields: [FieldDescriptor]
    public let oneofs: [OneOfDescriptor]
    public let constraints: [ConstraintDescriptor]
    public let reservedNumbers: [Int64]
    public let reservedNames: [String]
    public let nextId: Int64?
    public let options: [String: MetadataValue]
    public let effectiveOptions: [String: MetadataValue]
    public let fingerprint: String
    public let nativeRepresentation: String
    internal let boundNativeType: Swift.ObjectIdentifier?
    public let fieldsByName: [String: Int]
    internal let groupAt: [Int: OneOfDescriptor]
    public init(_ name: String, _ qualifiedName: String, _ fields: [FieldDescriptor],
                _ oneofs: [OneOfDescriptor], _ constraints: [ConstraintDescriptor],
                _ reservedNumbers: [Int64], _ reservedNames: [String], _ nextId: Int64?,
                _ options: [String: MetadataValue], _ effectiveOptions: [String: MetadataValue], _ fingerprint: String,
                _ nativeRepresentation: String = "struct", _ nativeType: Any.Type? = nil) {
        precondition(["struct", "class"].contains(nativeRepresentation), "invalid Swift native representation")
        precondition(!name.isEmpty && oneofs.count == constraints.count, "invalid Swift message inventory")
        var byName: [String: Int] = [:]; var groups: [Int: OneOfDescriptor] = [:]; var last: Int64 = 0
        for (i, field) in fields.enumerated() {
            precondition(field.number > last && byName[field.name] == nil, "unordered/duplicate Swift field")
            byName[field.name] = i; last = field.number
        }
        var nominated: [String: String] = [:]
        for group in oneofs {
            guard let i = byName[group.controllingField] else { preconditionFailure("unknown Swift discriminator") }
            let field = fields[i]
            precondition(field.type.kind == "enum", "wrong Swift discriminator category")
            precondition(field.type.reference == group.enumDescriptor.name && field.virtual == group.virtual &&
                         field.presence == "required" && !field.transient && groups[i] == nil, "invalid Swift discriminator")
            groups[i] = group
            for payload in group.members.values where !payload.isEmpty {
                guard let pi = byName[payload] else { preconditionFailure("unknown Swift payload") }
                precondition(fields[pi].presence != "required" && !fields[pi].virtual &&
                             (nominated[payload] == nil || nominated[payload] == group.controllingField), "invalid Swift payload nomination")
                nominated[payload] = group.controllingField
            }
        }
        var checked: Set<String> = []
        for constraint in constraints {
            guard case let .string(ctrl)? = constraint.parameters["controlling_field"],
                  let i = byName[ctrl], groups[i] != nil else { preconditionFailure("Swift constraint/group mismatch") }
            precondition(checked.insert(ctrl).inserted, "duplicate Swift constraint")
        }
        self.name = name; self.qualifiedName = qualifiedName; self.fields = fields; self.oneofs = oneofs
        self.constraints = constraints; self.reservedNumbers = reservedNumbers; self.reservedNames = reservedNames
        self.nextId = nextId; self.options = options; self.effectiveOptions = effectiveFacts(effectiveOptions)
        self.fingerprint = fingerprint; self.fieldsByName = byName; self.groupAt = groups
        self.nativeRepresentation = nativeRepresentation
        self.boundNativeType = nativeType.map { Swift.ObjectIdentifier($0) }
    }
    public func checkLinks() { for field in fields { field.type.checkLink() } }
}
public struct SchemaDescriptor {
    public let descriptorContractVersion = 1
    public let irVersion: Int
    public let identity: String
    public let messages: [String: MessageDescriptor]
    public let enums: [String: EnumDescriptor]
    public let options: [String: MetadataValue]
    public let effectiveOptions: [String: MetadataValue]
    public init(_ irVersion: Int, _ identity: String, _ messages: [String: MessageDescriptor],
                _ enums: [String: EnumDescriptor], _ options: [String: MetadataValue], _ effectiveOptions: [String: MetadataValue]) {
        precondition((1...3).contains(irVersion), "unsupported Swift native IR")
        func check(_ type: TypeDescriptor) {
            switch type.kind {
            case "message":
                let linked = type.messageDescriptor()
                guard let expected = messages[type.reference!] else { preconditionFailure("missing Swift message registry reference") }
                precondition(linked.qualifiedName == expected.qualifiedName && linked.fingerprint == expected.fingerprint &&
                             linked.boundNativeType == expected.boundNativeType, "wrong Swift message registry owner")
            case "enum":
                let linked = type.enumDescriptor()
                guard let expected = enums[type.reference!] else { preconditionFailure("missing Swift enum registry reference") }
                precondition(linked.qualifiedName == expected.qualifiedName && linked.fingerprint == expected.fingerprint,
                             "wrong Swift enum registry owner")
            case "list": check(type.element!)
            case "map": check(type.key!); check(type.value!)
            default: break
            }
        }
        for (name, descriptor) in messages {
            precondition(name == descriptor.name, "wrong Swift message registry category")
            for field in descriptor.fields { check(field.type) }
            for group in descriptor.oneofs {
                precondition(group.enumDescriptor.fingerprint == enums[group.enumDescriptor.name]?.fingerprint &&
                             group.enumDescriptor.qualifiedName == enums[group.enumDescriptor.name]?.qualifiedName,
                             "wrong Swift oneof enum registry owner")
            }
        }
        for (name, descriptor) in enums { precondition(name == descriptor.name, "wrong Swift enum registry category") }
        self.irVersion = irVersion; self.identity = identity; self.messages = messages; self.enums = enums
        self.options = options; self.effectiveOptions = effectiveFacts(effectiveOptions)
    }
}
/// A traversal callback boundary, never a common protocol for generated messages.
public protocol RecordTraversal: Swift.AnyObject {
    func record<V>(_ value: V, _ binding: MessageBinding<V>, _ path: [PathSegment]) -> Bool
    func issue(_ code: String, _ rule: String, _ path: [PathSegment], _ message: String) -> Bool
}
internal struct ReferenceIdentity: Hashable {
    let object: Swift.ObjectIdentifier
    let nativeType: Swift.ObjectIdentifier
    let schemaType: String
    let fingerprint: String
}
public struct MessageBinding<V> {
    public let descriptor: MessageDescriptor
    public let present: (V, Int) -> Bool
    public let enumValue: (V, Int) -> Int64?
    public let read: (V, Int) -> MetadataValue
    public let walk: (V, Int, any RecordTraversal, [PathSegment]) -> Bool
    internal let referenceIdentity: ((V) -> ReferenceIdentity)?
    public init(_ descriptor: MessageDescriptor, _ present: @escaping (V, Int) -> Bool,
                _ enumValue: @escaping (V, Int) -> Int64?, _ read: @escaping (V, Int) -> MetadataValue,
                _ walk: @escaping (V, Int, any RecordTraversal, [PathSegment]) -> Bool) {
        precondition(descriptor.boundNativeType == Swift.ObjectIdentifier(V.self) && descriptor.nativeRepresentation == "struct" &&
                     !(V.self is Swift.AnyObject.Type), "Swift native binding/descriptor type mismatch; regenerate/rebind")
        self.descriptor = descriptor; self.present = present; self.enumValue = enumValue; self.read = read
        self.walk = walk; self.referenceIdentity = nil
    }
    /// Reference adapters use the actual object's identity, never a bridged value.
    public init(reference descriptor: MessageDescriptor, _ present: @escaping (V, Int) -> Bool,
                _ enumValue: @escaping (V, Int) -> Int64?, _ read: @escaping (V, Int) -> MetadataValue,
                _ walk: @escaping (V, Int, any RecordTraversal, [PathSegment]) -> Bool) where V: Swift.AnyObject {
        precondition(descriptor.boundNativeType == Swift.ObjectIdentifier(V.self) && descriptor.nativeRepresentation == "class",
                     "Swift reference binding/descriptor type mismatch; regenerate/rebind")
        self.descriptor = descriptor; self.present = present; self.enumValue = enumValue; self.read = read
        self.walk = walk; self.referenceIdentity = {
            ReferenceIdentity(object: Swift.ObjectIdentifier($0), nativeType: Swift.ObjectIdentifier(V.self),
                              schemaType: descriptor.qualifiedName, fingerprint: descriptor.fingerprint)
        }
    }
}
public func requireMessageDescriptor(_ value: MessageDescriptor, _ fingerprint: String) -> MessageDescriptor {
    precondition(value.fingerprint == fingerprint && value.descriptorContractVersion == 1, "Swift imported child facts mismatch; regenerate/rebind child")
    return value
}
public func requireEnumDescriptor(_ value: EnumDescriptor, _ fingerprint: String) -> EnumDescriptor {
    precondition(value.fingerprint == fingerprint && value.descriptorContractVersion == 1, "Swift imported enum facts mismatch; regenerate/rebind child")
    return value
}
public func requireMessageBinding<V>(_ value: MessageBinding<V>, _ fingerprint: String) -> MessageBinding<V> {
    _ = requireMessageDescriptor(value.descriptor, fingerprint); return value
}
