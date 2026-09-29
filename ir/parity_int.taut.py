"""Codec parity fixture for the i64 integer contract.

Small on purpose: one scalar int, one schema-level map<int,int>, and one enum for
unknown-enum malformed vectors. Schema-level map keys are ordinary taut ints; raw
CBOR map-key overflow is tested separately in malformed vectors.

`OptBox` and `Empty` serve the schema-stage malformed rows M9-M12 and M15
(TautCheckedDecode.md CD-C1): an optional text field beside a list, and a message
with no fields, which must still be a map.
"""

import sys
from pathlib import Path

# Make the taut builder importable when this file is loaded by path.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from taut.ir.dsl import INT, STR, Enum, F, List, Map, Msg, Ref, schema

SCHEMA = schema(
    Enum("Mode", ok=0, alt=1),
    Msg("IntBox",
        F("n", 1, INT),
        F("by_id", 2, Map(INT, INT)),
        next_id=3),
    Msg("EnumBox",
        F("mode", 1, Ref("Mode")),
        next_id=2),
    Msg("OptBox",
        F("note", 1, STR, optional=True),
        F("tags", 2, List(STR)),
        next_id=3),
    Msg("Empty",
        next_id=1),
)
