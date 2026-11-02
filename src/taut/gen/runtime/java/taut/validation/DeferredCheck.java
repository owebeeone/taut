package taut.validation;
import java.util.*;
public final class DeferredCheck {
    private final String rule;
    private final List<PathSegment> path;
    private final String reasonCode;
    private final String message;
    public DeferredCheck(String rule, List<PathSegment> path, String reasonCode, String message) {
        this.rule = Objects.requireNonNull(rule);
        this.path = taut.validation.descriptors.Snapshots.list(path);
        this.reasonCode = Objects.requireNonNull(reasonCode);
        this.message = Objects.requireNonNull(message);
        
    }
    public String rule() { return rule; }
    public List<PathSegment> path() { return path; }
    public String reasonCode() { return reasonCode; }
    public String message() { return message; }
}
