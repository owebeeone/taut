# Options: typed properties declared with a taut schema

**Status:** DESIGN, proposed 2026-09-28 on the owner's direction (§0), awaiting the owner's ruling
on what §0 does not settle. A document only: no code, corpus, fixture or version has changed. Once
ruled, it becomes decision **D27** in [TautDecisions.md](TautDecisions.md); D26 is
[TautCheckedDecode.md](TautCheckedDecode.md), whose rev2 takes both of its bounds from this note.

**rev6, 2026-09-29:** OPT-M2 is in the code, in the taut commit that carries this revision (owner:
"go"). It adds `MISSING_OK` in the DSL, a three-valued `FieldDef.optional`, `"optional":
"missing_ok"` in the IR, the gate's ladder, and the change in the Python codec, the Rust generator and
the generator check. `missing_ok` is refused as a keyword and as an IR key. JS and TypeScript support
stays with v0.10.0; gwz-dev's uses move next. Changed: OPT-M2's status.

**rev5, 2026-09-28:** question 9 ruled: "no missing_ok support - transition all use to
optional=MISSING_OK". There is no alias: the keyword, `FieldDef.missing_ok` and the IR's `missing_ok`
key all go, the model and the IR carry the three values too, and every use moves (OPT-M2). Changed:
§0, §1, OPT-I1, OPT-M1, OPT-M2 and question 9.

**rev4, 2026-09-28:** the owner switched presence to one keyword ("switch the notes to
optional=MISSING_OK"): `optional=` takes `False`, `True` or `MISSING_OK` (OPT-M2), in place of rev3's
field option. OPT-D7 and question 10 are withdrawn, and with them the widening rule and the
field-level `effective`. Changed: §0, §1, §8, OPT-D1, OPT-D2, OPT-D7, OPT-L4, OPT-I1, OPT-I2,
OPT-F2, OPT-K1, OPT-P2, OPT-M1, OPT-M2 (new) and questions 1, 5, 9 and 10.

**rev3, 2026-09-28:** the owner's "ok - add option field": `missing_ok` becomes the first field
option (OPT-D7), and a wire option may be *widening*, graded one way (OPT-D1, OPT-K1).
TautCheckedDecode.md question 4 is ruled (a). Changed: §0, §1, OPT-D1, OPT-D2, OPT-D7 (new), OPT-L4,
OPT-I1, OPT-I2, OPT-F2, OPT-K1, OPT-P2, OPT-M1, and questions 1 and 5; questions 9 and 10 are new.

**rev2, 2026-09-28:** rebased onto taut's GitHub commits `3b84365`, `733e8a7` and `bcf98b6`
(2026-09-19 to 22), which this checkout lacked when the note was written. `bcf98b6` adds a sixth
field keyword, `missing_ok`: a wire property, which generators that lack it already refuse. Changed:
the evidence pin, §0's keyword list, OPT-L2, OPT-L5, OPT-F2, OPT-K1 and OPT-M1.

**Evidence.** Paths are from the glade-wz root; lines are at taut `bcf98b6` (rev2 re-pinned them
from `7a5f616`, whose code the first version read). From rev3 the note also cites gwz-dev, a separate
workspace: `gwz-transport` at `a7a36ae` and `gwz-core` at `4a0b7c8d`, the cited files clean.
**OWNER** marks the owner's direction, **PROPOSED** this design, **READ** code read but not run.
Nothing was run for this note.

## 0. The owner's direction

> "so depth becomes a new schema property - we need a different name than schema - protobuf does
> allow for properties at different levels, maybe this should be the beginning of defining a
> property rather than a specific schema struct?" ... "This looks good, it seems like a solid
> framework for current a future extensions." (the owner, 2026-09-28)

**OWNER, 2026-09-28.** Settled; this note does not reopen it:

- **"Option"** is the name, as in protobuf, whose Editions *features* are options that change the
  wire. Whether an option changes the wire is its **class**, part of its definition. **Levels:**
  file (the `.taut.py` module), message, field and enum; later enum value, service and method.
- **Syntax:** positional values, with the word `option` visible (below). Keywords already name
  declarations (`schema(Foo=Msg(...))`) and fields (`Msg(origin=F(...))`), so an option keyword
  would collide with a field of that name. A misspelled option fails at import, a wrong value type at
  its constructor, a wrong level in `tautc`. `option("ns.name", value)` is reserved for custom options.
- **One definition per option:** name and value type, levels, default, inheritance (a lower level
  overrides a higher one where allowed) and class: *wire* (changes what decodes, is covered by the
  parity corpus in every language, and a change of it is a compatibility change), *codegen* (changes
  generated code only) or *metadata* (no effect).
- **The IR** gets an `options` map at each level; `tautc` resolves effective values and generators
  read one each. The keywords `optional=`, `transient=`, `merge=`, `reserved=` and `next_id=` stay;
  a later migration is recorded (§9), not done. `missing_ok=` (rev2) goes, and every use moves to
  `optional=MISSING_OK` (rev5, below).
- **`max_depth`**, the first option: wire, at file and message level, default 32, capped by a fixed
  ceiling of 128, a runtime constant rather than an option, so no schema can reopen the stack
  overflow. `tautc` refuses a declared value below the schema's own deepest non-recursive nesting or
  above the ceiling. Each decode call resolves it from its root message: the message's option, else
  the file's, else 32.
- **Size, the second** ("I suppose we can use this mechanism for size"; "ok with max_size"), is
  **`max_encoded_len`** ("max_encoded_len? - bytes no"): it limits the encoded input's length, not an
  in-memory size. Its levels, default and ceiling are proposed in OPT-D6.
- **Presence** (rev4: "switch the notes to optional=MISSING_OK"): `optional=` takes `False`, `True`
  or `MISSING_OK`, the last also reading an absent key as null. It replaces the field option of rev3
  ("ok - add option field"), and nothing named `missing_ok` survives ("no missing_ok support",
  rev5). OPT-M2 defines it.
- **Protobuf** keeps depth out of the schema, as each reader's parser setting (C++ and Java 100, Go
  10,000). taut goes further, so that readers of one schema cannot disagree.

