# Checked decode: one error and one depth bound in Rust, TypeScript and Python

**Status:** DESIGN, proposed 2026-09-28, awaiting the owner's ruling. A document only: no code,
corpus, fixture or version has changed. Once ruled, it becomes decision **D26** in
[TautDecisions.md](TautDecisions.md) (D25 is the last) and parity contract `taut-codec-parity/i64/v1`.

**Builds on** [RustFailClosed.md](RustFailClosed.md) (fail-closed Rust is the default since v0.8.0)
and [TautCodecParityPlan.md](TautCodecParityPlan.md) (D1, D2 ratified 2026-07-07; §2b's tag vocabulary).

**Evidence.** Paths are from the glade-wz root; lines are at taut `7a5f616` (v0.9.1 + 3), glade
`2a3c6f8`, taut-shape `9a75209`, taut-shape-rs `b442d07`, taut-shape-ts `137f843`. **OWNER** marks a
ruling, **PROPOSED** this design, **MEASURED** a run on 2026-09-28, **READ** code read but not run.

## 0. The ruling this note implements

> "we are allowed to change the taut contract - (return error instead of panic) the question becomes
> consistency across languages (py,ts,rs) - taut has only a few clients, especially taut-shape*"
> (the owner, 2026-09-28)

**OWNER, 2026-09-28:** one typed decode-depth error in Rust, TypeScript and Python; a shared corpus
of bad inputs; an audit of each language's parity; and glade's move to the fail-closed codec
(`dev-docs/GladeFirstSlicePlan.md:945`, item 10). glade's node step "taut's checked decodes and
client-rs's checked `dispatch`" waits on this note (`dev-docs/GladeFirstSlicePlan.md:1099`).

The property this note makes precise: **for any input bytes, every decode entry point returns either
a value or a `DecodeError`. It never panics, aborts, runs out of stack or throws anything else, and
Rust, TypeScript and Python give the same tag and payload for the same bytes.** The scope is the four
Wave-1 codecs that `tautc parity` gates: rust, python, typescript and js. The Wave-2 codecs stay
allowlisted (§8, G1).

## 1. The recommendations in brief

| # | Topic | Recommendation (PROPOSED) |
|---|---|---|
| 1 | Error | Keep the one `DecodeError` each runtime already has and add two tags, `TooDeep{limit}` and `TooLarge{len, limit}`. Rust returns a `Result`, TypeScript throws and Python raises. One fixed order of checks decides which tag is reported. |
| 2 | Bounds | `MAX_DEPTH = 32` is a contract constant, not a per-call option: 32 nested arrays or maps decode and the 33rd is `TooDeep`. Size stays with each carrier; decode takes an optional `max_bytes` and raises `TooLarge` above it. |
| 3 | Corpus | A new `taut/corpus/parity/bounds.vectors.json` (16 rows) and 14 new rows in `malformed.vectors.json`. The gate and every client replay them, each client against the runtime copy it ships. |
| 4 | Audit | No runtime bounds depth. On deep input Rust overflows its stack (an abort), Python raises `RecursionError` and TypeScript `RangeError`. There are also ten smaller divergences (M1-M14), and a gate that can report GREEN for rows that never ran. |
| 5 | Version | taut **v0.10.0**, the release that already removes `--legacy-codec`. There is no opt-out of the bound. Clients adopt through a 0.10 shape release train. |
| 6 | glade | Regenerate `wire-rs` from v0.10.0's fail-closed path; delete `checked.rs` and `wellformed.rs` but keep their tests; node and client-rs call the fallible API; client-rs's carrier gets `frame_len`. client-ts moves later. |

## 2. The error

**CD-E1 (PROPOSED).** Each runtime keeps its one error type, `DecodeError`, and its tag vocabulary
(`TautCodecParityPlan.md:102-108`), and gains two tags. No new error type is added: the owner's
"typed decode-depth error" is the new `TooDeep` tag of that one type. The table maps each kind of
failure this note must cover onto its tags. There is no catch-all `Malformed` tag, because the
corpus pins the specific tags and D2 ratified them (`TautCodecParityPlan.md:55-57`).

| Kind | Tags (payload) |
|---|---|
| depth exceeded | **`TooDeep`** (`limit`), new |
| over size | **`TooLarge`** (`len`, `limit`), new |
| truncated | `Truncated` |
| malformed | `TrailingBytes`, `InvalidUtf8`, `UnsupportedInfo` (`info`), `UnsupportedMajor` (`major`), `NonIntegerMapKey`, `NegativeMapKey` (`key`), `DuplicateMapKey` (`key`), `NonCanonicalInt` (`value`), `IntOverflow` (`value`) |
| wrong type | `WrongType` (`expected`), `MissingKey` (`key`), `UnknownEnum` (`enum`, `value`) |

**CD-E2 (PROPOSED): the form in each language.**

- **Rust:** every decode entry point returns `Result<_, DecodeError>`, as `try_decode`, `from_cbor`
  and `from_wire` already do. The enum (`taut/src/taut/gen/runtime/cbor_fail_closed.rs:40-82`) gains
  `TooDeep { limit: usize }`, `TooLarge { len: usize, limit: usize }` and
  `fn tag(&self) -> &'static str` for the canonical tag; the gate's `tag_name`
  (`taut/src/taut/corpus/parity.py:357-373`) moves into the runtime as this method.
- **TypeScript:** decode **throws** a `DecodeError`
  (`taut/src/taut/gen/runtime/typescript/cbor.ts:50-65`); `DecodeErrorTag` (`:26-39`) gains
  `"TooDeep" | "TooLarge"` and `DecodeErrorFields` gains `limit` and `len`. CD-E3 gives the reasons.
- **Python:** decode raises `DecodeError(ValueError)` (`taut/src/taut/wire/cbor.py:33-42`) with
  `.tag` and the payload as attributes, e.g. `DecodeError("TooDeep", limit=32)`: one class, not a
  subclass per tag, so callers branch on `.tag` as in TypeScript and `except ValueError` still works.

**CD-E3 (PROPOSED): TypeScript throws; it does not return a result.** Both frame boundaries that
decode today already wrap it in `try`: taut-shape-ts (`taut-shape-ts/src/framing.ts:90-94`) and
glade's client-ts (`glade/client-ts/src/client.ts:132-138`); taut's own RPC client does not
(`taut/src/taut/gen/runtime/typescript/taut_client.ts:88-91`) and gains one. A result type would
change every call site for no safety a `try` lacks, and the codec recurses through `fromWire`, where a
throw unwinds for free but a result must be passed back up each level. Parity is on tag and payload,
not control flow: `Result` and `raise` are Rust's and Python's own idioms. What TypeScript must add is
a guarantee: **nothing but `DecodeError` escapes decode** (today a `RangeError` does, §5.3). As each
package vendors its own `cbor.ts`, a check across copies tests `e.name === "DecodeError"` (set at
`cbor.ts:61`) and a string `tag`, not `instanceof`.

**CD-E4 (PROPOSED): nothing else escapes.** No panic, abort or stack overflow in Rust; no
`RecursionError`, `TypeError` or `KeyError` in Python; no `RangeError`, `TypeError` or plain `Error`
in TypeScript. Likewise the extension helpers that decode a host message
(`taut/src/taut/gen/runtime/ext.rs:18-23`, `taut/src/taut/ext.py:35-38`,
`taut/src/taut/gen/runtime/typescript/ext.ts:17-22`): a host that is not a map is `WrongType{map}`.

**CD-E5 (PROPOSED): one order of checks.** Decode reads left to right and reports the first check
that fails:

1. With `max_bytes` given, input longer than it is `TooLarge`, before any byte is read.
2. Each item's head: no byte left is `Truncated`; major type 6 is `UnsupportedMajor`; additional
   info 28-31, or a major-7 value other than false, true, null and the three floats, is
   `UnsupportedInfo`; missing argument bytes are `Truncated`; an argument longer than needed is
   `NonCanonicalInt`.
3. Its body: an int outside `i64` is `IntOverflow`; a byte or text length beyond the remaining bytes
   is `Truncated`, whatever its size; text that is not UTF-8 is `InvalidUtf8`; an array or map one
   level too deep is `TooDeep`, before any of its items is read. Items are read in order, and a map
   entry key first: the key item, then `NonIntegerMapKey`, `NegativeMapKey`, `DuplicateMapKey`, then
   the value.
4. Bytes after the top-level item are `TrailingBytes`.
5. Only then the schema stage. The message must be a map (`WrongType{map}`), even one with no
   fields. Fields are checked in IR order: a required field absent is `MissingKey`; an optional field
   absent or null is null; a wrong CBOR type is `WrongType`; an unknown enum value is `UnknownEnum`.
   A `map<K,V>` entry checks for keys 1 and 2 before decoding either; a repeated key is
   `DuplicateMapKey`.

An absent optional field decodes to null because `taut/src/taut/ir/compat.py:11` classes "add an
*optional* field" as compatible, so a reader must accept bytes from a writer older than the field.

**CD-E6 (PROPOSED): payload words.** `WrongType.expected` is one of `int`, `float`, `bytes`,
`text`, `bool`, `array` or `map` in every language; Rust and Python already use these words, while
TypeScript and JS say `str` and `list` (§5.3). Display text is not part of the contract; tag and
payload are.

## 3. The bounds

**CD-B1 (PROPOSED): depth.** `MAX_DEPTH = 32`. An array or map has depth one more than the number
of arrays and maps around it, so a top-level container has depth 1. A container at depth 33 is refused
with `TooDeep{limit: 32}`, whether or not it is empty. Ints, strings, bools, null and floats add no
depth. So 32 nested containers decode, a scalar inside the 32nd decodes, and the 33rd container fails.
This is glade's F15 bound exactly (`glade/wire-rs/src/wellformed.rs:25`, `:122-124`, tested at
`:187-196`), so on depth alone glade accepts and refuses the same inputs it does today.

