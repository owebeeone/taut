"""Go generator: native structs + typed-const enums + CBOR codec, forward-compat
residual, PascalCase exported fields. (go-build parity verified out-of-band.)"""

from taut.corpus.build import IR_PATH
from taut.gen import go
from taut.ir.load import load_schema

RAZEL = load_schema(IR_PATH.parent / "razel.taut.py")


def test_emits_structs_enums_and_codec():
    s = go.emit_types(RAZEL)
    assert "package taut" in s
    assert "type BuildResult struct {" in s
    assert "type BuildStatus int64" in s
    assert "BuildStatusBuilt BuildStatus = 1" in s
    assert "func (x BuildResult) ToCbor() Cbor {" in s
    assert "func BuildResultFromCbor(c Cbor) BuildResult {" in s


def test_fields_pascalcased_and_optional_is_pointer():
    s = go.emit_types(RAZEL)
    assert "Recomputes int64" in s   # recomputes -> Recomputes (exported)
    assert "Message *string" in s    # optional -> nil-able pointer


def test_forward_compat_adds_residual():
    s = go.emit_types(RAZEL, forward_compat=True)
    assert "WireResidual []KV" in s
    assert "append(m, x.WireResidual...)" in s          # re-emitted (Encode sorts)
    assert "WireResidual" not in go.emit_types(RAZEL)   # off by default
