"""Deterministically (re)generate the taut codec-parity vector files.

    python gen_vectors.py            # rewrites int, malformed and bounds.vectors.json

The round-trip integer bytes are produced by taut's OWN reference wire codec
(`taut.wire.codec`), so the committed `.json` is at once **reviewable** (a human
reads the value + the bytes) and **regenerable** (this script re-derives them from
the frozen codec). Raw malformed vectors are **hand-authored hex** — each row is a
deliberate wire corruption carrying a one-line `why`; they are never mutated
golden entries. The `Late` and `Shapes` rows take their bytes from the same codec:
a value encoded (`codec.encode`), or its wire structure (`codec.encode_struct`)
altered and then encoded (`cbor.dumps`).

This parity corpus **SUPPLEMENTS** `tautc corpus` / the message golden corpora —
it never replaces them. The golden kit proves value round-trips; this fixture
adds the boundary, adversarial, and fail-closed vectors the kit cannot host.

Rows added beyond the reviewed cac5e62 baseline carry `"lead": true`. Those are
the **leading** rows: the strict-canonical D2 requirements (`NonCanonicalInt`,
`NegativeMapKey`) that no codec satisfies yet, a nested-truncation vector,
`2^53+1`, rows M1-M17 of TautCheckedDecode.md §4.4 (one order of checks,
payload words, and inputs that must decode), and the gaps the language agents
found (a leading BOM, the other simple values, every field shape, duplicate
non-int map keys), question 10's unknown fields and the `Names` fixture's field
names. Per-language *baseline* smoke tests
pin the reviewed set and skip the `lead` rows; the governed `tautc parity` gate
replays **every** row. This is how the gate LEADS (it demands not-yet-built
behaviour) without breaking the existing green per-language smoke tests.

A malformed row's `expect` is either `{"tag": ..., <payload>}`, whose payload
fields the gate compares as strings, or `{"accept": true}` for an input that must
decode without error and re-encode to its own bytes (CD-C2, CD-C4; D2's law,
decode ok => encode(decode(bytes)) == bytes). An accept row whose re-encoding
differs by declaration carries it as `"reencode": "<hex>"`: an absent
`optional=MISSING_OK` key re-encodes as null.

A from_cbor row may add `expect_dropping`, the expectation for a codec that drops a
message's unknown fields: the seven generated targets built without forward-compat.
Python, TypeScript and every `<target>/fc` variant keep them and are judged by `expect`
(TautCheckedDecode.md §8 question 10).

`bounds.vectors.json` holds TautCheckedDecode.md §4.4's rows B1-B30 (CD-C1, CD-C2), written
by hand like the raw malformed rows and all leading. Its header records contract v1's two
depth numbers. A row's `bytes` may be a list of segments, each a hex string or
`{"repeat": "<hex>", "count": N}`, so a 100,000-deep row stays one line, and `len` gives the
expanded length. A raw row's `limits` are what its call passes; every row's `bounds` are
what it is decoded under, checked here against Python's resolution.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent  # taut/
sys.path.insert(0, str(ROOT / "src"))

from taut.ir import options  # noqa: E402
from taut.ir.load import load_schema  # noqa: E402
from taut.ir.model import MsgRef, Scalar  # noqa: E402
from taut.wire import cbor, codec  # noqa: E402

CONTRACT = "taut-codec-parity/i64/v1"
SCHEMA_PATH = "ir/parity_int.taut.py"
SCHEMA = load_schema(ROOT / SCHEMA_PATH)
# Contract v1's depth numbers: bounds.vectors.json's header records them, and every runtime's
# constants, `taut.ir.options`' and the raw decoder's included, must equal them (CD-B3, CD-C4).
BOUNDS_HEADER = {"default_max_depth": 32, "max_depth_ceiling": 128}
assert (options.DEFAULT_MAX_DEPTH, options.MAX_DEPTH_CEILING) == tuple(BOUNDS_HEADER.values())
assert (cbor.DEFAULT_MAX_DEPTH, cbor.MAX_DEPTH_CEILING) == tuple(BOUNDS_HEADER.values())

INT_MIN = -(1 << 63)
INT_MAX = (1 << 63) - 1
TWO53 = 1 << 53
U64_MAX = (1 << 64) - 1


def _round_trip(name: str, n: int, pairs: tuple[tuple[int, int], ...] = (), *, lead: bool = False) -> dict:
    """A round_trip row whose canonical bytes come from taut's own codec."""
    native = {"n": n, "by_id": {k: v for k, v in pairs}}
    row: dict = {
        "name": name,
        "kind": "round_trip",
        "message": "IntBox",
        "value": {"n": str(n), "by_id": [[str(k), str(v)] for k, v in pairs]},
        "cbor": codec.encode(SCHEMA, "IntBox", native).hex(),
    }
    if lead:
        row["lead"] = True
    return row


