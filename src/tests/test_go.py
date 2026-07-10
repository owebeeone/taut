"""Go generator: native structs + typed-const enums + CBOR codec, forward-compat
residual, PascalCase exported fields. (go-build parity verified out-of-band.)"""

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
from taut.corpus import resext_build as resext
from taut.gen import go
from taut.gen import scaffold
from taut.ir.dsl import FLOAT, INT, F, List, Map, Msg, schema as mk
from taut.ir.load import load_schema
from taut.ir.shapes import BAND_START
from taut.wire import codec

ROOT = Path(__file__).resolve().parents[2]
RAZEL = load_schema(IR_PATH.parent / "razel.taut.py")
RESEXT = load_schema(resext.IR_PATH)
PARITY_SCHEMA = load_schema(ROOT / "ir/parity_int.taut.py")
PARITY_INT_VECTORS = ROOT / "corpus/parity/int.vectors.json"
PARITY_MALFORMED_VECTORS = ROOT / "corpus/parity/malformed.vectors.json"
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


def _go_i64_lit(s: str) -> str:
    if s == "-9223372036854775808":
        return "(-9223372036854775807 - 1)"
    return s


def _go_parity_int_rows(name: str, rows: list[dict]) -> str:
    lines = [f"var {name} = []intCase{{"]
    for row in rows:
        if row["kind"] != "round_trip":
            continue
        by_id = row["value"]["by_id"]
        if by_id:
            entries = ", ".join(f"{_go_i64_lit(k)}: {_go_i64_lit(v)}" for k, v in by_id)
            by_id_lit = f"map[int64]int64{{{entries}}}"
        else:
            by_id_lit = "map[int64]int64{}"
        lines.append(
            "\t{"
            f"name: {_go_str(row['name'])}, "
            f"n: {_go_i64_lit(row['value']['n'])}, "
            f"byID: {by_id_lit}, "
            f"wire: {_go_str(row['cbor'])}"
            "},"
        )
    lines.append("}")
    return "\n".join(lines)


def _go_parity_encode_fail_rows(name: str, rows: list[dict]) -> str:
    lines = [f"var {name} = []encodeFailCase{{"]
    for row in rows:
        if row["kind"] == "encode_fail":
            lines.append(f"\t{{name: {_go_str(row['name'])}, value: {_go_str(row['value']['n'])}}},")
    lines.append("}")
    return "\n".join(lines)


def _go_parity_malformed_rows(name: str, rows: list[dict]) -> str:
    lines = [f"var {name} = []malformedCase{{"]
    for row in rows:
        expect = row["expect"]
        fields = [
            f"name: {_go_str(row['name'])}",
            f"stage: {_go_str(row['stage'])}",
            f"schema: {_go_str(row.get('schema', ''))}",
            f"wire: {_go_str(row['bytes'])}",
            f"tag: {_go_str(expect['tag'])}",
            "info: -1",
            "major: -1",
            "key: -1",
        ]
        if "info" in expect:
            fields[5] = f"info: {expect['info']}"
        if "major" in expect:
            fields[6] = f"major: {expect['major']}"
        if "key" in expect:
            fields[7] = f"key: {expect['key']}"
        if "expected" in expect:
            fields.append(f"expected: {_go_str(expect['expected'])}")
        if "enum" in expect:
            fields.append(f"enumName: {_go_str(expect['enum'])}")
        if "value" in expect:
            fields.append(f"value: {_go_str(expect['value'])}")
        lines.append("\t{" + ", ".join(fields) + "},")
    lines.append("}")
    return "\n".join(lines)


