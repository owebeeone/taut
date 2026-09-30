"""Go generator: native structs + typed-const enums + CBOR codec, forward-compat
residual, PascalCase exported fields. The shared parity corpus replays through the
gate's Go runner (`taut.corpus.parity_go`)."""

import copy
import os
import json
import random
import re
from pathlib import Path
import shutil
import subprocess
import textwrap

import pytest

from taut import ext
from taut.corpus.build import IR_PATH
from taut.corpus import parity, parity_go, toolchains
from taut.corpus import resext_build as resext
from taut.gen import go
from taut.gen import scaffold
from taut.ir.dsl import BOOL, BYTES, FLOAT, INT, MISSING_OK, STR, Enum, F, List, Map, Msg, Ref, option, schema as mk
from taut.ir.load import load_schema
from taut.ir.model import EnumRef, ListOf, MapOf, MsgRef, Scalar
from taut.ir.options import effective
from taut.ir.shapes import BAND_START
from taut.ir.validate import validate
from taut.wire import cbor, codec

ROOT = Path(__file__).resolve().parents[2]
IR_FILES = sorted((ROOT / "ir").glob("*.taut.py"))
RAZEL = load_schema(IR_PATH.parent / "razel.taut.py")
RESEXT = load_schema(resext.IR_PATH)
FLOAT_SCHEMA = mk(Msg("FloatMsg",
                      F("x", 1, FLOAT),
                      F("xs", 2, List(FLOAT)),
                      F("by_id", 3, Map(INT, FLOAT)),
                      F("maybe", 4, FLOAT, optional=True)))


def _go_test_env(tmp_path: Path) -> dict[str, str]:
    go_cache = tmp_path / "gocache"
    go_tmp = tmp_path / "gotmp"
    go_cache.mkdir(exist_ok=True)
    go_tmp.mkdir(exist_ok=True)
    env = os.environ.copy()
    env["GO111MODULE"] = "off"
    env["GOCACHE"] = str(go_cache)
    env["GOTMPDIR"] = str(go_tmp)
    return env


def _struct_fields(src: str, name: str) -> dict[str, str]:
    """A generated struct's fields, name -> Go type, whatever gofmt's column alignment."""
    body = src[src.index(f"type {name} struct {{\n") + len(f"type {name} struct {{\n"):]
    return dict(line.split() for line in body[:body.index("}\n")].splitlines())


def test_emits_structs_enums_and_codec():
    s = go.emit_types(RAZEL)
    assert "package taut" in s
    assert "type BuildResult struct {" in s
    assert "type BuildStatus int64" in s
    assert re.search(r"\n\tBuildStatusBuilt +BuildStatus = 1\n", s)
    assert "func (x BuildResult) ToCbor() Cbor {" in s
    assert "func TryBuildResultFromCbor(c Cbor) (BuildResult, error) {" in s
    assert "func TryBuildStatusFromWire(v int64) (BuildStatus, error) {" in s
    assert "func TryBuildStatusFromCbor(c Cbor) (BuildStatus, error) {" in s


RUNTIME = ROOT / "src" / "taut" / "gen" / "runtime"


def test_no_panicking_decode_entry_point_survives():
    """Question 5 and CD-E4: every decode entry point returns `(value, error)`. Generated Go
    has only `TryXFromBytes`, `TryXFromCbor` and `TryXFromWire`, and neither it nor the
    runtime it vendors (`cbor.go`, `ext.go`) panics: the runtime's `Decode` and `Get` are
    gone, and its raw decode takes the caller's bounds."""
    entry_points = []
    for name, source in _generated_go().items():
        assert "panic(" not in source, name
        entry_points += re.findall(r"^func (\w+?)From(?:Bytes|Cbor|Wire)\(", source, re.M)
    assert entry_points and all(e.startswith("Try") for e in entry_points), sorted(set(entry_points))
    for rel, _ in scaffold._RUNTIMES["go"]:
        source = (RUNTIME / rel).read_text()
        assert "panic(" not in source, rel
    cbor_go = (RUNTIME / "cbor.go").read_text()
    assert "func Decode(" not in cbor_go and ") Get(" not in cbor_go
    assert "func TryDecode(data []byte) (Cbor, error) {" in cbor_go
    assert "func TryDecodeWith(data []byte, maxDepth int, maxEncodedLen int) (Cbor, error) {" in cbor_go


def test_fields_pascalcased_and_optional_is_pointer():
    fields = _struct_fields(go.emit_types(RAZEL), "BuildResult")
    assert fields["Recomputes"] == "int64"   # recomputes -> Recomputes (exported)
    assert fields["Message"] == "*string"    # optional -> nil-able pointer


def test_optional_list_and_map_are_pointers_like_every_optional_field():
    """An optional `T` is `*T` whatever `T` is: nil is null, and a pointer to an empty (or
    nil) slice or map is the empty array. Lists nest as slices of slices."""
    fields = _struct_fields(go.emit_types(parity.parity_schema()), "Shapes")
    assert fields["MaybeNumbers"] == "*[]int64"
    assert fields["MaybeTally"] == "*map[string]int64"
    assert (fields["MaybeCount"], fields["MaybeBoxed"], fields["LateNote"]) == ("*int64", "*EnumBox", "*string")
    assert (fields["Numbers"], fields["Grid"], fields["Tally"]) == ("[]int64", "[][]int64", "map[string]int64")


def test_forward_compat_adds_residual():
    s = go.emit_types(RAZEL, forward_compat=True)
    assert "WireResidual []KV" in s
    assert "append(m, x.WireResidual...)" in s          # re-emitted (Encode sorts)
    assert "WireResidual" not in go.emit_types(RAZEL)   # off by default


def test_float_scalar_codegen():
    s = go.emit_types(FLOAT_SCHEMA)
    assert _struct_fields(s, "FloatMsg") == {
        "X": "float64", "Xs": "[]float64", "ById": "map[int64]float64", "Maybe": "*float64"}
    assert "CFloat(x.X)" in s
    assert "a = append(a, CFloat(e))" in s
    assert "V: CFloat(x.ById[k])" in s
    assert "x, err := fv.TryFloat()" in s
    assert "v.X = x" in s
    assert "v.Maybe = &x" in s


