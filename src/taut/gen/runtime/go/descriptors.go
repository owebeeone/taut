// Canonical Go foundation: immutable facts and typed, instance-free adapters.
package taut

import (
	"fmt"
	"sync"
	"sync/atomic"
)

// Sealed readers retain pointer identity without exposing assignable shared structs.
type TypeDescriptor interface {
	Kind() string
	Reference() string
	Element() TypeDescriptor
	Key() TypeDescriptor
	Value() TypeDescriptor
	Message() MessageDescriptor
	Enum() EnumDescriptor
	rawTypeDescriptor() *typeDescriptor
}

func (d *typeDescriptor) rawTypeDescriptor() *typeDescriptor { return d }

type FieldDescriptor interface {
	Name() string
	Access() string
	Number() int64
	Type() TypeDescriptor
	Presence() string
	Transient() bool
	Virtual() bool
	Options() map[string]any
	rawFieldDescriptor() *fieldDescriptor
}

func (d *fieldDescriptor) rawFieldDescriptor() *fieldDescriptor { return d }

type EnumDescriptor interface {
	Name() string
	QualifiedName() string
	Fingerprint() string
	Members() map[string]int64
	Options() map[string]any
	MemberOptions() map[string]any
	rawEnumDescriptor() *enumDescriptor
}

func (d *enumDescriptor) rawEnumDescriptor() *enumDescriptor { return d }

type OneOfDescriptor interface {
	ControllingField() string
	Enum() EnumDescriptor
	Virtual() bool
	Exhaustive() bool
	Members() map[string]string
	rawOneOfDescriptor() *oneOfDescriptor
}

func (d *oneOfDescriptor) rawOneOfDescriptor() *oneOfDescriptor { return d }

type ConstraintDescriptor interface {
	Rule() string
	Parameters() map[string]any
	rawConstraintDescriptor() *constraintDescriptor
}

func (d *constraintDescriptor) rawConstraintDescriptor() *constraintDescriptor { return d }

type MessageDescriptor interface {
	Name() string
	QualifiedName() string
	DescriptorContractVersion() int
	Fingerprint() string
	Fields() []FieldDescriptor
	Oneofs() []OneOfDescriptor
	Constraints() []ConstraintDescriptor
	ReservedNumbers() []int64
	ReservedNames() []string
	NextID() (int64, bool)
	Options() map[string]any
	EffectiveOptions() map[string]any
	rawMessageDescriptor() *messageDescriptor
}

func (d *messageDescriptor) rawMessageDescriptor() *messageDescriptor { return d }

type SchemaDescriptor interface {
	DescriptorContractVersion() int
	IRVersion() int
	Identity() string
	Messages() map[string]MessageDescriptor
	Enums() map[string]EnumDescriptor
	Options() map[string]any
	EffectiveOptions() map[string]any
	rawSchemaDescriptor() *schemaDescriptor
}

func (d *schemaDescriptor) rawSchemaDescriptor() *schemaDescriptor { return d }

type MessageBinding interface {
	Descriptor() MessageDescriptor
	Present(any, string) bool
	Read(any, string) any
	rawMessageBinding() *messageBinding
}

func (d *messageBinding) rawMessageBinding() *messageBinding { return d }

const FoundationOwner = "taut.go.foundation"
const FoundationBuild = "go-oneof-reference.1"
const DescriptorContract = 1
const CodecContract = 1
const OneOfRule = "taut.oneof.v1"

// ContractGuard is deliberately a defined token. Old checkers that ignore new
// requirements cannot satisfy the generated assignment by returning no token.
type ContractGuard struct{ owner string }

func FoundationCapabilities() []string { return []string{"codec.v1", "descriptors.v1", "oneof.v1"} }
func ConfirmFoundation(guard ContractGuard, owner string, descriptor, codec int, capabilities []string) {
	if guard.owner != "taut.go.foundation" || owner != "taut.go.foundation" || descriptor != 1 || codec != 1 {
		panic("incompatible Go selected runtime exports; regenerate/rebind foundation")
	}
	seen := map[string]bool{}
	for _, c := range capabilities {
		seen[c] = true
	}
	for _, c := range []string{"codec.v1", "descriptors.v1", "oneof.v1"} {
		if !seen[c] {
			panic("missing Go selected runtime capability: " + c)
		}
	}
}

