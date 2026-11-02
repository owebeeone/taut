// GENERATED native Java types + codec; Java 8 foundation ABI.
// generator=java-oneof-reference.1; owner=taut.java.foundation; descriptor=1; codec=1
package taut;

enum Kind {
    TEXT(0L), NUMBER(1L), EMPTY(2L), CHILD(3L), FLAG(4L), ITEMS(5L);
    final long wire;
    Kind(long $w) { this.wire = $w; }
    static Kind fromWire(long $v) {
        for (Kind $e : values()) {
            if ($e.wire == $v) {
                return $e;
            }
        }
        throw Cbor.DecodeError.unknownEnum("Kind", $v);
    }
    public static taut.validation.descriptors.EnumDescriptor descriptor() { return $Taut_ed8ad9be2e8dc2fa.$E0; }
}

class Content {
    public Kind kind;
    public String text;
    public Long number;
    public Content child;
    public Boolean flag;
    public java.util.List<Long> items;
    static final int MAX_DEPTH = 32;
    static final Integer MAX_ENCODED_LEN = null;
    Cbor toCbor() { return Content$Codec.toCbor(this); }
    static Content fromCbor(Cbor $c) { return Content$Codec.fromCbor($c); }
    static Content decode(byte[] $bytes) { return Content$Codec.decode($bytes); }
    public static taut.validation.descriptors.MessageDescriptor descriptor() { return $Taut_ed8ad9be2e8dc2fa.$M0; }
    static taut.validation.descriptors.MessageAdapter<Content> $adapter() { return $Taut_ed8ad9be2e8dc2fa.$A0; }
    public taut.validation.ValidationReport validate() { return validate(true); }
    public taut.validation.ValidationReport validate(boolean $recursive) { return Content$Codec.$validate(this,$recursive); }
    public boolean isValid() { return isValid(true); }
    public boolean isValid(boolean $recursive) { return Content$Codec.$isValid(this,$recursive); }
}

final class Content$Codec {
    private Content$Codec() {}
    static Cbor toCbor(Content $self) {
        java.util.ArrayList<KV> $m = new java.util.ArrayList<KV>();
        $m.add(new KV(1, Cbor.int_($self.kind.wire)));
        $m.add(new KV(2, $self.text != null ? Cbor.text($self.text) : Cbor.NUL));
        $m.add(new KV(3, $self.number != null ? Cbor.int_($self.number) : Cbor.NUL));
        $m.add(new KV(4, $self.child != null ? $self.child.toCbor() : Cbor.NUL));
        $m.add(new KV(5, $self.flag != null ? Cbor.bool($self.flag) : Cbor.NUL));
        $m.add(new KV(6, $self.items != null ? Cbor.arr($self.items.stream().map($e -> Cbor.int_($e)).collect(java.util.stream.Collectors.collectingAndThen(java.util.stream.Collectors.toList(), java.util.Collections::unmodifiableList))) : Cbor.NUL));
        return Cbor.map($m);
    }
    static Content fromCbor(Cbor $c) {
        if ($c.kind != Cbor.MAP) {
            throw Cbor.DecodeError.wrongType("map");
        }
        Content $v = new Content();
        $v.kind = Kind.fromWire($c.get(1).asInt());
        { Cbor $f = $c.get(2); $v.text = $f.isNull() ? null : $f.asText(); }
        { Cbor $f = $c.get(3); $v.number = $f.isNull() ? null : $f.asInt(); }
        { Cbor $f = $c.get(4); $v.child = $f.isNull() ? null : Content.fromCbor($f); }
        { Cbor $f = $c.get(5); $v.flag = $f.isNull() ? null : $f.asBool(); }
        { Cbor $f = $c.get(6); $v.items = $f.isNull() ? null : $f.asArray().stream().map($e -> $e.asInt()).collect(java.util.stream.Collectors.collectingAndThen(java.util.stream.Collectors.toList(), java.util.Collections::unmodifiableList)); }
        return $v;
    }
    static Content decode(byte[] $bytes) {
        return fromCbor(Cbor.decode($bytes, Content.MAX_DEPTH, Content.MAX_ENCODED_LEN));
    }
    static taut.validation.ValidationReport $validate(Content $value, boolean $recursive) { return taut.validation.ValidationEngine.validate($value, $Taut_ed8ad9be2e8dc2fa.$A0, $recursive); }
    static boolean $isValid(Content $value, boolean $recursive) { return taut.validation.ValidationEngine.isValid($value, $Taut_ed8ad9be2e8dc2fa.$A0, $recursive); }
}

class Wrapper {
    public Content child;
    public java.util.List<Content> children;
    public java.util.Map<String, Content> by_text;
    public java.util.Map<Long, Content> by_int;
    public java.util.Map<Boolean, Content> by_bool;
    static final int MAX_DEPTH = 32;
    static final Integer MAX_ENCODED_LEN = null;
    Cbor toCbor() { return Wrapper$Codec.toCbor(this); }
    static Wrapper fromCbor(Cbor $c) { return Wrapper$Codec.fromCbor($c); }
    static Wrapper decode(byte[] $bytes) { return Wrapper$Codec.decode($bytes); }
    public static taut.validation.descriptors.MessageDescriptor descriptor() { return $Taut_ed8ad9be2e8dc2fa.$M1; }
    static taut.validation.descriptors.MessageAdapter<Wrapper> $adapter() { return $Taut_ed8ad9be2e8dc2fa.$A1; }
    public taut.validation.ValidationReport validate() { return validate(true); }
    public taut.validation.ValidationReport validate(boolean $recursive) { return Wrapper$Codec.$validate(this,$recursive); }
    public boolean isValid() { return isValid(true); }
    public boolean isValid(boolean $recursive) { return Wrapper$Codec.$isValid(this,$recursive); }
}

