// Minimal deterministic CBOR — the Go binding of the frozen wire substrate.
// Byte-for-byte identical to taut/src/taut/wire/cbor.py and the Rust/TS/C++/Swift
// runtimes: the same tiny subset (int, bytes, text, array, int-keyed map, bool,
// null, float) in core-deterministic encoding (definite length, shortest-form
// ints/floats, ascending map keys). Hand-rolled, stdlib only.
package taut

import (
	"fmt"
	"math"
	"sort"
	"strconv"
	"unicode/utf8"
)

type Kind int

const (
	KInt Kind = iota
	KBytes
	KText
	KArr
	KMap
	KBool
	KNull
	KFloat
)

// KV is one integer-keyed map entry.
type KV struct {
	K int64
	V Cbor
}

// Cbor is a decoded value (tagged union as a struct).
type Cbor struct {
	Kind Kind
	I    int64
	S    string
	B    []byte
	Arr  []Cbor
	Map  []KV
	F    float64
}

const (
	DecodeErrTruncated        = "Truncated"
	DecodeErrTrailingBytes    = "TrailingBytes"
	DecodeErrInvalidUtf8      = "InvalidUtf8"
	DecodeErrUnsupportedInfo  = "UnsupportedInfo"
	DecodeErrUnsupportedMajor = "UnsupportedMajor"
	DecodeErrNonIntegerMapKey = "NonIntegerMapKey"
	DecodeErrIntOverflow      = "IntOverflow"
	DecodeErrDuplicateMapKey  = "DuplicateMapKey"
	DecodeErrMissingKey       = "MissingKey"
	DecodeErrWrongType        = "WrongType"
	DecodeErrUnknownEnum      = "UnknownEnum"
)

const maxInt64Uint = uint64(1<<63 - 1)

type DecodeError struct {
	Tag      string
	Info     byte
	Major    byte
	Key      int64
	Expected string
	Enum     string
	Value    string
}

func UnknownEnumError(enum string, value int64) error {
	return &DecodeError{Tag: DecodeErrUnknownEnum, Enum: enum, Value: strconv.FormatInt(value, 10)}
}

func (e *DecodeError) Error() string {
	switch e.Tag {
	case DecodeErrUnsupportedInfo:
		return fmt.Sprintf("%s(%d)", e.Tag, e.Info)
	case DecodeErrUnsupportedMajor:
		return fmt.Sprintf("%s(%d)", e.Tag, e.Major)
	case DecodeErrDuplicateMapKey, DecodeErrMissingKey:
		return fmt.Sprintf("%s(%d)", e.Tag, e.Key)
	case DecodeErrWrongType:
		return fmt.Sprintf("%s(%s)", e.Tag, e.Expected)
	case DecodeErrUnknownEnum:
		return fmt.Sprintf("%s(%s=%s)", e.Tag, e.Enum, e.Value)
	case DecodeErrIntOverflow:
		return fmt.Sprintf("%s(%s)", e.Tag, e.Value)
	default:
		return e.Tag
	}
}

func CInt(n int64) Cbor     { return Cbor{Kind: KInt, I: n} }
func CText(s string) Cbor   { return Cbor{Kind: KText, S: s} }
func CBytes(b []byte) Cbor  { return Cbor{Kind: KBytes, B: b} }
func CArr(a []Cbor) Cbor    { return Cbor{Kind: KArr, Arr: a} }
func CMap(m []KV) Cbor      { return Cbor{Kind: KMap, Map: m} }
func CNull() Cbor           { return Cbor{Kind: KNull} }
func CFloat(n float64) Cbor { return Cbor{Kind: KFloat, F: n} }
func CBool(b bool) Cbor {
	c := Cbor{Kind: KBool}
	if b {
		c.I = 1
	}
	return c
}

// Get returns the value for an integer map key (panics if absent).
func (c Cbor) Get(key int64) Cbor {
	v, err := c.Require(key)
	if err != nil {
		panic(err)
	}
	return v
}

func (c Cbor) Require(key int64) (Cbor, error) {
	v, ok, err := c.Lookup(key)
	if err != nil {
		return Cbor{}, err
	}
	if !ok {
		return Cbor{}, &DecodeError{Tag: DecodeErrMissingKey, Key: key}
	}
	return v, nil
}

