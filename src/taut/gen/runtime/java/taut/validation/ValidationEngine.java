package taut.validation;
import java.util.*;
import taut.validation.descriptors.*;
/** One predicate/traversal implementation shared by report and short-circuit modes. */
public final class ValidationEngine {
    private ValidationEngine() {}
    public static <T> ValidationReport validate(T value,MessageAdapter<T> adapter,boolean recursive) {
        State state=new State(recursive,false);
        adapter.checkPair(value,adapter.descriptor());
        state.message(value,adapter,Collections.<PathSegment>emptyList());
        return new ValidationReport(state.issues,state.deferred,recursive?"recursive":"local");
    }
    public static <T> boolean isValid(T value,MessageAdapter<T> adapter,boolean recursive) {
        State state=new State(recursive,true);
        adapter.checkPair(value,adapter.descriptor());
        return state.message(value,adapter,Collections.<PathSegment>emptyList());
    }
    private static final class State implements Traversal {
        final boolean recursive, fast;
        final List<ValidationIssue> issues;
        final List<DeferredCheck> deferred;
        final Set<Object> ancestors=Collections.newSetFromMap(new IdentityHashMap<Object,Boolean>());
        State(boolean recursive,boolean fast) { this.recursive=recursive;this.fast=fast;issues=fast?null:new ArrayList<ValidationIssue>();deferred=fast?null:new ArrayList<DeferredCheck>(); }
        public boolean issue(String code,String rule,List<PathSegment> path,String message) { if(fast)return false;issues.add(new ValidationIssue(code,rule,path,message));return true; }
        boolean defer(List<PathSegment> path) { if(fast)return false;deferred.add(new DeferredCheck("taut.oneof.v1",path,"oneof.virtual_deferred","virtual selection is deferred"));return true; }
        public boolean enter(Object value,List<PathSegment> path) { if(ancestors.contains(value)) {issue("validation.ownership_cycle","validation.shape.v1",path,"active ancestor encountered");return false;} ancestors.add(value);return true; }
        public boolean continueAfterCycle() { return !fast; }
        public void leave(Object value) { ancestors.remove(value); }
        public <T> boolean message(T value,MessageAdapter<T> adapter,List<PathSegment> path) {
            adapter.checkPair(value,adapter.descriptor());
            if(!enter(value,path))return !fast;
            try {
                for(FieldBinding<T,?> field:adapter.fields()) {
                    FieldDescriptor f=field.descriptor();
                    OneOfDescriptor group=null;
                    for(OneOfDescriptor g:adapter.descriptor().oneofs()) if(g.controllingField().equals(f.name())) {group=g;break;}
                    if(group!=null && !group(value,adapter,group,path))return false;
                    if(recursive && !f.virtual() && group==null && !field.walk(value,this,ValueAdapter.append(path,PathSegment.forField(f.name()))))return false;
                }
                return true;
            } finally {leave(value);}
        }
        <T> boolean group(T value,MessageAdapter<T> adapter,OneOfDescriptor group,List<PathSegment> path) {
            List<PathSegment> control=ValueAdapter.append(path,PathSegment.forField(group.controllingField()));
            if(group.virtual())return defer(control);
            String member=adapter.field(group.controllingField()).enumName(value);
            if(member==null || !group.members().containsKey(member))return issue("oneof.invalid_discriminator","taut.oneof.v1",control,"expected controlling enum member");
            String selected=group.members().get(member);
            Set<String> payloads=new HashSet<String>(group.members().values());payloads.remove(null);
            for(FieldBinding<T,?> f:adapter.fields()) if(payloads.contains(f.descriptor().name())) {
                String name=f.descriptor().name();boolean present=f.present(value);
                if(name.equals(selected) && !present) {if(!issue("oneof.payload_missing","taut.oneof.v1",ValueAdapter.append(path,PathSegment.forField(name)),"selected payload is absent"))return false;}
                else if(!name.equals(selected) && present) {if(!issue("oneof.payload_unexpected","taut.oneof.v1",ValueAdapter.append(path,PathSegment.forField(name)),"nonselected payload is present"))return false;}
            }
            return true;
        }
    }
}
