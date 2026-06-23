"""Residual + extension conformance corpora — the Phase-2 fork oracle.

Generated from the Python reference (codec `__unknown__` + `ext.py`) over the shared
fixture `ir/resext.taut.py`. Two parse-free oracles every language target must reproduce:

  - residual_vectors.json : a host message with unknown tags decode→re-encodes byte-identical.
  - ext_vectors.json      : ext_set / ext_get / ext_clear, byte-exact against ext.py.

No new logic — this just freezes the existing Python truth into portable hex. Generated;
do not hand-edit the JSON: run this module."""

from __future__ import annotations

import json
from pathlib import Path

from .. import ext
from ..ir.load import load_schema
from ..ir.shapes import BAND_START
from ..wire import cbor, codec

_TAUT = Path(__file__).resolve().parents[3]
IR_PATH = _TAUT / "ir" / "resext.taut.py"
RESIDUAL_PATH = _TAUT / "corpus" / "residual_vectors.json"
EXT_PATH = _TAUT / "corpus" / "ext_vectors.json"

S = load_schema(IR_PATH)
TAG = BAND_START + 1
HOST = {"id": 1, "name": "ann", "score": 9}
DECISION = {"backend": "b7", "hops": 1}
DECISION2 = {"backend": "b9", "hops": 2}


def _residual_rows() -> list[dict]:
    base = codec.encode(S, "Host", HOST)
    rows = [{"note": "clean-no-unknowns", "message": "Host", "wire": base.hex()}]

    # interleaved unknown (tag 3, between known 2 and 5) + a trailing unknown (tag 9)
    m = cbor.loads(base)
    m[3] = "interleaved"
    m[9] = 42
    rows.append({"note": "interleaved+trailing-unknown", "message": "Host", "wire": cbor.dumps(m).hex()})

    # a band-tag extension riding as residual to a host-only decoder
    m = cbor.loads(base)
    m[TAG] = codec.encode_struct(S, "Decision", DECISION)
    rows.append({"note": "band-tag-extension-as-residual", "message": "Host", "wire": cbor.dumps(m).hex()})

    # both at once
    m = cbor.loads(base)
    m[3] = "interleaved"
    m[TAG] = codec.encode_struct(S, "Decision", DECISION)
    rows.append({"note": "interleaved+band", "message": "Host", "wire": cbor.dumps(m).hex()})

    # self-check: every vector must round-trip byte-for-byte through the reference codec
    for r in rows:
        wire = bytes.fromhex(r["wire"])
        assert codec.encode(S, "Host", codec.decode(S, "Host", wire)) == wire, r["note"]
    return rows


def _ext_rows() -> list[dict]:
    host = codec.encode(S, "Host", HOST)
    dec_wire = codec.encode(S, "Decision", DECISION).hex()
    dec2_wire = codec.encode(S, "Decision", DECISION2).hex()
    strapped = ext.ext_set(S, host, "Decision", TAG, DECISION)
    replaced = ext.ext_set(S, strapped, "Decision", TAG, DECISION2)
    return [
        {"op": "set", "note": "attach", "host": host.hex(), "ext_message": "Decision",
         "tag": TAG, "value": dec_wire, "expect": strapped.hex()},
        {"op": "set", "note": "replace-existing", "host": strapped.hex(), "ext_message": "Decision",
         "tag": TAG, "value": dec2_wire, "expect": replaced.hex()},
        {"op": "get", "note": "read", "host": strapped.hex(), "ext_message": "Decision",
         "tag": TAG, "expect": dec_wire},
        {"op": "get", "note": "absent", "host": host.hex(), "ext_message": "Decision",
         "tag": TAG, "expect": "null"},
        {"op": "clear", "note": "strip", "host": strapped.hex(), "tag": TAG, "expect": host.hex()},
    ]


def residual_json() -> str:
    return json.dumps(_residual_rows(), indent=2) + "\n"


def ext_json() -> str:
    return json.dumps(_ext_rows(), indent=2) + "\n"


def main() -> None:
    RESIDUAL_PATH.write_text(residual_json())
    EXT_PATH.write_text(ext_json())
    print(f"wrote {len(_residual_rows())} residual + {len(_ext_rows())} ext vectors to {RESIDUAL_PATH.parent}")


if __name__ == "__main__":
    main()
