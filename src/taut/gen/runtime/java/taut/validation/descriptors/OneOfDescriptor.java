package taut.validation.descriptors;
import java.util.*;
public final class OneOfDescriptor {
    private final String controllingField;
    private final EnumDescriptor enumDescriptor;
    private final boolean virtual;
    private final boolean exhaustive;
    private final Map<String,String> members;
    public OneOfDescriptor(String controllingField, EnumDescriptor enumDescriptor, boolean virtual, boolean exhaustive, Map<String,String> members) {
        this.controllingField = Objects.requireNonNull(controllingField);
        this.enumDescriptor = Objects.requireNonNull(enumDescriptor);
        this.virtual = virtual;
        this.exhaustive = exhaustive;
        this.members = Snapshots.map(members);
        
    }
    public String controllingField() { return controllingField; }
    public EnumDescriptor enumDescriptor() { return enumDescriptor; }
    public boolean virtual() { return virtual; }
    public boolean exhaustive() { return exhaustive; }
    public Map<String,String> members() { return members; }
}
