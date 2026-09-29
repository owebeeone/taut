"""TypeScript runner for the parity gate (see `parity_rust.py` for the shape).

node runs the IR-driven codec's `.ts` sources directly (`--experimental-strip-types`),
so there is no separate build: a runner that fails to load exits non-zero, which
fails the target. The codec is IR-driven and keeps a message's unknown fields, so it has
no forward-compat build and no `typescript/fc` variant (TautCheckedDecode.md §8
question 10). The three vector files and `dispatch.json` are copied beside it. A decoded
malformed or bounds row reports the hex of its re-encoding: `cbor.ts`'s `encode` of the
tree for a raw row, the codec's `encode` of the decoded value for a from_cbor row.

It speaks C3's bounds protocol (`parity.py`'s module docstring): it prints `#constants`
from `cbor.ts`'s `DEFAULT_MAX_DEPTH` and `MAX_DEPTH_CEILING`; a raw row's call passes
its `limits`; a from_cbor row decodes from bytes through `decode(schema, name, bytes)`,
which applies the message's effective bounds, and its line adds the bounds `SchemaIndex`
resolved for that root; and it expands a row's segments itself, reporting an expansion
whose length is not the row's `len` as `untyped`.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from . import parity, toolchains

TARGET = "typescript"

_RUNNER = r'''
import { readFileSync } from "node:fs";
import { DEFAULT_MAX_DEPTH, MAX_DEPTH_CEILING, decode as cborDecode, encode as cborEncode } from "./cbor.ts";
import { decode, decodeRef, encode } from "./codec.ts";
import { loadSchema } from "./schema.ts";

const schema = loadSchema(JSON.parse(readFileSync("parity_int.ir.json", "utf8")));
const intVectors = JSON.parse(readFileSync("int.vectors.json", "utf8")).vectors;
const malformed = JSON.parse(readFileSync("malformed.vectors.json", "utf8")).vectors;
const bounds = JSON.parse(readFileSync("bounds.vectors.json", "utf8")).vectors;
const dispatch = JSON.parse(readFileSync("dispatch.json", "utf8"));
const PAYLOAD = ["info", "major", "key", "expected", "enum", "value", "len", "limit"];

// The fixture's typed entry points, by message name (from_cbor) and enum name (from_wire).
// A message decodes from bytes under its effective bounds and returns the decoded value's
// own encoding; an enum row never accepts.
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

// One report line; tabs and line breaks inside a column are spaces.
function emit(...columns: string[]) {
  console.log(columns.map((column) => column.replace(/[\t\r\n]+/g, " ")).join("\t"));
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

// A row's bytes: a hex string, or segments, each a hex string or {repeat, count}, expanded
// here (the bounds protocol, item 5). An expansion whose length is not the row's `len`
// throws a plain Error, so the row is reported untyped.
function rowBytes(row: any): Uint8Array {
  const segments: [Uint8Array, number][] = (typeof row.bytes === "string" ? [row.bytes] : row.bytes).map(
    (seg: any) => (typeof seg === "string" ? [hexToBytes(seg), 1] : [hexToBytes(seg.repeat), seg.count]));
  const out = new Uint8Array(segments.reduce((sum, [piece, count]) => sum + piece.length * count, 0));
  let at = 0;
  for (const [piece, count] of segments) {
    for (let i = 0; i < count; i++) {
      out.set(piece, at);
      at += piece.length;
    }
  }
  if (row.len !== undefined && out.length !== row.len) {
    throw new Error(`bytes expand to ${out.length} bytes, len is ${row.len}`);
  }
  return out;
}

// A decoded row's re-encoding: the tree for raw_decode, decoded with the row's limits
// (item 2); the typed value for from_cbor, decoded from bytes by its message's typed entry
// point (item 3); nothing for from_wire.
function decodeRow(row: any, data: Uint8Array): Uint8Array {
  if (row.stage === "raw_decode") {
    const limits = row.limits ?? {};
    return cborEncode(cborDecode(data, { maxDepth: limits.max_depth, maxEncodedLen: limits.max_encoded_len }));
  } else if (row.stage === "from_cbor") {
    return fromCbor.get(row.schema)!(data);
  } else {
    fromWire.get(row.schema)!(data);
    return new Uint8Array(0);
  }
}

// A from_cbor row's fourth column (item 4): the bounds its typed entry point applies, as
// SchemaIndex resolves them for its root; an empty length where none applies.
function resolved(name: string): string {
  const e = schema.rootEffective({ k: "msg", name });
  return `max_depth=${e.max_depth};max_encoded_len=${e.max_encoded_len ?? ""}`;
}

// Item 1: the runtime's own constants, once.
emit("#constants", `default_max_depth=${DEFAULT_MAX_DEPTH};max_depth_ceiling=${MAX_DEPTH_CEILING}`);

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
for (const row of [...malformed, ...bounds]) {
  let columns: string[];
  try {
    columns = ["ok", bytesToHex(decodeRow(row, rowBytes(row)))];
  } catch (e: any) {
    columns = isDecodeError(e) ? ["err", describe(e)] : ["untyped", String(e)];
  }
  if (row.stage === "from_cbor") {
    columns.push(resolved(row.schema));
  }
  emit(row.name, ...columns);
}
'''


def run(forward_compat: bool = False) -> parity.TargetReport:
    """The typescript gate. There is no forward-compat build: `forward_compat` is refused."""
    if forward_compat:
        raise ValueError("typescript has no forward-compat variant: its IR-driven codec keeps unknown fields")
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