final class Wrapper$Codec {
    private Wrapper$Codec() {}
    static Cbor toCbor(Wrapper $self) {
        java.util.ArrayList<KV> $m = new java.util.ArrayList<KV>();
        $m.add(new KV(1, $self.child.toCbor()));
        $m.add(new KV(2, Cbor.arr($self.children.stream().map($e -> $e.toCbor()).collect(java.util.stream.Collectors.collectingAndThen(java.util.stream.Collectors.toList(), java.util.Collections::unmodifiableList)))));
        $m.add(new KV(3, Cbor.arr(Cbor.sortedByCodePoint($self.by_text).entrySet().stream().map($e -> Cbor.map(java.util.Collections.unmodifiableList(java.util.Arrays.asList(new KV(1, Cbor.text($e.getKey())), new KV(2, $e.getValue().toCbor()))))).collect(java.util.stream.Collectors.collectingAndThen(java.util.stream.Collectors.toList(), java.util.Collections::unmodifiableList)))));
        $m.add(new KV(4, Cbor.arr(new java.util.TreeMap<>($self.by_int).entrySet().stream().map($e -> Cbor.map(java.util.Collections.unmodifiableList(java.util.Arrays.asList(new KV(1, Cbor.int_($e.getKey())), new KV(2, $e.getValue().toCbor()))))).collect(java.util.stream.Collectors.collectingAndThen(java.util.stream.Collectors.toList(), java.util.Collections::unmodifiableList)))));
        $m.add(new KV(5, Cbor.arr(new java.util.TreeMap<>($self.by_bool).entrySet().stream().map($e -> Cbor.map(java.util.Collections.unmodifiableList(java.util.Arrays.asList(new KV(1, Cbor.bool($e.getKey())), new KV(2, $e.getValue().toCbor()))))).collect(java.util.stream.Collectors.collectingAndThen(java.util.stream.Collectors.toList(), java.util.Collections::unmodifiableList)))));
        return Cbor.map($m);
    }
    static Wrapper fromCbor(Cbor $c) {
        if ($c.kind != Cbor.MAP) {
            throw Cbor.DecodeError.wrongType("map");
        }
        Wrapper $v = new Wrapper();
        $v.child = Content.fromCbor($c.get(1));
        $v.children = $c.get(2).asArray().stream().map($e -> Content.fromCbor($e)).collect(java.util.stream.Collectors.collectingAndThen(java.util.stream.Collectors.toList(), java.util.Collections::unmodifiableList));
        $v.by_text = Cbor.decodeMap($c.get(3), $e -> $e.get(1).asText(), $e -> Content.fromCbor($e.get(2)));
        $v.by_int = Cbor.decodeMap($c.get(4), $e -> $e.get(1).asInt(), $e -> Content.fromCbor($e.get(2)));
        $v.by_bool = Cbor.decodeMap($c.get(5), $e -> $e.get(1).asBool(), $e -> Content.fromCbor($e.get(2)));
        return $v;
    }
    static Wrapper decode(byte[] $bytes) {
        return fromCbor(Cbor.decode($bytes, Wrapper.MAX_DEPTH, Wrapper.MAX_ENCODED_LEN));
    }
    static taut.validation.ValidationReport $validate(Wrapper $value, boolean $recursive) { return taut.validation.ValidationEngine.validate($value, $Taut_ed8ad9be2e8dc2fa.$A1, $recursive); }
    static boolean $isValid(Wrapper $value, boolean $recursive) { return taut.validation.ValidationEngine.isValid($value, $Taut_ed8ad9be2e8dc2fa.$A1, $recursive); }
}

class Virtual {
    public String text;
    public Content child;
    static final int MAX_DEPTH = 32;
    static final Integer MAX_ENCODED_LEN = null;
    Cbor toCbor() { return Virtual$Codec.toCbor(this); }
    static Virtual fromCbor(Cbor $c) { return Virtual$Codec.fromCbor($c); }
    static Virtual decode(byte[] $bytes) { return Virtual$Codec.decode($bytes); }
    public static taut.validation.descriptors.MessageDescriptor descriptor() { return $Taut_ed8ad9be2e8dc2fa.$M2; }
    static taut.validation.descriptors.MessageAdapter<Virtual> $adapter() { return $Taut_ed8ad9be2e8dc2fa.$A2; }
    public taut.validation.ValidationReport validate() { return validate(true); }
    public taut.validation.ValidationReport validate(boolean $recursive) { return Virtual$Codec.$validate(this,$recursive); }
    public boolean isValid() { return isValid(true); }
    public boolean isValid(boolean $recursive) { return Virtual$Codec.$isValid(this,$recursive); }
}

