"""Residual + extension conformance corpora — the Phase-2 fork oracle.

The committed corpora are dumps of the Python reference (codec `__unknown__` + `ext.py`)
over a shared fixture schema; every language target must reproduce these exact bytes.
Parse-free: raw CBOR hex in/out. Committed files stay in lockstep with the generator."""

import json

import pytest

from taut import ext
from taut.corpus import resext_build as rb
from taut.ir.load import load_schema
from taut.wire import cbor, codec

S = load_schema(rb.IR_PATH)


# --- lockstep gates (committed == generated) ---------------------------------

def test_committed_residual_corpus_matches_generator():
    assert rb.RESIDUAL_PATH.read_text() == rb.residual_json(), \
        "residual_vectors.json is stale — run `python -m taut.corpus.resext_build`"


def test_committed_ext_corpus_matches_generator():
    assert rb.EXT_PATH.read_text() == rb.ext_json(), \
        "ext_vectors.json is stale — run `python -m taut.corpus.resext_build`"


# --- A. residual: decode -> re-encode is byte-identical -----------------------

def test_residual_round_trips_byte_for_byte():
    rows = json.loads(rb.RESIDUAL_PATH.read_text())
    assert rows
    for r in rows:
        decoded = codec.decode(S, r["message"], bytes.fromhex(r["wire"]))
        assert codec.encode(S, r["message"], decoded).hex() == r["wire"], r["note"]


def test_residual_corpus_exercises_interleave_and_band():
    notes = {r["note"] for r in json.loads(rb.RESIDUAL_PATH.read_text())}
    assert any("interleaved" in n for n in notes)     # unknown tag between two known tags
    assert any("band" in n for n in notes)            # band-tag extension riding as residual


# --- B. extensions: ext_set / ext_get / ext_clear vs the Python oracle --------

def test_ext_ops_match_python_oracle():
    rows = json.loads(rb.EXT_PATH.read_text())
    assert rows
    for r in rows:
        host = bytes.fromhex(r["host"])
        if r["op"] == "set":
            value = codec.decode(S, r["ext_message"], bytes.fromhex(r["value"]))
            assert ext.ext_set(S, host, r["ext_message"], r["tag"], value).hex() == r["expect"], r["note"]
        elif r["op"] == "get":
            got = ext.ext_get(S, host, r["ext_message"], r["tag"])
            if r["expect"] == "null":
                assert got is None, r["note"]
            else:
                assert codec.encode(S, r["ext_message"], got).hex() == r["expect"], r["note"]
        elif r["op"] == "clear":
            assert ext.ext_clear(host, r["tag"]).hex() == r["expect"], r["note"]
        else:
            pytest.fail(f"unknown op {r['op']}")


# --- C. scaffold ext.<lang> runtime slot (wired in Phase 1; filled in Phase 2) -

def test_scaffold_registers_ext_runtime_slot():
    from taut.gen import scaffold
    for lang, files in scaffold._RUNTIMES.items():
        resources = [res for _, res in files]
        assert any(r == "Ext.java" or r.lower().startswith("ext.") for r in resources), \
            f"{lang} has no ext.<lang> runtime slot"


def test_emit_vendors_cbor_and_tolerates_missing_ext(tmp_path):
    from taut.gen import scaffold
    written = scaffold.emit(S, tmp_path, langs=["rust"], services=[], runtime=True, forward_compat=True)
    names = {p.name for p in written}
    assert "cbor.rs" in names              # cbor still vendored
    assert "ext.rs" not in names           # not present yet → skipped cleanly (Phase 2 drops it in)
