package taut.validation;
import java.util.*;
public final class ValidationReport {
    private final List<ValidationIssue> issues;
    private final List<DeferredCheck> deferredChecks;
    private final String scope;
    public ValidationReport(List<ValidationIssue> issues, List<DeferredCheck> deferredChecks, String scope) {
        this.issues = taut.validation.descriptors.Snapshots.list(issues);
        this.deferredChecks = taut.validation.descriptors.Snapshots.list(deferredChecks);
        this.scope = Objects.requireNonNull(scope);
        if (!scope.equals("local") && !scope.equals("recursive")) throw new IllegalArgumentException("scope must be local or recursive");
    }
    public List<ValidationIssue> issues() { return issues; }
    public List<DeferredCheck> deferredChecks() { return deferredChecks; }
    public String scope() { return scope; }
    public boolean isValid() { return issues.isEmpty(); }
    public boolean isComplete() { return deferredChecks.isEmpty(); }
}