final class Virtual$Codec {
    private Virtual$Codec() {}
    static Cbor toCbor(Virtual $self) {
        java.util.ArrayList<KV> $m = new java.util.ArrayList<KV>();
        $m.add(new KV(2, $self.text != null ? Cbor.text($self.text) : Cbor.NUL));
        $m.add(new KV(3, $self.child.toCbor()));
        return Cbor.map($m);
    }
    static Virtual fromCbor(Cbor $c) {
        if ($c.kind != Cbor.MAP) {
            throw Cbor.DecodeError.wrongType("map");
        }
        Virtual $v = new Virtual();
        { Cbor $f = $c.get(2); $v.text = $f.isNull() ? null : $f.asText(); }
        $v.child = Content.fromCbor($c.get(3));
        return $v;
    }
    static Virtual decode(byte[] $bytes) {
        return fromCbor(Cbor.decode($bytes, Virtual.MAX_DEPTH, Virtual.MAX_ENCODED_LEN));
    }
    static taut.validation.ValidationReport $validate(Virtual $value, boolean $recursive) { return taut.validation.ValidationEngine.validate($value, $Taut_ed8ad9be2e8dc2fa.$A2, $recursive); }
    static boolean $isValid(Virtual $value, boolean $recursive) { return taut.validation.ValidationEngine.isValid($value, $Taut_ed8ad9be2e8dc2fa.$A2, $recursive); }
}

class Multi {
    public Kind left;
    public Kind right;
    public String a;
    public Long b;
    static final int MAX_DEPTH = 32;
    static final Integer MAX_ENCODED_LEN = null;
    Cbor toCbor() { return Multi$Codec.toCbor(this); }
    static Multi fromCbor(Cbor $c) { return Multi$Codec.fromCbor($c); }
    static Multi decode(byte[] $bytes) { return Multi$Codec.decode($bytes); }
    public static taut.validation.descriptors.MessageDescriptor descriptor() { return $Taut_ed8ad9be2e8dc2fa.$M3; }
    static taut.validation.descriptors.MessageAdapter<Multi> $adapter() { return $Taut_ed8ad9be2e8dc2fa.$A3; }
    public taut.validation.ValidationReport validate() { return validate(true); }
    public taut.validation.ValidationReport validate(boolean $recursive) { return Multi$Codec.$validate(this,$recursive); }
    public boolean isValid() { return isValid(true); }
    public boolean isValid(boolean $recursive) { return Multi$Codec.$isValid(this,$recursive); }
}

final class Multi$Codec {
    private Multi$Codec() {}
    static Cbor toCbor(Multi $self) {
        java.util.ArrayList<KV> $m = new java.util.ArrayList<KV>();
        $m.add(new KV(1, Cbor.int_($self.left.wire)));
        $m.add(new KV(2, Cbor.int_($self.right.wire)));
        $m.add(new KV(3, $self.a != null ? Cbor.text($self.a) : Cbor.NUL));
        $m.add(new KV(4, $self.b != null ? Cbor.int_($self.b) : Cbor.NUL));
        return Cbor.map($m);
    }
    static Multi fromCbor(Cbor $c) {
        if ($c.kind != Cbor.MAP) {
            throw Cbor.DecodeError.wrongType("map");
        }
        Multi $v = new Multi();
        $v.left = Kind.fromWire($c.get(1).asInt());
        $v.right = Kind.fromWire($c.get(2).asInt());
        { Cbor $f = $c.get(3); $v.a = $f.isNull() ? null : $f.asText(); }
        { Cbor $f = $c.get(4); $v.b = $f.isNull() ? null : $f.asInt(); }
        return $v;
    }
    static Multi decode(byte[] $bytes) {
        return fromCbor(Cbor.decode($bytes, Multi.MAX_DEPTH, Multi.MAX_ENCODED_LEN));
    }
    static taut.validation.ValidationReport $validate(Multi $value, boolean $recursive) { return taut.validation.ValidationEngine.validate($value, $Taut_ed8ad9be2e8dc2fa.$A3, $recursive); }
    static boolean $isValid(Multi $value, boolean $recursive) { return taut.validation.ValidationEngine.isValid($value, $Taut_ed8ad9be2e8dc2fa.$A3, $recursive); }
}

class Plain {
    public long value;
    public byte[] blob;
    public Double ratio;
    static final int MAX_DEPTH = 32;
    static final Integer MAX_ENCODED_LEN = null;
    Cbor toCbor() { return Plain$Codec.toCbor(this); }
    static Plain fromCbor(Cbor $c) { return Plain$Codec.fromCbor($c); }
    static Plain decode(byte[] $bytes) { return Plain$Codec.decode($bytes); }
    public static taut.validation.descriptors.MessageDescriptor descriptor() { return $Taut_ed8ad9be2e8dc2fa.$M4; }
    static taut.validation.descriptors.MessageAdapter<Plain> $adapter() { return $Taut_ed8ad9be2e8dc2fa.$A4; }
    public taut.validation.ValidationReport validate() { return validate(true); }
    public taut.validation.ValidationReport validate(boolean $recursive) { return Plain$Codec.$validate(this,$recursive); }
    public boolean isValid() { return isValid(true); }
    public boolean isValid(boolean $recursive) { return Plain$Codec.$isValid(this,$recursive); }
}

