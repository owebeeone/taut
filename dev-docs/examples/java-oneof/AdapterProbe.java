package taut;
import java.util.*;
import taut.validation.descriptors.*;
/** Standalone typed ABI probe: no message base class and no validation engine. */
public final class AdapterProbe {
    static final class Row { long n; }
    public static void main(String[] args) {
        TypeDescriptor type=new TypeDescriptor("int",null,null,null,null,null,null);
        FieldDescriptor field=new FieldDescriptor("n","n",1,type,"required",false,false,Collections.<String,Object>emptyMap());
        List<FieldDescriptor> fields=new ArrayList<FieldDescriptor>();fields.add(field);
        MessageDescriptor desc=new MessageDescriptor("Row","probe.Row",1,fields,Collections.<OneOfDescriptor>emptyList(),Collections.<ConstraintDescriptor>emptyList(),Collections.<Long>emptyList(),Collections.<String>emptyList(),null,Collections.<String,Object>emptyMap(),Collections.<String,Object>emptyMap(),"probe");
        fields.clear();
        FieldBinding<Row,Long> access=new FieldBinding<Row,Long>(field,$row->$row.n,ValueAdapter.scalar(type,Long.class));
        MessageAdapter<Row> adapter=new MessageAdapter<Row>(Row.class,desc,Arrays.<FieldBinding<Row,?>>asList(access));
        SchemaDescriptor schema=new SchemaDescriptor(1,3,"probe",Collections.singletonMap("Row",desc),Collections.<String,EnumDescriptor>emptyMap(),Collections.<String,Object>emptyMap(),Collections.<String,Object>emptyMap());
        SchemaBinding binding=new SchemaBinding(schema,Collections.<String,MessageAdapter<?>>singletonMap("Row",adapter));
        Row value=new Row();adapter.checkPair(value,desc);
        if(!access.present(value) || access.readValue(value)!=0L || desc.fields().size()!=1 || binding.messages().get("Row")!=adapter)throw new AssertionError();
        System.out.println("typed-adapter Java8 PASS");
    }
}
