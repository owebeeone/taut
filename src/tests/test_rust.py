"""Rust generator/runtime float coverage.

The compiled crate may not be checked out beside this repository, so the runtime
test builds the vendored cbor.rs directly with rustc and drives it with the
shared float vector corpus.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import textwrap
from pathlib import Path

import pytest

from taut.gen import rust
from taut.ir.dsl import FLOAT, INT, F, List, Map, Msg, schema

ROOT = Path(__file__).resolve().parents[2]


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