func RequireFoundation(artifact, owner string, descriptor, codec int, capabilities ...string) ContractGuard {
	if owner != FoundationOwner || descriptor != DescriptorContract || codec != CodecContract {
		panic(fmt.Sprintf("%s: require Go owner=%s descriptor=1 codec=1; regenerate/rebind runtime", artifact, FoundationOwner))
	}
	for _, c := range capabilities {
		if c != "descriptors.v1" && c != "codec.v1" && c != "oneof.v1" {
			panic("unsupported Go foundation capability: " + c)
		}
	}
	return ContractGuard{FoundationOwner}
}

func snapshot(v any) any {
	switch x := v.(type) {
	case nil, string, bool, int, int64, float64:
		return x
	case []byte:
		return append([]byte(nil), x...)
	case []any:
		r := make([]any, len(x))
		for i, v := range x {
			r[i] = snapshot(v)
		}
		return r
	case map[string]any:
		r := make(map[string]any, len(x))
		for k, v := range x {
			r[k] = snapshot(v)
		}
		return r
	default:
		panic(fmt.Sprintf("unsupported immutable Go fact %T", v))
	}
}
func facts(x map[string]any) map[string]any {
	if x == nil {
		return map[string]any{}
	}
	return snapshot(x).(map[string]any)
}
func effectiveFacts(input map[string]any) map[string]any {
	if input == nil {
		input = map[string]any{"max_depth": int64(32), "max_encoded_len": nil}
	}
	if len(input) != 2 {
		panic("incomplete/unsupported Go effective codec facts")
	}
	result := facts(input)
	for _, name := range []string{"max_depth", "max_encoded_len"} {
		value, ok := result[name]
		if !ok {
			panic("missing Go effective codec option: " + name)
		}
		if value == nil && name == "max_encoded_len" {
			continue
		}
		var n int64
		switch v := value.(type) {
		case int64:
			n = v
		case int:
			n = int64(v)
		default:
			panic("invalid Go codec option type: " + name)
		}
		max := int64(128)
		if name == "max_encoded_len" {
			max = 1<<31 - 1
		}
		if n < 1 || n > max {
			panic("invalid Go codec option range: " + name)
		}
		result[name] = n
	}
	return result
}

type typeDescriptor struct {
	kind, reference     string
	element, key, value TypeDescriptor
	message             func() MessageDescriptor
	enum                func() EnumDescriptor
	linkOnce            sync.Once
	messageValue        MessageDescriptor
	enumValue           EnumDescriptor
}

func PrimitiveType(kind string) TypeDescriptor {
	switch kind {
	case "int", "str", "bool", "bytes", "float":
	default:
		panic("invalid primitive kind: " + kind)
	}
	return &typeDescriptor{kind: kind}
}
func MessageType(name string, link func() MessageDescriptor) TypeDescriptor {
	if name == "" || link == nil {
		panic("missing message link")
	}
	return &typeDescriptor{kind: "message", reference: name, message: link}
}
func EnumType(name string, link func() EnumDescriptor) TypeDescriptor {
	if name == "" || link == nil {
		panic("missing enum link")
	}
	return &typeDescriptor{kind: "enum", reference: name, enum: link}
}
func ListType(element TypeDescriptor) TypeDescriptor {
	if element == nil {
		panic("missing element")
	}
	return &typeDescriptor{kind: "list", element: element.rawTypeDescriptor()}
}
func MapType(key, value TypeDescriptor) TypeDescriptor {
	if key == nil || value == nil || (key.rawTypeDescriptor().kind != "int" && key.rawTypeDescriptor().kind != "str" && key.rawTypeDescriptor().kind != "bool") {
		panic("invalid map types")
	}
	return &typeDescriptor{kind: "map", key: key.rawTypeDescriptor(), value: value.rawTypeDescriptor()}
}
func (t *typeDescriptor) Kind() string            { return t.rawTypeDescriptor().kind }
func (t *typeDescriptor) Reference() string       { return t.rawTypeDescriptor().reference }
func (t *typeDescriptor) Element() TypeDescriptor { return t.rawTypeDescriptor().element }
func (t *typeDescriptor) Key() TypeDescriptor     { return t.rawTypeDescriptor().key }
func (t *typeDescriptor) Value() TypeDescriptor   { return t.rawTypeDescriptor().value }
func (t *typeDescriptor) Message() MessageDescriptor {
	if t.rawTypeDescriptor().kind != "message" {
		panic("not a message link")
	}
	t.linkOnce.Do(func() { t.messageValue = t.message() })
	d := t.messageValue
	if d == nil || d.rawMessageDescriptor().name != t.rawTypeDescriptor().reference || d.rawMessageDescriptor().contract != 1 {
		panic("missing/incompatible message descriptor: " + t.rawTypeDescriptor().reference)
	}
	return d.rawMessageDescriptor()
}
func (t *typeDescriptor) Enum() EnumDescriptor {
	if t.rawTypeDescriptor().kind != "enum" {
		panic("not an enum link")
	}
	t.linkOnce.Do(func() { t.enumValue = t.enum() })
	d := t.enumValue
	if d == nil || d.rawEnumDescriptor().name != t.rawTypeDescriptor().reference {
		panic("missing/incompatible enum descriptor: " + t.rawTypeDescriptor().reference)
	}
	return d.rawEnumDescriptor()
}

