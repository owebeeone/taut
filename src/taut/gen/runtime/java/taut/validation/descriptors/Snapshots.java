package taut.validation.descriptors;
import java.util.*;
/** Defensive snapshots of portable metadata. */
public final class Snapshots {
    private Snapshots() {}
    public static <T> List<T> list(Collection<? extends T> values) {
        List<T> copy = new ArrayList<T>(Objects.requireNonNull(values));
        for(T value:copy) Objects.requireNonNull(value);
        return Collections.unmodifiableList(copy);
    }
    public static <K,V> Map<K,V> map(Map<? extends K,? extends V> values) {
        return Collections.unmodifiableMap(new LinkedHashMap<K,V>(Objects.requireNonNull(values)));
    }
    public static Object freeze(Object value) {
        if (value instanceof Map) {
            Map<Object,Object> copy = new LinkedHashMap<Object,Object>();
            for (Map.Entry<?,?> e : ((Map<?,?>)value).entrySet()) copy.put(freeze(e.getKey()), freeze(e.getValue()));
            return Collections.unmodifiableMap(copy);
        }
        if (value instanceof Collection) {
            List<Object> copy = new ArrayList<Object>();
            for (Object e : (Collection<?>)value) copy.add(freeze(e));
            return Collections.unmodifiableList(copy);
        }
        if (value instanceof byte[]) return new ImmutableBytes((byte[])value);
        if (value instanceof ImmutableBytes) return value;
        if (value == null || value instanceof String || (value instanceof Long || value instanceof Integer || value instanceof Double || value instanceof Float || value instanceof Short || value instanceof Byte) || value instanceof Boolean) return value;
        throw new taut.validation.ConfigurationException("unsupported portable metadata value");
    }
    @SuppressWarnings("unchecked") public static Map<String,Object> options(Map<String,?> values) {
        return (Map<String,Object>)freeze(values);
    }
    public static Map<String,Object> entries(Object... pairs) {
        if (pairs.length % 2 != 0) throw new taut.validation.ConfigurationException("metadata requires key/value pairs");
        Map<String,Object> values = new LinkedHashMap<String,Object>();
        for (int i=0; i<pairs.length; i+=2) {
            String key=(String)pairs[i];
            if(values.containsKey(key)) throw new taut.validation.ConfigurationException("duplicate metadata key " + key);
            values.put(key,pairs[i+1]);
        }
        return options(values);
    }
}
