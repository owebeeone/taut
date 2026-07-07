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

from taut import ext as py_ext
from taut.gen import scaffold
from taut.gen import rust
from taut.ir.dsl import FLOAT, INT, STR, Enum, F, List, Map, Msg, Ref, schema
from taut.ir.load import load_schema
from taut.ir.shapes import BAND_START
from taut.wire import cbor as py_cbor
from taut.wire import codec

ROOT = Path(__file__).resolve().parents[2]
RESEXT_SCHEMA = load_schema(ROOT / "ir" / "resext.taut.py")
PARITY_SCHEMA = load_schema(ROOT / "ir" / "parity_int.taut.py")


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
    assert "x: c.get(1).float()" in out
    assert "maybe: { let v = c.get(2); if v.is_null() { None } else { Some(v.float()) } }" in out


def test_rust_runtime_matches_float_vectors(tmp_path):
    rustc = shutil.which("rustc")
    if rustc is None:
        pytest.skip("rustc not available")

    vectors = json.loads((ROOT / "corpus" / "float_vectors.json").read_text())
    rows = ",\n".join(
        f'        ("{row["note"]}", 0x{row["f64"]}u64, "{row["cbor"]}")'
        for row in vectors
    )
    cbor_path = (ROOT / "src" / "taut" / "gen" / "runtime" / "cbor.rs").as_posix()
    test_rs = tmp_path / "float_vectors.rs"
    test_rs.write_text(textwrap.dedent(f"""
        #[path = "{cbor_path}"]
        mod cbor;

        use cbor::{{decode, encode, Cbor}};

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

                let decoded = decode(&unhex(cbor_hex));
                assert_eq!(hexof(&encode(&decoded)), *cbor_hex, "re-encode {{note}}");
                if !note.starts_with("nan") {{
                    assert_eq!(decoded.float().to_bits(), *bits, "decode bits {{note}}");
                }}
            }}
        }}

        #[test]
        fn float_decode_accepts_all_widths() {{
            for hx in ["f93c00", "fa3f800000", "fb3ff0000000000000"] {{
                assert_eq!(decode(&unhex(hx)).float().to_bits(), 1.0f64.to_bits(), "{{hx}}");
            }}
        }}
    """))

    bin_path = tmp_path / "float_vectors"
    subprocess.run([rustc, "--test", str(test_rs), "-o", str(bin_path)], check=True)
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
        #[path = "{cbor_path}"]
        mod cbor;
        #[path = "{api_path}"]
        mod api;
        #[path = "{ext_path}"]
        mod ext;

        use api::{{Decision, Host}};
        use cbor::{{decode, encode, Cbor}};

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
            let c = decode(&unhex(hex));
            Decision::from_cbor(&c)
        }}

        #[test]
        fn residual_vectors_roundtrip_byte_exactly() {{
            for (note, wire) in RESIDUAL {{
                let decoded = decode(&unhex(wire));
                let host = Host::from_cbor(&decoded);
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
                        let got = ext::ext_set(&host, row.tag, decision.to_cbor());
                        assert_eq!(hexof(&got), row.expect, "ext set {{}}", row.note);
                    }}
                    "get" => {{
                        let got = ext::ext_get(&host, row.tag);
                        if row.expect == "null" {{
                            assert!(got.is_none(), "ext get absent {{}}", row.note);
                        }} else {{
                            let decision = Decision::from_cbor(&got.as_ref().unwrap());
                            assert_eq!(
                                hexof(&encode(&decision.to_cbor())),
                                row.expect,
                                "ext get {{}}",
                                row.note
                            );
                        }}
                    }}
                    "clear" => {{
                        let got = ext::ext_clear(&host, row.tag);
                        assert_eq!(hexof(&got), row.expect, "ext clear {{}}", row.note);
                    }}
                    _ => panic!("unknown op {{}}", row.op),
                }}
            }}
        }}

        #[test]
        #[should_panic(expected = "below the extension band")]
        fn ext_rejects_below_band_before_decoding_host() {{
            ext::ext_set(&[], (1 << 20) - 1, Cbor::Null);
        }}

        #[test]
        #[should_panic(expected = "top-level CBOR map")]
        fn ext_rejects_non_map_hosts() {{
            let decision = Decision {{ backend: "b7".to_string(), hops: 1, wire_residual: vec![] }};
            ext::ext_set(&encode(&Cbor::Int(1)), 1 << 20, decision.to_cbor());
        }}

        #[test]
        fn fixed_seed_resext_fuzz_matches_python_oracle() {{
            let mut mismatches = 0usize;
            for row in FUZZ {{
                let host = unhex(row.host);

                let decoded = decode(&host);
                let typed = Host::from_cbor(&decoded);
                let roundtrip = hexof(&encode(&typed.to_cbor()));
                if roundtrip != row.roundtrip {{
                    eprintln!(
                        "residual mismatch seed={{}} note={{}} input={{}} got={{}} expect={{}}",
                        FUZZ_SEED, row.note, row.host, roundtrip, row.roundtrip
                    );
                    mismatches += 1;
                }}

                let decision = decision_from_wire(row.value);
                let set = ext::ext_set(&host, row.tag, decision.to_cbor());
                let set_hex = hexof(&set);
                if set_hex != row.expect_set {{
                    eprintln!(
                        "ext_set mismatch seed={{}} note={{}} input={{}} got={{}} expect={{}}",
                        FUZZ_SEED, row.note, row.host, set_hex, row.expect_set
                    );
                    mismatches += 1;
                }}

                match ext::ext_get(&set, row.tag) {{
                    Some(c) => {{
                        let got = Decision::from_cbor(&c);
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

                let clear_hex = hexof(&ext::ext_clear(&set, row.tag));
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
    subprocess.run([rustc, "--test", str(test_rs), "-o", str(bin_path)], check=True)
    subprocess.run([str(bin_path)], check=True)


# =============================================================================
# Fail-closed (opt-in) Rust codec — the untrusted-boundary hardening.
#
# Non-negotiable: the default (no-flag) output is byte-for-byte today's, so a
# consumer that regenerates WITHOUT the flag is unaffected. These tests pin the
# opt-in shape and prove the default is unchanged, mirroring the forward-compat
# gates in test_forward_compat.py.
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
    rows = json.loads((ROOT / "corpus" / "parity" / "int.vectors.json").read_text())["vectors"]
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
    rows = json.loads((ROOT / "corpus" / "parity" / "malformed.vectors.json").read_text())["vectors"]
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
    rs = scaffold.rust_api(_FC, fail_closed=True)
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


def test_rust_fail_closed_enum_from_wire_is_fallible():
    rs = scaffold.rust_api(_FC, fail_closed=True)
    assert "pub fn from_wire(v: i64) -> Result<Self, DecodeError>" in rs
    assert 'return Err(DecodeError::UnknownEnum { enum_name: "Color", value: v })' in rs
    # wire() returns the i64 carrier so `Cbor::Int(x.wire())` type-checks
    assert "pub fn wire(self) -> i64" in rs


def test_rust_fail_closed_is_off_by_default_and_byte_identical():
    # Default output must be exactly today's: infallible from_cbor, i64 ints,
    # panicking from_wire, no DecodeError import.
    default = scaffold.rust_api(_FC)
    assert "pub fn from_cbor(c: &Cbor) -> Self {" in default
    assert "Result<Self, DecodeError>" not in default
    assert "DecodeError" not in default
    assert "pub n: i64," in default
    assert "i128" not in default
    assert "pub fn from_wire(v: i64) -> Self {" in default
    assert 'panic!("bad Color wire value' in default
    # and the flag genuinely changes the output
    assert scaffold.rust_api(_FC, fail_closed=True) != default


def test_fail_closed_rejects_non_rust_targets(tmp_path):
    # The flag is Rust-only today; refuse it for other targets rather than
    # silently emitting unhardened code.
    with pytest.raises(ValueError):
        scaffold.emit(_FC, tmp_path, langs=["rust", "python"], services=[], fail_closed=True)
    # rust-only is fine
    scaffold.emit(_FC, tmp_path, langs=["rust"], services=[], fail_closed=True)


def test_rust_fail_closed_runtime_decode_is_fail_closed(tmp_path):
    """rustc-driven: the hardened api.rs + cbor.rs decode every malformed /
    truncated / unknown-enum / wrong-type / trailing-byte / out-of-subset-int
    input to a typed error (never a panic); i64 extremes round-trip and a CBOR
    integer outside the frozen i64 subset is rejected (never wrapped)."""
    rustc = shutil.which("rustc")
    if rustc is None:
        pytest.skip("rustc not available")

    generated = tmp_path / "generated"
    scaffold.emit(_FC, generated, langs=["rust"], services=[], runtime=True, fail_closed=True)
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


def test_rust_fail_closed_replays_shared_i64_parity_corpus(tmp_path):
    rustc = shutil.which("rustc")
    if rustc is None:
        pytest.skip("rustc not available")

    generated = tmp_path / "generated"
    scaffold.emit(PARITY_SCHEMA, generated, langs=["rust"], services=[], runtime=True, fail_closed=True)
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
        use cbor::{{encode, try_decode, DecodeError}};

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
                    DecodeError::DuplicateMapKey(parse_i64(row.key.unwrap())),
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