func (c Cbor) Lookup(key int64) (Cbor, bool, error) {
	m, err := c.TryMap()
	if err != nil {
		return Cbor{}, false, err
	}
	for _, kv := range m {
		if kv.K == key {
			return kv.V, true, nil
		}
	}
	return Cbor{}, false, nil
}
func (c Cbor) Int() int64       { return c.I }
func (c Cbor) Text() string     { return c.S }
func (c Cbor) Bytes() []byte    { return c.B }
func (c Cbor) Bool() bool       { return c.I != 0 }
func (c Cbor) Array() []Cbor    { return c.Arr }
func (c Cbor) IsNull() bool     { return c.Kind == KNull }
func (c Cbor) MapEntries() []KV { return c.Map } // forward-compat residual capture
func (c Cbor) Float() float64   { return c.F }

func (c Cbor) TryInt() (int64, error) {
	if c.Kind != KInt {
		return 0, &DecodeError{Tag: DecodeErrWrongType, Expected: "int"}
	}
	return c.I, nil
}

func (c Cbor) TryText() (string, error) {
	if c.Kind != KText {
		return "", &DecodeError{Tag: DecodeErrWrongType, Expected: "str"}
	}
	return c.S, nil
}

func (c Cbor) TryBytes() ([]byte, error) {
	if c.Kind != KBytes {
		return nil, &DecodeError{Tag: DecodeErrWrongType, Expected: "bytes"}
	}
	return c.B, nil
}

func (c Cbor) TryBool() (bool, error) {
	if c.Kind != KBool {
		return false, &DecodeError{Tag: DecodeErrWrongType, Expected: "bool"}
	}
	return c.I != 0, nil
}

func (c Cbor) TryArray() ([]Cbor, error) {
	if c.Kind != KArr {
		return nil, &DecodeError{Tag: DecodeErrWrongType, Expected: "array"}
	}
	return c.Arr, nil
}

func (c Cbor) TryMap() ([]KV, error) {
	if c.Kind != KMap {
		return nil, &DecodeError{Tag: DecodeErrWrongType, Expected: "map"}
	}
	return c.Map, nil
}

func (c Cbor) TryFloat() (float64, error) {
	if c.Kind != KFloat {
		return 0, &DecodeError{Tag: DecodeErrWrongType, Expected: "float"}
	}
	return c.F, nil
}

func head(out *[]byte, major byte, n uint64) {
	mt := major << 5
	switch {
	case n < 24:
		*out = append(*out, mt|byte(n))
	case n < 0x100:
		*out = append(*out, mt|24, byte(n))
	case n < 0x10000:
		*out = append(*out, mt|25, byte(n>>8), byte(n))
	case n < 0x100000000:
		*out = append(*out, mt|26, byte(n>>24), byte(n>>16), byte(n>>8), byte(n))
	default:
		*out = append(*out, mt|27, byte(n>>56), byte(n>>48), byte(n>>40), byte(n>>32), byte(n>>24), byte(n>>16), byte(n>>8), byte(n))
	}
}

func Encode(c Cbor) []byte {
	var out []byte
	enc(c, &out)
	return out
}

func enc(c Cbor, out *[]byte) {
	switch c.Kind {
	case KInt:
		if c.I >= 0 {
			head(out, 0, uint64(c.I))
		} else {
			head(out, 1, uint64(-1-c.I))
		}
	case KBytes:
		head(out, 2, uint64(len(c.B)))
		*out = append(*out, c.B...)
	case KText:
		head(out, 3, uint64(len(c.S)))
		*out = append(*out, c.S...)
	case KArr:
		head(out, 4, uint64(len(c.Arr)))
		for _, x := range c.Arr {
			enc(x, out)
		}
	case KMap:
		m := make([]KV, len(c.Map))
		copy(m, c.Map)
		sort.SliceStable(m, func(i, j int) bool { return m[i].K < m[j].K }) // ascending keys
		head(out, 5, uint64(len(m)))
		for _, kv := range m {
			head(out, 0, uint64(kv.K))
			enc(kv.V, out)
		}
	case KBool:
		if c.I != 0 {
			*out = append(*out, 0xf5)
		} else {
			*out = append(*out, 0xf4)
		}
	case KNull:
		*out = append(*out, 0xf6)
	case KFloat:
		floatBytes(c.F, out)
	}
}

func floatBytes(v float64, out *[]byte) {
	if math.IsNaN(v) {
		*out = append(*out, 0xf9, 0x7e, 0x00)
		return
	}
	if h, ok := float64ToHalfBits(v); ok && math.Float64bits(halfToFloat64(h)) == math.Float64bits(v) {
		*out = append(*out, 0xf9, byte(h>>8), byte(h))
		return
	}
	f := float32(v)
	if math.Float64bits(float64(f)) == math.Float64bits(v) {
		bits := math.Float32bits(f)
		*out = append(*out, 0xfa, byte(bits>>24), byte(bits>>16), byte(bits>>8), byte(bits))
		return
	}
	bits := math.Float64bits(v)
	*out = append(*out, 0xfb, byte(bits>>56), byte(bits>>48), byte(bits>>40), byte(bits>>32), byte(bits>>24), byte(bits>>16), byte(bits>>8), byte(bits))
}

