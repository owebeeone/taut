"""Deterministically (re)generate the taut codec-parity vector files.

    python gen_vectors.py            # rewrites int.vectors.json + malformed.vectors.json

The round-trip integer bytes are produced by taut's OWN reference wire codec
(`taut.wire.codec`), so the committed `.json` is at once **reviewable** (a human
reads the value + the bytes) and **regenerable** (this script re-derives them from
the frozen codec). Malformed vectors are **hand-authored hex** — each row is a
deliberate wire corruption carrying a one-line `why`; they are never mutated
golden entries.

This parity corpus **SUPPLEMENTS** `tautc corpus` / the message golden corpora —
it never replaces them. The golden kit proves value round-trips; this fixture
adds the boundary, adversarial, and fail-closed vectors the kit cannot host.

Rows added beyond the reviewed cac5e62 baseline carry `"lead": true`. Those are
the **leading** rows: the strict-canonical D2 requirements (`NonCanonicalInt`,
`NegativeMapKey`) that no codec satisfies yet, a nested-truncation vector, and
`2^53+1`. Per-language *baseline* smoke tests pin the reviewed set and skip the
`lead` rows; the governed `tautc parity` gate replays **every** row. This is how
the gate LEADS (it demands not-yet-built behaviour) without breaking the existing
green per-language smoke tests.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent  # taut/
sys.path.insert(0, str(ROOT / "src"))

from taut.ir.load import load_schema  # noqa: E402
from taut.wire import codec  # noqa: E402

CONTRACT = "taut-codec-parity/i64/v0"
SCHEMA_PATH = "ir/parity_int.taut.py"
SCHEMA = load_schema(ROOT / SCHEMA_PATH)

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


def _mal(name, stage, bytes_hex, expect, why, *, schema=None, lead=False) -> dict:
    row: dict = {"name": name, "stage": stage}
    if schema is not None:
        row["schema"] = schema  # emitted before `bytes`, matching the reviewed baseline
    row["bytes"] = bytes_hex
    row["expect"] = expect
    row["why"] = why
    if lead:
        row["lead"] = True
    return row


# --- malformed-input vectors (hand-authored hex) ------------------------------
# Every canonical decode tag from the contract (§2b), one nested failure, plus
# the ratified D2-strict rows. Baseline rows are byte-for-byte stable; the four
# leading rows (NonCanonicalInt x2, NegativeMapKey, nested truncation) are last.
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


def render(vectors: list[dict]) -> str:
    """The exact committed file text for a vector list (stable + regenerable)."""
    doc = {
        "version": 1,
        "contract": CONTRACT,
        "schema_path": SCHEMA_PATH,
        "vectors": vectors,
    }
    return _fmt(doc, 0) + "\n"


def _write(path: Path, vectors: list[dict]) -> None:
    path.write_text(render(vectors))
    print(path)


def main() -> None:
    _write(HERE / "int.vectors.json", INT_VECTORS)
    _write(HERE / "malformed.vectors.json", MALFORMED_VECTORS)
    print(f"# {len(INT_VECTORS)} int vectors, {len(MALFORMED_VECTORS)} malformed vectors", file=sys.stderr)


if __name__ == "__main__":
    main()
