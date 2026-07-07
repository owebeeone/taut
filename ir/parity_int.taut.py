"""Codec parity fixture for the i64 integer contract.

Small on purpose: one scalar int, one schema-level map<int,int>, and one enum for
unknown-enum malformed vectors. Schema-level map keys are ordinary taut ints; raw
CBOR map-key overflow is tested separately in malformed vectors.
"""

import sys
from pathlib import Path

# Make the taut builder importable when this file is loaded by path.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from taut.ir.dsl import INT, Enum, F, Map, Msg, Ref, schema

SCHEMA = schema(
    Enum("Mode", ok=0, alt=1),
    Msg("IntBox",
        F("n", 1, INT),
        F("by_id", 2, Map(INT, INT)),
        next_id=3),
    Msg("EnumBox",
        F("mode", 1, Ref("Mode")),
        next_id=2),
)
