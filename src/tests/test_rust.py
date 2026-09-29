"""Rust generator/runtime float coverage.

The compiled crate may not be checked out beside this repository, so the runtime
test builds the vendored cbor.rs directly with rustc and drives it with the
shared float vector corpus.
"""

from __future__ import annotations

import json
import random
import shutil
import subprocess
import textwrap
from pathlib import Path

import pytest

from taut import cli
from taut import ext as py_ext
from taut.corpus import glade_build, parity, parity_rust, toolchains
from taut.gen import scaffold
from taut.gen import rust
from taut.ir.dsl import BOOL, FLOAT, INT, MISSING_OK, STR, Enum, F, List, Map, Msg, Ref, schema
from taut.ir.load import load_schema
from taut.ir.shapes import BAND_START
from taut.wire import cbor as py_cbor
from taut.wire import codec

ROOT = Path(__file__).resolve().parents[2]
RESEXT_SCHEMA = load_schema(ROOT / "ir" / "resext.taut.py")
PARITY_SCHEMA = load_schema(ROOT / "ir" / "parity_int.taut.py")
# The one Rust runtime, which `tautc gen --with-runtime` vendors as `cbor.rs`.
CBOR_RS = ROOT / "src" / "taut" / "gen" / "runtime" / "cbor_fail_closed.rs"


def test_rust_generator_emits_float_scalar_codec():
    s = schema(Msg("M",
                   F("x", 1, FLOAT),
                   F("maybe", 2, FLOAT, optional=True),
                   F("xs", 3, List(FLOAT)),
                   F("by_id", 4, Map(INT, FLOAT))))
    out = rust._emit(s, {})

    assert "pub x: f64," in out
    assert "(1, Cbor::Float(self.x))" in out
    assert "Some(v) => Cbor::Float(*v)" in out
    assert "Cbor::Array(self.xs.iter().map(|x| Cbor::Float(*x)).collect())" in out
    assert "(2, Cbor::Float(*v))" in out
    # The corpus emitter decodes as the package codegen does: fail-closed.
    assert "use crate::cbor::{Cbor, DecodeError};" in out
    assert "x: c.try_get(1)?.try_float()?," in out
    assert "maybe: { let v = c.try_get(2)?; if v.is_null() { None } else { Some(v.try_float()?) } }," in out
    assert "pub fn roundtrip(message: &str, bytes: &[u8]) -> Result<Vec<u8>, DecodeError> {" in out
    assert "let c = crate::cbor::try_decode(bytes)?;" in out
    assert '"M" => M::from_cbor(&c).map(|v| crate::cbor::encode(&v.to_cbor())),' in out
    assert '.expect("decode: M")' not in out


def test_rust_runtime_matches_float_vectors(tmp_path):
    rustc = shutil.which("rustc")
    if rustc is None:
        pytest.skip("rustc not available")

    vectors = json.loads((ROOT / "corpus" / "float_vectors.json").read_text())
    rows = ",\n".join(
        f'        ("{row["note"]}", 0x{row["f64"]}u64, "{row["cbor"]}")'
        for row in vectors
    )
    cbor_path = CBOR_RS.as_posix()
    test_rs = tmp_path / "float_vectors.rs"
    test_rs.write_text(textwrap.dedent(f"""
        extern crate alloc;
        #[path = "{cbor_path}"]
        mod cbor;

        use cbor::{{encode, try_decode, Cbor}};

        static VECTORS: &[(&str, u64, &str)] = &[
{rows}
        ];

        fn unhex(s: &str) -> Vec<u8> {{
            (0..s.len())
                .step_by(2)
                .map(|i| u8::from_str_radix(&s[i..i + 2], 16).unwrap())
                .collect()
        }}

        fn hexof(b: &[u8]) -> String {{
            use std::fmt::Write as _;
            b.iter().fold(String::new(), |mut s, x| {{
                let _ = write!(s, "{{x:02x}}");
                s
            }})
        }}

        #[test]
        fn float_vector_encode_decode_parity() {{
            for (note, bits, cbor_hex) in VECTORS {{
                let value = f64::from_bits(*bits);
                assert_eq!(hexof(&encode(&Cbor::Float(value))), *cbor_hex, "encode {{note}}");

                let decoded = try_decode(&unhex(cbor_hex)).unwrap();
                assert_eq!(hexof(&encode(&decoded)), *cbor_hex, "re-encode {{note}}");
                if !note.starts_with("nan") {{
                    assert_eq!(decoded.try_float().unwrap().to_bits(), *bits, "decode bits {{note}}");
                }}
            }}
        }}

        #[test]
        fn float_decode_accepts_all_widths() {{
            for hx in ["f93c00", "fa3f800000", "fb3ff0000000000000"] {{
                let decoded = try_decode(&unhex(hx)).unwrap();
                assert_eq!(decoded.try_float().unwrap().to_bits(), 1.0f64.to_bits(), "{{hx}}");
            }}
        }}
    """))

    bin_path = tmp_path / "float_vectors"
    subprocess.run([rustc, "--edition", "2021", "--test", str(test_rs), "-o", str(bin_path)], check=True)
    subprocess.run([str(bin_path)], check=True)


def _rs_str(s: str) -> str:
    return json.dumps(s)


def _opt_rs_str(s: object | None) -> str:
    return f"Some({_rs_str(str(s))})" if s is not None else "None"


def _opt_rs_u8(n: object | None) -> str:
    return f"Some({int(n)}u8)" if n is not None else "None"


def _rust_residual_rows() -> str:
    vectors = json.loads((ROOT / "corpus" / "residual_vectors.json").read_text())
    return ",\n".join(
        f"        ({_rs_str(row['note'])}, {_rs_str(row['wire'])})"
        for row in vectors
    )


def _rust_ext_rows() -> str:
    vectors = json.loads((ROOT / "corpus" / "ext_vectors.json").read_text())
    return ",\n".join(
        "        ExtRow { "
        f"op: {_rs_str(row['op'])}, "
        f"note: {_rs_str(row['note'])}, "
        f"host: {_rs_str(row['host'])}, "
        f"tag: {row['tag']}i64, "
        f"value: {_rs_str(row.get('value', ''))}, "
        f"expect: {_rs_str(row['expect'])} "
        "}"
        for row in vectors
    )


def _random_cbor_value(rng: random.Random, depth: int = 0):
    kind = rng.randrange(6 if depth == 0 else 5)
    if kind == 0:
        return rng.randint(-1000, 1000)
    if kind == 1:
        return f"s{rng.randrange(10_000)}"
    if kind == 2:
        return bytes(rng.randrange(256) for _ in range(rng.randrange(0, 8)))
    if kind == 3:
        return bool(rng.randrange(2))
    if kind == 4:
        return None
    return [_random_cbor_value(rng, depth + 1) for _ in range(rng.randrange(0, 4))]


def _resext_fuzz_rows(seed: int, count: int = 1000) -> list[dict]:
    rng = random.Random(seed)
    rows = []
    for i in range(count):
        host_map = {
            1: rng.randint(0, 10_000),
            2: f"name{rng.randrange(10_000)}",
            5: rng.randint(0, 10_000),
            3: _random_cbor_value(rng),  # interleaved unknown between known tags 2 and 5
            BAND_START + 1 + rng.randrange(1, 512): _random_cbor_value(rng),
        }
        for _ in range(rng.randrange(0, 4)):
            tag = rng.randrange(0, 1 << 21)
            if tag not in (1, 2, 3, 5):
                host_map[tag] = _random_cbor_value(rng)
        host = py_cbor.dumps(host_map)
        roundtrip = codec.encode(RESEXT_SCHEMA, "Host", codec.decode(RESEXT_SCHEMA, "Host", host))

        ext_tag = BAND_START + 1 + rng.randrange(0, 1024)
        decision = {"backend": f"b{rng.randrange(10_000)}", "hops": rng.randrange(0, 20)}
        strapped = py_ext.ext_set(RESEXT_SCHEMA, host, "Decision", ext_tag, decision)
        got = py_ext.ext_get(RESEXT_SCHEMA, strapped, "Decision", ext_tag)
        cleared = py_ext.ext_clear(strapped, ext_tag)
        assert got == decision
        rows.append({
            "note": f"seed{seed}-case{i}",
            "host": host.hex(),
            "roundtrip": roundtrip.hex(),
            "tag": ext_tag,
            "value": codec.encode(RESEXT_SCHEMA, "Decision", decision).hex(),
            "expect_set": strapped.hex(),
            "expect_get": codec.encode(RESEXT_SCHEMA, "Decision", got).hex(),
            "expect_clear": cleared.hex(),
        })
    return rows


