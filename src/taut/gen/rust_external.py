"""Explicit native type ownership for composed Rust schemas.

The complete dependency schema remains in the IR for validation and corpus
generation. Only its Rust declarations are replaced by imports. Consumers must
use the owner's CBOR runtime (for example, `pub use owner::cbor`) and compatible
codec options. Compilation checks that the dependency exports the promised API.
"""

import re

from ..ir.model import Schema

_IDENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*\Z")
_KEYWORDS = set("as break const continue crate else enum extern false fn for if impl in let loop "
                "match mod move mut pub ref return self Self static struct super trait true type "
                "unsafe use where while async await dyn abstract become box do final macro "
                "override priv typeof unsized virtual yield try gen".split())


def imports(schema: Schema, mapping: dict[str, str] | None) -> list[str]:
    """Validate before producing source; reject misspelled or injected paths."""
    if mapping is None:
        return []
    if not isinstance(mapping, dict):
        raise ValueError("Rust external types must be a name-to-path mapping")
    known = set(schema.messages) | set(schema.enums)
    result = []
    for name, path in sorted(mapping.items()):
        if name not in known:
            raise ValueError(f"unknown Rust external type {name!r}")
        if not isinstance(path, str):
            raise ValueError(f"invalid Rust external path for {name!r}")
        parts = path.split("::")
        if len(parts) < 2 or any(not _IDENT.fullmatch(p) for p in parts):
            raise ValueError(f"invalid Rust external path {path!r}")
        for index, part in enumerate(parts):
            if part in _KEYWORDS and not (index == 0 and part in {"crate", "self", "super"}):
                raise ValueError(f"reserved word in Rust external path {path!r}")
        result.append(f"pub use {path} as {name};")
    return result
