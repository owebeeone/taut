// GENERATED Go codec + mandatory descriptor ABI 1; generator=go-oneof-reference.1
package taut

type Choice int64

const (
	ChoiceText   Choice = 0
	ChoiceNumber Choice = 1
)

func TryChoiceFromWire(v int64) (Choice, error) {
	switch v {
	case 0:
		return ChoiceText, nil
	case 1:
		return ChoiceNumber, nil
	default:
		return 0, UnknownEnumError("Choice", v)
	}
}

func TryChoiceFromCbor(c Cbor) (Choice, error) {
	v, err := c.TryInt()
	if err != nil {
		return 0, err
	}
	return TryChoiceFromWire(v)
}

type Content struct {
	Kind   Choice
	Text   *string
	Number *int64
}

func (x Content) ToCbor() Cbor {
	m := make([]KV, 0, 3)
	m = append(m, KV{K: 1, V: CInt(int64(x.Kind))})
	if x.Text == nil {
		m = append(m, KV{K: 2, V: CNull()})
	} else {
		m = append(m, KV{K: 2, V: CText(*x.Text)})
	}
	if x.Number == nil {
		m = append(m, KV{K: 3, V: CNull()})
	} else {
		m = append(m, KV{K: 3, V: CInt(*x.Number)})
	}
	return CMap(m)
}

func TryContentFromCbor(c Cbor) (Content, error) {
	var v Content
	if _, err := c.TryMap(); err != nil {
		return v, err
	}
	{
		fv, err := c.Require(1)
		if err != nil {
			return v, err
		}
		x, err := TryChoiceFromCbor(fv)
		if err != nil {
			return v, err
		}
		v.Kind = x
	}
	{
		fv, err := c.Require(2)
		if err != nil {
			return v, err
		}
		if !fv.IsNull() {
			x, err := fv.TryText()
			if err != nil {
				return v, err
			}
			v.Text = &x
		}
	}
	{
		fv, err := c.Require(3)
		if err != nil {
			return v, err
		}
		if !fv.IsNull() {
			x, err := fv.TryInt()
			if err != nil {
				return v, err
			}
			v.Number = &x
		}
	}
	return v, nil
}

// Content's bounds: its effective max_depth and max_encoded_len (-1: none).
const (
	ContentMaxDepth      = 32
	ContentMaxEncodedLen = -1
)

// TryContentFromBytes decodes data rooted at Content, under its bounds.
func TryContentFromBytes(data []byte) (Content, error) {
	c, err := TryDecodeWith(data, ContentMaxDepth, ContentMaxEncodedLen)
	if err != nil {
		return Content{}, err
	}
	return TryContentFromCbor(c)
}

func DescribeChoice() EnumDescriptor {
	return tautDescf30bfb32bb251b27E0
}

func DescribeContent() MessageDescriptor {
	return tautDescf30bfb32bb251b27M0
}

func TautBindingContent() MessageBinding {
	return tautBindf30bfb32bb251b27M0
}

func (*Content) Descriptor() MessageDescriptor {
	return DescribeContent()
}

func DescribeSchema() SchemaDescriptor {
	return tautSchemaf30bfb32bb251b27
}

var tautSchemaf30bfb32bb251b27 SchemaDescriptor
var tautDescf30bfb32bb251b27E0 EnumDescriptor
var tautDescf30bfb32bb251b27M0 MessageDescriptor
var tautBindf30bfb32bb251b27M0 MessageBinding

func init() {
	var guard ContractGuard = RequireFoundation("go-oneof-golden", "taut.go.foundation", 1, 1, "descriptors.v1", "codec.v1", "oneof.v1")
	ConfirmFoundation(guard, FoundationOwner, DescriptorContract, CodecContract, FoundationCapabilities())
	tautDescf30bfb32bb251b27E0 = NewEnumDescriptor("Choice", "go-oneof-golden.Choice", map[string]int64{"text": 0, "number": 1}, map[string]any{}, map[string]any{"text": map[string]any{}, "number": map[string]any{}}, "ff0c856eff0439d665374149f2966cf754fd7228567659ac6bedf00ab71a44c0")
	tautDescf30bfb32bb251b27M0 = NewMessageDescriptor("Content", "go-oneof-golden.Content", []FieldDescriptor{NewFieldDescriptor("kind", "Kind", 1, EnumType("Choice", DescribeChoice), "required", false, false, map[string]any{}), NewFieldDescriptor("text", "Text", 2, PrimitiveType("str"), "nullable", false, false, map[string]any{}), NewFieldDescriptor("number", "Number", 3, PrimitiveType("int"), "nullable", false, false, map[string]any{})}, []OneOfDescriptor{}, []ConstraintDescriptor{}, []int64{}, []string{}, nil, map[string]any{}, map[string]any{"max_depth": int64(32), "max_encoded_len": nil}, "7f98c3103d3da6ab4ee9c0b02b48d249a27fe2a729fc7e656da76b8bb7a8c4fa")
	tautBindf30bfb32bb251b27M0 = NewMessageBinding[Content](tautDescf30bfb32bb251b27M0, func(v *Content, i int) bool {
		switch i {
		case 0:
			return true
		case 1:
			return v.Text != nil
		case 2:
			return v.Number != nil
		}
		return false
	}, func(v *Content, i int) (int64, bool) {
		switch i {
		case 0:
			return int64(v.Kind), true
		}
		return 0, false
	}, func(v *Content, i int) any {
		switch i {
		case 0:
			return v.Kind
		case 1:
			if v.Text == nil {
				return nil
			}
			return *v.Text
		case 2:
			if v.Number == nil {
				return nil
			}
			return *v.Number
		}
		return nil
	}, func(v *Content, i int, visitor Traversal, path []PathSegment) bool {
		switch i {
		case 0:
			switch int64(v.Kind) {
			case 0, 1:
			default:
				if !visitor.Issue("validation.type_mismatch", "validation.shape.v1", path, "invalid generated enum") {
					return false
				}
			}
		}
		return true
	})
	tautSchemaf30bfb32bb251b27 = NewSchemaDescriptor(2, "go-oneof-golden", map[string]MessageDescriptor{"Content": tautDescf30bfb32bb251b27M0}, map[string]EnumDescriptor{"Choice": tautDescf30bfb32bb251b27E0}, map[string]any{}, map[string]any{"max_depth": int64(32), "max_encoded_len": nil})
}
