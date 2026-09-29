# Checked decode: one error and schema-declared bounds in every taut language

**rev8, 2026-09-30:** the parity pass ("just bring all languages to parity";
[TautCodecParityPlan.md](TautCodecParityPlan.md) §8) built, in all nine codecs, the parts of this
note that do not wait on the bounds:
- CD-E5's order of checks and CD-E6's payload words;
- rows M1-M17, with M1 named `bytes-length-over-2^53`, since its bytes are a byte string;
- `optional=MISSING_OK` in every generator;
- a gate that compares payloads (CD-C4), fails a row that never reports, and requires a row that
  decodes to re-encode to its expected bytes.

`tautc parity` gates all nine with an empty allowlist (taut `2bd1f85` to `ca48911`). The bounds
(§3, rows B1-B30) and the rest stay proposed. The pass also found questions 9 and 10. Changed: the
status, the opt-in exception, CD-C1, §4.4's M1 and §8.

**rev7, 2026-09-30:** all nine languages in v0.10.0 ("fix all languages in v0.10.0"; TautOptions.md
question 2). The codec parity plan's Phase 4, which makes cpp, swift, go, kotlin and java fail-closed,
joins this release, and so do the bounds and `MISSING_OK` for them. Changed: the title, §0, CD-V2 and
G1.