Why 32: this workspace's schemas nest at most six deep (glade five,
`glade/wire-rs/src/wellformed.rs:19-24`; taut-shape's crdt read response six,
`taut-shape/ir/shape_crdt.taut.py:48-80`; razel three, `taut/ir/razel.taut.py:91-93`), leaving 26
levels for fields a later version adds and a reader keeps as residual (D9). At 33 frames no runtime
is near its limit: Python's default recursion limit is 1,000, and a debug glade build's 2 MiB worker
stack overflowed near 1,000 levels (`dev-docs/GladeFirstSlicePlan.md:994`).

**CD-B2 (PROPOSED): where the check runs.** Once a container's head (initial byte and argument) is
complete, and before its first item. So a torn head is `Truncated`, and a complete 33rd head is
`TooDeep` even if its items are missing. The bound applies per decode call: a `bytes` field that
carries CBOR, such as glade's `Op.payload`, is decoded by its own call with its own 32 levels. Depth
counts from the top-level item, unknown fields included. The schema stage recurses no deeper than
the raw decode did, so it needs no second counter.

**CD-B3 (PROPOSED): a contract constant, not an option.** Each runtime exports `MAX_DEPTH`; the
corpus records `"max_depth": 32` and every harness checks they are equal. No call may raise it (that
reopens the overflow) or lower it (the same bytes would then decode differently by caller); glade's
depth-2 `envelope::parse` (`glade/node/src/envelope.rs:305-345`) is a shape check and stays one.
`tautc` SHOULD refuse at validation a schema whose non-recursive nesting exceeds 32, which no
conforming reader could decode, and SHOULD warn about a message that refers to itself (a tree).

