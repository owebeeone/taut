// Extension accessors for the Go CBOR runtime.
// These operate schema-free on the host map and carry the typed extension value
// as a nested Cbor map produced by the generated extension message.
//
// They fail closed (TautCheckedDecode.md CD-E4): host bytes that do not decode are
// the *DecodeError decode reports, and a host that is not a map is WrongType{map}.
// A tag below the band is the caller's error, an *ExtTagError, checked before the
// host is read.
package taut

import "fmt"

const BandStart int64 = 1 << 20

// ExtTagError is an extension tag below BandStart: a caller error, not a
// *DecodeError, which reports bad input.
type ExtTagError struct {
	Tag int64
}

func (e *ExtTagError) Error() string {
	return fmt.Sprintf("extension tag %d is below the band (< %d)", e.Tag, BandStart)
}

// extHost checks tag, then returns the entries of the host's top-level map.
func extHost(host []byte, tag int64) ([]KV, error) {
	if tag < BandStart {
		return nil, &ExtTagError{Tag: tag}
	}
	// TODO(D1): read the host at the depth ceiling with no length bound (TautOptions.md
	// G3) once TryDecode takes D1's depth parameter.
	c, err := TryDecode(host)
	if err != nil {
		return nil, err
	}
	return c.TryMap()
}

// ExtSet sets or replaces an extension value at tag on a top-level host map.
func ExtSet(host []byte, tag int64, value Cbor) ([]byte, error) {
	entries, err := extHost(host, tag)
	if err != nil {
		return nil, err
	}
	m := make([]KV, 0, len(entries)+1)
	for _, kv := range entries {
		if kv.K != tag {
			m = append(m, kv)
		}
	}
	m = append(m, KV{K: tag, V: value})
	return Encode(CMap(m)), nil
}

// ExtGet returns the nested extension Cbor value at tag, and whether it is present.
func ExtGet(host []byte, tag int64) (Cbor, bool, error) {
	entries, err := extHost(host, tag)
	if err != nil {
		return Cbor{}, false, err
	}
	for _, kv := range entries {
		if kv.K == tag {
			return kv.V, true, nil
		}
	}
	return Cbor{}, false, nil
}

// ExtClear removes an extension value at tag from a top-level host map.
func ExtClear(host []byte, tag int64) ([]byte, error) {
	entries, err := extHost(host, tag)
	if err != nil {
		return nil, err
	}
	m := make([]KV, 0, len(entries))
	for _, kv := range entries {
		if kv.K != tag {
			m = append(m, kv)
		}
	}
	return Encode(CMap(m)), nil
}