final class Plain$Codec {
    private Plain$Codec() {}
    static Cbor toCbor(Plain $self) {
        java.util.ArrayList<KV> $m = new java.util.ArrayList<KV>();
        $m.add(new KV(1, Cbor.int_($self.value)));
        $m.add(new KV(2, $self.blob != null ? Cbor.bytes($self.blob) : Cbor.NUL));
        $m.add(new KV(3, $self.ratio != null ? Cbor.float_($self.ratio) : Cbor.NUL));
        return Cbor.map($m);
    }
    static Plain fromCbor(Cbor $c) {
        if ($c.kind != Cbor.MAP) {
            throw Cbor.DecodeError.wrongType("map");
        }
        Plain $v = new Plain();
        $v.value = $c.get(1).asInt();
        { Cbor $f = $c.get(2); $v.blob = $f.isNull() ? null : $f.asBytes(); }
        { Cbor $f = $c.get(3); $v.ratio = $f.isNull() ? null : $f.asFloat(); }
        return $v;
    }
    static Plain decode(byte[] $bytes) {
        return fromCbor(Cbor.decode($bytes, Plain.MAX_DEPTH, Plain.MAX_ENCODED_LEN));
    }
    static taut.validation.ValidationReport $validate(Plain $value, boolean $recursive) { return taut.validation.ValidationEngine.validate($value, $Taut_ed8ad9be2e8dc2fa.$A4, $recursive); }
    static boolean $isValid(Plain $value, boolean $recursive) { return taut.validation.ValidationEngine.isValid($value, $Taut_ed8ad9be2e8dc2fa.$A4, $recursive); }
}