**CD-B4 (PROPOSED): size stays with the carrier.** Decode sees bytes only once they are in memory,
so the bound that matters is the carrier's, on a frame's claimed length before it allocates, as
glade's `frame_len` does (`glade/node/src/frame.rs:19-33`; `glade/node/src/ws.rs:236-243`,
`glade/node/src/peer.rs:62-68`). taut cannot pick one number for glade (16 MiB), taut-shape's stdin
framing (u32) and razel's socket. taut adds only the shared tag and an opt-in check: Rust
`try_decode_max(bytes, max_bytes)`, Python `loads(data, *, max_bytes=None)` and
`codec.decode(..., max_bytes=None)`, TypeScript `decode(data, { maxBytes })`. With no limit there is
no size check; a caller with no carrier, such as one reading a record from disk, gets the same
`TooLarge` in every language.

**CD-B5 (PROPOSED): exactly at the bound.** Depth 32 decodes and 33 fails. Input of exactly
`max_bytes` decodes and one byte more fails; `max_bytes = 0` with empty input is `Truncated`.
glade's frame cap already accepts exactly 16 MiB (`glade/node/src/frame.rs:27`; test
`glade/node/src/peer.rs:664-694`).

## 4. The shared corpus

**CD-C1 (PROPOSED): layout.** The new file sits beside the existing files in `taut/corpus/parity/`:

```
allowlist.json           contract id -> taut-codec-parity/i64/v1
gen_vectors.py           also writes bounds.vectors.json (rows written by hand, as today)
int.vectors.json         rows unchanged; contract id bumped
malformed.vectors.json   + 14 rows (§4.4, M1-M14)
bounds.vectors.json      new: 16 depth and size rows (§4.4, B1-B16); "max_depth": 32
```

The fixture `taut/ir/parity_int.taut.py` gains two messages for the schema-stage rows:
`OptBox { note: str optional = 1, tags: list<str> = 2 }` and `Empty`, which has no fields.

**CD-C2 (PROPOSED): row format.** Rows keep today's fields (`name`, `stage`, `bytes`, `expect`,
`why`, `lead`; `taut/corpus/parity/malformed.vectors.json:6-124`). `bytes` may also be a list of
segments, each a hex string or `{"repeat": "<hex>", "count": N}`, so a 100,000-deep row stays one
line. A new `len` gives the expanded length, which a harness checks before decoding, and a new
`limits` carries `{"max_bytes": N}`. `expect` is either `{"tag": ..., <payload>}` or, for a row at a
bound that must decode, `{"accept": true}`. New rows enter with `"lead": true`, the gate's existing
way of demanding behaviour not yet built (`taut/corpus/parity/gen_vectors.py:17-24`).

**CD-C3 (PROPOSED): how each language reads it.** In **the gate** (`tautc parity`,
`taut/src/taut/corpus/parity.py`), Python reads the JSON directly (`:257-308`), the Rust runner gets
its tables written into its source (`:426-445`) as segments plus a small `expand` function, and the
TypeScript and JS runners read the JSON copied into their temporary directory (`:583-625`). **Each
client replays the rows against the copy it ships**, not taut's source. Rust clients have no JSON
parser (`glade/wire-rs/Cargo.toml` has no dependencies), so the conformance kit (D23) emits a
`parity_vectors.rs` table beside the vendored `cbor.rs`, and taut-shape-rs and glade's wire-rs replay
its `raw_decode` rows in `cargo test`. taut-shape-ts reads a vendored JSON copy; glade's client-ts
reads `taut/corpus/parity/` by the sibling path its oracle test already uses
(`glade/client-ts/test/oracle.test.ts:17`). The Python oracle, taut-shape, runs taut's installed
runtime, so `tautc parity -t python` at its pinned taut is its replay.

