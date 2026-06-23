"""Conformance corpus for the shortest-form float wire profile (RFC 8949 §4.2.1).

A language-agnostic oracle: each row is a double (by its 64-bit pattern) and the
exact CBOR bytes taut's canonical (Python) codec emits for it. Every target's
codec must reproduce `cbor` from `f64`, and re-encode `decode(cbor)` to `cbor`.

Curated to exercise the tricky parts each language hand-rolls: half/single/double
width selection (incl. subnormals + max-of-width boundaries), a near-miss that
must NOT shrink, -0.0 preservation, ±Inf, and NaN-payload canonicalisation.

Generated — do not hand-edit corpus/float_vectors.json; run this module."""

from __future__ import annotations

import json
import struct
from pathlib import Path

from ..wire import cbor

OUT_PATH = Path(__file__).resolve().parents[3] / "corpus" / "float_vectors.json"


def _bits(value: float) -> str:
    return struct.pack(">d", value).hex()


def _from_bits(hex16: str) -> float:
    return struct.unpack(">d", bytes.fromhex(hex16))[0]


# Finite + infinite cases, given as doubles. Notes name the expected width/edge.
_FINITE: list[tuple[str, float]] = [
    ("zero", 0.0), ("neg-zero", -0.0),
    ("one", 1.0), ("neg-one", -1.0), ("one-and-half", 1.5),
    ("half-min-subnormal", 2.0 ** -24), ("half-min-normal", 2.0 ** -14),
    ("half-max", 65504.0),
    ("near-miss-not-half-exact-single", 1.00048828125),
    ("single-100000", 100000.0), ("single-max", 3.4028234663852886e+38),
    ("single-min-subnormal", 2.0 ** -149),
    ("double-tenth", 0.1), ("double-1.1", 1.1), ("double-pi", 3.141592653589793),
    ("double-min-subnormal", 5e-324), ("double-max", 1.7976931348623157e+308),
    ("pos-inf", float("inf")), ("neg-inf", float("-inf")),
]

# NaN payloads carried as raw bits (not via a Python float, which may normalise
# the payload) — each must canonicalise to F9 7E00 on encode.
_NAN_BITS: list[tuple[str, str]] = [
    ("nan-quiet-canonical", "7ff8000000000000"),
    ("nan-signaling", "7ff0000000000001"),
    ("nan-neg-payload", "fff8000000000000"),
]


def build() -> list[dict]:
    rows = [{"note": note, "f64": _bits(v), "cbor": cbor.dumps(v).hex()} for note, v in _FINITE]
    rows += [{"note": note, "f64": bits, "cbor": cbor.dumps(_from_bits(bits)).hex()}
             for note, bits in _NAN_BITS]
    return rows


def corpus_json() -> str:
    """The neutral, language-agnostic oracle file (stable: preserve curated order)."""
    return json.dumps(build(), indent=2) + "\n"


def main() -> None:
    OUT_PATH.write_text(corpus_json())
    print(f"wrote {len(build())} float vectors to {OUT_PATH}")


if __name__ == "__main__":
    main()