```python
SCHEMA = schema(
    option.max_depth(16),                 # file level
    Enum("FrameType", ...),
    Msg("Tree",
        option.max_depth(64),             # message level, overrides the file's
        F("children", 1, List(Ref("Tree")))),
    Msg("Head",
        F("origin", 1, STR),
        F("hash", 3, BYTES, option.deprecated(True))),   # field level, a later option
)
```

## 1. The recommendations in brief

| # | Topic | Recommendation (PROPOSED) |
|---|---|---|
| 1 | Where | One new module, `taut/src/taut/ir/options.py`: the definitions, the `option` namespace, the resolver and the bound checks. `dsl.py` takes option values as positionals at every level; `model.py` stores what was declared; `validate.py` checks names, levels, values and bounds; `load.py` and `export.py` read and write IR version 2. |
| 2 | IR | Version 2. Every level carries its raw `options` (`{}` when none); the file and each message also carry `effective`, every wire and codegen option resolved, defaults included. The loader recomputes `effective` and refuses a mismatch, so only Python ever resolves. |
| 3 | Fail closed | An unknown name is refused at import, load and validation, whatever its class. A generator refuses a schema that declares a wire option it does not implement. In v0.10.0 rust, js, python and typescript implement both bounds; cpp, go, java, kotlin and swift refuse a schema that declares either, and mark what they still emit as unbounded. |
| 4 | Compatibility | Changing a wire option's effective value at any root is breaking, both ways; moving a declaration without changing an effective value is no change. Codegen changes are wire-compatible; metadata changes change nothing. |
| 5 | Corpus | Every row carries the bounds it is decoded under. A wire option brings rows at its default, at declared values, at its runtime ceiling if it has one, and rows pinning the root rule. Inheritance is computed only in Python and is unit-tested there. |
| 6 | Protobuf | The same levels, custom options in parentheses, Editions resolving down the scope. Protobuf leaves depth and size to each reader; taut declares them with the schema. |
| 7 | Size | `max_encoded_len`: file and message level, no default (a schema that declares none leaves size to its carriers), declared values at most 2^31 − 1. Carriers apply it before they allocate; decode raises `TooLarge` above it. |
| 8 | Presence | `optional=` takes `False`, `True` or `MISSING_OK` (OWNER); the last also reads an absent key as null. It is a keyword, not an option, and three-valued in the model and the IR too. Nothing named `missing_ok` is supported, and every use moves to `MISSING_OK` (OWNER). rust and python already have the behaviour, js and typescript get it in v0.10.0, and Wave 2 refuses it. |

## 2. What an option is

**OPT-D1 (PROPOSED): one definition per option.** `options.py` holds a registry of `OptionDef`s:

```python
@dataclass(frozen=True)
class OptionDef:
    name: str                   # "max_depth"; custom options, later, "ns.name"
    value_type: type            # int, bool or str
    levels: frozenset[str]      # "file", "message", "field", "enum"; later "enum_value", "service", "method"
    default: object             # the effective value where no level declares one (None: no value)
    klass: str                  # "wire" | "codegen" | "metadata"
    inherits: tuple[str, ...]   # levels consulted, most specific first; () for none
    targets: frozenset[str] | None = None   # codegen: the generators it concerns; None for all
```

A declared option is an `OptionValue(name, value)`, built by its typed constructor
(`option.max_depth(16)`). A unit test checks every definition: its default passes its own checks,
and `inherits` names only levels in `levels`.

**OPT-D2 (PROPOSED): what each class obliges.** **Wire:** every generator implements it or refuses a
schema that declares it (OPT-F2); the parity corpus carries rows for it (OPT-P2); a change of its
effective value is breaking (OPT-K1). **Codegen:** the definition names the generators it concerns
(`targets`); a named generator that does not implement it refuses, as for wire, and any other
ignores it by definition. **Metadata:** no generator reads it; it is exported, diffed for
information and otherwise inert.

**OPT-D3 (PROPOSED): resolution.** An option's effective value at an element is the value declared at
the first level of the definition's `inherits` that declares one, walking from the element out
through the levels that enclose it in the source, else the default. For `max_depth` (message, file):
the message's, else the file's, else 32. "Enclose" is lexical: taut declares messages side by side,
so a message used by another inherits nothing from it. `options.effective(schema, name, message=...)`
is the one implementation; generators call it, and readers outside Python read its output (OPT-I2).