def _encode_fail(name: str, n: int, *, lead: bool = False) -> dict:
    """A native int outside the frozen i64 subset — encode must reject it.

    REAL only for unbounded-carrier languages (Python `int`, TS/js `bigint`); a
    native-i64 target cannot even construct the value, so its harness marks the
    row satisfied-by-the-type-system rather than skipping it silently.
    """
    row: dict = {
        "name": name,
        "kind": "encode_fail",
        "message": "IntBox",
        "value": {"n": str(n), "by_id": []},
        "expect": {"tag": "IntOutOfSubset"},
    }
    if lead:
        row["lead"] = True
    return row


# --- integer-range vectors ----------------------------------------------------
# Baseline (reviewed) rows first, byte-for-byte stable; the one leading row last.
INT_VECTORS = [
    _round_trip("zero", 0),
    _round_trip("minus-one", -1),
    _round_trip("safe-int-max", TWO53 - 1),               # 2^53 - 1
    _round_trip("safe-int-plus-one", TWO53),              # 2^53
    _round_trip("i64-max", INT_MAX),                      # 2^63 - 1
    _round_trip("i64-min", INT_MIN),                      # -2^63
    _round_trip("map-key-i64-bounds", 0, ((INT_MIN, -1), (INT_MAX, 1))),
    _encode_fail("encode-too-large-positive", INT_MAX + 1),   # 2^63
    _encode_fail("encode-too-large-negative", INT_MIN - 1),   # -2^63 - 1
    _encode_fail("encode-u64-max", U64_MAX),                  # 2^64 - 1
    # --- leading -----------------------------------------------------------
    _round_trip("safe-int-plus-two", TWO53 + 1, lead=True),   # 2^53 + 1
]


def _mal(name, stage, bytes_hex, expect, why, *, schema=None, lead=False, expect_dropping=None) -> dict:
    row: dict = {"name": name, "stage": stage}
    if schema is not None:
        row["schema"] = schema  # emitted before `bytes`, matching the reviewed baseline
    row["bytes"] = bytes_hex
    row["expect"] = expect
    if expect_dropping is not None:
        row["expect_dropping"] = expect_dropping
    row["why"] = why
    if lead:
        row["lead"] = True
    return row


# --- schema-stage values: Late and Shapes (ir/parity_int.taut.py) -------------
# Their rows' bytes come from taut's own codec, never from hand-written hex.
SHAPES_TAGS = {f.name: f.tag for f in SCHEMA.messages["Shapes"].fields}

# Every field set, the optional ones included; at least two entries in each map.
SHAPES_FILLED = {
    "count": -1000,
    "ratio": 1.5,                                    # shortest form is a half: f9 3e00
    "label": "na\u00efve \u2603 \U0001d11e",             # 2-, 3- and 4-byte UTF-8
    "blob": b"\x00\x7f\xff",
    "flag": True,
    "mode": "alt",
    "boxed": {"mode": "alt"},
    "maybe_count": 7,
    "maybe_mode": "ok",
    "maybe_boxed": {"mode": "ok"},
    "numbers": [1, -2, 300],
    "boxes": [{"mode": "ok"}, {"mode": "alt"}],
    "grid": [[1, 2], [], [3]],                       # a nested list holding an empty list
    "tally": {"a": 1, "b": -2},
    "mode_by_flag": {False: "alt", True: "ok"},
    "box_by_id": {2: {"mode": "alt"}, 10: {"mode": "ok"}},
    "maybe_numbers": [4, 5],
    "maybe_tally": {"x": 0, "y": 9},
    "late_note": "late",
}

# Every optional field null, every collection empty, the MISSING_OK field present as null.
SHAPES_SPARSE = {
    "count": 0,
    "ratio": 0.0,
    "label": "",
    "blob": b"",
    "flag": False,
    "mode": "ok",
    "boxed": {"mode": "ok"},
    "maybe_count": None,
    "maybe_mode": None,
    "maybe_boxed": None,
    "numbers": [],
    "boxes": [],
    "grid": [],
    "tally": {},
    "mode_by_flag": {},
    "box_by_id": {},
    "maybe_numbers": None,
    "maybe_tally": None,
    "late_note": None,
}


def _encoded(message: str, value: dict) -> str:
    return codec.encode(SCHEMA, message, value).hex()


def _entries(field: str, mapping: dict) -> list:
    """A Shapes map field's wire entries for `mapping`, from taut's own codec."""
    return codec.encode_struct(SCHEMA, "Shapes", {**SHAPES_SPARSE, field: mapping})[SHAPES_TAGS[field]]


