package taut.validation.descriptors;
import java.util.*;
import taut.validation.ConfigurationException;
public final class MessageAdapter<T> {
    private final Class<T> type;
    private final MessageDescriptor descriptor;
    private final List<FieldBinding<T,?>> fields;
    private final Map<String,FieldBinding<T,?>> byName;
    public MessageAdapter(Class<T> type,MessageDescriptor descriptor,List<FieldBinding<T,?>> fields) {
        this.type=Objects.requireNonNull(type); this.descriptor=Objects.requireNonNull(descriptor); this.fields=Snapshots.list(fields);
        Map<String,FieldBinding<T,?>> names=new LinkedHashMap<String,FieldBinding<T,?>>();
        for(FieldBinding<T,?> field:fields) if(names.put(field.descriptor().name(),field)!=null) throw new ConfigurationException("duplicate bound field");
        this.byName=Snapshots.map(names);
    }
    public Class<T> type() { return type; }
    public MessageDescriptor descriptor() { return descriptor; }
    public List<FieldBinding<T,?>> fields() { return fields; }
    public FieldBinding<T,?> field(String name) { return byName.get(name); }
    public void checkPair(T value,MessageDescriptor descriptor) {
        if(value==null || !type.isInstance(value) || descriptor!=this.descriptor) throw new ConfigurationException("value/descriptor/adapter pair mismatch " + this.descriptor.qualifiedName());
    }
    public void check(Set<MessageAdapter<?>> checked) {
        if(!checked.add(this))return;
        if(fields.size()!=descriptor.fields().size()) throw new ConfigurationException("incomplete field binding " + descriptor.name());
        int last=0;
        for(int i=0;i<fields.size();i++) {
            FieldDescriptor f=fields.get(i).descriptor();
            if(f!=descriptor.fields().get(i) || f.number()<=last) throw new ConfigurationException("field order/link mismatch " + descriptor.name());
            last=f.number(); fields.get(i).check(checked);
            checkType(f.type());
        }
        Set<String> controls=new HashSet<String>(), payloads=new HashSet<String>();
        for(OneOfDescriptor g:descriptor.oneofs()) {
            FieldBinding<T,?> f=field(g.controllingField());
            if(f==null || !controls.add(g.controllingField()) || !f.descriptor().type().kind().equals("enum") || f.descriptor().type().enumeration()!=g.enumDescriptor() || f.descriptor().virtual()!=g.virtual() || !f.descriptor().presence().equals("required") || !g.members().keySet().equals(g.enumDescriptor().members().keySet())) throw new ConfigurationException("invalid oneof links " + descriptor.name());
            Set<String> local=new HashSet<String>();
            for(String target:g.members().values()) {
                if(target==null) { if(g.exhaustive()) throw new ConfigurationException("uncovered exhaustive choice"); continue; }
                FieldBinding<T,?> p=field(target);
                if(p==null || p.descriptor().virtual() || p.descriptor().presence().equals("required")) throw new ConfigurationException("invalid oneof payload " + target);
                local.add(target);
            }
            for(String target:local) if(!payloads.add(target)) throw new ConfigurationException("shared oneof payload " + target);
        }
        Set<String> constrained=new HashSet<String>();
        for(ConstraintDescriptor c:descriptor.constraints()) if(!c.rule().equals("taut.oneof.v1") || !constrained.add((String)c.parameters().get("controlling_field"))) throw new ConfigurationException("unsupported/duplicate constraint " + c.rule());
        if(!controls.equals(constrained)) throw new ConfigurationException("oneof constraints mismatch " + descriptor.name());
    }
    private static void checkType(TypeDescriptor t) {
        if(t.kind().equals("message")) { if(t.message().descriptorContractVersion()!=1 || !t.message().name().equals(t.reference()))throw new ConfigurationException("message link mismatch " + t.reference()); }
        if(t.kind().equals("enum") && !t.enumeration().name().equals(t.reference())) throw new ConfigurationException("enum link mismatch " + t.reference());
        if(t.element()!=null) checkType(t.element());
        if(t.key()!=null) { if(!t.key().kind().matches("str|int|bool"))throw new ConfigurationException("invalid map key kind"); checkType(t.key()); checkType(t.value()); }
    }
}
