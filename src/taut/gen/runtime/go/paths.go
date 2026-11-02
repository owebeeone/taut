// Canonical immutable Go paths for descriptor-only adapters.
package taut

import (
	"encoding/base64"
	"fmt"
)

type collectionIdentity struct {
	kind   string
	value  any
	length int
}

func ListIdentity[T any](value []T) any {
	if len(value) == 0 {
		return nil
	}
	// The typed start and traversed extent identify a view. A finite prefix
	// shares its start with the enclosing slice but is not the same traversal.
	return collectionIdentity{kind: "list", value: &value[0], length: len(value)}
}

// Go's documented %p map format identifies its backing map without field/type
// reflection, unsafe conversions, or a generic live-value wrapper graph.
func MapIdentity[K comparable, V any](value map[K]V) any {
	if len(value) == 0 {
		return nil
	}
	return collectionIdentity{kind: "map", value: fmt.Sprintf("%p", value)}
}

type PathSegment struct {
	kind, field, keyType, keyBase64 string
	index                           uint64
}

func FieldPath(name string) PathSegment  { return PathSegment{kind: "field", field: name} }
func IndexPath(index uint64) PathSegment { return PathSegment{kind: "index", index: index} }
func KeyPath(keyType string, encoded []byte) PathSegment {
	c, err := TryDecode(encoded)
	if err != nil || (keyType != "str" && keyType != "int" && keyType != "bool") || (keyType == "str" && c.Kind != KText) || (keyType == "int" && c.Kind != KInt) || (keyType == "bool" && c.Kind != KBool) || string(Encode(c)) != string(encoded) {
		panic("invalid canonical Go key path")
	}
	return PathSegment{kind: "key", keyType: keyType, keyBase64: base64.StdEncoding.EncodeToString(encoded)}
}
func (p PathSegment) Kind() string                  { return p.kind }
func (p PathSegment) FieldName() (string, bool)     { return p.field, p.kind == "field" }
func (p PathSegment) Index() (uint64, bool)         { return p.index, p.kind == "index" }
func (p PathSegment) KeyType() (string, bool)       { return p.keyType, p.kind == "key" }
func (p PathSegment) KeyCborBase64() (string, bool) { return p.keyBase64, p.kind == "key" }
func ChildPath(path []PathSegment, part PathSegment) []PathSegment {
	r := make([]PathSegment, len(path)+1)
	copy(r, path)
	r[len(path)] = part
	return r
}
func ownPath(path []PathSegment) []PathSegment {
	r := append([]PathSegment(nil), path...)
	for _, p := range r {
		if p.kind != "field" && p.kind != "index" && p.kind != "key" {
			panic("invalid diagnostic path")
		}
	}
	return r
}
