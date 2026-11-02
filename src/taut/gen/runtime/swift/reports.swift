/// Arrays and strings retain native owned value semantics, including nested paths.
public struct ValidationIssue {
    public let code: String
    public let rule: String
    public let path: [PathSegment]
    public let message: String
    public init(_ code: String, _ rule: String, _ path: [PathSegment], _ message: String) {
        self.code = code; self.rule = rule; self.path = path; self.message = message
    }
}
public struct DeferredCheck {
    public let rule: String
    public let path: [PathSegment]
    public let reasonCode: String
    public let message: String
    public init(_ rule: String, _ path: [PathSegment], _ reasonCode: String, _ message: String) {
        self.rule = rule; self.path = path; self.reasonCode = reasonCode; self.message = message
    }
}
public struct ValidationReport {
    public let issues: [ValidationIssue]
    public let deferredChecks: [DeferredCheck]
    public let scope: String
    public init(_ issues: [ValidationIssue] = [], _ deferredChecks: [DeferredCheck] = [], _ scope: String = "recursive") {
        precondition(scope == "local" || scope == "recursive", "invalid validation scope")
        self.issues = issues; self.deferredChecks = deferredChecks; self.scope = scope
    }
    public var isValid: Bool { issues.isEmpty }
    public var isComplete: Bool { deferredChecks.isEmpty }
}
