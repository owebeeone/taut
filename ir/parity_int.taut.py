"""Codec parity fixture for the i64 integer contract.

Small on purpose: one scalar int, one schema-level map<int,int>, and one enum for
unknown-enum malformed vectors. Schema-level map keys are ordinary taut ints; raw
CBOR map-key overflow is tested separately in malformed vectors.

`OptBox` and `Empty` serve the schema-stage malformed rows M9-M12 and M15
(TautCheckedDecode.md CD-C1): an optional text field beside a list, and a message
with no fields, which must still be a map.

`Late` serves M16 and M17 (CD-C1, rev3): its one field is `optional=MISSING_OK`, so
an absent key decodes to null and a present value of the wrong type is still refused.

`Shapes` covers the legal field shapes (`taut/ir/validate.py`) in one message, so
every generator must generate and compile each of them and the gate's accept rows
decode and re-encode them: the five scalars, an enum and a message field, the same
three optional, `list<int>`, `list<EnumBox>` and `list<list<int>>`, `map<str,int>`,
`map<bool,Mode>` and `map<int,EnumBox>`, an optional list and an optional map, and a
`str` with `optional=MISSING_OK`. A map key is int, str or bool, a map value is never
a list or map, lists nest, and any field may be optional.
"""

import sys
from pathlib import Path

# Make the taut builder importable when this file is loaded by path.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from taut.ir.dsl import (
    BOOL, BYTES, FLOAT, INT, MISSING_OK, STR, Enum, F, List, Map, Msg, Ref, schema,
)

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
    Msg("Late",
        note=F(1, STR, optional=MISSING_OK),
        next_id=2),
    Msg("Shapes",
        F("count", 1, INT),
        F("ratio", 2, FLOAT),
        F("label", 3, STR),
        F("blob", 4, BYTES),
        F("flag", 5, BOOL),
        F("mode", 6, Ref("Mode")),
        F("boxed", 7, Ref("EnumBox")),
        F("maybe_count", 8, INT, optional=True),
        F("maybe_mode", 9, Ref("Mode"), optional=True),
        F("maybe_boxed", 10, Ref("EnumBox"), optional=True),
        F("numbers", 11, List(INT)),
        F("boxes", 12, List(Ref("EnumBox"))),
        F("grid", 13, List(List(INT))),
        F("tally", 14, Map(STR, INT)),
        F("mode_by_flag", 15, Map(BOOL, Ref("Mode"))),
        F("box_by_id", 16, Map(INT, Ref("EnumBox"))),
        F("maybe_numbers", 17, List(INT), optional=True),
        F("maybe_tally", 18, Map(STR, INT), optional=True),
        F("late_note", 19, STR, optional=MISSING_OK),
        next_id=20),
)