**OPT-D4 (PROPOSED): a decode call has one root, and its bounds are the root's.** A call is rooted at
the type it is asked to decode: Python's `codec.decode(schema, "Tree", data)`
(`taut/src/taut/wire/codec.py:30-31`), TypeScript's `decode(schema, "Tree", data)`
(`taut/src/taut/gen/runtime/typescript/codec.ts:174`), or the generated `Tree::decode` in Rust and
JS (OPT-L6). The root's effective values bound the whole call: depth from its top-level item, unknown
fields included (TautCheckedDecode.md CD-B2), and length over the whole input. As the owner proposed,
a message nested inside does not change the bounds of a call in progress:

1. The raw stage applies the bounds (length before any byte is read, depth at each container's head)
   before the schema stage runs, and knows no schema (TautCheckedDecode.md CD-E5). It cannot tell
   where a nested message begins; applying a nested bound would merge the stages and change which
   tag the order of checks reports.
2. Counted from a nested message's own start, a depth bound would reopen the overflow: a `Tree`
   inside a `Tree` could add up to 128 levels at each step. Counted from the root, a nested bound
   above the root's could never be reached.
3. One number per call lets every reader of a root agree, and is what `TooDeep{limit}` and
   `TooLarge{len, limit}` report.

So an embedded message gets what fits within its root's bounds. In the parity fixture, which declares
no file-level bound, `Holds64 { t: Tree64 }` declares none and resolves to 32, so a `Tree64` inside it
may add at most 31 levels although `Tree64` alone may nest 64 (TautCheckedDecode.md §4.4, row B20;
B30 is the same rule for length). `tautc` SHOULD warn when a message's declared bound cannot take
effect because another message embeds it. A call whose root is not a message, such as an RPC out slot
typed `list<Tree>` (each RPC value is decoded by a call of its own, rooted at its slot's type,
`taut/src/taut/gen/runtime/typescript/taut_client.ts:89-91`), uses the file's effective values, else
the defaults. A raw decode applies the defaults, or the bounds its caller passes, the depth capped at
128 (TautCheckedDecode.md CD-B3). A `bytes` field that carries CBOR is decoded by a call of its own.

**OPT-D5 (PROPOSED): `max_depth`.**

```python
MAX_DEPTH_CEILING = 128   # a runtime constant, not an option
OPTIONS["max_depth"] = OptionDef("max_depth", int, frozenset({"file", "message"}), default=32,
                                 klass="wire", inherits=("message", "file"))
```

- **The constructor** refuses a value that is not an `int`, or is a `bool` (as `F` refuses a bool
  tag, `taut/src/taut/ir/dsl.py:148-149`), or lies outside 1 to 128.
- **`tautc`** refuses, for every root, an effective value below the root's **non-recursive nesting**,
  which no conforming reader could decode, and re-checks 1 to 128 for IR loaded from JSON, which never
  ran the constructor (`taut/src/taut/cli.py:31-35` accepts `.ir.json`). The roots are every message
  and every type a method binds as a param or out slot. I read the owner's "the schema's own deepest
  non-recursive nesting" per root: a file-level value must cover the roots that inherit it.
- **Non-recursive nesting** is the deepest a value reaches without a message repeating on the path: 0
  for a scalar or enum; 1 + that of `T` for `list<T>`; 2 + that of `V` for `map<K,V>`, whose wire is an
  array of `{1: key, 2: value}` maps (`dsl.py:129-130`); for a message, 1 + the largest among its wire
  fields (`taut/src/taut/ir/model.py:74-75`) and the extensions the schema declares, which may ride any
  message (TautDecisions.md D13), a message already on the path counting 0. `Tree` needs 2; glade's
  schema nests five deep (TautCheckedDecode.md CD-B1). A root that needs more than 128 is refused.
- `tautc` SHOULD warn about a recursive message (a tree) that declares no bound: the default limits
  it to 32, which its data may outgrow.

**OPT-D6 (PROPOSED; the option and its name OWNER): `max_encoded_len`.**

```python
MAX_ENCODED_LEN_CEILING = 2**31 - 1   # on declared values; checked by tautc, not by the runtimes
OPTIONS["max_encoded_len"] = OptionDef("max_encoded_len", int, frozenset({"file", "message"}),
                                       default=None, klass="wire", inherits=("message", "file"))
```

- **Levels: file and message**, as for `max_depth`: a protocol declares one limit for its frames, and
  a message that carries blobs declares its own.
- **Default: none.** A schema that declares nothing leaves size to its carriers, as today: taut cannot
  pick one number for glade (16 MiB), taut-shape's u32 stdin framing and razel's socket
  (TautCheckedDecode.md CD-B4). A default would make nothing safer, since decode sees bytes only once
  they are in memory, and only a carrier can refuse a claimed length before it allocates. In
  `effective`, `null` means no bound.
- **Ceiling: 2^31 − 1, on declared values only.** It is the largest length every target can hold in
  one array (a JVM array is indexed by a signed 32-bit int), so no schema declares a bound that a
  conforming reader cannot honour; protobuf stops at the same 2 GiB for the same reason. Unlike depth's,
  it protects no runtime from its input, so it is not a runtime constant, and a raw call may pass any
  length.
- **Floor:** `tautc` refuses a declared value below its root's smallest encoding (every field at its
  shortest canonical value: zero, an empty string, list or map, null for an optional field).