func roundShiftEven(n uint64, shift uint) uint64 {
	if shift == 0 {
		return n
	}
	q := n >> shift
	rem := n & ((uint64(1) << shift) - 1)
	half := uint64(1) << (shift - 1)
	if rem > half || (rem == half && q&1 == 1) {
		q++
	}
	return q
}

func float64ToHalfBits(v float64) (uint16, bool) {
	bits := math.Float64bits(v)
	sign := uint16((bits >> 48) & 0x8000)
	exp := int((bits >> 52) & 0x7ff)
	frac := bits & ((uint64(1) << 52) - 1)

	if exp == 0x7ff {
		if frac != 0 {
			return 0x7e00, true
		}
		return sign | 0x7c00, true
	}
	if exp == 0 {
		return sign, true
	}

	unbiased := exp - 1023
	sig := (uint64(1) << 52) | frac
	if unbiased > 15 {
		return sign | 0x7c00, false
	}
	if unbiased >= -14 {
		halfExp := unbiased + 15
		rounded := roundShiftEven(sig, 42)
		if rounded == 0x800 {
			halfExp++
			rounded = 0x400
			if halfExp >= 31 {
				return sign | 0x7c00, false
			}
		}
		return sign | uint16(halfExp<<10) | uint16(rounded&0x3ff), true
	}
	if unbiased < -25 {
		return sign, true
	}
	rounded := roundShiftEven(sig, uint(28-unbiased))
	if rounded == 0 {
		return sign, true
	}
	if rounded >= 0x400 {
		return sign | 0x0400, true
	}
	return sign | uint16(rounded), true
}

func halfToFloat64(h uint16) float64 {
	sign := uint64(h&0x8000) << 48
	exp := (h >> 10) & 0x1f
	frac := uint64(h & 0x03ff)
	switch exp {
	case 0:
		if frac == 0 {
			return math.Float64frombits(sign)
		}
		v := math.Ldexp(float64(frac), -24)
		if sign != 0 {
			return -v
		}
		return v
	case 0x1f:
		if frac == 0 {
			return math.Float64frombits(sign | 0x7ff0000000000000)
		}
		return math.Float64frombits(sign | 0x7ff8000000000000 | (frac << 42))
	default:
		exp64 := uint64(int(exp) - 15 + 1023)
		return math.Float64frombits(sign | (exp64 << 52) | (frac << 42))
	}
}

func Decode(data []byte) Cbor {
	v, err := TryDecode(data)
	if err != nil {
		panic(err)
	}
	return v
}

func TryDecode(data []byte) (Cbor, error) {
	v, off, err := dec(data, 0)
	if err != nil {
		return Cbor{}, err
	}
	if off != len(data) {
		return Cbor{}, &DecodeError{Tag: DecodeErrTrailingBytes}
	}
	return v, nil
}

func readArg(data []byte, off int, info byte) (uint64, int, error) {
	switch {
	case info < 24:
		return uint64(info), off, nil
	case info == 24:
		if off > len(data)-1 {
			return 0, off, &DecodeError{Tag: DecodeErrTruncated}
		}
		return uint64(data[off]), off + 1, nil
	case info == 25:
		if off > len(data)-2 {
			return 0, off, &DecodeError{Tag: DecodeErrTruncated}
		}
		return uint64(data[off])<<8 | uint64(data[off+1]), off + 2, nil
	case info == 26:
		if off > len(data)-4 {
			return 0, off, &DecodeError{Tag: DecodeErrTruncated}
		}
		var v uint64
		for j := 0; j < 4; j++ {
			v = v<<8 | uint64(data[off+j])
		}
		return v, off + 4, nil
	case info == 27:
		if off > len(data)-8 {
			return 0, off, &DecodeError{Tag: DecodeErrTruncated}
		}
		var v uint64
		for j := 0; j < 8; j++ {
			v = v<<8 | uint64(data[off+j])
		}
		return v, off + 8, nil
	default:
		return 0, off, &DecodeError{Tag: DecodeErrUnsupportedInfo, Info: info}
	}
}

func negOverflowValue(n uint64) string {
	if n == ^uint64(0) {
		return "-18446744073709551616"
	}
	return "-" + strconv.FormatUint(n+1, 10)
}