**CD-C4 (PROPOSED): what every harness checks.** `MAX_DEPTH` equals the corpus's `max_depth`; the
expanded length equals `len`; the error is the language's `DecodeError` (anything else is "untyped",
a failure); the tag matches; each payload field named in `expect` matches when compared as a string,
except `IntOverflow.value`, which Rust's variant does not carry. A row that never reports counts as a
failure, and a runner that exits non-zero fails its target.

### 4.4 The rows and the expected result for each

"Today" is READ from the code, except the gate's baseline (§5.1); `n×XX` is XX repeated n times.

| Row | Stage | Bytes | Expected | Today, where it differs |
|---|---|---|---|---|
| B1 depth-32-arrays | raw | 31×`81`, `80` | accept | — |
| B2 depth-33-arrays | raw | 32×`81`, `80` | `TooDeep{32}` | all accept |
| B3 depth-32-maps | raw | 31×`a100`, `a0` | accept | — |
| B4 depth-33-maps | raw | 32×`a100`, `a0` | `TooDeep{32}` | all accept |
| B5 depth-32-scalar-leaf | raw | 32×`81`, `00` | accept | — |
| B6 depth-33-items-missing | raw | 33×`81` | `TooDeep{32}` | all `Truncated` |
| B7 depth-33-torn-head | raw | 32×`81`, `9b00` | `Truncated` | — |
| B8 depth-33-mixed | raw | 16×`81a100`, `80` | `TooDeep{32}` | all accept |
| B9 depth-100000-arrays | raw | 99999×`81`, `80` | `TooDeep{32}` | Rust aborts; Python `RecursionError`; TS `RangeError` |
| B10 depth-100000-maps | raw | 99999×`a100`, `a0` | `TooDeep{32}` | as B9 |
| B11 depth-33-unknown-field | from_cbor IntBox | `a30100028009`, 31×`81`, `80` | `TooDeep{32}` | all accept |
| B12 depth-32-unknown-field | from_cbor IntBox | `a30100028009`, 30×`81`, `80` | accept | — |
| B13 size-at-limit | raw, max 4 | `83010203` | accept | no `max_bytes` yet |
| B14 size-over-limit | raw, max 3 | `83010203` | `TooLarge{4, 3}` | no `max_bytes` yet |
| B15 size-before-parse | raw, max 3 | `c0c0c0c0` | `TooLarge{4, 3}` | no `max_bytes` yet |
| B16 size-empty | raw, max 0 | (empty) | `Truncated` | no `max_bytes` yet |
| M1 text-length-over-2^53 | raw | `5b0020000000000000` | `Truncated` | TS, JS `IntOverflow` |
| M2 array-count-u64-max | raw | `9bffffffffffffffff` | `Truncated` | TS, JS `IntOverflow` |
| M3 items-read-in-order | raw | `85c0` | `UnsupportedMajor{6}` | glade `wellformed` says `Truncated` |
| M4 key-first-duplicate | raw | `a2010001` | `DuplicateMapKey{1}` | Rust `Truncated` |
| M5 key-first-text | raw | `a16178` | `NonIntegerMapKey` | Rust `Truncated` |
| M6 key-first-negative | raw | `a120` | `NegativeMapKey{-1}` | Rust `Truncated` |
| M7 major-6-info-28 | raw | `dc` | `UnsupportedMajor{6}` | JS `UnsupportedInfo{28}` |
| M8 map-key-2^53 | raw | `a11b002000000000000000` | accept | TS `NonIntegerMapKey` |
| M9 wrong-type-text | from_cbor OptBox | `a201010280` | `WrongType{text}` | TS, JS `str` |
| M10 wrong-type-array | from_cbor OptBox | `a201f60200` | `WrongType{array}` | TS `list` |
| M11 optional-absent | from_cbor OptBox | `a10280` | accept, `note` null | Rust, JS `MissingKey{1}` |
| M12 empty-message-not-map | from_cbor Empty | `00` | `WrongType{map}` | Rust, JS accept |
| M13 map-field-duplicate | from_cbor IntBox | `a201000282a201050201a201050202` | `DuplicateMapKey{5}` | Rust, JS accept (last entry wins) |
| M14 map-entry-keys-first | from_cbor IntBox | `a201000281a1016178` | `MissingKey{2}` | Rust, JS `WrongType{int}` |

The rows that test each rule: CD-B1, B1-B5 and B8-B10; CD-B2, B6, B7, B11 and B12; CD-B4 and CD-B5,
B13-B16; CD-E5, M1-M8 and M11-M14; CD-E6, M9 and M10.

## 5. The parity audit (2026-09-28)

### 5.1 What was measured

