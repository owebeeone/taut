package taut.validation.descriptors;
import java.util.*;
public final class FieldDescriptor {
    private final String name;
    private final String attribute;
    private final int number;
    private final TypeDescriptor type;
    private final String presence;
    private final boolean transientField;
    private final boolean virtual;
    private final Map<String,Object> options;
    public FieldDescriptor(String name, String attribute, int number, TypeDescriptor type, String presence, boolean transientField, boolean virtual, Map<String,Object> options) {
        this.name = Objects.requireNonNull(name);
        this.attribute = attribute;
        this.number = number;
        this.type = Objects.requireNonNull(type);
        this.presence = Objects.requireNonNull(presence);
        this.transientField = transientField;
        this.virtual = virtual;
        this.options = Snapshots.options(options);
        if (number <= 0 || !(presence.equals("required") || presence.equals("nullable") || presence.equals("missing_ok")) || virtual != (attribute == null)) throw new taut.validation.ConfigurationException("invalid field descriptor " + name);
    }
    public String name() { return name; }
    public String attribute() { return attribute; }
    public int number() { return number; }
    public TypeDescriptor type() { return type; }
    public String presence() { return presence; }
    public boolean transientField() { return transientField; }
    public boolean virtual() { return virtual; }
    public Map<String,Object> options() { return options; }
}