def _sparse_altered(*, drop: tuple[str, ...] = (), **wire) -> str:
    """shapes-sparse's wire structure with the fields in `drop` removed and the
    fields named in `wire` replaced by the given wire structures, then encoded."""
    struct = codec.encode_struct(SCHEMA, "Shapes", SHAPES_SPARSE)
    for name in drop:
        del struct[SHAPES_TAGS[name]]
    for name, value in wire.items():
        struct[SHAPES_TAGS[name]] = value
    return cbor.dumps(struct).hex()


LATE_ABSENT = cbor.dumps({}).hex()
LATE_NULL = _encoded("Late", {"note": None})
LATE_INT = cbor.dumps({1: 1}).hex()
# The encoder agrees with TautCheckedDecode.md §4.4's bytes for M16 and M17.
assert (LATE_ABSENT, LATE_NULL, LATE_INT) == ("a0", "a101f6", "a10101")

SHAPES_SPARSE_HEX = _encoded("Shapes", SHAPES_SPARSE)

# Question 10's unknown fields (TautCheckedDecode.md §8): Empty holding a field 1, and an
# IntBox beside a field 3. A codec that keeps them writes them back; one that drops them
# writes the message alone.
EMPTY_HEX = _encoded("Empty", {})
EMPTY_BESIDE_UNKNOWN_HEX = cbor.dumps({1: 0}).hex()
assert (EMPTY_HEX, EMPTY_BESIDE_UNKNOWN_HEX) == ("a0", "a10100")
INTBOX_KNOWN = {"n": 7, "by_id": {1: -1}}
INTBOX_KNOWN_HEX = _encoded("IntBox", INTBOX_KNOWN)
INTBOX_BESIDE_UNKNOWN_HEX = cbor.dumps({**codec.encode_struct(SCHEMA, "IntBox", INTBOX_KNOWN), 3: "x"}).hex()

# Names (ir/parity_int.taut.py): every field set, each int to its own tag, so a value
# written under another field's name changes the bytes.
NAMES_FILLED = {
    **{f.name: f.tag for f in SCHEMA.messages["Names"].fields if f.type == Scalar("int")},
    "c": "c",
    "e": [1, 2],
    "k": {"a": 1, "b": 2},
    "arr": ["x", "y"],
    "key": True,
    "entries": {1: 2, 3: 4},
}


