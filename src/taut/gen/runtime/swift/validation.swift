/// One predicate stream supplies collecting and short-circuit modes.
private final class ValidationWalk: RecordTraversal {
    let recursive: Bool
    let fast: Bool
    var issues: [ValidationIssue] = []
    var deferredChecks: [DeferredCheck] = []
    var ancestors: Set<ReferenceIdentity> = []
    init(_ recursive: Bool, _ fast: Bool) { self.recursive = recursive; self.fast = fast }
    func issue(_ code: String, _ rule: String, _ path: [PathSegment], _ message: String) -> Bool {
        if fast { return false }
        issues.append(ValidationIssue(code, rule, path, message)); return true
    }
    func group<V>(_ value: V, _ binding: MessageBinding<V>, _ group: OneOfDescriptor,
                  _ index: Int, _ path: [PathSegment]) -> Bool {
        if group.virtual {
            if fast { return false }
            deferredChecks.append(DeferredCheck(oneOfRule, path + [.forField(group.controllingField)],
                "oneof.virtual_deferred", "virtual selection is not implemented"))
            return true
        }
        guard let tag = binding.enumValue(value, index),
              let member = group.enumDescriptor.members.first(where: { $0.value == tag })?.key else {
            return issue("oneof.invalid_discriminator", oneOfRule,
                         path + [.forField(group.controllingField)], "expected controlling enum member")
        }
        let selected = group.members[member]!
        let payloads = Set(group.members.values.filter { !$0.isEmpty })
        for (i, field) in binding.descriptor.fields.enumerated() where payloads.contains(field.name) {
            let present = binding.present(value, i)
            let code = field.name == selected ? (present ? "" : "oneof.payload_missing")
                                              : (present ? "oneof.payload_unexpected" : "")
            if !code.isEmpty && !issue(code, oneOfRule, path + [.forField(field.name)], "oneof payload presence") { return false }
        }
        return true
    }
    func record<V>(_ value: V, _ binding: MessageBinding<V>, _ path: [PathSegment]) -> Bool {
        let descriptor = binding.descriptor
        descriptor.checkLinks()
        // Value bindings deliberately have no identity: neither addresses of
        // temporary copies nor Array backing stores identify an owned record.
        let identity = binding.referenceIdentity?(value)
        if let identity = identity {
            if ancestors.contains(identity) {
                return issue("validation.ownership_cycle", "validation.shape.v1", path, "active ancestor encountered")
            }
            ancestors.insert(identity)
        }
        defer { if let identity = identity { ancestors.remove(identity) } }
        for (i, field) in descriptor.fields.enumerated() {
            if let group = descriptor.groupAt[i], !self.group(value, binding, group, i, path) { return false }
            if recursive && !field.virtual && descriptor.groupAt[i] == nil && binding.present(value, i) {
                if !binding.walk(value, i, self, path + [.forField(field.name)]) { return false }
            }
        }
        return true
    }
}
public func validateRecord<V>(_ value: V, _ binding: MessageBinding<V>, recursive: Bool = true) -> ValidationReport {
    let walk = ValidationWalk(recursive, false)
    _ = walk.record(value, binding, [])
    return ValidationReport(walk.issues, walk.deferredChecks, recursive ? "recursive" : "local")
}
public func isRecordValid<V>(_ value: V, _ binding: MessageBinding<V>, recursive: Bool = true) -> Bool {
    ValidationWalk(recursive, true).record(value, binding, [])
}