- **Where it applies.** Decode checks the root's effective value before reading a byte and raises
  `TooLarge{len, limit}` above it (TautCheckedDecode.md CD-E5, step 1). A carrier takes it from the
  schema, where declared, for a frame's claimed length before it allocates; one that reads a length
  before it knows the root uses the largest effective value among the roots it may receive, none if
  any has none (CD-B4). It bounds the input, not what the input decodes to (TautCheckedDecode.md G3).

**OPT-D7 (withdrawn, rev4).** rev3 made `missing_ok` a field option on the owner's "add option
field"; the owner then chose one three-valued keyword instead, `optional=MISSING_OK` (OPT-M2). The ID
is not reused.

## 3. Where it lives and what changes (settles 1)

**OPT-L1 (PROPOSED): `taut/src/taut/ir/options.py`, new.** It holds `OptionDef`, `OptionValue`, the
registry `OPTIONS`, both ceilings, the `option` namespace, `effective()` and the two floor checks, and
imports only `model.py`. `option` follows `Ref`'s pattern (`dsl.py:110-121`): an object whose
attributes are the registered constructors, so `option.max_dept(16)` raises `AttributeError`, naming
the known options, at import, and calling `option("ns.name", v)` raises `TypeError` while custom
options are reserved (question 6). `dsl.py` re-exports it, since `.taut.py` modules import DSL names
from there (`taut/ir/parity_int.taut.py:14`). The Python raw decoder imports nothing from taut
(`taut/src/taut/wire/cbor.py:23-26`) and SHOULD stay so: like every runtime it defines its own
`DEFAULT_MAX_DEPTH = 32` and `MAX_DEPTH_CEILING = 128`, and the corpus header pins every copy,
`options.py`'s included (TautCheckedDecode.md CD-C4).

**OPT-L2 (PROPOSED): `dsl.py`.**

- `schema()` keeps every positional (`dsl.py:243-250`) but builds only enums, messages, services and
  extensions from them (`:251-267`), so a positional of any other type is dropped without a word. It
  MUST sort positionals into declarations and option values, and raise `TypeError` on anything else.
- `Msg()` takes only `F(...)` after its name (`:169-171`), `F()` only `(name, tag, type)` or
  `(tag, type)` (`:141-147`), and `Enum()` only a name (`:100-107`). Each MUST also take trailing
  option values, of any option, since a wrong level is `tautc`'s to refuse (OPT-L4). The same option
  twice at one level raises at import, as a message name given twice does (`:164-167`), itself a
  keyword collision the DSL works around: `Msg` takes a string keyword `name` as the message's name.
- `_field_named`, `_message_named` and `_enum_named` rebuild a definition attribute by attribute
  (`:48-57`, `:67-74`, `:84-85`), as does `schema()` (`:257-258`, `:261`), so each would drop a new
  `options` attribute silently. They MUST carry it, preferably through `dataclasses.replace`, so the
  next attribute cannot be dropped either; `_resolve_method` (`:231-238`) too, once methods have options.
  `bcf98b6` shows the cost: its new field attribute, `missing_ok`, had to be added by hand at each
  rebuild (`:56`, `:258`), and in `export.py` and `load.py` too (OPT-L5).

**OPT-L3 (PROPOSED): `model.py`.** `Schema`, `MessageDef`, `FieldDef` and `EnumDef`
(`model.py:136-141`, `:66-75`, `:54-63`, `:48-51`) each gain `options: dict[str, object]`, empty by
default: what was declared at that level, a dict in a frozen dataclass as `EnumDef.members` is
(`:51`). Effective values are computed, not stored. `ServiceDef`, `MethodDef` and enum values gain the
field when their level gets its first option.

**OPT-L4 (PROPOSED): `validate.py`.** `validate` returns error strings and `validate_or_raise` raises
them (`validate.py:17-18`, `:133-136`); `tautc` runs it before generating, building a corpus or
converting JSON (`cli.py:44`, `:89`, `:110`). It gains, at every level: the name is registered; the
level is among the definition's; the value has its type and range; and every root's effective bounds
lie between its floors and the ceilings (OPT-D5, OPT-D6). It has no channel for warnings, so the
SHOULD-warnings of OPT-D4 and OPT-D5 need one: a second list, or a `lint` beside `validate`.

**OPT-L5 (PROPOSED): `export.py` and `load.py`.** `schema_json` writes `"version": 1`
(`export.py:44`), and `schema_from_json` never reads it (`load.py:58-88`): it reads the keys it knows,
defaults those added later (`merge` and `missing_ok` `:65`, `reserved_tags` and `reserved_names`
`:70-71`, `services` `:75`, `extensions` `:87`) and ignores the rest, the derived `shapes` among them
(`export.py:45`). A v0.9 loader given an IR with options would drop them silently. The export
writes version 2 (OPT-I1); the loader accepts versions 1 and 2 only, reads `options` at every level,
refuses an unknown name (OPT-F1) and checks `effective` (OPT-I3). `load_schema` (`load.py:30-40`) is
unchanged: a DSL error surfaces when it executes the module.

