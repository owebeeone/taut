package taut.validation.descriptors;
import java.util.*;
public final class EnumDescriptor {
    private final String name;
    private final String qualifiedName;
    private final Map<String,Long> members;
    private final Map<String,Object> options;
    private final Map<String,Object> memberOptions;
    private final String fingerprint;
    public EnumDescriptor(String name, String qualifiedName, Map<String,Long> members, Map<String,Object> options, Map<String,Object> memberOptions, String fingerprint) {
        this.name = Objects.requireNonNull(name);
        this.qualifiedName = Objects.requireNonNull(qualifiedName);
        this.members = Snapshots.map(members);
        this.options = Snapshots.options(options);
        this.memberOptions = Snapshots.options(memberOptions);
        this.fingerprint = Objects.requireNonNull(fingerprint);
        
    }
    public String name() { return name; }
    public String qualifiedName() { return qualifiedName; }
    public Map<String,Long> members() { return members; }
    public Map<String,Object> options() { return options; }
    public Map<String,Object> memberOptions() { return memberOptions; }
    public String fingerprint() { return fingerprint; }
}
