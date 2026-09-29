"""Go generator: native structs + typed-const enums + CBOR codec, forward-compat
residual, PascalCase exported fields. The shared parity corpus replays through the
gate's Go runner (`taut.corpus.parity_go`)."""

import os
import json
import random
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
from taut.ir.dsl import BOOL, FLOAT, INT, MISSING_OK, STR, F, List, Map, Msg, schema as mk
from taut.ir.load import load_schema
from taut.ir.shapes import BAND_START
from taut.wire import cbor, codec

ROOT = Path(__file__).resolve().parents[2]
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


def test_emits_structs_enums_and_codec():
    s = go.emit_types(RAZEL)
    assert "package taut" in s
    assert "type BuildResult struct {" in s
    assert "type BuildStatus int64" in s
    assert "BuildStatusBuilt BuildStatus = 1" in s
    assert "func (x BuildResult) ToCbor() Cbor {" in s
    assert "func TryBuildResultFromCbor(c Cbor) (BuildResult, error) {" in s
    assert "func BuildResultFromCbor(c Cbor) BuildResult {" in s
    assert "func TryBuildStatusFromWire(v int64) (BuildStatus, error) {" in s


def test_fields_pascalcased_and_optional_is_pointer():
    s = go.emit_types(RAZEL)
    assert "Recomputes int64" in s   # recomputes -> Recomputes (exported)
    assert "Message *string" in s    # optional -> nil-able pointer


def test_forward_compat_adds_residual():
    s = go.emit_types(RAZEL, forward_compat=True)
    assert "WireResidual []KV" in s
    assert "append(m, x.WireResidual...)" in s          # re-emitted (Encode sorts)
    assert "WireResidual" not in go.emit_types(RAZEL)   # off by default


def test_float_scalar_codegen():
    s = go.emit_types(FLOAT_SCHEMA)
    assert "X float64" in s
    assert "Xs []float64" in s
    assert "ById map[int64]float64" in s
    assert "Maybe *float64" in s
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


def _needs_go() -> None:
    if toolchains.find_go() is None:
        pytest.skip("go not installed")


def _failures(report: parity.TargetReport) -> str:
    return "\n".join([report.fault, *(f"{r.name}: {r.detail}" for r in report.failures)])


def test_go_parity_gate_is_green():
    """`tautc parity -t go`: every int and malformed row through the generated Go codec."""
    _needs_go()
    report = parity_go.run()
    assert report.green, _failures(report)
    encode_fail = {r["name"] for r in parity.int_rows() if r["kind"] == "encode_fail"}
    assert {r.name for r in report.results if r.status == parity.TYPE_SATISFIED} == encode_fail


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
    ("fa3f800000", "ok"),                               # floats are exempt from shortest form
    ("fb3ff0000000000000", "ok"),
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
    try:
        cbor.loads(data)
    except cbor.DecodeError as exc:
        return parity.format_error(exc.tag, exc.payload)
    return "ok"


def _raw_row(hex_input: str, observed: str) -> dict:
    if observed == "ok":
        expect: dict = {"accept": True}
    else:
        tag, payload = parity.parse_error(observed)
        expect = {"tag": tag, **payload}
    return {"name": f"edge-{hex_input or 'empty'}", "stage": "raw_decode", "bytes": hex_input,
            "expect": expect, "why": "CD-E5 edge beyond the corpus"}


def test_raw_edges_state_what_python_the_reference_does():
    assert [(h, _python_observation(bytes.fromhex(h))) for h, _ in RAW_EDGES] == RAW_EDGES


def test_go_raw_decode_matches_python_beyond_the_corpus(monkeypatch):
    _needs_go()
    rows = [_raw_row(h, want) for h, want in RAW_EDGES]
    monkeypatch.setattr(parity, "malformed_rows", lambda: rows)
    report = parity_go.run()
    assert report.green, _failures(report)
    assert {r.name for r in report.results if r.kind == "malformed"} == {row["name"] for row in rows}


