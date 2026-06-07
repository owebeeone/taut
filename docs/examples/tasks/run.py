#!/usr/bin/env python3
"""Run the Tasks example end to end: load -> validate -> export -> encode/decode
a composed value -> run the breaking-change gate against the export. No network,
no codegen — just the library API. Run: python3 run.py"""

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2] / "src"))   # docs/examples/tasks -> prism/src

from prism.ir import compat
from prism.ir.export import export_to
from prism.ir.load import load_schema, schema_from_json
from prism.ir.validate import validate_or_raise
from prism.wire import codec


def main() -> None:
    schema = load_schema(HERE / "tasks.prism.py")
    validate_or_raise(schema)
    methods = sum(len(s.methods) for s in schema.services.values())
    print(f"valid IR: {len(schema.messages)} messages, {len(schema.enums)} enum(s), {methods} methods")

    export_to(schema, HERE / "tasks.ir.json")
    print("exported tasks.ir.json")

    # a composed value: Task embeds an optional User and a list of Comment
    task = {
        "id": 1, "title": "ship prism", "state": "doing",
        "assignee": {"id": 7, "name": "ann"},
        "comments": [
            {"author": {"id": 7, "name": "ann"}, "text": "started"},
            {"author": {"id": 9, "name": "bo"}, "text": "lgtm"},
        ],
    }
    blob = codec.encode(schema, "Task", task)
    assert codec.decode(schema, "Task", blob) == task
    print(f"Task -> {len(blob)} bytes: {blob.hex()}")
    print(f"round-trips (incl. nested + list-of-messages): {codec.decode(schema, 'Task', blob) == task}")

    # an absent optional nested message decodes as None
    later = {"id": 2, "title": "later", "state": "open", "assignee": None, "comments": []}
    assert codec.decode(schema, "Task", codec.encode(schema, "Task", later)) == later

    # the breaking-change gate against the export we just wrote: nothing changed
    baseline = schema_from_json(json.loads((HERE / "tasks.ir.json").read_text()))
    print(f"breaking changes vs export: {len(compat.breaking(baseline, schema))}")


if __name__ == "__main__":
    main()