type fieldDescriptor struct {
	name, access, presence string
	number                 int64
	typ                    TypeDescriptor
	transient, virtual     bool
	options                map[string]any
}

func NewFieldDescriptor(name, access string, number int64, typ TypeDescriptor, presence string, transient, virtual bool, options map[string]any) FieldDescriptor {
	if name == "" || number < 1 || typ == nil || (presence != "required" && presence != "nullable" && presence != "missing_ok") || (virtual && access != "") || (!virtual && access == "") {
		panic("invalid Go field descriptor: " + name)
	}
	return &fieldDescriptor{name, access, presence, number, typ.rawTypeDescriptor(), transient, virtual, facts(options)}
}
func (f *fieldDescriptor) Name() string            { return f.rawFieldDescriptor().name }
func (f *fieldDescriptor) Access() string          { return f.rawFieldDescriptor().access }
func (f *fieldDescriptor) Number() int64           { return f.rawFieldDescriptor().number }
func (f *fieldDescriptor) Type() TypeDescriptor    { return f.rawFieldDescriptor().typ }
func (f *fieldDescriptor) Presence() string        { return f.rawFieldDescriptor().presence }
func (f *fieldDescriptor) Transient() bool         { return f.rawFieldDescriptor().transient }
func (f *fieldDescriptor) Virtual() bool           { return f.rawFieldDescriptor().virtual }
func (f *fieldDescriptor) Options() map[string]any { return facts(f.rawFieldDescriptor().options) }

type enumDescriptor struct {
	name, qualified, fingerprint string
	members                      map[string]int64
	options, memberOptions       map[string]any
}

func NewEnumDescriptor(name, qualified string, members map[string]int64, options, memberOptions map[string]any, fingerprint string) EnumDescriptor {
	if name == "" || len(members) == 0 {
		panic("invalid/empty Go enum inventory")
	}
	r := &enumDescriptor{name: name, qualified: qualified, members: make(map[string]int64), options: facts(options), memberOptions: facts(memberOptions), fingerprint: fingerprint}
	seen := map[int64]bool{}
	for k, v := range members {
		if k == "" || seen[v] {
			panic("invalid enum inventory: " + name)
		}
		seen[v] = true
		r.members[k] = v
	}
	return r
}
func (e *enumDescriptor) Name() string          { return e.name }
func (e *enumDescriptor) QualifiedName() string { return e.qualified }
func (e *enumDescriptor) Fingerprint() string   { return e.fingerprint }
func (e *enumDescriptor) Members() map[string]int64 {
	r := map[string]int64{}
	for k, v := range e.members {
		r[k] = v
	}
	return r
}
func (e *enumDescriptor) Options() map[string]any       { return facts(e.options) }
func (e *enumDescriptor) MemberOptions() map[string]any { return facts(e.memberOptions) }

type oneOfDescriptor struct {
	controlling         string
	enum                EnumDescriptor
	virtual, exhaustive bool
	members             map[string]string
}

