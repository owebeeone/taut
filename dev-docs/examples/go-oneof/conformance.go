// Runnable native consumer. The example runner supplies explicit import paths.
package main

import (
	"fmt"
	"strings"
	a "@API@"
	r "@RUNTIME@"
)

func ptr[T any](v T) *T { return &v }
func path(parts []r.PathSegment) string {
	out := []string{}
	for _,p := range parts { switch p.Kind() {
	case "field": n,_:=p.FieldName(); out=append(out,"f="+n)
	case "index": n,_:=p.Index(); out=append(out,fmt.Sprintf("i=%d",n))
	case "key": t,_:=p.KeyType(); b,_:=p.KeyCborBase64(); out=append(out,"k="+t+","+b)
	} }; return strings.Join(out,"/")
}
func row(name string, report r.ValidationReport, fast bool) {
	if fast != (report.IsValid() && report.IsComplete()) { panic("Boolean/report parity") }
	out:=[]string{name,report.Scope(),fmt.Sprint(report.IsValid()),fmt.Sprint(report.IsComplete())}
	for _,i:=range report.Issues(){out=append(out,"I:"+i.Code()+":"+i.Rule()+":"+path(i.Path()))}
	for _,d:=range report.DeferredChecks(){out=append(out,"D:"+d.ReasonCode()+":"+d.Rule()+":"+path(d.Path()))}
	fmt.Println(strings.Join(out,"\t"))
}
func content(kind a.ContentKind) a.Content { return a.Content{Kind:kind} }
func cr(name string,c *a.Content) { row(name,c.Validate(),c.IsValid()) }
func main(){
	c:=content(a.ContentKindText); cr("missing",&c)
	c.Text=ptr(""); cr("empty",&c); c.Number=ptr(int64(0)); cr("extra",&c)
	old:=c.Validate(); c2,err:=a.TryContentFromCbor(c.ToCbor()); if err!=nil { panic(err) }; cr("roundtrip",&c2)
	c.Kind=a.ContentKindNumber; c.Text=nil; cr("zero",&c)
	if len(old.Issues())!=1 { panic("report snapshot") }
	c.Kind=a.ContentKindFlag; c.Number=nil; c.Flag=ptr(false); cr("false",&c)
	c.Flag=nil; c.Kind=a.ContentKindItems; c.Items=ptr([]int64{}); cr("empty-list",&c)
	c.Items=nil; c.Kind=a.ContentKindEmpty; cr("payload-free",&c)
	c.Kind=a.ContentKind(-99); c.Child=ptr(content(a.ContentKindText)); cr("bad-tag-child",&c)
	c.Kind=a.ContentKindEmpty; cr("nonselected-child",&c)
	c.Kind=a.ContentKindChild; c.Child=&c; cr("cycle",&c)
	bad:=content(a.ContentKindText)
	w:=a.Wrapper{Child:bad,Children:[]a.Content{bad,bad},ByText:map[string]a.Content{"z":bad,"":bad,"aa":bad},ByInt:map[int64]a.Content{-1:bad,24:bad,0:bad},ByBool:map[bool]a.Content{true:bad,false:bad}}
	row("wrapper",w.Validate(),w.IsValid()); o:=a.ValidationOptions{}; row("local",w.ValidateWithOptions(o),w.IsValidWithOptions(o))
	v:=a.Virtual{Child:bad}; row("virtual-child",v.Validate(),v.IsValid()); v.Child.Text=ptr(""); row("virtual-repaired",v.Validate(),v.IsValid()); row("virtual-local",v.ValidateWithOptions(o),v.IsValidWithOptions(o))
	m:=a.Multi{Left:a.ContentKind(-99),Right:a.ContentKindNumber}; row("independent",m.Validate(),m.IsValid())
	p:=a.Plain{}; row("plain",p.Validate(),p.IsValid())
	var nilRoot *a.Content; if nilRoot.IsValid() || nilRoot.Validate().Issues()[0].Code()!="validation.type_mismatch" || nilRoot.Descriptor()!=a.DescribeContent() { panic("nil root API") }
}
