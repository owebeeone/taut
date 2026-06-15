"""Conformance kit — derive a golden corpus from any IR, plus per-language parity
harnesses. The corpus is reference values encoded by taut's *canonical* (Python)
codec; a target conforms iff its codec reproduces the exact bytes (parity ==
correctness). This is the discipline taut uses on GripLab, made pointable at any
IR — so consumers stop hand-rolling `corpus.py` + `vectors.rs` + a parity test.
"""

from __future__ import annotations

import json
from typing import Any

from ..ir.model import Schema
from ..wire import codec


def build_corpus(schema: Schema, values: dict[str, tuple[str, Any]]) -> dict[str, dict]:
    """`{name: (message, native)}` -> `{name: {message, cbor-hex}}` (canonical codec)."""
    return {
        name: {"message": msg, "cbor": codec.encode(schema, msg, value).hex()}
        for name, (msg, value) in values.items()
    }


def golden_json(corpus: dict[str, dict]) -> str:
    """The neutral, language-agnostic oracle file (stable: sorted, indented)."""
    return json.dumps(corpus, indent=2, sort_keys=True) + "\n"


# --- per-language parity harness (Rust; others ride their generators in 0.3+) --

_RUST_HELPERS = '''
#[cfg(test)]
mod conformance {
    use super::reencode;
    fn unhex(s: &str) -> Vec<u8> {
        (0..s.len()).step_by(2).map(|i| u8::from_str_radix(&s[i..i + 2], 16).unwrap()).collect()
    }
    fn hexof(b: &[u8]) -> String {
        use std::fmt::Write as _;
        b.iter().fold(String::new(), |mut s, x| { let _ = write!(s, "{x:02x}"); s })
    }
    /// Parity == correctness: every golden vector (bytes from taut's Python codec)
    /// must decode and re-encode to the identical bytes via this crate's codec.
    #[test]
    fn corpus_byte_parity() {
        assert!(!super::VECTORS.is_empty(), "empty corpus");
        for (name, message, golden) in super::VECTORS {
            let out = hexof(&crate::encode(&reencode(message, &crate::decode(&unhex(golden)))));
            assert_eq!(&out, golden, "byte mismatch for {name} ({message})");
        }
    }
}
'''


def rust_vectors(schema: Schema, corpus: dict[str, dict]) -> str:
    """A self-contained `vectors.rs`: the data table + a `reencode` dispatcher +
    a `corpus_byte_parity` test. Assumes the crate re-exports its generated types,
    `Cbor`, `encode`, and `decode` at the crate root (the idiomatic
    `pub use generated::*; pub use cbor::*;`)."""
    messages = sorted({e["message"] for e in corpus.values()})
    lines = [
        "// GENERATED conformance vectors + byte-parity test (tautc corpus) — do not edit.",
        "// Requires the crate root to re-export its taut types + `Cbor`/`encode`/`decode`,",
        "// e.g. `pub use generated::*; pub use cbor::{Cbor, encode, decode};`.",
        "#![allow(dead_code)]",
        "",
        "#[rustfmt::skip]",
        "pub static VECTORS: &[(&str, &str, &str)] = &[",
    ]
    for name in sorted(corpus):
        e = corpus[name]
        lines.append(f'    ({json.dumps(name)}, {json.dumps(e["message"])}, {json.dumps(e["cbor"])}),')
    lines.append("];")
    lines.append("")
    lines.append("/// Decode->re-encode dispatch by message name, over this crate's generated types.")
    lines.append("pub fn reencode(message: &str, c: &crate::Cbor) -> crate::Cbor {")
    lines.append("    match message {")
    for m in messages:
        lines.append(f'        "{m}" => crate::{m}::from_cbor(c).to_cbor(),')
    lines.append('        other => panic!("reencode: unknown message {other}"),')
    lines.append("    }")
    lines.append("}")
    lines.append(_RUST_HELPERS)
    return "\n".join(lines).rstrip() + "\n"


# lang -> (relative output path, emitter). golden.json is always written; these
# are the runtime parity harnesses for targets that decode-then-reencode.
_HARNESS = {
    "rust": ("rust/vectors.rs", rust_vectors),
}
