package taut

// Decode bounds, the raw decoder's own contract (D26: TautCheckedDecode.md §3, CD-E5), as
// taut/src/tests/test_cbor.py pins Python's, the reference; and the extension helpers,
// which read a host at the depth ceiling with no length bound (TautOptions.md G3). Rows
// B1-B30 and the generated typed decodes run through the parity gate.

import (
	"bytes"
	"errors"
	"math"
	"reflect"
	"testing"
)

type decoder func([]byte) (Cbor, error)

// with is TryDecodeWith under the given bounds.
func with(maxDepth, maxEncodedLen int) decoder {
	return func(data []byte) (Cbor, error) {
		return TryDecodeWith(data, maxDepth, maxEncodedLen)
	}
}

// nest is count copies of opener (hex), then leaf: nest(t, "81", 31, "80") is 32 arrays.
func nest(t *testing.T, opener string, count int, leaf string) []byte {
	t.Helper()
	return append(bytes.Repeat(hexBytes(t, opener), count), hexBytes(t, leaf)...)
}

// accepts requires data to decode and re-encode to itself.
func accepts(t *testing.T, decode decoder, data []byte) {
	t.Helper()
	c, err := decode(data)
	if err != nil {
		t.Fatalf("%.40x: %v", data, err)
	}
	if again := Encode(c); !bytes.Equal(again, data) {
		t.Fatalf("%.40x re-encodes as %.40x", data, again)
	}
}

// refused requires data to be refused with want, a *DecodeError itself, and no value.
func refused(t *testing.T, decode decoder, data []byte, want DecodeError) {
	t.Helper()
	c, err := decode(data)
	got, ok := err.(*DecodeError)
	if !ok {
		t.Fatalf("%.40x: got %T %v, want %#v", data, err, err, want)
	}
	if *got != want {
		t.Fatalf("%.40x: got %#v, want %#v", data, *got, want)
	}
	if !reflect.DeepEqual(c, Cbor{}) {
		t.Fatalf("%.40x: a refusal returned %#v", data, c)
	}
}

func tooDeep(limit int) DecodeError {
	return DecodeError{Tag: DecodeErrTooDeep, Limit: limit}
}

func tooLarge(length, limit int) DecodeError {
	return DecodeError{Tag: DecodeErrTooLarge, Len: length, Limit: limit}
}

func TestBoundsConstants(t *testing.T) {
	if DefaultMaxDepth != 32 || MaxDepthCeiling != 128 {
		t.Fatalf("DefaultMaxDepth %d, MaxDepthCeiling %d; want 32 and 128", DefaultMaxDepth, MaxDepthCeiling)
	}
}

func TestBoundsDefaultDepthTakes32ContainersAndRefusesThe33rd(t *testing.T) {
	for _, c := range []struct{ opener, leaf string }{{"81", "80"}, {"a100", "a0"}, {"81", "a0"}, {"a100", "80"}} {
		for _, decode := range []decoder{TryDecode, with(DefaultMaxDepth, -1)} {
			accepts(t, decode, nest(t, c.opener, 31, c.leaf))
			accepts(t, decode, nest(t, c.opener, 32, "00")) // a scalar adds no depth
			refused(t, decode, nest(t, c.opener, 32, c.leaf), tooDeep(32))
		}
	}
}

func TestBoundsArraysAndMapsCountAlike(t *testing.T) {
	accepts(t, TryDecode, nest(t, "81a100", 16, "00")) // 32 containers, alternating
	refused(t, TryDecode, nest(t, "81a100", 16, "80"), tooDeep(32))
	refused(t, TryDecode, nest(t, "81a100", 16, "a0"), tooDeep(32))
}

func TestBoundsATopLevelContainerHasDepth1(t *testing.T) {
	for _, input := range []string{"00", "6161", "80", "a0", "8100", "a10000", "820102"} {
		accepts(t, with(1, -1), hexBytes(t, input))
	}
	for _, input := range []string{"8180", "81a0", "a10080", "a100a0", "820180"} {
		refused(t, with(1, -1), hexBytes(t, input), tooDeep(1))
	}
}

func TestBoundsAMapKeyIsAnItemOfItsMap(t *testing.T) {
	// The key item is read first, depth included, then checked (CD-E5 step 3).
	refused(t, with(1, -1), hexBytes(t, "a18000"), tooDeep(1))
	refused(t, with(2, -1), hexBytes(t, "a18000"), DecodeError{Tag: DecodeErrNonIntegerMapKey})
}

