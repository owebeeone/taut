package taut.validation.descriptors;
import java.util.*;
import java.util.function.Function;
import taut.validation.*;
public final class FieldBinding<T,V> {
    private final FieldDescriptor descriptor;
    private final Function<T,V> read;
    private final ValueAdapter<V> value;
    public FieldBinding(FieldDescriptor descriptor, Function<T,V> read, ValueAdapter<V> value) {
        this.descriptor=Objects.requireNonNull(descriptor); this.read=read; this.value=Objects.requireNonNull(value);
        if(descriptor.type()!=value.descriptor() || descriptor.virtual()!=(read==null)) throw new ConfigurationException("field adapter mismatch " + descriptor.name());
    }
    public FieldDescriptor descriptor() { return descriptor; }
    public V readValue(T receiver) {
        if(read==null) throw new ConfigurationException("virtual field has no value accessor " + descriptor.name());
        return read.apply(receiver);
    }
    public boolean present(T receiver) { return read!=null && read.apply(receiver)!=null; }
    public String enumName(T receiver) { return value.enumName(read.apply(receiver)); }
    public boolean walk(T receiver,Traversal traversal,List<PathSegment> path) {
        if(read==null) return true;
        V v=read.apply(receiver);
        return v==null || value.walk(v,traversal,path);
    }
    public void check(Set<MessageAdapter<?>> checked) { value.check(checked); }
}
