package taut.validation.descriptors;
import java.util.*;
public final class ConstraintDescriptor {
    private final String rule;
    private final Map<String,Object> parameters;
    public ConstraintDescriptor(String rule, Map<String,Object> parameters) {
        this.rule = Objects.requireNonNull(rule);
        this.parameters = Snapshots.options(parameters);
        
    }
    public String rule() { return rule; }
    public Map<String,Object> parameters() { return parameters; }
}