def _rust_fuzz_rows(seed: int, count: int = 1000) -> str:
    return ",\n".join(
        "        FuzzRow { "
        f"note: {_rs_str(row['note'])}, "
        f"host: {_rs_str(row['host'])}, "
        f"roundtrip: {_rs_str(row['roundtrip'])}, "
        f"tag: {row['tag']}i64, "
        f"value: {_rs_str(row['value'])}, "
        f"expect_set: {_rs_str(row['expect_set'])}, "
        f"expect_get: {_rs_str(row['expect_get'])}, "
        f"expect_clear: {_rs_str(row['expect_clear'])} "
        "}"
        for row in _resext_fuzz_rows(seed, count)
    )


def test_rust_resext_residual_ext_and_fuzz_vectors(tmp_path):
    rustc = shutil.which("rustc")
    if rustc is None:
        pytest.skip("rustc not available")

    generated = tmp_path / "generated"
    scaffold.emit(
        RESEXT_SCHEMA,
        generated,
        langs=["rust"],
        services=[],
        runtime=True,
        forward_compat=True,
    )
    rust_dir = generated / "rust"
    assert (rust_dir / "api.rs").exists()
    assert (rust_dir / "cbor.rs").exists()
    assert (rust_dir / "ext.rs").exists()

    seed = 0x5EED_5245
    residual_rows = _rust_residual_rows()
    ext_rows = _rust_ext_rows()
    fuzz_rows = _rust_fuzz_rows(seed)
    api_path = (rust_dir / "api.rs").as_posix()
    cbor_path = (rust_dir / "cbor.rs").as_posix()
    ext_path = (rust_dir / "ext.rs").as_posix()
    test_rs = tmp_path / "resext_vectors.rs"
    test_rs.write_text(textwrap.dedent(f"""
        extern crate alloc;
        #[path = "{cbor_path}"]
        mod cbor;
        #[path = "{api_path}"]
        mod api;
        #[path = "{ext_path}"]
        mod ext;

        use api::{{Decision, Host}};
        use cbor::{{encode, try_decode, Cbor, DecodeError, MapKey}};

        static RESIDUAL: &[(&str, &str)] = &[
{residual_rows}
        ];

        struct ExtRow {{
            op: &'static str,
            note: &'static str,
            host: &'static str,
            tag: i64,
            value: &'static str,
            expect: &'static str,
        }}

        static EXT: &[ExtRow] = &[
{ext_rows}
        ];

        struct FuzzRow {{
            note: &'static str,
            host: &'static str,
            roundtrip: &'static str,
            tag: i64,
            value: &'static str,
            expect_set: &'static str,
            expect_get: &'static str,
            expect_clear: &'static str,
        }}

        static FUZZ_SEED: u64 = {seed}u64;
        static FUZZ: &[FuzzRow] = &[
{fuzz_rows}
        ];

        fn unhex(s: &str) -> Vec<u8> {{
            (0..s.len())
                .step_by(2)
                .map(|i| u8::from_str_radix(&s[i..i + 2], 16).unwrap())
                .collect()
        }}

        fn hexof(b: &[u8]) -> String {{
            use std::fmt::Write as _;
            b.iter().fold(String::new(), |mut s, x| {{
                let _ = write!(s, "{{x:02x}}");
                s
            }})
        }}

        fn decision_from_wire(hex: &str) -> Decision {{
            let c = try_decode(&unhex(hex)).unwrap();
            Decision::from_cbor(&c).unwrap()
        }}

        #[test]
        fn residual_vectors_roundtrip_byte_exactly() {{
            for (note, wire) in RESIDUAL {{
                let decoded = try_decode(&unhex(wire)).unwrap();
                let host = Host::from_cbor(&decoded).unwrap();
                assert_eq!(hexof(&encode(&host.to_cbor())), *wire, "residual {{note}}");
            }}
        }}

        #[test]
        fn ext_vectors_match_python_oracle_through_generated_decision() {{
            for row in EXT {{
                let host = unhex(row.host);
                match row.op {{
                    "set" => {{
                        let decision = decision_from_wire(row.value);
                        let got = ext::ext_set(&host, row.tag, decision.to_cbor()).unwrap();
                        assert_eq!(hexof(&got), row.expect, "ext set {{}}", row.note);
                    }}
                    "get" => {{
                        let got = ext::ext_get(&host, row.tag).unwrap();
                        if row.expect == "null" {{
                            assert!(got.is_none(), "ext get absent {{}}", row.note);
                        }} else {{
                            let decision = Decision::from_cbor(got.as_ref().unwrap()).unwrap();
                            assert_eq!(
                                hexof(&encode(&decision.to_cbor())),
                                row.expect,
                                "ext get {{}}",
                                row.note
                            );
                        }}
                    }}
                    "clear" => {{
                        let got = ext::ext_clear(&host, row.tag).unwrap();
                        assert_eq!(hexof(&got), row.expect, "ext clear {{}}", row.note);
                    }}
                    _ => panic!("unknown op {{}}", row.op),
                }}
            }}
        }}

        // A tag below the band is the caller's error, not the input's: each helper
        // panics before it reads the host, whose bytes here (none) would be Truncated.
        #[test]
        #[should_panic(expected = "below the extension band")]
        fn ext_set_rejects_below_band_before_decoding_host() {{
            let _ = ext::ext_set(&[], (1 << 20) - 1, Cbor::Null);
        }}

        #[test]
        #[should_panic(expected = "below the extension band")]
        fn ext_get_rejects_below_band_before_decoding_host() {{
            let _ = ext::ext_get(&[], (1 << 20) - 1);
        }}

        #[test]
        #[should_panic(expected = "below the extension band")]
        fn ext_clear_rejects_below_band_before_decoding_host() {{
            let _ = ext::ext_clear(&[], (1 << 20) - 1);
        }}

        #[test]
        fn ext_helpers_refuse_a_host_that_is_not_a_map() {{
            let decision = Decision {{ backend: "b7".to_string(), hops: 1, wire_residual: vec![] }};
            let host = encode(&Cbor::Int(1));
            let not_map = DecodeError::WrongType {{ expected: "map" }};
            assert_eq!(ext::ext_set(&host, 1 << 20, decision.to_cbor()), Err(not_map.clone()));
            assert_eq!(ext::ext_get(&host, 1 << 20), Err(not_map.clone()));
            assert_eq!(ext::ext_clear(&host, 1 << 20), Err(not_map));
        }}

        #[test]
        fn ext_helpers_report_a_malformed_host_as_its_decode_error() {{
            let tag = 1 << 20;
            assert_eq!(ext::ext_get(&[0xa1, 0x01], tag), Err(DecodeError::Truncated));
            assert_eq!(ext::ext_clear(&[0xa0, 0x00], tag), Err(DecodeError::TrailingBytes));
            assert_eq!(
                ext::ext_set(&[0xa2, 0x01, 0x00, 0x01, 0x00], tag, Cbor::Null),
                Err(DecodeError::DuplicateMapKey(MapKey::Int(1)))
            );
            assert_eq!(ext::ext_get(&[0xa1, 0x61, 0x78, 0x00], tag), Err(DecodeError::NonIntegerMapKey));
            // The band's first tag is the helpers' to use.
            assert_eq!(ext::ext_get(&[0xa0], tag), Ok(None));
        }}

        #[test]
        fn fixed_seed_resext_fuzz_matches_python_oracle() {{
            let mut mismatches = 0usize;
            for row in FUZZ {{
                let host = unhex(row.host);

                let decoded = try_decode(&host).unwrap();
                let typed = Host::from_cbor(&decoded).unwrap();
                let roundtrip = hexof(&encode(&typed.to_cbor()));
                if roundtrip != row.roundtrip {{
                    eprintln!(
                        "residual mismatch seed={{}} note={{}} input={{}} got={{}} expect={{}}",
                        FUZZ_SEED, row.note, row.host, roundtrip, row.roundtrip
                    );
                    mismatches += 1;
                }}

                let decision = decision_from_wire(row.value);
                let set = ext::ext_set(&host, row.tag, decision.to_cbor()).expect(row.note);
                let set_hex = hexof(&set);
                if set_hex != row.expect_set {{
                    eprintln!(
                        "ext_set mismatch seed={{}} note={{}} input={{}} got={{}} expect={{}}",
                        FUZZ_SEED, row.note, row.host, set_hex, row.expect_set
                    );
                    mismatches += 1;
                }}

                match ext::ext_get(&set, row.tag).expect(row.note) {{
                    Some(c) => {{
                        let got = Decision::from_cbor(&c).expect(row.note);
                        let get_hex = hexof(&encode(&got.to_cbor()));
                        if get_hex != row.expect_get {{
                            eprintln!(
                                "ext_get mismatch seed={{}} note={{}} input={{}} got={{}} expect={{}}",
                                FUZZ_SEED, row.note, set_hex, get_hex, row.expect_get
                            );
                            mismatches += 1;
                        }}
                    }}
                    None => {{
                        eprintln!("ext_get missing seed={{}} note={{}} input={{}}", FUZZ_SEED, row.note, set_hex);
                        mismatches += 1;
                    }}
                }}

                let clear_hex = hexof(&ext::ext_clear(&set, row.tag).expect(row.note));
                if clear_hex != row.expect_clear {{
                    eprintln!(
                        "ext_clear mismatch seed={{}} note={{}} input={{}} got={{}} expect={{}}",
                        FUZZ_SEED, row.note, set_hex, clear_hex, row.expect_clear
                    );
                    mismatches += 1;
                }}
            }}
            assert_eq!(mismatches, 0, "fixed-seed fuzz mismatches for seed {{FUZZ_SEED}}");
        }}
    """))

    bin_path = tmp_path / "resext_vectors"
    subprocess.run([rustc, "--edition", "2021", "--test", str(test_rs), "-o", str(bin_path)], check=True)
    subprocess.run([str(bin_path)], check=True)