# --- malformed-input vectors ----------------------------------------------------
# Every canonical decode tag from the contract (§2b), one nested failure, plus
# the ratified D2-strict rows. Baseline rows are byte-for-byte stable; the leading
# rows (NonCanonicalInt x2, NegativeMapKey, nested truncation, M1-M17, then the
# gap rows) are last. Raw rows are hand-authored hex; Late and Shapes rows are not.
MALFORMED_VECTORS = [
    _mal("truncated-u64-argument", "raw_decode", "1b0000",
         {"tag": "Truncated"},
         "major-0 says eight argument bytes, only two are present"),
    _mal("trailing-byte", "raw_decode", "0000",
         {"tag": "TrailingBytes"},
         "one complete int followed by extra data"),
    _mal("invalid-utf8", "raw_decode", "61ff",
         {"tag": "InvalidUtf8"},
         "text string payload is not UTF-8"),
    _mal("reserved-additional-info-28", "raw_decode", "1c",
         {"tag": "UnsupportedInfo", "info": 28},
         "additional-info 28 is reserved by CBOR and outside taut's subset"),
    _mal("unsupported-major-tag", "raw_decode", "c0",
         {"tag": "UnsupportedMajor", "major": 6},
         "CBOR tags are outside taut's frozen subset"),
    _mal("non-integer-map-key", "raw_decode", "a1617800",
         {"tag": "NonIntegerMapKey"},
         "raw CBOR maps must use integer field-tag keys"),
    _mal("duplicate-map-key", "raw_decode", "a201000101",
         {"tag": "DuplicateMapKey", "key": 1},
         "same raw CBOR map key appears twice"),
    _mal("positive-int-overflow", "raw_decode", "1b8000000000000000",
         {"tag": "IntOverflow", "value": "9223372036854775808"},
         "CBOR major-0 value is just above i64::MAX"),
    _mal("negative-int-overflow", "raw_decode", "3b8000000000000000",
         {"tag": "IntOverflow", "value": "-9223372036854775809"},
         "CBOR major-1 value is just below i64::MIN"),
    _mal("missing-required-field", "from_cbor", "a10100",
         {"tag": "MissingKey", "key": 2}, schema="IntBox",
         why="IntBox.by_id is required and absent"),
    _mal("wrong-type-field", "from_cbor", "a20161780280",
         {"tag": "WrongType", "expected": "int"}, schema="IntBox",
         why="IntBox.n wants int, received text"),
    _mal("unknown-enum", "from_wire", "1863",
         {"tag": "UnknownEnum", "enum": "Mode", "value": "99"}, schema="Mode",
         why="Mode has no member with wire value 99"),
    # --- leading (D2-strict + nested) --------------------------------------
    _mal("non-canonical-int-2byte", "raw_decode", "190005",
         {"tag": "NonCanonicalInt", "value": "5"},
         "value 5 in a 2-byte argument (0x19 0x0005); canonical is the immediate 0x05 (width 25)",
         lead=True),
    _mal("non-canonical-int-8byte", "raw_decode", "1b0000000000000005",
         {"tag": "NonCanonicalInt", "value": "5"},
         "value 5 in an 8-byte argument; canonical is the immediate 0x05 (width 27)",
         lead=True),
    _mal("negative-map-key", "raw_decode", "a12000",
         {"tag": "NegativeMapKey", "key": "-1"},
         "raw CBOR map key -1 (major-1); the canonical encoder only emits non-negative field tags",
         lead=True),
    _mal("nested-truncated-string", "raw_decode", "a100636162",
         {"tag": "Truncated"},
         "text string nested inside a map claims 3 bytes but only 2 are present",
         lead=True),
    # --- leading: TautCheckedDecode.md §4.4 M1-M15 (CD-E5 order of checks, CD-E6 words) ---
    _mal("bytes-length-over-2^53", "raw_decode", "5b0020000000000000",
         {"tag": "Truncated"},
         "M1: a byte string (major 2) claims 2^53 bytes and none follow; a length beyond "
         "the remaining bytes is Truncated whatever its size, not IntOverflow",
         lead=True),
    _mal("array-count-u64-max", "raw_decode", "9bffffffffffffffff",
         {"tag": "Truncated"},
         "M2: an array claims 2^64-1 items and none follow; the first item's missing head "
         "is Truncated, not IntOverflow",
         lead=True),
    _mal("items-read-in-order", "raw_decode", "85c0",
         {"tag": "UnsupportedMajor", "major": 6},
         "M3: items are read in order, so the first item's tag head (major 6) fails "
         "before the four missing items are reached",
         lead=True),
    _mal("key-first-duplicate", "raw_decode", "a2010001",
         {"tag": "DuplicateMapKey", "key": 1},
         "M4: a map entry's key is checked before its value is read; key 1 repeats and "
         "its value is missing",
         lead=True),
    _mal("key-first-text", "raw_decode", "a16178",
         {"tag": "NonIntegerMapKey"},
         "M5: a map entry's key is checked before its value is read; the key is text and "
         "its value is missing",
         lead=True),
    _mal("key-first-negative", "raw_decode", "a120",
         {"tag": "NegativeMapKey", "key": "-1"},
         "M6: a map entry's key is checked before its value is read; the key is -1 and "
         "its value is missing",
         lead=True),
    _mal("major-6-info-28", "raw_decode", "dc",
         {"tag": "UnsupportedMajor", "major": 6},
         "M7: the major type is checked before the additional info; 0xdc is major 6 "
         "with the reserved info 28",
         lead=True),
    _mal("map-key-2^53", "raw_decode", "a11b002000000000000000",
         {"accept": True},
         "M8: a raw map key of 2^53 is an i64 like any other and decodes; 2^53 is no "
         "limit on keys",
         lead=True),
    _mal("wrong-type-text", "from_cbor", "a201010280",
         {"tag": "WrongType", "expected": "text"}, schema="OptBox",
         why="M9: OptBox.note wants text and holds an int; the payload word is `text` "
             "(CD-E6), not `str`",
         lead=True),
    _mal("wrong-type-array", "from_cbor", "a201f60200",
         {"tag": "WrongType", "expected": "array"}, schema="OptBox",
         why="M10: OptBox.tags wants an array and holds an int; the payload word is "
             "`array` (CD-E6), not `list`",
         lead=True),
    _mal("optional-absent", "from_cbor", "a10280",
         {"tag": "MissingKey", "key": 1}, schema="OptBox",
         why="M11: an absent optional field is MissingKey; the canonical encoder always "
             "writes it, as null when unset",
         lead=True),
    _mal("empty-message-not-map", "from_cbor", "00",
         {"tag": "WrongType", "expected": "map"}, schema="Empty",
         why="M12: a message with no fields must still be a map",
         lead=True),
    _mal("map-field-duplicate", "from_cbor", "a201000282a201050201a201050202",
         {"tag": "DuplicateMapKey", "key": 5}, schema="IntBox",
         why="M13: two IntBox.by_id entries share the key 5; a map<K,V> refuses a "
             "repeated key rather than keeping the last",
         lead=True),
    _mal("map-entry-keys-first", "from_cbor", "a201000281a1016178",
         {"tag": "MissingKey", "key": 2}, schema="IntBox",
         why="M14: a map<K,V> entry checks for keys 1 and 2 before decoding either; this "
             "entry lacks key 2 and its key 1 holds text",
         lead=True),
    _mal("optional-present-null", "from_cbor", "a201f60280",
         {"accept": True}, schema="OptBox",
         why="M15: an optional field present as null decodes, to null",
         lead=True),
    # --- leading: M16-M17 (Late, optional=MISSING_OK) --------------------------
    _mal("missing-ok-absent", "from_cbor", LATE_ABSENT,
         {"accept": True, "reencode": LATE_NULL}, schema="Late",
         why="M16: Late.note is optional=MISSING_OK, so an absent key decodes to null; the "
             "encoder writes the null back, the declared exception to D2's law",
         lead=True),
    _mal("missing-ok-wrong-type", "from_cbor", LATE_INT,
         {"tag": "WrongType", "expected": "text"}, schema="Late",
         why="M17: MISSING_OK forgives only an absent key; Late.note present as an int is "
             "still WrongType, with the payload word `text`",
         lead=True),
    # --- leading: gaps the language agents found (raw rows are hand-authored) ---
    _mal("text-leading-bom", "raw_decode", "64efbbbf61",
         {"accept": True},
         "U+FEFF (ef bb bf) opening a text string is ordinary text: decode keeps it and "
         "re-encoding writes it back; a UTF-8 decoder must not strip it as a byte-order mark",
         lead=True),
    _mal("simple-undefined", "raw_decode", "f7",
         {"tag": "UnsupportedInfo", "info": 23},
         "major 7 info 23 (undefined) is none of the kept values: false, true, null and the "
         "three floats",
         lead=True),
    _mal("simple-zero", "raw_decode", "e0",
         {"tag": "UnsupportedInfo", "info": 0},
         "major 7 info 0 (simple value 0) is none of the kept values",
         lead=True),
    _mal("simple-one-byte-torn", "raw_decode", "f8",
         {"tag": "UnsupportedInfo", "info": 24},
         "major 7 info 24 (a one-byte simple value) whose argument byte is missing: the "
         "initial byte decides, so its argument is never read (CD-E5 step 2)",
         lead=True),
    # --- leading: Shapes, every legal field shape (bytes from taut's own codec) ---
    _mal("shapes-filled", "from_cbor", _encoded("Shapes", SHAPES_FILLED),
         {"accept": True}, schema="Shapes",
         why="every field shape set, the optional ones included, decodes and re-encodes "
             "to these bytes: a half-width float, non-ASCII text, a nested list holding "
             "an empty list, and two entries in each map",
         lead=True),
    _mal("shapes-sparse", "from_cbor", SHAPES_SPARSE_HEX,
         {"accept": True}, schema="Shapes",
         why="every optional field null, every collection empty and the MISSING_OK field "
             "present as null: decodes and re-encodes to these bytes",
         lead=True),
    _mal("shapes-missing-ok-absent", "from_cbor", _sparse_altered(drop=("late_note",)),
         {"accept": True, "reencode": SHAPES_SPARSE_HEX}, schema="Shapes",
         why="shapes-sparse without the MISSING_OK key 19 decodes, and re-encodes with "
             "it as null: shapes-sparse's bytes",
         lead=True),
    _mal("map-str-key-order", "from_cbor",
         _encoded("Shapes", {**SHAPES_SPARSE, "tally": {"￿": 1, "\U00010000": 2, "a": 3}}),
         {"accept": True}, schema="Shapes",
         why="shapes-sparse whose map<str,int> holds the keys U+FFFF, U+10000 and \"a\", written "
             "in code point order (\"a\", U+FFFF, U+10000), which is UTF-8 byte order; a codec "
             "that sorts str keys by UTF-16 code unit puts U+10000 (d800 dc00) before U+FFFF "
             "and does not re-encode these bytes",
         lead=True),
    _mal("map-str-key-duplicate", "from_cbor",
         _sparse_altered(tally=[*_entries("tally", {"a": 1}), *_entries("tally", {"a": 2})]),
         {"tag": "DuplicateMapKey", "key": "a"}, schema="Shapes",
         why="shapes-sparse whose map<str,int> holds two entries keyed \"a\": a repeated "
             "key is refused whatever its type, and its key payload is the key as text, a "
             "str as itself (TautCheckedDecode.md §8 question 9)",
         lead=True),
    _mal("map-bool-key-duplicate", "from_cbor",
         _sparse_altered(mode_by_flag=[*_entries("mode_by_flag", {True: "ok"}),
                                       *_entries("mode_by_flag", {True: "alt"})]),
         {"tag": "DuplicateMapKey", "key": "true"}, schema="Shapes",
         why="shapes-sparse whose map<bool,Mode> holds two entries keyed true: "
             "DuplicateMapKey with the key as text, a bool as `true` or `false` (question 9)",
         lead=True),
    _mal("list-nested-wrong-type", "from_cbor", _sparse_altered(grid=[["x"]]),
         {"tag": "WrongType", "expected": "int"}, schema="Shapes",
         why="shapes-sparse whose list<list<int>> holds [[\"x\"]]: an inner list's item "
             "is checked as an int",
         lead=True),
    # --- leading: question 10, unknown fields (TautCheckedDecode.md §8) ------------
    _mal("unknown-field-round-trip", "from_cbor", EMPTY_BESIDE_UNKNOWN_HEX,
         {"accept": True}, schema="Empty",
         expect_dropping={"accept": True, "reencode": EMPTY_HEX},
         why="Empty holding a field 1 it does not know: python, typescript and every "
             "<target>/fc keep the unknown field and write it back; the seven generated "
             "without forward-compat drop it and re-encode the empty map",
         lead=True),
    _mal("unknown-field-beside-known", "from_cbor", INTBOX_BESIDE_UNKNOWN_HEX,
         {"accept": True}, schema="IntBox",
         expect_dropping={"accept": True, "reencode": INTBOX_KNOWN_HEX},
         why="an IntBox {n: 7, by_id: {1: -1}} beside an unknown field 3 = \"x\": a codec "
             "that keeps unknown fields writes field 3 back after the known ones, one that "
             "drops them writes the IntBox alone",
         lead=True),
    # --- leading: Names, fields named like generated locals (ir/parity_int.taut.py) ----
    _mal("names-round-trip", "from_cbor", _encoded("Names", NAMES_FILLED),
         {"accept": True}, schema="Names",
         why="every Names field set: fields named like the locals, parameters and unqualified "
             "helpers the generators emit (a Java field `m`, a C++ field `b`) generate, "
             "compile, decode and re-encode to these bytes",
         lead=True),
]