def test_go_runtime_and_parity_runner_are_gofmt_clean(tmp_path):
    gofmt = shutil.which("gofmt")
    if gofmt is None:
        pytest.skip("gofmt not installed")
    runner = tmp_path / "main.go"
    runner.write_text(parity_go._source())
    runtime = sorted(str(p) for p in (ROOT / "src/taut/gen/runtime").glob("*.go"))
    result = subprocess.run([gofmt, "-l", str(runner), *runtime], capture_output=True, text=True, check=False)
    assert (result.returncode, result.stdout, result.stderr) == (0, "", "")


# optional=MISSING_OK (TautCheckedDecode.md CD-E5, the opt-in exception): `Late` reads an
# absent key as null; `Opt`, plain optional, still requires the key.
PRESENCE_SCHEMA = mk(Msg("Late", F("note", 1, STR, optional=MISSING_OK)),
                     Msg("Opt", F("note", 1, STR, optional=True)))


def _decoder(src: str, name: str) -> str:
    return src[src.index(f"func Try{name}FromCbor("):src.index(f"func {name}FromCbor(")]


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
            wantDecodeError(t, "a0", err, DecodeError{Tag: DecodeErrMissingKey, Key: 1})
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


# A repeated `map<K,V>` entry key is refused whatever K is; the corpus (M13) pins an int key.
KEYS_SCHEMA = mk(Msg("Keys", F("by_name", 1, Map(STR, INT)), F("by_flag", 2, Map(BOOL, INT))))
KEYS_DISTINCT = cbor.dumps({1: [{1: "a", 2: 1}, {1: "b", 2: 2}], 2: [{1: False, 2: 0}, {1: True, 2: 1}]})
KEYS_REPEATED = {
    "name": cbor.dumps({1: [{1: "a", 2: 1}, {1: "a", 2: 2}], 2: []}),
    "flag": cbor.dumps({1: [], 2: [{1: True, 2: 1}, {1: True, 2: 2}]}),
}


def test_python_refuses_a_repeated_str_or_bool_map_key():
    assert codec.decode(KEYS_SCHEMA, "Keys", KEYS_DISTINCT) == {
        "by_name": {"a": 1, "b": 2}, "by_flag": {False: 0, True: 1}}
    for data in KEYS_REPEATED.values():
        with pytest.raises(cbor.DecodeError) as caught:
            codec.decode(KEYS_SCHEMA, "Keys", data)
        assert caught.value.tag == "DuplicateMapKey"