`tautc parity`, the Wave-1 gate: GREEN for rust, python, typescript and js on 11 int and 16
malformed rows (rust: 24 pass, 3 type-satisfied); none of the 27 nests anything. taut's `test_cbor.py`,
`test_python_parity.py` and `test_parity.py`: 23 passed. glade's `wire-rs` `cargo test`: 11 passed.
Only existing suites were run, so every other result below is READ.

### 5.2 Rust: taut's fail-closed runtime and generator

| Finding | Where |
|---|---|
| **Unbounded recursion.** `dec` calls itself once per level of array or map, with no counter. A deep enough input overflows the stack, which aborts the process: it is not a panic, and no `catch_unwind` can stop it. The module's claim that "decode never panics on any byte input" holds only because an overflow is not a panic. There is no `TooDeep` variant. | `taut/src/taut/gen/runtime/cbor_fail_closed.rs:558`, `:568-569`; the claim `:19-24`; the enum `:40-82` |
| A map's value is decoded before its key is checked. So `a2010001` gives `Truncated` where Python and TS give `DuplicateMapKey` (M4-M6). | `cbor_fail_closed.rs:568-580` |
| The duplicate-key check compares each key with every earlier key, so its cost grows with the square of the map's size. Python uses a dict and TS a `Set`. | `cbor_fail_closed.rs:578`; `taut/src/taut/wire/cbor.py:228`; `taut/src/taut/gen/runtime/typescript/cbor.ts:389-391` |
| `n as usize` truncates a length of 2^32 or more on a 32-bit target such as wasm32, so a 32-bit build can accept input that a 64-bit build calls `Truncated`. | `cbor_fail_closed.rs:543`, `:549` |
| An absent optional field is `MissingKey`, because every field is read with `try_get`. This contradicts `compat.py:11`, and Python and TS both return null. | `taut/src/taut/gen/rust.py:276-278`; `cbor_fail_closed.rs:211-222` |
| A message with no fields never looks at its input, so it accepts any item (M12). | `taut/src/taut/gen/rust.py:268-289`; for example `taut-shape-rs/crates/taut-shape/src/generated.rs:273-276` |
| A `map<K,V>` field is collected into a `BTreeMap`, so a repeated key silently keeps the last entry (M13). Each entry decodes key 1 before checking that key 2 exists (M14). | `taut/src/taut/gen/rust.py:142-145` |
| The shipped runtime still has functions that panic: `decode`, the infallible accessors, and `ext.rs` when the host is not a map. | `cbor_fail_closed.rs:141-193`, `:457-462`; `taut/src/taut/gen/runtime/ext.rs:18-23` |
| The corpus emitter still writes the legacy codec, whatever D1 says, and glade's build copies it into `glade/wire-rs/src` along with the legacy `cbor.rs`. Removing `--legacy-codec` at v0.10.0 does not reach this path. | `taut/src/taut/gen/rust.py:299-305`; `taut/src/taut/corpus/glade_build.py:31-32`, `:114-123` |

`glade/wire-rs/src/cbor.rs` is byte-identical to taut's legacy `taut/src/taut/gen/runtime/cbor.rs`
(MEASURED by `diff`): it indexes past the end (`cbor.rs:295`, `:276-287`), unwraps UTF-8 (`:317`),
asserts on trailing bytes (`:269`), panics on unsupported items (`:290`, `:339`, `:364`, `:366`),
wraps u64 into `i64` (`:302`, `:306`) and recurses without a bound (`:325`, `:335-336`); its
generated `from_wire` panics too (`glade/wire-rs/src/generated.rs:57`, `:77`, `:109`, `:135`).

### 5.3 Python and TypeScript (and JS)

| Finding | Where |
|---|---|
| **Python recursion is unbounded.** At about 1,000 levels a `RecursionError` escapes, and it is not a `DecodeError`. | `taut/src/taut/wire/cbor.py:216`, `:223`, `:230` |
| Python's extension helpers leak `TypeError` or `ValueError` when the host is not a map, and read the extension leniently (`strict=False`). | `taut/src/taut/ext.py:35-38`; `taut/src/taut/wire/codec.py:39` |
| **TypeScript recursion is unbounded.** A `RangeError` escapes once V8 runs out of stack. | `taut/src/taut/gen/runtime/typescript/cbor.ts:373`, `:384`, `:392` |
| TS calls a length or count above 2^53 − 1 `IntOverflow` (M1, M2); Rust and Python say `Truncated`. | `…/typescript/cbor.ts:333-337` |
| TS refuses a raw map key above 2^53 − 1 as `NonIntegerMapKey` (M8). Rust, Python and JS accept it; JS keeps it as a `bigint`. | `…/typescript/cbor.ts:387`; `taut/src/taut/gen/runtime/cbor.js:172-175` |
| TS says `WrongType{str}` and `WrongType{list}` where Rust and Python say `text` and `array` (M9, M10). | `…/typescript/codec.ts:113`, `:128`, `:131`; `cbor_fail_closed.rs:244`, `:265`; `codec.py:106`, `:131` |
| TS's extension helper throws a plain `Error` when the host is not a map. | `…/typescript/ext.ts:17-22` |
| JS, the fourth gated codec: its recursion is unbounded; it checks additional info ≥ 28 before the major type (M7); it says `IntOverflow` for long lengths and `str` for text; an absent optional field is `MissingKey`; in a `map<K,V>` the last entry wins. | `cbor.js:444`, `:455`, `:462`, `:415`, `:388-391`, `:121`; `taut/src/taut/gen/js.py:90`, `:41-43` |