def test_go_runtime_float_harness(tmp_path):
    if shutil.which("go") is None:
        pytest.skip("go not installed")

    env = _go_test_env(tmp_path)
    result = subprocess.run(
        ["go", "test", "./src/taut/gen/runtime"],
        cwd=ROOT,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    assert result.returncode == 0, result.stdout


# The runtime's own bounds tests (cbor_bounds_test.go, beside cbor.go): the raw decoder's
# contract as test_cbor.py pins Python's, and the extension helpers' host bounds.
BOUNDS_TESTS = (
    "TestBoundsConstants",
    "TestBoundsDefaultDepthTakes32ContainersAndRefusesThe33rd",
    "TestBoundsArraysAndMapsCountAlike",
    "TestBoundsATopLevelContainerHasDepth1",
    "TestBoundsAMapKeyIsAnItemOfItsMap",
    "TestBoundsADepthArgumentAppliesAsGiven",
    "TestBoundsADepthArgumentAboveTheCeilingAppliesTheCeiling",
    "TestBoundsDepthIsCheckedOnceTheHeadIsComplete",
    "TestBoundsDeepInputIsTooDeepAndNothingEscapes",
    "TestBoundsLength",
    "TestBoundsLengthIsCheckedBeforeAnyByteIsRead",
    "TestBoundsAZeroLengthBound",
    "TestBoundsADepthBelow1IsACallerError",
    "TestBoundsErrorTextNamesThePayload",
    "TestBoundsAHostIsReadAtTheDepthCeiling",
    "TestBoundsAHostIsReadWithNoLengthBound",
)


def test_go_runtime_bounds_harness(tmp_path):
    """D26's bounds in the Go runtime (TautCheckedDecode.md §3, CD-E5): TryDecode's default
    depth, TryDecodeWith's caller bounds, 100,000 and 1,000,000 deep refused without a stack
    overflow or a panic, and the extension helpers' host read at the ceiling with no length
    bound (TautOptions.md G3). Each test must run and pass."""
    _needs_go()
    result = subprocess.run(["go", "test", "-v", "-run", "^TestBounds", "./src/taut/gen/runtime"],
                            cwd=ROOT, env=_go_test_env(tmp_path), text=True, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, check=False)
    assert result.returncode == 0, result.stdout
    ran = set(re.findall(r"^--- PASS: (\w+)", result.stdout, re.M))
    assert ran == set(BOUNDS_TESTS), result.stdout


def _needs_go() -> None:
    if toolchains.find_go() is None:
        pytest.skip("go not installed")


def _failures(report: parity.TargetReport) -> str:
    return "\n".join([report.fault, *(f"{r.name}: {r.detail}" for r in report.failures)])


def test_go_parity_gate_is_green():
    """`tautc parity -t go`: every int, malformed and bounds row through the generated Go
    codec, as go and go/fc, each held to the gate's governance: GREEN, or RED and
    allowlisted."""
    _needs_go()
    reports, violations = parity.governed_variants(parity_go.run)
    assert violations == [], "\n".join(violations)
    encode_fail = {r["name"] for r in parity.int_rows() if r["kind"] == "encode_fail"}
    for report in reports:
        if not report.fault:
            satisfied = {r.name for r in report.results if r.status == parity.TYPE_SATISFIED}
            assert satisfied == encode_fail, report.target


def _const(src: str, name: str) -> int:
    """The value of the generated constant `name`, whatever gofmt's column alignment."""
    found = re.findall(rf"^\t{name} += (-?\d+)$", src, re.M)
    assert len(found) == 1, (name, found)
    return int(found[0])


def _typed_decode(name: str) -> str:
    """The generated decode from bytes of message `name`: its bounds, then the schema stage."""
    return (f"func Try{name}FromBytes(data []byte) ({name}, error) {{\n"
            f"\tc, err := TryDecodeWith(data, {name}MaxDepth, {name}MaxEncodedLen)\n"
            "\tif err != nil {\n"
            f"\t\treturn {name}{{}}, err\n"
            "\t}\n"
            f"\treturn Try{name}FromCbor(c)\n"
            "}\n")


@pytest.mark.parametrize("forward_compat", [False, True])
def test_every_message_has_its_bounds_and_a_typed_decode(forward_compat):
    """CD-B3, OPT-L6: each message's effective bounds as constants, taken from
    `options.effective` at generation time (-1 for no length bound), and a decode from bytes,
    `TryXFromBytes`, that applies both. The fixture's six bounds messages resolve as CD-C1 says."""
    schema = parity.parity_schema()
    src = go.emit_types(schema, forward_compat=forward_compat)
    for name in schema.messages:
        length = effective(schema, "max_encoded_len", message=name)
        assert _const(src, f"{name}MaxDepth") == effective(schema, "max_depth", message=name), name
        assert _const(src, f"{name}MaxEncodedLen") == (-1 if length is None else length), name
        assert _typed_decode(name) in src, name
    assert {name: (_const(src, f"{name}MaxDepth"), _const(src, f"{name}MaxEncodedLen")) for name in (
        "Tree64", "Tree128", "Flat2", "Sized8", "Holds64", "HoldsSized8", "IntBox")} == {
        "Tree64": (64, -1), "Tree128": (128, -1), "Flat2": (2, -1), "Sized8": (32, 8),
        "Holds64": (32, -1), "HoldsSized8": (32, -1), "IntBox": (32, -1)}


# A file that declares both bounds, a message that overrides one, and one that inherits both
# (test_bounds.py's FILED): the generated constants resolve as `options.effective` does.
FILED = mk(option.max_depth(3), option.max_encoded_len(16),
           Msg("Tree", F("kids", 1, List(Ref("Tree"))), option.max_depth(64), next_id=2),
           Msg("Plain", F("v", 1, List(INT)), next_id=2))


def test_a_file_level_bound_reaches_each_message_that_declares_none():
    src = go.emit_types(FILED)
    assert (_const(src, "TreeMaxDepth"), _const(src, "TreeMaxEncodedLen")) == (64, 16)
    assert (_const(src, "PlainMaxDepth"), _const(src, "PlainMaxEncodedLen")) == (3, 16)


def test_go_typed_decode_applies_its_messages_bounds(tmp_path):
    """The generated `TryXFromBytes` at run time, on FILED: a message root applies its own bounds, a
    declared depth and an inherited length (test_bounds.py's twin), and the two-step reader,
    TryDecode then TryXFromCbor, only the raw defaults (TautOptions.md G1)."""
    _needs_go()
    scaffold.emit(FILED, tmp_path, langs=["go"], services=[], runtime=True)
    go_dir = tmp_path / "go"
    (go_dir / "filed_test.go").write_text(textwrap.dedent("""
        package taut

        import (
            "encoding/hex"
            "strings"
            "testing"
        )

        func filedHex(t *testing.T, input string) []byte {
            t.Helper()
            data, err := hex.DecodeString(input)
            if err != nil {
                t.Fatalf("bad hex %q: %v", input, err)
            }
            return data
        }

        func wantRefusal(t *testing.T, input string, err error, want DecodeError) {
            t.Helper()
            got, ok := err.(*DecodeError)
            if !ok || *got != want {
                t.Fatalf("%.40s: got %T %v, want %#v", input, err, err, want)
            }
        }

        func TestFiledTreeAppliesItsOwnDepth(t *testing.T) {
            trees := "a10181" + "a10180" // Tree{[Tree{[]}]}: depth 4, beyond the file's 3
            tree, err := TryTreeFromBytes(filedHex(t, trees))
            if err != nil || len(tree.Kids) != 1 || len(tree.Kids[0].Kids) != 0 {
                t.Fatalf("%+v, %v", tree, err)
            }
        }

        func TestFiledPlainAppliesTheFilesBounds(t *testing.T) {
            deep := "a10181818100" // depth 4, refused before WrongType{int}
            _, err := TryPlainFromBytes(filedHex(t, deep))
            wantRefusal(t, deep, err, DecodeError{Tag: DecodeErrTooDeep, Limit: 3})
            atLen := "a1018d" + strings.Repeat("00", 13) // 16 bytes
            plain, err := TryPlainFromBytes(filedHex(t, atLen))
            if err != nil || len(plain.V) != 13 {
                t.Fatalf("%+v, %v", plain, err)
            }
            overLen := "a1018e" + strings.Repeat("00", 14) // 17 bytes
            _, err = TryPlainFromBytes(filedHex(t, overLen))
            wantRefusal(t, overLen, err, DecodeError{Tag: DecodeErrTooLarge, Len: 17, Limit: 16})
            _, err = TryTreeFromBytes(filedHex(t, overLen))
            wantRefusal(t, overLen, err, DecodeError{Tag: DecodeErrTooLarge, Len: 17, Limit: 16})
        }

        func TestFiledTwoStepReaderAppliesOnlyTheRawDefaults(t *testing.T) {
            deep := strings.Repeat("a10181", 11) + "a10180" // depth 24: past 3, within 32
            c, err := TryDecode(filedHex(t, deep))
            if err != nil {
                t.Fatal(err)
            }
            _, err = TryPlainFromCbor(c) // the schema stage, not the file's depth, refuses it
            wantRefusal(t, deep, err, DecodeError{Tag: DecodeErrWrongType, Expected: "int"})
            overLen := "a1018e" + strings.Repeat("00", 14)
            c, err = TryDecode(filedHex(t, overLen))
            if err != nil {
                t.Fatalf("the raw default has no length bound: %v", err)
            }
            if plain, err := TryPlainFromCbor(c); err != nil || len(plain.V) != 14 {
                t.Fatalf("%+v, %v", plain, err)
            }
        }
    """))
    _run_go_tests(go_dir, tmp_path, "TestFiledTreeAppliesItsOwnDepth",
                  "TestFiledPlainAppliesTheFilesBounds", "TestFiledTwoStepReaderAppliesOnlyTheRawDefaults")


def test_go_runner_reports_an_expansion_whose_length_is_not_len_as_untyped(monkeypatch):
    """The bounds protocol, item 5: the runner expands a row's segments itself and reports an
    expansion whose length is not the row's `len` as untyped, a raw row and a typed one alike."""
    _needs_go()
    torn = {"depth-100000-arrays", "len-8-declared"}
    rows = [{**row, "len": row["len"] + 1} if row["name"] in torn else row for row in parity.bounds_rows()]
    monkeypatch.setattr(parity, "bounds_rows", lambda: rows)
    report = parity_go.run()
    assert not report.fault, report.fault
    assert {r.name: r.detail.split(" ")[0] for r in report.failures} == {name: "untyped" for name in torn}


# Raw inputs beyond the corpus, each with what CD-E5 says of it. Python, the reference,
# must say the same; then Go must match Python through the gate's own runner and judge.
RAW_EDGES = [
    ("", "Truncated"),                                  # no byte for a head
    ("17", "ok"),                                       # the largest immediate argument
    ("1817", "NonCanonicalInt;value=23"),               # each width that fits a shorter form ...
    ("1818", "ok"),                                     # ... and the smallest value it may carry
    ("1900ff", "NonCanonicalInt;value=255"),
    ("190100", "ok"),
    ("1a0000ffff", "NonCanonicalInt;value=65535"),
    ("1a00010000", "ok"),
    ("1b00000000ffffffff", "NonCanonicalInt;value=4294967295"),
    ("1b0000000100000000", "ok"),
    ("3817", "NonCanonicalInt;value=23"),               # a negative int's argument
    ("5800", "NonCanonicalInt;value=0"),                # a byte length
    ("780161", "NonCanonicalInt;value=1"),              # a text length
    ("9800", "NonCanonicalInt;value=0"),                # an array count
    ("b800", "NonCanonicalInt;value=0"),                # a map count
    ("a1180000", "NonCanonicalInt;value=0"),            # a map key
    ("7b0000000000000001", "NonCanonicalInt;value=1"),  # the head is checked before the body
    ("1900", "Truncated"),                              # missing argument bytes
    ("7b0020000000000000", "Truncated"),                # a text length beyond the input
    # Decode takes any float width; re-encode writes the shortest (G2, question 7, open).
    ("fa3f800000", "ok;reencode=f93c00"),
    ("fb3ff0000000000000", "ok;reencode=f93c00"),
    ("f93c", "Truncated"),
    ("f7", "UnsupportedInfo;info=23"),                  # major 7 other than the eight kept values
    ("f800", "UnsupportedInfo;info=24"),
    ("e0", "UnsupportedInfo;info=0"),
    ("ff", "UnsupportedInfo;info=31"),
    ("9f", "UnsupportedInfo;info=31"),                  # indefinite lengths
    ("3c", "UnsupportedInfo;info=28"),
    ("d8", "UnsupportedMajor;major=6"),                 # major 6 before its argument
    ("df", "UnsupportedMajor;major=6"),
    ("a1f500", "NonIntegerMapKey"),                     # a bool key is not an int
    ("a2000000", "DuplicateMapKey;key=0"),
    ("a13b7fffffffffffffff00", "NegativeMapKey;key=-9223372036854775808"),
    ("a11b7fffffffffffffff00", "ok"),                   # the largest legal key
    ("a11b800000000000000000", "IntOverflow;value=9223372036854775808"),
    ("3bffffffffffffffff", "IntOverflow;value=-18446744073709551616"),
    ("8261ff00", "InvalidUtf8"),                        # items are read in order
    ("63eda080", "InvalidUtf8"),                        # a surrogate
    ("00ff", "TrailingBytes"),
]


def _python_observation(data: bytes) -> str:
    """`ok`, with `;reencode=<hex>` when the re-encoding differs from the input, or the error."""
    try:
        again = cbor.dumps(cbor.loads(data))
    except cbor.DecodeError as exc:
        return parity.format_error(exc.tag, exc.payload)
    return "ok" if again == data else f"ok;reencode={again.hex()}"


def _raw_row(hex_input: str, observed: str) -> dict:
    tag, payload = parity.parse_error(observed)
    if tag == "ok":
        expect: dict = {"accept": True, **payload}
    else:
        expect = {"tag": tag, **payload}
    return {"name": f"edge-{hex_input or 'empty'}", "stage": "raw_decode", "bytes": hex_input,
            "expect": expect, "why": "CD-E5 edge beyond the corpus"}


def test_raw_edges_state_what_python_the_reference_does():
    assert [(h, _python_observation(bytes.fromhex(h))) for h, _ in RAW_EDGES] == RAW_EDGES


def test_go_raw_decode_matches_python_beyond_the_corpus(monkeypatch):
    _needs_go()
    rows = [_raw_row(h, want) for h, want in RAW_EDGES]
    monkeypatch.setattr(parity, "malformed_rows", lambda: rows)
    monkeypatch.setattr(parity, "bounds_rows", lambda: [])
    report = parity_go.run()
    assert report.green, _failures(report)
    assert {r.name for r in report.results if r.kind == "malformed"} == {row["name"] for row in rows}


def test_go_runtime_and_parity_runner_are_gofmt_clean(tmp_path):
    gofmt = shutil.which("gofmt")
    if gofmt is None:
        pytest.skip("gofmt not installed")
    runner = tmp_path / "main.go"
    runner.write_text(parity_go._source())
    runtime = sorted(str(p) for p in RUNTIME.glob("*.go"))
    result = subprocess.run([gofmt, "-l", str(runner), *runtime], capture_output=True, text=True, check=False)
    assert (result.returncode, result.stdout, result.stderr) == (0, "", "")


# --- every legal field shape, at any nesting ----------------------------------------------

# Deeper than the fixture's `Shapes`: lists three deep, maps inside lists, each scalar in a
# nested list, a message inside a list of lists, and optional and MISSING_OK lists and maps.
# `IntBox` is the fixture's, as the gate's Go runner builds one.
DEEP_SCHEMA = mk(
    Enum("Mode", ok=0, alt=1),
    Msg("IntBox", F("n", 1, INT), F("by_id", 2, Map(INT, INT))),
    Msg("EnumBox", F("mode", 1, Ref("Mode"))),
    Msg("Row", F("cells", 1, List(List(INT)), optional=True)),
    Msg("Deep",
        F("cube", 1, List(List(List(INT)))),
        F("words", 2, List(List(STR))),
        F("blobs", 3, List(List(BYTES))),
        F("flags", 4, List(List(BOOL))),
        F("reals", 5, List(List(FLOAT))),
        F("modes", 6, List(List(Ref("Mode")))),
        F("rows", 7, List(List(Ref("Row")))),
        F("tallies", 8, List(Map(STR, INT))),
        F("mode_maps", 9, List(List(Map(BOOL, Ref("Mode"))))),
        F("box_maps", 10, List(Map(INT, Ref("EnumBox")))),
        F("maybe_cube", 11, List(List(List(FLOAT))), optional=True),
        F("maybe_rows", 12, List(Ref("Row")), optional=True),
        F("maybe_blobs", 13, List(Map(STR, BYTES)), optional=True),
        F("maybe_boxes", 14, Map(INT, Ref("EnumBox")), optional=True),
        F("late_grid", 15, List(List(STR)), optional=MISSING_OK),
        F("late_reals", 16, Map(BOOL, FLOAT), optional=MISSING_OK)),
)


def _generated_go() -> dict[str, str]:
    """api.go, with and without forward-compat, for every IR file and this file's schemas."""
    schemas = {path.name.removesuffix(".taut.py"): load_schema(path) for path in IR_FILES}
    schemas |= {"deep": DEEP_SCHEMA, "float": FLOAT_SCHEMA, "keys": KEYS_SCHEMA, "presence": PRESENCE_SCHEMA}
    return {f"{name}{'_fc' if fc else ''}": go.emit_types(schema, forward_compat=fc)
            for name, schema in schemas.items() for fc in (False, True)}


def test_generated_go_is_gofmt_clean(tmp_path):
    gofmt = shutil.which("gofmt")
    if gofmt is None:
        pytest.skip("gofmt not installed")
    paths = []
    for name, source in _generated_go().items():
        paths.append(tmp_path / f"{name}.go")
        paths[-1].write_text(source)
    result = subprocess.run([gofmt, "-l", *map(str, paths)], capture_output=True, text=True, check=False)
    assert (result.returncode, result.stdout, result.stderr) == (0, "", "")


def test_every_ir_file_generates_go_that_vets(tmp_path):
    _needs_go()
    env = _go_test_env(tmp_path)
    for path in IR_FILES:
        schema = load_schema(path)
        out = tmp_path / path.name.removesuffix(".taut.py")
        scaffold.emit(schema, out, langs=["go"], services=[], runtime=True, forward_compat=bool(schema.extensions))
        result = subprocess.run(["go", "vet"], cwd=out / "go", env=env, text=True,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)
        assert result.returncode == 0, f"{path.name}\n{result.stdout}"


_SAMPLES = {
    "int": [0, 1, -1, 23, 24, -25, 256, 1 << 40, -(1 << 63), (1 << 63) - 1],
    "str": ["", "a", "b", "naïve", "￿", "\U00010000"],
    "bytes": [b"", b"\x00", b"\xff\x00"],
    "bool": [False, True],
    "float": [0.0, -0.0, 1.5, 0.1, -2.25, 1e300, float("inf"), float("nan")],
}
# What a mutation puts in a node's place. No dict here holds a key a message lacks, so no
# row carries an unknown field (which Python keeps and non-forward-compat Go drops).
_REPLACEMENTS = [0, 7, -1, "x", b"", True, None, 1.5, [], {}, [0], ["x"], [{}], [[None]], [{1: 0}]]


def _native(t, rng: random.Random):
    """A random native value of type `t` in DEEP_SCHEMA, as `taut.wire.codec` takes one."""
    if isinstance(t, Scalar):
        return rng.choice(_SAMPLES[t.kind])
    if isinstance(t, EnumRef):
        return rng.choice(list(DEEP_SCHEMA.enums[t.name].members))
    if isinstance(t, MsgRef):
        return {f.name: None if f.optional and rng.randrange(3) == 0 else _native(f.type, rng)
                for f in DEEP_SCHEMA.messages[t.name].fields}
    if isinstance(t, ListOf):
        return [_native(t.elem, rng) for _ in range(rng.randrange(4))]
    assert isinstance(t, MapOf)
    return {_native(t.key, rng): _native(t.value, rng) for _ in range(rng.randrange(4))}


def _nodes(node, parent=None, key=None):
    """`(parent, key, node)` for every node of a decoded CBOR tree; the root's parent is None."""
    yield parent, key, node
    children = enumerate(node) if isinstance(node, list) else node.items() if isinstance(node, dict) else ()
    for child_key, child in children:
        yield from _nodes(child, node, child_key)


def _mutated(tree, rng: random.Random):
    """A copy of `tree` with one key dropped, one item repeated or one node replaced."""
    tree = copy.deepcopy(tree)
    nodes = list(_nodes(tree))
    maps = [node for _, _, node in nodes if isinstance(node, dict) and node]
    lists = [node for _, _, node in nodes if isinstance(node, list) and node]
    op = rng.randrange(3)
    if op == 0 and maps:
        node = rng.choice(maps)
        del node[rng.choice(list(node))]                  # MissingKey, or null for MISSING_OK
    elif op == 1 and lists:
        node = rng.choice(lists)
        index = rng.randrange(len(node))
        node.insert(index, copy.deepcopy(node[index]))   # in a map's array, a repeated key
    else:
        parent, key, _ = rng.choice(nodes)
        replacement = copy.deepcopy(rng.choice(_REPLACEMENTS))
        if parent is None:
            return replacement
        parent[key] = replacement
    return tree


def _python_expect(data: bytes) -> dict:
    """What `taut.wire.codec`, the reference, makes of `data` as a `Deep`: a row's expect,
    the whole payload, so a repeated str or bool key is judged by its text (question 9)."""
    try:
        again = codec.encode(DEEP_SCHEMA, "Deep", codec.decode(DEEP_SCHEMA, "Deep", data))
    except cbor.DecodeError as exc:
        return {"tag": exc.tag, **exc.payload}
    return {"accept": True, "reencode": again.hex()}


def _deep_rows(seed: int = 0x0302, values: int = 40, mutations: int = 500) -> list[dict]:
    """`from_cbor` rows for `Deep`: every optional null, every optional present and empty
    (an empty array, not null), random values, each field's key dropped in turn, then
    random mutations."""
    rng = random.Random(seed)
    fields = DEEP_SCHEMA.messages["Deep"].fields
    unset = {f.name: None if f.optional else [] for f in fields}
    empty = {f.name: {} if isinstance(f.type, MapOf) else [] for f in fields}
    natives = [unset, empty, *(_native(MsgRef("Deep"), rng) for _ in range(values))]
    encoded = [codec.encode(DEEP_SCHEMA, "Deep", value) for value in natives]
    trees = [cbor.loads(data) for data in encoded]
    for f in fields:
        tree = copy.deepcopy(rng.choice(trees))
        del tree[f.tag]                                   # MissingKey, or null for MISSING_OK
        encoded.append(cbor.dumps(tree))
    encoded += [cbor.dumps(_mutated(rng.choice(trees), rng)) for _ in range(mutations)]
    return [{"name": f"deep-{i}", "stage": "from_cbor", "schema": "Deep", "bytes": data.hex(),
             "expect": _python_expect(data), "why": "every shape at depth, beyond the corpus"}
            for i, data in enumerate(encoded)]


def test_go_decodes_and_reencodes_every_shape_at_depth_as_python_does(monkeypatch):
    """DEEP_SCHEMA through the gate's own Go runner and judge: what Python encodes, and
    mutations of it, decode or fail with Python's tag and payload, and re-encode as Python does."""
    assert validate(DEEP_SCHEMA) == []   # legal shapes only
    _needs_go()
    rows = _deep_rows()
    assert {row["expect"].get("tag", "accept") for row in rows} >= {
        "accept", "WrongType", "MissingKey", "DuplicateMapKey", "UnknownEnum"}
    duplicate_keys = {row["expect"]["key"] for row in rows if row["expect"].get("tag") == "DuplicateMapKey"}
    assert {"true", "false", "", "a", -1} <= duplicate_keys   # bool, str and int keys, as text
    assert rows[1]["expect"]["reencode"] != rows[0]["expect"]["reencode"]   # empty is not null
    monkeypatch.setattr(parity, "parity_schema", lambda: DEEP_SCHEMA)
    monkeypatch.setattr(parity, "malformed_rows", lambda: rows)
    monkeypatch.setattr(parity, "bounds_rows", lambda: [])
    report = parity_go.run()
    assert report.green, _failures(report)
    assert {r.name for r in report.results if r.kind == "malformed"} == {row["name"] for row in rows}


# optional=MISSING_OK (TautCheckedDecode.md CD-E5, the opt-in exception): `Late` reads an
# absent key as null; `Opt`, plain optional, still requires the key.
PRESENCE_SCHEMA = mk(Msg("Late", F("note", 1, STR, optional=MISSING_OK)),
                     Msg("Opt", F("note", 1, STR, optional=True)))


def _decoder(src: str, name: str) -> str:
    """The body of the generated `TryXFromCbor` for message `name`."""
    start = src.index(f"func Try{name}FromCbor(")
    end = src.find("\nfunc ", start)
    return src[start:] if end < 0 else src[start:end]


def test_missing_ok_looks_the_key_up_and_optional_requires_it():
    s = go.emit_types(PRESENCE_SCHEMA)
    late, opt = _decoder(s, "Late"), _decoder(s, "Opt")
    assert "c.Lookup(1)" in late and "c.Require(1)" not in late
    assert "c.Require(1)" in opt and "c.Lookup(1)" not in opt
    assert "c.TryMap()" in late and "c.TryMap()" in opt   # a message must be a map


def test_scaffold_generates_missing_ok_for_go(tmp_path):
    written = scaffold.emit(PRESENCE_SCHEMA, tmp_path, langs=["go"], services=[])
    assert tmp_path / "go" / "api.go" in written


def test_go_missing_ok_runtime(tmp_path):
    _needs_go()
    scaffold.emit(PRESENCE_SCHEMA, tmp_path, langs=["go"], services=[], runtime=True)
    go_dir = tmp_path / "go"
    (go_dir / "presence_test.go").write_text(textwrap.dedent("""
        package taut

        import (
            "encoding/hex"
            "testing"
        )

        func decodeHex(t *testing.T, input string) Cbor {
            t.Helper()
            data, err := hex.DecodeString(input)
            if err != nil {
                t.Fatalf("bad hex %q: %v", input, err)
            }
            c, err := TryDecode(data)
            if err != nil {
                t.Fatalf("%s: raw decode: %v", input, err)
            }
            return c
        }

        func wantDecodeError(t *testing.T, input string, err error, want DecodeError) {
            t.Helper()
            got, ok := err.(*DecodeError)
            if !ok {
                t.Fatalf("%s: got %T %v, want %v", input, err, err, &want)
            }
            if *got != want {
                t.Fatalf("%s: got %#v, want %#v", input, *got, want)
            }
        }

        func TestLateReadsAnAbsentOrNullNoteAsNil(t *testing.T) {
            for _, input := range []string{"a0", "a101f6"} {
                late, err := TryLateFromCbor(decodeHex(t, input))
                if err != nil {
                    t.Fatalf("%s: %v", input, err)
                }
                if late.Note != nil {
                    t.Fatalf("%s: note %q, want nil", input, *late.Note)
                }
            }
        }

        func TestLateReadsAPresentNote(t *testing.T) {
            late, err := TryLateFromCbor(decodeHex(t, "a101617a"))
            if err != nil {
                t.Fatal(err)
            }
            if late.Note == nil || *late.Note != "z" {
                t.Fatalf("note %v, want z", late.Note)
            }
        }

        func TestLateStillRefusesAWrongTypeAndANonMap(t *testing.T) {
            _, err := TryLateFromCbor(decodeHex(t, "a10101"))
            wantDecodeError(t, "a10101", err, DecodeError{Tag: DecodeErrWrongType, Expected: "text"})
            _, err = TryLateFromCbor(decodeHex(t, "00"))
            wantDecodeError(t, "00", err, DecodeError{Tag: DecodeErrWrongType, Expected: "map"})
        }

        func TestLateEncodesAnUnsetNoteAsNull(t *testing.T) {
            if got := hex.EncodeToString(Encode(Late{}.ToCbor())); got != "a101f6" {
                t.Fatalf("got %s, want a101f6", got)
            }
        }

        func TestOptRequiresTheKeyAndReadsNullAsNil(t *testing.T) {
            _, err := TryOptFromCbor(decodeHex(t, "a0"))
            wantDecodeError(t, "a0", err, DecodeError{Tag: DecodeErrMissingKey, Key: "1"})
            opt, err := TryOptFromCbor(decodeHex(t, "a101f6"))
            if err != nil {
                t.Fatal(err)
            }
            if opt.Note != nil {
                t.Fatalf("note %q, want nil", *opt.Note)
            }
        }
    """))
    _run_go_tests(go_dir, tmp_path, "TestLateReadsAnAbsentOrNullNoteAsNil", "TestLateReadsAPresentNote",
                  "TestLateStillRefusesAWrongTypeAndANonMap", "TestLateEncodesAnUnsetNoteAsNull",
                  "TestOptRequiresTheKeyAndReadsNullAsNil")


def _run_go_tests(go_dir: Path, tmp_path: Path, *names: str) -> None:
    result = subprocess.run(["go", "test", "-v"], cwd=go_dir, env=_go_test_env(tmp_path), text=True,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)
    assert result.returncode == 0, result.stdout
    for name in names:
        assert f"--- PASS: {name}" in result.stdout


# A repeated `map<K,V>` entry key is refused whatever K is, and its payload is the key as text
# (TautCheckedDecode.md §8 question 9): an int in decimal, a str as itself, a bool as `true` or
# `false`. The corpus pins an int key (M13), a str and a bool one.
KEYS_SCHEMA = mk(Msg("Keys", F("by_name", 1, Map(STR, INT)), F("by_flag", 2, Map(BOOL, INT)),
                     F("by_id", 3, Map(INT, INT))))
KEYS_DISTINCT = cbor.dumps({1: [{1: "a", 2: 1}, {1: "b", 2: 2}], 2: [{1: False, 2: 0}, {1: True, 2: 1}],
                            3: [{1: -7, 2: 0}, {1: 7, 2: 1}]})
# The repeated key's text -> a `Keys` with one map that repeats that key.
KEYS_REPEATED = {
    "a": cbor.dumps({1: [{1: "a", 2: 1}, {1: "a", 2: 2}], 2: [], 3: []}),
    "true": cbor.dumps({1: [], 2: [{1: True, 2: 1}, {1: True, 2: 2}], 3: []}),
    "false": cbor.dumps({1: [], 2: [{1: False, 2: 1}, {1: False, 2: 2}], 3: []}),
    "-7": cbor.dumps({1: [], 2: [], 3: [{1: -7, 2: 1}, {1: -7, 2: 2}]}),
}


def test_python_refuses_a_repeated_map_key_with_the_key_as_text():
    assert codec.decode(KEYS_SCHEMA, "Keys", KEYS_DISTINCT) == {
        "by_name": {"a": 1, "b": 2}, "by_flag": {False: 0, True: 1}, "by_id": {-7: 0, 7: 1}}
    for text, data in KEYS_REPEATED.items():
        with pytest.raises(cbor.DecodeError) as caught:
            codec.decode(KEYS_SCHEMA, "Keys", data)
        assert (caught.value.tag, str(caught.value.payload["key"])) == ("DuplicateMapKey", text)


def test_go_map_field_refuses_a_repeated_key_with_the_key_as_text(tmp_path):
    _needs_go()
    scaffold.emit(KEYS_SCHEMA, tmp_path, langs=["go"], services=[], runtime=True)
    go_dir = tmp_path / "go"
    repeated = ", ".join(f'{{"{data.hex()}", {_go_str(text)}}}' for text, data in KEYS_REPEATED.items())
    (go_dir / "keys_test.go").write_text(textwrap.dedent(f"""
        package taut

        import (
            "encoding/hex"
            "testing"
        )

        func decodeKeys(t *testing.T, input string) (Keys, error) {{
            t.Helper()
            data, err := hex.DecodeString(input)
            if err != nil {{
                t.Fatalf("bad hex %q: %v", input, err)
            }}
            c, err := TryDecode(data)
            if err != nil {{
                t.Fatalf("%s: raw decode: %v", input, err)
            }}
            return TryKeysFromCbor(c)
        }}

        func TestKeysDecodesDistinctKeys(t *testing.T) {{
            keys, err := decodeKeys(t, "{KEYS_DISTINCT.hex()}")
            if err != nil {{
                t.Fatal(err)
            }}
            if len(keys.ByName) != 2 || keys.ByName["a"] != 1 || keys.ByName["b"] != 2 {{
                t.Fatalf("by_name %v", keys.ByName)
            }}
            if len(keys.ByFlag) != 2 || keys.ByFlag[false] != 0 || keys.ByFlag[true] != 1 {{
                t.Fatalf("by_flag %v", keys.ByFlag)
            }}
            if len(keys.ById) != 2 || keys.ById[-7] != 0 || keys.ById[7] != 1 {{
                t.Fatalf("by_id %v", keys.ById)
            }}
        }}

        func TestKeysRefusesARepeatedKeyWithTheKeyAsText(t *testing.T) {{
            for _, c := range []struct{{ input, key string }}{{{repeated}}} {{
                _, err := decodeKeys(t, c.input)
                want := DecodeError{{Tag: DecodeErrDuplicateMapKey, Key: c.key}}
                got, ok := err.(*DecodeError)
                if !ok || *got != want {{
                    t.Fatalf("%s: got %T %v, want %#v", c.input, err, err, want)
                }}
                if text := got.Error(); text != "DuplicateMapKey("+c.key+")" {{
                    t.Fatalf("%s: Error() is %q", c.input, text)
                }}
            }}
        }}
    """))
    _run_go_tests(go_dir, tmp_path, "TestKeysDecodesDistinctKeys", "TestKeysRefusesARepeatedKeyWithTheKeyAsText")


def _go_str(s: str) -> str:
    return json.dumps(s)


def _go_residual_rows(name: str, rows: list[dict]) -> str:
    lines = [f"var {name} = []residualCase{{"]
    for r in rows:
        lines.append(f"\t{{note: {_go_str(r['note'])}, wire: {_go_str(r['wire'])}}},")
    lines.append("}")
    return "\n".join(lines)


def _go_ext_rows(name: str, rows: list[dict]) -> str:
    lines = [f"var {name} = []extCase{{"]
    for r in rows:
        fields = [
            f"op: {_go_str(r['op'])}",
            f"note: {_go_str(r['note'])}",
            f"host: {_go_str(r['host'])}",
            f"tag: {r['tag']}",
            f"expect: {_go_str(r['expect'])}",
        ]
        if "value" in r:
            fields.append(f"value: {_go_str(r['value'])}")
        lines.append("\t{" + ", ".join(fields) + "},")
    lines.append("}")
    return "\n".join(lines)


def _rand_cbor_value(rng: random.Random):
    choice = rng.randrange(5)
    if choice == 0:
        return rng.randint(-2000, 2000)
    if choice == 1:
        return f"s{rng.randrange(100000)}"
    if choice == 2:
        return bytes(rng.randrange(256) for _ in range(rng.randrange(0, 8)))
    if choice == 3:
        return [rng.randint(-20, 20), f"a{rng.randrange(1000)}"]
    return None if rng.randrange(2) == 0 else bool(rng.randrange(2))


def _resext_fuzz_rows(seed: int = 0x55_04, iterations: int = 1000) -> tuple[list[dict], list[dict]]:
    rng = random.Random(seed)
    residual_rows: list[dict] = []
    ext_rows: list[dict] = []
    for i in range(iterations):
        unknown = {
            3: _rand_cbor_value(rng),                         # interleaves between known 2 and 5
            BAND_START + rng.randrange(0, 1 << 20): _rand_cbor_value(rng),
        }
        for _ in range(rng.randrange(0, 3)):
            tag = rng.randrange(0, 1 << 21)
            if tag not in (1, 2, 3, 5) and tag not in unknown:
                unknown[tag] = _rand_cbor_value(rng)
        host_value = {
            "id": rng.randint(0, 100000),
            "name": f"n{rng.randrange(100000)}",
            "score": rng.randint(-500, 500),
            "__unknown__": unknown,
        }
        host_hex = codec.encode(RESEXT, "Host", host_value).hex()
        residual_rows.append({"note": f"fuzz-{i}", "wire": host_hex})

        decision = {"backend": f"b{rng.randrange(10000)}", "hops": rng.randint(0, 20)}
        value_hex = codec.encode(RESEXT, "Decision", decision).hex()
        tag = BAND_START + 1 + rng.randrange(0, 200)
        ext_rows.append({
            "op": "fuzz",
            "note": f"fuzz-{i}",
            "host": host_hex,
            "tag": tag,
            "value": value_hex,
            "set_expect": ext.ext_set(RESEXT, bytes.fromhex(host_hex), "Decision", tag, decision).hex(),
            "get_expect": value_hex,
            "clear_expect": ext.ext_clear(
                ext.ext_set(RESEXT, bytes.fromhex(host_hex), "Decision", tag, decision), tag
            ).hex(),
        })
    return residual_rows, ext_rows


def _go_fuzz_rows(name: str, rows: list[dict]) -> str:
    lines = [f"var {name} = []fuzzCase{{"]
    for r in rows:
        lines.append(
            "\t{"
            f"note: {_go_str(r['note'])}, "
            f"host: {_go_str(r['host'])}, "
            f"tag: {r['tag']}, "
            f"value: {_go_str(r['value'])}, "
            f"setExpect: {_go_str(r['set_expect'])}, "
            f"getExpect: {_go_str(r['get_expect'])}, "
            f"clearExpect: {_go_str(r['clear_expect'])}"
            "},"
        )
    lines.append("}")
    return "\n".join(lines)


def _write_resext_go_harness(tmp_path: Path) -> Path:
    scaffold.emit(RESEXT, tmp_path, langs=["go"], services=[], runtime=True, forward_compat=True)
    go_dir = tmp_path / "go"
    residual_rows = json.loads(resext.RESIDUAL_PATH.read_text())
    ext_rows = json.loads(resext.EXT_PATH.read_text())
    fuzz_residual_rows, fuzz_ext_rows = _resext_fuzz_rows()
    (go_dir / "resext_phase2_test.go").write_text(textwrap.dedent(f"""
        package taut

        import (
            "encoding/hex"
            "errors"
            "testing"
        )

        type residualCase struct {{
            note string
            wire string
        }}

        type extCase struct {{
            op string
            note string
            host string
            tag int64
            value string
            expect string
        }}

        type fuzzCase struct {{
            note string
            host string
            tag int64
            value string
            setExpect string
            getExpect string
            clearExpect string
        }}

        func mustHex(t *testing.T, s string) []byte {{
            t.Helper()
            b, err := hex.DecodeString(s)
            if err != nil {{
                t.Fatalf("bad hex %q: %v", s, err)
            }}
            return b
        }}

        func hexOf(b []byte) string {{
            return hex.EncodeToString(b)
        }}

        func mustDecode(t *testing.T, wire []byte) Cbor {{
            t.Helper()
            c, err := TryDecode(wire)
            if err != nil {{
                t.Fatalf("decode %x: %v", wire, err)
            }}
            return c
        }}

        func mustHost(t *testing.T, wire string) Host {{
            t.Helper()
            host, err := TryHostFromCbor(mustDecode(t, mustHex(t, wire)))
            if err != nil {{
                t.Fatalf("host %s: %v", wire, err)
            }}
            return host
        }}

        func mustDecision(t *testing.T, c Cbor) Decision {{
            t.Helper()
            decision, err := TryDecisionFromCbor(c)
            if err != nil {{
                t.Fatalf("decision %x: %v", Encode(c), err)
            }}
            return decision
        }}

        func mustExtSet(t *testing.T, host []byte, tag int64, value Cbor) []byte {{
            t.Helper()
            out, err := ExtSet(host, tag, value)
            if err != nil {{
                t.Fatalf("ExtSet(%x, %d): %v", host, tag, err)
            }}
            return out
        }}

        func mustExtGet(t *testing.T, host []byte, tag int64) (Cbor, bool) {{
            t.Helper()
            value, ok, err := ExtGet(host, tag)
            if err != nil {{
                t.Fatalf("ExtGet(%x, %d): %v", host, tag, err)
            }}
            return value, ok
        }}

        func mustExtClear(t *testing.T, host []byte, tag int64) []byte {{
            t.Helper()
            out, err := ExtClear(host, tag)
            if err != nil {{
                t.Fatalf("ExtClear(%x, %d): %v", host, tag, err)
            }}
            return out
        }}

        // extErrors runs ExtSet, ExtGet and ExtClear on host at tag, each expected to fail, and
        // returns their errors; a failing accessor returns no bytes and reports no value.
        func extErrors(t *testing.T, host []byte, tag int64) []error {{
            t.Helper()
            set, setErr := ExtSet(host, tag, CMap(nil))
            _, ok, getErr := ExtGet(host, tag)
            cleared, clearErr := ExtClear(host, tag)
            if set != nil || ok || cleared != nil {{
                t.Fatalf("%x at %d: a failing accessor returned %x, %v, %x", host, tag, set, ok, cleared)
            }}
            return []error{{setErr, getErr, clearErr}}
        }}

        {_go_residual_rows("residualCorpus", residual_rows)}

        {_go_ext_rows("extCorpus", ext_rows)}

        {_go_residual_rows("fuzzResidualCorpus", fuzz_residual_rows)}

        {_go_fuzz_rows("fuzzExtCorpus", fuzz_ext_rows)}

        func TestResExtResidualCorpus(t *testing.T) {{
            mismatches := 0
            for _, row := range residualCorpus {{
                got := hexOf(Encode(mustHost(t, row.wire).ToCbor()))
                if got != row.wire {{
                    t.Errorf("%s: got %s want %s", row.note, got, row.wire)
                    mismatches++
                }}
            }}
            t.Logf("residual corpus mismatches=%d rows=%d", mismatches, len(residualCorpus))
        }}

        func TestResExtExtensionCorpus(t *testing.T) {{
            mismatches := 0
            for _, row := range extCorpus {{
                switch row.op {{
                case "set":
                    typed := mustDecision(t, mustDecode(t, mustHex(t, row.value)))
                    got := hexOf(mustExtSet(t, mustHex(t, row.host), row.tag, typed.ToCbor()))
                    if got != row.expect {{
                        t.Errorf("%s set: got %s want %s", row.note, got, row.expect)
                        mismatches++
                    }}
                case "get":
                    got, ok := mustExtGet(t, mustHex(t, row.host), row.tag)
                    if row.expect == "null" {{
                        if ok {{
                            t.Errorf("%s get: got present value, want absent", row.note)
                            mismatches++
                        }}
                        continue
                    }}
                    if !ok {{
                        t.Errorf("%s get: got absent, want %s", row.note, row.expect)
                        mismatches++
                        continue
                    }}
                    typed := mustDecision(t, got)
                    if gotHex := hexOf(Encode(typed.ToCbor())); gotHex != row.expect {{
                        t.Errorf("%s get: got %s want %s", row.note, gotHex, row.expect)
                        mismatches++
                    }}
                case "clear":
                    got := hexOf(mustExtClear(t, mustHex(t, row.host), row.tag))
                    if got != row.expect {{
                        t.Errorf("%s clear: got %s want %s", row.note, got, row.expect)
                        mismatches++
                    }}
                default:
                    t.Fatalf("unknown op %s", row.op)
                }}
            }}
            t.Logf("extension corpus mismatches=%d rows=%d", mismatches, len(extCorpus))
        }}

        // CD-E4: a tag below the band is the caller's error, an *ExtTagError and not a
        // *DecodeError, checked before the host is read (here it is not CBOR at all).
        func TestResExtRefusesATagBelowTheBandAsACallerError(t *testing.T) {{
            for op, err := range extErrors(t, []byte{{0xff}}, BandStart-1) {{
                var tagErr *ExtTagError
                if !errors.As(err, &tagErr) || tagErr.Tag != BandStart-1 {{
                    t.Fatalf("op %d: got %T %v, want an *ExtTagError for %d", op, err, err, BandStart-1)
                }}
                var decodeErr *DecodeError
                if errors.As(err, &decodeErr) {{
                    t.Fatalf("op %d: a caller error is a *DecodeError: %v", op, err)
                }}
            }}
        }}

        // CD-E4: bad host bytes are a *DecodeError, and a host that is not a map is WrongType{{map}}.
        func TestResExtRefusesABadHostWithADecodeError(t *testing.T) {{
            cases := []struct {{
                host string
                want DecodeError
            }}{{
                {{"01", DecodeError{{Tag: DecodeErrWrongType, Expected: "map"}}}},
                {{"80", DecodeError{{Tag: DecodeErrWrongType, Expected: "map"}}}},
                {{"", DecodeError{{Tag: DecodeErrTruncated}}}},
                {{"a1", DecodeError{{Tag: DecodeErrTruncated}}}},
                {{"ff", DecodeError{{Tag: DecodeErrUnsupportedInfo, Info: 31}}}},
                {{"a2000000", DecodeError{{Tag: DecodeErrDuplicateMapKey, Key: "0"}}}},
                {{"a000", DecodeError{{Tag: DecodeErrTrailingBytes}}}},
            }}
            for _, c := range cases {{
                for op, err := range extErrors(t, mustHex(t, c.host), BandStart) {{
                    got, ok := err.(*DecodeError)
                    if !ok || *got != c.want {{
                        t.Fatalf("%q op %d: got %T %v, want %#v", c.host, op, err, err, c.want)
                    }}
                }}
            }}
        }}

        func TestResExtFuzzFixedSeed(t *testing.T) {{
            mismatches := 0
            for _, row := range fuzzResidualCorpus {{
                got := hexOf(Encode(mustHost(t, row.wire).ToCbor()))
                if got != row.wire {{
                    t.Errorf("%s residual: got %s want %s seed=0x5504", row.note, got, row.wire)
                    mismatches++
                }}
            }}
            for _, row := range fuzzExtCorpus {{
                typed := mustDecision(t, mustDecode(t, mustHex(t, row.value)))
                setBytes := mustExtSet(t, mustHex(t, row.host), row.tag, typed.ToCbor())
                if got := hexOf(setBytes); got != row.setExpect {{
                    t.Errorf("%s set: got %s want %s seed=0x5504", row.note, got, row.setExpect)
                    mismatches++
                    continue
                }}
                gotCbor, ok := mustExtGet(t, setBytes, row.tag)
                if !ok {{
                    t.Errorf("%s get: got absent want %s seed=0x5504", row.note, row.getExpect)
                    mismatches++
                }} else {{
                    gotTyped := mustDecision(t, gotCbor)
                    if got := hexOf(Encode(gotTyped.ToCbor())); got != row.getExpect {{
                        t.Errorf("%s get: got %s want %s seed=0x5504", row.note, got, row.getExpect)
                        mismatches++
                    }}
                }}
                if got := hexOf(mustExtClear(t, setBytes, row.tag)); got != row.clearExpect {{
                    t.Errorf("%s clear: got %s want %s seed=0x5504", row.note, got, row.clearExpect)
                    mismatches++
                }}
            }}
            t.Logf("resext fuzz seed=0x5504 iterations=%d mismatches=%d", len(fuzzResidualCorpus), mismatches)
        }}
    """))
    return go_dir


def test_go_resext_phase2_harness(tmp_path):
    _needs_go()
    go_dir = _write_resext_go_harness(tmp_path)
    _run_go_tests(go_dir, tmp_path, "TestResExtResidualCorpus", "TestResExtExtensionCorpus",
                  "TestResExtRefusesATagBelowTheBandAsACallerError",
                  "TestResExtRefusesABadHostWithADecodeError", "TestResExtFuzzFixedSeed")
