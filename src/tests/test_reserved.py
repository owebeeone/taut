"""`reserved` and `next_id` as first-class IR features: the validator enforces
them; the breaking-change gate treats un-reserving as breaking."""

from taut.ir import compat
from taut.ir.dsl import INT, STR, F, Msg, schema
from taut.ir.export import schema_json
from taut.ir.load import schema_from_json
from taut.ir.validate import validate


def test_reserved_tag_and_name_rejected():
    s = schema(Msg("A", F("x", 1, STR), F("old", 2, INT), reserved=[2, "old"]))
    errs = validate(s)
    assert any("uses reserved tag 2" in e for e in errs)
    assert any("uses reserved name 'old'" in e for e in errs)


def test_reserved_clean_message_validates():
    # tag 3 + name "priority" retired; current fields avoid them
    s = schema(Msg("A", F("x", 1, STR), F("y", 2, INT), reserved=[3, "priority"], next_id=4))
    assert validate(s) == []


def test_next_id_must_exceed_all_tags():
    too_low = schema(Msg("A", F("x", 1, STR), F("y", 2, INT), next_id=2))
    assert any("tag 2 >= next_id 2" in e for e in validate(too_low))
    # reserved tag must also be below next_id
    reserved_high = schema(Msg("A", F("x", 1, STR), reserved=[5], next_id=3))
    assert any("tag 5 >= next_id 3" in e for e in validate(reserved_high))


def test_round_trips_through_json():
    s = schema(Msg("A", F("x", 1, STR), reserved=[3, "old"], next_id=5))
    assert schema_from_json(schema_json(s)) == s


def test_un_reserving_is_breaking_reserving_is_compatible():
    old = schema(Msg("A", F("x", 1, STR), reserved=[3]))
    un = schema(Msg("A", F("x", 1, STR)))                      # dropped the reservation
    more = schema(Msg("A", F("x", 1, STR), reserved=[3, 4]))   # added one
    assert any("tag 3 un-reserved" in c.detail for c in compat.breaking(old, un))
    assert compat.breaking(old, more) == []
    assert any("tag 4 reserved" in c.detail for c in compat.diff(old, more))