func dec(data []byte, off int) (Cbor, int, error) {
	if off >= len(data) {
		return Cbor{}, off, &DecodeError{Tag: DecodeErrTruncated}
	}
	initial := data[off]
	major := initial >> 5
	info := initial & 0x1f
	off++
	if info >= 28 {
		return Cbor{}, off, &DecodeError{Tag: DecodeErrUnsupportedInfo, Info: info}
	}
	switch major {
	case 0:
		n, o, err := readArg(data, off, info)
		if err != nil {
			return Cbor{}, o, err
		}
		if n > maxInt64Uint {
			return Cbor{}, o, &DecodeError{Tag: DecodeErrIntOverflow, Value: strconv.FormatUint(n, 10)}
		}
		return CInt(int64(n)), o, nil
	case 1:
		n, o, err := readArg(data, off, info)
		if err != nil {
			return Cbor{}, o, err
		}
		if n > maxInt64Uint {
			return Cbor{}, o, &DecodeError{Tag: DecodeErrIntOverflow, Value: negOverflowValue(n)}
		}
		return CInt(-1 - int64(n)), o, nil
	case 2:
		n, o, err := readArg(data, off, info)
		if err != nil {
			return Cbor{}, o, err
		}
		if n > uint64(len(data)-o) {
			return Cbor{}, o, &DecodeError{Tag: DecodeErrTruncated}
		}
		k := int(n)
		return CBytes(append([]byte{}, data[o:o+k]...)), o + k, nil
	case 3:
		n, o, err := readArg(data, off, info)
		if err != nil {
			return Cbor{}, o, err
		}
		if n > uint64(len(data)-o) {
			return Cbor{}, o, &DecodeError{Tag: DecodeErrTruncated}
		}
		k := int(n)
		if !utf8.Valid(data[o : o+k]) {
			return Cbor{}, o + k, &DecodeError{Tag: DecodeErrInvalidUtf8}
		}
		return CText(string(data[o : o+k])), o + k, nil
	case 4:
		n, o, err := readArg(data, off, info)
		if err != nil {
			return Cbor{}, o, err
		}
		a := []Cbor{}
		for i := uint64(0); i < n; i++ {
			v, o2, err := dec(data, o)
			if err != nil {
				return Cbor{}, o2, err
			}
			a = append(a, v)
			o = o2
		}
		return CArr(a), o, nil
	case 5:
		n, o, err := readArg(data, off, info)
		if err != nil {
			return Cbor{}, o, err
		}
		m := []KV{}
		seen := map[int64]bool{}
		for i := uint64(0); i < n; i++ {
			kc, o2, err := dec(data, o)
			if err != nil {
				return Cbor{}, o2, err
			}
			if kc.Kind != KInt {
				return Cbor{}, o2, &DecodeError{Tag: DecodeErrNonIntegerMapKey}
			}
			if seen[kc.I] {
				return Cbor{}, o2, &DecodeError{Tag: DecodeErrDuplicateMapKey, Key: kc.I}
			}
			seen[kc.I] = true
			vc, o3, err := dec(data, o2)
			if err != nil {
				return Cbor{}, o3, err
			}
			m = append(m, KV{K: kc.I, V: vc})
			o = o3
		}
		return CMap(m), o, nil
	case 7:
		switch info {
		case 20:
			return CBool(false), off, nil
		case 21:
			return CBool(true), off, nil
		case 22:
			return CNull(), off, nil
		case 25:
			if off > len(data)-2 {
				return Cbor{}, off, &DecodeError{Tag: DecodeErrTruncated}
			}
			bits := uint16(data[off])<<8 | uint16(data[off+1])
			return CFloat(halfToFloat64(bits)), off + 2, nil
		case 26:
			if off > len(data)-4 {
				return Cbor{}, off, &DecodeError{Tag: DecodeErrTruncated}
			}
			var bits uint32
			for j := 0; j < 4; j++ {
				bits = bits<<8 | uint32(data[off+j])
			}
			return CFloat(float64(math.Float32frombits(bits))), off + 4, nil
		case 27:
			if off > len(data)-8 {
				return Cbor{}, off, &DecodeError{Tag: DecodeErrTruncated}
			}
			var bits uint64
			for j := 0; j < 8; j++ {
				bits = bits<<8 | uint64(data[off+j])
			}
			return CFloat(math.Float64frombits(bits)), off + 8, nil
		}
	}
	return Cbor{}, off, &DecodeError{Tag: DecodeErrUnsupportedMajor, Major: major}
}