# --- bounds vectors: TautCheckedDecode.md §4.4 B1-B30 ---------------------------------
RAW = "raw_decode"
ACCEPT = {"accept": True}
TRUNCATED = {"tag": "Truncated"}


def _too_deep(limit: int) -> dict:
    return {"tag": "TooDeep", "limit": limit}


def _too_large(length: int, limit: int) -> dict:
    return {"tag": "TooLarge", "len": length, "limit": limit}


def _rep(hexed: str, count: int) -> dict:
    """A segment: `hexed` repeated `count` times."""
    return {"repeat": hexed, "count": count}


def _expanded(segments: str | list) -> bytes:
    if isinstance(segments, str):
        return bytes.fromhex(segments)
    return b"".join(bytes.fromhex(s) if isinstance(s, str) else bytes.fromhex(s["repeat"]) * s["count"]
                    for s in segments)


def _b(name: str, root: str, segments: str | list, bounds: tuple[int, int | None], expect: dict,
       why: str, *, limits: dict | None = None, expect_dropping: dict | None = None) -> dict:
    """A bounds row. `root` is RAW or the message a typed row decodes; `bounds` is
    (max_depth, max_encoded_len or None), what the row is decoded under: a raw row's `limits`,
    the depth capped at the ceiling, else the defaults; a typed row's message's effective
    values, which must be what Python resolves (`codec.bounds`)."""
    limits = limits or {}
    if root == RAW:
        resolved = (min(limits.get("max_depth", BOUNDS_HEADER["default_max_depth"]),
                        BOUNDS_HEADER["max_depth_ceiling"]), limits.get("max_encoded_len"))
    else:
        resolved = codec.bounds(SCHEMA, MsgRef(root))
    assert resolved == bounds, (name, resolved, bounds)
    row: dict = {"name": name, "stage": RAW if root == RAW else "from_cbor"}
    if root != RAW:
        row["schema"] = root
    row["bytes"] = segments
    row["len"] = len(_expanded(segments))
    if limits:
        row["limits"] = limits
    depth, length = bounds
    row["bounds"] = {"max_depth": depth} if length is None else {"max_depth": depth, "max_encoded_len": length}
    row["expect"] = expect
    if expect_dropping is not None:
        row["expect_dropping"] = expect_dropping
    row["why"] = why
    row["lead"] = True
    return row


