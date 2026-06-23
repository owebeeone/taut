# taut — Go API

> Using taut-generated **Go** code: native types, the deterministic-CBOR wire,
> forward-compatibility, and side-channel extensions. Authoring an IR is in
> [Reference.md](Reference.md); serving a service is in [Server.md](Server.md).

Generated Go is plain types over a vendored, dependency-free CBOR runtime. Every
language reproduces the *same bytes* — the conformance corpus proves it.

## 1. Generate

```sh
tautc gen --lang go --with-runtime -o <out>
```

Writes, into `<out>/go/`:

| file | what |
| --- | --- |
| `api.go` | native types (`int64` enums / structs) + `ToCbor`/`FromCbor` |
| `cbor.go` | the deterministic-CBOR runtime (`Cbor`, `Encode`, `Decode`) |
| `ext.go` | extension accessors (`ExtSet`/`ExtGet`/`ExtClear`) |
| `client.go` / `server.go` | typed stubs over a transport (see [Server.md](Server.md)) |

Everything is `package taut` — drop the files in one package and they resolve each
other directly. No third-party modules; `go.mod` only names the module path.

## 2. Native types

Enums are an `int64` named type carrying the wire value; the names are a projection:

```go
type TaskState int64

const (
	TaskStateOpen  TaskState = 0
	TaskStateDoing TaskState = 1
	TaskStateDone  TaskState = 2
)
```

Messages are structs with `ToCbor` / `FromCbor`:

```go
type User struct {
	Id   int64
	Name string
}

func (x User) ToCbor() Cbor      // CMap([]KV{{1, ..}, {2, ..}})
func UserFromCbor(c Cbor) User   // c.Get(1).Int(), c.Get(2).Text()
```

Field mapping: `INT → int64`, `STR → string`, `BYTES → []byte`, `BOOL → bool`,
`FLOAT → float64`, `List(T) → []T`, `Map(K,V) → map[K]V`. Fields and methods are
**PascalCased** (Go exports require capitals). **Optional** fields are `*T`
(encoded as CBOR `null` when `nil`). **Transient** fields are in the struct but
never on the wire (left as the Go zero value on decode).

## 3. Encode / decode

A message ↔ CBOR bytes goes through the generated `ToCbor`/`FromCbor` plus the
runtime `Encode`/`Decode`:

```go
b := Encode(task.ToCbor())        // serialize: []byte
task := TaskFromCbor(Decode(b))   // deserialize
```

## 4. The `Cbor` runtime (`cbor.go`)

A tiny frozen subset of RFC 8949 in core deterministic encoding (definite lengths,
shortest-form ints, ascending map keys, shortest-form floats). Hand-rolled, stdlib
only (`math`, `sort`). `Cbor` is a tagged struct (not an enum) — `Kind` selects the
populated field:

```go
type Kind int
const ( KInt Kind = iota; KBytes; KText; KArr; KMap; KBool; KNull; KFloat )

type KV struct { K int64; V Cbor }            // one integer-keyed map entry

type Cbor struct {
	Kind Kind
	I    int64;  S string;  B []byte
	Arr  []Cbor; Map []KV;  F float64
}

func Encode(c Cbor) []byte
func Decode(data []byte) Cbor
```

Constructors: `CInt(int64)`, `CText(string)`, `CBytes([]byte)`, `CArr([]Cbor)`,
`CMap([]KV)`, `CNull()`, `CFloat(float64)`, `CBool(bool)`. Accessors (return the
zero value on the wrong `Kind`): `.Int()`, `.Text()`, `.Bytes()`, `.Bool()`,
`.Float()`, `.Array()`, `.Get(key int64)` (map value by key — **panics if absent**),
`.MapEntries()`, `.IsNull()`.

## 5. Forward-compatibility (unknown-field preservation)

Generate with `--forward-compat` and each struct gains `WireResidual []KV`. On
`FromCbor`, keys the struct doesn't name are captured there; on `ToCbor`, they're
appended to the known entries and `Encode` sorts the map by key — so the result is
canonical and a node that *decodes → edits → re-encodes* a newer message never
drops fields it doesn't understand. Because Go's `Encode` sorts ascending, the
residual just rides along (no explicit merge step). A message with no unknowns is
byte-identical with or without the flag.

A schema that declares an extension **requires** `--forward-compat` (build error
otherwise — extensions ride the residual space).

## 6. Extensions (side-channels) — `ext.go`

Attach / read / clear a declared extension on *any* host message's wire bytes,
knowing only the extension's schema (never the host's). Tags live in the band
≥ `1<<20` (`BandStart`):

```go
func ExtSet(host []byte, tag int64, value Cbor) []byte   // attach / replace
func ExtGet(host []byte, tag int64) (Cbor, bool)         // ok=false if absent
func ExtClear(host []byte, tag int64) []byte             // strip
```

`value` is the generated extension message's `ToCbor()`; decode `ExtGet`'s result
with `…FromCbor`:

```go
raw := ExtSet(host, 0x100001, decision.ToCbor())
if c, ok := ExtGet(raw, 0x100001); ok {
	decision := DecisionFromCbor(c)
}
raw = ExtClear(raw, 0x100001)
```

A below-band `tag` panics (`"extension tag below band"`); a non-map host panics
(`"extension host is not a map"`). The host app decodes its own message obliviously
— the extension rides in `WireResidual` and survives.

## 7. Consuming the runtime

`cbor.go` / `ext.go` are vendored, dependency-free source — drop them into the
`taut` package alongside `api.go`. `go build` / `go test` is the only toolchain. The
bytes match every other taut target.