**rev6, 2026-09-28:** nothing named `missing_ok` is supported ("no missing_ok support - transition
all use to optional=MISSING_OK"; [TautOptions.md](TautOptions.md) question 9, ruled). The design text
says `optional=MISSING_OK` throughout; `missing_ok` remains only where the note describes `bcf98b6`'s
code. Changed: CD-E5, the opt-in exception, CD-C1, CD-V1, CD-V2, G2 and question 4.

**rev5, 2026-09-28:** presence is one keyword with three values, `optional=` `False`, `True` or
`MISSING_OK` ("switch the notes to optional=MISSING_OK"; [TautOptions.md](TautOptions.md) OPT-M2),
in place of rev4's field option. Changed: §0, the opt-in exception, CD-C1, CD-V2 and question 4.

**rev4, 2026-09-28:** question 4 is ruled (a) ("ok"), and `missing_ok` becomes the first field
option, `option.missing_ok(True)` ("add option field"; [TautOptions.md](TautOptions.md) OPT-D7).
Changed: §0, the opt-in exception, CD-C1, CD-V2 and question 4.

**rev3, 2026-09-28:** rebased onto taut's GitHub commits `3b84365`, `733e8a7` and `bcf98b6`
(2026-09-19 to 22), which this checkout lacked when rev1 and rev2 were written. `bcf98b6` adds the
field keyword `missing_ok`, an optional field whose absent key reads as null; makes Python's strict
decode refuse any other absent optional key; and makes a message with no fields require a map in
Rust. Changed: the evidence pins, §1 row 3, CD-E5, CD-C1, M11, M12, the new M16 and M17,
§5.2-5.3's absent-field and empty-message findings, G2, CD-V1, CD-V2 and question 4. Every taut
line is re-pinned to `bcf98b6`.

**rev2, 2026-09-28:** depth from the `max_depth` option, [`TautOptions.md`](TautOptions.md); size
from the `max_encoded_len` option; the owner's rulings on questions 4 and 6 recorded. Changed: the
title, §0, §1, CD-E5, CD-B1-B5, CD-C1, CD-C2, CD-C4, §4.4, the absent-field findings in §5.2-5.3,
CD-V2, CD-V3, CD-G1-G4, G1, G3, G4 and questions 1, 2, 4 and 6.

**Status:** DESIGN, proposed 2026-09-28; rev2 records the owner's rulings of the same day (§0) and
awaits the rest. rev8: the parity pass built CD-E5, CD-E6, rows M1-M17 and `optional=MISSING_OK`
everywhere (above); the rest is still a document only. Once ruled, it
becomes decision **D26** in [TautDecisions.md](TautDecisions.md) (D25 is the last) and parity
contract `taut-codec-parity/i64/v1`.

**Builds on** [RustFailClosed.md](RustFailClosed.md) (fail-closed Rust is the default since v0.8.0),
[TautCodecParityPlan.md](TautCodecParityPlan.md) (D1, D2 ratified 2026-07-07; §2b's tag vocabulary)
and, from rev2, [TautOptions.md](TautOptions.md) (the `max_depth` and `max_encoded_len` options).

**Evidence.** Paths are from the glade-wz root; lines are at taut `bcf98b6` (v0.9.1 + 6; rev3
re-pinned them from `7a5f616`, whose code rev1 and rev2 read), glade `2a3c6f8`, taut-shape `9a75209`,
taut-shape-rs `b442d07` (its rebase onto GitHub's `df13036`, a version bump, moved no cited line),
taut-shape-ts `137f843`. **OWNER** marks a ruling, **PROPOSED** this design, **MEASURED** a run on
2026-09-28, **READ** code read but not run.

## 0. The ruling this note implements

> "we are allowed to change the taut contract - (return error instead of panic) the question becomes
> consistency across languages (py,ts,rs) - taut has only a few clients, especially taut-shape*"
> (the owner, 2026-09-28)

**OWNER, 2026-09-28:** one typed decode-depth error in Rust, TypeScript and Python; a shared corpus
of bad inputs; an audit of each language's parity; and glade's move to the fail-closed codec
(`dev-docs/GladeFirstSlicePlan.md:945`, item 10). glade's node step "taut's checked decodes and
client-rs's checked `dispatch`" waits on this note (`dev-docs/GladeFirstSlicePlan.md:1099`).

**OWNER, 2026-09-28 (rev2):** the bounds are declared with the schema, as options
([TautOptions.md](TautOptions.md)): `max_depth` (default 32, ceiling 128) and, for size,
`max_encoded_len` ("I suppose we can use this mechanism for size"; "ok with max_size"; the name:
"max_encoded_len? - bytes no"). An absent optional key stays `MissingKey` ("ok with the MissingKey
adoption", question 4). glade's node step drops `checked.rs` ("drop checked.rs"), and
`wellformed.rs` with it, keeping their tests (question 6).

**OWNER, 2026-09-28 (rev4):** question 4 (a) ("ok"). Adding an optional field is compatible only when
it is `missing_ok`, and JS and TypeScript implement `missing_ok` in v0.10.0. `missing_ok` becomes an
option ("add option field"): a field-level wire option, widening, so turning it on is compatible and
turning it off breaking (TautOptions.md OPT-D7, OPT-K1).

**OWNER, 2026-09-28 (rev5):** presence is one keyword instead ("switch the notes to
optional=MISSING_OK"): `optional=` takes `False`, `True` or `MISSING_OK`, replacing rev4's field
option (TautOptions.md OPT-M2). Question 4's ruling stands in those terms: adding an optional field
is compatible only at `MISSING_OK`.

**OWNER, 2026-09-30 (rev7):** "all the generators need to support the same set of features" and
"fix all languages in v0.10.0". Every language this note covers now includes the five Wave-2 targets.

The property this note makes precise: **for any input bytes, every decode entry point returns either
a value or a `DecodeError`. It never panics, aborts, runs out of stack or throws anything else, and
Rust, TypeScript and Python give the same tag and payload for the same bytes decoded from the same
root, whose schema sets the bounds (CD-B3, CD-B4).** The scope is the four
Wave-1 codecs that `tautc parity` gates: rust, python, typescript and js. The Wave-2 codecs stay
allowlisted (§8, G1).

## 1. The recommendations in brief

| # | Topic | Recommendation (PROPOSED) |
|---|---|---|
| 1 | Error | Keep the one `DecodeError` each runtime already has and add two tags, `TooDeep{limit}` and `TooLarge{len, limit}`. Rust returns a `Result`, TypeScript throws and Python raises. One fixed order of checks decides which tag is reported. |
| 2 | Bounds | Both are schema options (TautOptions.md), resolved per decode call from its root, so every reader of a root applies the same bounds and no typed call can change them. `max_depth`: default 32, ceiling 128; at the default, 32 nested arrays or maps decode and the 33rd is `TooDeep`. `max_encoded_len`: no default; where declared, carriers refuse a longer frame before allocating and decode raises `TooLarge`. |
| 3 | Corpus | A new `taut/corpus/parity/bounds.vectors.json` (30 rows, each carrying the bounds it is decoded under) and 17 new rows in `malformed.vectors.json`. The gate and every client replay them, each client against the runtime copy it ships. |
| 4 | Audit | No runtime bounds depth. On deep input Rust overflows its stack (an abort), Python raises `RecursionError` and TypeScript `RangeError`. There are also ten smaller divergences (M1-M14), and a gate that can report GREEN for rows that never ran. |
| 5 | Version | taut **v0.10.0**, the release that already removes `--legacy-codec`. There is no opt-out of the bound. Clients adopt through a 0.10 shape release train. |
| 6 | glade | Regenerate `wire-rs` from v0.10.0's fail-closed path; delete `checked.rs` and `wellformed.rs` but keep their tests (ruled); node and client-rs call the fallible API; client-rs's carrier gets `frame_len`, whose limit comes from glade's schema. client-ts moves later. |

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

1. With a length bound in effect (the root's effective `max_encoded_len`, or a raw call's), input
   longer than it is `TooLarge`, before any byte is read.
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
   fields. Fields are checked in IR order: any field absent, required or optional, is `MissingKey`,
   except a field with `optional=MISSING_OK`, which is null (rev3); an optional field present as null
   is null; a wrong CBOR type is `WrongType`; an unknown enum value is `UnknownEnum`. A `map<K,V>`
   entry checks for keys 1 and 2 before decoding either; a repeated key is `DuplicateMapKey`.

**An absent optional field is `MissingKey` (OWNER, 2026-09-28, reversing rev1).** The rule settled
with the codec parity plan, which replaced the lenient model first settled in TautModules.md §2 and
D3, where even a missing required field decoded to null (`TautModules.md:85-86`). D1 and D2 were
ratified 2026-07-07 (`TautCodecParityPlan.md:48-58`), and D2's law is that `decode(bytes)` ok ⇒
`encode(decode(bytes)) == bytes`. The canonical encoder always writes an optional field, as `null`
when unset (`taut/docs/Reference.md:84`), so a map without the key is bytes no conforming writer
emits, and accepting it would break the law. The plan counts TypeScript's and JavaScript's
missing→`null` as failing open (`TautCodecParityPlan.md:77`), its Step 2.1 makes Python's missing a
`MissingKey` (`:144-146`), and its review states the split: absent is `MissingKey`, present null is
null (`TautCodecParityPlan-Review25.md:118`). So Rust and JS are right today, Python's strict decode
has been since `bcf98b6` (`taut/src/taut/wire/codec.py:157-160`), and TypeScript changes in v0.10.0
(M11, M15).

**The opt-in exception (rev3, from `bcf98b6`).** `optional=MISSING_OK` (rev5; TautOptions.md OPT-M2),
which `bcf98b6` spells `optional=True, missing_ok=True` until that spelling goes (rev6), reads an
absent key as null as well as a present null. It still refuses a present value of the wrong type and
a message that is not a map (`taut/src/taut/gen/rust.py:287-289`; `cbor_fail_closed.rs:242-255`;
`codec.py:158`). `validate` requires `optional=True` with the keyword today
(`taut/src/taut/ir/validate.py:63-64`). The encoder is unchanged and still writes the key, so for
such a field D2's law deliberately does not hold: a message read without the key re-encodes with it,
as null. Only Python and Rust implemented it at `bcf98b6`; `scaffold.emit` refused every other
target for a schema that used it (`scaffold.py:624-636`), and TypeScript's IR-driven codec ignored
it, reading every absent optional key as null. rev8: all nine implement it, and `scaffold.emit` no
longer refuses it.
What the rule and the exception mean for `compat.py:11` is question 4.

**CD-E6 (PROPOSED): payload words.** `WrongType.expected` is one of `int`, `float`, `bytes`,
`text`, `bool`, `array` or `map` in every language; Rust and Python already use these words, while
TypeScript and JS say `str` and `list` (§5.3). Display text is not part of the contract; tag and
payload are.

## 3. The bounds

**CD-B1 (PROPOSED, rev2): depth.** A decode call's depth bound, n, is its root's effective
`max_depth` (CD-B3): 32 unless the schema declares another, never above 128. An array or map has depth
one more than the number of arrays and maps around it, so a top-level container has depth 1. A
container at depth n + 1 is refused with `TooDeep{limit: n}`, whether or not it is empty. Ints,
strings, bools, null and floats add no depth. So at the default 32 nested containers decode, a scalar
inside the 32nd decodes, and the 33rd container fails. The default is glade's F15 bound exactly
(`glade/wire-rs/src/wellformed.rs:25`, `:122-124`, tested at `:187-196`), and glade's schema declares
no `max_depth`, so on depth alone glade accepts and refuses the same inputs it does today.

Why a default of 32: this workspace's schemas nest at most six deep (glade five,
`glade/wire-rs/src/wellformed.rs:19-24`; taut-shape's crdt read response six,
`taut-shape/ir/shape_crdt.taut.py:48-80`; razel three, `taut/ir/razel.taut.py:91-93`), leaving 26
levels for fields a later version adds and a reader keeps as residual (D9). Why a ceiling of 128: it
is an eighth of the smallest limits found here, Python's default recursion limit of 1,000 and the
~1,000 levels at which a debug glade build's 2 MiB worker stack overflowed
(`dev-docs/GladeFirstSlicePlan.md:994`), so no runtime is near its limit at any legal bound.

**CD-B2 (PROPOSED): where the check runs.** Once a container's head (initial byte and argument) is
complete, and before its first item. So a torn head is `Truncated`, and a complete head at depth
n + 1 is `TooDeep` even if its items are missing. The bound applies per decode call, from that call's
root (CD-B3); a message nested inside does not change it (TautOptions.md OPT-D4), and a `bytes` field
that carries CBOR, such as glade's `Op.payload`, is decoded by its own call with its own root's
bound. Depth counts from the top-level item, unknown fields included. The schema stage recurses no
deeper than the raw decode did, so it needs no second counter.

**CD-B3 (PROPOSED, rev2): the depth bound is the schema's `max_depth` option.** rev1 made
`MAX_DEPTH = 32` a contract constant; on the owner's direction the bound is declared with the schema
instead (TautOptions.md §0, OPT-D5):

- **Per root.** `max_depth` is a wire option at file and message level. A decode call applies its
  root's effective value: the root message's option, else the file's, else 32. `tautc` resolves it
  once (TautOptions.md OPT-D3), so every reader of one root applies the same number in every
  language.
- **Default and ceiling.** Each runtime exports `DEFAULT_MAX_DEPTH = 32` and
  `MAX_DEPTH_CEILING = 128`; the corpus header records both and every harness checks they are equal
  (CD-C4). The ceiling is a constant, not an option: `tautc` refuses a declared value above it, so no
  schema can reopen the overflow, and an effective value below its root's non-recursive nesting,
  which no conforming reader could decode. It SHOULD warn about a recursive message (a tree) that
  declares no bound.
- **Typed decode** takes no depth argument, so no call can raise or lower its root's bound. Python's
  `codec.decode(schema, message, data)` and TypeScript's `decode(schema, message, data)` read it from
  the schema (`taut/src/taut/wire/codec.py:30-31`; `taut/src/taut/gen/runtime/typescript/codec.ts:174`).
  Generated Rust and JS have only `from_cbor` over a decoded tree today
  (`taut/src/taut/gen/rust.py:279`, `taut/src/taut/gen/js.py:83`), so each message gains `MAX_DEPTH`,
  `MAX_ENCODED_LEN` and a `decode` from bytes that applies both.
- **Raw decode** knows no schema. It applies 32, or the depth its caller passes, capped at 128, and
  `TooDeep.limit` names the bound applied. Rust adds `try_decode_with(bytes, max_depth,
  max_encoded_len)` beside `try_decode` and `try_decode_max`, which keep the default depth; Python
  `loads(data, *, max_depth=32, max_encoded_len=None)`; TypeScript and JS
  `decode(data, { maxDepth, maxEncodedLen })`. The argument serves generated code, the runtime codecs
  and schema-blind carriers; a typed reader never passes one (question 1).
- glade's depth-2 `envelope::parse` (`glade/node/src/envelope.rs:305-345`) is a shape check and stays
  one.

**CD-B4 (OWNER 2026-09-28 for the option; PROPOSED for the rest): size is the `max_encoded_len`
option, applied first by the carrier.** On the owner's ruling, size uses the same mechanism, named
for what it limits: the encoded input's length, which is not an in-memory size (TautOptions.md
OPT-D6). It is a wire option at file and message level with no default: a schema that declares none
leaves size to its carriers, as rev1 did, since taut cannot pick one number for glade (16 MiB),
taut-shape's stdin framing (u32) and razel's socket. Decode sees bytes only once they are in memory,
so the bound that matters is still the carrier's, on a frame's claimed length before it allocates, as
glade's `frame_len` does (`glade/node/src/frame.rs:19-33`; `glade/node/src/ws.rs:236-243`,
`glade/node/src/peer.rs:62-68`). A carrier now takes that limit from the schema's effective
`max_encoded_len` where one is declared, and from its own setting where none is; one that reads a
length before it knows the root uses the largest effective value among the roots it may receive, none
if any has none. Decode applies the root's effective value too, before it reads a byte, and raises
`TooLarge{len, limit}` above it. Typed decode takes no length argument; the raw decode takes an
opt-in one: Rust `try_decode_max(bytes, max_encoded_len)`, Python `loads(data, *,
max_encoded_len=None)`, TypeScript and JS `decode(data, { maxEncodedLen })`. With neither there is no
length check; a caller with no carrier, such as one reading a record from disk, gets the same
`TooLarge` in every language, from a declared bound or its own argument.

**CD-B5 (PROPOSED): exactly at the bound.** With depth bound n, depth n decodes and n + 1 fails: 32
and 33 at the default, 128 and 129 at the ceiling. Input of exactly `max_encoded_len` decodes and one
byte more fails; a raw call's `max_encoded_len = 0` with empty input is `Truncated`. glade's frame cap
already accepts exactly 16 MiB (`glade/node/src/frame.rs:27`; test `glade/node/src/peer.rs:664-694`).

## 4. The shared corpus

**CD-C1 (PROPOSED): layout.** The new file sits beside the existing files in `taut/corpus/parity/`:

```
allowlist.json           contract id -> taut-codec-parity/i64/v1
gen_vectors.py           also writes bounds.vectors.json (rows written by hand, as today)
int.vectors.json         rows unchanged; contract id bumped
malformed.vectors.json   + 17 rows (§4.4, M1-M17)
bounds.vectors.json      new: 30 depth and length rows (§4.4, B1-B30), each with its bounds;
                         "default_max_depth": 32, "max_depth_ceiling": 128
```

The fixture `taut/ir/parity_int.taut.py` gains three messages for the schema-stage rows:
`OptBox { note: str optional = 1, tags: list<str> = 2 }`; `Empty`, which has no fields; and, from
rev3, `Late`, whose one field is `note=F(1, STR, optional=MISSING_OK)` (rev5). rev8: all three are
in the fixture, and every generator generates `Late`; the fixture also gains `Shapes`, which covers
every legal field shape, with 11 more rows (TautCodecParityPlan.md §8). rev2 adds
six for the bounds rows: `Tree64 { kids: list<Tree64> = 1 }` declaring `option.max_depth(64)`;
`Tree128`, the same declaring 128; `Flat2 { v: list<int> = 1 }` declaring 2, its non-recursive
nesting; `Sized8 { b: bytes = 1 }` declaring `option.max_encoded_len(8)`; and
`Holds64 { t: Tree64 = 1 }` and `HoldsSized8 { s: Sized8 = 1 }`, which declare nothing. Nor does the
file, so those two and every other message resolve to the defaults: depth 32 and no length bound.

**CD-C2 (PROPOSED): row format.** Rows keep today's fields (`name`, `stage`, `bytes`, `expect`,
`why`, `lead`; `taut/corpus/parity/malformed.vectors.json:6-124`). `bytes` may also be a list of
segments, each a hex string or `{"repeat": "<hex>", "count": N}`, so a 100,000-deep row stays one
line. A new `len` gives the expanded length, which a harness checks before decoding, and a new
`limits` carries what a raw row's call passes, `{"max_depth": N, "max_encoded_len": N}`, either one
optional. Every row in `bounds.vectors.json` carries the bounds it is decoded under (TautOptions.md
OPT-P1): `max_depth` always, and `max_encoded_len` when a length bound applies. For a raw row they are
what `limits` passes, the depth capped at 128, else the defaults; for a `from_cbor` row, what the
fixture resolves its message to. A `from_cbor` row decodes through its message's typed entry point
(CD-B3), not through `try_decode` and then `from_cbor` as the gate does today
(`taut/src/taut/corpus/parity.py:385`, `:404`). `expect` is either `{"tag": ..., <payload>}` or, for
a row at a bound that must decode, `{"accept": true}`. New rows enter with `"lead": true`, the gate's existing
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

**CD-C4 (PROPOSED): what every harness checks.** The runtime's `DEFAULT_MAX_DEPTH` and
`MAX_DEPTH_CEILING` equal the header's; before a `from_cbor` row, its message's effective bounds (the
generated constants in Rust and JS, the resolver in Python, the loaded IR's `effective` in
TypeScript) equal the row's; the expanded length equals `len`; the error is the language's `DecodeError` (anything else is "untyped",
a failure); the tag matches; each payload field named in `expect` matches when compared as a string,
except `IntOverflow.value`, which Rust's variant does not carry. A row that never reports counts as a
failure, and a runner that exits non-zero fails its target.

### 4.4 The rows and the expected result for each

"Today" is READ from the code, except the gate's baseline (§5.1); `n×XX` is XX repeated n times. A
raw stage names any bound its call passes ("depth n", "len n"); a `from_cbor` stage gives in brackets
the bound its message resolves to, where the row tests one.

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
| B13 size-at-limit | raw, len 4 | `83010203` | accept | no length bound yet |
| B14 size-over-limit | raw, len 3 | `83010203` | `TooLarge{4, 3}` | no length bound yet |
| B15 size-before-parse | raw, len 3 | `c0c0c0c0` | `TooLarge{4, 3}` | no length bound yet |
| B16 size-empty | raw, len 0 | (empty) | `Truncated` | no length bound yet |
| B17 depth-64-declared | from_cbor Tree64 [64] | 31×`a10181`, `a10180` | accept | — |
| B18 depth-65-declared | from_cbor Tree64 [64] | 32×`a10181`, `a10180` | `TooDeep{64}` | all accept |
| B19 raw-ignores-declared | raw | 31×`a10181`, `a10180` | `TooDeep{32}` | all accept |
| B20 depth-root-decides | from_cbor Holds64 [32] | `a101`, 15×`a10181`, `a10180` | `TooDeep{32}` | all accept |
| B21 depth-2-declared | from_cbor Flat2 [2] | `a1018100` | accept | — |
| B22 depth-3-declared | from_cbor Flat2 [2] | `a1018180` | `TooDeep{2}` | all reach the schema stage |
| B23 depth-128-ceiling | from_cbor Tree128 [128] | 63×`a10181`, `a10180` | accept | — |
| B24 depth-129-ceiling | from_cbor Tree128 [128] | 64×`a10181`, `a10180` | `TooDeep{128}` | all accept |
| B25 raw-depth-128 | raw, depth 128 | 127×`81`, `80` | accept | no depth argument yet |
| B26 raw-depth-129 | raw, depth 128 | 128×`81`, `80` | `TooDeep{128}` | no depth argument yet |
| B27 raw-depth-capped | raw, depth 1000 [128] | 128×`81`, `80` | `TooDeep{128}` | no depth argument yet |
| B28 len-8-declared | from_cbor Sized8 [len 8] | `a101450102030405` | accept | — |
| B29 len-9-declared | from_cbor Sized8 [len 8] | `a10146010203040506` | `TooLarge{9, 8}` | all accept |
| B30 len-root-decides | from_cbor HoldsSized8 [none] | `a101a1014a`, `00010203040506070809` | accept | — |
| M1 bytes-length-over-2^53 | raw | `5b0020000000000000` | `Truncated` | TS, JS `IntOverflow` |
| M2 array-count-u64-max | raw | `9bffffffffffffffff` | `Truncated` | TS, JS `IntOverflow` |
| M3 items-read-in-order | raw | `85c0` | `UnsupportedMajor{6}` | glade `wellformed` says `Truncated` |
| M4 key-first-duplicate | raw | `a2010001` | `DuplicateMapKey{1}` | Rust `Truncated` |
| M5 key-first-text | raw | `a16178` | `NonIntegerMapKey` | Rust `Truncated` |
| M6 key-first-negative | raw | `a120` | `NegativeMapKey{-1}` | Rust `Truncated` |
| M7 major-6-info-28 | raw | `dc` | `UnsupportedMajor{6}` | JS `UnsupportedInfo{28}` |
| M8 map-key-2^53 | raw | `a11b002000000000000000` | accept | TS `NonIntegerMapKey` |
| M9 wrong-type-text | from_cbor OptBox | `a201010280` | `WrongType{text}` | TS, JS `str` |
| M10 wrong-type-array | from_cbor OptBox | `a201f60200` | `WrongType{array}` | TS `list` |
| M11 optional-absent | from_cbor OptBox | `a10280` | `MissingKey{1}` | TS accepts, `note` null; Python did until `bcf98b6` |
| M12 empty-message-not-map | from_cbor Empty | `00` | `WrongType{map}` | JS accepts; Rust did until `bcf98b6` |
| M13 map-field-duplicate | from_cbor IntBox | `a201000282a201050201a201050202` | `DuplicateMapKey{5}` | Rust, JS accept (last entry wins) |
| M14 map-entry-keys-first | from_cbor IntBox | `a201000281a1016178` | `MissingKey{2}` | Rust, JS `WrongType{int}` |
| M15 optional-present-null | from_cbor OptBox | `a201f60280` | accept, `note` null | — |
| M16 missing-ok-absent (rev3) | from_cbor Late | `a0` | accept, `note` null | JS cannot generate `Late` |
| M17 missing-ok-wrong-type (rev3) | from_cbor Late | `a10101` | `WrongType{text}` | TS `str`; JS cannot generate `Late` |

The rows that test each rule: CD-B1, B1-B5 and B8-B10; CD-B2, B6, B7, B11, B12 and B20; CD-B3,
B17-B27; CD-B4, B13-B16 and B28-B30; CD-B5, each pair at a bound and one beyond it (B1-B4, B13-B14,
B17-B18, B21-B26, B28-B29); CD-E5, M1-M8, M11-M17 and B22, where depth is refused before the schema
stage; CD-E6, M9 and M10.

## 5. The parity audit (2026-09-28)

### 5.1 What was measured

`tautc parity`, the Wave-1 gate: GREEN for rust, python, typescript and js on 11 int and 16
malformed rows (rust: 24 pass, 3 type-satisfied); none of the 27 nests anything. taut's `test_cbor.py`,
`test_python_parity.py` and `test_parity.py`: 23 passed. glade's `wire-rs` `cargo test`: 11 passed.
Only existing suites were run, so every other result below is READ.

### 5.2 Rust: taut's fail-closed runtime and generator

| Finding | Where |
|---|---|
| **Unbounded recursion.** `dec` calls itself once per level of array or map, with no counter. A deep enough input overflows the stack, which aborts the process: it is not a panic, and no `catch_unwind` can stop it. The module's claim that "decode never panics on any byte input" holds only because an overflow is not a panic. There is no `TooDeep` variant. | `taut/src/taut/gen/runtime/cbor_fail_closed.rs:591`, `:601-602`; the claim `:19-24`; the enum `:40-82` |
| A map's value is decoded before its key is checked. So `a2010001` gives `Truncated` where Python and TS give `DuplicateMapKey` (M4-M6). | `cbor_fail_closed.rs:601-613` |
| The duplicate-key check compares each key with every earlier key, so its cost grows with the square of the map's size. Python uses a dict and TS a `Set`. | `cbor_fail_closed.rs:611`; `taut/src/taut/wire/cbor.py:228`; `taut/src/taut/gen/runtime/typescript/cbor.ts:389-391` |
| `n as usize` truncates a length of 2^32 or more on a 32-bit target such as wasm32, so a 32-bit build can accept input that a 64-bit build calls `Truncated`. | `cbor_fail_closed.rs:576`, `:582` |
| An absent optional field is `MissingKey`, because it is read with `try_get`. Since `bcf98b6` a `missing_ok` field is read with `try_get_opt`, which returns none for an absent key and still refuses a non-map. rev2 keeps `MissingKey` as the rule (CD-E5); TS, which returns null, is the one that changes (M11). | `taut/src/taut/gen/rust.py:286-292`; `cbor_fail_closed.rs:229-240`, `:242-255` |
| A message with no fields never looked at its input, so it accepted any item (M12). `bcf98b6` makes both emitters check for a map first, the default one with an `assert!`; code generated before it still accepts any item until it is regenerated. | `taut/src/taut/gen/rust.py:250-251`, `:280-281`; still accepting, for example, `taut-shape-rs/crates/taut-shape/src/generated.rs:273-276` |
| A `map<K,V>` field is collected into a `BTreeMap`, so a repeated key silently keeps the last entry (M13). Each entry decodes key 1 before checking that key 2 exists (M14). | `taut/src/taut/gen/rust.py:142-145` |
| The shipped runtime still has functions that panic: `decode`, the infallible accessors, and `ext.rs` when the host is not a map. | `cbor_fail_closed.rs:159-211`, `:490-495`; `taut/src/taut/gen/runtime/ext.rs:18-23` |
| The corpus emitter still writes the legacy codec, whatever D1 says, and glade's build copies it into `glade/wire-rs/src` along with the legacy `cbor.rs`. Removing `--legacy-codec` at v0.10.0 does not reach this path. | `taut/src/taut/gen/rust.py:313-319`; `taut/src/taut/corpus/glade_build.py:31-32`, `:114-123` |

`glade/wire-rs/src/cbor.rs` was byte-identical to taut's legacy `taut/src/taut/gen/runtime/cbor.rs` at
`7a5f616` (MEASURED by `diff`); `bcf98b6` has since added `is_map` and `get_opt` to taut's copy (18
lines, MEASURED), which glade's gains when `glade_build` next runs. glade's copy indexes past the
end (`cbor.rs:295`, `:276-287`), unwraps UTF-8 (`:317`), asserts on trailing bytes (`:269`), panics
on unsupported items (`:290`, `:339`, `:364`, `:366`), wraps u64 into `i64` (`:302`, `:306`) and
recurses without a bound (`:325`, `:335-336`); its generated `from_wire` panics too
(`glade/wire-rs/src/generated.rs:57`, `:77`, `:109`, `:135`).

