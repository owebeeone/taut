package taut.validation.descriptors;
import java.util.*;
public final class SchemaDescriptor {
    private final int descriptorContractVersion;
    private final int irVersion;
    private final String identity;
    private final Map<String,MessageDescriptor> messages;
    private final Map<String,EnumDescriptor> enums;
    private final Map<String,Object> options;
    private final Map<String,Object> effectiveOptions;
    public SchemaDescriptor(int descriptorContractVersion, int irVersion, String identity, Map<String,MessageDescriptor> messages, Map<String,EnumDescriptor> enums, Map<String,Object> options, Map<String,Object> effectiveOptions) {
        this.descriptorContractVersion = descriptorContractVersion;
        this.irVersion = irVersion;
        this.identity = Objects.requireNonNull(identity);
        this.messages = Snapshots.map(messages);
        this.enums = Snapshots.map(enums);
        this.options = Snapshots.options(options);
        this.effectiveOptions = Snapshots.options(effectiveOptions);
        if (descriptorContractVersion != 1 || irVersion < 1 || irVersion > 3) throw new taut.validation.ConfigurationException(identity + ": unsupported descriptor/IR contract");
    }
    public int descriptorContractVersion() { return descriptorContractVersion; }
    public int irVersion() { return irVersion; }
    public String identity() { return identity; }
    public Map<String,MessageDescriptor> messages() { return messages; }
    public Map<String,EnumDescriptor> enums() { return enums; }
    public Map<String,Object> options() { return options; }
    public Map<String,Object> effectiveOptions() { return effectiveOptions; }
}