func TestBoundsADepthArgumentAppliesAsGiven(t *testing.T) {
	for _, depth := range []int{1, 2, 5, 31, 33, 64, 127, 128} {
		accepts(t, with(depth, -1), nest(t, "81", depth-1, "80"))
		refused(t, with(depth, -1), nest(t, "81", depth, "80"), tooDeep(depth))
	}
}

func TestBoundsADepthArgumentAboveTheCeilingAppliesTheCeiling(t *testing.T) {
	for _, depth := range []int{129, 1000, math.MaxInt32, math.MaxInt} {
		accepts(t, with(depth, -1), nest(t, "81", 127, "80"))
		refused(t, with(depth, -1), nest(t, "81", 128, "80"), tooDeep(128))
	}
}

func TestBoundsDepthIsCheckedOnceTheHeadIsComplete(t *testing.T) {
	// CD-B2: before the first item, so missing items do not matter...
	refused(t, TryDecode, nest(t, "81", 33, ""), tooDeep(32))
	refused(t, TryDecode, nest(t, "a100", 32, "a1"), tooDeep(32))
	refused(t, TryDecode, nest(t, "81", 32, "9bffffffffffffffff"), tooDeep(32))
	refused(t, TryDecode, nest(t, "81", 32, "bbffffffffffffffff"), tooDeep(32))
	// ...but a torn head is Truncated, and the head's own faults come first.
	for _, torn := range []string{"98", "9900", "9a000000", "9b00", "b8", "bb00000000000000"} {
		refused(t, TryDecode, nest(t, "81", 32, torn), DecodeError{Tag: DecodeErrTruncated})
	}
	refused(t, TryDecode, nest(t, "81", 32, "9800"), DecodeError{Tag: DecodeErrNonCanonicalInt, Value: "0"})
	refused(t, TryDecode, nest(t, "81", 32, "9c"), DecodeError{Tag: DecodeErrUnsupportedInfo, Info: 28})
	refused(t, TryDecode, nest(t, "81", 32, "bf"), DecodeError{Tag: DecodeErrUnsupportedInfo, Info: 31})
}

// Deep input is refused at the bound, with no stack overflow and no panic: before D1 a
// megabyte of nesting exhausted the goroutine stack, which kills the process.
func TestBoundsDeepInputIsTooDeepAndNothingEscapes(t *testing.T) {
	for _, c := range []struct{ opener, leaf string }{{"81", "80"}, {"a100", "a0"}, {"81a100", "80"}} {
		for _, count := range []int{100000, 1000000} {
			data := nest(t, c.opener, count, c.leaf)
			refused(t, TryDecode, data, tooDeep(32))
			refused(t, with(MaxDepthCeiling, -1), data, tooDeep(128))
			refused(t, with(1000000000, -1), data, tooDeep(128))
		}
	}
}

func TestBoundsLength(t *testing.T) {
	data := hexBytes(t, "83010203")
	accepts(t, with(DefaultMaxDepth, 4), data) // exactly at the bound
	accepts(t, with(DefaultMaxDepth, math.MaxInt), data)
	refused(t, with(DefaultMaxDepth, 3), data, tooLarge(4, 3))
	big := Encode(CBytes(bytes.Repeat([]byte("x"), 100000)))
	accepts(t, TryDecode, big) // no bound unless one is passed
	for _, none := range []int{-1, -2, math.MinInt} {
		accepts(t, with(DefaultMaxDepth, none), big) // a negative length is no bound
	}
	refused(t, with(DefaultMaxDepth, len(big)-1), big, tooLarge(len(big), len(big)-1))
}

func TestBoundsLengthIsCheckedBeforeAnyByteIsRead(t *testing.T) {
	refused(t, with(DefaultMaxDepth, 3), hexBytes(t, "c0c0c0c0"), tooLarge(4, 3))
	refused(t, with(DefaultMaxDepth, 10), nest(t, "81", 40, "80"), tooLarge(41, 10))
	refused(t, with(DefaultMaxDepth, 1), hexBytes(t, "0000"), tooLarge(2, 1))
}

func TestBoundsAZeroLengthBound(t *testing.T) {
	refused(t, with(DefaultMaxDepth, 0), []byte{}, DecodeError{Tag: DecodeErrTruncated})
	refused(t, with(DefaultMaxDepth, 0), hexBytes(t, "00"), tooLarge(1, 0))
}

