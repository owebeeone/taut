import Foundation

/// Owned value paths, shared by metadata adapters and optional diagnostics.
public struct PathSegment: Equatable {
    public let kind: String
    public let fieldName: String?
    public let index: Int?
    public let keyType: String?
    public let keyCborBase64: String?
    public init(_ kind: String, _ fieldName: String? = nil, _ index: Int? = nil,
                _ keyType: String? = nil, _ keyCborBase64: String? = nil) {
        self.kind = kind; self.fieldName = fieldName; self.index = index
        self.keyType = keyType; self.keyCborBase64 = keyCborBase64
    }
    public static func forField(_ name: String) -> Self { Self("field", name) }
    public static func forIndex(_ index: Int) -> Self {
        precondition(index >= 0, "negative validation path index")
        return Self("index", nil, index)
    }
    public static func forKey(_ type: String, _ bytes: [UInt8]) -> Self {
        precondition(["str", "int", "bool"].contains(type), "unsupported map key category")
        return Self("key", nil, nil, type, Foundation.Data(bytes).base64EncodedString())
    }
}