**OPT-L6 (PROPOSED): the decode entry points that name their root.** Python's `codec.decode`
(`wire/codec.py:30-31`) and the JSON profile's `cbor_to_json` (`wire/jsoncodec.py:133`) resolve the
message's bounds with `effective()` and pass them to the raw decoder. TypeScript's `decode` and
`decodeRef` (`…/typescript/codec.ts:174`, `:183`) read them from the IR's `effective` through
`SchemaIndex` (`…/typescript/schema.ts:73`). Generated Rust and JS have only `from_cbor` over a tree
the caller decoded (`taut/src/taut/gen/rust.py:279`, `taut/src/taut/gen/js.py:83`); each message
gains `MAX_DEPTH`, `MAX_ENCODED_LEN` and a `decode` from bytes that applies both (TautCheckedDecode.md
CD-B3).

## 4. The IR (settles 2)

**OPT-I1 (PROPOSED): version 2.** A reader accepts versions 1 and 2 and refuses any other. A version-1
IR cannot declare options, so its effective values are the defaults. The 20 exported `.ir.json` files
in the workspace (READ: taut's corpus, taut-shape's and taut-shape-ts's six shape files each, glade's
demo, glade-decl's three copies, taut's docs example) keep working and change only when re-exported.
A field's `optional` also takes `"missing_ok"` (OPT-M2). The `missing_ok` key that taut `bcf98b6`
writes (`taut/src/taut/ir/export.py:64`) is refused, with a message to re-export. A new option does not
change the version,
since an older reader refuses its unknown name (OPT-F1); a change to the IR's structure does.

**OPT-I2 (PROPOSED): raw at every level, effective where it is used.** Every level carries `options`,
the raw map as written, `{}` when none: at the top level for the file, and in each message, field and
enum. Each service and method, and each enum value through its enum's `member_options`, carries one
too, reserved so that their first option needs no new version; until then any name there is unknown
and refused. The file and each message also carry `effective`: every wire and codegen option defined
for that level, resolved (OPT-D3), defaults included.

```json
{"version": 2, "options": {"max_depth": 16}, "effective": {"max_depth": 16, "max_encoded_len": null},
 "messages": [{"name": "Tree", "options": {"max_depth": 64},
               "effective": {"max_depth": 64, "max_encoded_len": null},
               "fields": [{"name": "children", "tag": 1, "options": {}, "...": "..."}]}]}
```

Raw values record what the author wrote, so the IR round-trips to the model and a diff shows where a
value was declared. Effective values are what readers outside Python use: the TypeScript runtime
(OPT-L6) and D25's providers, which receive the IR as JSON (TautDecisions.md D25). Inheritance and
defaults are then implemented once, in Python, and cannot resolve differently by language. The
alternatives are question 1's.

**OPT-I3 (PROPOSED): the loader checks `effective`.** `schema_from_json` builds the model from the
raw maps, recomputes the effective values and refuses an IR whose `effective` differs, a stale or
hand-edited export. The export already writes derived data that the loader ignores (`shapes`,
`export.py:45`); `effective` is derived data that it checks.

## 5. Fail closed (settles 3)

**OPT-F1 (PROPOSED): an unknown option is refused, whatever its class:** in the DSL at import, in IR
JSON at load, and in `validate` for a `Schema` built any other way. A reader cannot know the class of
an option it has never seen, so it cannot know that ignoring it is safe; an unknown name in an IR
means a newer taut wrote it, and the IR is refused until the reader is upgraded.

**OPT-F2 (PROPOSED): a generator that does not implement a wire option refuses a schema that
declares it.** Each target lists the wire options it implements, beside `_LANGS`
(`taut/src/taut/gen/scaffold.py:557-567`). Before writing anything, `scaffold.emit` refuses when a
requested target lacks an option declared at any level, as it already refuses an IR with extensions
but no forward-compat (`scaffold.py:651-657`) and, since `bcf98b6`, a schema with a `missing_ok` field
for any target but Python and Rust (`:624-636`), a list written inline rather than beside `_LANGS`.
It never emits code that ignores a declared value.

| Target | Codec | `max_depth` and `max_encoded_len` in v0.10.0 | A schema that declares one |
|---|---|---|---|
| rust | generated `from_cbor` over the vendored `cbor.rs` | implements both: `MAX_DEPTH`, `MAX_ENCODED_LEN` and `decode` per message | generates |
| js | generated `fromCbor` over the vendored `cbor.js` | implements both, as rust | generates |
| python | types only (`scaffold.py:80-99`); `taut.wire.codec` decodes from the `Schema` | implements both in the runtime, through `effective()` | generates |
| typescript | types only (`scaffold.py:163-177`); `codec.ts` decodes from the IR JSON | implements both in the runtime, from `effective` | generates |
| cpp, go, java, kotlin, swift | generated; neither fail-closed nor bounded (`TautCodecParityPlan.md:78`) | implements neither | **refuses** |

**OPT-F3 (PROPOSED): what Wave 2 emits for a schema that declares nothing.** Every schema has an
effective `max_depth`, if only the default, and the five Wave-2 targets enforce no bound: they
recurse without one, panic on malformed input, and are allowlisted until Phase 4
(`taut/corpus/parity/allowlist.json`; TautCheckedDecode.md G1). Refusing every schema would stop all
five until then. Recommended: they keep generating a schema that declares no wire option, with a
header saying that its decode enforces none of taut's bounds, as the legacy codec's banner did
(`scaffold.py:573-578`). A declaration is the author asking for a bound, and it is refused (question 2).

