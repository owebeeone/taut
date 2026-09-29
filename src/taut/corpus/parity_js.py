"""JavaScript runner for the parity gate (see `parity_rust.py` for the shape).

node loads the generated `api.js` and vendored `cbor.js` directly, so there is no
separate build: a runner that fails to load, or finds a fixture entry point missing
from `api.js`, exits non-zero, which fails the target. A decoded malformed or bounds row
reports the hex of its re-encoding: `cbor.js`'s `encode` of the tree for a raw row, of
the decoded value's `toCbor()` for a from_cbor row.

The runner speaks the bounds protocol (`parity.py`'s docstring, TautCheckedDecode.md
CD-C4): it prints `#constants` once from `cbor.js`'s own `DEFAULT_MAX_DEPTH` and
`MAX_DEPTH_CEILING`; passes a raw row's `limits` to `decode(data, { maxDepth,
maxEncodedLen })`; decodes every from_cbor row from bytes through its message's typed
entry point, `X.decode(bytes)`, and reports as a fourth column the bounds that entry
point applies, `X.MAX_DEPTH` and `X.MAX_ENCODED_LEN`; and expands a row's segments
itself, reporting an expansion whose length is not the row's `len` as untyped.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from . import parity, toolchains

TARGET = "js"

_RUNNER = r'''
"use strict";
const api = require("./api.js");
const { DEFAULT_MAX_DEPTH, MAX_DEPTH_CEILING, decode, encode } = require("./cbor.js");
const intVectors = require("./int.vectors.json").vectors;
const decodeRows = [...require("./malformed.vectors.json").vectors, ...require("./bounds.vectors.json").vectors];
const dispatch = require("./dispatch.json");
const PAYLOAD = ["info", "major", "key", "expected", "enum", "value", "len", "limit"];
// A raw row's limits, named as the corpus names them, as decode's options (CD-B3).
const OPTIONS = { max_depth: "maxDepth", max_encoded_len: "maxEncodedLen" };

function entryPoint(owner, key, name) {
  if (owner === undefined || typeof owner[key] !== "function") {
    throw new Error(`api.js has no entry point for ${name}`);
  }
  return (c) => owner[key](c);
}

// A message's class, the owner of its typed entry point `decode` and of the bounds it applies.
function messageClass(name) {
  entryPoint(api[name], "decode", name);
  return api[name];
}

// The fixture's typed entry points: a message's class by name (from_cbor), an enum's
// FromCbor by name (from_wire).
const messages = new Map(dispatch.messages.map((name) => [name, messageClass(name)]));
const fromWire = new Map(dispatch.enums.map((name) => [name, entryPoint(api, `${name}FromCbor`, name)]));

function bytesFromHex(hex) {
  const out = new Uint8Array(hex.length / 2);
  for (let i = 0; i < out.length; i++) {
    out[i] = parseInt(hex.slice(i * 2, i * 2 + 2), 16);
  }
  return out;
}

function hexFromBytes(b) {
  return Array.from(b, (x) => x.toString(16).padStart(2, "0")).join("");
}

// A row's input, its segments expanded (the bounds protocol, item 5): a hex string, or a
// list of hex strings and {repeat, count} segments. An expansion whose length is not the
// row's `len` throws a plain Error, which the row reports as untyped.
function rowBytes(row) {
  const segments = typeof row.bytes === "string" ? [row.bytes] : row.bytes;
  const parts = segments.map((seg) => (typeof seg === "string"
    ? [bytesFromHex(seg), 1]
    : [bytesFromHex(seg.repeat), seg.count]));
  const out = new Uint8Array(parts.reduce((total, [unit, count]) => total + unit.length * count, 0));
  let at = 0;
  for (const [unit, count] of parts) {
    for (let i = 0; i < count; i++) {
      out.set(unit, at);
      at += unit.length;
    }
  }
  if (row.len !== undefined && out.length !== row.len) {
    throw new Error(`bytes expand to ${out.length} bytes, len is ${row.len}`);
  }
  return out;
}

// The options a raw row's call passes: its limits, or none for the defaults (item 2).
function limitsOf(row) {
  const options = {};
  for (const [name, value] of Object.entries(row.limits || {})) {
    options[OPTIONS[name] || name] = value;
  }
  return options;
}

// The bounds a message's typed entry point applies, as its class states them (item 4).
function resolved(cls) {
  const length = cls.MAX_ENCODED_LEN;
  return `max_depth=${cls.MAX_DEPTH};max_encoded_len=${length === null ? "" : length}`;
}

function box(row) {
  return new api.IntBox({ n: BigInt(row.value.n), by_id: new Map(row.value.by_id.map(([k, v]) => [BigInt(k), BigInt(v)])) });
}

function emit(...columns) {
  console.log(columns.map((column) => String(column).replace(/[\t\r\n]+/g, " ")).join("\t"));
}

// A DecodeError is recognised by name and tag, not instanceof (TautCheckedDecode.md CD-E3).
function isDecodeError(e) {
  return e != null && e.name === "DecodeError" && typeof e.tag === "string";
}

function describe(e) {
  let detail = e.tag;
  for (const field of PAYLOAD) {
    if (e[field] !== undefined) {
      detail += `;${field}=${String(e[field])}`;
    }
  }
  return detail;
}

// A decoded row's re-encoding: a raw row's tree, decoded with its limits (item 2); a
// from_cbor row's typed value, decoded from bytes by its message's `decode`, which applies
// the message's bounds (item 3); and nothing for from_wire (an enum row never accepts).
function decodeRow(row, data) {
  if (row.stage === "from_cbor") {
    return encode(messages.get(row.schema).decode(data).toCbor());
  } else if (row.stage === "from_wire") {
    fromWire.get(row.schema)(decode(data));
    return new Uint8Array(0);
  }
  return encode(decode(data, limitsOf(row)));
}

emit("#constants", `default_max_depth=${DEFAULT_MAX_DEPTH};max_depth_ceiling=${MAX_DEPTH_CEILING}`);
for (const row of intVectors) {
  if (row.kind === "round_trip") {
    try {
      const enc = hexFromBytes(encode(box(row).toCbor()));
      if (enc !== row.cbor) {
        emit(row.name, "fail", `encode ${enc}`);
        continue;
      }
      const dec = api.IntBox.decode(bytesFromHex(row.cbor));
      const ok = typeof dec.n === "bigint" && dec.n === BigInt(row.value.n) && hexFromBytes(encode(dec.toCbor())) === row.cbor;
      emit(row.name, ok ? "pass" : "fail", ok ? "" : "roundtrip mismatch");
    } catch (e) {
      emit(row.name, "fail", `threw ${e && e.tag ? e.tag : e}`);
    }
  } else {
    try {
      encode(box(row).toCbor());
      emit(row.name, "fail", "encoded, expected IntOutOfSubset");
    } catch (e) {
      emit(row.name, e && e.tag === row.expect.tag ? "pass" : "fail", e && e.tag ? e.tag : String(e));
    }
  }
}
for (const row of decodeRows) {
  let outcome = "ok";
  let detail;
  try {
    detail = hexFromBytes(decodeRow(row, rowBytes(row)));
  } catch (e) {
    outcome = isDecodeError(e) ? "err" : "untyped";
    detail = isDecodeError(e) ? describe(e) : String(e);
  }
  if (row.stage === "from_cbor") {
    emit(row.name, outcome, detail, resolved(messages.get(row.schema)));
  } else {
    emit(row.name, outcome, detail);
  }
}
'''


def run(forward_compat: bool = False) -> parity.TargetReport:
    """The js gate, or with `forward_compat` its `js/fc` variant (`parity_rust.py`)."""
    name = parity.variant(TARGET, forward_compat)
    node = toolchains.find_node()
    if node is None:
        return parity.skipped(name, "node not found")
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        failed = parity.generate(name, work, runtime=True)
        if failed is not None:
            return failed
        js_dir = work / TARGET
        parity.write_json_rows(js_dir)
        (js_dir / "runner.js").write_text(_RUNNER)
        return parity.run_runner(name, [node, "runner.js"], cwd=js_dir)