### 5.3 Python and TypeScript (and JS)

| Finding | Where |
|---|---|
| **Python recursion is unbounded.** At about 1,000 levels a `RecursionError` escapes, and it is not a `DecodeError`. | `taut/src/taut/wire/cbor.py:216`, `:223`, `:230` |
| Python's extension helpers leak `TypeError` or `ValueError` when the host is not a map, and read the extension leniently (`strict=False`). | `taut/src/taut/ext.py:35-38`; `taut/src/taut/wire/codec.py:39` |
| **TypeScript recursion is unbounded.** A `RangeError` escapes once V8 runs out of stack. | `taut/src/taut/gen/runtime/typescript/cbor.ts:373`, `:384`, `:392` |
| TS calls a length or count above 2^53 − 1 `IntOverflow` (M1, M2); Rust and Python say `Truncated`. | `…/typescript/cbor.ts:333-337` |
| TS refuses a raw map key above 2^53 − 1 as `NonIntegerMapKey` (M8). Rust, Python and JS accept it; JS keeps it as a `bigint`. | `…/typescript/cbor.ts:387`; `taut/src/taut/gen/runtime/cbor.js:172-175` |
| TS says `WrongType{str}` and `WrongType{list}` where Rust and Python say `text` and `array` (M9, M10). | `…/typescript/codec.ts:113`, `:128`, `:131`; `cbor_fail_closed.rs:277`, `:298`; `codec.py:106`, `:131` |
| TS's extension helper throws a plain `Error` when the host is not a map. | `…/typescript/ext.ts:17-22` |
| TS decodes an absent optional field to null, where the rule is `MissingKey` (CD-E5, M11), and has no `missing_ok`. Python did too until `bcf98b6`: its strict decode, which `codec.decode` uses, now refuses one unless the field is `missing_ok`, while `decode_struct`, lenient by default, still reads any absent field as null, even a required one. | `…/typescript/codec.ts:151-156`; `taut/src/taut/wire/codec.py:157-160`, `:31`, `:39` |
| JS, the fourth gated codec: its recursion is unbounded; it checks additional info ≥ 28 before the major type (M7); it says `IntOverflow` for long lengths and `str` for text; an absent optional field is `MissingKey`, as the rule requires (M11); in a `map<K,V>` the last entry wins. It has no `missing_ok`, and generating JS for a schema that uses it is refused (M16, M17). | `cbor.js:444`, `:455`, `:462`, `:415`, `:388-391`, `:121`; `taut/src/taut/gen/js.py:90`, `:41-43`; `taut/src/taut/gen/scaffold.py:624-636` |

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
`taut/src/taut/cli.py:160-164`). Before 1.0 a minor release may break things, and this one does: the
new Rust variants break exhaustive matches, the bound refuses input that v0.9 accepted, and the TS
payload words change. There is no opt-out and no deprecation window. The owner's words ("taut has only
a few clients") allow this, and a depth bound requires it, since an opt-out would reopen the stack
overflow. The parity contract becomes `taut-codec-parity/i64/v1`, and the decision is recorded as D26.
taut's `3b84365`-`bcf98b6` are not yet released (the last tag is v0.9.1), so v0.10.0 also carries
`optional=MISSING_OK` (in place of `bcf98b6`'s `missing_ok`), external Rust types and Python's
stricter decode, unless a v0.9 release ships them first.

**CD-V2 (PROPOSED): what changes for generated code.** **Rust:** every message gains `MAX_DEPTH`,
`MAX_ENCODED_LEN` and a `decode` from bytes (CD-B3); every `from_cbor` first requires a map, as it
already does since `bcf98b6`; an absent optional field stays `MissingKey` unless it is
`optional=MISSING_OK`;
a `map<K,V>` field refuses a repeated key and checks each entry for keys 1 and 2 first. The vendored
`cbor.rs` gains `DEFAULT_MAX_DEPTH`, `MAX_DEPTH_CEILING`, the two tags, `tag()`, `try_decode_max`
and `try_decode_with`, reads the key before the value, converts lengths with `usize::try_from` and
keeps duplicate keys in a set. The legacy path goes entirely (`--legacy-codec`, `fail_closed=False`,
the legacy `cbor.rs` template, `decode()` and the accessors that panic); `ext.rs` becomes fallible
(`ext_get -> Result<Option<Cbor>, DecodeError>`); `rust.py`'s corpus emitter and `glade_build`
switch to the fail-closed path. **JS:** the same per-message constants and `decode`, the same
`fromCbor` changes, and `cbor.js` as §5.3 lists; and, as question 4 rules, `MISSING_OK` as Rust
reads it, so that `scaffold.emit` stops refusing JS for it. **TypeScript and Python:** no generated
change; their runtimes change (`cbor.ts`, `codec.ts`, `ext.ts`, and `schema.ts` for IR version 2;
`wire/cbor.py`, `codec.py`, `ext.py`), among other things so that TypeScript refuses an absent
optional field as `MissingKey`, as Python's strict decode already does, and, as question 4 rules,
reads `"optional": "missing_ok"` from the IR (TautOptions.md OPT-M2).
The exported IR becomes version 2, which readers accept beside version 1 (TautOptions.md OPT-I1).
**cpp, swift, go, kotlin and java (rev7):** the codec parity plan's Phase 4 in full. Each gets
fail-closed decode with typed errors carrying §2b's tags, the out-of-`i64` range check, D2 strictness
and `fail_closed=True` as `emit()`'s default. Each also gets both bounds, `MISSING_OK` and a runtime
harness in `tautc parity`, so the allowlist ends empty. C++ keeps its constexpr encode goldens and
adds a runtime binary for the malformed rows (`TautCodecParityPlan.md:162-170`). All five build and
test locally: Apple clang, Swift and Go are on PATH, and Java and Kotlin use Android Studio's JDK 21
and kotlinc 2.2.20. Encode is untouched, so every golden corpus (`glade.golden.json`, `log.v0.json`
and the rest) stays byte-identical.

**CD-V3 (PROPOSED): how the clients adopt it.** A consumer pinned below v0.10.0 is unaffected until
it regenerates, as with D1. The shape packages move as one 0.10 release train, which the release
check already enforces (the protocol package's major.minor must equal the train's,
`taut-shape/release/check_compatibility.py:131`). **taut-shape** raises its pin to
`taut-proto >=0.10.0,<0.11` and reruns its corpus generators with `--check`, expecting no change to
its vectors; any IR JSON it re-exports moves to version 2 (TautOptions.md OPT-I1).
**taut-shape-rs** re-vendors `cbor.rs`, every `generated*.rs` and `parity_vectors.rs` from the tag
(closing the drift since `70e17b7`), replays the rows in `cargo test` and caps its frame length.
**taut-shape-ts** re-copies `cbor.ts` and `codec.ts` (they match today's source, so the diff is
exactly v0.10.0's), its `schema.ts` and the rows as JSON; `framing.ts` reads the length unsigned (`>>> 0`), caps it
and catches only `DecodeError`. **Other projects generating Rust from taut** (razel; gwz, per
`RustFailClosed.md:220-234`) meet the change when they regenerate; the compiler lists every site.

## 7. glade's move off the legacy codec

**CD-G1 (PROPOSED; `checked.rs` OWNER, 2026-09-28): wire-rs.** `glade_build` regenerates `generated.rs` and `cbor.rs` from
v0.10.0's fail-closed path, each header naming the taut tag it came from (no regeneration command is
recorded today: `TautCodecParityPlan.md:24-26`). `from_wire`, `from_cbor` and `try_decode` return
`Result`; the tests' `cbor::decode` calls become `try_decode(..).unwrap()`
(`glade/wire-rs/src/lib.rs:39`, `:50`, `:59`). `checked.rs` is deleted ("drop checked.rs"): the generated `from_wire`
refuses what it refused, and its hand-kept ranges (`checked.rs:33-58`) stop duplicating the IR.

**CD-G2 (OWNER, 2026-09-28): `wellformed` goes with `checked.rs`; its tests stay.** Once taut's
decode is bounded and fail-closed, it checks everything the two check, and the pre-check adds nothing
and costs something: every frame is walked twice; its
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
   internals (`glade/client-rs/Cargo.toml:5`, P00-a). glade's schema declares `max_encoded_len` at
   file level, set so that the frame cap, tag byte included, stays 16 MiB, and `frame_len` takes its
   limit from that declaration (CD-B4), so node and client-rs cannot drift apart.
4. **Later, separately:** client-ts re-vendors taut's TS runtime (its `int` fields become `bigint`,
   rippling through session, fold and store); `envelope::parse` gives way to `try_decode`.

