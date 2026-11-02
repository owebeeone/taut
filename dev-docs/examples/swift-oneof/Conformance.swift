import TautFoundation

func path(_ segments: [PathSegment]) -> String {
    segments.map { s in
        if s.kind == "field" { return "f=" + s.fieldName! }
        if s.kind == "index" { return "i=" + String(s.index!) }
        return "k=" + s.keyType! + "," + s.keyCborBase64!
    }.joined(separator: "/")
}
func report<V>(_ name: String, _ value: V, _ binding: MessageBinding<V>, _ recursive: Bool = true) {
    let r=validateRecord(value,binding,recursive:recursive)
    precondition(isRecordValid(value,binding,recursive:recursive) == (r.isValid && r.isComplete))
    var parts=[name,r.scope,String(r.isValid),String(r.isComplete)]
    parts += r.issues.map { "I:" + $0.code + ":" + $0.rule + ":" + path($0.path) }
    parts += r.deferredChecks.map { "D:" + $0.reasonCode + ":" + $0.rule + ":" + path($0.path) }
    print(parts.joined(separator:"\t"))
}
let c=Content(kind:.text)
report("missing",c,Content.tautBinding)
precondition(c.validate().issues.count == 1 && !c.isValid())
c.text=""; report("empty",c,Content.tautBinding)
precondition(c.isValid())
c.number=0; report("extra",c,Content.tautBinding)
let decoded=try! Content.decode(encode(c.toCbor()))
precondition(decoded.text == "" && decoded.number == 0)
report("roundtrip",decoded,Content.tautBinding)
c.kind = .number; c.text=nil; report("zero",c,Content.tautBinding)
c.kind = .flag; c.number=nil; c.flag=false; report("false",c,Content.tautBinding)
c.flag=nil; c.kind = .items; c.items=[]; report("empty-list",c,Content.tautBinding)
c.items=nil; c.kind = .empty; report("payload-free",c,Content.tautBinding)
// Swift's native enum cannot store an unknown tag. A typed negative adapter
// exercises the same runtime predicate and continued child traversal without
// manufacturing an invalid enum bit pattern.
let cb=Content.tautBinding
let badTag=MessageBinding<Content>(reference:Content.descriptor,cb.present,{ _,_ in 99 },cb.read,cb.walk)
c.child=Content(kind:.text); report("bad-tag-child",c,badTag)
report("nonselected-child",c,Content.tautBinding)
let cycle=Content(kind:.child); cycle.child=cycle
report("cycle",cycle,Content.tautBinding); cycle.child=nil
let bad=Content(kind:.text)
let w=Wrapper(child:bad,children:[bad,bad],by_text:["z":bad,"":bad,"aa":bad],by_int:[-1:bad,24:bad,0:bad],by_bool:[true:bad,false:bad])
report("wrapper",w,Wrapper.tautBinding); report("local",w,Wrapper.tautBinding,false)
let v=Virtual(child:bad)
report("virtual-child",v,Virtual.tautBinding)
bad.text=""; report("virtual-repaired",v,Virtual.tautBinding); report("virtual-local",v,Virtual.tautBinding,false)
let mb=Multi.tautBinding
let badLeft=MessageBinding<Multi>(Multi.descriptor,mb.present,{ value,i in i == 0 ? 99 : mb.enumValue(value,i) },mb.read,mb.walk)
report("independent",Multi(left:.empty,right:.number),badLeft)
report("plain",Plain(value:0),Plain.tautBinding)
let snapshot=c.validate(); c.child=nil
precondition(snapshot.issues.count == 2)
let synthetic=ValidationReport([ValidationIssue("app.custom","app.rule.v1",[],"owned")])
precondition(!synthetic.isValid && synthetic.isComplete)
precondition(Content.descriptor.fields.count == 6 && Content.descriptor.reservedNumbers == [7] && Content.descriptor.nextId == 9)
precondition(Virtual.descriptor.fields[0].virtual && Content.descriptor.nativeRepresentation == "class")
precondition(Wrapper.descriptor.nativeRepresentation == "struct")
precondition(Content.schemaDescriptor.messages.count == 5)