# =============================================================================
# The fail-closed Rust codec — the untrusted-boundary hardening, and since
# v0.10.0 the only Rust codec: the legacy (fail-open) codec, its `--legacy-codec`
# opt-out and its runtime template are gone (TautCheckedDecode.md question 5).
# These tests pin its shape and its behaviour on every decode path.
# =============================================================================

# A schema exercising every scalar + an enum + optional + collections, so the
# fallible codegen is checked on each decode path.
_FC = schema(
    Enum("Color", red=0, green=1, blue=2),
    Msg("M",
        F("n", 1, INT),
        F("name", 2, STR),
        F("c", 3, Ref("Color")),
        F("maybe", 4, INT, optional=True),
        F("ns", 5, List(INT)),
        F("by_id", 6, Map(INT, INT))),
)


def _rust_parity_int_rows() -> tuple[str, str]:
    # Baseline smoke test: pin the reviewed set; `lead` rows are the governed
    # `tautc parity` gate's job (see corpus/parity/gen_vectors.py).
    rows = [r for r in json.loads((ROOT / "corpus" / "parity" / "int.vectors.json").read_text())["vectors"]
            if not r.get("lead")]
    round_trip = []
    encode_fail = []
    for row in rows:
        if row["kind"] == "round_trip":
            pairs = ", ".join(
                f"({_rs_str(k)}, {_rs_str(v)})"
                for k, v in row["value"]["by_id"]
            )
            round_trip.append(
                "        IntRow { "
                f"name: {_rs_str(row['name'])}, "
                f"cbor: {_rs_str(row['cbor'])}, "
                f"n: {_rs_str(row['value']['n'])}, "
                f"by_id: &[{pairs}] "
                "}"
            )
        elif row["kind"] == "encode_fail":
            encode_fail.append(
                "        EncodeFailRow { "
                f"name: {_rs_str(row['name'])}, "
                f"value: {_rs_str(row['value']['n'])}, "
                f"tag: {_rs_str(row['expect']['tag'])} "
                "}"
            )
        else:
            raise AssertionError(f"unknown parity int vector kind {row['kind']!r}")
    return ",\n".join(round_trip), ",\n".join(encode_fail)


def _rust_parity_malformed_rows() -> str:
    rows = [r for r in json.loads((ROOT / "corpus" / "parity" / "malformed.vectors.json").read_text())["vectors"]
            if not r.get("lead")]
    out = []
    for row in rows:
        expect = row["expect"]
        out.append(
            "        MalformedRow { "
            f"name: {_rs_str(row['name'])}, "
            f"stage: {_rs_str(row['stage'])}, "
            f"schema: {_opt_rs_str(row.get('schema'))}, "
            f"bytes: {_rs_str(row['bytes'])}, "
            f"tag: {_rs_str(expect['tag'])}, "
            f"key: {_opt_rs_str(expect.get('key'))}, "
            f"expected: {_opt_rs_str(expect.get('expected'))}, "
            f"enum_name: {_opt_rs_str(expect.get('enum'))}, "
            f"value: {_opt_rs_str(expect.get('value'))}, "
            f"info: {_opt_rs_u8(expect.get('info'))}, "
            f"major: {_opt_rs_u8(expect.get('major'))} "
            "}"
        )
    return ",\n".join(out)


def test_rust_fail_closed_emits_fallible_from_cbor_and_i64_ints():
    rs = scaffold.rust_api(_FC)
    # from_cbor is fallible and never panics on input
    assert "pub fn from_cbor(c: &Cbor) -> Result<Self, DecodeError>" in rs
    assert "use crate::cbor::{Cbor, DecodeError};" in rs
    # int fields keep the i64 carrier (the frozen wire int subset); an out-of-i64
    # wire int is a typed decode error, not a silent u64 wrap or a wider carry
    assert "pub n: i64," in rs
    assert "pub maybe: Option<i64>," in rs
    # decode uses the fallible runtime accessors with `?`-propagation
    assert "n: c.try_get(1)?.try_int()?," in rs
    assert "name: c.try_get(2)?.try_text()?," in rs
    # enum decode is fallible on both from_wire and the int accessor
    assert "c: Color::from_wire(c.try_get(3)?.try_int()?)?," in rs
    # optional decode threads the fallible get + accessor
    assert "maybe: { let v = c.try_get(4)?; if v.is_null() { None } else { Some(v.try_int()?) } }," in rs


def test_rust_missing_ok_only_relaxes_selected_optional_slot():
    s = schema(Msg("M", F("old", 1, STR, optional=True),
                   F("new", 2, STR, optional=MISSING_OK)))
    rs = scaffold.rust_api(s)
    assert "old: { let v = c.try_get(1)?; if v.is_null() { None } else { Some(v.try_text()?) } }," in rs
    assert "new: { let v = c.try_get_opt(2)?; match v { None => None, Some(v) => if v.is_null() { None } else { Some(v.try_text()?) } } }," in rs


def test_rust_fail_closed_enum_from_wire_is_fallible():
    rs = scaffold.rust_api(_FC)
    assert "pub fn from_wire(v: i64) -> Result<Self, DecodeError>" in rs
    assert 'return Err(DecodeError::UnknownEnum { enum_name: "Color", value: v })' in rs
    # wire() returns the i64 carrier so `Cbor::Int(x.wire())` type-checks
    assert "pub fn wire(self) -> i64" in rs


def test_a_repeated_map_field_key_is_reported_as_the_key_itself():
    """Question 9: each key kind of a `map<K,V>` field reports its repeated key itself,
    converted into the runtime's `MapKey`, never an entry's index or a stand-in number."""
    s = schema(Msg("M", F("by_int", 1, Map(INT, INT)), F("by_text", 2, Map(STR, INT)),
                   F("by_flag", 3, Map(BOOL, INT))))
    rs = scaffold.rust_api(s)
    assert rs.count("return Err(DecodeError::DuplicateMapKey(k.into()));") == 3
    assert "enumerate()" not in rs and "i as i64" not in rs and "i64::from(k)" not in rs


