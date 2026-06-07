#!/usr/bin/env python3
"""Generate the per-language code for the Tasks API into ./generated/ :
api (types), client, and server stubs for Python, TypeScript, Rust, and C++.
Run: python generate.py"""

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2] / "src"))   # docs/examples/tasks -> taut/src

from taut.gen import scaffold
from taut.ir.load import load_schema
from taut.ir.validate import validate_or_raise


def main() -> None:
    schema = load_schema(HERE / "tasks.taut.py")
    validate_or_raise(schema)
    written = scaffold.emit_all(schema, "Tasks", HERE / "generated")
    print(f"generated {len(written)} files:")
    for p in written:
        print(" ", p.relative_to(HERE))


if __name__ == "__main__":
    main()