# B12's IntBox, n 0 and by_id empty, without its unknown field 9.
INTBOX_ZERO_HEX = _encoded("IntBox", {"n": 0, "by_id": {}})
assert INTBOX_ZERO_HEX == "a201000280"

BOUNDS_VECTORS = [
    _b("depth-32-arrays", RAW, [_rep("81", 31), "80"], (32, None), ACCEPT,
       "B1: 32 nested arrays, the innermost empty, decode under the default depth bound, 32 "
       "(CD-B1)"),
    _b("depth-33-arrays", RAW, [_rep("81", 32), "80"], (32, None), _too_deep(32),
       "B2: a 33rd nested array is one beyond the default bound: TooDeep, though it is empty"),
    _b("depth-32-maps", RAW, [_rep("a100", 31), "a0"], (32, None), ACCEPT,
       "B3: 32 nested maps, each holding the next under key 0, decode: a map counts as an "
       "array does"),
    _b("depth-33-maps", RAW, [_rep("a100", 32), "a0"], (32, None), _too_deep(32),
       "B4: a 33rd nested map is TooDeep"),
    _b("depth-32-scalar-leaf", RAW, [_rep("81", 32), "00"], (32, None), ACCEPT,
       "B5: an int inside the 32nd array adds no depth: ints, strings, bools, null and floats "
       "never count"),
    _b("depth-33-items-missing", RAW, [_rep("81", 33)], (32, None), _too_deep(32),
       "B6: the 33rd array's head is complete and its item missing: depth is checked once a "
       "head is read, before its first item, so TooDeep and not Truncated (CD-B2)"),
    _b("depth-33-torn-head", RAW, [_rep("81", 32), "9b00"], (32, None), TRUNCATED,
       "B7: the 33rd array's head claims an 8-byte count and holds one byte: a torn head is "
       "Truncated, before depth is checked (CD-B2)"),
    _b("depth-33-mixed", RAW, [_rep("81a100", 16), "80"], (32, None), _too_deep(32),
       "B8: arrays and maps alternating, 33 deep: both count toward the one bound"),
    _b("depth-100000-arrays", RAW, [_rep("81", 99999), "80"], (32, None), _too_deep(32),
       "B9: 100,000 nested arrays are refused at the 33rd, with no stack overflow, "
       "RecursionError or RangeError on the way (CD-E4)"),
    _b("depth-100000-maps", RAW, [_rep("a100", 99999), "a0"], (32, None), _too_deep(32),
       "B10: 100,000 nested maps, as B9"),
    _b("depth-33-unknown-field", "IntBox", ["a30100028009", _rep("81", 31), "80"], (32, None),
       _too_deep(32),
       "B11: an IntBox whose unknown field 9 holds 32 nested arrays, 33 deep with the message's "
       "map: depth counts unknown fields, and the raw stage refuses them before the schema stage "
       "runs (CD-B2)"),
    _b("depth-32-unknown-field", "IntBox", ["a30100028009", _rep("81", 30), "80"], (32, None),
       ACCEPT, expect_dropping={"accept": True, "reencode": INTBOX_ZERO_HEX},
       why="B12: the same with 31 arrays, 32 deep, decodes: a codec that keeps unknown fields "
           "writes field 9 back, one that drops them writes the IntBox alone"),
    _b("size-at-limit", RAW, "83010203", (32, 4), ACCEPT,
       "B13: four bytes under a raw call's max_encoded_len of 4 decode: input exactly at the "
       "bound is accepted (CD-B5)",
       limits={"max_encoded_len": 4}),
    _b("size-over-limit", RAW, "83010203", (32, 3), _too_large(4, 3),
       "B14: the same four bytes under a bound of 3 are TooLarge, naming the input's length "
       "and the bound (CD-B4)",
       limits={"max_encoded_len": 3}),
    _b("size-before-parse", RAW, "c0c0c0c0", (32, 3), _too_large(4, 3),
       "B15: the length is checked before a byte is read: four CBOR tags, UnsupportedMajor "
       "once read, are TooLarge under a bound of 3 (CD-E5 step 1)",
       limits={"max_encoded_len": 3}),
    _b("size-empty", RAW, "", (32, 0), TRUNCATED,
       "B16: empty input is within a bound of 0, so it is read, and is Truncated (CD-B5)",
       limits={"max_encoded_len": 0}),
    _b("depth-64-declared", "Tree64", [_rep("a10181", 31), "a10180"], (64, None), ACCEPT,
       "B17: a Tree64 64 deep decodes: a typed decode applies its root's declared max_depth, "
       "64 (CD-B3)"),
    _b("depth-65-declared", "Tree64", [_rep("a10181", 32), "a10180"], (64, None), _too_deep(64),
       "B18: a Tree64 65 deep is TooDeep{64}"),
    _b("raw-ignores-declared", RAW, [_rep("a10181", 31), "a10180"], (32, None), _too_deep(32),
       "B19: B17's bytes through the raw decode, which knows no schema, meet the default bound "
       "(CD-B3)"),
    _b("depth-root-decides", "Holds64", ["a101", _rep("a10181", 15), "a10180"], (32, None),
       _too_deep(32),
       "B20: a Tree64 inside a Holds64, 33 deep: the root, Holds64, declares nothing, so 32 "
       "bounds the whole call though Tree64 declares 64 (OPT-D4)"),
    _b("depth-2-declared", "Flat2", "a1018100", (2, None), ACCEPT,
       "B21: a Flat2 at its declared bound, 2, its own non-recursive nesting, decodes"),
    _b("depth-3-declared", "Flat2", "a1018180", (2, None), _too_deep(2),
       "B22: an array inside Flat2's list is 3 deep: TooDeep{2} from the raw stage, before "
       "the schema stage would find a WrongType (CD-E5)"),
    _b("depth-128-ceiling", "Tree128", [_rep("a10181", 63), "a10180"], (128, None), ACCEPT,
       "B23: a Tree128 128 deep, at the ceiling, decodes (CD-B5)"),
    _b("depth-129-ceiling", "Tree128", [_rep("a10181", 64), "a10180"], (128, None),
       _too_deep(128),
       "B24: a Tree128 129 deep is TooDeep{128}"),
    _b("raw-depth-128", RAW, [_rep("81", 127), "80"], (128, None), ACCEPT,
       "B25: a raw call passing max_depth 128 decodes 128 nested arrays",
       limits={"max_depth": 128}),
    _b("raw-depth-129", RAW, [_rep("81", 128), "80"], (128, None), _too_deep(128),
       "B26: the same call refuses 129",
       limits={"max_depth": 128}),
    _b("raw-depth-capped", RAW, [_rep("81", 128), "80"], (128, None), _too_deep(128),
       "B27: a raw call passing max_depth 1000 applies the ceiling, and TooDeep names the bound "
       "applied, 128 (CD-B3, question 1)",
       limits={"max_depth": 1000}),
    _b("len-8-declared", "Sized8", "a101450102030405", (32, 8), ACCEPT,
       "B28: a Sized8 of exactly 8 bytes decodes under its declared max_encoded_len, 8"),
    _b("len-9-declared", "Sized8", "a10146010203040506", (32, 8), _too_large(9, 8),
       "B29: a Sized8 of 9 bytes is TooLarge, before a byte is read (CD-B4)"),
    _b("len-root-decides", "HoldsSized8", ["a101a1014a", "00010203040506070809"], (32, None),
       ACCEPT,
       "B30: a Sized8 longer than 8 bytes inside a HoldsSized8 decodes: the root declares no "
       "length bound, and Sized8's does not apply inside it (OPT-D4)"),
]


