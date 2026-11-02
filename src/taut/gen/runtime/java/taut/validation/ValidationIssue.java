package taut.validation;
import java.util.*;
public final class ValidationIssue {
    private final String code;
    private final String rule;
    private final List<PathSegment> path;
    private final String message;
    public ValidationIssue(String code, String rule, List<PathSegment> path, String message) {
        this.code = Objects.requireNonNull(code);
        this.rule = Objects.requireNonNull(rule);
        this.path = taut.validation.descriptors.Snapshots.list(path);
        this.message = Objects.requireNonNull(message);
        
    }
    public String code() { return code; }
    public String rule() { return rule; }
    public List<PathSegment> path() { return path; }
    public String message() { return message; }
}
