"""Forward compat (unknown-field preservation, default-on) and declared
side-channel extensions."""

import pytest

from taut import ext
from taut.gen import scaffold
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


# --- cross-version conformance: an old struct must preserve a newer field -----

def test_cross_version_preserves_unknown_field_byte_for_byte():
    # v2 knows field id 2; v1 doesn't. v1 must carry it through unchanged.
    v2 = mk_schema(Msg("M", F("f1", 1, INT), F("f2", 2, INT), F("f3", 3, INT)))
    v1 = mk_schema(Msg("M", F("f1", 1, INT), F("f3", 3, INT)))   # missing tag 2

    cbor1 = codec.encode(v2, "M", {"f1": 1, "f2": 2, "f3": 3})
    m1 = codec.decode(v1, "M", cbor1)                  # v1 reads v2's bytes
    assert m1["f1"] == 1 and m1["f3"] == 3
    assert m1["__unknown__"] == {2: 2}                 # f2 captured as residual
    cbor2 = codec.encode(v1, "M", m1)                  # v1 re-emits
    assert cbor2 == cbor1                              # nothing lost: byte-identical

    # mutate a known field in both; v1 (carrying f2 as residual) matches v2 exactly
    m1["f3"] = 7
    assert codec.encode(v1, "M", m1) == codec.encode(v2, "M", {"f1": 1, "f2": 2, "f3": 7})


# --- generator-side forward-compat (Rust) + the gates ------------------------

def test_wire_prefix_is_reserved():
    errs = validate(mk_schema(Msg("M", F("wire_residual", 1, INT))))
    assert any("wire_" in e for e in errs)


def test_rust_forward_compat_emits_residual_field():
    rs = scaffold.rust_api(S, forward_compat=True)
    assert "pub wire_residual: Vec<(i64, Cbor)>" in rs
    assert "map_entries()" in rs
    # off by default
    assert "wire_residual" not in scaffold.rust_api(S)


def test_extensions_require_forward_compat_for_rust(tmp_path):
    # S declares an extension -> generating Rust without forward-compat is an error
    with pytest.raises(ValueError):
        scaffold.emit(S, tmp_path, langs=["rust"], services=[])
    scaffold.emit(S, tmp_path, langs=["rust"], services=[], forward_compat=True)  # ok with the flag


def test_cpp_forward_compat_emits_residual():
    hpp = scaffold.cpp_api(S, forward_compat=True)
    assert "std::vector<std::pair<long long, Cbor>> wire_residual;" in hpp
    assert "encode_value(b" in hpp                       # residual re-emitted
    assert "wire_residual" not in scaffold.cpp_api(S)    # off by default


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
