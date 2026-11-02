package taut;
import java.util.*;
import taut.validation.*;
import taut.validation.descriptors.*;
public final class Conformance {
    static void check(boolean ok,String message) { if(!ok) throw new AssertionError(message); }
    static Content content(Kind kind) { Content c=new Content(); c.kind=kind;return c; }
    static void report(String name,ValidationReport r,boolean fast) {
        check(fast==(r.isValid() && r.isComplete()),"fast/report " + name);
        StringBuilder s=new StringBuilder(name+"\t"+r.scope()+"\t"+r.isValid()+"\t"+r.isComplete());
        for(ValidationIssue i:r.issues()) s.append("\tI:").append(i.code()).append(":").append(i.rule()).append(":").append(path(i.path()));
        for(DeferredCheck d:r.deferredChecks())s.append("\tD:").append(d.reasonCode()).append(":").append(d.rule()).append(":").append(path(d.path()));
        System.out.println(s);
    }
    static String path(List<PathSegment> p) {
        StringBuilder s=new StringBuilder();
        for(PathSegment e:p) {
            if(s.length()!=0)s.append('/');
            if(e.kind().equals("field"))s.append("f=").append(e.fieldName());
            else if(e.kind().equals("index"))s.append("i=").append(e.index());
            else s.append("k=").append(e.keyType()).append(',').append(e.keyCborBase64());
        }
        return s.toString();
    }
    public static void main(String[] args) {
        Content c=content(Kind.TEXT);
        ValidationReport snapshot=c.validate();
        report("missing",snapshot,c.isValid());
        c.text="";report("empty",c.validate(),c.isValid());
        check(snapshot.issues().size()==1,"snapshot survives repair");
        c.number=0L;report("extra",c.validate(),c.isValid());
        Content round=Content.decode(Cbor.encode(c.toCbor()));
        check(round.text.equals("") && round.number==0L,"invalid draft codec preserved");
        report("roundtrip",round.validate(),round.isValid());
        c.kind=Kind.NUMBER;c.text=null;report("zero",c.validate(),c.isValid());
        c.kind=Kind.FLAG;c.number=null;c.flag=false;report("false",c.validate(),c.isValid());
        c.flag=null;c.kind=Kind.ITEMS;c.items=new ArrayList<Long>();report("empty-list",c.validate(),c.isValid());
        c.items=null;c.kind=Kind.EMPTY;report("payload-free",c.validate(),c.isValid());
        c.kind=null;c.child=content(Kind.TEXT);report("bad-tag-child",c.validate(),c.isValid());
        c.kind=Kind.EMPTY;report("nonselected-child",c.validate(),c.isValid());
        c.kind=Kind.CHILD;c.child=c;report("cycle",c.validate(),c.isValid());
        Wrapper w=new Wrapper(); Content bad=content(Kind.TEXT);
        w.child=bad; w.children=Arrays.asList(bad,bad); w.by_text=new LinkedHashMap<String,Content>();
        w.by_text.put("z",bad);w.by_text.put("",bad);w.by_text.put("aa",bad);
        w.by_int=new LinkedHashMap<Long,Content>();w.by_int.put(-1L,bad);w.by_int.put(24L,bad);w.by_int.put(0L,bad);
        w.by_bool=new LinkedHashMap<Boolean,Content>();w.by_bool.put(true,bad);w.by_bool.put(false,bad);
        report("wrapper",w.validate(),w.isValid());report("local",w.validate(false),w.isValid(false));
        Virtual v=new Virtual();v.child=bad;report("virtual-child",v.validate(),v.isValid());
        bad.text="";report("virtual-repaired",v.validate(),v.isValid());
        report("virtual-local",v.validate(false),v.isValid(false));
        Multi m=new Multi();m.left=null;m.right=Kind.NUMBER;report("independent",m.validate(),m.isValid());
        Plain p=new Plain();report("plain",p.validate(),p.isValid());
        // Shared immutable public diagnostics remain open to future rule families.
        List<ValidationIssue> issues=new ArrayList<ValidationIssue>();
        issues.add(new ValidationIssue("application.bad","application.rule.v9",Arrays.asList(PathSegment.forField("x")),"custom"));
        ValidationReport general=new ValidationReport(issues,Collections.<DeferredCheck>emptyList(),"local");issues.clear();
        check(!general.isValid() && general.isComplete() && general.issues().size()==1,"general snapshot");
        try {general.issues().clear();throw new AssertionError("mutable report");}catch(UnsupportedOperationException expected){}
        check(Content.descriptor()==Content.descriptor(),"shared descriptor identity");
        MessageDescriptor d=Content.descriptor();
        check(d.fields().size()==6 && d.oneofs().size()==1 && d.constraints().size()==1 && d.reservedNumbers().equals(Arrays.asList(7L)) && d.reservedNames().equals(Arrays.asList("retired")) && d.nextId()==9L,"complete descriptor inventory");
        check(d.fields().get(3).type().message()==d,"recursive stable link");
        check(Virtual.descriptor().fields().get(0).virtual() && Virtual.descriptor().fields().get(0).attribute()==null,"logical virtual metadata");
        try{d.fields().clear();throw new AssertionError("mutable descriptors");}catch(UnsupportedOperationException expected){}
        try{d.effectiveOptions().clear();throw new AssertionError("mutable options");}catch(UnsupportedOperationException expected){}
        try{Content.$adapter().checkPair(null,d);throw new AssertionError("null pair");}catch(ConfigurationException expected){}
        try{Content.$adapter().checkPair(content(Kind.EMPTY),Plain.descriptor());throw new AssertionError("wrong pair");}catch(ConfigurationException expected){}
        try{Content nothing=null;nothing.validate();throw new AssertionError("null receiver");}catch(NullPointerException expected){}
        try{new MessageDescriptor("X","X",2,Collections.<FieldDescriptor>emptyList(),Collections.<OneOfDescriptor>emptyList(),Collections.<ConstraintDescriptor>emptyList(),Collections.<Long>emptyList(),Collections.<String>emptyList(),null,Collections.<String,Object>emptyMap(),Collections.<String,Object>emptyMap(),"x");throw new AssertionError("bad descriptor contract");}catch(ConfigurationException expected){}
        RuntimeContract.require("compatible-patch","taut.java.foundation",1,1,"oneof.v1");
        try{RuntimeContract.require("old","split-owner",1,1);throw new AssertionError("split owner");}catch(ConfigurationException expected){}
        try{RuntimeContract.require("future","taut.java.foundation",1,1,"future.rule");throw new AssertionError("unsupported capability");}catch(ConfigurationException expected){}
    }
}