def test_go_map_field_refuses_a_repeated_str_or_bool_key(tmp_path):
    _needs_go()
    scaffold.emit(KEYS_SCHEMA, tmp_path, langs=["go"], services=[], runtime=True)
    go_dir = tmp_path / "go"
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
        }}

        func TestKeysRefusesARepeatedKey(t *testing.T) {{
            for _, input := range []string{{"{KEYS_REPEATED['name'].hex()}", "{KEYS_REPEATED['flag'].hex()}"}} {{
                _, err := decodeKeys(t, input)
                got, ok := err.(*DecodeError)
                if !ok || got.Tag != DecodeErrDuplicateMapKey {{
                    t.Fatalf("%s: got %T %v, want DuplicateMapKey", input, err, err)
                }}
            }}
        }}
    """))
    _run_go_tests(go_dir, tmp_path, "TestKeysDecodesDistinctKeys", "TestKeysRefusesARepeatedKey")


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
            "fmt"
            "strings"
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

        func mustHex(s string) []byte {{
            b, err := hex.DecodeString(s)
            if err != nil {{
                panic(err)
            }}
            return b
        }}

        func hexOf(b []byte) string {{
            return hex.EncodeToString(b)
        }}

        func mustPanicContains(t *testing.T, want string, fn func()) {{
            t.Helper()
            defer func() {{
                r := recover()
                if r == nil {{
                    t.Fatalf("expected panic containing %q", want)
                }}
                if !strings.Contains(fmt.Sprint(r), want) {{
                    t.Fatalf("panic = %v, want substring %q", r, want)
                }}
            }}()
            fn()
        }}

        {_go_residual_rows("residualCorpus", residual_rows)}

        {_go_ext_rows("extCorpus", ext_rows)}

        {_go_residual_rows("fuzzResidualCorpus", fuzz_residual_rows)}

        {_go_fuzz_rows("fuzzExtCorpus", fuzz_ext_rows)}

        func TestResExtResidualCorpus(t *testing.T) {{
            mismatches := 0
            for _, row := range residualCorpus {{
                got := hexOf(Encode(HostFromCbor(Decode(mustHex(row.wire))).ToCbor()))
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
                    typed := DecisionFromCbor(Decode(mustHex(row.value)))
                    got := hexOf(ExtSet(mustHex(row.host), row.tag, typed.ToCbor()))
                    if got != row.expect {{
                        t.Errorf("%s set: got %s want %s", row.note, got, row.expect)
                        mismatches++
                    }}
                case "get":
                    got, ok := ExtGet(mustHex(row.host), row.tag)
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
                    typed := DecisionFromCbor(got)
                    if gotHex := hexOf(Encode(typed.ToCbor())); gotHex != row.expect {{
                        t.Errorf("%s get: got %s want %s", row.note, gotHex, row.expect)
                        mismatches++
                    }}
                case "clear":
                    got := hexOf(ExtClear(mustHex(row.host), row.tag))
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

        func TestResExtInvalidCases(t *testing.T) {{
            mustPanicContains(t, "below band", func() {{
                ExtSet([]byte{{0xff}}, BandStart-1, CMap(nil))
            }})
            mustPanicContains(t, "below band", func() {{
                ExtGet([]byte{{0xff}}, BandStart-1)
            }})
            mustPanicContains(t, "below band", func() {{
                ExtClear([]byte{{0xff}}, BandStart-1)
            }})
            mustPanicContains(t, "not a map", func() {{
                ExtSet(mustHex("01"), BandStart, CMap(nil))
            }})
            mustPanicContains(t, "not a map", func() {{
                ExtGet(mustHex("01"), BandStart)
            }})
            mustPanicContains(t, "not a map", func() {{
                ExtClear(mustHex("01"), BandStart)
            }})
        }}

        func TestResExtFuzzFixedSeed(t *testing.T) {{
            mismatches := 0
            for _, row := range fuzzResidualCorpus {{
                got := hexOf(Encode(HostFromCbor(Decode(mustHex(row.wire))).ToCbor()))
                if got != row.wire {{
                    t.Errorf("%s residual: got %s want %s seed=0x5504", row.note, got, row.wire)
                    mismatches++
                }}
            }}
            for _, row := range fuzzExtCorpus {{
                typed := DecisionFromCbor(Decode(mustHex(row.value)))
                setBytes := ExtSet(mustHex(row.host), row.tag, typed.ToCbor())
                if got := hexOf(setBytes); got != row.setExpect {{
                    t.Errorf("%s set: got %s want %s seed=0x5504", row.note, got, row.setExpect)
                    mismatches++
                    continue
                }}
                gotCbor, ok := ExtGet(setBytes, row.tag)
                if !ok {{
                    t.Errorf("%s get: got absent want %s seed=0x5504", row.note, row.getExpect)
                    mismatches++
                }} else {{
                    gotTyped := DecisionFromCbor(gotCbor)
                    if got := hexOf(Encode(gotTyped.ToCbor())); got != row.getExpect {{
                        t.Errorf("%s get: got %s want %s seed=0x5504", row.note, got, row.getExpect)
                        mismatches++
                    }}
                }}
                if got := hexOf(ExtClear(setBytes, row.tag)); got != row.clearExpect {{
                    t.Errorf("%s clear: got %s want %s seed=0x5504", row.note, got, row.clearExpect)
                    mismatches++
                }}
            }}
            t.Logf("resext fuzz seed=0x5504 iterations=%d mismatches=%d", len(fuzzResidualCorpus), mismatches)
        }}
    """))
    return go_dir


def test_go_resext_phase2_harness(tmp_path):
    if shutil.which("go") is None:
        pytest.skip("go not installed")

    go_dir = _write_resext_go_harness(tmp_path)
    env = _go_test_env(tmp_path)
    result = subprocess.run(
        ["go", "test", "-v"],
        cwd=go_dir,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    assert result.returncode == 0, result.stdout