def test_the_legacy_codec_is_gone(tmp_path):
    """Question 5: the fail-closed codec is the only Rust codec. Neither `emit` nor
    `rust_api` takes `fail_closed`, no legacy runtime template is left, and the vendored
    `cbor.rs` is the fail-closed runtime, with no panicking `decode` or accessor."""
    with pytest.raises(TypeError, match="fail_closed"):
        scaffold.emit(_FC, tmp_path / "legacy", langs=["rust"], services=[], fail_closed=False)
    with pytest.raises(TypeError, match="fail_closed"):
        scaffold.emit(_FC, tmp_path / "legacy", langs=["rust"], services=[], fail_closed=True)
    with pytest.raises(TypeError, match="fail_closed"):
        scaffold.rust_api(_FC, fail_closed=True)
    assert not (tmp_path / "legacy").exists()
    assert not scaffold._runtime_exists("cbor.rs")

    generated = tmp_path / "gen"
    scaffold.emit(_FC, generated, langs=["rust"], services=[], runtime=True)
    api = (generated / "rust" / "api.rs").read_text()
    assert "pub fn from_cbor(c: &Cbor) -> Result<Self, DecodeError>" in api
    assert "DEPRECATED" not in api and "panic!" not in api
    runtime = (generated / "rust" / "cbor.rs").read_text()
    assert runtime == CBOR_RS.read_text()
    assert "pub fn try_decode" in runtime
    assert "panic!" not in runtime
    for gone in ("decode", "get", "get_opt", "int", "float", "text", "bytes", "boolean", "array"):
        assert f"pub fn {gone}(" not in runtime, gone


def test_tautc_gen_refuses_legacy_codec_and_takes_fail_closed_as_a_no_op(tmp_path, capsys):
    ir = (ROOT / "ir" / "parity_int.taut.py").as_posix()
    base = ["gen", ir, "-l", "rust", "--api-only", "--with-runtime"]
    with pytest.raises(SystemExit) as refused:
        cli.main([*base, "-o", str(tmp_path / "legacy"), "--legacy-codec"])
    assert refused.value.code == 2
    assert "--legacy-codec" in capsys.readouterr().err
    assert not (tmp_path / "legacy").exists()

    assert cli.main([*base, "-o", str(tmp_path / "plain")]) == 0
    assert "--fail-closed" not in capsys.readouterr().err
    assert cli.main([*base, "-o", str(tmp_path / "flag"), "--fail-closed"]) == 0
    assert "--fail-closed is a no-op" in capsys.readouterr().err
    for name in ("api.rs", "cbor.rs", "ext.rs"):
        plain = (tmp_path / "plain" / "rust" / name).read_text()
        assert (tmp_path / "flag" / "rust" / name).read_text() == plain, name


def test_rust_fail_closed_runtime_decode_is_fail_closed(tmp_path):
    """rustc-driven: the hardened api.rs + cbor.rs decode every malformed /
    truncated / unknown-enum / wrong-type / trailing-byte / out-of-subset-int
    input to a typed error (never a panic); i64 extremes round-trip and a CBOR
    integer outside the frozen i64 subset is rejected (never wrapped)."""
    rustc = shutil.which("rustc")
    if rustc is None:
        pytest.skip("rustc not available")

    generated = tmp_path / "generated"
    scaffold.emit(_FC, generated, langs=["rust"], services=[], runtime=True)
    rust_dir = generated / "rust"
    api_path = (rust_dir / "api.rs").as_posix()
    cbor_path = (rust_dir / "cbor.rs").as_posix()
    # The hardened cbor.rs uses `alloc::…`; alias alloc->std for the std test bin.
    test_rs = tmp_path / "fail_closed.rs"
    test_rs.write_text(textwrap.dedent(f"""
        extern crate alloc;
        #[path = "{cbor_path}"]
        mod cbor;
        #[path = "{api_path}"]
        mod api;

        use cbor::{{try_decode, encode, Cbor, DecodeError}};
        use api::{{Color, M}};

        fn ok_map() -> Vec<u8> {{
            // a fully valid M whose i64 field carries the in-subset extreme i64::MAX
            let m = M {{
                n: i64::MAX,
                name: "x".to_string(),
                c: Color::Blue,
                maybe: None,
                ns: vec![1, 2],
                by_id: std::collections::BTreeMap::new(),
            }};
            encode(&m.to_cbor())
        }}

        #[test]
        fn i64_extremes_round_trip_and_out_of_subset_is_rejected() {{
            // The frozen wire int subset is i64: the in-subset extreme i64::MAX
            // (carried by `n` in ok_map) survives the full struct round-trip...
            let bytes = ok_map();
            let decoded = try_decode(&bytes).expect("valid");
            let m = M::from_cbor(&decoded).expect("valid M");
            assert_eq!(m.n, i64::MAX);
            // ...and both i64 extremes round-trip at the Cbor carrier level.
            for v in [i64::MAX, i64::MIN, 0i64, -1, 1] {{
                assert_eq!(try_decode(&encode(&Cbor::Int(v))), Ok(Cbor::Int(v)));
            }}
            // A physically valid CBOR integer OUTSIDE the frozen i64 subset is a
            // typed error — never a silent wrap, a panic, or a 128-bit carry.
            // u64::MAX   (major-0, 2^64 - 1)
            assert_eq!(try_decode(&[0x1b, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff]),
                       Err(DecodeError::IntOverflow));
            // -2^64      (major-1, -1 - (2^64 - 1))
            assert_eq!(try_decode(&[0x3b, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff]),
                       Err(DecodeError::IntOverflow));
            // 2^63       (major-0, i64::MAX + 1) — just over
            assert_eq!(try_decode(&[0x1b, 0x80, 0, 0, 0, 0, 0, 0, 0]),
                       Err(DecodeError::IntOverflow));
            // -2^63 - 1  (major-1, i64::MIN - 1) — just under
            assert_eq!(try_decode(&[0x3b, 0x80, 0, 0, 0, 0, 0, 0, 0]),
                       Err(DecodeError::IntOverflow));
        }}

        #[test]
        fn every_bad_input_is_a_typed_error_never_a_panic() {{
            // empty / truncated argument
            assert_eq!(try_decode(&[]), Err(DecodeError::Truncated));
            assert_eq!(try_decode(&[0x1b, 0, 0, 0]), Err(DecodeError::Truncated)); // 8-byte int, 3 present
            // unknown major (major 6 = tags, out of subset)
            assert!(matches!(try_decode(&[0xc0]), Err(DecodeError::UnsupportedMajor(6))));
            // unknown enum arm
            assert_eq!(
                Color::from_wire(99),
                Err(DecodeError::UnknownEnum {{ enum_name: "Color", value: 99 }})
            );
            // wrong type: field 1 (n) wants int, give text
            let wrong = encode(&Cbor::Map(vec![
                (1, Cbor::Text("nope".to_string())),
                (2, Cbor::Text("x".to_string())),
                (3, Cbor::Int(0)),
                (5, Cbor::Array(vec![])),
                (6, Cbor::Array(vec![])),
            ]));
            assert_eq!(
                M::from_cbor(&try_decode(&wrong).unwrap()),
                Err(DecodeError::WrongType {{ expected: "int" }})
            );
            // missing key: drop field 2
            let missing = encode(&Cbor::Map(vec![(1, Cbor::Int(1))]));
            assert_eq!(
                M::from_cbor(&try_decode(&missing).unwrap()),
                Err(DecodeError::MissingKey(2))
            );
            // trailing bytes after a complete item
            let mut trailing = encode(&Cbor::Int(1));
            trailing.push(0x00);
            assert_eq!(try_decode(&trailing), Err(DecodeError::TrailingBytes));
        }}

        #[test]
        fn valid_message_still_decodes() {{
            let m = M::from_cbor(&try_decode(&ok_map()).unwrap()).unwrap();
            assert_eq!(m.name, "x");
            assert_eq!(m.c, Color::Blue);
            assert_eq!(m.ns, vec![1i64, 2]);
        }}
    """))

    bin_path = tmp_path / "fail_closed"
    subprocess.run([rustc, "--edition", "2021", "--test", str(test_rs), "-o", str(bin_path)], check=True)
    subprocess.run([str(bin_path)], check=True)