**OPT-F4 (PROPOSED): runtimes that read the IR refuse at load.** The Python and TypeScript codecs are
driven by the schema at run time, so `schema_from_json` and TypeScript's `loadSchema`, which today
casts the JSON without a check (`…/typescript/schema.ts:67`, `:107-109`), refuse an unknown version
and an `effective` entry naming a wire option they do not implement.

**OPT-F5 (PROPOSED): providers.** D25's providers (SPEC) generate too. `tautc` MUST ask each for the
wire options it implements and refuse to run it on a schema that declares another; a provider that
states none implements none. Schema options reach it inside the IR JSON; D25's `options["layout"]`,
the generation parameters `tautc` passes a provider, is a different thing and keeps its name.

## 6. Compatibility (settles 4)

**OPT-K1 (PROPOSED): a wire option.** Changing a wire option's effective value at any root is
**breaking**, both ways. Raising a bound lets new writers produce bytes that readers still at the old
bound refuse; lowering it refuses bytes that old writers produced, which may be stored. For
`max_encoded_len`, none counts as unbounded, so a first declaration lowers it. Neither is like adding
an optional field, which an old reader keeps as an unknown tag (`taut/src/taut/ir/compat.py:11`) and
a new reader, if the field is `optional=MISSING_OK`, reads as null in old messages
(TautCheckedDecode.md question 4; OPT-M2 grades presence): a reader cannot skip nesting that is too
deep or input that is too long, it refuses the whole message. The gate compares effective values, not
raw ones, so moving a declaration without changing an effective value is no change, and a new message
that declares a bound is "message added", compatible as today (`compat.py:115`). `_diff_messages`
(`compat.py:70-115`) gains the per-root comparison; `check_or_raise` (`:177-180`) refuses it under the
same major version.

**OPT-K2 (PROPOSED): codegen and metadata.** A codegen change leaves the bytes alone and is
wire-compatible; it may change the generated API, which the gate, judging only the wire, reports as a
compatible change with a note. A metadata change affects nothing; the gate may list it.

**OPT-K3 (PROPOSED): what older readers see.** A reader carries the effective values of the schema it
was built from: generated Rust and JS as constants, Python and TypeScript in the IR they loaded.
Until every reader and writer of a schema is rebuilt, they disagree on a changed bound, which is why
the change is breaking. A reader older than taut v0.10.0 takes version 2 without checking
(`load.py:58-88`; `schema.ts:107-109`) and ignores `options`, but applies no bound at all, so it is
no worse than today. From v0.10.0 on, readers refuse versions and names they do not know.

**OPT-K4 (PROPOSED): taut's own numbers.** A default is part of the codec contract: changing one
changes the effective value of every schema that relies on it, which needs a new parity contract and
a breaking taut release. Raising a ceiling invalidates no declaration; lowering one can, and is breaking.

## 7. The parity corpus (settles 5)

**OPT-P1 (PROPOSED): rows carry their bounds.** Every row states the effective value of each wire
option it is decoded under, `max_depth` and, when a length bound applies, `max_encoded_len`; a raw
row also carries what its call passes, in `limits`. Before a typed row a harness checks that its
runtime resolved the row's message to those values (generated constants, or `effective` in the IR it
loaded), so a wrong resolution shows as a mismatch, not as an unexplained accept or refusal. The
header carries taut's runtime numbers, `default_max_depth` and `max_depth_ceiling`, which every
runtime's constants must equal (TautCheckedDecode.md CD-C2, CD-C4).

**OPT-P2 (PROPOSED): what a wire option brings.** Rows at its default; at declared values, each
accepted at the bound and refused one beyond it; at its runtime ceiling, if it has one; one pinning
the root rule (OPT-D4); and, where a raw call caps its argument, one pinning the cap. For `max_depth`:
B1-B12 and B17-B27, on fixture messages declaring 64, 2 and 128. For `max_encoded_len`: B13-B16 (raw
calls) and B28-B30, on a fixture message declaring 8 (TautCheckedDecode.md CD-C1, §4.4).

**OPT-P3 (PROPOSED): what stays out of the corpus.** Resolution runs once, in Python, and every other
runtime reads its result, so inheritance cannot differ by language: `options.py`'s unit tests cover
it, with `tautc`'s refusals (below a floor, above a ceiling, at a wrong level, an unknown name). The
length ceiling binds declarations, not runtimes, so it is a `tautc` test too. A call argument out of
range is misuse, not input, and belongs to each runtime's own tests.

## 8. Protobuf (settles 6)

