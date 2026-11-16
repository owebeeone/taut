// Compile with C++ interoperability, the example bridge module and cbor.swift.
import CustomerBigIntBridge
public enum CustomerBigIntAdapter: BigIntAdapter {
    public typealias Value = CustomerBigIntBridge
    public static func isNegative(_ value: Value) -> Bool { value.negative() }
    public static func magnitude(_ value: Value) -> [UInt8] {
        (0..<value.byteCount()).map { value.byteAt($0) }
    }
    public static func fromMagnitude(negative: Bool, bytes: [UInt8]) -> Value {
        bytes.withUnsafeBufferPointer { Value.fromBytes(negative, $0.baseAddress, $0.count) }
    }
}