// A depth below 1 is the caller's error: an ordinary error, never a *DecodeError, reported
// before any byte is read or the length is checked.
func TestBoundsADepthBelow1IsACallerError(t *testing.T) {
	for _, depth := range []int{0, -1, math.MinInt} {
		for _, input := range []string{"", "00", "c0c0c0c0", "8180"} {
			for _, length := range []int{-1, 0, 1000} {
				c, err := TryDecodeWith(hexBytes(t, input), depth, length)
				var decodeErr *DecodeError
				if err == nil || errors.As(err, &decodeErr) {
					t.Fatalf("depth %d, %q, len %d: got %T %v, want a caller error", depth, input, length, err, err)
				}
				if !reflect.DeepEqual(c, Cbor{}) {
					t.Fatalf("depth %d, %q: a caller error returned %#v", depth, input, c)
				}
			}
		}
	}
}

func TestBoundsErrorTextNamesThePayload(t *testing.T) {
	if text := (&DecodeError{Tag: DecodeErrTooDeep, Limit: 32}).Error(); text != "TooDeep(limit=32)" {
		t.Fatalf("TooDeep text %q", text)
	}
	if text := (&DecodeError{Tag: DecodeErrTooLarge, Len: 4, Limit: 3}).Error(); text != "TooLarge(len=4, limit=3)" {
		t.Fatalf("TooLarge text %q", text)
	}
}

// host is a host map whose unknown field 7 holds arrays nested arrays: 1 + arrays deep.
func host(t *testing.T, arrays int) []byte {
	t.Helper()
	return append(hexBytes(t, "a107"), nest(t, "81", arrays-1, "80")...)
}

// The extension helpers cannot know the host's schema, so they read it at the depth
// ceiling, the one depth every valid host meets, and leave its own bounds to its reader.
func TestBoundsAHostIsReadAtTheDepthCeiling(t *testing.T) {
	const tag = BandStart + 1
	value := CMap([]KV{{K: 1, V: CText("b7")}, {K: 2, V: CInt(1)}})
	atCeiling := host(t, 127) // 128 deep
	if _, ok, err := ExtGet(atCeiling, tag); ok || err != nil {
		t.Fatalf("ExtGet at the ceiling: %v, %v", ok, err)
	}
	if cleared, err := ExtClear(atCeiling, tag); err != nil || !bytes.Equal(cleared, atCeiling) {
		t.Fatalf("ExtClear at the ceiling: %x, %v", cleared, err)
	}
	strapped, err := ExtSet(atCeiling, tag, value)
	if err != nil {
		t.Fatalf("ExtSet at the ceiling: %v", err)
	}
	if got, ok, err := ExtGet(strapped, tag); err != nil || !ok || !bytes.Equal(Encode(got), Encode(value)) {
		t.Fatalf("ExtGet of the set value: %x, %v, %v", Encode(got), ok, err)
	}
	for _, arrays := range []int{128, 100000} { // 129 deep, and far beyond
		deep := host(t, arrays)
		set, setErr := ExtSet(deep, tag, value)
		_, ok, getErr := ExtGet(deep, tag)
		cleared, clearErr := ExtClear(deep, tag)
		if set != nil || ok || cleared != nil {
			t.Fatalf("%d arrays: a refused host returned %x, %v, %x", arrays, set, ok, cleared)
		}
		for op, err := range []error{setErr, getErr, clearErr} {
			got, isDecodeErr := err.(*DecodeError)
			if !isDecodeErr || *got != tooDeep(MaxDepthCeiling) {
				t.Fatalf("%d arrays, op %d: got %T %v, want TooDeep{128}", arrays, op, err, err)
			}
		}
	}
}

func TestBoundsAHostIsReadWithNoLengthBound(t *testing.T) {
	const tag = BandStart + 1
	value := CMap([]KV{{K: 1, V: CText("b7")}, {K: 2, V: CInt(1)}})
	big := Encode(CMap([]KV{{K: 1, V: CInt(1)}, {K: 7, V: CBytes(bytes.Repeat([]byte("x"), 100000))}}))
	strapped, err := ExtSet(big, tag, value)
	if err != nil {
		t.Fatalf("ExtSet: %v", err)
	}
	if got, ok, err := ExtGet(strapped, tag); err != nil || !ok || !bytes.Equal(Encode(got), Encode(value)) {
		t.Fatalf("ExtGet: %x, %v, %v", Encode(got), ok, err)
	}
	if cleared, err := ExtClear(strapped, tag); err != nil || !bytes.Equal(cleared, big) {
		t.Fatalf("ExtClear: %v", err)
	}
}
