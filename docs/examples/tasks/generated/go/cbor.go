// Minimal deterministic CBOR — the Go binding of the frozen wire substrate.
// Byte-for-byte identical to taut/src/taut/wire/cbor.py and the Rust/TS/C++/Swift
// runtimes: the same tiny subset (int, bytes, text, array, int-keyed map, bool,
// null) in core-deterministic encoding (definite length, shortest-form ints,
// ascending map keys). Hand-rolled, stdlib only.
package taut

import "sort"

type Kind int

const (
	KInt Kind = iota
	KBytes
	KText
	KArr
	KMap
	KBool
	KNull
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
}

func CInt(n int64) Cbor    { return Cbor{Kind: KInt, I: n} }
func CText(s string) Cbor  { return Cbor{Kind: KText, S: s} }
func CBytes(b []byte) Cbor { return Cbor{Kind: KBytes, B: b} }
func CArr(a []Cbor) Cbor   { return Cbor{Kind: KArr, Arr: a} }
func CMap(m []KV) Cbor     { return Cbor{Kind: KMap, Map: m} }
func CNull() Cbor          { return Cbor{Kind: KNull} }
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
		}
	}
	panic("unsupported CBOR item")
}