final class $Taut_ed8ad9be2e8dc2fa {
    private $Taut_ed8ad9be2e8dc2fa() {}
    private static <T> java.util.Map<String,T> $map(java.util.List<String> $keys,java.util.List<T> $values) { java.util.Map<String,T> $result=new java.util.LinkedHashMap<String,T>(); for(int $i=0;$i<$keys.size();$i++) $result.put($keys.get($i),$values.get($i)); return $result; }
    static { taut.validation.descriptors.RuntimeContract.require("schema_fbbfcaa31eceac80", "taut.java.foundation", 1, 1, "descriptors.v1", "codec.v1", "oneof.v1"); }
    static final taut.validation.descriptors.EnumDescriptor $E0 = new taut.validation.descriptors.EnumDescriptor("Kind", "schema_fbbfcaa31eceac80.Kind", $map(java.util.Arrays.<String>asList("text", "number", "empty", "child", "flag", "items"), java.util.Arrays.<Long>asList(0L, 1L, 2L, 3L, 4L, 5L)), taut.validation.descriptors.Snapshots.entries(), taut.validation.descriptors.Snapshots.entries("text", taut.validation.descriptors.Snapshots.entries(), "number", taut.validation.descriptors.Snapshots.entries(), "empty", taut.validation.descriptors.Snapshots.entries(), "child", taut.validation.descriptors.Snapshots.entries(), "flag", taut.validation.descriptors.Snapshots.entries(), "items", taut.validation.descriptors.Snapshots.entries()), "3ad3851b62312a8d3e291ef91477fe455bac1716dd270507bb78ee6c1172db6e");
    static final taut.validation.descriptors.FieldDescriptor $M0F0 = new taut.validation.descriptors.FieldDescriptor("kind", "kind", 1, new taut.validation.descriptors.TypeDescriptor("enum", "Kind", null, null, null, null, () -> $Taut_ed8ad9be2e8dc2fa.$E0), "required", false, false, taut.validation.descriptors.Snapshots.entries());
    static final taut.validation.descriptors.FieldDescriptor $M0F1 = new taut.validation.descriptors.FieldDescriptor("text", "text", 2, new taut.validation.descriptors.TypeDescriptor("str", null, null, null, null, null, null), "nullable", false, false, taut.validation.descriptors.Snapshots.entries());
    static final taut.validation.descriptors.FieldDescriptor $M0F2 = new taut.validation.descriptors.FieldDescriptor("number", "number", 3, new taut.validation.descriptors.TypeDescriptor("int", null, null, null, null, null, null), "nullable", false, false, taut.validation.descriptors.Snapshots.entries());
    static final taut.validation.descriptors.FieldDescriptor $M0F3 = new taut.validation.descriptors.FieldDescriptor("child", "child", 4, new taut.validation.descriptors.TypeDescriptor("message", "Content", null, null, null, () -> $Taut_ed8ad9be2e8dc2fa.$M0, null), "nullable", false, false, taut.validation.descriptors.Snapshots.entries());
    static final taut.validation.descriptors.FieldDescriptor $M0F4 = new taut.validation.descriptors.FieldDescriptor("flag", "flag", 5, new taut.validation.descriptors.TypeDescriptor("bool", null, null, null, null, null, null), "nullable", false, false, taut.validation.descriptors.Snapshots.entries());
    static final taut.validation.descriptors.FieldDescriptor $M0F5 = new taut.validation.descriptors.FieldDescriptor("items", "items", 6, new taut.validation.descriptors.TypeDescriptor("list", null, new taut.validation.descriptors.TypeDescriptor("int", null, null, null, null, null, null), null, null, null, null), "nullable", false, false, taut.validation.descriptors.Snapshots.entries());
    static final taut.validation.descriptors.FieldDescriptor $M1F0 = new taut.validation.descriptors.FieldDescriptor("child", "child", 1, new taut.validation.descriptors.TypeDescriptor("message", "Content", null, null, null, () -> $Taut_ed8ad9be2e8dc2fa.$M0, null), "required", false, false, taut.validation.descriptors.Snapshots.entries());
    static final taut.validation.descriptors.FieldDescriptor $M1F1 = new taut.validation.descriptors.FieldDescriptor("children", "children", 2, new taut.validation.descriptors.TypeDescriptor("list", null, new taut.validation.descriptors.TypeDescriptor("message", "Content", null, null, null, () -> $Taut_ed8ad9be2e8dc2fa.$M0, null), null, null, null, null), "required", false, false, taut.validation.descriptors.Snapshots.entries());
    static final taut.validation.descriptors.FieldDescriptor $M1F2 = new taut.validation.descriptors.FieldDescriptor("by_text", "by_text", 3, new taut.validation.descriptors.TypeDescriptor("map", null, null, new taut.validation.descriptors.TypeDescriptor("str", null, null, null, null, null, null), new taut.validation.descriptors.TypeDescriptor("message", "Content", null, null, null, () -> $Taut_ed8ad9be2e8dc2fa.$M0, null), null, null), "required", false, false, taut.validation.descriptors.Snapshots.entries());
    static final taut.validation.descriptors.FieldDescriptor $M1F3 = new taut.validation.descriptors.FieldDescriptor("by_int", "by_int", 4, new taut.validation.descriptors.TypeDescriptor("map", null, null, new taut.validation.descriptors.TypeDescriptor("int", null, null, null, null, null, null), new taut.validation.descriptors.TypeDescriptor("message", "Content", null, null, null, () -> $Taut_ed8ad9be2e8dc2fa.$M0, null), null, null), "required", false, false, taut.validation.descriptors.Snapshots.entries());
    static final taut.validation.descriptors.FieldDescriptor $M1F4 = new taut.validation.descriptors.FieldDescriptor("by_bool", "by_bool", 5, new taut.validation.descriptors.TypeDescriptor("map", null, null, new taut.validation.descriptors.TypeDescriptor("bool", null, null, null, null, null, null), new taut.validation.descriptors.TypeDescriptor("message", "Content", null, null, null, () -> $Taut_ed8ad9be2e8dc2fa.$M0, null), null, null), "required", false, false, taut.validation.descriptors.Snapshots.entries());
    static final taut.validation.descriptors.FieldDescriptor $M2F0 = new taut.validation.descriptors.FieldDescriptor("kind", null, 1, new taut.validation.descriptors.TypeDescriptor("enum", "Kind", null, null, null, null, () -> $Taut_ed8ad9be2e8dc2fa.$E0), "required", false, true, taut.validation.descriptors.Snapshots.entries());
    static final taut.validation.descriptors.FieldDescriptor $M2F1 = new taut.validation.descriptors.FieldDescriptor("text", "text", 2, new taut.validation.descriptors.TypeDescriptor("str", null, null, null, null, null, null), "nullable", false, false, taut.validation.descriptors.Snapshots.entries());
    static final taut.validation.descriptors.FieldDescriptor $M2F2 = new taut.validation.descriptors.FieldDescriptor("child", "child", 3, new taut.validation.descriptors.TypeDescriptor("message", "Content", null, null, null, () -> $Taut_ed8ad9be2e8dc2fa.$M0, null), "required", false, false, taut.validation.descriptors.Snapshots.entries());
    static final taut.validation.descriptors.FieldDescriptor $M3F0 = new taut.validation.descriptors.FieldDescriptor("left", "left", 1, new taut.validation.descriptors.TypeDescriptor("enum", "Kind", null, null, null, null, () -> $Taut_ed8ad9be2e8dc2fa.$E0), "required", false, false, taut.validation.descriptors.Snapshots.entries());
    static final taut.validation.descriptors.FieldDescriptor $M3F1 = new taut.validation.descriptors.FieldDescriptor("right", "right", 2, new taut.validation.descriptors.TypeDescriptor("enum", "Kind", null, null, null, null, () -> $Taut_ed8ad9be2e8dc2fa.$E0), "required", false, false, taut.validation.descriptors.Snapshots.entries());
    static final taut.validation.descriptors.FieldDescriptor $M3F2 = new taut.validation.descriptors.FieldDescriptor("a", "a", 3, new taut.validation.descriptors.TypeDescriptor("str", null, null, null, null, null, null), "nullable", false, false, taut.validation.descriptors.Snapshots.entries());
    static final taut.validation.descriptors.FieldDescriptor $M3F3 = new taut.validation.descriptors.FieldDescriptor("b", "b", 4, new taut.validation.descriptors.TypeDescriptor("int", null, null, null, null, null, null), "nullable", false, false, taut.validation.descriptors.Snapshots.entries());
    static final taut.validation.descriptors.FieldDescriptor $M4F0 = new taut.validation.descriptors.FieldDescriptor("value", "value", 1, new taut.validation.descriptors.TypeDescriptor("int", null, null, null, null, null, null), "required", false, false, taut.validation.descriptors.Snapshots.entries());
    static final taut.validation.descriptors.FieldDescriptor $M4F1 = new taut.validation.descriptors.FieldDescriptor("blob", "blob", 2, new taut.validation.descriptors.TypeDescriptor("bytes", null, null, null, null, null, null), "nullable", false, false, taut.validation.descriptors.Snapshots.entries());
    static final taut.validation.descriptors.FieldDescriptor $M4F2 = new taut.validation.descriptors.FieldDescriptor("ratio", "ratio", 3, new taut.validation.descriptors.TypeDescriptor("float", null, null, null, null, null, null), "nullable", false, false, taut.validation.descriptors.Snapshots.entries());
    static final taut.validation.descriptors.MessageDescriptor $M0 = new taut.validation.descriptors.MessageDescriptor("Content", "schema_fbbfcaa31eceac80.Content", 1, java.util.Arrays.<taut.validation.descriptors.FieldDescriptor>asList($M0F0, $M0F1, $M0F2, $M0F3, $M0F4, $M0F5), java.util.Arrays.<taut.validation.descriptors.OneOfDescriptor>asList(new taut.validation.descriptors.OneOfDescriptor("kind", $E0, false, false, $map(java.util.Arrays.<String>asList("text", "number", "empty", "child", "flag", "items"), java.util.Arrays.<String>asList("text", "number", null, "child", "flag", "items")))), java.util.Arrays.<taut.validation.descriptors.ConstraintDescriptor>asList(new taut.validation.descriptors.ConstraintDescriptor("taut.oneof.v1", taut.validation.descriptors.Snapshots.entries("controlling_field", "kind"))), java.util.Arrays.<Long>asList(7L), java.util.Arrays.<String>asList("retired"), 9L, taut.validation.descriptors.Snapshots.entries(), taut.validation.descriptors.Snapshots.entries("max_depth", 32L, "max_encoded_len", null), "d50a6ebd679c9d74bed58b33db4521be66a80919d5b88c25487e3e571bdff023");
    static final taut.validation.descriptors.MessageDescriptor $M1 = new taut.validation.descriptors.MessageDescriptor("Wrapper", "schema_fbbfcaa31eceac80.Wrapper", 1, java.util.Arrays.<taut.validation.descriptors.FieldDescriptor>asList($M1F0, $M1F1, $M1F2, $M1F3, $M1F4), java.util.Arrays.<taut.validation.descriptors.OneOfDescriptor>asList(), java.util.Arrays.<taut.validation.descriptors.ConstraintDescriptor>asList(), java.util.Arrays.<Long>asList(), java.util.Arrays.<String>asList(), null, taut.validation.descriptors.Snapshots.entries(), taut.validation.descriptors.Snapshots.entries("max_depth", 32L, "max_encoded_len", null), "7aab4615d8deb5388ba8dd4ef7cf4a2948446c53c34f12a3ac3aa4ad4ef0d0cb");
    static final taut.validation.descriptors.MessageDescriptor $M2 = new taut.validation.descriptors.MessageDescriptor("Virtual", "schema_fbbfcaa31eceac80.Virtual", 1, java.util.Arrays.<taut.validation.descriptors.FieldDescriptor>asList($M2F0, $M2F1, $M2F2), java.util.Arrays.<taut.validation.descriptors.OneOfDescriptor>asList(new taut.validation.descriptors.OneOfDescriptor("kind", $E0, true, false, $map(java.util.Arrays.<String>asList("text", "number", "empty", "child", "flag", "items"), java.util.Arrays.<String>asList("text", null, null, null, null, null)))), java.util.Arrays.<taut.validation.descriptors.ConstraintDescriptor>asList(new taut.validation.descriptors.ConstraintDescriptor("taut.oneof.v1", taut.validation.descriptors.Snapshots.entries("controlling_field", "kind"))), java.util.Arrays.<Long>asList(), java.util.Arrays.<String>asList(), null, taut.validation.descriptors.Snapshots.entries(), taut.validation.descriptors.Snapshots.entries("max_depth", 32L, "max_encoded_len", null), "9a97979761a5a4b18d847760134abc33fb008c74d6bd6ab4e151414a7b035a94");
    static final taut.validation.descriptors.MessageDescriptor $M3 = new taut.validation.descriptors.MessageDescriptor("Multi", "schema_fbbfcaa31eceac80.Multi", 1, java.util.Arrays.<taut.validation.descriptors.FieldDescriptor>asList($M3F0, $M3F1, $M3F2, $M3F3), java.util.Arrays.<taut.validation.descriptors.OneOfDescriptor>asList(new taut.validation.descriptors.OneOfDescriptor("left", $E0, false, false, $map(java.util.Arrays.<String>asList("text", "number", "empty", "child", "flag", "items"), java.util.Arrays.<String>asList("a", null, null, null, null, null))), new taut.validation.descriptors.OneOfDescriptor("right", $E0, false, false, $map(java.util.Arrays.<String>asList("text", "number", "empty", "child", "flag", "items"), java.util.Arrays.<String>asList(null, "b", null, null, null, null)))), java.util.Arrays.<taut.validation.descriptors.ConstraintDescriptor>asList(new taut.validation.descriptors.ConstraintDescriptor("taut.oneof.v1", taut.validation.descriptors.Snapshots.entries("controlling_field", "left")), new taut.validation.descriptors.ConstraintDescriptor("taut.oneof.v1", taut.validation.descriptors.Snapshots.entries("controlling_field", "right"))), java.util.Arrays.<Long>asList(), java.util.Arrays.<String>asList(), null, taut.validation.descriptors.Snapshots.entries(), taut.validation.descriptors.Snapshots.entries("max_depth", 32L, "max_encoded_len", null), "fe44c71f1c4d5e6c1c59978641317793c5118e98a6ea967bd0b4b645d830646c");
    static final taut.validation.descriptors.MessageDescriptor $M4 = new taut.validation.descriptors.MessageDescriptor("Plain", "schema_fbbfcaa31eceac80.Plain", 1, java.util.Arrays.<taut.validation.descriptors.FieldDescriptor>asList($M4F0, $M4F1, $M4F2), java.util.Arrays.<taut.validation.descriptors.OneOfDescriptor>asList(), java.util.Arrays.<taut.validation.descriptors.ConstraintDescriptor>asList(), java.util.Arrays.<Long>asList(), java.util.Arrays.<String>asList(), null, taut.validation.descriptors.Snapshots.entries(), taut.validation.descriptors.Snapshots.entries("max_depth", 32L, "max_encoded_len", null), "d1e39990ba19514eeadde8435b33567c83cf6ea874efa2e8dd8bc3a89627085b");
    static final taut.validation.descriptors.MessageAdapter<Content> $A0 = new taut.validation.descriptors.MessageAdapter<Content>(Content.class, $M0, java.util.Arrays.<taut.validation.descriptors.FieldBinding<Content,?>>asList(new taut.validation.descriptors.FieldBinding<Content, Kind>($M0F0, $self -> $self.kind, taut.validation.descriptors.ValueAdapter.enumeration($M0F0.type(), Kind.class, $e -> { switch($e) { case TEXT: return "text"; case NUMBER: return "number"; case EMPTY: return "empty"; case CHILD: return "child"; case FLAG: return "flag"; case ITEMS: return "items"; default: throw new taut.validation.ConfigurationException("invalid enum"); } })), new taut.validation.descriptors.FieldBinding<Content, String>($M0F1, $self -> $self.text, taut.validation.descriptors.ValueAdapter.scalar($M0F1.type(), String.class)), new taut.validation.descriptors.FieldBinding<Content, Long>($M0F2, $self -> $self.number, taut.validation.descriptors.ValueAdapter.scalar($M0F2.type(), Long.class)), new taut.validation.descriptors.FieldBinding<Content, Content>($M0F3, $self -> $self.child, taut.validation.descriptors.ValueAdapter.message($M0F3.type(), Content.class, () -> $Taut_ed8ad9be2e8dc2fa.$A0)), new taut.validation.descriptors.FieldBinding<Content, Boolean>($M0F4, $self -> $self.flag, taut.validation.descriptors.ValueAdapter.scalar($M0F4.type(), Boolean.class)), new taut.validation.descriptors.FieldBinding<Content, java.util.List<Long>>($M0F5, $self -> $self.items, taut.validation.descriptors.ValueAdapter.list($M0F5.type(), taut.validation.descriptors.ValueAdapter.scalar($M0F5.type().element(), Long.class)))));
    static final taut.validation.descriptors.MessageAdapter<Wrapper> $A1 = new taut.validation.descriptors.MessageAdapter<Wrapper>(Wrapper.class, $M1, java.util.Arrays.<taut.validation.descriptors.FieldBinding<Wrapper,?>>asList(new taut.validation.descriptors.FieldBinding<Wrapper, Content>($M1F0, $self -> $self.child, taut.validation.descriptors.ValueAdapter.message($M1F0.type(), Content.class, () -> $Taut_ed8ad9be2e8dc2fa.$A0)), new taut.validation.descriptors.FieldBinding<Wrapper, java.util.List<Content>>($M1F1, $self -> $self.children, taut.validation.descriptors.ValueAdapter.list($M1F1.type(), taut.validation.descriptors.ValueAdapter.message($M1F1.type().element(), Content.class, () -> $Taut_ed8ad9be2e8dc2fa.$A0))), new taut.validation.descriptors.FieldBinding<Wrapper, java.util.Map<String, Content>>($M1F2, $self -> $self.by_text, taut.validation.descriptors.ValueAdapter.map($M1F2.type(), taut.validation.descriptors.ValueAdapter.scalar($M1F2.type().key(), String.class), $key -> Cbor.encode(Cbor.text($key)), taut.validation.descriptors.ValueAdapter.message($M1F2.type().value(), Content.class, () -> $Taut_ed8ad9be2e8dc2fa.$A0))), new taut.validation.descriptors.FieldBinding<Wrapper, java.util.Map<Long, Content>>($M1F3, $self -> $self.by_int, taut.validation.descriptors.ValueAdapter.map($M1F3.type(), taut.validation.descriptors.ValueAdapter.scalar($M1F3.type().key(), Long.class), $key -> Cbor.encode(Cbor.int_($key)), taut.validation.descriptors.ValueAdapter.message($M1F3.type().value(), Content.class, () -> $Taut_ed8ad9be2e8dc2fa.$A0))), new taut.validation.descriptors.FieldBinding<Wrapper, java.util.Map<Boolean, Content>>($M1F4, $self -> $self.by_bool, taut.validation.descriptors.ValueAdapter.map($M1F4.type(), taut.validation.descriptors.ValueAdapter.scalar($M1F4.type().key(), Boolean.class), $key -> Cbor.encode(Cbor.bool($key)), taut.validation.descriptors.ValueAdapter.message($M1F4.type().value(), Content.class, () -> $Taut_ed8ad9be2e8dc2fa.$A0)))));
    static final taut.validation.descriptors.MessageAdapter<Virtual> $A2 = new taut.validation.descriptors.MessageAdapter<Virtual>(Virtual.class, $M2, java.util.Arrays.<taut.validation.descriptors.FieldBinding<Virtual,?>>asList(new taut.validation.descriptors.FieldBinding<Virtual, Kind>($M2F0, null, taut.validation.descriptors.ValueAdapter.enumeration($M2F0.type(), Kind.class, $e -> { switch($e) { case TEXT: return "text"; case NUMBER: return "number"; case EMPTY: return "empty"; case CHILD: return "child"; case FLAG: return "flag"; case ITEMS: return "items"; default: throw new taut.validation.ConfigurationException("invalid enum"); } })), new taut.validation.descriptors.FieldBinding<Virtual, String>($M2F1, $self -> $self.text, taut.validation.descriptors.ValueAdapter.scalar($M2F1.type(), String.class)), new taut.validation.descriptors.FieldBinding<Virtual, Content>($M2F2, $self -> $self.child, taut.validation.descriptors.ValueAdapter.message($M2F2.type(), Content.class, () -> $Taut_ed8ad9be2e8dc2fa.$A0))));
    static final taut.validation.descriptors.MessageAdapter<Multi> $A3 = new taut.validation.descriptors.MessageAdapter<Multi>(Multi.class, $M3, java.util.Arrays.<taut.validation.descriptors.FieldBinding<Multi,?>>asList(new taut.validation.descriptors.FieldBinding<Multi, Kind>($M3F0, $self -> $self.left, taut.validation.descriptors.ValueAdapter.enumeration($M3F0.type(), Kind.class, $e -> { switch($e) { case TEXT: return "text"; case NUMBER: return "number"; case EMPTY: return "empty"; case CHILD: return "child"; case FLAG: return "flag"; case ITEMS: return "items"; default: throw new taut.validation.ConfigurationException("invalid enum"); } })), new taut.validation.descriptors.FieldBinding<Multi, Kind>($M3F1, $self -> $self.right, taut.validation.descriptors.ValueAdapter.enumeration($M3F1.type(), Kind.class, $e -> { switch($e) { case TEXT: return "text"; case NUMBER: return "number"; case EMPTY: return "empty"; case CHILD: return "child"; case FLAG: return "flag"; case ITEMS: return "items"; default: throw new taut.validation.ConfigurationException("invalid enum"); } })), new taut.validation.descriptors.FieldBinding<Multi, String>($M3F2, $self -> $self.a, taut.validation.descriptors.ValueAdapter.scalar($M3F2.type(), String.class)), new taut.validation.descriptors.FieldBinding<Multi, Long>($M3F3, $self -> $self.b, taut.validation.descriptors.ValueAdapter.scalar($M3F3.type(), Long.class))));
    static final taut.validation.descriptors.MessageAdapter<Plain> $A4 = new taut.validation.descriptors.MessageAdapter<Plain>(Plain.class, $M4, java.util.Arrays.<taut.validation.descriptors.FieldBinding<Plain,?>>asList(new taut.validation.descriptors.FieldBinding<Plain, Long>($M4F0, $self -> $self.value, taut.validation.descriptors.ValueAdapter.scalar($M4F0.type(), Long.class)), new taut.validation.descriptors.FieldBinding<Plain, byte[]>($M4F1, $self -> $self.blob, taut.validation.descriptors.ValueAdapter.scalar($M4F1.type(), byte[].class)), new taut.validation.descriptors.FieldBinding<Plain, Double>($M4F2, $self -> $self.ratio, taut.validation.descriptors.ValueAdapter.scalar($M4F2.type(), Double.class))));
    static final taut.validation.descriptors.SchemaDescriptor $schema = new taut.validation.descriptors.SchemaDescriptor(1, 3, "schema_fbbfcaa31eceac80", $map(java.util.Arrays.<String>asList("Content", "Wrapper", "Virtual", "Multi", "Plain"), java.util.Arrays.<taut.validation.descriptors.MessageDescriptor>asList($M0, $M1, $M2, $M3, $M4)), $map(java.util.Arrays.<String>asList("Kind"), java.util.Arrays.<taut.validation.descriptors.EnumDescriptor>asList($E0)), taut.validation.descriptors.Snapshots.entries(), taut.validation.descriptors.Snapshots.entries("max_depth", 32L, "max_encoded_len", null));
    static final taut.validation.descriptors.SchemaBinding $binding = new taut.validation.descriptors.SchemaBinding($schema, $map(java.util.Arrays.<String>asList("Content", "Wrapper", "Virtual", "Multi", "Plain"), java.util.Arrays.<taut.validation.descriptors.MessageAdapter<?>>asList($A0, $A1, $A2, $A3, $A4)));
}
