"""The float conformance corpus — the language-agnostic oracle for Phase 2.

Each row pairs a double (by its 64-bit pattern) with the exact shortest-form CBOR
taut's canonical Python codec emits. Every target codec must reproduce `cbor` from
`f64`, and `decode -> re-encode` must be idempotent. The committed file stays in
lockstep with its generator (regen gate, like the golden corpus)."""

import json
import struct

from taut.corpus import float_build
from taut.wire import cbor


def _f(bits: str) -> float:
    return struct.unpack(">d", bytes.fromhex(bits))[0]


def test_committed_corpus_matches_generator():
    assert float_build.OUT_PATH.read_text() == float_build.corpus_json(), \
        "corpus/float_vectors.json is stale — run `python -m taut.corpus.float_build`"


def test_corpus_rows_encode_and_reencode():
    rows = json.loads(float_build.OUT_PATH.read_text())
    assert rows, "empty float corpus"
    for row in rows:
        # bits -> shortest-form CBOR (exercises narrow16/narrow32 + canonical NaN)
        assert cbor.dumps(_f(row["f64"])).hex() == row["cbor"], row["note"]
        # decode -> re-encode parity (handles NaN without bit-comparing)
        reenc = cbor.dumps(cbor.loads(bytes.fromhex(row["cbor"]))).hex()
        assert reenc == row["cbor"], row["note"]
        # decode -> exact f64 bits (finite/inf widen losslessly; NaN payloads don't)
        if not row["note"].startswith("nan"):
            got = struct.pack(">d", cbor.loads(bytes.fromhex(row["cbor"])))
            assert got == bytes.fromhex(row["f64"]), row["note"]


def test_corpus_covers_all_widths_and_specials():
    rows = json.loads(float_build.OUT_PATH.read_text())
    heads = {row["cbor"][:2] for row in rows}
    assert {"f9", "fa", "fb"} <= heads                       # half, single, double all present
    assert any(r["cbor"] == "f97e00" for r in rows)          # canonical NaN
    assert any(r["note"] == "neg-zero" and r["f64"] == "8000000000000000" for r in rows)
    # every distinct NaN payload row canonicalises to the same bytes
    assert {r["cbor"] for r in rows if r["note"].startswith("nan")} == {"f97e00"}