**CD-G4 (PROPOSED): what client-rs's checked `dispatch` becomes.** It decodes the whole frame into a
typed value before touching any state. A refused frame is handled as client-ts handles one
(`glade/client-ts/src/client.ts:510-514`): every waiting subscribe fails with the error's text,
since the refused frame may have been its ack, and the read loop carries on. An empty frame, dropped
silently today (`client.rs:118-120`), becomes `Truncated` and is reported like any other. glade's
schema declares no `max_depth` and only a file-level `max_encoded_len`, which the carrier has already
applied, so every frame type resolves to the same bounds, and the one raw `try_decode` below, at the
default depth, serves every arm; were a message to declare its own bound, its arm would call that
message's `decode` (CD-B3).

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

- **G1 Wave 2.** Closed (rev7): the owner put Phase 4 (`TautCodecParityPlan.md:162-170`) into v0.10.0,
  so cpp, swift, go, kotlin and java replay the rows and leave the allowlist (CD-V2).
- **G2 The D2 law is not fully enforced.** Every decoder accepts raw map keys out of order,
  `map<K,V>` entries out of order (D24 requires them sorted) and floats wider than needed, so a
  successful decode does not yet guarantee a byte-identical re-encode (`TautCodecParityPlan.md:57`).
  All languages agree here, so it is not a parity bug. An absent field with `optional=MISSING_OK` is
  different: a declared exception, not a gap (rev3, CD-E5).
