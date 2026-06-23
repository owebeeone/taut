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
from taut.ir.dsl import FLOAT, INT, F, List, Map, Msg, schema
from taut.ir.load import load_schema
from taut.ir.shapes import BAND_START
from taut.wire import cbor as py_cbor
from taut.wire import codec

ROOT = Path(__file__).resolve().parents[2]
RESEXT_SCHEMA = load_schema(ROOT / "ir" / "resext.taut.py")


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