def _scalar(v) -> str:
    if v == [] and isinstance(v, list):
        return "[]"
    if v == {} and isinstance(v, dict):
        return "{}"
    return json.dumps(v)


def _inline(container) -> bool:
    """A dict/list is emitted on one line iff none of its children is a
    *non-empty* dict/list (reproduces the reviewed baseline's compact style:
    scalar objects like `expect` and empty `by_id` stay inline; nested pair
    arrays expand)."""
    values = container.values() if isinstance(container, dict) else container
    return all(not (isinstance(v, (dict, list)) and v) for v in values)


def _fmt(obj, indent: int) -> str:
    pad, child = " " * indent, " " * (indent + 2)
    if isinstance(obj, dict):
        if not obj:
            return "{}"
        if _inline(obj):
            return "{" + ", ".join(f"{json.dumps(k)}: {_scalar(v)}" for k, v in obj.items()) + "}"
        body = ",\n".join(f"{child}{json.dumps(k)}: {_fmt(v, indent + 2)}" for k, v in obj.items())
        return "{\n" + body + "\n" + pad + "}"
    if isinstance(obj, list):
        if not obj:
            return "[]"
        if _inline(obj):
            return "[" + ", ".join(_scalar(v) for v in obj) + "]"
        body = ",\n".join(f"{child}{_fmt(v, indent + 2)}" for v in obj)
        return "[\n" + body + "\n" + pad + "]"
    return _scalar(obj)


def render(vectors: list[dict], header: dict | None = None) -> str:
    """The exact committed file text for a vector list (stable + regenerable), with
    `header`'s fields after the schema path (bounds.vectors.json's two numbers)."""
    doc = {
        "version": 1,
        "contract": CONTRACT,
        "schema_path": SCHEMA_PATH,
        **(header or {}),
        "vectors": vectors,
    }
    return _fmt(doc, 0) + "\n"


def _write(path: Path, vectors: list[dict], header: dict | None = None) -> None:
    path.write_text(render(vectors, header))
    print(path)


def main() -> None:
    _write(HERE / "int.vectors.json", INT_VECTORS)
    _write(HERE / "malformed.vectors.json", MALFORMED_VECTORS)
    _write(HERE / "bounds.vectors.json", BOUNDS_VECTORS, BOUNDS_HEADER)
    print(f"# {len(INT_VECTORS)} int vectors, {len(MALFORMED_VECTORS)} malformed vectors, "
          f"{len(BOUNDS_VECTORS)} bounds vectors", file=sys.stderr)


if __name__ == "__main__":
    main()