- **G3 Amplification.** Each input byte can become one decoded item of tens of bytes (a Rust `Cbor`,
  `cbor_fail_closed.rs:125-134`, is 32), so a 16 MiB frame can decode to hundreds of MiB; a
  carrier's cap or `max_encoded_len` bounds the input, and nothing bounds the number of items.
- **G4 Outside this workspace**, gwz's schemas meet `tautc`'s nesting check (TautOptions.md OPT-D5)
  only when they regenerate at v0.10.0, and razel's data (not its schema) is unchecked against 32.
- **G5 Thin measurement.** Only the gate and four existing suites ran; §5's READ behaviours are to be
  confirmed by the lead rows.

**Questions.** Each lists its alternatives; (a) is recommended.

1. **Depth bound (rev2).** Its source is settled by the owner: the `max_depth` option, default 32,
   ceiling 128, from each call's root (CD-B3; TautOptions.md's questions cover the option itself).
   Open here is a raw decode's depth argument. (a) Optional and capped at the ceiling, with
   `TooDeep.limit` naming the bound applied; generated code, the runtime codecs and schema-blind
   carriers pass it. (b) Optional, but a value above the ceiling is refused as a caller error, not a
   `DecodeError`. (c) None: a raw decode always applies 32, and generated code reaches its bound
   through a private path.
