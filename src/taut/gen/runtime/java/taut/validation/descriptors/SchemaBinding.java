package taut.validation.descriptors;
import java.util.*;
import taut.validation.ConfigurationException;
public final class SchemaBinding {
    private final SchemaDescriptor schema;
    private final Map<String,MessageAdapter<?>> messages;
    public SchemaBinding(SchemaDescriptor schema,Map<String,MessageAdapter<?>> messages) {
        this.schema=Objects.requireNonNull(schema); this.messages=Snapshots.map(messages);
        RuntimeContract.require(schema.identity(),RuntimeContract.OWNER,schema.descriptorContractVersion(),1,"descriptors.v1","codec.v1","oneof.v1");
        if(!messages.keySet().equals(schema.messages().keySet()))throw new ConfigurationException("incomplete schema adapters " + schema.identity());
        Set<MessageAdapter<?>> checked=Collections.newSetFromMap(new IdentityHashMap<MessageAdapter<?>,Boolean>());
        for(Map.Entry<String,MessageAdapter<?>> e:messages.entrySet()) {
            if(e.getValue().descriptor()!=schema.messages().get(e.getKey()))throw new ConfigurationException("schema descriptor/adapter mismatch " + e.getKey());
            e.getValue().check(checked);
            for(FieldDescriptor f:e.getValue().descriptor().fields()) checkRegistry(f.type());
        }
    }
    private void checkRegistry(TypeDescriptor type) {
        if(type.kind().equals("message") && schema.messages().get(type.reference())!=type.message()) throw new ConfigurationException("message registry link/owner mismatch " + type.reference());
        if(type.kind().equals("enum") && schema.enums().get(type.reference())!=type.enumeration()) throw new ConfigurationException("enum registry link/owner mismatch " + type.reference());
        if(type.element()!=null) checkRegistry(type.element());
        if(type.key()!=null) {checkRegistry(type.key());checkRegistry(type.value());}
    }
    public SchemaDescriptor schema() { return schema; }
    public Map<String,MessageAdapter<?>> messages() { return messages; }
}