| | protobuf | taut |
|---|---|---|
| Levels | file, message, field, oneof, enum, enum value, service, method, extension range: one `*Options` message each in `descriptor.proto` | file, message, field, enum; enum value, service and method reserved (OPT-I2) |
| Custom options | extensions of an `*Options` message, written in parentheses, `(my.opt)` | `option("ns.name", v)`, reserved |
| Where one may sit | recent versions let a definition name its element types (`targets`) | `levels`, checked by `tautc` |
| Options that change the wire | Editions *features* such as `repeated_field_encoding`, `message_encoding` and `utf8_validation`, resolved down the scope from the edition's defaults | the wire class, resolved down the scope from taut's defaults |
| Unknown option | `protoc` refuses it | refused at import, load and validation |
| A generator that cannot honour one | a plugin declares the editions it supports, and `protoc` refuses the rest | a target refuses a declared wire option it lacks |
| Depth | each reader's parser setting: C++ and Java 100, Go 10,000 | the schema's `max_depth`: 32 unless declared, 128 at most |
| Size | each reader's setting (C++ `SetTotalBytesLimit`, Java `setSizeLimit`), under a hard 2 GiB from signed 32-bit lengths | the schema's `max_encoded_len`: none unless declared, 2^31 − 1 at most |
| Presence | Editions' `field_presence` feature, `LEGACY_REQUIRED`, `EXPLICIT` or `IMPLICIT`, in place of proto2's `required` and `optional` labels | `optional=`: `False`, `True` or `MISSING_OK`, a keyword (OPT-M2) |

The protobuf column is from protobuf's documentation, not from code in this workspace; the depth
defaults are the owner's figures. The difference that matters: two protobuf readers of one schema can
disagree about the same bytes, a message 150 deep being refused in C++ and accepted in Go; two taut
readers of one root cannot.

## 9. The existing keywords, for a later migration

**OPT-M1 (PROPOSED, recorded only).** Five keywords stay; from rev4 `optional=` takes a third value,
and from rev5 `missing_ok=` is gone (OPT-M2, question 9). Moved onto options, their classes would be:

| Keyword | Today | Class |
|---|---|---|
| `optional=` | `F` (`dsl.py:134-151`); three values from rev4 (OPT-M2) | wire, one three-valued option, as protobuf's `field_presence` (§8): `False` needs the key and a value, `True` the key, whose value may be null, and `MISSING_OK` also reads an absent key as null (TautCheckedDecode.md CD-E5, OWNER 2026-09-28) |
| `transient=` | `F`; never on the wire (`model.py:60`, `:74-75`) | wire: it takes the field off the wire |
| `merge=` | `F`; "does not affect the wire encoding" (`model.py:61-62`) | unsettled: the model calls it metadata, but the gate calls a change breaking (`compat.py:93`), since replicas that merge differently diverge (question 7) |
| `reserved=`, `next_id=` | `Msg` (`dsl.py:154-182`); checked (`validate.py:55-58`, `:72-77`) | metadata that `tautc` checks: they constrain how a schema may evolve, not its bytes |