2. **Size.** RULED (OWNER, 2026-09-28): an option, `max_encoded_len`, which carriers apply before they
   allocate and decode reports as `TooLarge` (CD-B4). Open: its default and ceiling, TautOptions.md
   question 8, where (a) is no default, so a schema that declares none leaves size to its carriers as
   today, and a ceiling of 2^31 − 1 on declared values; (b) a default, such as 16 MiB, for every
   schema; (c) no ceiling.
3. **TypeScript form.** (a) Throw `DecodeError` and nothing else. (b) Return `{ ok, value | error }`.
   (c) Both.
4. **Absent optional field.** RULED (OWNER, 2026-09-28): `MissingKey` everywhere ("ok with the
   MissingKey adoption"; CD-E5). Its consequence, RULED (a) (OWNER, rev4: "ok"), spelled
   `optional=MISSING_OK` from rev5 (TautOptions.md OPT-M2): `taut/src/taut/ir/compat.py:11` still
   classes "add an *optional* field" as compatible, but only one direction is. An old reader keeps
   the new field as an unknown tag, while a new reader refuses every message written before the
   field existed, whether an old peer's or a stored record, such as glade's journals. rev3:
   `bcf98b6` already gives a way out, field by field. Added with `missing_ok=True`, a field reads
   such messages as null, so adding it is compatible both ways. The gate classes turning
   `missing_ok` on as compatible and off as breaking (`compat.py:94-96`), but still classes adding
   any optional field as compatible. (a) The gate classes adding an optional field as compatible
   only at `optional=MISSING_OK`, and as breaking otherwise; JS and TypeScript implement
   `MISSING_OK` in v0.10.0, so every Wave-1 codec reads it alike and the corpus covers it (M16,
   M17). (b) The gate classes adding any field as breaking, so it never promises what decode
   refuses; a schema whose messages are stored adds one with a new major version and a rewrite of
   its stored records, decoded with the old schema and re-encoded with the new. (c) Keep
   "compatible" and document the one direction; the gate then passes changes that strand stored
   data. (d) Make an omitted optional field the canonical form of null, so adding one is compatible
   both ways and D2's law holds; but every encoder changes, and every stored record that holds a
   null becomes non-canonical, which strict decode then refuses.
5. **Packaging.** (a) All in v0.10.0 with the legacy removal, no opt-out. (b) v0.10.0 removes legacy,
   v0.11.0 adds the bound: a second breaking regeneration for every client. (c) A flag first, which
   leaves the overflow open while it exists.
6. **`wellformed`.** RULED (OWNER, 2026-09-28): (a). The node step drops `checked.rs` ("drop
   checked.rs") and `wellformed.rs` with it, since the fail-closed codec then checks everything the
   two check; their tests are kept (CD-G1, CD-G2).
7. **G2.** (a) A D2 follow-up after v0.10.0 with its own lead rows; a tag such as `UnsortedMapKeys`
   would also make the duplicate check one comparison per key. (b) Fold it into v0.10.0.
8. **client-ts.** (a) Its own step after the node step. (b) Inside the node step, which the `bigint`
   change would enlarge.
9. **A repeated non-int map key (rev8).** A repeated key in a `map<K,V>` field is `DuplicateMapKey`
   in all nine, but its `key` payload is pinned only for an int key. For a str or bool key the nine
   report the key itself, 0, the entry's index or nothing, and Python spells a bool `True`, so the
   rows `map-str-key-duplicate` and `map-bool-key-duplicate` pin only the tag.
   - (a) The key as text in every language: an int in decimal, a str as itself, a bool as `true` or
     `false`. Rust's `DuplicateMapKey(i64)` becomes a key type that holds all three (breaking, like
     v0.10.0's other variant changes), and Swift, Go, C++ and Java widen their key field.
   - (b) No `key` payload for a non-int key.
   - (c) Leave it unpinned.
10. **Unknown fields on re-encode (rev8).** Python's and TypeScript's codecs keep a message's
   unknown fields and write them back. The seven generated targets keep them only when generated
   with `--forward-compat`, which is off by default, and otherwise drop them. So `a10100` decoded
   as `Empty` re-encodes as `a10100` in two languages and as `a0` in seven, and no row covers it.
   - (a) The gate also generates the seven with forward-compat, and a row pins the round trip.
     Dropping stays the documented behaviour of generation without the flag.
   - (b) Make forward-compat the generators' default in v0.10.0.
   - (c) Declare dropping an exception to the D2 law.