def _write_parity_go_harness(tmp_path: Path) -> Path:
    scaffold.emit(PARITY_SCHEMA, tmp_path, langs=["go"], services=[], runtime=True)
    go_dir = tmp_path / "go"
    # Baseline smoke test: pin the reviewed set; `lead` rows belong to the
    # governed `tautc parity` gate (corpus/parity/gen_vectors.py).
    int_rows = [r for r in json.loads(PARITY_INT_VECTORS.read_text())["vectors"] if not r.get("lead")]
    malformed_rows = [r for r in json.loads(PARITY_MALFORMED_VECTORS.read_text())["vectors"] if not r.get("lead")]
    harness = textwrap.dedent("""
        package taut

        import (
            "encoding/hex"
            "math/big"
            "reflect"
            "testing"
        )

        type intCase struct {
            name string
            n int64
            byID map[int64]int64
            wire string
        }

        type encodeFailCase struct {
            name string
            value string
        }

        type malformedCase struct {
            name string
            stage string
            schema string
            wire string
            tag string
            info int
            major int
            key int64
            expected string
            enumName string
            value string
        }

        func mustHex(t *testing.T, s string) []byte {
            t.Helper()
            b, err := hex.DecodeString(s)
            if err != nil {
                t.Fatalf("bad hex %q: %v", s, err)
            }
            return b
        }

        func hexOf(b []byte) string {
            return hex.EncodeToString(b)
        }

        @@INT_ROWS@@

        @@ENCODE_FAIL_ROWS@@

        @@MALFORMED_ROWS@@

        func TestParityIntRoundTrips(t *testing.T) {
            for _, row := range intCorpus {
                value := IntBox{N: row.n, ById: row.byID}
                if got := hexOf(Encode(value.ToCbor())); got != row.wire {
                    t.Fatalf("%s encode: got %s want %s", row.name, got, row.wire)
                }
                c, err := TryDecode(mustHex(t, row.wire))
                if err != nil {
                    t.Fatalf("%s decode: %v", row.name, err)
                }
                decoded, err := TryIntBoxFromCbor(c)
                if err != nil {
                    t.Fatalf("%s from_cbor: %v", row.name, err)
                }
                if decoded.N != row.n || !reflect.DeepEqual(decoded.ById, row.byID) {
                    t.Fatalf("%s value: got %+v want n=%d byID=%+v", row.name, decoded, row.n, row.byID)
                }
                if got := hexOf(Encode(decoded.ToCbor())); got != row.wire {
                    t.Fatalf("%s re-encode: got %s want %s", row.name, got, row.wire)
                }
            }
            t.Logf("round_trip=%d", len(intCorpus))
        }

        func TestParityEncodeFailRowsAreOutsideNativeInt64(t *testing.T) {
            two63 := new(big.Int).Lsh(big.NewInt(1), 63)
            min := new(big.Int).Neg(new(big.Int).Set(two63))
            max := new(big.Int).Sub(new(big.Int).Set(two63), big.NewInt(1))
            for _, row := range encodeFailCorpus {
                n, ok := new(big.Int).SetString(row.value, 10)
                if !ok {
                    t.Fatalf("%s: bad integer %q", row.name, row.value)
                }
                if n.Cmp(min) >= 0 && n.Cmp(max) <= 0 {
                    t.Fatalf("%s: %s is representable as int64", row.name, row.value)
                }
            }
            t.Logf("encode_fail_unrepresentable=%d", len(encodeFailCorpus))
        }

        func malformedError(t *testing.T, row malformedCase) error {
            t.Helper()
            if row.stage == "raw_decode" {
                _, err := TryDecode(mustHex(t, row.wire))
                return err
            }
            c, err := TryDecode(mustHex(t, row.wire))
            if err != nil {
                return err
            }
            switch row.stage {
            case "from_cbor":
                switch row.schema {
                case "IntBox":
                    _, err = TryIntBoxFromCbor(c)
                    return err
                default:
                    t.Fatalf("unknown from_cbor schema %s", row.schema)
                }
            case "from_wire":
                switch row.schema {
                case "Mode":
                    _, err = TryModeFromCbor(c)
                    return err
                default:
                    t.Fatalf("unknown from_wire schema %s", row.schema)
                }
            default:
                t.Fatalf("unknown stage %s", row.stage)
            }
            return nil
        }

        func expectDecodeError(t *testing.T, row malformedCase, err error) {
            t.Helper()
            if err == nil {
                t.Fatalf("%s: expected %s, got nil", row.name, row.tag)
            }
            derr, ok := err.(*DecodeError)
            if !ok {
                t.Fatalf("%s: got %T %v, want *DecodeError", row.name, err, err)
            }
            if derr.Tag != row.tag {
                t.Fatalf("%s: tag got %s want %s (%v)", row.name, derr.Tag, row.tag, err)
            }
            if row.info >= 0 && int(derr.Info) != row.info {
                t.Fatalf("%s: info got %d want %d", row.name, derr.Info, row.info)
            }
            if row.major >= 0 && int(derr.Major) != row.major {
                t.Fatalf("%s: major got %d want %d", row.name, derr.Major, row.major)
            }
            if row.key >= 0 && derr.Key != row.key {
                t.Fatalf("%s: key got %d want %d", row.name, derr.Key, row.key)
            }
            if row.expected != "" && derr.Expected != row.expected {
                t.Fatalf("%s: expected got %s want %s", row.name, derr.Expected, row.expected)
            }
            if row.enumName != "" && derr.Enum != row.enumName {
                t.Fatalf("%s: enum got %s want %s", row.name, derr.Enum, row.enumName)
            }
            if row.value != "" && derr.Value != row.value {
                t.Fatalf("%s: value got %s want %s", row.name, derr.Value, row.value)
            }
        }

        func TestParityMalformedCorpus(t *testing.T) {
            for _, row := range malformedCorpus {
                expectDecodeError(t, row, malformedError(t, row))
            }
            t.Logf("malformed=%d", len(malformedCorpus))
        }
    """)
    harness = harness.replace("@@INT_ROWS@@", _go_parity_int_rows("intCorpus", int_rows))
    harness = harness.replace("@@ENCODE_FAIL_ROWS@@", _go_parity_encode_fail_rows("encodeFailCorpus", int_rows))
    harness = harness.replace("@@MALFORMED_ROWS@@", _go_parity_malformed_rows("malformedCorpus", malformed_rows))
    (go_dir / "parity_test.go").write_text(harness)
    return go_dir


def test_go_shared_parity_harness(tmp_path):
    if shutil.which("go") is None:
        pytest.skip("go not installed")

    go_dir = _write_parity_go_harness(tmp_path)
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
    assert "round_trip=7" in result.stdout
    assert "encode_fail_unrepresentable=3" in result.stdout
    assert "malformed=12" in result.stdout


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
