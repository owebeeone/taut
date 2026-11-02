package taut.validation;
import java.util.*;
public final class PathSegment {
    private final String kind, fieldName, keyType, keyCborBase64;
    private final Long index;
    public PathSegment(String kind, String fieldName, Long index, String keyType, String keyCborBase64) {
        boolean valid = "field".equals(kind) && fieldName != null && index == null && keyType == null && keyCborBase64 == null
            || "index".equals(kind) && fieldName == null && index != null && index >= 0 && keyType == null && keyCborBase64 == null
            || "key".equals(kind) && fieldName == null && index == null && keyType != null && keyCborBase64 != null;
        if (!valid) throw new IllegalArgumentException("invalid path segment");
        if ("key".equals(kind)) {
            byte[] bytes=Base64.getDecoder().decode(keyCborBase64);
            taut.Cbor key=taut.Cbor.decode(bytes);
            int expected="int".equals(keyType)?taut.Cbor.INT:"str".equals(keyType)?taut.Cbor.TEXT:"bool".equals(keyType)?taut.Cbor.BOOL:-1;
            if (key.kind != expected || !Arrays.equals(bytes,taut.Cbor.encode(key)) || !Base64.getEncoder().encodeToString(bytes).equals(keyCborBase64)) throw new IllegalArgumentException("noncanonical map key");
        }
        this.kind=kind; this.fieldName=fieldName; this.index=index; this.keyType=keyType; this.keyCborBase64=keyCborBase64;
    }
    public static PathSegment forField(String name) { return new PathSegment("field",name,null,null,null); }
    public static PathSegment forIndex(long index) { return new PathSegment("index",null,index,null,null); }
    public static PathSegment forKey(String type, byte[] bytes) { return new PathSegment("key",null,null,type,Base64.getEncoder().encodeToString(bytes)); }
    public String kind() { return kind; }
    public String fieldName() { return fieldName; }
    public Long index() { return index; }
    public String keyType() { return keyType; }
    public String keyCborBase64() { return keyCborBase64; }
}
