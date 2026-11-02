package taut.validation.descriptors;
import java.util.function.Supplier;
import taut.validation.ConfigurationException;
public final class TypeDescriptor {
    private final String kind, reference;
    private final TypeDescriptor element, key, value;
    private final Supplier<MessageDescriptor> message;
    private final Supplier<EnumDescriptor> enumeration;
    public TypeDescriptor(String kind, String reference, TypeDescriptor element, TypeDescriptor key, TypeDescriptor value,
                          Supplier<MessageDescriptor> message, Supplier<EnumDescriptor> enumeration) {
        this.kind=kind; this.reference=reference; this.element=element; this.key=key; this.value=value; this.message=message; this.enumeration=enumeration;
        boolean good = ("int str bool bytes float".contains(kind) && kind.matches("int|str|bool|bytes|float") && reference==null && element==null && key==null && value==null && message==null && enumeration==null)
            || ("message".equals(kind) && reference!=null && message!=null && enumeration==null && element==null && key==null && value==null)
            || ("enum".equals(kind) && reference!=null && enumeration!=null && message==null && element==null && key==null && value==null)
            || ("list".equals(kind) && element!=null && reference==null && key==null && value==null && message==null && enumeration==null)
            || ("map".equals(kind) && key!=null && value!=null && reference==null && element==null && message==null && enumeration==null);
        if(!good) throw new ConfigurationException("invalid TypeDescriptor " + kind);
    }
    public String kind() { return kind; }
    public String reference() { return reference; }
    public TypeDescriptor element() { return element; }
    public TypeDescriptor key() { return key; }
    public TypeDescriptor value() { return value; }
    public MessageDescriptor message() { return message==null?null:java.util.Objects.requireNonNull(message.get(),"unlinked message descriptor"); }
    public EnumDescriptor enumeration() { return enumeration==null?null:java.util.Objects.requireNonNull(enumeration.get(),"unlinked enum descriptor"); }
}