# Each DecodeError variant, as Rust builds it, and the canonical tag it reports.
_TAGGED_ERRORS = {
    "Truncated": "DecodeError::Truncated",
    "TrailingBytes": "DecodeError::TrailingBytes",
    "InvalidUtf8": "DecodeError::InvalidUtf8",
    "UnsupportedInfo": "DecodeError::UnsupportedInfo(28)",
    "UnsupportedMajor": "DecodeError::UnsupportedMajor(6)",
    "NonIntegerMapKey": "DecodeError::NonIntegerMapKey",
    "DuplicateMapKey": 'DecodeError::DuplicateMapKey(MapKey::Text("a".to_string()))',
    "IntOverflow": "DecodeError::IntOverflow",
    "NonCanonicalInt": "DecodeError::NonCanonicalInt(5)",
    "NegativeMapKey": "DecodeError::NegativeMapKey(-1)",
    "MissingKey": "DecodeError::MissingKey(2)",
    "WrongType": 'DecodeError::WrongType { expected: "map" }',
    "UnknownEnum": 'DecodeError::UnknownEnum { enum_name: "Mode", value: 99 }',
}

_RUNTIME_ERRORS_TEST = r"""
extern crate alloc;
#[path = "@CBOR@"]
mod cbor;

use cbor::{encode, try_decode, Cbor, DecodeError, MapKey};

#[test]
fn every_variant_reports_its_canonical_tag() {
    let cases: Vec<(DecodeError, &str)> = vec![
@TAGGED@
    ];
    for (e, tag) in &cases {
        assert_eq!(e.tag(), *tag);
        // The tag is the variant's name.
        assert!(format!("{e:?}").starts_with(tag), "{e:?}");
    }
}

#[test]
fn a_map_key_prints_as_the_parity_text() {
    assert_eq!(MapKey::Int(5).to_string(), "5");
    assert_eq!(MapKey::Int(-1).to_string(), "-1");
    assert_eq!(MapKey::Int(i64::MIN).to_string(), "-9223372036854775808");
    assert_eq!(MapKey::Text("a".to_string()).to_string(), "a");
    assert_eq!(MapKey::Text(String::new()).to_string(), "");
    assert_eq!(MapKey::Text("a;key=b".to_string()).to_string(), "a;key=b");
    assert_eq!(MapKey::Bool(true).to_string(), "true");
    assert_eq!(MapKey::Bool(false).to_string(), "false");
    assert_eq!(MapKey::from(7i64), MapKey::Int(7));
    assert_eq!(MapKey::from(true), MapKey::Bool(true));
    assert_eq!(MapKey::from("k".to_string()), MapKey::Text("k".to_string()));
    let e = DecodeError::DuplicateMapKey(MapKey::Text("a".to_string()));
    assert_eq!(e.to_string(), "duplicate map key a");
    assert_eq!(DecodeError::DuplicateMapKey(MapKey::Bool(true)).to_string(), "duplicate map key true");
}

#[test]
fn a_raw_map_reports_its_repeated_int_key() {
    assert_eq!(try_decode(&[0xa2, 0x01, 0x00, 0x01, 0x01]), Err(DecodeError::DuplicateMapKey(MapKey::Int(1))));
    // A map of 20,000 distinct keys decodes; with its first key repeated after the
    // last, it is refused with that key.
    let n: u16 = 20_000;
    let entries: Vec<(i64, Cbor)> = (0..i64::from(n)).map(|k| (k, Cbor::Null)).collect();
    let mut bytes = encode(&Cbor::Map(entries));
    assert_eq!(bytes[0], 0xb9); // a map whose count takes two bytes
    assert_eq!(try_decode(&bytes).map(|c| c.map_entries().len()), Ok(usize::from(n)));
    bytes[1..3].copy_from_slice(&(n + 1).to_be_bytes());
    bytes.extend_from_slice(&[0x00, 0xf6]);
    assert_eq!(try_decode(&bytes), Err(DecodeError::DuplicateMapKey(MapKey::Int(0))));
}

#[test]
fn a_length_beyond_the_input_is_truncated_whatever_its_size() {
    let cases: [&[u8]; 5] = [
        &[0x5b, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff],       // bytes, 2^64 - 1
        &[0x7b, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff],       // text, 2^64 - 1
        &[0x5b, 0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x00],       // bytes, 2^32
        &[0x7b, 0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01, 0x61], // text, 2^32 + 1
        &[0x7a, 0xff, 0xff, 0xff, 0xff],                               // text, 2^32 - 1
    ];
    for bytes in cases {
        assert_eq!(try_decode(bytes), Err(DecodeError::Truncated), "{bytes:02x?}");
    }
}
"""


def test_rust_runtime_errors_carry_their_tag_and_key_as_text(tmp_path):
    """CD-E2 and question 9 at the runtime: `DecodeError::tag()` names each variant as the
    gate does, `DuplicateMapKey` carries the key as a `MapKey` whose text is the parity
    contract's, a raw map's repeated key is found in a set, and a length beyond the input
    is `Truncated` whatever its size."""
    assert set(_TAGGED_ERRORS) <= parity.DECODE_TAGS
    rustc = shutil.which("rustc")
    if rustc is None:
        pytest.skip("rustc not available")
    tagged = "\n".join(f"        ({rust_value}, {json.dumps(tag)})," for tag, rust_value in _TAGGED_ERRORS.items())
    test_rs = tmp_path / "runtime_errors.rs"
    test_rs.write_text(_RUNTIME_ERRORS_TEST.replace("@CBOR@", CBOR_RS.as_posix()).replace("@TAGGED@", tagged))
    bin_path = tmp_path / "runtime_errors"
    subprocess.run([rustc, "--edition", "2021", "--test", str(test_rs), "-o", str(bin_path)], check=True)
    subprocess.run([str(bin_path)], check=True)


_WASM32_LENGTHS = r"""
extern crate alloc;
#[path = "@CBOR@"]
mod cbor;

#[no_mangle]
pub extern "C" fn usize_bits() -> u32 {
    usize::BITS
}

/// One bit per case that does not decode to `Truncated`.
#[no_mangle]
pub extern "C" fn not_truncated() -> u32 {
    let cases: [&[u8]; 4] = [
        &[0x5b, 0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x00],       // bytes, 2^32: `as usize` made it 0
        &[0x7b, 0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01, 0x61], // text, 2^32 + 1: `as usize` made it 1
        &[0x5b, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff],       // bytes, 2^64 - 1
        &[0x7a, 0xff, 0xff, 0xff, 0xff],                               // text, 2^32 - 1, which fits
    ];
    let mut bits = 0u32;
    for (i, bytes) in cases.iter().enumerate() {
        if cbor::try_decode(bytes) != Err(cbor::DecodeError::Truncated) {
            bits |= 1 << i;
        }
    }
    bits
}
"""

_WASM32_RUN = """
const fs = require("fs");
WebAssembly.instantiate(fs.readFileSync(process.argv[1]), {}).then(({ instance }) => {
  console.log(instance.exports.usize_bits(), instance.exports.not_truncated());
});
"""


def test_rust_runtime_keeps_long_lengths_whole_on_a_32_bit_target(tmp_path):
    """§5.2: `n as usize` cut a length of 2^32 or more to its low 32 bits on a 32-bit target,
    so a wasm32 build accepted input that a 64-bit build calls `Truncated`. The runtime is
    built for wasm32 and run under node; either missing skips."""
    rustc = shutil.which("rustc")
    node = toolchains.find_node()
    if rustc is None or node is None:
        pytest.skip("rustc or node not available")
    probe = tmp_path / "lengths.rs"
    probe.write_text(_WASM32_LENGTHS.replace("@CBOR@", CBOR_RS.as_posix()))
    wasm = tmp_path / "lengths.wasm"
    built = subprocess.run([rustc, "--edition", "2021", "--target", "wasm32-unknown-unknown",
                            "--crate-type", "cdylib", "-O", str(probe), "-o", str(wasm)],
                           capture_output=True, text=True)
    if built.returncode != 0 and "may not be installed" in built.stderr:
        pytest.skip("the wasm32-unknown-unknown target is not installed")
    assert built.returncode == 0, built.stderr
    ran = subprocess.run([node, "-e", _WASM32_RUN, str(wasm)], capture_output=True, text=True, check=True)
    assert ran.stdout.split() == ["32", "0"]