func NewOneOfDescriptor(controlling string, enum EnumDescriptor, virtual, exhaustive bool, members map[string]string) OneOfDescriptor {
	if enum == nil || len(enum.rawEnumDescriptor().members) == 0 || len(enum.rawEnumDescriptor().members) != len(members) {
		panic("incomplete oneof enum inventory")
	}
	copy := map[string]string{}
	for k, v := range members {
		if _, ok := enum.rawEnumDescriptor().members[k]; !ok || (exhaustive && v == "") {
			panic("invalid oneof coverage")
		}
		copy[k] = v
	}
	return &oneOfDescriptor{controlling, enum.rawEnumDescriptor(), virtual, exhaustive, copy}
}
func (o *oneOfDescriptor) ControllingField() string { return o.controlling }
func (o *oneOfDescriptor) Enum() EnumDescriptor     { return o.enum }
func (o *oneOfDescriptor) Virtual() bool            { return o.virtual }
func (o *oneOfDescriptor) Exhaustive() bool         { return o.exhaustive }

// The empty payload name is the normalized payload-free choice.
func (o *oneOfDescriptor) Members() map[string]string {
	r := map[string]string{}
	for k, v := range o.members {
		r[k] = v
	}
	return r
}

type constraintDescriptor struct {
	rule       string
	parameters map[string]any
}

func NewConstraintDescriptor(rule string, parameters map[string]any) ConstraintDescriptor {
	p := facts(parameters)
	ctrl, ok := p["controlling_field"].(string)
	if rule != OneOfRule || len(p) != 1 || !ok || ctrl == "" {
		panic("unsupported/malformed constraint grammar: " + rule)
	}
	return &constraintDescriptor{rule, p}
}
func (c *constraintDescriptor) Rule() string { return c.rawConstraintDescriptor().rule }
func (c *constraintDescriptor) Parameters() map[string]any {
	return facts(c.rawConstraintDescriptor().parameters)
}

type messageDescriptor struct {
	name, qualified, fingerprint string
	contract                     int
	fields                       []FieldDescriptor
	groups                       []OneOfDescriptor
	constraints                  []ConstraintDescriptor
	reservedNumbers              []int64
	reservedNames                []string
	nextID                       *int64
	options, effective           map[string]any
	byName                       map[string]int
	groupAt                      map[int]OneOfDescriptor
	published                    uint32
}

func NewMessageDescriptor(name, qualified string, fields []FieldDescriptor, groups []OneOfDescriptor, constraints []ConstraintDescriptor, reservedNumbers []int64, reservedNames []string, nextID *int64, options, effective map[string]any, fingerprint string) MessageDescriptor {
	d := &messageDescriptor{name: name, qualified: qualified, contract: 1, fingerprint: fingerprint, fields: append([]FieldDescriptor(nil), fields...), groups: append([]OneOfDescriptor(nil), groups...), constraints: append([]ConstraintDescriptor(nil), constraints...), reservedNumbers: append([]int64(nil), reservedNumbers...), reservedNames: append([]string(nil), reservedNames...), options: facts(options), effective: effectiveFacts(effective), byName: map[string]int{}, groupAt: map[int]OneOfDescriptor{}}
	if nextID != nil {
		n := *nextID
		d.nextID = &n
	}
	last := int64(0)
	for i, f := range d.fields {
		if f == nil || f.rawFieldDescriptor().number <= last {
			panic("Go descriptor fields must have distinct ascending numbers")
		}
		if _, ok := d.byName[f.rawFieldDescriptor().name]; ok {
			panic("duplicate descriptor field")
		}
		last = f.rawFieldDescriptor().number
		d.byName[f.rawFieldDescriptor().name] = i
		d.fields[i] = f.rawFieldDescriptor()
	}
	if len(groups) != len(constraints) {
		panic("incomplete oneof constraint inventory")
	}
	nominated := map[string]string{}
	for _, g := range d.groups {
		if g == nil {
			panic("nil oneof")
		}
		i, ok := d.byName[g.rawOneOfDescriptor().controlling]
		if !ok {
			panic("unknown discriminator")
		}
		f := d.fields[i]
		if f.rawFieldDescriptor().typ.Kind() != "enum" || f.rawFieldDescriptor().typ.Reference() != g.rawOneOfDescriptor().enum.rawEnumDescriptor().name || f.rawFieldDescriptor().virtual != g.rawOneOfDescriptor().virtual || f.rawFieldDescriptor().presence != "required" || f.rawFieldDescriptor().transient {
			panic("invalid controlling field")
		}
		if d.groupAt[i] != nil {
			panic("duplicate oneof")
		}
		d.groupAt[i] = g
		for _, payload := range g.rawOneOfDescriptor().members {
			if payload == "" {
				continue
			}
			pi, ok := d.byName[payload]
			if !ok || d.fields[pi].Presence() == "required" || d.fields[pi].Virtual() {
				panic("invalid oneof payload")
			}
			if ctrl, exists := nominated[payload]; exists && ctrl != g.rawOneOfDescriptor().controlling {
				panic("multiple payload discriminators")
			}
			nominated[payload] = g.rawOneOfDescriptor().controlling
		}
	}
	for i, g := range d.groups {
		d.groups[i] = g.rawOneOfDescriptor()
	}
	seen := map[string]bool{}
	for _, c := range constraints {
		if c == nil || c.rawConstraintDescriptor().rule != OneOfRule {
			panic("invalid constraint")
		}
		ctrl := c.rawConstraintDescriptor().parameters["controlling_field"].(string)
		i, ok := d.byName[ctrl]
		if !ok || d.groupAt[i] == nil || seen[ctrl] {
			panic("constraint/oneof mismatch")
		}
		seen[ctrl] = true
	}
	for i, c := range d.constraints {
		d.constraints[i] = c.rawConstraintDescriptor()
	}
	return d
}
func (d *messageDescriptor) Name() string                   { return d.name }
func (d *messageDescriptor) QualifiedName() string          { return d.qualified }
func (d *messageDescriptor) DescriptorContractVersion() int { return d.contract }
func (d *messageDescriptor) Fingerprint() string            { return d.fingerprint }
func (d *messageDescriptor) Fields() []FieldDescriptor {
	return append([]FieldDescriptor(nil), d.fields...)
}
func (d *messageDescriptor) Oneofs() []OneOfDescriptor {
	return append([]OneOfDescriptor(nil), d.groups...)
}
func (d *messageDescriptor) Constraints() []ConstraintDescriptor {
	return append([]ConstraintDescriptor(nil), d.constraints...)
}
func (d *messageDescriptor) ReservedNumbers() []int64 {
	return append([]int64(nil), d.reservedNumbers...)
}
func (d *messageDescriptor) ReservedNames() []string {
	return append([]string(nil), d.reservedNames...)
}
func (d *messageDescriptor) NextID() (int64, bool) {
	if d.nextID == nil {
		return 0, false
	}
	return *d.nextID, true
}
func (d *messageDescriptor) Options() map[string]any          { return facts(d.options) }
func (d *messageDescriptor) EffectiveOptions() map[string]any { return facts(d.effective) }

