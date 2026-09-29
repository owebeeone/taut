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

`Names` catches generated code that clashes with a field's name, as a Java field `m`
clashes with `toCbor`'s local `m` (TautV010Plan.md §0). Its fields are named like the
locals, parameters and unqualified helpers the generators (`taut/gen/*.py`) emit in a
message's code:
  - every generator: the decoder's parameter `c`;
  - rust: `m`, `v`, `x`, `k`, `t`, `e`, `i`, `ek`, `ev`;
  - cpp: `to_cbor`'s parameter `b`, `v`, `f`, `x`, `k`, `e`, `kv`, and the forward-compat
    `to_cbor`'s unqualified call of the runtime's `encode_value`;
  - swift: `v`, and `fromCbor`'s unqualified call of the runtime's `decodeDictionary`;
  - go: the receiver `x`, `m`, `a`, `e`, `ks`, `k`, `i`, `j`, `v`, `fv`, `ok`, `err`,
    `arr`, `kc`, `vc`, `dup`, `entries`, `kv`;
  - kotlin: the lambda parameter `it`;
  - java: `m`, `v`, `f`, `e`, `kv`, and `java`, the root of the `java.util.List.of`
    that encodes a map;
  - js: the constructor's `o`, `m`, `v`, `f`, `e`, `k`, `a`, `b`, `key`, `kv`.
A scalar, a list and a map field are among them, with an optional and a MISSING_OK one.
None is a keyword in any of the nine languages (keywords are a separate concern), so
JS's `value` is left out as a Kotlin modifier keyword; `self`, `$0` and C++'s reserved
`__` names cannot be fields.

The last six serve the bounds rows B17-B30 (TautCheckedDecode.md CD-C1, §4.4): `Tree64`
and `Tree128`, trees declaring `max_depth` 64 and 128, the ceiling; `Flat2`, declaring
`max_depth` 2, its own non-recursive nesting; `Sized8`, declaring `max_encoded_len` 8; and
`Holds64` and `HoldsSized8`, which declare nothing and embed a `Tree64` and a `Sized8`, so
that a decode rooted at them applies their own bounds (TautOptions.md OPT-D4). The file
declares no bound, so these two and every other message resolve to the defaults: depth 32
and no length bound. tautc's lint warns, by design, that `Tree64`'s and `Sized8`'s bounds
cannot take effect inside the messages that embed them; a warning fails nothing.
"""

import sys
from pathlib import Path

# Make the taut builder importable when this file is loaded by path.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from taut.ir.dsl import (
    BOOL, BYTES, FLOAT, INT, MISSING_OK, STR, Enum, F, List, Map, Msg, Ref, option, schema,
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
    Msg("Names",
        F("m", 1, INT),
        F("b", 2, INT),
        F("c", 3, STR),
        F("v", 4, INT),
        F("o", 5, INT),
        F("f", 6, INT, optional=True),
        F("x", 7, INT),
        F("e", 8, List(INT)),
        F("k", 9, Map(STR, INT)),
        F("i", 10, INT),
        F("j", 11, INT),
        F("a", 12, INT),
        F("t", 13, INT),
        F("it", 14, INT),
        F("kv", 15, INT),
        F("fv", 16, INT, optional=MISSING_OK),
        F("ok", 17, INT),
        F("err", 18, INT),
        F("arr", 19, List(STR)),
        F("ks", 20, INT),
        F("kc", 21, INT),
        F("vc", 22, INT),
        F("ek", 23, INT),
        F("ev", 24, INT),
        F("key", 25, BOOL),
        F("dup", 26, INT),
        F("entries", 27, Map(INT, INT)),
        F("encode_value", 28, INT),
        F("java", 29, INT),
        F("decodeDictionary", 30, INT),
        next_id=31),
    Msg("Tree64", F("kids", 1, List(Ref("Tree64"))), option.max_depth(64), next_id=2),
    Msg("Tree128", F("kids", 1, List(Ref("Tree128"))), option.max_depth(128), next_id=2),
    Msg("Flat2", F("v", 1, List(INT)), option.max_depth(2), next_id=2),
    Msg("Sized8", F("b", 1, BYTES), option.max_encoded_len(8), next_id=2),
    Msg("Holds64", F("t", 1, Ref("Tree64")), next_id=2),
    Msg("HoldsSized8", F("s", 1, Ref("Sized8")), next_id=2),
)
