// GENERATED native Go types + codec — do not edit.
// Pairs with the vendored cbor.go runtime (same package).
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
