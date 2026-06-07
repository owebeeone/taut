#!/usr/bin/env python3
"""Run the Tasks example end to end: load -> validate -> export -> encode/decode
a composed value -> run the breaking-change gate against the export. No network,
no codegen — just the library API. Run: python3 run.py"""

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2] / "src"))   # docs/examples/tasks -> taut/src

from taut import ext
from taut.ir import compat
from taut.ir.dsl import INT, STR, F, Msg, extension, schema as mk_schema
from taut.ir.export import export_to
from taut.ir.load import load_schema, schema_from_json
from taut.ir.shapes import BAND_START
from taut.ir.validate import validate_or_raise
from taut.wire import codec


def main() -> None:
    schema = load_schema(HERE / "tasks.taut.py")
    validate_or_raise(schema)
    methods = sum(len(s.methods) for s in schema.services.values())
    print(f"valid IR: {len(schema.messages)} messages, {len(schema.enums)} enum(s), {methods} methods")

    export_to(schema, HERE / "tasks.ir.json")
    print("exported tasks.ir.json")

    # a composed value: Task embeds an optional User and a list of Comment
    task = {
        "id": 1, "title": "ship taut", "state": "doing",
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

    # --- forward-compat + a side-channel extension --------------------------
    # An *infra* schema (separate from the app) declares a Trace side-channel.
    infra = mk_schema(
        Msg("Trace", F("trace_id", 1, STR), F("hop", 2, INT)),
        extension("Trace", tag=BAND_START + 7),
    )
    trace_tag = BAND_START + 7

    blob = codec.encode(schema, "Task", task)
    tagged = ext.ext_set(infra, blob, "Trace", trace_tag, {"trace_id": "abc123", "hop": 1})
    print(f"infra reads its side-channel: {ext.ext_get(infra, tagged, 'Trace', trace_tag)}")

    # the app decodes its Task, oblivious to the Trace, and preserves it
    back = codec.decode(schema, "Task", tagged)
    print(f"app sees its own fields (title={back['title']!r}); "
          f"side-channel preserved: {trace_tag in back.get('__unknown__', {})}")


if __name__ == "__main__":
    main()
