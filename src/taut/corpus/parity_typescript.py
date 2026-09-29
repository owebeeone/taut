"""TypeScript runner for the parity gate (see `parity_rust.py` for the shape).

node runs the IR-driven codec's `.ts` sources directly (`--experimental-strip-types`),
so there is no separate build: a runner that fails to load exits non-zero, which
fails the target. The rows and `dispatch.json` are copied beside it. A decoded
malformed row reports the hex of its re-encoding: `cbor.ts`'s `encode` of the tree
for a raw row, the codec's `encode` of the decoded value for a from_cbor row.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from . import parity, toolchains

TARGET = "typescript"

_RUNNER = r'''
import { readFileSync } from "node:fs";
import { decode as cborDecode, encode as cborEncode } from "./cbor.ts";
import { decode, decodeRef, encode } from "./codec.ts";
import { loadSchema } from "./schema.ts";

const schema = loadSchema(JSON.parse(readFileSync("parity_int.ir.json", "utf8")));
const intVectors = JSON.parse(readFileSync("int.vectors.json", "utf8")).vectors;
const malformed = JSON.parse(readFileSync("malformed.vectors.json", "utf8")).vectors;
const dispatch = JSON.parse(readFileSync("dispatch.json", "utf8"));
const PAYLOAD = ["info", "major", "key", "expected", "enum", "value"];

// The fixture's typed entry points, by message name (from_cbor) and enum name (from_wire).
// A message returns the decoded value's own encoding; an enum row never accepts.
const fromCbor = new Map<string, (b: Uint8Array) => Uint8Array>(
  dispatch.messages.map((name: string) => [name, (b: Uint8Array) => encode(schema, name, decode(schema, name, b))]));
const fromWire = new Map<string, (b: Uint8Array) => unknown>(
  dispatch.enums.map((name: string) => [name, (b: Uint8Array) => decodeRef(schema, { k: "enum", name }, b)]));

function hexToBytes(hex: string): Uint8Array {
  return Uint8Array.from(Buffer.from(hex, "hex"));
}

function bytesToHex(b: Uint8Array): string {
  return Buffer.from(b).toString("hex");
}

function intBox(v: any) {
  return { n: BigInt(v.n), by_id: new Map(v.by_id.map(([k, x]: [string, string]) => [BigInt(k), BigInt(x)])) };
}

function emit(name: string, outcome: string, detail: string) {
  console.log(`${name}\t${outcome}\t${detail.replace(/[\t\r\n]+/g, " ")}`);
}

// A DecodeError is recognised by name and tag, not instanceof (TautCheckedDecode.md CD-E3).
function isDecodeError(e: any): boolean {
  return e != null && e.name === "DecodeError" && typeof e.tag === "string";
}

function describe(e: any): string {
  let detail = e.tag;
  for (const field of PAYLOAD) {
    if (e[field] !== undefined) {
      detail += `;${field}=${String(e[field])}`;
    }
  }
  return detail;
}

// A decoded row's re-encoding: the tree for raw_decode, the typed value for
// from_cbor, and nothing for from_wire.
function decodeRow(row: any, data: Uint8Array): Uint8Array {
  if (row.stage === "raw_decode") {
    return cborEncode(cborDecode(data));
  } else if (row.stage === "from_cbor") {
    return fromCbor.get(row.schema)!(data);
  } else {
    fromWire.get(row.schema)!(data);
    return new Uint8Array(0);
  }
}

for (const row of intVectors) {
  const native = intBox(row.value);
  if (row.kind === "round_trip") {
    try {
      const enc = bytesToHex(encode(schema, row.message, native));
      if (enc !== row.cbor) {
        emit(row.name, "fail", `encode ${enc}`);
        continue;
      }
      const dec: any = decode(schema, row.message, hexToBytes(row.cbor));
      const ok = dec.n === native.n && bytesToHex(encode(schema, row.message, dec)) === row.cbor;
      emit(row.name, ok ? "pass" : "fail", ok ? "" : "roundtrip mismatch");
    } catch (e: any) {
      emit(row.name, "fail", `threw ${e && e.tag ? e.tag : e}`);
    }
  } else {
    try {
      encode(schema, row.message, native);
      emit(row.name, "fail", "encoded, expected IntOutOfSubset");
    } catch (e: any) {
      emit(row.name, e && e.tag === row.expect.tag ? "pass" : "fail", e && e.tag ? e.tag : String(e));
    }
  }
}
for (const row of malformed) {
  try {
    const again = decodeRow(row, hexToBytes(row.bytes));
    emit(row.name, "ok", bytesToHex(again));
  } catch (e: any) {
    if (isDecodeError(e)) {
      emit(row.name, "err", describe(e));
    } else {
      emit(row.name, "untyped", String(e));
    }
  }
}
'''


def run() -> parity.TargetReport:
    node = toolchains.find_node_for_typescript()
    if node is None:
        return parity.skipped(TARGET, "node with --experimental-strip-types (node >= 22.6) not found")
    from ..ir.export import export_to

    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        failed = parity.generate(TARGET, work, runtime=True)
        if failed is not None:
            return failed
        ts_dir = work / TARGET
        export_to(parity.parity_schema(), ts_dir / "parity_int.ir.json")
        parity.write_json_rows(ts_dir)
        (ts_dir / "runner.ts").write_text(_RUNNER)
        return parity.run_runner(TARGET, [node, "--experimental-strip-types", "runner.ts"], cwd=ts_dir)
