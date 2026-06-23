// Minimal deterministic CBOR — the Go binding of the frozen wire substrate.
// Byte-for-byte identical to taut/src/taut/wire/cbor.py and the Rust/TS/C++/Swift
// runtimes: the same tiny subset (int, bytes, text, array, int-keyed map, bool,
// null, float) in core-deterministic encoding (definite length, shortest-form
// ints/floats, ascending map keys). Hand-rolled, stdlib only.
package taut

import (
	"math"
	"sort"
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
	for _, kv := range c.Map {
		if kv.K == key {
			return kv.V
		}
	}
	panic("no map key")
}
func (c Cbor) Int() int64       { return c.I }
func (c Cbor) Text() string     { return c.S }
func (c Cbor) Bytes() []byte    { return c.B }
func (c Cbor) Bool() bool       { return c.I != 0 }
func (c Cbor) Array() []Cbor    { return c.Arr }
func (c Cbor) IsNull() bool     { return c.Kind == KNull }
func (c Cbor) MapEntries() []KV { return c.Map } // forward-compat residual capture
func (c Cbor) Float() float64   { return c.F }

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
	v, off := dec(data, 0)
	if off != len(data) {
		panic("trailing bytes after top-level CBOR item")
	}
	return v
}

func readArg(data []byte, off int, info byte) (uint64, int) {
	switch {
	case info < 24:
		return uint64(info), off
	case info == 24:
		return uint64(data[off]), off + 1
	case info == 25:
		return uint64(data[off])<<8 | uint64(data[off+1]), off + 2
	case info == 26:
		var v uint64
		for j := 0; j < 4; j++ {
			v = v<<8 | uint64(data[off+j])
		}
		return v, off + 4
	default:
		var v uint64
		for j := 0; j < 8; j++ {
			v = v<<8 | uint64(data[off+j])
		}
		return v, off + 8
	}
}

func dec(data []byte, off int) (Cbor, int) {
	initial := data[off]
	major := initial >> 5
	info := initial & 0x1f
	off++
	switch major {
	case 0:
		n, o := readArg(data, off, info)
		return CInt(int64(n)), o
	case 1:
		n, o := readArg(data, off, info)
		return CInt(-1 - int64(n)), o
	case 2:
		n, o := readArg(data, off, info)
		k := int(n)
		return CBytes(append([]byte{}, data[o:o+k]...)), o + k
	case 3:
		n, o := readArg(data, off, info)
		k := int(n)
		return CText(string(data[o : o+k])), o + k
	case 4:
		n, o := readArg(data, off, info)
		a := []Cbor{}
		for i := uint64(0); i < n; i++ {
			v, o2 := dec(data, o)
			a = append(a, v)
			o = o2
		}
		return CArr(a), o
	case 5:
		n, o := readArg(data, off, info)
		m := []KV{}
		for i := uint64(0); i < n; i++ {
			kc, o2 := dec(data, o)
			vc, o3 := dec(data, o2)
			m = append(m, KV{K: kc.I, V: vc})
			o = o3
		}
		return CMap(m), o
	case 7:
		switch info {
		case 20:
			return CBool(false), off
		case 21:
			return CBool(true), off
		case 22:
			return CNull(), off
		case 25:
			bits := uint16(data[off])<<8 | uint16(data[off+1])
			return CFloat(halfToFloat64(bits)), off + 2
		case 26:
			var bits uint32
			for j := 0; j < 4; j++ {
				bits = bits<<8 | uint32(data[off+j])
			}
			return CFloat(float64(math.Float32frombits(bits))), off + 4
		case 27:
			var bits uint64
			for j := 0; j < 8; j++ {
				bits = bits<<8 | uint64(data[off+j])
			}
			return CFloat(math.Float64frombits(bits)), off + 8
		}
	}
	panic("unsupported CBOR item")
}
