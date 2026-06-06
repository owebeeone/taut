"""Load an authored `.prism.py` IR module by path and return its SCHEMA.

The authored IR uses an unusual double extension (`griplab.prism.py`) and is not
a normal import target, so it is loaded explicitly here — appropriate, since the
loader is exactly the thing that consumes authored intent.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

from .model import Schema


def load_schema(path: str | Path) -> Schema:
    path = Path(path)
    spec = importlib.util.spec_from_file_location("_prism_ir_module", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load IR module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    schema = getattr(module, "SCHEMA", None)
    if not isinstance(schema, Schema):
        raise ValueError(f"{path} must define SCHEMA: Schema")
    return schema
