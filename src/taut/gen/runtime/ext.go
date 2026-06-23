// Extension accessors for the Go CBOR runtime.
// These operate schema-free on the host map and carry the typed extension value
// as a nested Cbor map produced by the generated extension message.
package taut

const BandStart int64 = 1 << 20

func checkExtHost(host Cbor) {
	if host.Kind != KMap {
		panic("extension host is not a map")
	}
}

// ExtSet sets or replaces an extension value at tag on a top-level host map.
func ExtSet(host []byte, tag int64, value Cbor) []byte {
	if tag < BandStart {
		panic("extension tag below band")
	}
	c := Decode(host)
	checkExtHost(c)
	m := make([]KV, 0, len(c.Map)+1)
	for _, kv := range c.Map {
		if kv.K != tag {
			m = append(m, kv)
		}
	}
	m = append(m, KV{K: tag, V: value})
	return Encode(CMap(m))
}

// ExtGet returns the nested extension Cbor value at tag, if present.
func ExtGet(host []byte, tag int64) (Cbor, bool) {
	if tag < BandStart {
		panic("extension tag below band")
	}
	c := Decode(host)
	checkExtHost(c)
	for _, kv := range c.Map {
		if kv.K == tag {
			return kv.V, true
		}
	}
	return Cbor{}, false
}

// ExtClear removes an extension value at tag from a top-level host map.
func ExtClear(host []byte, tag int64) []byte {
	if tag < BandStart {
		panic("extension tag below band")
	}
	c := Decode(host)
	checkExtHost(c)
	m := make([]KV, 0, len(c.Map))
	for _, kv := range c.Map {
		if kv.K != tag {
			m = append(m, kv)
		}
	}
	return Encode(CMap(m))
}
