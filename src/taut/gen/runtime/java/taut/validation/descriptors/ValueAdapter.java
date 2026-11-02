package taut.validation.descriptors;
import java.util.*;
import java.util.function.*;
import taut.validation.*;
/** Static typed value operations; no field scanning, reflection, or live-field wrappers. */
public abstract class ValueAdapter<T> {
    private final TypeDescriptor descriptor;
    protected ValueAdapter(TypeDescriptor descriptor) { this.descriptor=Objects.requireNonNull(descriptor); }
    public final TypeDescriptor descriptor() { return descriptor; }
    public abstract boolean walk(T value, Traversal traversal, List<PathSegment> path);
    public String enumName(T value) { throw new ConfigurationException("enum read on non-enum adapter"); }
    public void check(Set<MessageAdapter<?>> checked) {}
    public static List<PathSegment> append(List<PathSegment> path, PathSegment segment) {
        List<PathSegment> result=new ArrayList<PathSegment>(path); result.add(segment); return result;
    }
    private static boolean mismatch(Traversal t,List<PathSegment> p) { return t.issue("validation.type_mismatch","validation.shape.v1",p,"expected declared value type"); }
    public static <T> ValueAdapter<T> scalar(final TypeDescriptor desc, final Class<T> type) {
        return new ValueAdapter<T>(desc) {
            public boolean walk(T value, Traversal t, List<PathSegment> p) { return type.isInstance(value) || mismatch(t,p); }
        };
    }
    public static <T> ValueAdapter<T> enumeration(final TypeDescriptor desc, final Class<T> type, final Function<T,String> name) {
        return new ValueAdapter<T>(desc) {
            public String enumName(T value) { return value==null?null:name.apply(type.cast(value)); }
            public boolean walk(T value, Traversal t, List<PathSegment> p) { return type.isInstance(value) || mismatch(t,p); }
        };
    }
    public static <T> ValueAdapter<T> message(final TypeDescriptor desc, final Class<T> type, final Supplier<MessageAdapter<T>> adapter) {
        return new ValueAdapter<T>(desc) {
            public boolean walk(T value, Traversal t,List<PathSegment> p) { return type.isInstance(value)?t.message(type.cast(value),adapter.get(),p):mismatch(t,p); }
            public void check(Set<MessageAdapter<?>> checked) {
                MessageAdapter<T> a=Objects.requireNonNull(adapter.get());
                if(a.descriptor()!=desc.message() || a.type()!=type) throw new ConfigurationException("child descriptor/typed adapter mismatch " + desc.reference());
                a.check(checked);
            }
        };
    }
    public static <E> ValueAdapter<List<E>> list(final TypeDescriptor desc, final ValueAdapter<E> element) {
        return new ValueAdapter<List<E>>(desc) {
            public boolean walk(List<E> value,Traversal t,List<PathSegment> p) {
                if(value==null) return mismatch(t,p);
                if(!t.enter(value,p)) return t.continueAfterCycle();
                try { for(int i=0;i<value.size();i++) if(!element.walk(value.get(i),t,append(p,PathSegment.forIndex(i)))) return false; return true; }
                finally { t.leave(value); }
            }
            public void check(Set<MessageAdapter<?>> checked) { if(desc.element()!=element.descriptor()) throw new ConfigurationException("list adapter descriptor mismatch"); element.check(checked); }
        };
    }
    public static <K,V> ValueAdapter<Map<K,V>> map(final TypeDescriptor desc, final ValueAdapter<K> key, final Function<K,byte[]> encode, final ValueAdapter<V> item) {
        return new ValueAdapter<Map<K,V>>(desc) {
            public boolean walk(Map<K,V> value,Traversal t,List<PathSegment> p) {
                if(value==null) return mismatch(t,p);
                if(!t.enter(value,p)) return t.continueAfterCycle();
                try {
                    List<Map.Entry<byte[],V>> entries=new ArrayList<Map.Entry<byte[],V>>();
                    for(Map.Entry<K,V> e:value.entrySet()) {
                        try { entries.add(new AbstractMap.SimpleImmutableEntry<byte[],V>(encode.apply(e.getKey()),e.getValue())); }
                        catch(ClassCastException | NullPointerException ex) { if(!mismatch(t,p)) return false; }
                    }
                    Collections.sort(entries,(a,b)->compare(a.getKey(),b.getKey()));
                    for(Map.Entry<byte[],V> e:entries) if(!item.walk(e.getValue(),t,append(p,PathSegment.forKey(desc.key().kind(),e.getKey())))) return false;
                    return true;
                } finally { t.leave(value); }
            }
            public void check(Set<MessageAdapter<?>> checked) { if(desc.key()!=key.descriptor() || desc.value()!=item.descriptor()) throw new ConfigurationException("map adapter descriptor mismatch"); key.check(checked); item.check(checked); }
        };
    }
    private static int compare(byte[] a,byte[] b) { for(int i=0;i<Math.min(a.length,b.length);i++) {int c=Integer.compare(a[i]&255,b[i]&255);if(c!=0)return c;} return Integer.compare(a.length,b.length); }
}