taut-shape-ts's `cbor.ts` and `codec.ts` match taut's line for line below their provenance headers
(MEASURED by `diff`), so every TS finding holds there too.

### 5.4 The gate

| Finding | Where |
|---|---|
| **A row that never reports is not counted as a failure, and the Rust runner's exit status is ignored.** A runner killed by a stack overflow at B9 would print only the rows before it, and the target could still read GREEN. The TS and JS targets count as unavailable only when they print nothing at all. | `taut/src/taut/corpus/parity.py:239-240`, `:457-470`, `:496-497`, `:601`, `:621` |
| Only the tag is compared, so payload drift (M9, M10) passes. The TS check accepts any object whose `.tag` matches. | `parity.py:302-305`, `:419`, `:540`, `:578` |
| The gate replays taut's sources, not the copies clients ship. taut-shape-rs's `cbor.rs`, vendored at taut `70e17b7`, lacks `DuplicateMapKey`, `NonCanonicalInt` and `NegativeMapKey`, and nothing flagged it. | `taut-shape-rs/crates/taut-shape/src/cbor.rs:13-15`, `:65-97`, `:563-579`; `RustFailClosed.md:172-181` |

### 5.5 Clients

| Client | Decoder and findings | Where |
|---|---|---|
| taut-shape (Python oracle) | Uses taut's installed `taut.wire.codec`, so it inherits §5.3. It pins `taut-proto >=0.9.1,<0.10`. | `taut-shape/corpus/gen.py:117-123`; `taut-shape/release/compatibility.v1.json:32` |
| taut-shape-rs | A stale fail-closed copy (§5.4). Its framing allocates whatever u32 length a frame claims, up to 4 GiB. | `taut-shape-rs/crates/taut-shape-tool/src/framing.rs:85-92` |
| taut-shape-ts | A current copy (§5.3). A length of 2^31 or more reads as negative through `<< 24` and is refused, where Rust would allocate it; there is no lower cap. Any throw, including a `RangeError`, becomes a `FrameError`. | `taut-shape-ts/src/framing.ts:153-156`, `:90-94` |
| glade node | The legacy codec behind two hand-written guards: `checked` for enum values and `wellformed` for depth 32, truncation and the CBOR subset. After them, `from_cbor` still panics on a missing field or a wrong type, and, in the plan's words, "a panicking session leaks its connection until taut's checked decodes (ruled) land". A third decoder, `envelope::parse`, is bounded at depth 2. | `glade/node/src/frame.rs:86-108`; `glade/wire-rs/src/checked.rs:33-58`; `glade/wire-rs/src/wellformed.rs:64-156`; `dev-docs/GladeFirstSlicePlan.md:1010`; `glade/node/src/envelope.rs:305-345` |
| glade client-rs | `dispatch` uses the raw legacy decode: `from_wire` that panics, `cbor::decode` with unbounded recursion, and `from_cbor` that panics. Its websocket allocates whatever 64-bit length a frame claims. | `glade/client-rs/src/client.rs:117-199` (`:121`, `:122`); `glade/client-rs/src/ws.rs:83-92` |
| glade client-ts | **Its own early copy** of taut's TS runtime, `glade/client-ts/src/taut/cbor.ts`: 143 lines from 2026-06-13, before the fail-closed, `bigint` and float work. It throws plain `Error`s and reads past the end as `undefined`. It decodes invalid UTF-8 to U+FFFD, takes any map key, keeps the last duplicate, loses 8-byte ints above 2^53, has no floats, and recurses without bound. Its `codec.ts` passes scalars through unchecked and reads missing fields as null. `onMessage` catches every throw, so it does not crash. | `cbor.ts:88`, `:92`, `:107`, `:113`, `:123-125`, `:86`, `:130-136`; `glade/client-ts/src/taut/codec.ts:45-46`, `:67-68`; `glade/client-ts/src/client.ts:129-138` |

## 6. The contract change and versioning

**CD-V1 (PROPOSED): taut v0.10.0.** This is the next minor release, which already removes
`--legacy-codec` and the legacy runtime template (`RustFailClosed.md:3-9`;
`taut/src/taut/cli.py:157-161`). Before 1.0 a minor release may break things, and this one does: the
new Rust variants break exhaustive matches, the bound refuses input that v0.9 accepted, and the TS
payload words change. There is no opt-out and no deprecation window. The owner's words ("taut has only
a few clients") allow this, and a depth bound requires it, since an opt-out would reopen the stack
overflow. The parity contract becomes `taut-codec-parity/i64/v1`, and the decision is recorded as D26.

