"""JavaScript runner for the parity gate (see `parity_rust.py` for the shape).

node loads the generated `api.js` and vendored `cbor.js` directly, so there is no
separate build: a runner that fails to load, or finds a fixture entry point missing
from `api.js`, exits non-zero, which fails the target. A decoded malformed row
reports the hex of its re-encoding: `cbor.js`'s `encode` of the tree for a raw row,
of the decoded value's `toCbor()` for a from_cbor row.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from . import parity, toolchains

TARGET = "js"

_RUNNER = r'''
"use strict";
const api = require("./api.js");
const { decode, encode } = require("./cbor.js");
const intVectors = require("./int.vectors.json").vectors;
const malformed = require("./malformed.vectors.json").vectors;
const dispatch = require("./dispatch.json");
const PAYLOAD = ["info", "major", "key", "expected", "enum", "value"];

function entryPoint(owner, key, name) {
  if (owner === undefined || typeof owner[key] !== "function") {
    throw new Error(`api.js has no entry point for ${name}`);
  }
  return (c) => owner[key](c);
}

// The fixture's typed entry points, by message name (from_cbor) and enum name (from_wire).
const fromCbor = new Map(dispatch.messages.map((name) => [name, entryPoint(api[name], "fromCbor", name)]));
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

function box(row) {
  return new api.IntBox({ n: BigInt(row.value.n), by_id: new Map(row.value.by_id.map(([k, v]) => [BigInt(k), BigInt(v)])) });
}

function emit(name, outcome, detail) {
  console.log(`${name}\t${outcome}\t${detail.replace(/[\t\r\n]+/g, " ")}`);
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

// A decoded row's re-encoding: the tree for raw_decode, the typed value for
// from_cbor, and nothing for from_wire (an enum row never accepts).
function decodeRow(row, data) {
  const c = decode(data);
  if (row.stage === "from_cbor") {
    return encode(fromCbor.get(row.schema)(c).toCbor());
  } else if (row.stage === "from_wire") {
    fromWire.get(row.schema)(c);
    return new Uint8Array(0);
  }
  return encode(c);
}

for (const row of intVectors) {
  if (row.kind === "round_trip") {
    try {
      const enc = hexFromBytes(encode(box(row).toCbor()));
      if (enc !== row.cbor) {
        emit(row.name, "fail", `encode ${enc}`);
        continue;
      }
      const dec = api.IntBox.fromCbor(decode(bytesFromHex(row.cbor)));
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
for (const row of malformed) {
  try {
    const again = decodeRow(row, bytesFromHex(row.bytes));
    emit(row.name, "ok", hexFromBytes(again));
  } catch (e) {
    if (isDecodeError(e)) {
      emit(row.name, "err", describe(e));
    } else {
      emit(row.name, "untyped", String(e));
    }
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
