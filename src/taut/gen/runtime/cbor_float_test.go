package taut

import (
	"encoding/binary"
	"encoding/hex"
	"encoding/json"
	"math"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

type floatVector struct {
	Note string `json:"note"`
	F64  string `json:"f64"`
	Cbor string `json:"cbor"`
}

func readFloatVectors(t *testing.T) []floatVector {
	t.Helper()
	dir, err := os.Getwd()
	if err != nil {
		t.Fatal(err)
	}
	for {
		path := filepath.Join(dir, "corpus", "float_vectors.json")
		data, err := os.ReadFile(path)
		if err == nil {
			var rows []floatVector
			if err := json.Unmarshal(data, &rows); err != nil {
				t.Fatal(err)
			}
			return rows
		}
		parent := filepath.Dir(dir)
		if parent == dir {
			t.Fatal("could not find corpus/float_vectors.json")
		}
		dir = parent
	}
}

func hexBytes(t *testing.T, s string) []byte {
	t.Helper()
	b, err := hex.DecodeString(s)
	if err != nil {
		t.Fatal(err)
	}
	return b
}

func f64FromHex(t *testing.T, s string) float64 {
	t.Helper()
	b := hexBytes(t, s)
	if len(b) != 8 {
		t.Fatalf("f64 bit string has %d bytes", len(b))
	}
	return math.Float64frombits(binary.BigEndian.Uint64(b))
}

func TestFloatVectorsEncodeReencodeAndDecodeBits(t *testing.T) {
	for _, row := range readFloatVectors(t) {
		v := f64FromHex(t, row.F64)
		if got := hex.EncodeToString(Encode(CFloat(v))); got != row.Cbor {
			t.Fatalf("%s encode: got %s want %s", row.Note, got, row.Cbor)
		}

		decoded := Decode(hexBytes(t, row.Cbor))
		if decoded.Kind != KFloat {
			t.Fatalf("%s decode kind: got %v want KFloat", row.Note, decoded.Kind)
		}
		if got := hex.EncodeToString(Encode(decoded)); got != row.Cbor {
			t.Fatalf("%s re-encode: got %s want %s", row.Note, got, row.Cbor)
		}
		if !strings.HasPrefix(row.Note, "nan") && math.Float64bits(decoded.Float()) != math.Float64bits(v) {
			t.Fatalf("%s decode bits: got %016x want %s", row.Note, math.Float64bits(decoded.Float()), row.F64)
		}
	}
}

func TestFloatDecodeAcceptsAllWidths(t *testing.T) {
	for _, hx := range []string{"f93c00", "fa3f800000", "fb3ff0000000000000"} {
		if got := Decode(hexBytes(t, hx)).Float(); got != 1.0 {
			t.Fatalf("%s decoded to %v", hx, got)
		}
	}
}