**CD-V2 (PROPOSED): what changes for generated code.** **Rust:** every `from_cbor` first requires
a map; an absent optional field is `None`; a `map<K,V>` field refuses a repeated key and checks each
entry for keys 1 and 2 first. The vendored `cbor.rs` gains `MAX_DEPTH`, the two tags, `tag()` and
`try_decode_max`, reads the key before the value, converts lengths with `usize::try_from` and keeps
duplicate keys in a set. The legacy path goes entirely (`--legacy-codec`, `fail_closed=False`, the
legacy `cbor.rs` template, `decode()` and the accessors that panic); `ext.rs` becomes fallible
(`ext_get -> Result<Option<Cbor>, DecodeError>`); `rust.py`'s corpus emitter and `glade_build`
switch to the fail-closed path. **JS:** the same three `fromCbor` changes, and `cbor.js` as §5.3
lists. **TypeScript and Python:** no generated change; their runtimes change (`cbor.ts`, `codec.ts`,
`ext.ts`; `wire/cbor.py`, `codec.py`, `ext.py`). Encode is untouched, so every golden corpus
(`glade.golden.json`, `log.v0.json` and the rest) stays byte-identical.

**CD-V3 (PROPOSED): how the clients adopt it.** A consumer pinned below v0.10.0 is unaffected until
it regenerates, as with D1. The shape packages move as one 0.10 release train, which the release
check already enforces (the protocol package's major.minor must equal the train's,
`taut-shape/release/check_compatibility.py:131`). **taut-shape** raises its pin to
`taut-proto >=0.10.0,<0.11` and reruns its corpus generators with `--check`, expecting no change.
**taut-shape-rs** re-vendors `cbor.rs`, every `generated*.rs` and `parity_vectors.rs` from the tag
(closing the drift since `70e17b7`), replays the rows in `cargo test` and caps its frame length.
**taut-shape-ts** re-copies `cbor.ts` and `codec.ts` (they match today's source, so the diff is
exactly v0.10.0's) and the rows as JSON; `framing.ts` reads the length unsigned (`>>> 0`), caps it
and catches only `DecodeError`. **Other projects generating Rust from taut** (razel; gwz, per
`RustFailClosed.md:220-234`) meet the change when they regenerate; the compiler lists every site.

## 7. glade's move off the legacy codec

**CD-G1 (PROPOSED): wire-rs.** `glade_build` regenerates `generated.rs` and `cbor.rs` from
v0.10.0's fail-closed path, each header naming the taut tag it came from (no regeneration command is
recorded today: `TautCodecParityPlan.md:24-26`). `from_wire`, `from_cbor` and `try_decode` return
`Result`; the tests' `cbor::decode` calls become `try_decode(..).unwrap()`
(`glade/wire-rs/src/lib.rs:39`, `:50`, `:59`). `checked.rs` is deleted: the generated `from_wire`
refuses what it refused, and its hand-kept ranges (`checked.rs:33-58`) stop duplicating the IR.

**CD-G2 (PROPOSED): `wellformed` goes; its tests stay.** Once taut's decode is bounded and
fail-closed, the pre-check adds nothing and costs something: every frame is walked twice; its
`Malformed` tags differ from `DecodeError`'s, so glade would name the same bytes' faults differently
from taut's other clients; it refuses some inputs with another tag (M3: it checks a count against the
remaining bytes before reading items, `wellformed.rs:127-129`); and it accepts inputs the codec
refuses (non-canonical ints, negative or repeated keys, ints beyond `i64`). Its three F15 tests
(`wellformed.rs:187-281`) are pointed at `cbor::try_decode`: 100,000 and 33 deep are `TooDeep` and
32 deep decodes; every proper prefix of every golden vector, and every length or count of 2^64 − 1,
is `Truncated`; each item outside the subset gets its `DecodeError` tag. The F15b source guard
(`glade/node/src/envelope.rs:849-882`) stays.

**CD-G3 (PROPOSED): the order.**

1. **taut first**, in separable steps: the gate fixes of §5.4, with the v1 rows as lead rows and the
   Wave-1 targets allowlisted ("checked-decode v1 rows"); Rust, Python, and TS with JS, each to GREEN
   and off the allowlist; then v0.10.0, tagged by the owner.
2. **glade's node step** (`dev-docs/GladeFirstSlicePlan.md:1099`): regenerate `wire-rs` at v0.10.0
   (CD-G1). `Frame::from_bytes` becomes `FrameType::from_wire(tag)?`, `cbor::try_decode(rest)?` and
   `X::from_cbor(&c)?` (`glade/node/src/frame.rs:86-108`); every F15b site calls `try_decode` in
   place of `wellformed::decode` (`envelope.rs:152-158`, `:186-188` and the sites
   `dev-docs/GladeFirstSlicePlan.md:1010` lists); `wellformed.rs` and `checked.rs` go in the same
   commit. A badly structured body is then refused like any bad frame, so a session no longer panics
   and leaks its connection. Before the desk's node binary is replaced, a dry run decodes every
   stored record and journal op with the new codec and counts refusals: strict-canonical decode may
   refuse stored bytes the legacy codec took, which F15b's rule would then skip.
