"""ResExt parity fixture — the shared Phase-1 oracle schema for residual + extension
conformance (one host message, one extension message, one band-tag extension).

`Host`'s tags are deliberately non-contiguous (1, 2, 5) so a residual unknown can land
*between* two known tags — the interleave that is the #1 byte trap for the ports."""

import sys
from pathlib import Path

# Make the taut builder importable when this file is loaded by path.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from taut.ir.dsl import INT, STR, F, Msg, extension, schema
from taut.ir.shapes import BAND_START

SCHEMA = schema(
    Msg("Host",
        F("id", 1, INT),
        F("name", 2, STR),
        F("score", 5, INT)),               # gap at 3, 4 → residual unknowns interleave
    Msg("Decision",                         # the extension message (rides at a band tag)
        F("backend", 1, STR),
        F("hops", 2, INT)),
    extension("Decision", tag=BAND_START + 1),
)