type schemaDescriptor struct {
	version            int
	identity           string
	messages           map[string]MessageDescriptor
	enums              map[string]EnumDescriptor
	options, effective map[string]any
}

func NewSchemaDescriptor(version int, identity string, messages map[string]MessageDescriptor, enums map[string]EnumDescriptor, options, effective map[string]any) SchemaDescriptor {
	if version < 1 || version > 3 {
		panic("unsupported native IR version")
	}
	d := &schemaDescriptor{version, identity, map[string]MessageDescriptor{}, map[string]EnumDescriptor{}, facts(options), effectiveFacts(effective)}
	for k, v := range messages {
		if v == nil || v.rawMessageDescriptor().name != k || v.rawMessageDescriptor().contract != 1 {
			panic("invalid message registry")
		}
		d.messages[k] = v.rawMessageDescriptor()
	}
	for k, v := range enums {
		if v == nil || v.rawEnumDescriptor().name != k {
			panic("invalid enum registry")
		}
		d.enums[k] = v.rawEnumDescriptor()
	}
	var check func(TypeDescriptor)
	check = func(t TypeDescriptor) {
		switch t.rawTypeDescriptor().kind {
		case "message":
			if t.Message() != d.messages[t.rawTypeDescriptor().reference] {
				panic("wrong message category/owner link")
			}
		case "enum":
			if t.Enum() != d.enums[t.rawTypeDescriptor().reference] {
				panic("wrong enum category/owner link")
			}
		case "list":
			check(t.rawTypeDescriptor().element)
		case "map":
			check(t.rawTypeDescriptor().key)
			check(t.rawTypeDescriptor().value)
		}
	}
	for _, m := range d.messages {
		for _, f := range m.rawMessageDescriptor().fields {
			check(f.rawFieldDescriptor().typ)
		}
		for _, group := range m.rawMessageDescriptor().groups {
			if group.Enum() != d.enums[group.Enum().Name()] {
				panic("wrong oneof enum category/owner link")
			}
		}
	}
	for _, m := range d.messages {
		atomic.StoreUint32(&m.rawMessageDescriptor().published, 1)
	}
	return d
}
func descriptorPublished(d MessageDescriptor) bool {
	return atomic.LoadUint32(&d.rawMessageDescriptor().published) == 1
}
func (s *schemaDescriptor) DescriptorContractVersion() int { return 1 }
func (s *schemaDescriptor) IRVersion() int                 { return s.version }
func (s *schemaDescriptor) Identity() string               { return s.identity }
func (s *schemaDescriptor) Messages() map[string]MessageDescriptor {
	r := map[string]MessageDescriptor{}
	for k, v := range s.messages {
		r[k] = v
	}
	return r
}
func (s *schemaDescriptor) Enums() map[string]EnumDescriptor {
	r := map[string]EnumDescriptor{}
	for k, v := range s.enums {
		r[k] = v
	}
	return r
}
func (s *schemaDescriptor) Options() map[string]any          { return facts(s.options) }
func (s *schemaDescriptor) EffectiveOptions() map[string]any { return facts(s.effective) }

