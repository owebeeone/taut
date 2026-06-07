"""Vendored per-language CBOR runtimes, emitted on demand by `tautc gen
--with-runtime` so generated compiled-target code is self-contained.

These are the canonical deterministic-CBOR codecs the generated types depend on
(`cbor.rs` for `use crate::cbor`, `cbor.hpp` for `#include "taut/cbor.hpp"`).
They are data files, read via importlib.resources — not imported as Python."""