def test_rust_missing_ok_runtime_behavior(tmp_path):
    """Compile generated code and exercise absent/null/malformed slots.

    A plain optional slot remains a required nullable map entry. Only the opted-in
    slot accepts absence; a present wrong type remains an error.
    """
    rustc = shutil.which("rustc")
    if rustc is None:
        pytest.skip("rustc not available")

    s = schema(
        Msg(
            "M",
            F("required", 1, STR),
            F("strict_optional", 2, STR, optional=True),
            F("missing_optional", 3, STR, optional=MISSING_OK),
        )
    )
    generated = tmp_path / "generated"
    scaffold.emit(s, generated, langs=["rust"], services=[], runtime=True)
    rust_dir = generated / "rust"
    api_path = (rust_dir / "api.rs").as_posix()
    cbor_path = (rust_dir / "cbor.rs").as_posix()
    test_rs = tmp_path / "missing_ok.rs"
    test_rs.write_text(textwrap.dedent(f"""
        extern crate alloc;
        #[path = "{cbor_path}"]
        mod cbor;
        #[path = "{api_path}"]
        mod api;
        use cbor::{{Cbor, DecodeError}};
        use api::M;

        fn map(entries: &[(i64, Cbor)]) -> Cbor {{
            Cbor::Map(entries.iter().map(|(k, v)| (*k, v.clone())).collect())
        }}

        #[test]
        fn field_presence_and_malformed_values_are_scoped() {{
            let v = M::from_cbor(&map(&[(1, Cbor::Text("ok".into())), (2, Cbor::Null)])).expect("valid");
            assert_eq!(v.missing_optional, None);
            assert_eq!(M::from_cbor(&map(&[(1, Cbor::Text("ok".into()))])), Err(DecodeError::MissingKey(2)));
            assert_eq!(M::from_cbor(&map(&[(2, Cbor::Null), (3, Cbor::Null)])), Err(DecodeError::MissingKey(1)));
            assert_eq!(
                M::from_cbor(&map(&[(1, Cbor::Text("ok".into())), (2, Cbor::Null), (3, Cbor::Int(9))])),
                Err(DecodeError::WrongType {{ expected: "text" }})
            );
            let nulled = M::from_cbor(&map(&[(1, Cbor::Text("ok".into())), (2, Cbor::Null), (3, Cbor::Null)]));
            assert!(nulled.is_ok());
        }}
    """))
    bin_path = tmp_path / "missing_ok"
    subprocess.run([rustc, "--edition", "2021", "--test", str(test_rs), "-o", str(bin_path)], check=True)
    subprocess.run([str(bin_path)], check=True)


def test_rust_empty_message_requires_map(tmp_path):
    rustc = shutil.which("rustc")
    if rustc is None:
        pytest.skip("rustc not available")

    generated = tmp_path / "empty"
    scaffold.emit(schema(Msg("Empty")), generated, langs=["rust"], services=[], runtime=True)
    rust_dir = generated / "rust"
    api_path = (rust_dir / "api.rs").as_posix()
    cbor_path = (rust_dir / "cbor.rs").as_posix()
    test_rs = tmp_path / "empty.rs"
    test_rs.write_text(textwrap.dedent(f"""
        extern crate alloc;
        #[path = "{cbor_path}"]
        mod cbor;
        #[path = "{api_path}"]
        mod api;
        use cbor::{{Cbor, DecodeError}};
        use api::Empty;

        #[test]
        fn empty_message_checks_container_shape() {{
            assert!(Empty::from_cbor(&Cbor::Map(vec![])).is_ok());
            assert_eq!(Empty::from_cbor(&Cbor::Bool(true)), Err(DecodeError::WrongType {{ expected: "map" }}));
        }}
    """))
    bin_path = tmp_path / "empty_bin"
    subprocess.run([rustc, "--edition", "2021", "--test", str(test_rs), "-o", str(bin_path)], check=True)
    subprocess.run([str(bin_path)], check=True)


_MAP_FIELDS_TEST = r"""
extern crate alloc;
#[path = "@CBOR@"]
mod cbor;
#[path = "@API@"]
mod api;

use api::Maps;
use cbor::{encode, try_decode, Cbor, DecodeError, MapKey};
use std::collections::BTreeMap;

fn text(s: &str) -> Cbor {
    Cbor::Text(s.to_string())
}

fn entry(key: Cbor, value: Cbor) -> Cbor {
    Cbor::Map(vec![(1, key), (2, value)])
}

fn entries(items: Vec<Cbor>) -> Cbor {
    Cbor::Array(items)
}

/// A valid `Maps` whose field `tag` is replaced by `value`.
fn decode_with(tag: i64, value: Cbor) -> Result<Maps, DecodeError> {
    let mut fields = vec![
        (1, entries(vec![entry(Cbor::Int(1), text("a"))])),
        (2, entries(vec![entry(text("a"), Cbor::Int(1))])),
        (3, entries(vec![entry(Cbor::Bool(true), Cbor::Int(1))])),
        (4, Cbor::Null),
        (5, entries(vec![entries(vec![entry(Cbor::Int(1), Cbor::Int(1))])])),
    ];
    for field in fields.iter_mut() {
        if field.0 == tag {
            field.1 = value.clone();
        }
    }
    Maps::from_cbor(&Cbor::Map(fields))
}

#[test]
fn every_map_shape_round_trips() {
    let maps = Maps {
        by_int: BTreeMap::from([(1, "a".to_string()), (2, "b".to_string())]),
        by_text: BTreeMap::from([("a".to_string(), 1), ("b".to_string(), 2)]),
        by_flag: BTreeMap::from([(false, 0), (true, 1)]),
        maybe: Some(BTreeMap::from([(3, 4)])),
        many: vec![BTreeMap::from([(5, 6)]), BTreeMap::new()],
    };
    let bytes = encode(&maps.to_cbor());
    let back = Maps::from_cbor(&try_decode(&bytes).unwrap()).unwrap();
    assert_eq!(back, maps);
    assert_eq!(encode(&back.to_cbor()), bytes);
    assert_eq!(decode_with(4, Cbor::Null).unwrap().maybe, None);
}

#[test]
fn an_entry_needs_keys_1_and_2_before_either_is_decoded() {
    let key_only = Cbor::Map(vec![(1, text("x"))]);
    assert_eq!(decode_with(1, entries(vec![key_only])), Err(DecodeError::MissingKey(2)));
    let value_only = Cbor::Map(vec![(2, text("a"))]);
    assert_eq!(decode_with(1, entries(vec![value_only])), Err(DecodeError::MissingKey(1)));
    assert_eq!(decode_with(1, entries(vec![Cbor::Int(5)])), Err(DecodeError::WrongType { expected: "map" }));
    // Entries are read in order: the first entry's bad key fails before the
    // second entry's missing key 2 is seen.
    let second = Cbor::Map(vec![(1, Cbor::Int(5))]);
    assert_eq!(
        decode_with(1, entries(vec![entry(text("bad"), text("a")), second])),
        Err(DecodeError::WrongType { expected: "int" })
    );
}

#[test]
fn a_repeated_key_is_refused_before_its_value_is_decoded() {
    let repeated = entries(vec![entry(Cbor::Int(5), text("a")), entry(Cbor::Int(5), text("b"))]);
    assert_eq!(decode_with(1, repeated), Err(DecodeError::DuplicateMapKey(MapKey::Int(5))));
    // The repeated entry's value has the wrong type; it is never decoded.
    let bad_value = entries(vec![entry(Cbor::Int(5), text("a")), entry(Cbor::Int(5), Cbor::Int(7))]);
    assert_eq!(decode_with(1, bad_value), Err(DecodeError::DuplicateMapKey(MapKey::Int(5))));
    let optional = entries(vec![entry(Cbor::Int(3), Cbor::Int(1)), entry(Cbor::Int(3), Cbor::Int(2))]);
    assert_eq!(decode_with(4, optional), Err(DecodeError::DuplicateMapKey(MapKey::Int(3))));
    let inner = entries(vec![entry(Cbor::Int(4), Cbor::Int(1)), entry(Cbor::Int(4), Cbor::Int(2))]);
    assert_eq!(
        decode_with(5, entries(vec![entries(vec![]), inner])),
        Err(DecodeError::DuplicateMapKey(MapKey::Int(4)))
    );
}

#[test]
fn a_repeated_bool_or_text_key_is_reported_as_the_key() {
    // Question 9: the key itself, whose text is `false` or the str; never 0 or an index.
    let flags = entries(vec![entry(Cbor::Bool(false), Cbor::Int(1)), entry(Cbor::Bool(false), Cbor::Int(2))]);
    let got = decode_with(3, flags);
    assert_eq!(got, Err(DecodeError::DuplicateMapKey(MapKey::Bool(false))));
    assert_eq!(got.unwrap_err().to_string(), "duplicate map key false");
    let texts = entries(vec![
        entry(text("a"), Cbor::Int(1)),
        entry(text("b"), Cbor::Int(2)),
        entry(text("a"), Cbor::Int(3)),
    ]);
    let got = decode_with(2, texts);
    assert_eq!(got, Err(DecodeError::DuplicateMapKey(MapKey::Text("a".to_string()))));
    assert_eq!(got.unwrap_err().to_string(), "duplicate map key a");
    // An empty str is a key like any other.
    let empties = entries(vec![entry(text(""), Cbor::Int(1)), entry(text(""), Cbor::Int(2))]);
    assert_eq!(decode_with(2, empties), Err(DecodeError::DuplicateMapKey(MapKey::Text(String::new()))));
}
"""