// Traversal is the callback boundary, not a common message interface. Static
// bindings capture typed functions only, never a live message.
type Traversal interface {
	Record(any, MessageBinding, []PathSegment) bool
	Issue(string, string, []PathSegment, string) bool
	Enter(any, []PathSegment) (bool, bool)
	Leave(any)
}
type messageBinding struct {
	descriptor MessageDescriptor
	accepts    func(any) bool
	present    func(any, int) bool
	enum       func(any, int) (int64, bool)
	read       func(any, int) any
	walk       func(any, int, Traversal, []PathSegment) bool
}

func NewMessageBinding[T any](descriptor MessageDescriptor, present func(*T, int) bool, enum func(*T, int) (int64, bool), read func(*T, int) any, walk func(*T, int, Traversal, []PathSegment) bool) MessageBinding {
	if descriptor == nil || present == nil || enum == nil || read == nil || walk == nil {
		panic("incomplete Go typed adapter")
	}
	descriptor = descriptor.rawMessageDescriptor()
	return &messageBinding{descriptor, func(v any) bool { p, ok := v.(*T); return ok && p != nil }, func(v any, i int) bool { return present(v.(*T), i) }, func(v any, i int) (int64, bool) { return enum(v.(*T), i) }, func(v any, i int) any { return read(v.(*T), i) }, func(v any, i int, t Traversal, p []PathSegment) bool { return walk(v.(*T), i, t, p) }}
}
func (b *messageBinding) Descriptor() MessageDescriptor { return b.descriptor }
func (b *messageBinding) field(value any, name string) int {
	if !b.accepts(value) {
		panic("Go typed binding/value mismatch; use actual generated type")
	}
	i, ok := b.descriptor.rawMessageDescriptor().byName[name]
	if !ok {
		panic("unknown Go binding field: " + name)
	}
	return i
}
func (b *messageBinding) Present(value any, name string) bool {
	return b.present(value, b.field(value, name))
}
func (b *messageBinding) Read(value any, name string) any {
	i := b.field(value, name)
	if b.descriptor.rawMessageDescriptor().fields[i].Virtual() {
		panic("virtual Go field has no value accessor: " + name)
	}
	return b.read(value, i)
}
func RequireMessageBinding(binding MessageBinding, descriptor MessageDescriptor, fingerprint string) MessageBinding {
	if binding == nil || descriptor == nil || binding.rawMessageBinding().descriptor != descriptor.rawMessageDescriptor() || descriptor.rawMessageDescriptor().fingerprint != fingerprint {
		panic("Go imported message facts/typed owner mismatch; regenerate/rebind child")
	}
	return binding.rawMessageBinding()
}
func RequireMessageDescriptor(descriptor MessageDescriptor, fingerprint string) MessageDescriptor {
	if descriptor == nil || descriptor.rawMessageDescriptor().fingerprint != fingerprint {
		panic("Go imported message facts mismatch; regenerate/rebind child")
	}
	return descriptor.rawMessageDescriptor()
}
func RequireEnumDescriptor(descriptor EnumDescriptor, fingerprint string) EnumDescriptor {
	if descriptor == nil || descriptor.rawEnumDescriptor().fingerprint != fingerprint {
		panic("Go imported enum facts mismatch; regenerate/rebind child")
	}
	return descriptor.rawEnumDescriptor()
}
