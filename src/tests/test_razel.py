"""razel.taut.py is a second, real customer contract (the razel build daemon's
surface). Beyond GripLab, it exercises the builder against an independently
authored IR: it validates, round-trips on the wire, and survives export/reload.
The authoritative working copy lives in the razel repo; this is the taut-side
conformance fixture."""

from taut.corpus.build import IR_PATH
from taut.ir.export import schema_json
from taut.ir.load import load_schema, schema_from_json
from taut.ir.validate import validate
from taut.wire import codec

RAZEL = IR_PATH.parent / "razel.taut.py"


def test_razel_validates():
    assert validate(load_schema(RAZEL)) == []


def test_razel_shape_surface():
    s = load_schema(RAZEL)
    methods = {m.name: m for m in s.services["Razel"].methods}
    assert set(methods) == {"build", "sync_file", "version", "affected", "build.subscribe"}
    # build.subscribe is the one streaming endpoint (atom); the rest are unary.
    assert methods["build.subscribe"].shape == "atom" and methods["build.subscribe"].streams()
    assert all(not methods[n].streams() for n in methods if n != "build.subscribe")


def test_razel_wire_roundtrips():
    s = load_schema(RAZEL)
    # enum + list-of-msg + optional present + bytes
    full = {"target": "//pkg:lib", "status": "built", "recomputes": 7,
            "outputs": [{"path": "out/lib.rlib", "digest": b"\xde\xad\xbe\xef"}],
            "message": "ok"}
    assert codec.decode(s, "BuildResult", codec.encode(s, "BuildResult", full)) == full
    # optional absent
    bare = {"target": "//y", "status": "failed", "recomputes": 0, "outputs": [], "message": None}
    assert codec.decode(s, "BuildResult", codec.encode(s, "BuildResult", bare)) == bare
    # the affected query result (lists of strings + messages)
    impact = {"sources": ["a.rs", "b.rs"],
              "targets": [{"label": "//x:bin", "kind": "binary"}],
              "tests": [{"label": "//x:test", "kind": "test"}]}
    assert codec.decode(s, "ImpactSet", codec.encode(s, "ImpactSet", impact)) == impact
    # the atom subscription payload
    state = {"revision": 42,
             "targets": [{"label": "//a", "kind": "library", "status": "cached",
                          "output_digest": b"\x01\x02"}]}
    assert codec.decode(s, "BuildState", codec.encode(s, "BuildState", state)) == state


def test_razel_export_reload_identity():
    s = load_schema(RAZEL)
    reloaded = schema_from_json(schema_json(s))
    assert validate(reloaded) == []
    assert set(reloaded.messages) == set(s.messages)
    assert set(reloaded.services) == set(s.services)