def test_rust_fail_closed_map_fields_check_each_entry_in_order(tmp_path):
    """CD-E5 for `map<K,V>` fields (M13, M14) beyond the fixture's `map<int,int>`:
    each entry, in order, must be a map holding keys 1 and 2 before either is
    decoded, and a repeated key is refused before its value is decoded. Covers
    int, str and bool keys, an optional map and a list of maps."""
    rustc = shutil.which("rustc")
    if rustc is None:
        pytest.skip("rustc not available")

    s = schema(Msg("Maps",
                   F("by_int", 1, Map(INT, STR)),
                   F("by_text", 2, Map(STR, INT)),
                   F("by_flag", 3, Map(BOOL, INT)),
                   F("maybe", 4, Map(INT, INT), optional=True),
                   F("many", 5, List(Map(INT, INT)))))
    generated = tmp_path / "generated"
    scaffold.emit(s, generated, langs=["rust"], services=[], runtime=True)
    rust_dir = generated / "rust"
    test_rs = tmp_path / "map_fields.rs"
    test_rs.write_text(_MAP_FIELDS_TEST
                       .replace("@CBOR@", (rust_dir / "cbor.rs").as_posix())
                       .replace("@API@", (rust_dir / "api.rs").as_posix()))
    bin_path = tmp_path / "map_fields"
    subprocess.run([rustc, "--edition", "2021", "--test", str(test_rs), "-o", str(bin_path)], check=True)
    subprocess.run([str(bin_path)], check=True)


def test_rust_fail_closed_replays_shared_i64_parity_corpus(tmp_path):
    rustc = shutil.which("rustc")
    if rustc is None:
        pytest.skip("rustc not available")

    generated = tmp_path / "generated"
    scaffold.emit(PARITY_SCHEMA, generated, langs=["rust"], services=[], runtime=True)
    rust_dir = generated / "rust"
    api_path = (rust_dir / "api.rs").as_posix()
    cbor_path = (rust_dir / "cbor.rs").as_posix()
    round_trip_rows, encode_fail_rows = _rust_parity_int_rows()
    malformed_rows = _rust_parity_malformed_rows()

    test_rs = tmp_path / "parity_vectors.rs"
    test_rs.write_text(textwrap.dedent(f"""
        extern crate alloc;
        #[path = "{cbor_path}"]
        mod cbor;
        #[path = "{api_path}"]
        mod api;

        use api::{{IntBox, Mode}};
        use cbor::{{encode, try_decode, DecodeError, MapKey}};

        struct IntRow {{
            name: &'static str,
            cbor: &'static str,
            n: &'static str,
            by_id: &'static [(&'static str, &'static str)],
        }}

        static ROUND_TRIP: &[IntRow] = &[
{round_trip_rows}
        ];

        struct EncodeFailRow {{
            name: &'static str,
            value: &'static str,
            tag: &'static str,
        }}

        static ENCODE_FAIL: &[EncodeFailRow] = &[
{encode_fail_rows}
        ];

        struct MalformedRow {{
            name: &'static str,
            stage: &'static str,
            schema: Option<&'static str>,
            bytes: &'static str,
            tag: &'static str,
            key: Option<&'static str>,
            expected: Option<&'static str>,
            enum_name: Option<&'static str>,
            value: Option<&'static str>,
            info: Option<u8>,
            major: Option<u8>,
        }}

        static MALFORMED: &[MalformedRow] = &[
{malformed_rows}
        ];

        fn parse_i64(s: &str) -> i64 {{
            s.parse::<i64>().unwrap_or_else(|e| panic!("bad i64 {{s}}: {{e}}"))
        }}

        fn unhex(s: &str) -> Vec<u8> {{
            (0..s.len())
                .step_by(2)
                .map(|i| u8::from_str_radix(&s[i..i + 2], 16).unwrap())
                .collect()
        }}

        fn hexof(b: &[u8]) -> String {{
            use std::fmt::Write as _;
            b.iter().fold(String::new(), |mut s, x| {{
                let _ = write!(s, "{{x:02x}}");
                s
            }})
        }}

        fn by_id(row: &IntRow) -> std::collections::BTreeMap<i64, i64> {{
            row.by_id
                .iter()
                .map(|(k, v)| (parse_i64(k), parse_i64(v)))
                .collect()
        }}

        fn assert_error(row: &MalformedRow, got: DecodeError) {{
            match row.tag {{
                "Truncated" => assert_eq!(got, DecodeError::Truncated, "{{}}", row.name),
                "TrailingBytes" => assert_eq!(got, DecodeError::TrailingBytes, "{{}}", row.name),
                "InvalidUtf8" => assert_eq!(got, DecodeError::InvalidUtf8, "{{}}", row.name),
                "UnsupportedInfo" => assert_eq!(
                    got,
                    DecodeError::UnsupportedInfo(row.info.unwrap()),
                    "{{}}",
                    row.name
                ),
                "UnsupportedMajor" => assert_eq!(
                    got,
                    DecodeError::UnsupportedMajor(row.major.unwrap()),
                    "{{}}",
                    row.name
                ),
                "NonIntegerMapKey" => assert_eq!(got, DecodeError::NonIntegerMapKey, "{{}}", row.name),
                "DuplicateMapKey" => assert_eq!(
                    got,
                    DecodeError::DuplicateMapKey(MapKey::Int(parse_i64(row.key.unwrap()))),
                    "{{}}",
                    row.name
                ),
                "IntOverflow" => assert_eq!(got, DecodeError::IntOverflow, "{{}}", row.name),
                "MissingKey" => assert_eq!(
                    got,
                    DecodeError::MissingKey(parse_i64(row.key.unwrap())),
                    "{{}}",
                    row.name
                ),
                "WrongType" => assert_eq!(
                    got,
                    DecodeError::WrongType {{ expected: row.expected.unwrap() }},
                    "{{}}",
                    row.name
                ),
                "UnknownEnum" => assert_eq!(
                    got,
                    DecodeError::UnknownEnum {{
                        enum_name: row.enum_name.unwrap(),
                        value: parse_i64(row.value.unwrap()),
                    }},
                    "{{}}",
                    row.name
                ),
                other => panic!("unknown expected tag {{other}} for {{}}", row.name),
            }}
        }}

        #[test]
        fn round_trip_rows_match_shared_corpus() {{
            assert_eq!(ROUND_TRIP.len(), 7);
            for row in ROUND_TRIP {{
                let expected_by_id = by_id(row);
                let constructed = IntBox {{
                    n: parse_i64(row.n),
                    by_id: expected_by_id.clone(),
                }};
                assert_eq!(hexof(&encode(&constructed.to_cbor())), row.cbor, "encode {{}}", row.name);

                let decoded_cbor = try_decode(&unhex(row.cbor)).unwrap_or_else(|e| {{
                    panic!("decode {{}}: {{e:?}}", row.name)
                }});
                let decoded = IntBox::from_cbor(&decoded_cbor).unwrap_or_else(|e| {{
                    panic!("from_cbor {{}}: {{e:?}}", row.name)
                }});
                assert_eq!(decoded.n, parse_i64(row.n), "n {{}}", row.name);
                assert_eq!(decoded.by_id, expected_by_id, "by_id {{}}", row.name);
                assert_eq!(hexof(&encode(&decoded.to_cbor())), row.cbor, "re-encode {{}}", row.name);
            }}
        }}

        #[test]
        fn encode_fail_rows_are_rejected_at_i64_construction_boundary() {{
            assert_eq!(ENCODE_FAIL.len(), 3);
            for row in ENCODE_FAIL {{
                assert_eq!(row.tag, "IntOutOfSubset", "{{}}", row.name);
                assert!(
                    row.value.parse::<i64>().is_err(),
                    "encode-fail value {{}} for {{}} should not fit Rust i64",
                    row.value,
                    row.name
                );
            }}
        }}

        #[test]
        fn malformed_rows_return_expected_typed_errors() {{
            assert_eq!(MALFORMED.len(), 12);
            for row in MALFORMED {{
                match row.stage {{
                    "raw_decode" => {{
                        let got = try_decode(&unhex(row.bytes)).expect_err(row.name);
                        assert_error(row, got);
                    }}
                    "from_cbor" => {{
                        let c = try_decode(&unhex(row.bytes)).unwrap_or_else(|e| {{
                            panic!("raw decode {{}}: {{e:?}}", row.name)
                        }});
                        let got = match row.schema {{
                            Some("IntBox") => IntBox::from_cbor(&c).map(|_| ()).expect_err(row.name),
                            other => panic!("unsupported from_cbor schema {{other:?}} for {{}}", row.name),
                        }};
                        assert_error(row, got);
                    }}
                    "from_wire" => {{
                        let c = try_decode(&unhex(row.bytes)).unwrap_or_else(|e| {{
                            panic!("raw decode {{}}: {{e:?}}", row.name)
                        }});
                        let value = c.try_int().unwrap_or_else(|e| {{
                            panic!("enum int {{}}: {{e:?}}", row.name)
                        }});
                        let got = match row.schema {{
                            Some("Mode") => Mode::from_wire(value).map(|_| ()).expect_err(row.name),
                            other => panic!("unsupported from_wire schema {{other:?}} for {{}}", row.name),
                        }};
                        assert_error(row, got);
                    }}
                    other => panic!("unknown malformed stage {{other}} for {{}}", row.name),
                }}
            }}
        }}
    """))

    bin_path = tmp_path / "parity_vectors"
    subprocess.run([rustc, "--edition", "2021", "--test", str(test_rs), "-o", str(bin_path)], check=True)
    subprocess.run([str(bin_path)], check=True)