3. **client-rs's checked `dispatch`**, in the same step (CD-G4). `MAX_FRAME_BYTES` and `frame_len`
   move from `glade/node/src/frame.rs:19-33` into glade-wire, so client-rs's websocket checks a
   claimed length before allocating (`glade/client-rs/src/ws.rs:83-92`); client-rs may not use node
   internals (`glade/client-rs/Cargo.toml:5`, P00-a).
4. **Later, separately:** client-ts re-vendors taut's TS runtime (its `int` fields become `bigint`,
   rippling through session, fold and store); `envelope::parse` gives way to `try_decode`.

**CD-G4 (PROPOSED): what client-rs's checked `dispatch` becomes.** It decodes the whole frame into a
typed value before touching any state. A refused frame is handled as client-ts handles one
(`glade/client-ts/src/client.ts:510-514`): every waiting subscribe fails with the error's text,
since the refused frame may have been its ack, and the read loop carries on. An empty frame, dropped
silently today (`client.rs:118-120`), becomes `Truncated` and is reported like any other.

```rust
async fn dispatch(self: &Arc<Self>, bytes: &[u8]) {
    match Inbound::decode(bytes) {
        Ok(inbound) => self.take(inbound).await, // today's arms (client.rs:123-198), typed
        Err(why) => self.not_taken(why).await,  // as client-ts's notTaken
    }
}

fn decode(bytes: &[u8]) -> Result<Inbound, DecodeError> { // in `impl Inbound`
    let (&tag, body) = bytes.split_first().ok_or(DecodeError::Truncated)?;
    let ty = FrameType::from_wire(i64::from(tag))?;
    let c = cbor::try_decode(body)?;
    Ok(match ty {
        FrameType::Ops => Inbound::Ops(Ops::from_cbor(&c)?.ops),
        FrameType::Heads => Inbound::Heads(Heads::from_cbor(&c)?),
        FrameType::Error => Inbound::Error(Error::from_cbor(&c)?),
        FrameType::Welcome => Inbound::Welcome(Welcome::from_cbor(&c)?),
        FrameType::ExchangeReq => Inbound::ExchangeReq(ExchangeReq::from_cbor(&c)?),
        FrameType::ExchangeRes => Inbound::ExchangeRes(ExchangeRes::from_cbor(&c)?),
        _ => Inbound::Ignored, // channel frames, as today
    })
}
```

## 8. Gaps and questions for the owner

**Named gaps** (not solved here):

- **G1 Wave 2.** cpp, swift, go, kotlin and java stay allowlisted and recurse without a bound until
  Phase 4 replays the rows (`TautCodecParityPlan.md:162-170`).
- **G2 The D2 law is not fully enforced.** Every decoder accepts raw map keys out of order,
  `map<K,V>` entries out of order (D24 requires them sorted) and floats wider than needed, so a
  successful decode does not yet guarantee a byte-identical re-encode (`TautCodecParityPlan.md:57`).
  All languages agree here, so it is not a parity bug.
- **G3 Amplification.** Each input byte can become one decoded item of tens of bytes (a Rust `Cbor`,
  `cbor_fail_closed.rs:125-134`, is 32), so a 16 MiB frame can decode to hundreds of MiB; a
  carrier's cap bounds it, nothing bounds the number of items.
- **G4 Outside this workspace**, gwz's schemas and razel's data (not its schema) are unchecked against 32.
- **G5 Thin measurement.** Only the gate and four existing suites ran; §5's READ behaviours are to be
  confirmed by the lead rows.

**Questions.** Each lists its alternatives; (a) is recommended.

1. **Depth bound.** (a) 32, a contract constant no call can change. (b) 32 with a per-call lower
   limit: `envelope::parse` could use the codec, but the same bytes would decode differently by
   caller. (c) 64: more headroom, with no known need.
2. **Size.** (a) Carriers own the cap; taut adds `TooLarge` and an opt-in `max_bytes`. (b) A
   taut-wide default, say 16 MiB, for razel, taut-shape and glade alike. (c) No size in taut; "over
   size" is each carrier's own error.
3. **TypeScript form.** (a) Throw `DecodeError` and nothing else. (b) Return `{ ok, value | error }`.
   (c) Both.
4. **Absent optional field.** (a) Null everywhere, as `compat.py:11` requires; Rust and JS change.
   (b) `MissingKey` everywhere, which makes adding an optional field breaking and changes `compat.py`.
5. **Packaging.** (a) All in v0.10.0 with the legacy removal, no opt-out. (b) v0.10.0 removes legacy,
   v0.11.0 adds the bound: a second breaking regeneration for every client. (c) A flag first, which
   leaves the overflow open while it exists.
6. **`wellformed`.** (a) Delete it in glade's node step, keeping its tests. (b) Keep it one release as
   a pre-check: every frame walked twice, two error vocabularies.
7. **G2.** (a) A D2 follow-up after v0.10.0 with its own lead rows; a tag such as `UnsortedMapKeys`
   would also make the duplicate check one comparison per key. (b) Fold it into v0.10.0.
8. **client-ts.** (a) Its own step after the node step. (b) Inside the node step, which the `bigint`
   change would enlarge.
