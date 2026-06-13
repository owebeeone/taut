"""Glade chain-hash conformance (GLP-0005, P1.S4). The op-hash oracle pins the
sha256-over-canonical-CBOR step; the Rust node + TS client reproduce it. The
chain-linking invariant (each op's prev = predecessor's hash) is verified here."""

import json

from taut.crdt.glade_chain import HASHES_PATH, IR_PATH, build_chain, op_hash, vectors
from taut.ir.load import load_schema


def test_oracle_reproducible():
    schema = load_schema(IR_PATH)
    committed = json.loads(HASHES_PATH.read_text())
    recomputed = vectors(schema)
    assert committed == recomputed, "glade_hashes.json out of date — rerun glade_chain"


def test_chain_links_predecessor_hash():
    schema = load_schema(IR_PATH)
    chain = build_chain(schema, "a", 4)
    assert chain[0]["prev"] is None  # baseline
    for i in range(1, len(chain)):
        assert chain[i]["prev"] == op_hash(schema, chain[i - 1]), f"broken link at {i}"


def test_equivocation_forks_hash():
    schema = load_schema(IR_PATH)
    chain = build_chain(schema, "a", 1)
    fork = {**chain[0], "payload": b"different"}
    assert op_hash(schema, fork) != op_hash(schema, chain[0])  # same (origin,seq), diff hash


def test_hash_is_32_bytes():
    schema = load_schema(IR_PATH)
    chain = build_chain(schema, "a", 1)
    assert len(op_hash(schema, chain[0])) == 32