# =============================================================================
# The corpus emitter and glade_build: the fail-closed codec too (question 5).
# =============================================================================

_CORPUS_EMITTER_TEST = r"""
extern crate alloc;
#[path = "@CBOR@"]
mod cbor;
#[path = "@GENERATED@"]
mod generated;

use cbor::DecodeError;
use generated::{roundtrip, VECTORS};

fn unhex(s: &str) -> Vec<u8> {
    (0..s.len()).step_by(2).map(|i| u8::from_str_radix(&s[i..i + 2], 16).unwrap()).collect()
}

fn hexof(b: &[u8]) -> String {
    b.iter().map(|x| format!("{x:02x}")).collect()
}

#[test]
fn every_golden_vector_round_trips_through_its_typed_message() {
    assert!(!VECTORS.is_empty(), "no vectors generated");
    for (name, message, hex) in VECTORS {
        let again = roundtrip(message, &unhex(hex)).unwrap_or_else(|e| panic!("{name}: {e:?}"));
        assert_eq!(&hexof(&again), hex, "{name}");
    }
}

#[test]
fn malformed_input_is_a_decode_error_never_a_panic() {
    for (name, message, hex) in VECTORS {
        let bytes = unhex(hex);
        for cut in 0..bytes.len() {
            assert_eq!(roundtrip(message, &bytes[..cut]), Err(DecodeError::Truncated), "{name} cut at {cut}");
        }
        let mut trailing = bytes.clone();
        trailing.push(0x00);
        assert_eq!(roundtrip(message, &trailing), Err(DecodeError::TrailingBytes), "{name}");
        assert_eq!(roundtrip(message, &[0x00]), Err(DecodeError::WrongType { expected: "map" }), "{name}");
    }
}

#[test]
#[should_panic(expected = "unknown message")]
fn an_unknown_message_name_is_the_callers_error() {
    let _ = roundtrip("NoSuchMessage", &[0xa0]);
}
"""


def _run_corpus_emitter(rustc: str, tmp_path: Path, cbor_rs: Path, generated_rs: Path) -> None:
    test_rs = tmp_path / "corpus_emitter.rs"
    test_rs.write_text(_CORPUS_EMITTER_TEST
                       .replace("@CBOR@", cbor_rs.as_posix())
                       .replace("@GENERATED@", generated_rs.as_posix()))
    bin_path = tmp_path / "corpus_emitter"
    subprocess.run([rustc, "--edition", "2021", "--test", str(test_rs), "-o", str(bin_path)], check=True)
    subprocess.run([str(bin_path)], check=True)


def test_rust_corpus_emitter_is_fail_closed(tmp_path):
    """The corpus emitter (`rust._emit`, behind `rust.emit` and glade's `generated.rs`)
    generates the fail-closed codec: `roundtrip` returns a `Result`, every golden vector
    round-trips byte for byte, and malformed input is a `DecodeError`, never a panic."""
    rustc = shutil.which("rustc")
    if rustc is None:
        pytest.skip("rustc not available")
    griplab = load_schema(ROOT / "ir" / "griplab.taut.py")
    golden = json.loads((ROOT / "corpus" / "griplab.golden.json").read_text())
    generated = tmp_path / "generated.rs"
    generated.write_text(rust._emit(griplab, golden))
    _run_corpus_emitter(rustc, tmp_path, CBOR_RS, generated)


def test_glade_build_writes_the_fail_closed_codec_and_runtime(tmp_path, monkeypatch):
    """`glade_build` regenerates glade's wire-rs sources from the fail-closed path: its
    `cbor.rs` is the fail-closed runtime and its `generated.rs` the corpus emitter's
    fail-closed codec. Written into a scratch crate, since `glade_build.main()` writes into
    glade itself."""
    crate = tmp_path / "glade" / "wire-rs"
    monkeypatch.setattr(glade_build, "GLADE_RS_DIR", crate / "src")
    glade_schema = load_schema(glade_build.IR_PATH)
    corpus = json.loads(glade_build.GOLDEN_PATH.read_text())
    glade_build.emit_rust(glade_schema, corpus)
    assert not crate.exists()   # no crate scaffolded: nothing to regenerate

    crate.mkdir(parents=True)
    glade_build.emit_rust(glade_schema, corpus)
    src = crate / "src"
    assert sorted(p.name for p in src.iterdir()) == ["cbor.rs", "generated.rs"]
    assert (src / "cbor.rs").read_text() == CBOR_RS.read_text()
    generated = (src / "generated.rs").read_text()
    assert generated == rust._emit(glade_schema, corpus)
    assert "use crate::cbor::{Cbor, DecodeError};" in generated
    assert "pub fn from_wire(v: i64) -> Result<Self, DecodeError>" in generated
    rustc = shutil.which("rustc")
    if rustc is None:
        pytest.skip("rustc not available")
    _run_corpus_emitter(rustc, tmp_path, src / "cbor.rs", src / "generated.rs")


# =============================================================================
# The gate.
# =============================================================================

def test_rust_passes_the_parity_gate():
    """Every row of the shared corpus through the gate's Rust runner (`tautc parity -t rust`),
    as rust and rust/fc, each held to the gate's governance: GREEN, or RED and allowlisted.
    The runner reports each error's tag from the runtime's `DecodeError::tag()` (CD-E2)."""
    assert "e.tag()" in parity_rust._MAIN
    reports, violations = parity.governed_variants(parity_rust.run)
    for report in reports:
        if not report.available:
            pytest.skip(report.skip_reason)
    assert violations == [], "\n".join(violations)
    # Only an encode-fail row may be satisfied by the type system; every other row ran.
    for report in reports:
        if not report.fault:
            satisfied = {r.name for r in report.results if r.status == parity.TYPE_SATISFIED}
            assert satisfied == {r["name"] for r in parity.int_rows() if r["kind"] == "encode_fail"}, \
                report.target
