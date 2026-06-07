"""Forward compat (unknown-field preservation, default-on) and declared
side-channel extensions."""

import pytest

from taut import ext
from taut.ir.dsl import INT, STR, F, Msg, extension, schema as mk_schema
from taut.ir.shapes import BAND_START
from taut.ir.validate import validate
from taut.wire import cbor, codec

S = mk_schema(
    Msg("Host", F("id", 1, INT), F("name", 2, STR)),
    Msg("Decision", F("backend", 1, STR), F("hops", 2, INT)),
    extension("Decision", tag=BAND_START + 1),
)


# --- unknown-field preservation ----------------------------------------------

def test_unknown_fields_round_trip():
    v = {"id": 1, "name": "ann"}
    blob = codec.encode(S, "Host", v)
    # a newer producer adds a field this schema doesn't know (tag 7)
    m = cbor.loads(blob)
    m[7] = "from-the-future"
    newer = cbor.dumps(m)

    decoded = codec.decode(S, "Host", newer)          # old schema decodes it
    assert decoded["id"] == 1 and decoded["name"] == "ann"
    assert decoded["__unknown__"] == {7: "from-the-future"}  # captured, not dropped

    reencoded = codec.encode(S, "Host", decoded)      # ...and re-emits it
    assert cbor.loads(reencoded)[7] == "from-the-future"


def test_clean_messages_have_no_unknown_key():
    decoded = codec.decode(S, "Host", codec.encode(S, "Host", {"id": 1, "name": "x"}))
    assert "__unknown__" not in decoded               # only present when there are unknowns


# --- extensions (side-channels) ----------------------------------------------

def test_ir_with_extension_validates():
    assert validate(S) == []


def test_attach_read_clear_without_host_schema_awareness():
    host = codec.encode(S, "Host", {"id": 1, "name": "ann"})
    tag = BAND_START + 1

    strapped = ext.ext_set(S, host, "Decision", tag, {"backend": "b7", "hops": 1})
    assert ext.ext_get(S, strapped, "Decision", tag) == {"backend": "b7", "hops": 1}

    # the host app decodes its own message, oblivious to the side-channel,
    # and preserves it (it rides in __unknown__)
    hv = codec.decode(S, "Host", strapped)
    assert hv["id"] == 1 and hv["name"] == "ann"
    assert tag in hv["__unknown__"]

    stripped = ext.ext_clear(strapped, tag)
    assert ext.ext_get(S, stripped, "Decision", tag) is None


# --- band partition ----------------------------------------------------------

def test_validator_enforces_the_band():
    app_in_band = mk_schema(Msg("M", F("x", BAND_START, STR)))
    assert any("extension band" in e for e in validate(app_in_band))

    ext_below_band = mk_schema(Msg("D", F("x", 1, STR)), extension("D", tag=5))
    assert any("below the band" in e for e in validate(ext_below_band))