**OPT-M2 (OWNER, 2026-09-28, rev4: "switch the notes to optional=MISSING_OK"; rev5: "no missing_ok
support - transition all use to optional=MISSING_OK"; the rest PROPOSED): presence is one keyword with
three values.** It replaces rev3's field option (OPT-D7). LANDED 2026-09-29 (rev6), all but JS and
TypeScript support, which v0.10.0 brings.

| `optional=` | the field's key | a present `null` | native type |
|---|---|---|---|
| `False`, the default | required (`MissingKey`) | refused (`WrongType`) | `T` |
| `True` | required (`MissingKey`) | `None` | `T` or none |
| `MISSING_OK` | may be absent, read as `None` | `None` | `T` or none |

- **The DSL** exports `MISSING_OK` from `taut.ir.dsl`, beside `INT` and `STR`.
  `F(5, INT, optional=MISSING_OK)` does what `bcf98b6` spells `optional=True, missing_ok=True`, and `F`
  refuses any other value for `optional=`. `F` no longer takes `missing_ok=`: it raises `TypeError`, as
  for any unknown keyword. So the combination `validate` refuses today, `missing_ok` on a required
  field (`taut/src/taut/ir/validate.py:63-64`), can no longer be written at all.
- **The model and the IR carry the three values too** (rev5). `FieldDef.optional` holds `False`, `True`
  or `MISSING_OK`, and `FieldDef.missing_ok` goes (`taut/src/taut/ir/model.py:59`, `:63`).
  `MISSING_OK` is truthy, so every `if f.optional` keeps meaning "may be null"; only the decoders, the
  gate and the generator check ask for `MISSING_OK` (`taut/src/taut/gen/rust.py:287`,
  `taut/src/taut/wire/codec.py:158`, `compat.py:94-96`, `scaffold.py:624-636`). The export writes
  `"optional": "missing_ok"` in place of `bcf98b6`'s key (`export.py:64`), and the loader refuses that
  key with a message to re-export (`load.py:64-65`). A reader older than the change takes
  `"missing_ok"` as a true `optional`, so it reads such a field as a plain optional one.
- **Every use moves** (rev5), in gwz-dev, together with gwz-dev's own taut checkout (at `bcf98b6`),
  since gwz's schemas import `MISSING_OK` from it:
  - gwz-transport's protocol: six fields to `optional=MISSING_OK`
    (`gwz-transport/protocol/transport.taut.py:42-43`, `:74`, `:84-86`), and its exported IR,
    `gwz-transport/protocol/transport.ir.json`, re-exported.
  - gwz-core's tests: twelve `FieldDef`s drop their seventh positional and take `MISSING_OK` as their
    `optional` (`gwz-core/tests/transport_consumer/protocol/candidate.taut.py:77-107`), and the test
    that asserts `field.missing_ok` checks `field.optional` instead
    (`gwz-core/tests/transport_consumer/candidate/test_candidate.py:63`, `:88-89`).
  - gwz's live design documents that name the keyword: `dev-docs/GwzCoreSessionDesign.md:531`,
    `dev-docs/GwzCoreSessionPlan.md:166`, `gwz-core/dev-docs/GwzRemoteTransportPlacementA.md:16` and
    `gwz-core/dev-docs/GwzRemoteTransportSetupFailureAmendment.md:29`. Review and verdict records
    that quote it stay as written.
  - In taut, its tests and `docs/Reference.md`, which documents the keyword until the code changes.
- **Compatibility.** The three values form a ladder, each accepting every message the one before it
  accepts. The gate grades a move by direction, towards `MISSING_OK` compatible and away from it
  breaking. One comparison of `optional` replaces the gate's two checks today, of `optional`
  (`taut/src/taut/ir/compat.py:88-91`) and of `missing_ok` (`:94-96`), which grade the same way.
  Adding an optional field is compatible only at `MISSING_OK` (TautCheckedDecode.md question 4, ruled
  (a)).
- **Targets.** rust and python already have the behaviour, and js and typescript get it in v0.10.0
  (question 4, ruled). `scaffold.emit` keeps refusing the other five for a schema that uses it, with
  js and typescript taken off its list (`taut/src/taut/gen/scaffold.py:624-636`).
- **At the later migration** (OPT-M1), `optional=` moves as one three-valued wire option, as
  protobuf's `field_presence` did (§8).

## 10. Gaps and questions for the owner

**Named gaps** (not solved here):

- **G1 Two-step readers.** A caller that decodes the bytes and then the tree (Rust's or JS's
  `try_decode` then `from_cbor`; Python's `cbor.loads` then `decode_struct`, `codec.py:39-41`) applies
  the raw defaults, not the message's bounds; only the typed entry point applies them (OPT-L6). No
  schema here declares a bound yet, so both agree today, but nothing makes a reader of a schema that
  declares one use the typed entry point.
- **G2 Encode checks neither bound.** Encode stays infallible (`TautCodecParityPlan.md:59-65`), so a
  writer can encode a value deeper or longer than its own readers accept.
- **G3 Extension helpers** decode a host whose schema they do not know (TautCheckedDecode.md CD-E4).
  Recommended: the depth ceiling and no length bound for the host, the only bounds every valid host
  meets, leaving the host's own bounds to its reader. An extension declared in another schema rides a
  host's residual without entering `tautc`'s nesting check.
- **G4 Later levels.** How a method's or service's option combines with its slot's root message, and
  the DSL form for an enum value's options (members are keywords, `dsl.py:100-107`), wait for the first
  option that needs them.
- **G5 Other unknown keys.** The loader still ignores unknown IR keys outside `options`
  (`load.py:58-88`); only options are made strict here.
- **G6 Wave 2** enforces neither bound until Phase 4 (OPT-F3).

**Questions.** Each lists its alternatives; (a) is recommended.

1. **Resolved values in the IR.** (a) Raw `options` at every level and `effective` at file and message
   level, checked by the loader. (b) Raw only: the TypeScript runtime and every provider reimplement
   inheritance and defaults, a new parity surface. (c) Effective only: the IR no longer records where
   a value was declared, and cannot round-trip to the DSL.
2. **Wave 2 in v0.10.0.** (a) Refuse a schema that declares either bound; emit the rest with a header
   saying their decode is unbounded. (b) Refuse every schema until Phase 4, the strictest reading of
   "never ignore the option". (c) Add both checks to the five runtimes now, as a panic or throw until
   they are fail-closed.
3. **Unknown options.** (a) Refused, whatever the class. (b) Let unknown metadata options through,
   which needs each option's class in the IR, so that a reader can tell one it has never seen.
4. **Levels in version 2.** (a) `options` at all seven levels now, so the later three need no new
   version. (b) The four named now, and version 3 when the others get options.
5. **Changing a wire option.** (a) Breaking both ways. (b) Raising a bound compatible, accepting that
   readers still at the old bound refuse new writers' bytes.
6. **Custom options.** (a) `option("ns.name", v)` raises at import until custom options are designed.
   (b) Accepted there, then refused by `tautc` as unknown.
7. **`merge` at the migration.** (a) A fourth class, *semantic*: no byte changes but what readers
   compute does, so a change is breaking as for wire. (b) Wire. (c) Metadata, which contradicts the
   gate.
8. **`max_encoded_len`'s default and ceiling.** (a) No default, so a schema that declares none leaves
   size to its carriers as today, and a ceiling of 2^31 − 1 on declared values. (b) A default for
   every schema, such as glade's 16 MiB: uniform, but razel and taut-shape would have to declare more
   to keep what they accept today, and no safer, since only a carrier refuses before it allocates.
   (c) No ceiling, which lets a schema declare a bound a JVM or wasm32 reader cannot hold.
9. **The `missing_ok=` keyword.** RULED (OWNER, 2026-09-28, rev5): "no missing_ok support - transition
   all use to optional=MISSING_OK". No alias in any form: the keyword, `FieldDef.missing_ok` and the
   IR key all go, and every use moves (OPT-M2). The alternatives were an alias through v0.10.x, an
   alias for good, and removal at v0.10.0 with gwz moving at its own regeneration.
10. **`missing_ok`'s levels (rev3).** Withdrawn in rev4: `optional=` is a keyword, written on each
    field.
