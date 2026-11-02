package taut.validation.descriptors;
import java.util.*;
public final class MessageDescriptor {
    private final String name;
    private final String qualifiedName;
    private final int descriptorContractVersion;
    private final List<FieldDescriptor> fields;
    private final List<OneOfDescriptor> oneofs;
    private final List<ConstraintDescriptor> constraints;
    private final List<Long> reservedNumbers;
    private final List<String> reservedNames;
    private final Long nextId;
    private final Map<String,Object> options;
    private final Map<String,Object> effectiveOptions;
    private final String fingerprint;
    public MessageDescriptor(String name, String qualifiedName, int descriptorContractVersion, List<FieldDescriptor> fields, List<OneOfDescriptor> oneofs, List<ConstraintDescriptor> constraints, List<Long> reservedNumbers, List<String> reservedNames, Long nextId, Map<String,Object> options, Map<String,Object> effectiveOptions, String fingerprint) {
        this.name = Objects.requireNonNull(name);
        this.qualifiedName = Objects.requireNonNull(qualifiedName);
        this.descriptorContractVersion = descriptorContractVersion;
        this.fields = Snapshots.list(fields);
        this.oneofs = Snapshots.list(oneofs);
        this.constraints = Snapshots.list(constraints);
        this.reservedNumbers = Snapshots.list(reservedNumbers);
        this.reservedNames = Snapshots.list(reservedNames);
        this.nextId = nextId;
        this.options = Snapshots.options(options);
        this.effectiveOptions = Snapshots.options(effectiveOptions);
        this.fingerprint = Objects.requireNonNull(fingerprint);
        if (descriptorContractVersion != 1) throw new taut.validation.ConfigurationException(qualifiedName + ": descriptor contract must be 1, found " + descriptorContractVersion);
    }
    public String name() { return name; }
    public String qualifiedName() { return qualifiedName; }
    public int descriptorContractVersion() { return descriptorContractVersion; }
    public List<FieldDescriptor> fields() { return fields; }
    public List<OneOfDescriptor> oneofs() { return oneofs; }
    public List<ConstraintDescriptor> constraints() { return constraints; }
    public List<Long> reservedNumbers() { return reservedNumbers; }
    public List<String> reservedNames() { return reservedNames; }
    public Long nextId() { return nextId; }
    public Map<String,Object> options() { return options; }
    public Map<String,Object> effectiveOptions() { return effectiveOptions; }
    public String fingerprint() { return fingerprint; }
}
